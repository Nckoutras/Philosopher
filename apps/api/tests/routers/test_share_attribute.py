"""POST /api/v1/share/attribute — signup attribution, and its four refusals.

THE ASSERTIONS HERE ARE MOSTLY ABOUT SOMETHING NOT HAPPENING, which is the most
dangerous shape a test can have: an endpoint wired to a typo'd name, or one that
never runs at all, passes every "no event fired" assertion trivially. So the
happy path is asserted first and hard — one event, exact payload — and each
refusal is asserted against that same working path with one thing changed.

FOUR REFUSALS, ONE RESPONSE. Unknown share, revoked share, self-referral and
already-attributed all answer 204 with no body, exactly as success does. That is
not tidiness: a response that varied would turn this endpoint into an oracle for
probing whether a given share_id exists, which is the one thing an unguessable
token is for. The status code is asserted on every branch for that reason.
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from models import Share, User

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
SHARER_ID = "bbbbbbbb-0000-0000-0000-000000000002"
# The URL token the client sends. 22 chars, because that is what a share link
# carries — the column it resolves to holds shares.id instead, which is the
# distinction 068 exists to make.
PUBLIC_ID = "AbCdEfGhIjKlMnOpQrStUv"
# Some OTHER share this account was already attributed to. A UUID, matching
# the column, not the token shape.
OTHER_SHARE_UUID = "99999999-0000-0000-0000-000000000009"
ENDPOINT = "/api/v1/share/attribute"


def _user(auth_provider=None, signup_share_id=None) -> User:
    """A real User, not a MagicMock.

    C-06: the endpoint reads .id, .auth_provider and .signup_share_id, and a
    MagicMock answers all three with truthy Mocks — so `signup_share_id is not
    None` would be True and every test would silently exercise the
    already-attributed refusal while claiming to test something else.
    """
    return User(
        id=USER_ID, email="new@example.com", hashed_password=None, full_name=None,
        auth_provider=auth_provider, signup_share_id=signup_share_id,
    )


def _share(owner=SHARER_ID, revoked=False) -> Share:
    return Share(
        id="11111111-0000-0000-0000-000000000001",
        public_id=PUBLIC_ID, user_id=owner,
        artifact_type="line",
        artifact_id="22222222-0000-0000-0000-000000000001",
        snapshot={"v": 1, "artifact_type": "line", "headline": "x", "attribution": "y"},
        revoked_at=(datetime.now(timezone.utc) if revoked else None),
    )


class _Session:
    def __init__(self, share):
        self._share = share

    async def execute(self, stmt, *a, **kw):
        share = self._share

        class _R:
            def scalar_one_or_none(self):
                return share

        return _R()

    async def flush(self):
        return None

    async def commit(self):
        return None


@contextmanager
def _client(user, share):
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    app.dependency_overrides[get_current_user_plan] = lambda: (user, "free")
    app.dependency_overrides[get_db] = lambda: _Session(share)
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_current_user_plan, None)
        app.dependency_overrides.pop(get_db, None)


# ── The happy path, asserted hard so the refusals below mean something ───────

def test_a_new_account_is_attributed_and_fires_one_event():
    user = _user()
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, _share()) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    # THE COLUMN HOLDS shares.id, NOT THE TOKEN THE CLIENT SENT. public_id is a
    # credential — whoever holds it can read the share — and this row belongs to
    # a THIRD PARTY to that share and is exported to them. Storing the token
    # would hand them a working key that outlives the sharer revoking the link.
    # The value below is also exactly what the analytics event carries, so the
    # DB and PostHog join with no translation step.
    assert user.signup_share_id == "11111111-0000-0000-0000-000000000001"
    assert user.signup_share_id != PUBLIC_ID
    track.assert_called_once()
    event, distinct_id, props = track.call_args[0]
    assert event == "share_signup"
    # The NEW USER's id — signing up is their act. share_landing_view uses an
    # anonymous id because opening a link is a stranger's act; the funnel joins
    # these two on share_id, never on distinct_id.
    assert distinct_id == USER_ID
    assert props == {
        "share_id": "11111111-0000-0000-0000-000000000001",
        "artifact_type": "line",
        "method": "otp",
    }


def test_the_method_comes_from_the_account_not_the_request():
    """auth_provider is set at creation by the OAuth path and never by OTP.

    A client-supplied method would be attacker-controlled and would land in the
    funnel, so the request has no say in it — there is no field for it to use.
    """
    user = _user(auth_provider="google")
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, _share()) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    assert track.call_args[0][2]["method"] == "google"


# ── The four refusals. Same 204, no event, nothing written. ──────────────────

def test_an_unknown_share_is_refused_indistinguishably():
    user = _user()
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, None) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    assert resp.content == b""
    assert user.signup_share_id is None
    track.assert_not_called()


def test_a_revoked_share_does_not_attribute():
    user = _user()
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, _share(revoked=True)) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    assert user.signup_share_id is None
    track.assert_not_called()


def test_self_referral_does_not_attribute():
    """Worth nothing today, worth money the day a referral reward exists.

    Added now rather than then, because adding it later would silently change
    what every historical number meant.
    """
    user = _user()
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, _share(owner=USER_ID)) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    assert user.signup_share_id is None
    track.assert_not_called()


def test_an_already_attributed_account_is_not_attributed_twice():
    """Idempotency, and the reason the column exists at all.

    Attribution is triggered by a call the CLIENT makes, so a refresh, a retry or
    a double-mounted effect fires it twice. The NULL check makes "at most one
    share_signup per account" a property of the row rather than of the client
    behaving.
    """
    user = _user(signup_share_id=OTHER_SHARE_UUID)
    with patch("routers.share.analytics_service.track") as track:
        with _client(user, _share()) as client:
            resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})

    assert resp.status_code == 204
    # Unchanged — the first attribution stands.
    assert user.signup_share_id == OTHER_SHARE_UUID
    track.assert_not_called()


def test_every_outcome_answers_the_same_bytes():
    """The no-oracle property, asserted as one comparison rather than five.

    Success, unknown, revoked, self-referral and already-attributed must be
    indistinguishable from outside. Collected here so that a future branch which
    returns a body, or a 200, or a 409, fails one obvious test instead of
    quietly making the endpoint a lookup service.
    """
    cases = [
        (_user(), _share()),                                   # attributed
        (_user(), None),                                       # unknown
        (_user(), _share(revoked=True)),                       # revoked
        (_user(), _share(owner=USER_ID)),                      # self-referral
        (_user(signup_share_id=OTHER_SHARE_UUID), _share()),  # already
    ]
    seen = set()
    for user, share in cases:
        with patch("routers.share.analytics_service.track"):
            with _client(user, share) as client:
                resp = client.post(ENDPOINT, json={"share_id": PUBLIC_ID})
        seen.add((resp.status_code, resp.content))

    assert seen == {(204, b"")}, seen


# ── Shape validation, which must not become an oracle either ─────────────────

def test_a_malformed_token_is_rejected_on_shape_alone():
    """422 here is safe and 422 on a WELL-FORMED unknown token would not be.

    Length and alphabet are public facts about the scheme — anyone can see a
    share URL. Whether a particular well-formed token names a real share is not,
    and that question answers 204 either way (above).
    """
    user = _user()
    with _client(user, _share()) as client:
        for bad in ["", "short", "A" * 23, "not/valid/chars!!!!!!!"]:
            resp = client.post(ENDPOINT, json={"share_id": bad})
            assert resp.status_code == 422, bad
