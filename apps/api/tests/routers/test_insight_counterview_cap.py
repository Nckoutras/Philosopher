"""The Pro fair-use cap on the INSIGHT counterview door (TD-70), and its ordering.

POST /insights/{id}/counterview spends the same five persona generations the
direct door does, and check_fair_use_limit counts the rows it writes either way
— so before this PR the cap had, in its own docstring's words, "an uncapped door
beside it". This file pins the cap and, more importantly, the three orderings
that make it correct. Each of them is a way to pass the plain cap test and still
be wrong:

  DEDUP BEFORE QUOTA — a second tap on the same insight returns the row that
    already exists and generates nothing, so it must cost nothing. Check the cap
    first and re-reading your own counterview burns quota, which would make the
    ceiling depend on how often the page was opened.

  CRISIS BEFORE QUOTA — the #591 rule, which the direct door already keeps: a
    person in crisis who has spent their allowance is not answered with a quota.
    The same person reaches the same state through either door.

  FAIR-USE ONLY — the free daily cap counts source='direct' rows and its
    docstring says this path never consumes that allowance. A free user is
    bounded transitively instead (one counterview per insight; insights come
    from chat, which is capped).

NOT covered here: generation itself, the dedup's own semantics, and the safety
suppression inside the service. Those are test_counterview_orphan_insight.py's,
and this PR does not touch them.
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

from schemas import CounterviewOut
from services.rate_limit_service import PRO_DAILY_FAIR_USE_LIMIT, RateLimitResult

INSIGHT_ID = "33333333-3333-3333-3333-333333333333"
URL = f"/api/v1/insights/{INSIGHT_ID}/counterview"

RESET = datetime(2026, 9, 3, tzinfo=timezone.utc)
ALLOWED = RateLimitResult(
    allowed=True, remaining=10, limit=PRO_DAILY_FAIR_USE_LIMIT, reset_at=RESET,
)
CAPPED = RateLimitResult(
    allowed=False, remaining=0, limit=PRO_DAILY_FAIR_USE_LIMIT, reset_at=RESET,
)

CRISIS_TEXTS = ["I want to kill myself", "θέλω να αυτοκτονήσω", "den antexo allo"]


def _user(is_admin=False):
    u = MagicMock()
    u.id = str(uuid4())
    u.is_admin = is_admin
    return u


def _insight(content="I should never rely on anyone."):
    """A real-ish anchor. `content` is the only field the router reads, and it is
    what the safety gate sees — set explicitly rather than auto-mocked (C-06)."""
    i = MagicMock()
    i.id = INSIGHT_ID
    i.content = content
    return i


def _cv(status="generated"):
    """A persisted counterview as _serialize_counterview would render it. A real
    model, not a MagicMock: the response_model validates it, and a Mock would
    satisfy every field read while failing pydantic for reasons unrelated to the
    cap (C-06)."""
    return CounterviewOut(
        id="44444444-4444-4444-4444-444444444444",
        source="insight",
        anchor_text="I should never rely on anyone.",
        status=status,
        still_stands=None,
        title="Trust and its limits",
        responses=[],
        turns=[],
        rebuttals_remaining=0,
        is_saved=False,
    )


def _client(user):
    from main import app
    from auth import get_current_user
    from db.session import get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    return TestClient(app, raise_server_exceptions=False)


def _reset():
    from main import app
    app.dependency_overrides.clear()


def _patches(*, existing=None, fair_use=ALLOWED, insight=None, tier="pro"):
    """The router's collaborators. `existing` is the dedup answer — None means a
    first tap, a row means a second one."""
    return (
        patch("routers.memory.resolve_insight_anchor",
              new=AsyncMock(return_value=insight if insight is not None else _insight())),
        patch("routers.memory.find_counterview_for_insight",
              new=AsyncMock(return_value=existing)),
        patch("routers.memory.get_user_tier", new=AsyncMock(return_value=tier)),
        patch("routers.memory.check_fair_use_limit", new=AsyncMock(return_value=fair_use)),
        patch("routers.memory.generate_counterview", new=AsyncMock(return_value=MagicMock())),
        patch("routers.memory._serialize_counterview", new=AsyncMock(return_value=_cv())),
    )


# ── The cap itself ────────────────────────────────────────────────────────────

def test_a_first_tap_at_the_cap_is_refused_with_the_right_code():
    """The hole TD-70 names. Before this PR the request generated five persona
    verdicts and wrote a row the cap would then count, having never asked it."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED)
        with p[0], p[1], p[2], p[3], p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 429
        assert res.json() == {"error_code": "fair_use_limit"}
        # Refused BEFORE generation — a capped call must cost zero LLM.
        gen.assert_not_awaited()
    finally:
        _reset()


def test_the_refusal_carries_the_rate_limit_headers():
    """Same three headers the direct door sends, so one client handler reads both."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED)
        with p[0], p[1], p[2], p[3], p[4], p[5]:
            res = client.post(URL)

        assert res.headers["X-RateLimit-Limit"] == str(PRO_DAILY_FAIR_USE_LIMIT)
        assert res.headers["X-RateLimit-Remaining"] == "0"
        assert res.headers["X-RateLimit-Reset"] == RESET.isoformat()
    finally:
        _reset()


def test_the_cap_never_returns_the_paywall_error_code():
    """`rate_limited` is what the client turns into setShowPaywall(). This user is
    already a subscriber — the same defect #625 fixed on the direct door."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED)
        with p[0], p[1], p[2], p[3], p[4], p[5]:
            res = client.post(URL)

        assert res.json()["error_code"] != "rate_limited"
        assert res.json()["error_code"] != "daily_limit"
    finally:
        _reset()


def test_a_first_tap_under_the_cap_generates():
    """The ordinary path stays ordinary: the cap is consulted and passed."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=ALLOWED)
        with p[0], p[1], p[2], p[3] as check, p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 200
        check.assert_awaited_once()
        gen.assert_awaited_once()
    finally:
        _reset()


# ── DEDUP BEFORE QUOTA ────────────────────────────────────────────────────────

def test_a_second_tap_on_the_same_insight_never_consults_the_cap():
    """THE idempotence guarantee. The row already exists, so nothing is generated
    and nothing may be charged. The cap is SKIPPED, not checked-and-passed: a user
    re-reading their own counterview must not be refused on the day they are at
    the ceiling, and must not move the counter by opening the page twice."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(existing=MagicMock(), fair_use=CAPPED)
        with p[0], p[1], p[2] as tier, p[3] as check, p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 200
        check.assert_not_awaited()
        tier.assert_not_awaited()
        # Still served — generate_counterview returns the existing row via its dedup.
        gen.assert_awaited_once()
    finally:
        _reset()


def test_a_second_tap_is_not_even_safety_checked():
    """Corollary of the ordering: the dedup short-circuits ahead of the safety gate
    too, so re-reading an existing counterview costs nothing at all."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(existing=MagicMock())
        with p[0], p[1], p[2], p[3], p[4], p[5], \
             patch("routers.memory.safety_service.check_input", new=AsyncMock()) as safety:
            res = client.post(URL)

        assert res.status_code == 200
        safety.assert_not_awaited()
    finally:
        _reset()


# ── CRISIS BEFORE QUOTA ───────────────────────────────────────────────────────

@pytest.mark.parametrize("text", CRISIS_TEXTS)
def test_crisis_content_at_the_cap_still_reaches_the_service(text):
    """#591's rule, kept on this door too. A Pro user at the ceiling whose insight
    carries crisis content gets the crisis response, not a 429. Checking the cap
    first would restore the old defect and pass every other test in this file."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED, insight=_insight(text))
        with p[0], p[1], p[2], p[3], p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 200
        gen.assert_awaited_once()
    finally:
        _reset()


def test_an_admin_is_not_capped():
    """Matches the direct door's `not user.is_admin` exemption exactly."""
    user = _user(is_admin=True)
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED)
        with p[0], p[1], p[2], p[3] as check, p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 200
        check.assert_not_awaited()
        gen.assert_awaited_once()
    finally:
        _reset()


def test_the_safety_gate_sees_the_insight_content():
    """The anchor the router checks is the insight's own text — the one layer the
    router can see. The service's conversation-level check still runs behind it."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(insight=_insight("a very specific anchor"))
        with p[0], p[1], p[2], p[3], p[4], p[5], \
             patch("routers.memory.safety_service.check_input", new=AsyncMock()) as safety:
            safety.return_value.should_suppress_persona = False
            client.post(URL)

        assert safety.await_args.args[0] == "a very specific anchor"
    finally:
        _reset()


# ── FAIR-USE ONLY ─────────────────────────────────────────────────────────────

def test_the_free_daily_counterview_cap_is_not_applied_here():
    """check_counterview_limit counts source='direct' rows and its docstring states
    this path never consumes that allowance. Applying it here would change a cap's
    meaning, not just its reach — and break its own test."""
    import routers.memory as memory_router_module

    assert not hasattr(memory_router_module, "check_counterview_limit")


def test_a_free_user_is_not_refused_by_the_fair_use_cap():
    """check_fair_use_limit returns allowed unconditionally below Pro, so the free
    tier reaches generation exactly as it did before this PR. The free user's bound
    on this door is transitive — one counterview per insight, and insights come
    from chat, which check_rate_limit caps."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=ALLOWED, tier="free")
        with p[0], p[1], p[2], p[3], p[4] as gen, p[5]:
            res = client.post(URL)

        assert res.status_code == 200
        gen.assert_awaited_once()
    finally:
        _reset()


# ── Analytics ─────────────────────────────────────────────────────────────────

def test_analytics_names_this_door_and_not_the_direct_one():
    """'insight_counterview', not 'counterview'. The two doors carry different cap
    semantics and different intent, and one shared value would make the series
    unable to answer which door hit the ceiling — the question that found TD-70."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=CAPPED)
        with p[0], p[1], p[2], p[3], p[4], p[5], \
             patch("routers.memory.analytics_service") as analytics:
            client.post(URL)

        analytics.track.assert_called_once()
        event, uid, props = analytics.track.call_args.args
        assert event == "usage_cap_hit"
        assert props == {
            "tier": "pro",
            "cap_kind": "pro_fair_use",
            "path": "insight_counterview",
        }
    finally:
        _reset()


def test_analytics_carries_no_user_text():
    """A cap event describes the refusal, not the request (constants.py:138-141)."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(
            fair_use=CAPPED,
            insight=_insight("the user's own words, which must not appear"),
        )
        with p[0], p[1], p[2], p[3], p[4], p[5], \
             patch("routers.memory.analytics_service") as analytics:
            client.post(URL)

        _, _, props = analytics.track.call_args.args
        assert "the user's own words" not in str(props)
    finally:
        _reset()


def test_no_analytics_when_nothing_is_refused():
    """usage_cap_hit means a refusal happened. An allowed call files nothing."""
    user = _user()
    client = _client(user)
    try:
        p = _patches(fair_use=ALLOWED)
        with p[0], p[1], p[2], p[3], p[4], p[5], \
             patch("routers.memory.analytics_service") as analytics:
            client.post(URL)

        analytics.track.assert_not_called()
    finally:
        _reset()


# ── The 404, which must still come first ──────────────────────────────────────

def test_an_insight_that_is_not_yours_404s_before_any_cap_is_read():
    """Ownership is settled before anything else is read or refused. A 429 for
    somebody else's insight id would confirm that the id exists."""
    user = _user()
    client = _client(user)
    try:
        with patch("routers.memory.resolve_insight_anchor",
                   new=AsyncMock(side_effect=ValueError("counterview anchor not found"))), \
             patch("routers.memory.find_counterview_for_insight", new=AsyncMock()) as dedup, \
             patch("routers.memory.check_fair_use_limit",
                   new=AsyncMock(return_value=CAPPED)) as check:
            res = client.post(URL)

        assert res.status_code == 404
        dedup.assert_not_awaited()
        check.assert_not_awaited()
    finally:
        _reset()
