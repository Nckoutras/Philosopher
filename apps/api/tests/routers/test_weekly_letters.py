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


# ── A17: 'failed' rows must never reach the client ────────────────────────────

def test_list_excludes_failed_letters(client):
    """A17 — a 'failed' row records a letter the LLM wrote and we lost to malformed
    JSON. It is an operator-visibility fact, never a user-facing state: the letters
    list renders any non-'generated', non-'suppressed' row as "A quiet week — no
    letter this time", which for a failed row is a confident falsehood about a week
    that was not quiet.

    This asserts the QUERY, not the mocked rows. The session here is an AsyncMock, so
    it returns whatever it is told and no SQL is ever executed — a test that fed it two
    rows and checked only one came back would be asserting on its own mock. Compiling
    the statement is the only way to prove the predicate is actually there.
    """
    captured = []

    letters_result = MagicMock()
    letters_result.scalars.return_value.all.return_value = []

    async def capturing_execute(stmt):
        captured.append(stmt)
        return letters_result

    client._db[0].execute = capturing_execute

    resp = client.get("/api/v1/weekly-letters")

    assert resp.status_code == 200
    assert len(captured) == 1, "expected exactly one query (no personas to load)"

    sql = str(captured[0].compile(compile_kwargs={"literal_binds": True}))
    assert "status != 'failed'" in sql, (
        f"list query must exclude failed letters; compiled WHERE was:\n{sql}"
    )
    # The pre-existing ownership filter is untouched.
    assert "user_id" in sql


# ── Γ-5: letter_write_back, the correspondence loop's closure ─────────────────
#
# The third and last of the letter events. delivered says an email left the
# building, open_to_app says one brought a person back, this says they answered
# it — and until Γ-5 the answering half was the only one of the three that the
# product collected and never counted.

def _patch_db_with_persona(client, letter, persona):
    """Two sequential execute() results: the letter, then its voice persona.

    _patch_db_for returns ONE result for every query, which is fine while
    voice_persona_id is None and the persona lookup is skipped. The host property
    needs the second query to answer differently, so this dispatches by call
    order rather than by inspecting the statement — the endpoint issues exactly
    these two, in this order.
    """
    letter_result, persona_result = MagicMock(), MagicMock()
    letter_result.scalar_one_or_none.return_value = letter
    persona_result.scalar_one_or_none.return_value = persona
    calls = []

    async def fake_execute(q):
        calls.append(q)
        return letter_result if len(calls) == 1 else persona_result

    client._db[0].execute = fake_execute
    client._db[0].commit = AsyncMock()


def _make_persona(slug="oscar_wilde"):
    p = MagicMock()
    p.slug = slug
    p.name = "Oscar Wilde"
    return p


def test_a_first_write_back_fires_the_event(client):
    """The closure event, with the three properties the registry declares."""
    letter = _make_letter()
    letter.period_start = datetime(2026, 9, 6, tzinfo=timezone.utc)
    letter.voice_persona_id = "bbbbbbbb-0000-0000-0000-000000000001"
    _patch_db_with_persona(client, letter, _make_persona())

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.patch(WRITE_BACK_URL, json={"text": TEXT})

    assert resp.status_code == 200
    analytics.track.assert_called_once()
    name, user_id, props = analytics.track.call_args[0]
    assert name == "letter_write_back"
    assert user_id == USER_ID
    assert props == {"week": "2026-W36", "host": "oscar_wilde",
                     "length_bucket": "under_100"}


def test_the_week_and_host_are_spelled_as_the_other_two_letter_events_spell_them(client):
    """THE REASON THE PROPERTY NAMES AND FORMATS MATTER MORE THAN USUAL.

    These three events are one funnel. letter_delivered and letter_open_to_app
    both send `week` as period_start.strftime('%G-W%V') and `host` as the voice
    persona's SLUG. A week rendered any other way — an ISO date, a period_start
    timestamp, the persona's display NAME — would not join, and the funnel would
    silently report zero conversion rather than failing.
    """
    letter = _make_letter()
    letter.period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)  # ISO week 2026-W01
    letter.voice_persona_id = "bbbbbbbb-0000-0000-0000-000000000001"
    _patch_db_with_persona(client, letter, _make_persona("carl_jung"))

    with patch("routers.weekly_letters.analytics_service") as analytics:
        client.patch(WRITE_BACK_URL, json={"text": TEXT})

    _, _, props = analytics.track.call_args[0]
    # 2026-01-01 falls in ISO week 2026-W01; %G (not %Y) is what makes the
    # year-boundary weeks agree across the three events.
    assert props["week"] == "2026-W01"
    assert props["host"] == "carl_jung"  # the slug, never the display name
    assert "Jung" not in str(props)


def test_a_revision_does_not_fire_again(client):
    """FIRST WRITE-BACK ONLY — the letter_open_to_app precedent, where a NULL
    email_opened_at is the idempotence and a second visit changes nothing.

    A re-submit overwrites the stored text, and that is a person changing their
    words rather than the loop closing a second time. Counting it would make the
    funnel's denominator mean two things at once.
    """
    letter = _make_letter()
    letter.voice_persona_id = None
    letter.write_back_at = datetime.now(timezone.utc) - timedelta(days=1)
    letter.write_back_text = "an earlier answer"
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.patch(WRITE_BACK_URL, json={"text": "a revised answer"})

    assert resp.status_code == 200
    analytics.track.assert_not_called()
    # The revision still LANDS — suppressing the event must not suppress the write.
    assert letter.write_back_text == "a revised answer"


def test_the_write_back_text_never_becomes_a_property(client):
    """The most sensitive string on this route: the reader's own words back to a
    letter. It may ride into the prompt and into a memory row; it may never ride
    into an analytics property, in any form — not whole, not truncated, not
    hashed, and not as an exact length."""
    letter = _make_letter()
    letter.voice_persona_id = None
    _patch_db_for(client, letter)
    secret = "My brother's name is Tomas and I have not called him since April."

    with patch("routers.weekly_letters.analytics_service") as analytics:
        client.patch(WRITE_BACK_URL, json={"text": secret})

    _, _, props = analytics.track.call_args[0]
    assert set(props) == {"week", "host", "length_bucket"}
    blob = str(props)
    for fragment in ("Tomas", "brother", "April", "called"):
        assert fragment not in blob
    assert str(len(secret)) not in blob   # not the exact length either


def test_the_event_fires_after_the_commit(client):
    """AFTER THE COMMIT, NEVER BEFORE — the Γ-1 rule, asserted by ORDER rather
    than by reading the code. An event that reports a write which then fails to
    persist is worse than no event: it reports a loop closing that did not."""
    letter = _make_letter()
    letter.voice_persona_id = None
    _patch_db_for(client, letter)

    order = []
    client._db[0].commit = AsyncMock(side_effect=lambda: order.append("commit"))

    with patch("routers.weekly_letters.analytics_service") as analytics:
        analytics.track.side_effect = lambda *a, **k: order.append("track")
        client.patch(WRITE_BACK_URL, json={"text": TEXT})

    assert order == ["commit", "track"]


def test_all_three_letter_events_build_week_with_the_same_expression():
    """The join, pinned at the SOURCE rather than at one call site's output.

    The test above proves THIS event renders 2026-W01. It cannot prove the other
    two still render it the same way — and the funnel breaks if any one of the
    three drifts, silently, by reporting zero conversion instead of an error.
    So this reads the three sites and asserts they share one expression.

    %G, not %Y: at a year boundary they differ (2026-01-01 is ISO week 2026-W01,
    but 2027-01-03 is 2026-W53), and a mix would break exactly the weeks nobody
    tests by hand.
    """
    import pathlib
    import re

    api_root = pathlib.Path(__file__).resolve().parents[2]
    sources = {
        "letter_delivered / _maybe_send_weekly_letter_email":
            (api_root / "workers" / "arq_worker.py").read_text(encoding="utf-8"),
        "letter_open_to_app + letter_write_back":
            (api_root / "routers" / "weekly_letters.py").read_text(encoding="utf-8"),
    }
    for where, src in sources.items():
        formats = set(re.findall(r'strftime\("([^"]+)"\)', src))
        assert formats == {"%G-W%V"}, (
            f"{where} renders a week as {formats or 'nothing'} — all three letter "
            f"events must use %G-W%V or they stop joining"
        )
    # And all three names are present across those two files, so this test starts
    # failing if an event is renamed out from under it.
    joined = "".join(sources.values())
    for name in ("letter_delivered", "letter_open_to_app", "letter_write_back"):
        assert f'"{name}"' in joined
