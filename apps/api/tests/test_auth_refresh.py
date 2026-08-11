"""
Tests for the sliding-session token refresh (A11).

Pattern follows test_otp.py: import the unit, call it directly, assert.
No FastAPI test client, no database, no network.

The endpoint itself (routers/auth.py POST /auth/refresh) is two lines over
get_current_user, which already 401s an expired/invalid token and already
confirms the user still exists. What is worth pinning is the token behaviour it
depends on — identity preserved, expiry extended, expired still rejected.

Run: cd apps/api && pytest tests/test_auth_refresh.py -v
"""
import time

import pytest
from fastapi import HTTPException
from jose import jwt

from auth import create_token, decode_token
from config import config


USER_ID = "11111111-2222-3333-4444-555555555555"
EMAIL = "reader@example.com"


def test_refreshed_token_carries_the_same_identity():
    """A refreshed token must be the SAME session, not a new one: same subject,
    same email. get_current_user resolves the user from `sub`, so a drift here
    would silently hand the caller someone else's account."""
    original = decode_token(create_token(USER_ID, EMAIL))
    refreshed = decode_token(create_token(USER_ID, EMAIL))

    assert refreshed["sub"] == original["sub"] == USER_ID
    assert refreshed["email"] == original["email"] == EMAIL


def test_refreshed_token_expires_strictly_later():
    """The whole point: expiry runs from ISSUE, so re-minting moves `exp` forward.
    Without this the endpoint would return a token that dies at the same moment as
    the one it replaced, and the user would still be logged out on day 7."""
    original = decode_token(create_token(USER_ID, EMAIL))
    time.sleep(1.1)  # exp has 1-second granularity
    refreshed = decode_token(create_token(USER_ID, EMAIL))

    assert refreshed["exp"] > original["exp"], (
        "a refreshed token must outlive the one it replaces"
    )


def test_expired_token_is_still_rejected():
    """Refresh must not become a way in for a dead token. The endpoint's only gate
    is get_current_user -> decode_token, so this is the gate: an expired token
    raises 401 and never reaches the refresh body."""
    expired = jwt.encode(
        {"sub": USER_ID, "email": EMAIL, "exp": int(time.time()) - 60},
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        decode_token(expired)
    assert exc.value.status_code == 401


def test_malformed_token_is_still_rejected():
    """Same gate, the other failure mode — a token signed with the wrong secret
    must not be refreshable into a valid one."""
    forged = jwt.encode(
        {"sub": USER_ID, "email": EMAIL, "exp": int(time.time()) + 3600},
        "not-the-real-secret",
        algorithm=config.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        decode_token(forged)
    assert exc.value.status_code == 401


def test_refresh_endpoint_is_registered_and_authenticated():
    """The route exists, is a POST, and depends on get_current_user — i.e. it is
    not reachable unauthenticated. Cheap structural guard against the endpoint
    being renamed or its dependency dropped."""
    from routers.auth import router

    routes = {
        (r.path, tuple(sorted(r.methods))): r
        for r in router.routes
        if hasattr(r, "methods")
    }
    key = ("/auth/refresh", ("POST",))
    assert key in routes, f"POST /auth/refresh not registered; have: {list(routes)}"

    dependency_names = {
        d.call.__name__ for d in routes[key].dependant.dependencies if d.call
    }
    assert "get_current_user" in dependency_names, (
        f"/auth/refresh must authenticate via get_current_user; got {dependency_names}"
    )
