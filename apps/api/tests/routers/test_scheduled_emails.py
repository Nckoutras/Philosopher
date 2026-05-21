"""Tests for POST/GET/DELETE /api/v1/scheduled-emails.

Uses FastAPI TestClient with dependency overrides for DB and auth.
DB calls patched at the router module level via sqlalchemy select mocks.

Run: cd apps/api && pytest tests/routers/test_scheduled_emails.py -v
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

USER_ID    = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER_ID   = "aaaaaaaa-0000-0000-0000-000000000002"
PERSONA_ID = "dddddddd-0000-0000-0000-000000000001"
LINE_ID    = "eeeeeeee-0000-0000-0000-000000000001"
EMAIL_ID   = "ffffffff-0000-0000-0000-000000000001"

POST_URL   = "/api/v1/scheduled-emails"
GET_URL    = "/api/v1/scheduled-emails"
DELETE_URL = f"/api/v1/scheduled-emails/{EMAIL_ID}"

_FUTURE_1H  = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
_FUTURE_4Y  = (datetime.now(timezone.utc) + timedelta(days=365 * 4)).isoformat()
_TOO_SOON   = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
_TOO_FAR    = (datetime.now(timezone.utc) + timedelta(days=365 * 6)).isoformat()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(is_admin=False):
    u = MagicMock()
    u.id = USER_ID
    u.email = "user@example.com"
    u.is_admin = is_admin
    return u


def _make_saved_line():
    sl = MagicMock()
    sl.id = LINE_ID
    sl.user_id = USER_ID
    sl.persona_id = PERSONA_ID
    sl.deleted_at = None
    return sl


def _make_email_row(status="pending"):
    row = MagicMock()
    row.id = EMAIL_ID
    row.saved_line_id = LINE_ID
    row.persona_id = PERSONA_ID
    row.note = None
    row.recipient_email = "user@example.com"
    row.scheduled_for = datetime.now(timezone.utc) + timedelta(hours=2)
    row.status = status
    row.sent_at = None
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


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


# ── POST /api/v1/scheduled-emails ────────────────────────────────────────────

def test_post_201_pro_user(client):
    saved_line = _make_saved_line()
    email_row  = _make_email_row()

    with (
        patch("routers.scheduled_emails.get_user_tier", AsyncMock(return_value="pro")),
        patch("routers.scheduled_emails.select", side_effect=lambda *a, **kw: MagicMock()),
    ):
        # Patch the db.execute chain for saved_line lookup
        sl_result = MagicMock()
        sl_result.scalar_one_or_none.return_value = saved_line

        async def fake_execute(q):
            return sl_result

        async def fake_refresh(row):
            row.id = EMAIL_ID
            row.created_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)

        client._db[0].execute = fake_execute
        client._db[0].refresh = fake_refresh
        client._db[0].add = MagicMock()
        client._db[0].commit = AsyncMock()

        resp = client.post(POST_URL, json={
            "saved_line_id": LINE_ID,
            "scheduled_for": _FUTURE_1H,
        })

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["persona_id"] == PERSONA_ID


def test_post_403_free_user(client):
    with patch("routers.scheduled_emails.get_user_tier", AsyncMock(return_value="free")):
        resp = client.post(POST_URL, json={
            "saved_line_id": LINE_ID,
            "scheduled_for": _FUTURE_1H,
        })
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Pro subscription required"


def test_post_422_scheduled_for_too_soon(client):
    with patch("routers.scheduled_emails.get_user_tier", AsyncMock(return_value="pro")):
        resp = client.post(POST_URL, json={
            "saved_line_id": LINE_ID,
            "scheduled_for": _TOO_SOON,
        })
    assert resp.status_code == 422


def test_post_422_scheduled_for_too_far(client):
    with patch("routers.scheduled_emails.get_user_tier", AsyncMock(return_value="pro")):
        resp = client.post(POST_URL, json={
            "saved_line_id": LINE_ID,
            "scheduled_for": _TOO_FAR,
        })
    assert resp.status_code == 422


def test_validator_accepts_4_years():
    from schemas import ScheduledEmailCreate
    future_4y = datetime.now(timezone.utc) + timedelta(days=365 * 4)
    obj = ScheduledEmailCreate(saved_line_id="some-id", scheduled_for=future_4y)
    assert obj.scheduled_for == future_4y


def test_post_404_saved_line_not_found(client):
    sl_result = MagicMock()
    sl_result.scalar_one_or_none.return_value = None

    async def fake_execute(q):
        return sl_result

    client._db[0].execute = fake_execute

    with patch("routers.scheduled_emails.get_user_tier", AsyncMock(return_value="pro")):
        resp = client.post(POST_URL, json={
            "saved_line_id": LINE_ID,
            "scheduled_for": _FUTURE_1H,
        })
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Saved line not found"


# ── GET /api/v1/scheduled-emails ─────────────────────────────────────────────

def test_get_200_returns_list(client):
    row = {
        "id": EMAIL_ID,
        "persona_id": PERSONA_ID,
        "persona_name": "Marcus Aurelius",
        "persona_portrait_url": "https://cdn.example.com/marcus.jpg",
        "scheduled_for": datetime.now(timezone.utc) + timedelta(hours=2),
        "status": "pending",
        "sent_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    mappings_mock = MagicMock()
    mappings_mock.all.return_value = [row]
    result_mock = MagicMock()
    result_mock.mappings.return_value = mappings_mock

    async def fake_execute(q):
        return result_mock

    client._db[0].execute = fake_execute

    resp = client.get(GET_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["persona_name"] == "Marcus Aurelius"
    assert body[0]["status"] == "pending"


def test_get_status_filter_pending(client):
    mappings_mock = MagicMock()
    mappings_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.mappings.return_value = mappings_mock

    async def fake_execute(q):
        return result_mock

    client._db[0].execute = fake_execute

    resp = client.get(GET_URL + "?status=pending")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_invalid_status_filter(client):
    resp = client.get(GET_URL + "?status=invalid")
    assert resp.status_code == 422


# ── DELETE /api/v1/scheduled-emails/{id} ─────────────────────────────────────

def test_delete_204_cancels_pending(client):
    row = _make_email_row(status="pending")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row

    async def fake_execute(q):
        return result_mock

    client._db[0].execute = fake_execute
    client._db[0].commit = AsyncMock()

    resp = client.delete(DELETE_URL)
    assert resp.status_code == 204
    assert row.status == "cancelled"


def test_delete_409_already_sent(client):
    row = _make_email_row(status="sent")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row

    async def fake_execute(q):
        return result_mock

    client._db[0].execute = fake_execute

    resp = client.delete(DELETE_URL)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Only pending emails can be cancelled"


def test_delete_404_not_found(client):
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None

    async def fake_execute(q):
        return result_mock

    client._db[0].execute = fake_execute

    resp = client.delete(DELETE_URL)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Scheduled email not found"
