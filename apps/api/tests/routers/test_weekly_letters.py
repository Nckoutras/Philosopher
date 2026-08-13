"""Tests for PATCH /api/v1/weekly-letters/{id}/write-back — A13 memory hand-off.

Covers ONLY the A13 change: a successful write-back distils the reader's own
words into the memory pipeline, and a memory failure never breaks the write-back.
The endpoint's pre-existing paths (403 free tier, 422 empty, 404 missing letter,
overwrite semantics) predate A13 and are deliberately not covered here.

Uses FastAPI TestClient with dependency overrides for DB and auth, matching
tests/routers/test_scheduled_emails.py. Auth here is get_current_user_plan, which
yields a (user, plan) tuple rather than a bare user.

Run: cd apps/api && pytest tests/routers/test_weekly_letters.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID   = "aaaaaaaa-0000-0000-0000-000000000001"
LETTER_ID = "cccccccc-0000-0000-0000-000000000001"

WRITE_BACK_URL = f"/api/v1/weekly-letters/{LETTER_ID}/write-back"

TEXT = "I have been avoiding the conversation with my brother for three months now."


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = "user@example.com"
    return u


def _make_letter():
    """A Sunday letter with no write-back yet. voice_persona_id is None so the
    endpoint takes its single-query path (no persona lookup)."""
    letter = MagicMock()
    letter.id = LETTER_ID
    letter.user_id = USER_ID
    letter.period_start = datetime.now(timezone.utc) - timedelta(days=7)
    letter.period_end = datetime.now(timezone.utc)
    letter.status = "delivered"
    letter.kind = "weekly"
    letter.payload = {"pull_quote": "You already know."}
    letter.read_at = datetime.now(timezone.utc)
    letter.write_back_text = None
    letter.write_back_at = None
    letter.voice_persona_id = None
    return letter


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    db_holder   = [AsyncMock()]
    auth_holder = [(_make_user(), "pro")]

    async def override_db():
        yield db_holder[0]

    async def override_auth():
        return auth_holder[0]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_plan] = override_auth

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    # NOT `_auth` — httpx.Client uses that name internally for its auth flow.
    tc._auth_holder = auth_holder
    tc._app = app

    # Preserve whatever the app already carries so one test can never leak an
    # arq_queue into another.
    had_queue = hasattr(app.state, "arq_queue")
    prior = getattr(app.state, "arq_queue", None)

    yield tc

    if had_queue:
        app.state.arq_queue = prior
    elif hasattr(app.state, "arq_queue"):
        delattr(app.state, "arq_queue")
    app.dependency_overrides.clear()


def _patch_db_for(client, letter):
    """Wire the mocked session so the letter lookup returns `letter`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = letter

    async def fake_execute(q):
        return result

    client._db[0].execute = fake_execute
    client._db[0].commit = AsyncMock()


# ── A13 ───────────────────────────────────────────────────────────────────────

def test_write_back_enqueues_distill_to_memory(client):
    """T1 — the reader's own words are handed to the memory pipeline with the
    letter_write_back label and a null conversation_id (a letter is not a
    conversation), so they feed chat recall / letters / insights like every other
    self-stated text."""
    letter = _make_letter()
    arq_queue = AsyncMock()
    client._app.state.arq_queue = arq_queue

    with patch("routers.weekly_letters.select", side_effect=lambda *a, **kw: MagicMock()):
        _patch_db_for(client, letter)
        resp = client.patch(WRITE_BACK_URL, json={"text": TEXT})

    assert resp.status_code == 200

    arq_queue.enqueue_job.assert_awaited_once_with(
        "distill_user_text_to_memory_task",
        USER_ID,
        None,
        TEXT,
        "letter_write_back",
    )


def test_enqueue_failure_does_not_break_the_write_back(client, caplog):
    """T2 — the A13 hard requirement. The write-back is the user's data; the memory
    distil is a side effect. If the queue is down the endpoint must still return 200
    with the write-back persisted, and the failure must be logged, not raised."""
    letter = _make_letter()
    arq_queue = AsyncMock()
    arq_queue.enqueue_job.side_effect = RuntimeError("redis is down")
    client._app.state.arq_queue = arq_queue

    with patch("routers.weekly_letters.select", side_effect=lambda *a, **kw: MagicMock()):
        _patch_db_for(client, letter)
        with caplog.at_level("ERROR", logger="routers.weekly_letters"):
            resp = client.patch(WRITE_BACK_URL, json={"text": TEXT})

    # The endpoint survived the raise.
    assert resp.status_code == 200

    # The write-back itself is persisted — committed before the enqueue is attempted.
    assert letter.write_back_text == TEXT
    assert letter.write_back_at is not None
    client._db[0].commit.assert_awaited()

    # And the response still carries it back to the reader.
    body = resp.json()
    assert body["write_back_text"] == TEXT
    assert body["write_back_at"] is not None

    # The failure was logged rather than swallowed silently.
    assert any(
        "Letter write-back enqueue failed" in r.message and LETTER_ID in r.message
        for r in caplog.records
    )
