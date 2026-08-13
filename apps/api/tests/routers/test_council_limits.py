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
