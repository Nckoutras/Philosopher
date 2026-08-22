"""The Google callback's redirect must say whether THIS sign-in created the account.

THE DEFECT THIS PINS (A8b). auth_oauth.py:127-148 creates User + Stripe customer +
Subscription for an unrecognised Google account, and :125 has always computed
`is_new_user = user is None` without ever surfacing it. So a Google sign-in with an
address the user did not mean to use produced a second, empty account in silence — the
same defect A8 fixed on the OTP path, on the sibling surface.

WHY BOTH BRANCHES LIVE IN ONE FILE. A test that only checked the unknown-account case
would pass against a version that hardcoded new_account=1 for everyone, which would send
every returning Google user to a screen telling them their account was just created.
Asserting BOTH values is what makes this discriminate between the branches rather than
merely detect a missing field.

WHAT IS STUBBED AND WHY
  - `get_redis`          — the CSRF state check (:71-75). Not under test; without it the
                           callback bails before reaching the branch at all.
  - `httpx.AsyncClient`  — Google's token exchange (:80) and userinfo fetch (:96). These
                           are network calls to a third party. The stub returns a fixed
                           identity so `email` / `google_sub` are deterministic.
  - `stripe.Customer.create` — a live billing call inside the creation branch (:140).
  - `user_needs_acceptance`  — orthogonal; pinned to False so needs_disclaimer cannot be
                           confused with the flag under test.
  - `analytics_service`  — fire-and-forget, already wrapped in try/except.

Nothing between the branch decision (:125) and the redirect (:174-176) is stubbed. That
path runs for real.

Run: cd apps/api && pytest tests/routers/test_oauth_new_account.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from models import User

URL = "/api/v1/auth/oauth/google/callback"
GOOGLE_SUB = "google-sub-12345"
EMAIL = "picked-the-wrong-one@gmail.com"


def _existing_user() -> User:
    """A user row as the database returns it — every column populated."""
    u = User(email=EMAIL, hashed_password=None, full_name="Existing Person")
    u.id = str(uuid4())
    u.is_admin = False
    u.token_version = 0
    u.created_at = datetime.now(timezone.utc)
    return u


def _google_client_stub():
    """An httpx.AsyncClient context manager returning a fixed Google identity."""
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json = MagicMock(return_value={"access_token": "ya29.stub"})

    userinfo_resp = MagicMock()
    userinfo_resp.status_code = 200
    userinfo_resp.json = MagicMock(
        return_value={"email": EMAIL, "sub": GOOGLE_SUB, "name": "Test Person"}
    )

    client = MagicMock()
    client.post = AsyncMock(return_value=token_resp)
    client.get = AsyncMock(return_value=userinfo_resp)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


def _flushing_db(found_user):
    """A session whose flush() applies the ORM defaults a real flush would.

    The initial SELECT runs twice in the callback (by oauth_provider_id, then by email),
    so `found_user` is returned for both.
    """
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=found_user)
    db.execute = AsyncMock(return_value=result)

    added: list = []
    db.add = MagicMock(side_effect=added.append)

    async def flush():
        for obj in added:
            if isinstance(obj, User):
                if obj.id is None:
                    obj.id = str(uuid4())
                if obj.is_admin is None:
                    obj.is_admin = False
                if obj.token_version is None:
                    obj.token_version = 0
                if obj.created_at is None:
                    obj.created_at = datetime.now(timezone.utc)

    db.flush = AsyncMock(side_effect=flush)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _redis_stub():
    r = AsyncMock()
    r.get = AsyncMock(return_value="1")   # state token is valid
    r.delete = AsyncMock()
    return r


def _callback(found_user):
    """Drive the callback to its redirect. Returns the parsed query string."""
    from main import app
    from db.session import get_db

    db = _flushing_db(found_user)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    customer = MagicMock()
    customer.id = "cus_oauth_test"

    with patch("routers.auth_oauth.get_redis", AsyncMock(return_value=_redis_stub())), \
         patch("routers.auth_oauth.httpx.AsyncClient", _google_client_stub()), \
         patch("routers.auth_oauth.stripe.Customer.create", MagicMock(return_value=customer)), \
         patch("routers.auth_oauth.user_needs_acceptance", AsyncMock(return_value=False)), \
         patch("routers.auth_oauth.analytics_service", MagicMock()):
        client = TestClient(app, follow_redirects=False)
        try:
            resp = client.get(URL, params={"code": "auth-code", "state": "state-token"})
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 302, resp.text
    location = resp.headers["location"]
    assert "/auth/oauth/finish" in location, (
        f"callback did not reach the finish redirect — got {location!r}"
    )
    return parse_qs(urlparse(location).query)


def test_unknown_google_account_sets_new_account_1():
    """No user row for this Google identity, so the callback CREATED the account."""
    qs = _callback(found_user=None)

    assert qs.get("new_account") == ["1"], (
        "the callback created an account (auth_oauth.py:127-148) but the redirect does "
        f"not say so — got new_account={qs.get('new_account')!r}. This is the silent "
        "second-account defect on the Google path."
    )


def test_known_google_account_sets_new_account_0():
    """An ordinary Google sign-in must NOT be reported as a new account."""
    qs = _callback(found_user=_existing_user())

    assert qs.get("new_account") == ["0"], (
        "a returning Google user was reported as a new account — every one of them "
        f"would be told their account was just created. got {qs.get('new_account')!r}"
    )


def test_the_existing_redirect_keys_are_untouched():
    """new_account is additive: token and needs_disclaimer still travel as before."""
    qs = _callback(found_user=_existing_user())

    assert qs.get("token"), "the token disappeared from the finish redirect"
    assert qs.get("needs_disclaimer") == ["0"]
