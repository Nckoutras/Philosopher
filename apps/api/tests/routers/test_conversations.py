"""Tests for POST /api/v1/conversations/{id}/messages — PATH A rate limiting.

Verifies per-persona rate limit, ritual exemption, admin bypass, and
X-RateLimit-* header behavior on both 429 and 200 responses.

Run: cd apps/api && pytest tests/routers/test_conversations.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from models import Conversation, DailyUsage

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
PERSONA_ID = "bbbbbbbb-0000-0000-0000-000000000001"
SOCRATES_PERSONA_ID = "dddddddd-0000-0000-0000-000000000001"
CONV_ID = "cccccccc-0000-0000-0000-000000000001"
RITUAL_CONV_ID = "ffffffff-0000-0000-0000-000000000001"
RITUAL_ID = "eeeeeeee-0000-0000-0000-000000000001"

ENDPOINT = "/api/v1/conversations/{conv_id}/messages"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(is_admin=False):
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = is_admin
    u.full_name = "Test User"
    return u


def _make_persona(persona_id=PERSONA_ID):
    p = MagicMock()
    p.id = persona_id
    p.config = {}
    return p


def _make_conv(ritual_id=None, persona_id=PERSONA_ID, user_id=USER_ID, conv_id=CONV_ID):
    c = MagicMock(spec=Conversation)
    c.id = conv_id
    c.user_id = user_id
    c.persona_id = persona_id
    # No sticky guest by default ⇒ responder/quota coalesce to persona_id.
    c.active_persona_id = None
    c.deep_mode = False
    c.ritual_id = ritual_id
    return c


def _make_subscription(active=True, plan="pro"):
    if not active:
        return None
    s = MagicMock()
    # `plan` MUST be set explicitly. get_user_tier ends with
    #     if sub.plan not in ("pro", "premium"): return "free"
    # (added in #203, after this mock was written). An unset attribute on a
    # MagicMock is auto-created, is not in that tuple, and silently resolves the
    # tier to "free" — so a test asserting "pro is not rate limited" got a 429
    # with nothing raised anywhere. A mock feeding a branch condition has to
    # populate every field that condition reads.
    s.plan = plan
    s.status = "active"
    s.current_period_end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    return s


def _make_usage(count, persona_id=PERSONA_ID):
    return DailyUsage(
        user_id=USER_ID,
        persona_id=persona_id,
        usage_date=__import__("datetime").date.today(),
        message_count=count,
    )


def _make_db(conv, persona=None, subscription=None, usage=None):
    """Build mock AsyncSession for send_message.

    Dispatches on the STATEMENT, not on call order. It used to be an ordered
    side_effect list documenting "1. Conversation, 2. Persona, 3. Subscription,
    4. DailyUsage", which broke the moment the Pro fair-use cap added two count
    queries: Pro skips the DailyUsage read inside check_rate_limit, so the
    4th entry was consumed by a COUNT and returned a Mock where an int was
    needed. Order-based dispatch is what made 17 tests in this repo fail for
    months (TD-45); this answers by shape so a new query cannot shift the
    others.

    Unmatched statements return an empty result rather than raising, so a query
    a given test does not care about is simply absent instead of fatal.
    """
    if persona is None:
        persona = _make_persona()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    def _or_none(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        return r

    def _one(val):
        r = MagicMock()
        r.scalar_one.return_value = val
        return r

    def _count(val):
        r = MagicMock()
        r.scalar_one.return_value = val
        return r

    usage_count = usage.message_count if usage is not None else 0

    async def _execute(stmt, *a, **kw):
        text = str(stmt).lower()
        if "from conversations" in text:
            return _or_none(conv)
        if "from personas" in text:
            r = MagicMock()
            r.scalar_one.return_value = persona
            r.scalar_one_or_none.return_value = persona
            return r
        if "from subscriptions" in text:
            return _or_none(subscription)
        if "from daily_usage" in text:
            # A2 (2026-09-14): check_rate_limit now SUMS too — it used to
            # select the per-persona row. Both free and Pro caps are aggregates
            # over the same column, so the branch below serves both and the row
            # branch survives only for check_go_deeper_limit, which stays
            # per-persona.
            if "sum(" in text or "count(" in text:
                return _count(usage_count)
            return _or_none(usage)
        if "from counterviews" in text:
            return _count(0)
        return _or_none(None)

    db.execute = AsyncMock(side_effect=_execute)
    return db


async def _fake_stream(*args, **kwargs):
    yield 'data: {"type": "done"}\n\n'


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from main import app
    # §5 pool-leak fix: the send_message route now authenticates via the
    # no-pin get_user_plan_streaming dependency and runs its preflight inside
    # `async with AsyncSessionLocal()` rather than Depends(get_db). Override the
    # new dependency and patch the preflight session factory to the mock db.
    from auth import get_current_user_plan, get_user_plan_streaming
    from db.session import get_db

    db_holder = [None]
    auth_holder = [(_make_user(), "free")]

    async def override_get_db():
        yield db_holder[0]

    async def override_plan():
        return auth_holder[0]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_plan] = override_plan
    app.dependency_overrides[get_user_plan_streaming] = override_plan

    def _fake_session_factory():
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=db_holder[0])
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    session_patch = patch("routers.conversations.AsyncSessionLocal", _fake_session_factory)
    session_patch.start()

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    tc.test_auth = auth_holder  # avoid _auth which conflicts with HTTPX internals

    yield tc

    session_patch.stop()
    app.dependency_overrides.clear()


# ── Rate limit — free user ────────────────────────────────────────────────────

def test_free_user_tenth_message_allowed_with_remaining_0(client):
    """A2, 2026-09-14: 9 prior replies (across ANY personas) — the 10th is
    allowed and X-RateLimit-Remaining is 0. Was 4 prior / 5th allowed."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(9))
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Remaining"] == "0"
    assert resp.headers["X-RateLimit-Limit"] == "10"
    assert "X-RateLimit-Reset" in resp.headers


def test_free_user_eleventh_message_blocked_returns_429(client):
    """A2, 2026-09-14: 10 prior replies spend the day's budget — the 11th returns
    429 with the LLMErrorResponse body. Was 5 prior / 6th blocked."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(10))
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream) as mock_stream:
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 429
    body = resp.json()
    assert body["error_code"] == "rate_limited"
    assert len(body["persona_voice"]) > 0


def test_429_response_has_rate_limit_headers(client):
    """429 response includes X-RateLimit-Limit, Remaining (0), and Reset headers.

    A2, 2026-09-14: the advertised limit is now 10.
    """
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(10))
    client._db[0] = db

    resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 429
    assert resp.headers["X-RateLimit-Limit"] == "10"
    assert resp.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in resp.headers


def test_200_response_has_rate_limit_headers(client):
    """200 response includes X-RateLimit-* headers for free users."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=None)
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert "X-RateLimit-Reset" in resp.headers
    assert resp.headers["X-RateLimit-Limit"] == "10"
    # A2: 0 prior replies → remaining=10 before the call → 9 after
    assert resp.headers["X-RateLimit-Remaining"] == "9"


# ── A15: the rate-limit headers must be READABLE cross-origin ────────────────
#
# Setting them is not enough. Without expose_headers on the CORS middleware,
# Starlette never sends Access-Control-Expose-Headers, and a browser on a
# different origin (web app on Netlify, API on Render) can read only the seven
# CORS-safelisted response headers. lib/api.ts then falls back to '0' and
# new Date() — the paywall telling free users their limit resets NOW.
#
# These assert real middleware behaviour through the real app, not config shape:
# an Origin header is required, because CORSMiddleware passes non-CORS requests
# straight through without adding anything.

EXPOSED_RATE_LIMIT_HEADERS = (
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
)
ORIGIN = "https://philosopher.netlify.app"


def test_429_exposes_rate_limit_headers_cross_origin(client):
    """The 429 that drives the paywall must expose all three headers, or the
    modal renders a fabricated reset time."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(10))
    client._db[0] = db

    resp = client.post(
        ENDPOINT.format(conv_id=CONV_ID),
        json={"content": "Hello"},
        headers={"Origin": ORIGIN},
    )

    assert resp.status_code == 429
    exposed = resp.headers.get("access-control-expose-headers")
    assert exposed is not None, (
        "Access-Control-Expose-Headers missing — the browser cannot read any "
        "X-RateLimit-* header and the paywall falls back to 'resets now'"
    )
    for name in EXPOSED_RATE_LIMIT_HEADERS:
        assert name in exposed, f"{name} not exposed; got: {exposed!r}"


def test_200_exposes_rate_limit_headers_cross_origin(client):
    """The same must hold on the streaming 200, which carries the live
    remaining-count the client tracks between turns."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=None)
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(
            ENDPOINT.format(conv_id=CONV_ID),
            json={"content": "Hello"},
            headers={"Origin": ORIGIN},
        )

    assert resp.status_code == 200
    exposed = resp.headers.get("access-control-expose-headers")
    assert exposed is not None
    for name in EXPOSED_RATE_LIMIT_HEADERS:
        assert name in exposed, f"{name} not exposed; got: {exposed!r}"


def test_stream_response_not_called_on_429(client):
    """When rate limited, response is JSON (not streaming) — stream_response never called."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(10))
    client._db[0] = db

    resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 429
    assert resp.headers["content-type"].startswith("application/json")


# ── Rate limit — pro user ─────────────────────────────────────────────────────

def test_pro_user_not_rate_limited(client):
    """Pro user with any number of messages succeeds; rate limit is not enforced."""
    conv = _make_conv(ritual_id=None)
    sub = _make_subscription(active=True)
    # usage=_make_usage(100) to prove pro is unlimited even at high count
    db = _make_db(conv=conv, subscription=sub, usage=_make_usage(100))
    client.test_auth[0] = (_make_user(), "pro")
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200


# ── Admin bypass ──────────────────────────────────────────────────────────────

def test_admin_user_bypasses_rate_limit(client):
    """Admin user is never rate-limited, regardless of usage count."""
    conv = _make_conv(ritual_id=None)
    # DB only needs conv + persona; no subscription/usage queries made
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(100))
    client.test_auth[0] = (_make_user(is_admin=True), "free")
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200


def test_admin_response_has_no_rate_limit_headers(client):
    """Admin bypass means no X-RateLimit-* headers on the successful response."""
    conv = _make_conv(ritual_id=None)
    db = _make_db(conv=conv)
    client.test_auth[0] = (_make_user(is_admin=True), "free")
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers
    assert "X-RateLimit-Remaining" not in resp.headers


# ── Ritual exemption ──────────────────────────────────────────────────────────

def test_ritual_conversation_bypasses_rate_limit(client):
    """Ritual conversation (ritual_id != None) is exempt from rate limiting."""
    conv = _make_conv(ritual_id=RITUAL_ID)
    # DB only needs conv + persona; no subscription/usage queries made
    db = _make_db(conv=conv, subscription=None, usage=_make_usage(10))
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200


def test_ritual_response_has_no_rate_limit_headers(client):
    """Ritual bypass means no X-RateLimit-* headers on the successful response."""
    conv = _make_conv(ritual_id=RITUAL_ID)
    db = _make_db(conv=conv)
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers
    assert "X-RateLimit-Remaining" not in resp.headers


def test_blocked_on_regular_but_allowed_on_ritual(client):
    """Free user maxed out on a regular conv can still message in a ritual conv."""
    ritual_conv = _make_conv(ritual_id=RITUAL_ID, conv_id=RITUAL_CONV_ID)
    # Ritual conv: only 2 DB queries (conv + persona), no rate limit queries
    db = _make_db(conv=ritual_conv)
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(ENDPOINT.format(conv_id=RITUAL_CONV_ID), json={"content": "Hello"})

    assert resp.status_code == 200


# ── The budget is shared across personas (A2) ─────────────────────────────────

def test_switching_persona_does_not_refill_the_budget(client):
    """A2, 2026-09-14. THIS TEST INVERTED, and it is the point of the change.

    It was `test_per_persona_marcus_blocked_socrates_allowed`: Marcus at 5/5
    blocked while Socrates on the same account still had a full allowance. That
    was the rule, and it is the rule A2 removed — a user who had spent the day
    could refill simply by opening a different mind.

    Amended rather than deleted, at the ROUTER level rather than only in the
    service, because this is the behaviour a person actually experiences: hit the
    wall, switch mind, hit the wall again. Both halves are asserted so a
    reintroduced persona filter fails here and not only in the unit test.

    The usage row still carries a persona_id — daily_usage is still keyed that
    way — but the check sums the day, so which persona owns the row no longer
    changes the answer.
    """
    # Marcus: the day's 10 are spent.
    marcus_conv = _make_conv(ritual_id=None, persona_id=PERSONA_ID)
    db_marcus = _make_db(conv=marcus_conv, subscription=None, usage=_make_usage(10, PERSONA_ID))
    client._db[0] = db_marcus

    resp_marcus = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})
    assert resp_marcus.status_code == 429

    # Socrates: same account, same day, same spent budget — also refused.
    socrates_conv = _make_conv(ritual_id=None, persona_id=SOCRATES_PERSONA_ID, conv_id=RITUAL_CONV_ID)
    db_socrates = _make_db(
        conv=socrates_conv, subscription=None,
        usage=_make_usage(10, SOCRATES_PERSONA_ID),
    )
    client._db[0] = db_socrates

    resp_socrates = client.post(
        ENDPOINT.format(conv_id=RITUAL_CONV_ID), json={"content": "Hello"}
    )
    assert resp_socrates.status_code == 429


def test_a_second_persona_still_works_while_the_budget_lasts(client):
    """The other side of the same rule, so the test above cannot pass by the cap
    simply blocking everything. With 4 replies spent, a different mind answers
    normally — the budget is shared, not exhausted by switching."""
    socrates_conv = _make_conv(ritual_id=None, persona_id=SOCRATES_PERSONA_ID, conv_id=RITUAL_CONV_ID)
    db = _make_db(
        conv=socrates_conv, subscription=None,
        usage=_make_usage(4, SOCRATES_PERSONA_ID),
    )
    client._db[0] = db

    with patch("routers.conversations.conversation_service.stream_response", _fake_stream):
        resp = client.post(
            ENDPOINT.format(conv_id=RITUAL_CONV_ID), json={"content": "Hello"}
        )
    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Remaining"] == "5"


# ── Ownership ─────────────────────────────────────────────────────────────────

def test_conversation_not_found_returns_404(client):
    """Conversation not owned by user → 404."""
    db = _make_db(conv=None)
    client._db[0] = db

    resp = client.post(ENDPOINT.format(conv_id=CONV_ID), json={"content": "Hello"})
    assert resp.status_code == 404


# ── GET /conversations/{id} ────────────────────────────────────────────────────

def _make_full_conv(user_id=USER_ID, conv_id=CONV_ID):
    """Mock conv with persona eagerly attached for GET /conversations/{id}."""
    c = MagicMock(spec=Conversation)
    c.id = conv_id
    c.user_id = user_id
    c.persona_id = PERSONA_ID
    c.ritual_id = None
    c.title = "Test conversation"
    c.message_count = 0
    c.last_message_at = None
    c.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    c.source_persona_slug = None
    c.source_saved_line_id = None
    # No sticky guest ⇒ _conv_out coalesces to the home persona, origin == persona.
    c.active_persona_id = None
    c.active_persona = None
    c.deep_mode = False

    p = MagicMock()
    p.id = PERSONA_ID
    p.slug = "marcus-aurelius"
    p.name = "Marcus Aurelius"
    p.era = "2nd century AD"
    p.tradition = "Stoic"
    p.tier = "free"
    p.portrait_url = "/personas/marcus-aurelius.webp"
    c.persona = p

    return c


def _make_single_conv_db(conv):
    """Build mock AsyncSession for GET /conversations/{id}.

    Execute call order:
      1. select(Conversation) — ownership check → scalar_one_or_none
    _build_source_contents returns {} immediately (no source_saved_line_id).
    """
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = conv
    db.execute = AsyncMock(return_value=r)
    return db


@pytest.fixture
def get_conv_client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db_holder = [None]

    async def override_get_db():
        yield db_holder[0]

    async def override_user():
        return _make_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder

    yield tc

    app.dependency_overrides.clear()


def test_get_conversation_by_id_200(get_conv_client):
    """Owner fetches own conversation → 200 with ConversationOut body."""
    conv = _make_full_conv()
    get_conv_client._db[0] = _make_single_conv_db(conv)

    resp = get_conv_client.get(f"/api/v1/conversations/{CONV_ID}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == CONV_ID
    assert body["persona"]["slug"] == "marcus-aurelius"


def test_get_conversation_by_id_404(get_conv_client):
    """Non-existent or non-owned conversation → 404."""
    get_conv_client._db[0] = _make_single_conv_db(None)

    resp = get_conv_client.get(f"/api/v1/conversations/{CONV_ID}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conversation not found"
