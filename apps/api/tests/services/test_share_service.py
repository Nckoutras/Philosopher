"""The share loop's service layer: token, limits, snapshot envelope, revocation.

The landing route's own guarantees are in tests/routers/test_public_share.py;
this file is about what happens before a link exists.
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

import services.share_service as share_service
from models import Share
from schemas import ShareSnapshot, ShareVoice


# ── The token ────────────────────────────────────────────────────────────────

def test_the_token_is_22_urlsafe_characters():
    """128 bits, and the shape the column is sized to.

    VARCHAR(22) is exactly len(secrets.token_urlsafe(16)); a scheme change that
    produced a different length would be silently truncated by Postgres or
    rejected, so the length is pinned here where the reason is written down.
    """
    for _ in range(200):
        tok = share_service._new_public_id()
        assert len(tok) == 22
        assert re.fullmatch(r"[A-Za-z0-9_-]{22}", tok), tok


def test_tokens_do_not_repeat():
    """Not a proof of entropy — a smoke alarm for a seeded or truncated scheme.

    A real collision at 128 bits will not happen; a scheme that accidentally
    became 4 characters, or that used `random` seeded per process, would show up
    here immediately.
    """
    seen = {share_service._new_public_id() for _ in range(5000)}
    assert len(seen) == 5000


def test_the_public_url_points_at_the_landing_route():
    url = share_service.public_url("AbCdEfGhIjKlMnOpQrStUv")
    assert url.endswith("/s/AbCdEfGhIjKlMnOpQrStUv")
    assert "//" in url and url.count("/s/") == 1


# ── The two rate-limit windows ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_both_windows_are_always_incremented():
    """Burst first, and the daily counter is incremented even when burst fails.

    Short-circuiting would let someone hammering the button burn burst allowance
    while their daily count stood still — they would be refused all day for
    requests that were never counted against the day.
    """
    limiter = AsyncMock(return_value=False)
    with patch("services.share_service.rate_limit_service.check_and_increment", new=limiter):
        with pytest.raises(share_service.ShareRateLimited):
            await share_service._enforce_creation_limits("user-1")

    keys = [c.kwargs["key"] for c in limiter.call_args_list]
    assert keys == ["share:burst:user-1", "share:day:user-1"]


@pytest.mark.asyncio
async def test_the_burst_window_is_reported_as_burst():
    limiter = AsyncMock(side_effect=[False, True])
    with patch("services.share_service.rate_limit_service.check_and_increment", new=limiter):
        with pytest.raises(share_service.ShareRateLimited) as e:
            await share_service._enforce_creation_limits("user-1")
    assert e.value.scope == "burst"


@pytest.mark.asyncio
async def test_the_daily_window_is_reported_as_daily():
    limiter = AsyncMock(side_effect=[True, False])
    with patch("services.share_service.rate_limit_service.check_and_increment", new=limiter):
        with pytest.raises(share_service.ShareRateLimited) as e:
            await share_service._enforce_creation_limits("user-1")
    assert e.value.scope == "daily"


@pytest.mark.asyncio
async def test_an_unreachable_limiter_fails_closed():
    """Creation refuses rather than minting an unmetered share.

    The public landing route makes the opposite choice; see its own test.
    """
    limiter = AsyncMock(side_effect=RuntimeError("redis down"))
    with patch("services.share_service.rate_limit_service.check_and_increment", new=limiter):
        with pytest.raises(share_service.ShareUnavailable):
            await share_service._enforce_creation_limits("user-1")


@pytest.mark.asyncio
async def test_the_limit_is_checked_before_the_snapshot_is_built():
    """Two reasons, and the second is the one worth a test.

    A caller who is already over their limit should not pay for several queries;
    and, more importantly, they must not be able to use a refused share as an
    oracle for whether an artifact id exists.
    """
    builder = AsyncMock()
    limiter = AsyncMock(return_value=False)
    with patch("services.share_service.rate_limit_service.check_and_increment", new=limiter), \
         patch("services.share_service.build_snapshot", new=builder):
        with pytest.raises(share_service.ShareRateLimited):
            await share_service.create_share(
                AsyncMock(), artifact_type="line", artifact_id="x", user_id="u",
            )
    builder.assert_not_called()


# ── The snapshot envelope ────────────────────────────────────────────────────

def test_the_envelope_is_versioned():
    """A JSONB blob with no schema rots, and this one has to outlive the link."""
    s = ShareSnapshot(artifact_type="line", headline="x", attribution="y")
    assert s.v == 1
    assert s.model_dump(mode="json")["v"] == 1


def test_a_snapshot_round_trips_through_json():
    """What goes into JSONB must come back out as the same object.

    The landing route re-validates on read, so a field that serialises to
    something the model rejects would render as a 500 on a public page.
    """
    original = ShareSnapshot(
        artifact_type="counterview",
        headline="Restraint is wisdom.",
        attribution="Counterview",
        occurred_at=datetime(2026, 9, 20, 8, 9, tzinfo=timezone.utc),
        voices=[
            ShareVoice(persona_slug="miyamoto_musashi", persona_name="Miyamoto Musashi", text="Cut."),
            ShareVoice(persona_slug="niccolo_machiavelli", persona_name="Niccolò Machiavelli", text="Wait."),
        ],
    )
    revived = ShareSnapshot.model_validate(original.model_dump(mode="json"))
    assert revived == original
    assert revived.voices[1].persona_name == "Niccolò Machiavelli"


def test_every_artifact_type_has_a_builder():
    """The CHECK constraint and the builder map must not drift apart.

    A kind the database accepts but nothing can snapshot would fail at share
    time; a kind with a builder the database rejects would fail at INSERT.
    """
    from schemas import ShareArtifactType
    import typing
    declared = set(typing.get_args(ShareArtifactType))
    assert set(share_service._BUILDERS) == declared


@pytest.mark.asyncio
async def test_an_unknown_artifact_type_is_refused():
    with pytest.raises(ValueError):
        await share_service.build_snapshot(
            AsyncMock(), artifact_type="diary", artifact_id="x", user_id="u",
        )


def test_the_landing_attribution_is_not_the_cards():
    """Copy ruling 3: the card is first-person, the landing page is not.

    The card says "Marcus Aurelius told me" because the sharer is its reader.
    A stranger opening the link is not the sharer, so the same words would be a
    lie in their mouth. Pinned because it is the kind of difference a later
    refactor "tidies" into one string.

    STRING LITERALS ONLY, not the whole file. An earlier version of this test
    grepped the source text and failed on the COMMENT four lines above the code
    it was checking — which explains that the card says "told me" and the
    snapshot must not. A comment saying "do not do X" is not an instance of X.
    """
    import ast
    tree = ast.parse(open(share_service.__file__, encoding="utf-8").read())
    literals = [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    # Docstrings are string literals too, and carry the same explanation, so
    # they are excluded by shape: multi-line, or long.
    code_literals = [
        lit for lit in literals
        if chr(10) not in lit and len(lit) < 120
    ]
    assert any(", in conversation" in lit for lit in code_literals),         "the landing attribution wording is gone"
    leaked = [lit for lit in code_literals if "told me" in lit]
    assert not leaked, f"the card's first-person wording leaked into a snapshot: {leaked}"


# ── Revocation ───────────────────────────────────────────────────────────────

class _OneShareSession:
    def __init__(self, share):
        self._share = share
        self.flushed = 0

    async def execute(self, stmt, *a, **kw):
        class _R:
            def __init__(self, one):
                self._one = one

            def scalar_one_or_none(self):
                return self._one

        return _R(self._share)

    async def flush(self):
        self.flushed += 1


def _share():
    return Share(
        id="11111111-0000-0000-0000-000000000001",
        public_id="AbCdEfGhIjKlMnOpQrStUv",
        user_id="u",
        artifact_type="line",
        artifact_id="22222222-0000-0000-0000-000000000001",
        snapshot={"v": 1, "artifact_type": "line", "headline": "x", "attribution": "y"},
        revoked_at=None,
    )


@pytest.mark.asyncio
async def test_revoking_sets_the_timestamp_and_keeps_the_row():
    """The row SURVIVES. A deleted row would 404, and a withdrawn link has
    something to say."""
    share = _share()
    db = _OneShareSession(share)
    ok = await share_service.revoke_share(db, public_id=share.public_id, user_id="u")
    assert ok is True
    assert share.revoked_at is not None
    assert share.snapshot, "revocation must not destroy the row's content"


@pytest.mark.asyncio
async def test_revoking_twice_is_idempotent_and_keeps_the_first_timestamp():
    """Someone tapping twice must not move the record of when they withdrew it."""
    share = _share()
    db = _OneShareSession(share)
    await share_service.revoke_share(db, public_id=share.public_id, user_id="u")
    first = share.revoked_at
    await share_service.revoke_share(db, public_id=share.public_id, user_id="u")
    assert share.revoked_at == first
    assert db.flushed == 1, "the second revoke must not write"


@pytest.mark.asyncio
async def test_revoking_someone_elses_share_reports_not_found():
    """False, which the router turns into 404 rather than 403.

    Whether a given public_id exists is not something a caller should learn by
    trying to revoke it.
    """
    db = _OneShareSession(None)
    ok = await share_service.revoke_share(db, public_id="AbCdEfGhIjKlMnOpQrStUv", user_id="someone-else")
    assert ok is False
