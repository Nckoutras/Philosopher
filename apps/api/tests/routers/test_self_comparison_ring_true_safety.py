"""Safety gate on the self-comparison ring-true note (A18c).

This surface was the worse of the two: no safety call of any kind on the note,
no memory enqueue, and a 204 with no body — so a crisis signal was written to
the database and neither the user nor an operator saw anything.

(services/self_comparison_service.py does gate the generation *prompt*; it is
the ring-true note that was ungated.)

Run: cd apps/api && pytest tests/routers/test_self_comparison_ring_true_safety.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
COMPARISON_ID = "33333333-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/self-comparison/{COMPARISON_ID}/ring-true"

CRISIS_NOTE = "honestly I want to die"
SAFE_NOTE = "the older me sounded calmer"

SAFETY_FRAGMENT = "please reach out to someone you trust"


class FakeComparison:
    """Plain object so an unwanted attribute write is observable — see the note
    in test_mirror_ring_true_safety.FakeMirror."""

    def __init__(self):
        self.id = COMPARISON_ID
        self.ring_true = None
        self.ring_true_note = None
        self.ring_true_at = None


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _make_db(row):
    db = AsyncMock()

    row_result = MagicMock()
    row_result.scalar_one_or_none.return_value = row

    db.execute = AsyncMock(return_value=row_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@contextmanager
def _client(row):
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db = _make_db(row)
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app, raise_server_exceptions=False), db
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_crisis_note_is_not_persisted_and_returns_200_with_safety_body():
    """The load-bearing case. Note must not reach the database; response carries
    the safety copy at 200 rather than the usual empty 204."""
    row = FakeComparison()

    with _client(row) as (client, db):
        resp = client.patch(ENDPOINT, json={"ring_true": "yes", "note": CRISIS_NOTE})

    assert resp.status_code == 200
    body = resp.json()
    assert body["safety"] is True
    assert SAFETY_FRAGMENT in body["message"]

    # NOT persisted.
    assert row.ring_true_note is None, "crisis note was written to the row"
    assert row.ring_true is None, "ring_true was written despite safety firing"
    assert row.ring_true_at is None

    assert db.add.call_count == 1, "expected exactly one SafetyEvent row"


def test_safe_note_still_returns_204_and_persists():
    """The normal path is unchanged: 204, no body, note written."""
    row = FakeComparison()

    with _client(row) as (client, db):
        resp = client.patch(ENDPOINT, json={"ring_true": "partly", "note": SAFE_NOTE})

    assert resp.status_code == 204
    assert resp.content == b""

    assert row.ring_true == "partly"
    assert row.ring_true_note == SAFE_NOTE
    assert row.ring_true_at is not None


def test_empty_note_skips_the_safety_check_entirely():
    row = FakeComparison()

    with patch("routers.self_comparison.safety_service.check_input", new=AsyncMock()) as spy:
        with _client(row) as (client, db):
            resp = client.patch(ENDPOINT, json={"ring_true": "no"})

    assert resp.status_code == 204
    spy.assert_not_awaited()
    assert row.ring_true == "no"
    assert row.ring_true_note is None


def test_whitespace_only_note_skips_the_safety_check():
    row = FakeComparison()

    with patch("routers.self_comparison.safety_service.check_input", new=AsyncMock()) as spy:
        with _client(row) as (client, db):
            resp = client.patch(ENDPOINT, json={"ring_true": "yes", "note": "  "})

    assert resp.status_code == 204
    spy.assert_not_awaited()


def test_medium_risk_note_also_suppresses():
    """should_suppress_persona is level >= medium, not high-only."""
    row = FakeComparison()

    with _client(row) as (client, db):
        resp = client.patch(ENDPOINT, json={"ring_true": "yes", "note": "nothing matters now"})

    assert resp.status_code == 200
    assert resp.json()["safety"] is True
    assert row.ring_true_note is None


def test_low_risk_note_is_logged_but_still_persisted():
    """Low risk logs and lets the write through — independent gates."""
    row = FakeComparison()

    with _client(row) as (client, db):
        resp = client.patch(ENDPOINT, json={"ring_true": "yes", "note": "just exhausted"})

    assert resp.status_code == 204
    assert row.ring_true_note == "just exhausted"
    assert db.add.call_count == 1, "low-risk note should still record a SafetyEvent"
