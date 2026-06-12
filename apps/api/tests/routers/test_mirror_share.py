"""Tests for POST /api/v1/mirrors/{mirror_id}/share.

Mirrors the TestClient + patch pattern in test_share.py. The mirror share
endpoint reuses the same free-tier counter (share_screenshot:{user_id}) as the
line and council share endpoints.

Run: cd apps/api && pytest tests/routers/test_mirror_share.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
MIRROR_ID = "22222222-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/mirrors/{MIRROR_ID}/share"
FAKE_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100


def _make_user(is_admin=False):
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = is_admin
    return u


@contextmanager
def _client_with_plan(plan):
    """TestClient with the auth + db FastAPI deps overridden (patch() can't
    replace an already-resolved Depends, so use dependency_overrides)."""
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


def test_mirror_share_200_for_valid_mirror():
    """Valid mirror owned by auth user → 200 image/png."""
    with patch("routers.mirrors.generate_mirror_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.mirrors.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG


def test_mirror_share_404_for_missing_or_unowned_mirror():
    """Mirror not found / not owned → 404."""
    with patch(
        "routers.mirrors.generate_mirror_share_image",
        new=AsyncMock(side_effect=ValueError("Mirror not found")),
    ), \
         patch("routers.mirrors.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={})

    assert resp.status_code == 404


def test_mirror_share_429_when_rate_limit_exceeded():
    """Free user who has exhausted the shared share counter → 429."""
    with patch("routers.mirrors.generate_mirror_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.mirrors.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)), \
         _client_with_plan("free") as client:
        resp = client.post(ENDPOINT, json={})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "share_limit_reached"


def test_mirror_share_pro_user_bypasses_rate_limit():
    """Pro user: the shared counter is never touched, always 200."""
    with patch("routers.mirrors.generate_mirror_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.mirrors.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)) as mock_rl, \
         _client_with_plan("pro") as client:
        resp = client.post(ENDPOINT, json={})

    assert resp.status_code == 200
    mock_rl.assert_not_called()
