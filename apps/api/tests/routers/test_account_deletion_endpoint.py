"""DELETE /api/v1/auth/me — the route contract.

WHAT THIS PINS, beyond "it returns 204":

  1. A Stripe cancel failure is a 502 AND says the account was not deleted. The
     status code is the difference between "try again" and "your data is gone
     and you are still being billed", and the user has no way to check.

  2. The route is authenticated. An unauthenticated DELETE on the one
     irreversible endpoint in the product must never reach the service.

  3. No token_version bump. The row's absence revokes every token by itself
     (get_current_user 401s on a missing user before it reads "ver"), so a bump
     would be a write to a row being deleted in the same request. Asserted so
     that nobody "fixes" the apparent omission later.

Run: cd apps/api && pytest tests/routers/test_account_deletion_endpoint.py -v
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
from services.account_deletion_service import StripeCancelFailed

URL = "/api/v1/auth/me"


def _user() -> User:
    u = User(email="someone@example.com", hashed_password=None, full_name="A Person")
    u.id = str(uuid4())
    u.is_admin = False
    u.token_version = 0
    u.created_at = datetime.now(timezone.utc)
    return u


def _client(user, *, authenticated=True):
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    db = AsyncMock()

    if authenticated:
        app.dependency_overrides[get_current_user_plan] = lambda: (user, "pro")
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app, raise_server_exceptions=False)
    return client, db


def _reset():
    from main import app
    app.dependency_overrides.clear()


def test_a_successful_deletion_returns_204():
    user = _user()
    client, db = _client(user)
    try:
        with patch(
            "routers.auth.delete_account", new=AsyncMock(return_value={})
        ) as deleter:
            res = client.delete(URL)
        assert res.status_code == 204, res.text
        assert res.content == b""
        deleter.assert_awaited_once()
        # The plan reaches the service — the analytics event carries it and it
        # must be read while the subscription row still exists.
        assert deleter.await_args.kwargs["plan"] == "pro"
    finally:
        _reset()


def test_a_stripe_failure_is_a_502_that_says_nothing_was_deleted():
    """Not a 500. The account still exists, the failure is upstream, and the
    message is the only way the user learns their data is intact."""
    user = _user()
    client, db = _client(user)
    try:
        with patch(
            "routers.auth.delete_account",
            new=AsyncMock(side_effect=StripeCancelFailed("card network down")),
        ):
            res = client.delete(URL)
        assert res.status_code == 502, res.text
        detail = res.json()["detail"]
        assert "NOT been deleted" in detail, detail
        # The upstream error text is not echoed to the user.
        assert "card network down" not in detail
    finally:
        _reset()


def test_the_route_requires_authentication():
    user = _user()
    client, _ = _client(user, authenticated=False)
    try:
        with patch("routers.auth.delete_account", new=AsyncMock()) as deleter:
            res = client.delete(URL)
        assert res.status_code in (401, 403), res.status_code
        deleter.assert_not_awaited()
    finally:
        _reset()


def test_the_route_does_not_bump_token_version():
    """Deletion revokes tokens by removing the row, not by incrementing a column
    on it. If someone adds a bump here, this fails and the comment explains why
    it was never needed."""
    user = _user()
    before = user.token_version
    client, _ = _client(user)
    try:
        with patch("routers.auth.delete_account", new=AsyncMock(return_value={})):
            res = client.delete(URL)
        assert res.status_code == 204
        assert user.token_version == before
    finally:
        _reset()
