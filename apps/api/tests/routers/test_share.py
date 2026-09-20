"""Tests for POST /api/v1/share/screenshot.

Follows the same TestClient + patch pattern as test_conversations.py.

Run: cd apps/api && pytest tests/routers/test_share.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from schemas import ShareSnapshot

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
SAVED_LINE_ID = "11111111-0000-0000-0000-000000000001"
ENDPOINT = "/api/v1/share/screenshot"
FAKE_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100


def _make_user(is_admin=False):
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = is_admin
    u.full_name = "Test User"
    return u


@contextmanager
def _client_with_plan(plan):
    """TestClient with the auth + db FastAPI deps overridden.

    patch() CANNOT replace an already-resolved Depends: FastAPI builds the
    dependency tree at route registration, so patching `auth.get_current_user`
    afterwards leaves the real dependency in place. These four tests did exactly
    that and every one of them got `403 {'detail': 'Not authenticated'}` — the
    real authenticator running against no credentials. Nothing raised; the
    assertions simply compared 403 against the status they wanted.

    dependency_overrides is the supported mechanism, and is what the sibling
    test_mirror_share.py (same endpoint shape, green throughout) already used.

    The subscription/db mocks this file used to build are gone: the route reads
    `plan` straight off get_current_user_plan and never calls get_user_tier, so
    the tier was never coming from the database on this path.
    """
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    user = _make_user()
    app.dependency_overrides[get_current_user_plan] = lambda: (user, plan)
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_current_user_plan, None)
        app.dependency_overrides.pop(get_db, None)


# ── Tests ─────────────────────────────────────────────────────────────────────
#
# WHAT PR-1 CHANGED UNDER THESE TESTS, since all four needed rewriting and only
# one of the four was a harness break:
#
#   1. THE LIMITER MOVED. It used to live in this router and was patched at
#      `routers.share.rate_limit_service`. It now lives in share_service,
#      which every one of the six kinds routes through. Patching the old path
#      raises ModuleNotFoundError — loudly, which is the good case.
#   2. THE ERROR CODE SPLIT. `share_limit_reached` became
#      `share_rate_limited_daily` and `share_rate_limited_burst`, because the
#      client shows a different sentence for each and a single code gave it
#      nothing to choose with.
#   3. THE PRO BYPASS IS GONE. Pro and premium used to skip the limit entirely.
#      20/day now applies to every tier — see the note on the test below, which
#      asserts the NEW behaviour precisely because it is a deliberate reversal.
#   4. A THIRD OUTCOME EXISTS. The limiter being unreachable is now 503
#      `share_unavailable` rather than an uncaught 500.
#
# `build_snapshot` is patched rather than left to the mocked session. A bare
# AsyncMock db hands back Mock objects that pydantic rejects deep inside the
# builder, so the failure would look like a snapshot bug in a test about routing
# (C-06). The builders have their own tests, against real rows.

_SNAPSHOT = ShareSnapshot(
    artifact_type="line", headline="A line worth keeping.",
    attribution="Marcus Aurelius, in conversation",
)


def _patches(*, limiter, generator=None):
    """The three things every test here needs to pin."""
    gen = generator if generator is not None else AsyncMock(return_value=FAKE_PNG)
    return (
        patch("routers.share.generate_share_image", new=gen),
        patch("services.share_service.build_snapshot", new=AsyncMock(return_value=_SNAPSHOT)),
        patch("services.share_service.rate_limit_service.check_and_increment", new=limiter),
    )


def test_share_screenshot_200_and_the_card_carries_the_share_link():
    """A share is minted and its link is handed back with the PNG."""
    p1, p2, p3 = _patches(limiter=AsyncMock(return_value=True))
    with p1, p2, p3, _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG
    # The whole point of PR-1: the response identifies the share it just created.
    assert len(resp.headers["X-Share-Id"]) == 22
    assert resp.headers["X-Share-Url"].endswith("/s/" + resp.headers["X-Share-Id"])


def test_share_screenshot_404_when_the_artifact_is_not_the_users():
    """Ownership is checked in the SNAPSHOT now, not only in the generator.

    That is the stricter of the two and it runs first, so a share row can never
    be minted for something whose card would refuse to render.
    """
    p1, _p2, p3 = _patches(limiter=AsyncMock(return_value=True))
    with p1,          patch("services.share_service.build_snapshot",
               new=AsyncMock(side_effect=ValueError("not found"))),          p3, _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 404


def test_share_screenshot_429_burst_carries_its_own_error_code():
    """First call is the burst window, so a single False lands on burst."""
    p1, p2, p3 = _patches(limiter=AsyncMock(return_value=False))
    with p1, p2, p3, _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "share_rate_limited_burst"


def test_share_screenshot_429_daily_carries_its_own_error_code():
    """Burst passes, daily does not — the two codes must not be interchangeable.

    The order matters and is asserted here rather than assumed: burst is checked
    and incremented first, so [True, False] is 'within the minute, over the day'.
    """
    p1, p2, p3 = _patches(limiter=AsyncMock(side_effect=[True, False]))
    with p1, p2, p3, _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "share_rate_limited_daily"


def test_share_screenshot_503_when_the_limiter_is_unreachable():
    """Fail CLOSED on creation. Redis down means no share is minted.

    The public landing route makes the opposite choice on purpose; that
    asymmetry is tested in test_public_share.py.
    """
    p1, p2, p3 = _patches(limiter=AsyncMock(side_effect=RuntimeError("redis down")))
    with p1, p2, p3, _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "share_unavailable"


def test_share_screenshot_pro_is_rate_limited_too():
    """THE PRO BYPASS IS GONE, AND THAT IS THE ASSERTION.

    This test used to be `pro_user_bypasses_rate_limit` and asserted the
    limiter was never called for a paid tier. A share loop where a paid account
    can mint unlimited public links is an abuse surface rather than a benefit,
    and 20 a day is well past what a person shares. Inverted rather than
    deleted: the reversal is deliberate, so something should fail if it is
    quietly undone.
    """
    limiter = AsyncMock(return_value=False)
    p1, p2, p3 = _patches(limiter=limiter)
    with p1, p2, p3, _client_with_plan("pro") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 429
    assert limiter.called, "pro must be metered like every other tier"
