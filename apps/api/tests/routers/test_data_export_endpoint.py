"""GET /api/v1/auth/me/export — the route contract.

WHAT THIS PINS beyond "it returns JSON":

  1. The rate limit runs BEFORE the export is assembled. Order matters: a limit
     checked afterwards has already done the expensive work it exists to
     prevent, and this endpoint's whole cost is the assembly.

  2. A second call inside the window is 429 with the approved copy, and does NOT
     assemble anything.

  3. The size guard is checked BEFORE assembly too, and returns 413 with the
     support address rather than a hung request.

  4. The route is authenticated. An unauthenticated GET on the endpoint that
     returns an entire account must never reach the service.

  5. Analytics carries counts and a bucket, never content.

Run: cd apps/api && pytest tests/routers/test_data_export_endpoint.py -v
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from models import User

URL = "/api/v1/auth/me/export"

_EXPORT = {
    "schema_version": 1,
    "exported_at": "2026-09-02T00:00:00Z",
    "user_id": "u1",
    "conversations": [{"id": "c1"}, {"id": "c2"}],
    "messages": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
    "memories": [],
}


def _user() -> User:
    u = User(email="someone@example.com", hashed_password=None, full_name="A Person")
    u.id = str(uuid4())
    u.is_admin = False
    u.token_version = 0
    u.created_at = datetime.now(timezone.utc)
    return u


def _client(user, *, authenticated=True):
    from main import app
    from auth import get_current_user
    from db.session import get_db

    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    return TestClient(app, raise_server_exceptions=False)


def _reset():
    from main import app
    app.dependency_overrides.clear()


def test_a_successful_export_returns_the_payload():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=True)), \
             patch("routers.auth.count_messages", new=AsyncMock(return_value=3)), \
             patch("routers.auth.build_export", new=AsyncMock(return_value=_EXPORT)):
            res = client.get(URL)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["schema_version"] == 1
        assert len(body["messages"]) == 3
    finally:
        _reset()


def test_the_rate_limit_is_checked_before_anything_is_assembled():
    """Order asserted directly. A limit checked after the build has already paid
    the cost it exists to prevent."""
    user = _user()
    client = _client(user)
    calls = []
    try:
        with patch("routers.auth.check_and_increment",
                   new=AsyncMock(side_effect=lambda *a, **k: calls.append("LIMIT") or True)), \
             patch("routers.auth.count_messages",
                   new=AsyncMock(side_effect=lambda *a, **k: calls.append("COUNT") or 3)), \
             patch("routers.auth.build_export",
                   new=AsyncMock(side_effect=lambda *a, **k: calls.append("BUILD") or _EXPORT)):
            client.get(URL)
        assert calls == ["LIMIT", "COUNT", "BUILD"], calls
    finally:
        _reset()


def test_a_second_call_within_the_hour_is_429_and_builds_nothing():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=False)), \
             patch("routers.auth.build_export", new=AsyncMock()) as build, \
             patch("routers.auth.count_messages", new=AsyncMock()) as count:
            res = client.get(URL)
        assert res.status_code == 429, res.text
        assert res.json()["detail"] == (
            "You can download your data once an hour. Please try again shortly."
        )
        build.assert_not_awaited()
        count.assert_not_awaited()
    finally:
        _reset()


def test_the_rate_limit_key_is_per_user_and_one_per_hour():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=True)) as limit, \
             patch("routers.auth.count_messages", new=AsyncMock(return_value=1)), \
             patch("routers.auth.build_export", new=AsyncMock(return_value=_EXPORT)):
            client.get(URL)
        limit.assert_awaited_once()
        key = limit.await_args.args[0]
        assert key == f"data_export:{user.id}"
        assert limit.await_args.kwargs["max_count"] == 1
        assert limit.await_args.kwargs["window_seconds"] == 3600
    finally:
        _reset()


def test_an_oversized_account_is_413_and_builds_nothing():
    """The guard exists so the failure is an error someone can act on rather
    than a timeout. It must therefore fire BEFORE the build."""
    from routers.auth import EXPORT_MAX_MESSAGES
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=True)), \
             patch("routers.auth.count_messages",
                   new=AsyncMock(return_value=EXPORT_MAX_MESSAGES + 1)), \
             patch("routers.auth.build_export", new=AsyncMock()) as build:
            res = client.get(URL)
        assert res.status_code == 413, res.text
        assert "support@thewiseroom.app" in res.json()["detail"]
        build.assert_not_awaited()
    finally:
        _reset()


def test_exactly_at_the_cap_still_exports():
    """`>` not `>=` — a user sitting exactly on the cap is not over it."""
    from routers.auth import EXPORT_MAX_MESSAGES
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=True)), \
             patch("routers.auth.count_messages",
                   new=AsyncMock(return_value=EXPORT_MAX_MESSAGES)), \
             patch("routers.auth.build_export", new=AsyncMock(return_value=_EXPORT)):
            res = client.get(URL)
        assert res.status_code == 200
    finally:
        _reset()


def test_the_route_requires_authentication():
    user = _user()
    client = _client(user, authenticated=False)
    try:
        with patch("routers.auth.build_export", new=AsyncMock()) as build:
            res = client.get(URL)
        assert res.status_code in (401, 403), res.status_code
        build.assert_not_awaited()
    finally:
        _reset()


def test_analytics_carries_counts_and_a_bucket_only():
    user = _user()
    client = _client(user)
    try:
        with patch("routers.auth.check_and_increment", new=AsyncMock(return_value=True)), \
             patch("routers.auth.count_messages", new=AsyncMock(return_value=3)), \
             patch("routers.auth.build_export", new=AsyncMock(return_value=_EXPORT)), \
             patch("routers.auth.analytics_service") as analytics:
            client.get(URL)

        analytics.track.assert_called_once()
        event, user_id, props = analytics.track.call_args.args
        assert event == "data_exported"
        assert set(props) == {"conversation_count", "record_count", "size_bucket"}
        assert props["conversation_count"] == 2
        assert props["record_count"] == 5          # 2 conversations + 3 messages
        assert props["size_bucket"] == "under_1mb"
        # Nothing from the export's CONTENT may ride along.
        assert all(isinstance(v, (int, str)) for v in props.values())
    finally:
        _reset()
