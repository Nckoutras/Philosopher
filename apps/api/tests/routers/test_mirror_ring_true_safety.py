"""Safety gate on the mirror ring-true note (A18c).

The note is free text about the user's own reaction to the mirror. Before this
gate the note was committed and only then handed to the ARQ memory task, whose
safety check runs asynchronously in the worker — so a crisis signal was stored
and nothing answered it.

Follows the TestClient + dependency_overrides pattern in test_mirror_share.py.

Run: cd apps/api && pytest tests/routers/test_mirror_ring_true_safety.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
MIRROR_ID = "22222222-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/mirrors/{MIRROR_ID}/ring-true"

CRISIS_NOTE = "reading this made me want to die"
SAFE_NOTE = "this landed harder than I expected"


class FakeMirror:
    """Plain object, not a MagicMock: attribute writes must be observable.

    A MagicMock would silently accept and record `ring_true_note = ...` while
    still answering any read, so "was the note written?" could not be asserted
    honestly. Real attributes make an unwanted write visible.
    """

    def __init__(self):
        self.id = MIRROR_ID
        self.kind = "weekly"
        self.status = "generated"
        self.period_start = datetime(2026, 8, 10, tzinfo=timezone.utc)
        self.period_end = datetime(2026, 8, 17, tzinfo=timezone.utc)
        self.payload = {"body": "a mirror"}
        self.created_at = datetime(2026, 8, 17, tzinfo=timezone.utc)
        self.host_persona_id = None
        self.ring_true = None
        self.ring_true_note = None
        self.ring_true_at = None


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _make_db(mirror):
    """Mock session. First execute() returns the mirror; later ones (persona
    lookup) return an empty result."""
    db = AsyncMock()

    mirror_result = MagicMock()
    mirror_result.scalar_one_or_none.return_value = mirror

    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None

    calls = [mirror_result]

    async def _execute(*args, **kwargs):
        return calls.pop(0) if calls else empty

    db.execute = AsyncMock(side_effect=_execute)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@contextmanager
def _client(mirror):
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db = _make_db(mirror)
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app, raise_server_exceptions=False), db
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


SAFETY_FRAGMENT = "please reach out to someone you trust"


def test_crisis_note_is_not_persisted_and_returns_safety_copy():
    """The load-bearing case: a high-risk note must not reach the database, and
    the caller must get the app-voice safety message back."""
    mirror = FakeMirror()

    with _client(mirror) as (client, db):
        resp = client.post(ENDPOINT, json={"ring_true": "yes", "note": CRISIS_NOTE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["safety_triggered"] is True
    assert SAFETY_FRAGMENT in body["safety_message"]

    # NOT persisted — no attribute was assigned, and no commit was issued.
    assert mirror.ring_true_note is None, "crisis note was written to the mirror"
    assert mirror.ring_true is None, "ring_true was written despite safety firing"
    assert mirror.ring_true_at is None
    db.commit.assert_not_awaited()

    # The event was recorded for operators.
    assert db.add.call_count == 1, "expected exactly one SafetyEvent row"


def test_safe_note_is_persisted_normally():
    """A note with no risk phrase behaves exactly as before the gate."""
    mirror = FakeMirror()

    with _client(mirror) as (client, db):
        resp = client.post(ENDPOINT, json={"ring_true": "partly", "note": SAFE_NOTE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["safety_triggered"] is False
    assert body["safety_message"] is None
    assert body["ring_true"] == "partly"
    assert body["ring_true_note"] == SAFE_NOTE

    assert mirror.ring_true == "partly"
    assert mirror.ring_true_note == SAFE_NOTE
    assert mirror.ring_true_at is not None
    db.commit.assert_awaited()


def test_empty_note_skips_the_safety_check_entirely():
    """No note → check_input is never called, and the write proceeds."""
    mirror = FakeMirror()

    with patch("routers.mirrors.safety_service.check_input", new=AsyncMock()) as spy:
        with _client(mirror) as (client, db):
            resp = client.post(ENDPOINT, json={"ring_true": "no", "note": None})

    assert resp.status_code == 200
    spy.assert_not_awaited()
    assert mirror.ring_true == "no"
    assert mirror.ring_true_note is None


def test_whitespace_only_note_skips_the_safety_check():
    """`.strip()` makes a blank note equivalent to no note."""
    mirror = FakeMirror()

    with patch("routers.mirrors.safety_service.check_input", new=AsyncMock()) as spy:
        with _client(mirror) as (client, db):
            resp = client.post(ENDPOINT, json={"ring_true": "yes", "note": "   "})

    assert resp.status_code == 200
    spy.assert_not_awaited()


def test_medium_risk_note_also_suppresses():
    """should_suppress_persona is level >= medium, not high-only."""
    mirror = FakeMirror()

    with _client(mirror) as (client, db):
        resp = client.post(ENDPOINT, json={"ring_true": "yes", "note": "everything feels hopeless"})

    assert resp.status_code == 200
    assert resp.json()["safety_triggered"] is True
    assert mirror.ring_true_note is None


def test_low_risk_note_is_logged_but_still_persisted():
    """Low risk logs a SafetyEvent and lets the write through — matching chat,
    where `should_log` and `should_suppress_persona` are independent gates."""
    mirror = FakeMirror()

    with _client(mirror) as (client, db):
        resp = client.post(ENDPOINT, json={"ring_true": "yes", "note": "I feel worthless lately"})

    assert resp.status_code == 200
    assert resp.json()["safety_triggered"] is False
    assert mirror.ring_true_note == "I feel worthless lately"
    assert db.add.call_count == 1, "low-risk note should still record a SafetyEvent"


def test_safety_response_is_a_well_formed_mirror_out():
    """The reason the safety path returns MirrorOut rather than a bare dict: the
    client must still receive every field it reads off this shape. The mirror is
    returned in pre-note state, since the note was rejected before any write."""
    mirror = FakeMirror()
    mirror.ring_true = "yes"          # a value from an earlier, safe submission
    mirror.ring_true_note = "earlier note"

    with _client(mirror) as (client, db):
        resp = client.post(ENDPOINT, json={"ring_true": "no", "note": CRISIS_NOTE})

    body = resp.json()
    for field in ("id", "kind", "status", "period_start", "period_end",
                  "payload", "ring_true", "ring_true_note", "created_at"):
        assert field in body, f"MirrorOut field {field} missing from safety response"

    assert body["id"] == MIRROR_ID
    assert body["safety_triggered"] is True
    # Pre-note state preserved: the rejected submission did not overwrite either
    # the prior value or the prior note.
    assert body["ring_true"] == "yes"
    assert body["ring_true_note"] == "earlier note"
