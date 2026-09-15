"""Tests for the X-RateLimit-Reset header on the two weekly-limit 429s (A15b).

Council (1/source/week) and You-vs-You (n/week by tier) both returned a 429 with
Limit and Remaining but no Reset. The frontend falls back to `new Date()` when the
header is absent, so the paywall told the user their limit "resets now" — every
time. These pin the header that fixes it.

Scope is the 429 paths only. Council's success path also gained the header (see
routers/council.py) but is not covered here: it wraps a StreamingResponse around a
live LLM generator, and stubbing that costs more than the path is worth.

Patching weekly_remaining -> 0 makes each endpoint return before any LLM call.

Run: cd apps/api && pytest tests/routers/test_council_limits.py -v
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

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"

COUNCIL_URL         = "/api/v1/council"
SELF_COMPARISON_URL = "/api/v1/self-comparison"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = "user@example.com"
    u.is_admin = False          # admins bypass the limit entirely
    return u


def _assert_reset_header_is_sane(resp):
    """The four A15b assertions, shared by both endpoints.

    'At most 7 days ahead' is the real guard: the reset is the start of the NEXT
    week counted from a Monday-00:00-UTC boundary, so it is always strictly inside
    a 7-day horizon. A regression that reset a fixed +7d from `now` instead of from
    the week boundary would pass the future check and fail this one.
    """
    assert "X-RateLimit-Reset" in resp.headers, (
        "X-RateLimit-Reset missing — the paywall falls back to 'resets now'"
    )

    raw = resp.headers["X-RateLimit-Reset"]
    reset_at = datetime.fromisoformat(raw)      # raises if not ISO-8601
    assert reset_at.tzinfo is not None, f"reset must be tz-aware, got {raw!r}"

    now = datetime.now(timezone.utc)
    assert reset_at > now, f"reset {raw!r} is not in the future (now={now.isoformat()})"
    assert reset_at <= now + timedelta(days=7), (
        f"reset {raw!r} is more than 7 days ahead (now={now.isoformat()})"
    )


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

    yield tc

    app.dependency_overrides.clear()


# ── Council — 1 per source per week ───────────────────────────────────────────

def test_council_weekly_limit_429_sets_reset_header(client):
    with patch(
        "routers.council.council_service.weekly_remaining",
        AsyncMock(return_value=0),
    ):
        resp = client.post(COUNCIL_URL, json={"matter": "Should I take the job?"})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "council_weekly_limit"
    # The pre-existing headers are unchanged by A15b.
    assert resp.headers["X-RateLimit-Limit"] == "1"
    assert resp.headers["X-RateLimit-Remaining"] == "0"

    _assert_reset_header_is_sane(resp)


# ── You-vs-You — n per week by tier ───────────────────────────────────────────

def test_self_comparison_weekly_limit_429_sets_reset_header(client):
    with patch(
        "routers.self_comparison.self_comparison_service.weekly_remaining",
        AsyncMock(return_value=0),
    ):
        resp = client.post(SELF_COMPARISON_URL, json={"prompt": "Am I steadier than I was?"})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "weekly_limit"
    assert resp.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Limit" in resp.headers

    _assert_reset_header_is_sane(resp)


# ── Γ-1b — the funnel, and what a refusal does and does not emit ─────────────
#
# council_started used to fire BEFORE the 400 (matter_too_long) and this 429, so
# every refused attempt counted as a started council. The funnel it feeds is
# council_started -> council_completed, and a numerator padded with requests the
# server never attempted reads as a generation failure that is not happening.
#
# These pin the order. They live in this file rather than a new one because the
# fixture that makes a refusal reachable without an LLM is already here.

def test_a_rate_limited_council_emits_one_cap_hit_and_no_started(client):
    """The refusal is a cap event, not a start. Both halves asserted together:
    asserting only the absence of council_started would pass against a version
    that had simply deleted the event."""
    with patch(
        "routers.council.council_service.weekly_remaining",
        AsyncMock(return_value=0),
    ), patch("routers.council.analytics_service") as analytics:
        resp = client.post(COUNCIL_URL, json={"matter": "Should I take the job?"})

    assert resp.status_code == 429

    names = [c[0][0] for c in analytics.track.call_args_list]
    assert names == ["usage_cap_hit"], (
        f"a refused council must emit exactly one usage_cap_hit and nothing else; got {names}"
    )

    _, user_id, props = analytics.track.call_args_list[0][0]
    assert user_id == USER_ID
    assert props == {"tier": "pro", "cap_kind": "council", "path": "council"}


def test_an_over_long_matter_emits_nothing_at_all(client):
    """The other refusal path. No cap was hit — the request was malformed — so
    this one emits nothing, and must still not count as a started council."""
    with patch("routers.council.analytics_service") as analytics:
        resp = client.post(COUNCIL_URL, json={"matter": "x" * 601})

    assert resp.status_code == 400
    assert resp.json()["error_code"] == "matter_too_long"
    analytics.track.assert_not_called()


def test_an_empty_matter_emits_nothing_at_all(client):
    with patch("routers.council.analytics_service") as analytics:
        resp = client.post(COUNCIL_URL, json={"matter": "   "})

    assert resp.status_code == 400
    assert resp.json()["error_code"] == "empty_matter"
    analytics.track.assert_not_called()


def test_an_admin_is_not_rate_limited_and_emits_no_cap_hit(client):
    """Admins bypass weekly_remaining entirely, so they must emit no cap event —
    a cap series padded with people who were never capped is the same defect in
    the other direction."""
    user = client._auth_holder[0][0]
    user.is_admin = True

    with patch("routers.council.analytics_service") as analytics, \
         patch("routers.council.council_service.stream_council", MagicMock(return_value=iter([]))):
        resp = client.post(COUNCIL_URL, json={"matter": "Should I take the job?"})

    assert resp.status_code == 200
    names = [c[0][0] for c in analytics.track.call_args_list]
    assert "usage_cap_hit" not in names, f"an admin hit no cap; got {names}"
    assert names == ["council_started"]


@pytest.mark.parametrize("sent,expected", [
    ("direct", "direct"),
    ("mirror", "mirror"),
    ("chat",   "chat"),
    ("nudge",  "nudge"),      # the insight-card door; post-dates the schema comment
    ("made_up", "direct"),    # shape-valid, not a door we ship -> normalised
])
def test_council_started_sends_the_normalised_source(client, sent, expected):
    """The event now agrees with the rate limiter and the DB row, which both read
    the normalised local. It used to send `body.source` — whatever the client put
    in sessionStorage — while everything else in the request saw the checked value.
    """
    user = client._auth_holder[0][0]
    user.is_admin = True      # skip the limiter; this is about the property

    with patch("routers.council.analytics_service") as analytics, \
         patch("routers.council.council_service.stream_council", MagicMock(return_value=iter([]))):
        resp = client.post(COUNCIL_URL, json={"matter": "Should I take the job?", "source": sent})

    assert resp.status_code == 200
    _, _, props = analytics.track.call_args_list[0][0]
    assert props == {"source": expected}


@pytest.mark.parametrize("bad", ["Direct", "a b", "x" * 33, "chat!", ""])
def test_a_source_that_breaks_the_pattern_is_refused_at_the_edge(client, bad):
    """422 from pydantic, before any handler code. Unlike the letter's `src` query
    marker, this is a body field our own frontend fills from a fixed set of four
    writers — nothing external rewrites it — so a bound here costs no real request
    and stops an unbounded string from reaching the router at all.
    """
    with patch("routers.council.analytics_service") as analytics:
        resp = client.post(COUNCIL_URL, json={"matter": "Should I take the job?", "source": bad})

    assert resp.status_code == 422, f"source={bad!r} should be refused by the schema"
    analytics.track.assert_not_called()


# ── Γ-7-lite: the seed insight link ───────────────────────────────────────────
#
# Of the three rituals an insight card can open, the Council was the one that did
# not record its trigger — the door passed the insight's TEXT and never its id.
# 065 adds council_cases.insight_id; these pin what the ROUTER hands the service.
#
# OWNERSHIP IS THE POINT OF THE QUERY, and the foreign key would not do it. A
# UUID that exists is not a UUID that belongs to the caller: without the lookup,
# a client could hand up somebody else's insight id and the FK would accept it.

def _insight_lookup(client, *, found):
    """Make the router's ownership SELECT answer found / not-found."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = "insight-abc" if found else None

    async def fake_execute(_q):
        return result

    client._db[0].execute = fake_execute


def _start(client, body):
    with patch("routers.council.council_service.stream_council") as stream, \
         patch("routers.council.analytics_service"):
        stream.return_value = iter([])
        resp = client.post(COUNCIL_URL, json=body)
    return resp, stream


def test_an_owned_insight_id_is_passed_through(client):
    client._auth_holder[0][0].is_admin = True   # bypass the weekly limit query
    _insight_lookup(client, found=True)

    resp, stream = _start(client, {
        "matter": "Should I take the job?", "source": "nudge",
        "insight_id": "insight-abc",
    })

    assert resp.status_code == 200
    assert stream.call_args.kwargs["insight_id"] == "insight-abc"


def test_a_direct_council_stores_null(client):
    """The common case, and the reason the column is nullable: most councils have
    no insight behind them at all."""
    client._auth_holder[0][0].is_admin = True
    _insight_lookup(client, found=True)   # would resolve, but nothing asks it to

    resp, stream = _start(client, {"matter": "Should I take the job?"})

    assert resp.status_code == 200
    assert stream.call_args.kwargs["insight_id"] is None


def test_an_insight_belonging_to_someone_else_is_dropped_not_linked(client):
    """The ownership check, from the outside. The lookup is scoped to the caller,
    so a foreign id resolves to nothing and no link is written."""
    client._auth_holder[0][0].is_admin = True
    _insight_lookup(client, found=False)

    resp, stream = _start(client, {
        "matter": "Should I take the job?", "source": "nudge",
        "insight_id": "somebody-elses-insight",
    })

    assert resp.status_code == 200
    assert stream.call_args.kwargs["insight_id"] is None


def test_an_unrecognised_insight_id_does_not_refuse_the_council(client):
    """DELIBERATELY NOT A 404, unlike the counterview path.

    There the insight IS the subject — without it there is nothing to argue
    against, so refusing is right. Here the matter is already in hand and the link
    is only a record of where it came from. Refusing to convene would spend the
    person's one-council-per-week on an analytics annotation.
    """
    client._auth_holder[0][0].is_admin = True
    _insight_lookup(client, found=False)

    resp, _ = _start(client, {
        "matter": "Should I take the job?", "source": "nudge",
        "insight_id": "00000000-0000-0000-0000-000000000000",
    })

    assert resp.status_code == 200
