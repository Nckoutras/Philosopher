"""Γ-1c — the Google half of the letter returnTo, carried in the CSRF state entry.

WHY THE STATE ENTRY AND NOT A QUERY PARAM. The returnTo has to survive a round
trip through Google, and anything put in that redirect is visible and rewritable
for the whole journey. The flow already mints a CSRF state token into Redis with
the literal value "1" and a 300s TTL, so the destination rides as that VALUE:
never in a URL, expiring on its own, and reachable only by presenting the state
token that names it.

THE NARROW EXCEPTION THIS TAKES. Γ-1c is otherwise forbidden from touching auth
logic. Only the state entry's PAYLOAD changes — the existence check that makes it
a CSRF gate is untouched, and test_an_unknown_state_is_still_refused is here to
prove that rather than assert it in a comment.

TWO COPIES OF THE VALIDATION RULE EXIST, deliberately: this one and
apps/web/lib/safeReturnTo.ts. The client cannot be trusted to have validated —
/auth/oauth/google is a plain GET anyone can call with any query string — and the
web copy still runs at the point of use. test_the_web_twin_has_the_same_clauses
is what stops them drifting apart in silence.

Run: cd apps/api && pytest tests/routers/test_oauth_return_to.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pathlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from models import User
from routers.auth_oauth import OAUTH_STATE_NO_RETURN, safe_return_to

CALLBACK_URL = "/api/v1/auth/oauth/google/callback"
START_URL = "/api/v1/auth/oauth/google"
EMAIL = "reader@example.com"
GOOGLE_SUB = "google-sub-12345"

LETTER = "/app/letters/7f3c1a90-0000-4000-8000-000000000001"
LETTER_WITH_MARKER = f"{LETTER}?src=email"

# The same table the web unit tests use. Each entry is a documented redirect
# technique, not a generic bad string.
HOSTILE = [
    "//evil.com",
    "///evil.com",
    "/\\evil.com",
    "/app/\\evil.com",
    "https://evil.com",
    "http://evil.com",
    "javascript:alert(1)",
    "/auth?mode=signin",
    "/admin",
    "app/today",
    "",
    "/appfoo/bar",
    "%2f%2fevil.com",
    "/app/" + "a" * 600,
]


# ── The rule itself ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", HOSTILE)
def test_hostile_values_are_refused(value):
    assert safe_return_to(value) is None, f"{value!r} must not be accepted as a returnTo"


@pytest.mark.parametrize("value", [
    "/app/today",
    LETTER,
    LETTER_WITH_MARKER,
    "/app/letters/x?src=email&foo=bar",
])
def test_real_destinations_are_accepted(value):
    assert safe_return_to(value) == value


def test_none_and_empty_are_refused():
    assert safe_return_to(None) is None
    assert safe_return_to("") is None


def test_a_value_whose_second_decode_escapes_is_refused():
    """Layering an extra encoding must not reach anywhere one decode would not."""
    assert safe_return_to("/app/x") == "/app/x"
    assert safe_return_to("%2f%2fevil.com") is None


def test_the_web_twin_has_the_same_clauses():
    """The drift guard for the second copy of this rule.

    Structural rather than behavioural — the TS cannot be executed from pytest —
    but it fails the moment a clause is dropped on one side, which is the only way
    these two realistically diverge. Someone loosening the web rule has to notice
    this test to get past it.
    """
    web = (
        pathlib.Path(__file__).resolve().parents[3]
        / "web" / "lib" / "safeReturnTo.ts"
    )
    src = web.read_text(encoding="utf-8")
    for clause in ("'//'", "'/\\\\'", "'\\\\'", "'://'", "512", "'/app/'"):
        assert clause in src, (
            f"apps/web/lib/safeReturnTo.ts no longer contains {clause} — the web rule "
            f"and the server rule have drifted"
        )


# ── Stubs, matching tests/routers/test_oauth_new_account.py ──────────────────

def _existing_user() -> User:
    u = User(email=EMAIL, hashed_password=None, full_name="Existing Person")
    u.id = str(uuid4())
    u.is_admin = False
    u.token_version = 0
    u.created_at = datetime.now(timezone.utc)
    return u


def _google_client_stub():
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


def _db_for(found_user):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=found_user)
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _callback_with_state_value(stored, found_user=None):
    """Drive the callback with a given Redis state value. Returns (status, location)."""
    from main import app
    from db.session import get_db

    db = _db_for(found_user if found_user is not None else _existing_user())

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    r = AsyncMock()
    r.get = AsyncMock(return_value=stored)
    r.delete = AsyncMock()

    with patch("routers.auth_oauth.get_redis", AsyncMock(return_value=r)), \
         patch("routers.auth_oauth.httpx.AsyncClient", _google_client_stub()), \
         patch("routers.auth_oauth.stripe.Customer.create", MagicMock()), \
         patch("routers.auth_oauth.user_needs_acceptance", AsyncMock(return_value=False)), \
         patch("routers.auth_oauth.analytics_service", MagicMock()):
        client = TestClient(app, follow_redirects=False)
        try:
            resp = client.get(CALLBACK_URL, params={"code": "auth-code", "state": "state-token"})
        finally:
            app.dependency_overrides.clear()

    return resp.status_code, resp.headers["location"]


# ── The CSRF gate is unchanged ───────────────────────────────────────────────

def test_an_unknown_state_is_still_refused():
    """THE ONE THAT GUARDS THE EXCEPTION. Carrying a payload in the state entry
    must not weaken what the entry is FOR. An absent key — expired, forged, or
    already consumed — still fails closed, before any token exchange."""
    status, location = _callback_with_state_value(None)

    assert status == 302
    assert "oauth_invalid_state" in location, (
        f"a missing state entry must be refused; got {location!r}"
    )
    assert "/auth/oauth/finish" not in location


# ── The carrier ──────────────────────────────────────────────────────────────

def test_a_stored_letter_path_reaches_the_finish_url():
    status, location = _callback_with_state_value(LETTER_WITH_MARKER)

    assert status == 302
    assert "/auth/oauth/finish" in location
    qs = parse_qs(urlparse(location).query)
    assert qs.get("next") == [LETTER_WITH_MARKER], (
        f"the returnTo parked at start did not survive to the finish URL: {qs.get('next')!r}"
    )
    # src=email must still be attached to the letter, or the reader arrives
    # unattributed and email_opened_at is never written.
    assert "src=email" in qs["next"][0]


def test_the_sentinel_produces_no_next_at_all():
    """Absent, not empty. The finish page's searchParams.get must return null so
    it falls through to its own default rather than reading an empty string."""
    status, location = _callback_with_state_value(OAUTH_STATE_NO_RETURN)

    assert status == 302
    qs = parse_qs(urlparse(location).query)
    assert "next" not in qs, f"expected no next key, got {qs.get('next')!r}"


@pytest.mark.parametrize("value", ["//evil.com", "https://evil.com", "/auth"])
def test_a_hostile_value_in_the_store_is_dropped_on_the_way_out(value):
    """Defence in depth. The value was validated before it was stored, so this
    state is not reachable by the normal path — which is exactly why it is worth
    asserting: a value read back from a store is an input like any other."""
    status, location = _callback_with_state_value(value)

    assert status == 302
    qs = parse_qs(urlparse(location).query)
    assert "next" not in qs, f"a hostile stored value reached the finish URL: {qs.get('next')!r}"


# ── The start endpoint parks it ──────────────────────────────────────────────

def _start_with(next_param):
    """Drive GET /auth/oauth/google and return the VALUE it parked in Redis.

    config is patched on the INSTANCE, not the class — the router holds the
    imported singleton, so a class-level patch changes nothing it can see.
    """
    from main import app
    from config import config

    r = AsyncMock()
    r.set = AsyncMock()
    with patch("routers.auth_oauth.get_redis", AsyncMock(return_value=r)), \
         patch.object(config, "GOOGLE_OAUTH_ENABLED", True), \
         patch.object(config, "GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com"):
        client = TestClient(app, follow_redirects=False)
        params = {"next": next_param} if next_param is not None else {}
        resp = client.get(START_URL, params=params)

    assert resp.status_code == 302, resp.text
    r.set.assert_awaited_once()
    key, value = r.set.call_args[0][0], r.set.call_args[0][1]
    assert key.startswith("oauth_state:")
    assert r.set.call_args[1]["ex"] == 300, "the 300s TTL must be unchanged"
    return value


def test_start_parks_a_valid_return_to_as_the_state_value():
    assert _start_with(LETTER_WITH_MARKER) == LETTER_WITH_MARKER


def test_start_parks_the_sentinel_when_there_is_no_return_to():
    assert _start_with(None) == OAUTH_STATE_NO_RETURN


@pytest.mark.parametrize("value", ["//evil.com", "https://evil.com", "/auth", "/admin"])
def test_start_refuses_to_park_a_hostile_return_to(value):
    """Validated BEFORE storage, so a crafted start URL cannot even get its value
    into Redis. The worst it achieves is the default destination."""
    assert _start_with(value) == OAUTH_STATE_NO_RETURN
