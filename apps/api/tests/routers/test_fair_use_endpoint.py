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

from services.rate_limit_service import (
    PRO_DAILY_FAIR_USE_LIMIT, PRO_MONTHLY_FAIR_USE_LIMIT, RateLimitResult,
)

CONV_ID = "11111111-1111-1111-1111-111111111111"
URL = f"/api/v1/conversations/{CONV_ID}/messages"

RESET = datetime(2026, 9, 3, tzinfo=timezone.utc)
ALLOWED = RateLimitResult(allowed=True, remaining=-1, limit=-1, reset_at=RESET)
CAPPED = RateLimitResult(
    allowed=False, remaining=0, limit=PRO_DAILY_FAIR_USE_LIMIT, reset_at=RESET,
)

CRISIS_TEXTS = ["I want to kill myself", "θέλω να αυτοκτονήσω", "den antexo allo"]


def _assert_cap_consulted_only_for_tier_b(text, cap, stream):
    """SAFETY-002 changed WHEN the cap is consulted, not the outcome. Tier A still
    skips it unconsulted. A Tier-B message consults it first, because a RELEASED
    Tier-B message must meet it; at the cap it is judged in the router, and a judge
    failure (the kill switch is off in tests) is fail-closed, so the crisis path
    runs and fair_use_limit is never returned."""
    import asyncio
    from services import safety_gate
    from services.safety_service import safety_service as real_safety
    level = safety_gate.lexicon_level(text, asyncio.run(real_safety.check_input(text)))
    if level == "A":
        cap.assert_not_awaited()
    else:
        cap.assert_awaited_once()
        assert stream.call_args.kwargs["prejudged"].failed is True


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
        _assert_cap_consulted_only_for_tier_b(text, cap, stream)
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


# ── The monthly ceiling (founder ruling 2026-09-24) ──────────────────────────
# Same error_code, same exemptions — only the window and the wording differ.
# The client picks the monthly sentence from `period`; a new error_code would
# have fallen through useStream's else-branch to the PaywallModal.

MONTH_RESET = datetime(2026, 10, 1, tzinfo=timezone.utc)
CAPPED_MONTH = RateLimitResult(
    allowed=False, remaining=0, limit=PRO_MONTHLY_FAIR_USE_LIMIT,
    reset_at=MONTH_RESET, period="month",
)


def _post_at(cap_result, text, user, analytics=None):
    client = _client(user)
    with patch("routers.conversations.AsyncSessionLocal",
               return_value=_session(_conv(user.id), _persona())), \
         patch("routers.conversations.rate_limit_service.check_rate_limit",
               new=AsyncMock(return_value=ALLOWED)), \
         patch("routers.conversations.rate_limit_service.check_fair_use_limit",
               new=AsyncMock(return_value=cap_result)) as cap, \
         patch("routers.conversations.analytics_service", analytics or MagicMock()), \
         patch("routers.conversations.conversation_service.stream_response") as stream:
        stream.return_value = iter([b"data: {}\n\n"])
        res = client.post(URL, json={"content": text})
    return res, cap, stream


@pytest.mark.parametrize("text", CRISIS_TEXTS)
def test_crisis_text_at_the_monthly_cap_still_reaches_the_service(text):
    """400/400 is no different from 150/150: a crisis message is never answered
    with a quota, and the cap is not even consulted."""
    user = _user()
    try:
        res, cap, stream = _post_at(CAPPED_MONTH, text, user)
        assert res.status_code == 200, res.text
        assert "fair_use_limit" not in res.text
        _assert_cap_consulted_only_for_tier_b(text, cap, stream)
        stream.assert_called_once()
    finally:
        _reset()


def test_an_admin_is_not_capped_monthly_either():
    user = _user(is_admin=True)
    try:
        res, cap, stream = _post_at(CAPPED_MONTH, "testing", user)
        assert res.status_code == 200
        cap.assert_not_awaited()
    finally:
        _reset()


def test_the_monthly_refusal_names_its_window_and_never_sells():
    user = _user()
    try:
        res, _, stream = _post_at(CAPPED_MONTH, "an ordinary question", user)
        assert res.status_code == 429, res.text
        assert res.json() == {"error_code": "fair_use_limit", "period": "month"}
        assert "rate_limited" not in res.text
        assert res.headers["X-RateLimit-Limit"] == str(PRO_MONTHLY_FAIR_USE_LIMIT)
        assert res.headers["X-RateLimit-Reset"] == MONTH_RESET.isoformat()
        stream.assert_not_called()
    finally:
        _reset()


def test_the_daily_refusal_says_day():
    user = _user()
    try:
        res, _, _ = _post_at(CAPPED, "an ordinary question", user)
        assert res.json() == {"error_code": "fair_use_limit", "period": "day"}
    finally:
        _reset()


def test_the_monthly_refusal_has_its_own_cap_kind():
    """Separate from pro_fair_use so the dashboard can tell the ceiling that
    bounds cost from the one that bounds a single day."""
    user = _user()
    analytics = MagicMock()
    try:
        _post_at(CAPPED_MONTH, "the user's own words", user, analytics=analytics)
        event, _, props = analytics.track.call_args.args
        assert event == "usage_cap_hit"
        assert props == {"tier": "pro", "cap_kind": "pro_fair_use_monthly", "path": "chat"}
    finally:
        _reset()


# ── SAFETY-002: a Pro user at the fair-use cap, with a Tier-B message ─────────
#
# The over-limit rule, on the second limit. Released -> the normal fair_use_limit,
# no persona reply, no allowance consumed, the row written by the router.
# INTENT -> the crisis path, the verdict handed to the service.

from services.safety_judge import JudgeVerdict

RELEASABLE = "What did the Stoics think about suicide as a rational choice?"   # B:HIGH, no keys


def _verdict(v):
    return JudgeVerdict(verdict=v, failed=False, fail_kind=None,
                        model="claude-haiku-4-5-20251001", latency_ms=900,
                        input_tokens=1200, output_tokens=30)


def _post_at_the_cap(verdict):
    user = _user()
    client = _client(user)
    session = _session(_conv(user.id), _persona())
    try:
        with patch("routers.conversations.AsyncSessionLocal", return_value=session), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=ALLOWED)), \
             patch("routers.conversations.rate_limit_service.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)), \
             patch("routers.conversations.conversation_service.stream_response") as stream, \
             patch("routers.conversations.log_safety_event", new=AsyncMock()) as log, \
             patch("services.safety_judge.judge", new=AsyncMock(return_value=verdict)):
            stream.return_value = iter([b"data: {}\n\n"])
            res = client.post(URL, json={"content": RELEASABLE})
        return res, stream, log, session.__aenter__.return_value
    finally:
        _reset()


def test_a_released_tier_b_message_at_the_pro_cap_gets_fair_use_limit():
    res, stream, log, db = _post_at_the_cap(_verdict("DISCUSSING"))

    assert res.status_code == 429, res.text
    assert res.json()["error_code"] == "fair_use_limit"
    stream.assert_not_called()
    log.assert_awaited_once()
    assert log.await_args.kwargs["action_taken"] == "released"
    db.commit.assert_awaited()


def test_intent_at_the_pro_cap_gets_the_crisis_path():
    res, stream, log, _ = _post_at_the_cap(_verdict("INTENT"))

    assert res.status_code == 200, res.text
    assert "fair_use_limit" not in res.text
    assert stream.call_args.kwargs["prejudged"].verdict == "INTENT"
    log.assert_not_awaited()
