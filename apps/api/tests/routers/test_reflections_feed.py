"""Tests for GET /api/v1/reflections/feed.

Uses FastAPI TestClient with dependency overrides for DB and auth.
The feed service is patched at the router module level.

Run: cd apps/api && pytest tests/routers/test_reflections_feed.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
FEED_URL = "/api/v1/reflections/feed"

NOW = datetime.now(timezone.utc)


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _line(saved_at):
    return {
        "kind": "line",
        "id": "eeeeeeee-0000-0000-0000-000000000001",
        "message_id": "bbbbbbbb-0000-0000-0000-000000000001",
        "persona_id": "dddddddd-0000-0000-0000-000000000001",
        "persona_slug": "marcus-aurelius",
        "persona_display_name": "Marcus Aurelius",
        "message_content": "You have power over your mind.",
        "conversation_id": "cccccccc-0000-0000-0000-000000000001",
        "saved_at": saved_at,
        "source_type": "manual_save",
    }


def _mirror(saved_at):
    return {
        "kind": "mirror_verdict",
        "save_id": "11111111-0000-0000-0000-000000000001",
        "mirror_id": "22222222-0000-0000-0000-000000000001",
        "thread": "You may be circling the same fear from a safer distance.",
        "host_persona_slug": "carl_jung",
        "host_persona_name": "Carl Jung",
        "mirror_kind": "weekly",
        "saved_at": saved_at,
    }


def _council(saved_at):
    return {
        "kind": "council_verdict",
        "save_id": "33333333-0000-0000-0000-000000000001",
        "session_id": "44444444-0000-0000-0000-000000000001",
        "synthesis": "The four agree only that you already know.",
        "persona_slugs": ["niccolo_machiavelli", "epictetus", "sigmund_freud", "simone_de_beauvoir"],
        "created_at": saved_at,
        "saved_at": saved_at,
    }


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
    yield tc

    app.dependency_overrides.clear()


def test_feed_returns_three_kinds(client):
    from unittest.mock import patch
    items = [_line(NOW), _mirror(NOW - timedelta(hours=1)), _council(NOW - timedelta(hours=2))]
    with patch("routers.reflections.reflections_feed_service.get_feed", AsyncMock(return_value=items)):
        resp = client.get(FEED_URL)

    assert resp.status_code == 200
    body = resp.json()["items"]
    assert [i["kind"] for i in body] == ["line", "mirror_verdict", "council_verdict"]


def test_feed_preserves_service_ordering(client):
    """Router does not re-sort; it trusts the service's saved_at-desc order."""
    from unittest.mock import patch
    items = [_mirror(NOW), _line(NOW - timedelta(days=1)), _council(NOW - timedelta(days=2))]
    with patch("routers.reflections.reflections_feed_service.get_feed", AsyncMock(return_value=items)):
        resp = client.get(FEED_URL)

    assert resp.status_code == 200
    saved_ats = [i["saved_at"] for i in resp.json()["items"]]
    assert saved_ats == sorted(saved_ats, reverse=True)


def test_feed_mirror_item_shape(client):
    from unittest.mock import patch
    with patch("routers.reflections.reflections_feed_service.get_feed", AsyncMock(return_value=[_mirror(NOW)])):
        resp = client.get(FEED_URL)

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["kind"] == "mirror_verdict"
    assert item["thread"]
    assert item["host_persona_name"] == "Carl Jung"
    assert item["mirror_kind"] == "weekly"


def test_feed_council_item_shape(client):
    from unittest.mock import patch
    with patch("routers.reflections.reflections_feed_service.get_feed", AsyncMock(return_value=[_council(NOW)])):
        resp = client.get(FEED_URL)

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["kind"] == "council_verdict"
    assert item["synthesis"]
    assert len(item["persona_slugs"]) == 4


def test_feed_empty(client):
    from unittest.mock import patch
    with patch("routers.reflections.reflections_feed_service.get_feed", AsyncMock(return_value=[])):
        resp = client.get(FEED_URL)

    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_feed_requires_auth(client):
    from main import app
    from auth import get_current_user
    del app.dependency_overrides[get_current_user]
    try:
        resp = client.get(FEED_URL)
        assert resp.status_code in (401, 403)
    finally:
        pass


# ── Service seam: {"kind": "line", **row} expansion ──────────────────────────
# saved_lines_service.list_for_user returns list[dict] (Row._asdict()). The
# _lines() expansion is the one untested seam that 500s the whole feed if the
# upstream shape ever changes (e.g. to ORM objects). This test pins it.

async def test_lines_expands_dict_rows_with_kind():
    from unittest.mock import patch
    from services.reflections_feed_service import reflections_feed_service

    row = {
        "id": "eeeeeeee-0000-0000-0000-000000000001",
        "message_id": "bbbbbbbb-0000-0000-0000-000000000001",
        "persona_id": "dddddddd-0000-0000-0000-000000000001",
        "source_type": "manual_save",
        "saved_at": NOW,
        "message_content": "You have power over your mind.",
        "conversation_id": "cccccccc-0000-0000-0000-000000000001",
        "persona_slug": "marcus-aurelius",
        "persona_display_name": "Marcus Aurelius",
    }
    with patch(
        "services.reflections_feed_service.saved_lines_service.list_for_user",
        AsyncMock(return_value=[row]),
    ):
        items = await reflections_feed_service._lines(AsyncMock(), USER_ID)

    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "line"
    # Every original key survives the **row expansion unchanged...
    for key, value in row.items():
        assert item[key] == value
    # ...and the result validates against the ReflectionFeedLine schema, proving
    # the dict keys match the wire contract the frontend consumes.
    from schemas import ReflectionFeedLine
    ReflectionFeedLine.model_validate(item)
