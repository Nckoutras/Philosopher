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
from datetime import datetime, timezone
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


def _make_subscription(plan="free", active=True):
    if not active:
        return None
    s = MagicMock()
    s.plan = plan
    s.status = "active"
    s.current_period_end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    return s


def _make_db(subscription=None):
    db = AsyncMock()
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = subscription
    db.execute = AsyncMock(return_value=sub_result)
    return db


def _get_client():
    from main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_share_screenshot_200_for_valid_saved_line():
    """Valid saved_line_id owned by auth user → 200 image/png."""
    user = _make_user()
    sub = _make_subscription("free")
    db = _make_db(sub)

    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         patch("auth.get_current_user", return_value=user), \
         patch("auth.get_current_user_plan", return_value=(user, "free")), \
         patch("db.session.get_db", return_value=db):

        client = _get_client()
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == FAKE_PNG


def test_share_screenshot_404_for_wrong_user():
    """Saved line not owned by requesting user → 404."""
    user = _make_user()
    sub = _make_subscription("free")
    db = _make_db(sub)

    with patch(
        "routers.share.generate_share_image",
        new=AsyncMock(side_effect=ValueError("Saved line not found")),
    ), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=True)), \
         patch("auth.get_current_user", return_value=user), \
         patch("auth.get_current_user_plan", return_value=(user, "free")), \
         patch("db.session.get_db", return_value=db):

        client = _get_client()
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 404


def test_share_screenshot_429_when_rate_limit_exceeded():
    """Free user who has exhausted limit → 429 + error_code=share_limit_reached."""
    user = _make_user()
    sub = _make_subscription("free")
    db = _make_db(sub)

    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)), \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)), \
         patch("auth.get_current_user", return_value=user), \
         patch("auth.get_current_user_plan", return_value=(user, "free")), \
         patch("db.session.get_db", return_value=db):

        client = _get_client()
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 429
    assert resp.json()["error_code"] == "share_limit_reached"


def test_share_screenshot_pro_user_bypasses_rate_limit():
    """Pro user: rate_limit check is never called, always 200."""
    user = _make_user()
    sub = _make_subscription("pro")
    db = _make_db(sub)

    with patch("routers.share.generate_share_image", new=AsyncMock(return_value=FAKE_PNG)) as mock_gen, \
         patch("routers.share.rate_limit_service.check_and_increment", new=AsyncMock(return_value=False)) as mock_rl, \
         patch("auth.get_current_user", return_value=user), \
         patch("auth.get_current_user_plan", return_value=(user, "pro")), \
         patch("db.session.get_db", return_value=db):

        client = _get_client()
        resp = client.post(ENDPOINT, json={"saved_line_id": SAVED_LINE_ID})

    assert resp.status_code == 200
    # Rate limit must NOT have been called for pro user
    mock_rl.assert_not_called()
