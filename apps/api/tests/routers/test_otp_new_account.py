"""POST /auth/otp/verify must report whether THIS request created the account.

THE DEFECT THIS PINS. OTP sign-in is passwordless and account creation is implicit:
verifying a code for an email with no user row creates one (routers/auth.py:198). The
response was identical either way, so the client had no way to distinguish "signed in"
from "just created an account". A UAT tester typed a gmail address instead of her yahoo
one — both hers — and landed in a brand-new empty account that looked exactly like her
real one. Her activity ended up split across two accounts.

WHY THE FLAG IS ON THE RESPONSE AND NOT ON /auth/otp/request. Telling an unauthenticated
caller whether an email is known is account enumeration. After a successful verification
the caller has proven control of the mailbox, so the disclosure leaks nothing.

WHY THE FAKE FLUSH. The new-account branch builds a real `User` whose id, is_admin and
created_at come from ORM/server defaults applied AT FLUSH. Against a bare AsyncMock those
stay None and `UserOut.model_validate` fails on a schema error that has nothing to do
with what is under test. `_flushing_db` populates exactly what a real flush would, so the
handler runs its true path.

Run: cd apps/api && pytest tests/routers/test_otp_new_account.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from models import User

URL = "/api/v1/auth/otp/verify"
NEW_EMAIL = "brand-new@example.com"
KNOWN_EMAIL = "already-here@example.com"
CODE = "123456"


def _existing_user() -> User:
    """A user row as it comes back from the database — every column populated."""
    u = User(email=KNOWN_EMAIL, hashed_password=None, full_name="Existing Person")
    u.id = str(uuid4())
    u.is_admin = False
    u.token_version = 0
    u.created_at = datetime.now(timezone.utc)
    return u


def _flushing_db(found_user):
    """An AsyncMock session whose flush() applies the ORM defaults a real flush would.

    `found_user` is what the initial SELECT returns: None to exercise the create branch,
    a User to exercise the sign-in branch.
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
    return db


def _client(found_user):
    from main import app
    from db.session import get_db

    db = _flushing_db(found_user)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app, raise_server_exceptions=True)


def _post(found_user, email):
    """Verify an OTP with every external dependency stubbed. Only the branch under
    test is real."""
    customer = MagicMock()
    customer.id = "cus_test_123"

    with patch("routers.auth.verify_otp", AsyncMock(return_value=MagicMock())), \
         patch("routers.auth.user_needs_acceptance", AsyncMock(return_value=False)), \
         patch("routers.auth.analytics_service", MagicMock()), \
         patch("routers.auth.stripe.Customer.create", MagicMock(return_value=customer)):
        client = _client(found_user)
        try:
            return client.post(URL, json={"email": email, "code": CODE})
        finally:
            from main import app
            app.dependency_overrides.clear()


def test_unknown_email_reports_a_new_account():
    """The account did not exist a moment ago. The user must be told."""
    resp = _post(found_user=None, email=NEW_EMAIL)

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["is_new_account"] is True, (
        "verifying an unknown email CREATED an account (auth.py:198) but the response "
        "does not say so — this is the silent-second-account defect"
    )
    assert body["user"]["email"] == NEW_EMAIL


def test_existing_email_is_not_a_new_account():
    """An ordinary sign-in must not show the new-account screen."""
    resp = _post(found_user=_existing_user(), email=KNOWN_EMAIL)

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["is_new_account"] is False, (
        "an existing user signing in was reported as a new account — every returning "
        "user would be told their account was just created"
    )
    assert body["user"]["email"] == KNOWN_EMAIL


def test_flag_does_not_disturb_the_rest_of_the_payload():
    """The field is additive: the token and user payload are unchanged around it."""
    resp = _post(found_user=_existing_user(), email=KNOWN_EMAIL)

    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["id"]
