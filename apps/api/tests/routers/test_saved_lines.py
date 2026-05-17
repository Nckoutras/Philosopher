"""Tests for POST/GET/DELETE /api/v1/saved-lines.

Uses FastAPI TestClient with dependency overrides for DB and auth.
Service methods patched at the router module level.

Run: cd apps/api && pytest tests/routers/test_saved_lines.py -v
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

from services.saved_lines_service import (
    FreeSavesLimitError,
    SavedLineNotFoundError,
    MessageNotFoundError,
    MessageRoleError,
    SavedLineAlreadyExistsError,
    FREE_SAVE_LIMIT,
)

USER_ID    = "aaaaaaaa-0000-0000-0000-000000000001"
MSG_ID     = "bbbbbbbb-0000-0000-0000-000000000001"
PERSONA_ID = "dddddddd-0000-0000-0000-000000000001"
LINE_ID    = "eeeeeeee-0000-0000-0000-000000000001"
CONV_ID    = "cccccccc-0000-0000-0000-000000000001"

POST_URL   = "/api/v1/saved-lines"
GET_URL    = "/api/v1/saved-lines"
DELETE_URL = f"/api/v1/saved-lines/{LINE_ID}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _make_saved_line():
    sl = MagicMock()
    sl.id = LINE_ID
    sl.user_id = USER_ID
    sl.message_id = MSG_ID
    sl.persona_id = PERSONA_ID
    sl.source_type = "manual_save"
    sl.saved_at = datetime.now(timezone.utc)
    sl.deleted_at = None
    return sl


def _make_list_item():
    return {
        "id": LINE_ID,
        "message_id": MSG_ID,
        "persona_id": PERSONA_ID,
        "source_type": "manual_save",
        "saved_at": datetime.now(timezone.utc),
        "message_content": "You have power over your mind.",
        "conversation_id": CONV_ID,
        "persona_slug": "marcus-aurelius",
        "persona_display_name": "Marcus Aurelius",
    }


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db_holder = [AsyncMock()]
    user_holder = [_make_user()]

    async def override_db():
        yield db_holder[0]

    async def override_user():
        return user_holder[0]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    tc._user = user_holder

    yield tc

    app.dependency_overrides.clear()


# ── POST /api/v1/saved-lines ─────────────────────────────────────────────────

def test_post_201_success(client):
    saved_line = _make_saved_line()
    with patch("routers.saved_lines.saved_lines_service.create", AsyncMock(return_value=saved_line)):
        resp = client.post(POST_URL, json={"message_id": MSG_ID})

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == LINE_ID
    assert body["user_id"] == USER_ID
    assert body["message_id"] == MSG_ID
    assert body["persona_id"] == PERSONA_ID
    assert body["source_type"] == "manual_save"
    assert "saved_at" in body


def test_post_404_message_not_found(client):
    with patch("routers.saved_lines.saved_lines_service.create", AsyncMock(side_effect=MessageNotFoundError())):
        resp = client.post(POST_URL, json={"message_id": MSG_ID})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Message not found"


def test_post_400_user_role_message_rejected(client):
    with patch("routers.saved_lines.saved_lines_service.create", AsyncMock(side_effect=MessageRoleError())):
        resp = client.post(POST_URL, json={"message_id": MSG_ID})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only persona replies can be saved"


def test_post_409_already_saved(client):
    with patch("routers.saved_lines.saved_lines_service.create", AsyncMock(side_effect=SavedLineAlreadyExistsError())):
        resp = client.post(POST_URL, json={"message_id": MSG_ID})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Already saved"


def test_post_402_free_tier_limit_reached(client):
    err = FreeSavesLimitError(limit=FREE_SAVE_LIMIT, current_count=FREE_SAVE_LIMIT)
    with patch("routers.saved_lines.saved_lines_service.create", AsyncMock(side_effect=err)):
        resp = client.post(POST_URL, json={"message_id": MSG_ID})

    assert resp.status_code == 402
    body = resp.json()
    assert body["detail"] == "Free tier save limit reached"
    assert body["code"] == "free_saves_limit"
    assert body["limit"] == FREE_SAVE_LIMIT
    assert body["current_count"] == FREE_SAVE_LIMIT


def test_post_requires_auth(client):
    from main import app
    from auth import get_current_user
    # Remove auth override to trigger real auth dependency (no token → 403/401)
    del app.dependency_overrides[get_current_user]
    try:
        resp = client.post(POST_URL, json={"message_id": MSG_ID})
        assert resp.status_code in (401, 403)
    finally:
        # Re-add override so fixture teardown is clean
        async def override_user():
            return _make_user()
        app.dependency_overrides[get_current_user] = override_user


# ── GET /api/v1/saved-lines ───────────────────────────────────────────────────

def test_get_200_returns_items_free_user(client):
    items = [_make_list_item()]
    with (
        patch("routers.saved_lines.saved_lines_service.list_for_user", AsyncMock(return_value=items)),
        patch("routers.saved_lines.get_user_tier", AsyncMock(return_value="free")),
    ):
        resp = client.get(GET_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_count"] == 1
    assert body["free_tier_limit"] == FREE_SAVE_LIMIT
    assert len(body["items"]) == 1
    assert body["items"][0]["persona_slug"] == "marcus-aurelius"
    assert body["items"][0]["message_content"] == "You have power over your mind."


def test_get_200_empty_list(client):
    with (
        patch("routers.saved_lines.saved_lines_service.list_for_user", AsyncMock(return_value=[])),
        patch("routers.saved_lines.get_user_tier", AsyncMock(return_value="free")),
    ):
        resp = client.get(GET_URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total_count"] == 0
    assert body["free_tier_limit"] == FREE_SAVE_LIMIT


def test_get_pro_user_returns_null_limit(client):
    with (
        patch("routers.saved_lines.saved_lines_service.list_for_user", AsyncMock(return_value=[])),
        patch("routers.saved_lines.get_user_tier", AsyncMock(return_value="pro")),
    ):
        resp = client.get(GET_URL)

    assert resp.status_code == 200
    assert resp.json()["free_tier_limit"] is None


def test_get_items_ordered_newest_first(client):
    t_old = datetime(2026, 5, 1, tzinfo=timezone.utc)
    t_new = datetime(2026, 5, 17, tzinfo=timezone.utc)
    items = [
        {**_make_list_item(), "id": "new-id", "saved_at": t_new},
        {**_make_list_item(), "id": "old-id", "saved_at": t_old},
    ]
    with (
        patch("routers.saved_lines.saved_lines_service.list_for_user", AsyncMock(return_value=items)),
        patch("routers.saved_lines.get_user_tier", AsyncMock(return_value="free")),
    ):
        resp = client.get(GET_URL)

    body = resp.json()
    assert body["items"][0]["id"] == "new-id"
    assert body["items"][1]["id"] == "old-id"


# ── DELETE /api/v1/saved-lines/{id} ──────────────────────────────────────────

def test_delete_204_success(client):
    with patch("routers.saved_lines.saved_lines_service.delete", AsyncMock(return_value=None)):
        resp = client.delete(DELETE_URL)

    assert resp.status_code == 204
    assert resp.content == b""


def test_delete_404_not_found(client):
    with patch("routers.saved_lines.saved_lines_service.delete", AsyncMock(side_effect=SavedLineNotFoundError())):
        resp = client.delete(DELETE_URL)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Saved line not found"


def test_delete_already_soft_deleted_returns_404(client):
    # Service raises SavedLineNotFoundError when row has deleted_at set
    with patch("routers.saved_lines.saved_lines_service.delete", AsyncMock(side_effect=SavedLineNotFoundError())):
        resp = client.delete(DELETE_URL)

    assert resp.status_code == 404


def test_delete_requires_auth(client):
    from main import app
    from auth import get_current_user
    del app.dependency_overrides[get_current_user]
    try:
        resp = client.delete(DELETE_URL)
        assert resp.status_code in (401, 403)
    finally:
        async def override_user():
            return _make_user()
        app.dependency_overrides[get_current_user] = override_user
