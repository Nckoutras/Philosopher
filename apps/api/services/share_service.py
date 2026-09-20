"""The share loop: a share becomes an object with a link and an off switch.

WHAT THIS IS FOR. Until PR-1 the six share endpoints rendered a PNG, returned
the bytes and persisted nothing. A share had no identity, so there was nothing
to link to, nothing to attribute a signup to, and nothing to switch off. This
module is where a share acquires all three, and it is deliberately the ONLY
place that does: the six endpoints call create_share and pass the resulting URL
into their existing generator, and that is the whole of their involvement.

WHY ONE SERVICE RATHER THAN SIX ENDPOINTS DOING THE SAME FOUR THINGS. The
endpoints live in four different routers (share.py, council.py, mirrors.py,
weekly_letters.py) and already disagree about small things — three of them
consult a rate-limit counter the other three have never heard of. Six copies of
"limit, snapshot, insert, track" would disagree within a month. The routers get
one call each and no share logic at all.

THE SNAPSHOT IS THE SOURCE OF TRUTH, AND THAT IS THE WHOLE DESIGN.
/s/{public_id} reads `snapshot` and never touches the artifact it came from. So:

  - editing the artifact cannot silently change what a stranger already saw
  - deleting the artifact cannot break a link that is already in circulation
  - the landing page does no ownership check, no persona lookup, no join

The cost is stated in 067's docstring rather than hidden: deleting a reflection
does NOT unpublish a share of it. Turning the link off is a separate act.

REVOCATION WITHDRAWS THE DESTINATION, NOT THE CARD. The card image was handed to
the OS share sheet as a FILE — it is in someone's camera roll or a WhatsApp
thread, and it was never ours to recall. Everything this module does to a
revoked share affects the page the QR points at and nothing else. The user-facing
copy says so explicitly, and it must keep saying so.
"""
import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import config, is_unset_public_url
from models import (
    Counterview,
    CounterviewResponse,
    CouncilCase,
    CouncilResponse,
    CouncilSession,
    Message,
    Mirror,
    Persona,
    Quote,
    SavedLine,
    Share,
    WeeklyLetter,
)
from schemas import ShareSnapshot, ShareVoice
import services.rate_limit_service as rate_limit_service

logger = logging.getLogger(__name__)


# ── Rate limits (founder-locked) ──────────────────────────────────────────────
#
# TWO KEYS, TWO WINDOWS, AND THEY MEASURE DIFFERENT THINGS. The daily cap is
# about volume; the burst cap is about a script or a stuck button. A single
# counter cannot express both — 20/day alone permits 20 in four seconds, and
# 5/min alone permits 7200 a day.
#
# THIS REPLACES FREE_SHARE_LIMIT = 3 per 90 days, which applied to only three of
# the six kinds (line, counterview, quote) and was invisible to council, mirror
# and letter. The new limits apply to all six, which is a tightening for three
# kinds and a large loosening for the other three.
SHARE_DAILY_LIMIT    = 20
SHARE_DAILY_WINDOW   = 24 * 60 * 60
SHARE_BURST_LIMIT    = 5
SHARE_BURST_WINDOW   = 60


class ShareRateLimited(Exception):
    """Raised when a creation limit is hit. `scope` selects the user-facing copy."""

    def __init__(self, scope: str):
        self.scope = scope          # 'daily' | 'burst'
        super().__init__(f"share rate limited ({scope})")


class ShareUnavailable(Exception):
    """The limiter itself could not be consulted — Redis unreachable.

    FAIL CLOSED. A share that is minted without passing the limiter is a share
    the limiter does not know about, and the next one would not know either. The
    public landing route makes the opposite choice, deliberately, and says why
    at its own call site.
    """


def _new_public_id() -> str:
    """22 URL-safe characters, 128 bits.

    secrets, not random: this token is the only thing standing between a
    stranger and someone else's reflection. `random` is seeded predictably and
    is not a security primitive, and the difference is invisible in every test
    that could be written against it.
    """
    return secrets.token_urlsafe(16)


def public_url(public_id: str) -> str:
    """The absolute link that goes on the card and into the QR.

    Built from FRONTEND_URL, which is what every other outbound link in the
    product resolves from (OAuth returns, email links, Stripe returns). Its
    default is localhost:3000, which fails LOUDLY — the config comment above it
    makes the case for that: a URL default that quietly succeeds at the wrong
    thing is worse than one that obviously does not work.
    """
    return f"{config.FRONTEND_URL.rstrip('/')}/s/{public_id}"


async def _enforce_creation_limits(user_id: str) -> None:
    """Both windows, fail closed. Raises ShareRateLimited or ShareUnavailable."""
    try:
        within_burst = await rate_limit_service.check_and_increment(
            key=f"share:burst:{user_id}",
            max_count=SHARE_BURST_LIMIT,
            window_seconds=SHARE_BURST_WINDOW,
        )
        within_day = await rate_limit_service.check_and_increment(
            key=f"share:day:{user_id}",
            max_count=SHARE_DAILY_LIMIT,
            window_seconds=SHARE_DAILY_WINDOW,
        )
    except Exception as e:
        # Fail closed, but as a NAMED failure rather than an uncaught 500. The
        # semantics are what they were; what changes is that the client can tell
        # "you have shared enough today" from "we cannot tell right now", which
        # are different sentences to a reader.
        logger.error(f"Share rate limiter unavailable for user={user_id}: {e}")
        raise ShareUnavailable() from e

    # BURST IS CHECKED AND INCREMENTED FIRST, BOTH COUNTERS ALWAYS. Short-
    # circuiting on the burst failure would leave the daily counter un-incremented
    # for a request the user did make, so someone hammering the button would burn
    # burst allowance while their daily count stood still.
    if not within_burst:
        raise ShareRateLimited("burst")
    if not within_day:
        raise ShareRateLimited("daily")


# ── Snapshot builders — one per kind, all returning the same envelope ─────────
#
# Each mirrors the read its generator already does, and captures TEXT. None of
# them store an id the landing page would have to resolve: a persona renamed or
# retired after the share was created must still render as it did on the day.

async def _snapshot_line(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    saved_line = (await db.execute(
        select(SavedLine).where(
            SavedLine.id == artifact_id,
            SavedLine.user_id == user_id,
            SavedLine.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if not saved_line:
        raise ValueError("Saved line not found")

    msg = (await db.execute(
        select(Message).where(Message.id == saved_line.message_id)
    )).scalar_one_or_none()
    if not msg:
        raise ValueError("Source message not found")

    persona = (await db.execute(
        select(Persona).where(Persona.id == saved_line.persona_id)
    )).scalar_one()

    return ShareSnapshot(
        artifact_type="line",
        headline=msg.content,
        # NOT the card's "{name} told me" — that is the sharer's voice, and the
        # reader of a public page is not the sharer.
        attribution=f"{persona.name}, in conversation",
        persona_slug=persona.slug,
        persona_name=persona.name,
        occurred_at=saved_line.saved_at,
    )


async def _snapshot_quote(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    # Quotes are global, not user-owned — the generator says so too. user_id is
    # accepted for call-site parity and deliberately unused.
    quote = (await db.execute(
        select(Quote).where(Quote.id == artifact_id, Quote.is_active.is_(True))
    )).scalar_one_or_none()
    if quote is None:
        raise ValueError("Quote not found")

    persona = (await db.execute(
        select(Persona).where(Persona.slug == quote.persona_slug)
    )).scalar_one_or_none()
    name = persona.name if persona else quote.persona_slug

    return ShareSnapshot(
        artifact_type="quote",
        headline=quote.text_en,
        attribution=f"{name}, in conversation",
        persona_slug=quote.persona_slug,
        persona_name=name,
    )


async def _snapshot_council(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    session = (await db.execute(
        select(CouncilSession)
        .join(CouncilCase, CouncilSession.case_id == CouncilCase.id)
        .where(CouncilSession.id == artifact_id, CouncilCase.user_id == user_id)
    )).scalar_one_or_none()
    if not session or not session.synthesis:
        raise ValueError("Council session not found or has no synthesis")

    slugs: list[str] = []
    for slug in (await db.execute(
        select(CouncilResponse.persona_slug)
        .where(CouncilResponse.session_id == artifact_id)
        .order_by(CouncilResponse.position)
    )).scalars().all():
        if slug not in slugs:
            slugs.append(slug)
    slugs = slugs[:4]

    by_slug = {}
    if slugs:
        by_slug = {
            p.slug: p for p in
            (await db.execute(select(Persona).where(Persona.slug.in_(slugs)))).scalars().all()
        }

    return ShareSnapshot(
        artifact_type="council",
        headline=session.synthesis,
        attribution="The Council",
        occurred_at=session.created_at,
        # The seats, in order. No verdict text: the card shows the synthesis, and
        # a landing page that showed more than the card would be a different
        # artifact wearing the same link.
        voices=[
            ShareVoice(
                persona_slug=slug,
                persona_name=(by_slug[slug].name if slug in by_slug else slug),
                text="",
            )
            for slug in slugs
        ],
    )


async def _snapshot_mirror(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    mirror = (await db.execute(
        select(Mirror).where(Mirror.id == artifact_id, Mirror.user_id == user_id)
    )).scalar_one_or_none()
    if mirror is None:
        raise ValueError("Mirror not found")

    thread = (mirror.payload or {}).get("thread")
    if not thread:
        raise ValueError("Mirror has no reflection to share")

    persona = None
    if mirror.host_persona_id:
        persona = (await db.execute(
            select(Persona).where(Persona.id == mirror.host_persona_id)
        )).scalar_one_or_none()

    return ShareSnapshot(
        artifact_type="mirror",
        headline=thread,
        attribution=(f"{persona.name}, in conversation" if persona else "The Wise Room"),
        persona_slug=(persona.slug if persona else None),
        persona_name=(persona.name if persona else None),
        occurred_at=mirror.created_at,
    )


async def _snapshot_letter(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    letter = (await db.execute(
        select(WeeklyLetter).where(
            WeeklyLetter.id == artifact_id,
            WeeklyLetter.user_id == user_id,
        )
    )).scalar_one_or_none()
    if letter is None or letter.status != "generated":
        raise ValueError("Letter not found")

    pull_quote = (letter.payload or {}).get("pull_quote")
    if not pull_quote:
        raise ValueError("Letter has no quote to share")

    persona = None
    if letter.voice_persona_id:
        persona = (await db.execute(
            select(Persona).where(Persona.id == letter.voice_persona_id)
        )).scalar_one_or_none()

    return ShareSnapshot(
        artifact_type="letter",
        headline=pull_quote,
        attribution=(f"{persona.name}, in conversation" if persona else "The Wise Room"),
        persona_slug=(persona.slug if persona else None),
        persona_name=(persona.name if persona else None),
        occurred_at=letter.created_at,
    )


async def _snapshot_counterview(db: AsyncSession, artifact_id: str, user_id: str) -> ShareSnapshot:
    cv = (await db.execute(
        select(Counterview).where(
            Counterview.id == artifact_id,
            Counterview.user_id == user_id,
            Counterview.status == "generated",
        )
    )).scalar_one_or_none()
    if cv is None:
        raise ValueError("Counterview not found or not shareable")

    responses = (await db.execute(
        select(CounterviewResponse)
        .where(
            CounterviewResponse.counterview_id == artifact_id,
            CounterviewResponse.round == 0,
        )
        .order_by(CounterviewResponse.position.asc())
    )).scalars().all()
    if len(responses) < 2:
        raise ValueError("Counterview has no case to share")

    left, right = responses[0], responses[1]
    by_slug = {
        p.slug: p for p in
        (await db.execute(
            select(Persona).where(Persona.slug.in_([left.persona_slug, right.persona_slug]))
        )).scalars().all()
    }

    def _name(slug: str) -> str:
        p = by_slug.get(slug)
        return p.name if p else slug

    return ShareSnapshot(
        artifact_type="counterview",
        # The belief the two voices are arguing about — the framing, not a verdict.
        headline=cv.title or cv.anchor_text or "",
        attribution="Counterview",
        occurred_at=cv.created_at,
        voices=[
            ShareVoice(persona_slug=r.persona_slug, persona_name=_name(r.persona_slug), text=r.verdict)
            for r in (left, right)
        ],
    )


_BUILDERS = {
    "line": _snapshot_line,
    "quote": _snapshot_quote,
    "council": _snapshot_council,
    "mirror": _snapshot_mirror,
    "letter": _snapshot_letter,
    "counterview": _snapshot_counterview,
}


async def build_snapshot(
    db: AsyncSession, *, artifact_type: str, artifact_id: str, user_id: str,
) -> ShareSnapshot:
    """Freeze one artifact's text. Raises ValueError if absent or not owned.

    OWNERSHIP IS CHECKED HERE, not only in the generator. The generator's check
    guards the image; this one guards the ROW, and the row outlives the image.
    Each builder carries the same WHERE clause its generator uses, so a share
    cannot be minted for something whose card would refuse to render.
    """
    builder = _BUILDERS.get(artifact_type)
    if builder is None:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
    return await builder(db, artifact_id, user_id)


async def create_share(
    db: AsyncSession, *, artifact_type: str, artifact_id: str, user_id: str,
) -> Share:
    """Limit, snapshot, insert, track. The only way a share is created.

    Raises ShareRateLimited, ShareUnavailable, or ValueError (unknown/unowned
    artifact) — the routers map each to its own status code and copy.

    THE LIMIT IS CHECKED BEFORE THE SNAPSHOT. The snapshot is several queries; a
    caller who is already over their limit should not pay for them, and should
    not be able to use a refused share as a way to probe whether an artifact id
    exists.
    """
    # ── TD-77's rule, applied to the third outbound-link builder ─────────────
    #
    # REFUSE TO MINT A CARD WHOSE LINK WOULD BE DEAD. The URL is composed from
    # FRONTEND_URL and then PAINTED INTO THE PNG — into the QR and the printed
    # line both. Everything else in this feature survives a wrong env var:
    # nothing composed is stored, so the row, "Your links" and the data export
    # all come out right the moment the variable is corrected. The card does
    # not. It has already gone to the OS share sheet as a file, into a camera
    # roll or a message thread, and it is no more recallable than anything else
    # this module refuses to pretend it can recall.
    #
    # WHY REFUSING, WHERE THE EMAIL PATHS SUPPRESS AND RETRY. cron.py can mark a
    # letter pending and send it once FRONTEND_URL is fixed, because the letter
    # has not left yet. A share is synchronous: by the time anyone notices, the
    # card is in someone else's hands. There is no later here, so the only safe
    # direction is not to produce it.
    #
    # BEFORE THE LIMITER, deliberately. This request cannot succeed whatever the
    # counters say, and burning a person's daily allowance on it would charge
    # them for our misconfiguration.
    if is_unset_public_url(config.FRONTEND_URL):
        logger.error(
            "Share creation REFUSED — FRONTEND_URL is localhost/unset (%r), so the "
            "QR and printed link on the card would be dead. Nothing was minted. "
            "This is config, not user error: set FRONTEND_URL to the public "
            "frontend URL on Render. user_id=%s",
            config.FRONTEND_URL, user_id,
        )
        raise ShareUnavailable()

    await _enforce_creation_limits(user_id)

    snapshot = await build_snapshot(
        db, artifact_type=artifact_type, artifact_id=artifact_id, user_id=user_id,
    )

    share = Share(
        public_id=_new_public_id(),
        user_id=user_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        snapshot=snapshot.model_dump(mode="json"),
    )
    db.add(share)
    await db.flush()

    # share_created is NOT tracked here, deliberately. It fires from
    # routers/share.py:create_and_render, AFTER the commit and after the card has
    # actually rendered — an event should describe something that happened, and
    # until both of those succeed nothing has. Firing at flush time would record
    # shares that a later rollback erased, and cards the person never received.
    # test_share_created_fires_from_exactly_one_place pins the count at one.
    return share


async def revoke_share(db: AsyncSession, *, public_id: str, user_id: str) -> bool:
    """Turn a link off. Idempotent. False when the share is not this user's.

    The row is NOT deleted: a revoked share must still resolve so the page can
    say it was withdrawn. A 404 reads as a broken application to someone who has
    just scanned a friend's card, which is the opposite of what a withdrawal
    should feel like.
    """
    share = (await db.execute(
        select(Share).where(Share.public_id == public_id, Share.user_id == user_id)
    )).scalar_one_or_none()
    if share is None:
        return False
    if share.revoked_at is None:
        share.revoked_at = datetime.now(timezone.utc)
        await db.flush()
    return True


async def list_shares(db: AsyncSession, *, user_id: str, limit: int = 100) -> list[Share]:
    """Every link this person has made, newest first. Revoked ones included.

    REVOKED ROWS STAY IN THE LIST, muted and actionless in the UI. Seeing that
    you turned a link off IS the confirmation that you did — a list that silently
    dropped them would leave a person wondering whether the tap registered, which
    is the same uncertainty revocation exists to remove.

    Ordered to match ix_shares_user_created exactly, so this is an index scan
    rather than a sort. `limit` is a guard against an unbounded response, not a
    pagination scheme: there is no cursor in v1 because 20 shares a day is the
    ceiling and nobody has 100 links yet. When someone does, this needs a cursor
    rather than a bigger number.
    """
    return list((await db.execute(
        select(Share)
        .where(Share.user_id == user_id)
        .order_by(Share.created_at.desc())
        .limit(limit)
    )).scalars().all())


async def get_public_share(db: AsyncSession, *, public_id: str) -> Share | None:
    """The landing page's only read. No auth, no ownership, no join.

    Returns the row even when revoked — the caller decides what to withhold, and
    withholding is its job rather than this one's.
    """
    return (await db.execute(
        select(Share).where(Share.public_id == public_id)
    )).scalar_one_or_none()
