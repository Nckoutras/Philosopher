"""
Tests for auth token behaviour (A11 refresh + A16 revocation).

Pattern follows test_otp.py: import the unit, call it directly, assert.
No FastAPI test client, no network; the database is an AsyncMock.

One module owns token semantics on purpose. create_token's signature is shared by
five mint sites, and the validators are the only thing standing between a stolen
token and an account — when that contract changes, exactly one test file should
break, loudly.

A11 (refresh): the endpoint is two lines over get_current_user, which already 401s
an expired/invalid token and confirms the user still exists. What is worth pinning
is the token behaviour it depends on — identity preserved, expiry extended,
expired still rejected.

A16 (revocation): tokens carry the users.token_version they were minted with
("ver"); both validators reject a mismatch. A missing claim reads as 0 so pre-A16
tokens survive deploy. BOTH validators are covered here — get_current_user and
get_user_plan_streaming are separate code paths, and a revoked token accepted by
the streaming one would leave every SSE endpoint open.

Run: cd apps/api && pytest tests/test_auth_refresh.py -v
"""
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from auth import create_token, decode_token
from config import config


USER_ID = "11111111-2222-3333-4444-555555555555"
EMAIL = "reader@example.com"
VER = 0


def test_refreshed_token_carries_the_same_identity():
    """A refreshed token must be the SAME session, not a new one: same subject,
    same email. get_current_user resolves the user from `sub`, so a drift here
    would silently hand the caller someone else's account."""
    original = decode_token(create_token(USER_ID, EMAIL, VER))
    refreshed = decode_token(create_token(USER_ID, EMAIL, VER))

    assert refreshed["sub"] == original["sub"] == USER_ID
    assert refreshed["email"] == original["email"] == EMAIL


def test_refreshed_token_expires_strictly_later():
    """The whole point: expiry runs from ISSUE, so re-minting moves `exp` forward.
    Without this the endpoint would return a token that dies at the same moment as
    the one it replaced, and the user would still be logged out on day 7."""
    original = decode_token(create_token(USER_ID, EMAIL, VER))
    time.sleep(1.1)  # exp has 1-second granularity
    refreshed = decode_token(create_token(USER_ID, EMAIL, VER))

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


# ── A16 — token revocation ────────────────────────────────────────────────────

def _make_user(token_version: int):
    """A User row as the validators see it after the select."""
    u = MagicMock()
    u.id = USER_ID
    u.email = EMAIL
    u.token_version = token_version
    return u


def _db_returning(user):
    """AsyncMock session whose single select resolves to `user`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


def _creds(token: str):
    c = MagicMock()
    c.credentials = token
    return c


def _token_without_ver_claim(exp_offset: int = 3600) -> str:
    """A pre-A16 token: correctly signed, no "ver" claim at all. Minted by hand
    because create_token can no longer produce one."""
    return jwt.encode(
        {"sub": USER_ID, "email": EMAIL, "exp": int(time.time()) + exp_offset},
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )


async def test_token_minted_with_current_version_is_accepted():
    """T1 — the ordinary case. A token minted from the user's current
    token_version passes both the signature gate and the revocation check."""
    from auth import get_current_user

    user = _make_user(3)
    got = await get_current_user(_creds(create_token(USER_ID, EMAIL, 3)), _db_returning(user))

    assert got is user


async def test_token_is_rejected_after_the_version_is_incremented():
    """T2 — the whole feature. The token is still perfectly valid by signature and
    expiry; what kills it is that the column moved underneath it."""
    from auth import get_current_user

    token = create_token(USER_ID, EMAIL, 3)          # minted at version 3
    user = _make_user(4)                              # signout-all has since run

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(token), _db_returning(user))
    assert exc.value.status_code == 401


async def test_pre_a16_token_without_ver_claim_is_accepted_at_version_zero():
    """T3 — the no-mass-logout guarantee. Every token minted before A16 lacks the
    claim; a missing claim reads as 0, which is the column's default. If this ever
    fails, deploying A16 signs out the entire user base at once."""
    from auth import get_current_user

    user = _make_user(0)
    got = await get_current_user(_creds(_token_without_ver_claim()), _db_returning(user))

    assert got is user


async def test_pre_a16_token_dies_once_the_user_has_revoked():
    """T4 — the other half of T3, and the one that makes revocation honest. A
    revocation that spared old tokens would leave the leaked token alive, which is
    precisely the token you are trying to kill."""
    from auth import get_current_user

    user = _make_user(1)                              # revoked once

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_creds(_token_without_ver_claim()), _db_returning(user))
    assert exc.value.status_code == 401


async def test_signout_all_increments_the_column_and_commits():
    """T5 — the endpoint's entire job. 204 is declared on the route (status_code=204,
    no body returned); what matters here is that the counter moved and was committed,
    because an uncommitted increment revokes nothing."""
    from routers.auth import signout_all

    user = _make_user(7)
    db = AsyncMock()

    result = await signout_all(user=user, db=db)

    assert user.token_version == 8
    db.commit.assert_awaited_once()
    assert result is None                             # 204 carries no body


async def test_streaming_validator_also_rejects_a_revoked_token(monkeypatch):
    """T6 — the one this PR cannot ship without. get_user_plan_streaming is a SECOND,
    independent validator used by every SSE endpoint. If only get_current_user checked
    the version, revoked tokens would still stream chat, council and letters."""
    import auth as auth_module

    user = _make_user(4)
    db = _db_returning(user)

    class _Session:
        async def __aenter__(self): return db
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(auth_module, "AsyncSessionLocal", lambda: _Session())

    with pytest.raises(HTTPException) as exc:
        await auth_module.get_user_plan_streaming(_creds(create_token(USER_ID, EMAIL, 3)))
    assert exc.value.status_code == 401


async def test_signout_all_endpoint_is_registered_and_authenticated():
    """Structural guard, mirroring the /auth/refresh one: the route exists, is a
    POST, and is not reachable unauthenticated."""
    from routers.auth import router

    routes = {
        (r.path, tuple(sorted(r.methods))): r
        for r in router.routes
        if hasattr(r, "methods")
    }
    key = ("/auth/signout-all", ("POST",))
    assert key in routes, f"POST /auth/signout-all not registered; have: {list(routes)}"

    dependency_names = {
        d.call.__name__ for d in routes[key].dependant.dependencies if d.call
    }
    assert "get_current_user" in dependency_names, (
        f"/auth/signout-all must authenticate via get_current_user; got {dependency_names}"
    )
