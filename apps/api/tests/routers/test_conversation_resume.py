"""Γ-3 — the bare persona open resumes, and says so exactly once.

THE EVENT PAIR IS THE POINT. conversation_started and conversation_resumed are
mutually exclusive, and getting that wrong is not a reporting nicety: a resumed
thread counted as a start would inflate the top of the funnel with RETURNS, so
the started -> completed ratio would read worse every time the open-thread loop
actually worked. The feature would look like a regression in the dashboard that
measures it.

The QUERY semantics (newest wins, 14-day window, deleted, other personas) live
in tests/db_live/test_resume_thread.py — they are three-valued SQL against real
rows and a mocked session would answer whatever it was told.

Run: cd apps/api && pytest tests/routers/test_conversation_resume.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
CONV_ID = "cccccccc-0000-0000-0000-000000000009"
URL = "/api/v1/conversations"


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _make_persona():
    p = MagicMock()
    p.id = "pppppppp-0000-0000-0000-000000000001"
    p.slug = "socrates"
    p.name = "Socrates"
    p.era = None
    p.tradition = None
    p.tier = "free"
    p.tagline = None
    p.portrait_url = "/personas/socrates.webp"
    p.bio = None
    p.is_active = True
    return p


def _make_conv(last_message_at, message_count=4):
    """C-06: every field ConversationOut reads is set explicitly. A MagicMock
    attribute reaching a pydantic model raises inside the router, not here."""
    c = MagicMock()
    c.id = CONV_ID
    c.user_id = USER_ID
    c.persona = _make_persona()
    c.title = None
    c.message_count = message_count
    c.last_message_at = last_message_at
    c.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    c.source_persona_slug = None
    c.source_context_content = None
    c.last_message_snippet = None
    c.deep_mode = False
    c.ritual_id = None
    c.deleted_at = None
    return c


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    db_holder = [AsyncMock()]

    async def override_db():
        yield db_holder[0]

    async def override_auth():
        return (_make_user(), "pro")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_plan] = override_auth

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    yield tc
    app.dependency_overrides.clear()


# ── The two events never both fire ───────────────────────────────────────────

def test_a_resume_fires_conversation_resumed_and_not_started(client):
    conv = _make_conv(datetime.now(timezone.utc) - timedelta(hours=5))

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, True))), \
         patch("routers.conversations.analytics_service") as analytics:
        resp = client.post(URL, json={"persona_slug": "socrates", "resume": True})

    assert resp.status_code == 201
    names = [c[0][0] for c in analytics.track.call_args_list]
    assert names == ["conversation_resumed"], (
        f"a resumed thread did not START; expected only conversation_resumed, got {names}"
    )
    _, user_id, props = analytics.track.call_args_list[0][0]
    assert user_id == USER_ID
    # Γ-5 added conversation_id, and it is asserted to be THE RESUMED THREAD'S id
    # rather than merely present. That is the whole value of the property: the
    # event exists to be joined to message_sent on this id, and an id naming some
    # other conversation would make the join silently wrong instead of absent.
    assert props == {
        "persona_slug": "socrates",
        "conversation_id": CONV_ID,
        "gap_bucket": "under_24h",
    }


def test_a_miss_still_fires_conversation_started(client):
    """resume=true that finds nothing resumable must behave exactly as today —
    the fallback is the whole reason this is safe to turn on for every open."""
    conv = _make_conv(None, message_count=0)

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, False))), \
         patch("routers.conversations.analytics_service") as analytics:
        resp = client.post(URL, json={"persona_slug": "socrates", "resume": True})

    assert resp.status_code == 201
    names = [c[0][0] for c in analytics.track.call_args_list]
    assert names == ["conversation_started"]
    _, _, props = analytics.track.call_args_list[0][0]
    assert props["via"] == "direct"
    assert props["seeded_topic"] is False


def test_the_default_path_never_resumes(client):
    """Every seeded door omits `resume`, and must keep creating. A seed appended
    to an old thread would land the letter's opening line in the middle of a
    week-old conversation."""
    conv = _make_conv(None, message_count=0)

    with patch("routers.conversations.conversation_service.create",
               AsyncMock(return_value=conv)) as create, \
         patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock()) as resume, \
         patch("routers.conversations.analytics_service") as analytics:
        resp = client.post(URL, json={"persona_slug": "socrates"})

    assert resp.status_code == 201
    create.assert_awaited_once()
    resume.assert_not_awaited()
    assert [c[0][0] for c in analytics.track.call_args_list] == ["conversation_started"]


def test_a_seeded_open_still_creates(client):
    """skip_opening is the seeded-door marker; it must not route through resume."""
    conv = _make_conv(None, message_count=0)

    with patch("routers.conversations.conversation_service.create",
               AsyncMock(return_value=conv)) as create, \
         patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock()) as resume, \
         patch("routers.conversations.analytics_service"):
        resp = client.post(URL, json={"persona_slug": "socrates", "skip_opening": True})

    assert resp.status_code == 201
    create.assert_awaited_once()
    resume.assert_not_awaited()


# ── The response tells the client what happened ──────────────────────────────

@pytest.mark.parametrize("resumed", [True, False])
def test_the_response_carries_the_resumed_flag(client, resumed):
    """The client cannot work it out for itself, and it changes where the user
    lands: /app/chat/[slug] holds no history, so a resumed thread has to be
    handed to the conversation page that loads one."""
    conv = _make_conv(datetime.now(timezone.utc) - timedelta(hours=2))

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, resumed))), \
         patch("routers.conversations.analytics_service"):
        resp = client.post(URL, json={"persona_slug": "socrates", "resume": True})

    assert resp.json()["resumed"] is resumed


def test_a_plain_create_reports_resumed_false(client):
    conv = _make_conv(None, message_count=0)
    with patch("routers.conversations.conversation_service.create",
               AsyncMock(return_value=conv)), \
         patch("routers.conversations.analytics_service"):
        resp = client.post(URL, json={"persona_slug": "socrates"})
    assert resp.json()["resumed"] is False


# ── The bucket ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hours,expected", [
    (0.25, "under_1h"),
    (0.99, "under_1h"),
    (1, "under_24h"),      # boundaries are exclusive-below: 1h is NOT under_1h
    (23.5, "under_24h"),
    (24, "under_72h"),
    (71, "under_72h"),
    (72, "under_7d"),
    (167, "under_7d"),
    (168, "under_14d"),
    (300, "under_14d"),
])
def test_the_gap_bucket_boundaries(client, hours, expected):
    conv = _make_conv(datetime.now(timezone.utc) - timedelta(hours=hours))

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, True))), \
         patch("routers.conversations.analytics_service") as analytics:
        client.post(URL, json={"persona_slug": "socrates", "resume": True})

    _, _, props = analytics.track.call_args_list[0][0]
    assert props["gap_bucket"] == expected


def test_a_row_with_no_last_message_at_reports_unknown(client):
    """Possible on old rows. A bucket that guesses is worse than one that admits
    it does not know — 'unknown' is visible in the dashboard, a wrong bucket is
    not."""
    conv = _make_conv(None)

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, True))), \
         patch("routers.conversations.analytics_service") as analytics:
        client.post(URL, json={"persona_slug": "socrates", "resume": True})

    _, _, props = analytics.track.call_args_list[0][0]
    assert props["gap_bucket"] == "unknown"


def test_a_naive_last_message_at_does_not_raise(client):
    """TD-76. A naive timestamp is read in the server's timezone; the helper
    treats it as UTC rather than crashing the open."""
    conv = _make_conv(datetime.utcnow() - timedelta(hours=3))

    with patch("routers.conversations.conversation_service.create_or_resume",
               AsyncMock(return_value=(conv, True))), \
         patch("routers.conversations.analytics_service") as analytics:
        resp = client.post(URL, json={"persona_slug": "socrates", "resume": True})

    assert resp.status_code == 201
    _, _, props = analytics.track.call_args_list[0][0]
    assert props["gap_bucket"] in {"under_1h", "under_24h", "under_72h", "under_7d", "under_14d"}
