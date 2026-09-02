"""The fair-use cap at the routes, and the ordering it must not break.

THE ONE THAT MATTERS MOST is test_crisis_text_at_the_fair_use_cap_still_reaches
_the_service. #591 moved the safety gate ahead of the rate limit because a
person in crisis who had spent their allowance was being shown a paywall. This
PR adds a SECOND ceiling behind that gate, and the obvious way to get it wrong
is to check the new one first — which would restore the old defect for paying
users and pass every other test in this file.

Also pinned: the cap returns error_code "fair_use_limit" and NOT "rate_limited".
The web client turns rate_limited into setShowPaywall(), and a Pro subscriber
has nothing left to buy. The distinct code is what routes to a plain notice.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.rate_limit_service import PRO_DAILY_FAIR_USE_LIMIT, RateLimitResult

CONV_ID = "11111111-1111-1111-1111-111111111111"
URL = f"/api/v1/conversations/{CONV_ID}/messages"

RESET = datetime(2026, 9, 3, tzinfo=timezone.utc)
ALLOWED = RateLimitResult(allowed=True, remaining=-1, limit=-1, reset_at=RESET)
CAPPED = RateLimitResult(
    allowed=False, remaining=0, limit=PRO_DAILY_FAIR_USE_LIMIT, reset_at=RESET,
)

CRISIS_TEXTS = ["I want to kill myself", "θέλω να αυτοκτονήσω", "den antexo allo"]


def _conv(user_id):
    c = MagicMock()
    c.id = CONV_ID
    c.user_id = user_id
    c.persona_id = "22222222-2222-2222-2222-222222222222"
    c.active_persona_id = None
    c.ritual_id = None
    return c


def _persona():
    p = MagicMock()
    p.id = "22222222-2222-2222-2222-222222222222"
    p.slug = "marcus_aurelius"
    return p


def _session(conv, persona):
    db = AsyncMock()

    async def execute(stmt, *a, **kw):
        result = MagicMock()
        if "FROM conversations" in str(stmt):
            result.scalar_one_or_none.return_value = conv
        else:
            result.scalar_one.return_value = persona
            result.scalar_one_or_none.return_value = persona
        return result

    db.execute = AsyncMock(side_effect=execute)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _user(is_admin=False):
    u = MagicMock()
    u.id = str(uuid4())
    u.is_admin = is_admin
    return u


def _client(user, plan="pro"):
    from main import app
    from auth import get_user_plan_streaming
    app.dependency_overrides[get_user_plan_streaming] = lambda: (user, plan)
    return TestClient(app, raise_server_exceptions=False)


def _reset():
    from main import app
    app.dependency_overrides.clear()


# ── THE ORDERING TEST — the one this PR must not break ───────────────────────

@pytest.mark.parametrize("text", CRISIS_TEXTS)
def test_crisis_text_at_the_fair_use_cap_still_reaches_the_service(text):
    """A Pro user at 150/150 writes a crisis message. They get the crisis
    response, not a cap notice.

    Flip the cap check ahead of the safety gate and this is the only test that
    fails — which is exactly why it is here.
    """
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=ALLOWED)), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)) as cap, \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            stream.return_value = iter([b"data: {}\n\n"])
            res = client.post(URL, json={"content": text})

        assert res.status_code == 200, res.text
        assert "fair_use_limit" not in res.text
        # The cap was not even consulted for a crisis message.
        cap.assert_not_awaited()
        stream.assert_called_once()
    finally:
        _reset()


# ── The cap working ──────────────────────────────────────────────────────────

def test_an_ordinary_message_at_the_cap_is_refused():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=ALLOWED)), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)), \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            res = client.post(URL, json={"content": "what should I read next?"})

        assert res.status_code == 429, res.text
        assert res.json()["error_code"] == "fair_use_limit"
        assert res.headers["X-RateLimit-Limit"] == str(PRO_DAILY_FAIR_USE_LIMIT)
        assert res.headers["X-RateLimit-Reset"] == RESET.isoformat()
        stream.assert_not_called()
    finally:
        _reset()


def test_the_cap_never_returns_the_paywall_error_code():
    """`rate_limited` is what the client turns into setShowPaywall(). Showing a
    subscriber an upgrade prompt is the defect this whole design avoids."""
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=ALLOWED)), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)), \
             patch("routers.conversations.conversation_service.stream_response"):
            res = client.post(URL, json={"content": "an ordinary question"})
        assert "rate_limited" not in res.text
    finally:
        _reset()


def test_an_admin_is_not_capped():
    user = _user(is_admin=True)
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)) as cap, \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            stream.return_value = iter([b"data: {}\n\n"])
            res = client.post(URL, json={"content": "testing"})
        assert res.status_code == 200
        cap.assert_not_awaited()
    finally:
        _reset()


def test_analytics_fires_with_closed_enums_only():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=ALLOWED)), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)), \
             patch("routers.conversations.analytics_service") as analytics, \
             patch("routers.conversations.conversation_service.stream_response"):
            client.post(URL, json={"content": "the user's own words, which must not appear"})

        analytics.track.assert_called_once()
        event, uid, props = analytics.track.call_args.args
        assert event == "usage_cap_hit"
        assert props == {"tier": "pro", "cap_kind": "pro_fair_use", "path": "chat"}
        assert "the user's own words" not in str(props)
    finally:
        _reset()


def test_the_free_tier_path_is_unchanged():
    """A free user hits check_rate_limit and gets rate_limited, exactly as
    before — the fair-use cap returns allowed for them and changes nothing."""
    user = _user()
    client = _client(user, plan="free")
    exhausted = RateLimitResult(allowed=False, remaining=0, limit=5, reset_at=RESET)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session(_conv(user.id), _persona())), \
             patch("routers.conversations.get_user_tier", new=AsyncMock(return_value="free")), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=exhausted)), \
             patch("routers.conversations.conversation_service.stream_response"):
            res = client.post(URL, json={"content": "an ordinary question"})

        assert res.status_code == 429
        assert res.json()["error_code"] == "rate_limited"   # paywall path, unchanged
    finally:
        _reset()
