"""GET /api/v1/s/{public_id} — the one unauthenticated route that returns writing.

WHAT IS PINNED HERE, and each fails independently:

  1. THE LANDING READ TOUCHES ONLY `shares`. This is founder ruling 1 and it is
     the load-bearing one: if the page ever reads the source artifact, then
     editing that artifact silently rewrites what a stranger already saw, and
     deleting it breaks a link already in circulation. Asserted by counting the
     statements the route issues, not by reading the code.
  2. A REVOKED SHARE RETURNS 200 WITH NO SNAPSHOT. Not 404 (which reads as a
     broken app to someone who just scanned a friend's card) and not the text
     alongside a flag (which leaves it one devtools tab from the people it was
     withdrawn from).
  3. THE LIMITER FAILS OPEN. The opposite of the creation routes, deliberately:
     a Redis blip must not take down the acquisition page.
  4. THE ANALYTICS IDENTITY IS NOT THE SHARER. A landing view is a stranger's
     act; filing it under the sharer's id would put other people's browsing in
     that person's profile.
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models import Share
from schemas import ShareSnapshot

PUBLIC_ID = "AbCdEfGhIjKlMnOpQrStUv"
USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
ENDPOINT = f"/api/v1/s/{PUBLIC_ID}"

SNAPSHOT = ShareSnapshot(
    artifact_type="line",
    headline="You are not choosing stability for them.",
    attribution="Marcus Aurelius, in conversation",
    persona_slug="marcus_aurelius",
    persona_name="Marcus Aurelius",
)


def _share(revoked=False) -> Share:
    """A real Share, not a MagicMock.

    C-06: the route reads .revoked_at, .artifact_type, .snapshot and .id, and a
    MagicMock answers every one of them with a truthy Mock — so `revoked_at is
    not None` would be True on a live share and the test would assert the
    withdrawn path while claiming to test the live one.
    """
    s = Share(
        id="11111111-0000-0000-0000-000000000001",
        public_id=PUBLIC_ID,
        user_id=USER_ID,
        artifact_type="line",
        artifact_id="22222222-0000-0000-0000-000000000001",
        snapshot=SNAPSHOT.model_dump(mode="json"),
        revoked_at=(datetime.now(timezone.utc) if revoked else None),
    )
    return s


class _RecordingSession:
    """Answers one query and remembers every statement it was asked for."""

    def __init__(self, share):
        self._share = share
        self.statements: list[str] = []

    async def execute(self, stmt, *a, **kw):
        self.statements.append(str(stmt))

        class _R:
            def __init__(self, one):
                self._one = one

            def scalar_one_or_none(self):
                return self._one

        return _R(self._share)


@contextmanager
def _client(share, limiter=None):
    from main import app
    from db.session import get_db

    session = _RecordingSession(share)
    app.dependency_overrides[get_db] = lambda: session
    lim = limiter if limiter is not None else AsyncMock(return_value=True)
    try:
        with patch("services.rate_limit_service.check_and_increment", new=lim):
            yield TestClient(app, raise_server_exceptions=False), session
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── 1. The ruling: the landing read touches only `shares` ────────────────────

def test_the_landing_read_queries_shares_and_nothing_else():
    """Ruling 1, asserted mechanically rather than by reading the route.

    One statement, against `shares`. No saved_lines, no messages, no personas,
    no counterviews. A future edit that "just" resolves a persona name for the
    page would fail here, which is the point: that edit is what re-couples the
    page to an artifact that can be deleted underneath it.
    """
    with _client(_share()) as (client, session):
        resp = client.get(ENDPOINT)

    assert resp.status_code == 200
    assert len(session.statements) == 1, session.statements
    sql = session.statements[0].lower()
    assert "from shares" in sql
    for table in ("saved_lines", "messages", "personas", "counterviews",
                  "mirrors", "weekly_letters", "quotes", "council_sessions"):
        assert table not in sql, f"the landing read reached into {table}"


def test_a_live_share_returns_its_frozen_text():
    with _client(_share()) as (client, _s):
        resp = client.get(ENDPOINT)

    body = resp.json()
    assert resp.status_code == 200
    assert body["revoked"] is False
    assert body["artifact_type"] == "line"
    assert body["snapshot"]["headline"] == SNAPSHOT.headline
    assert body["snapshot"]["attribution"] == "Marcus Aurelius, in conversation"


# ── 2. Revocation ─────────────────────────────────────────────────────────────

def test_a_revoked_share_is_200_with_no_snapshot():
    """Withdrawn, not missing — and the text does not travel."""
    with _client(_share(revoked=True)) as (client, _s):
        resp = client.get(ENDPOINT)

    body = resp.json()
    assert resp.status_code == 200
    assert body["revoked"] is True
    assert body["snapshot"] is None
    assert SNAPSHOT.headline not in resp.text


def test_an_unknown_id_is_404():
    """Nothing to say about a link that never existed."""
    with _client(None) as (client, _s):
        resp = client.get(ENDPOINT)

    assert resp.status_code == 404


# ── 3. The limiter fails OPEN here, unlike on creation ───────────────────────

def test_the_landing_page_survives_the_limiter_being_down():
    """A stranger opening a link is not the request to sacrifice to a Redis blip.

    The creation routes make the opposite choice and return 503; that asymmetry
    is the whole reason both are written out rather than sharing a helper.
    """
    with _client(_share(), limiter=AsyncMock(side_effect=RuntimeError("redis down"))) as (client, _s):
        resp = client.get(ENDPOINT)

    assert resp.status_code == 200
    assert resp.json()["snapshot"]["headline"] == SNAPSHOT.headline


# ── 4. The analytics identity ────────────────────────────────────────────────

def test_the_landing_view_identity_is_never_the_sharer():
    from routers.public_share import _anon_distinct_id

    anon = _anon_distinct_id(PUBLIC_ID)
    assert anon != USER_ID
    assert PUBLIC_ID not in anon, "the token must not be recoverable from the identity"
    assert anon.startswith("share_"), "must not collide with a real user id namespace"
    assert anon == _anon_distinct_id(PUBLIC_ID), "must be stable, so repeat opens dedupe"
    assert anon != _anon_distinct_id("ZzZzZzZzZzZzZzZzZzZzZz")


def test_a_revoked_share_fires_no_landing_event():
    """A dead end is not an acquisition surface; counting it inflates the funnel."""
    with patch("routers.public_share.analytics_service.track") as track:
        with _client(_share(revoked=True)) as (client, _s):
            client.get(ENDPOINT)
    track.assert_not_called()


def test_a_live_share_fires_one_landing_event_with_the_share_id():
    with patch("routers.public_share.analytics_service.track") as track:
        with _client(_share()) as (client, _s):
            client.get(ENDPOINT)

    track.assert_called_once()
    event, distinct_id, props = track.call_args[0]
    assert event == "share_landing_view"
    assert distinct_id.startswith("share_")
    assert distinct_id != USER_ID
    assert props == {"artifact_type": "line", "share_id": "11111111-0000-0000-0000-000000000001"}
