"""The public landing read: GET /s/{public_id}. No authentication.

THIS IS THE ONLY UNAUTHENTICATED ROUTE IN THE PRODUCT THAT RETURNS SOMEONE'S
WRITING, and every decision in this file follows from that sentence.

IT READS THE SNAPSHOT AND NOTHING ELSE. No artifact row, no persona row, no
ownership check, no join. That is a founder ruling and it buys three things: an
artifact can be edited without silently changing what a stranger already saw, an
artifact can be deleted without breaking a link already in circulation, and this
route cannot be turned into an oracle for whether some other id exists.

IT IS SEPARATE FROM share.py BECAUSE ITS PREFIX IS. The creation and revoke
routes hang off /share and require a bearer token; this one is /s, is mounted at
the same API prefix, and requires nothing. Keeping them in one router would mean
one missing dependency away from a private route becoming public, and that is
not a mistake anyone should be able to make in a diff this size.

THE RATE LIMITER FAILS OPEN HERE, AND ONLY HERE. On creation a limiter that
cannot be consulted refuses the request, because minting an unmetered share is a
real cost. Here the request is a stranger opening a link someone sent them: a
Redis blip must not take down the acquisition page. The asymmetry is deliberate
and is the reason both directions are written out in full rather than sharing a
helper that would have to pick one.
"""
import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas import SharePublicResponse, ShareSnapshot
import services.rate_limit_service as rate_limit_service
import services.share_service as share_service
from services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/s", tags=["share-public"])

# Generous, and aimed at enumeration rather than at readers. A share that lands
# in a group chat can legitimately be opened hundreds of times in a minute from
# one egress IP, so this is set where a human audience never reaches it and a
# script walking the keyspace does. 128-bit tokens make that walk hopeless
# anyway; this is the belt to that pair of braces.
LANDING_IP_LIMIT   = 120
LANDING_IP_WINDOW  = 60


def _anon_distinct_id(public_id: str) -> str:
    """The analytics identity for a landing view. NEVER the sharer's user id.

    A landing view is a STRANGER'S act. Attributing it to the person who created
    the share would file other people's browsing under that person's profile —
    and the sharer is often not even among the viewers.

    Derived from the share id by a one-way hash so repeat opens of the same link
    collapse to one identity (which is what makes "how many people opened this"
    answerable) while the value reveals nothing and reverses to nothing useful.
    Prefixed so it can never collide with a real user id in the same namespace.
    """
    return "share_" + hashlib.sha256(f"share:{public_id}".encode()).hexdigest()[:32]


@router.get("/{public_id}", response_model=SharePublicResponse)
async def get_public_share(
    public_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SharePublicResponse:
    """Return a shared artifact's frozen text, or the fact that it was withdrawn.

    A REVOKED SHARE RETURNS 200 WITH NO SNAPSHOT, NOT 404. The page has something
    to say — that the link was turned off — and 404 would render as a broken
    application to someone who has just scanned a friend's card. An unknown id
    still 404s: there is nothing to say about a link that never existed.

    `snapshot` is omitted entirely when revoked rather than sent alongside a flag.
    Revocation withdraws the content; shipping the text with `revoked: true` would
    leave it one devtools tab away from exactly the people it was withdrawn from.
    """
    # ── Fail-open limiter. See the module docstring for why this direction. ──
    try:
        client_ip = (request.client.host if request.client else "unknown")
        await rate_limit_service.check_and_increment(
            key=f"share_landing:{client_ip}",
            max_count=LANDING_IP_LIMIT,
            window_seconds=LANDING_IP_WINDOW,
        )
    except Exception as e:
        # Deliberately swallowed. A stranger opening a link is not the request to
        # sacrifice when Redis is unreachable.
        logger.warning(f"Landing rate limiter unavailable, failing open: {e}")

    share = await share_service.get_public_share(db, public_id=public_id)
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")

    if share.revoked_at is not None:
        # No analytics for a withdrawn link: it is not an acquisition surface and
        # counting it would inflate the funnel with views of a dead end.
        return SharePublicResponse(
            artifact_type=share.artifact_type, revoked=True, snapshot=None,
        )

    analytics_service.track(
        "share_landing_view",
        _anon_distinct_id(share.public_id),
        {"artifact_type": share.artifact_type, "share_id": share.id},
    )

    return SharePublicResponse(
        artifact_type=share.artifact_type,
        revoked=False,
        # Validated on the way out as well as on the way in. A row written by an
        # older version of this code renders or fails loudly; it does not reach
        # the page as a half-shaped object.
        snapshot=ShareSnapshot.model_validate(share.snapshot),
    )
