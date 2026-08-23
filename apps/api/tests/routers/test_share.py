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

def test_share_screenshot_200_for_valid_saved_line():
    """Valid saved_line_id owned by auth user → 200 image/png."""
    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG


def test_share_screenshot_404_for_wrong_user():
    """Saved line not owned by requesting user → 404."""
    with patch(
        "routers.share.generate_share_image",
        new=AsyncMock(side_effect=ValueError("Saved line not found")),
    ), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 404


def test_share_screenshot_429_when_rate_limit_exceeded():
    """Free user who has exhausted limit → 429 + error_code=share_limit_reached."""
    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "share_limit_reached"


def test_share_screenshot_pro_user_bypasses_rate_limit():
    """Pro user: rate_limit check is never called, always 200."""
    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)) as mock_rl, \
         _client_with_plan("pro") as client:
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 200
    # Rate limit must NOT have been called for pro user
    mock_rl.assert_not_called()
