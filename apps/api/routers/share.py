"""Share endpoints: three creation routes, the public landing read, and revoke.

WHAT CHANGED IN PR-1. These endpoints used to render a PNG and return the bytes,
persisting nothing — so there was no link to put on the card, nothing to attribute
a later signup to, and nothing to turn off. Now every creation route mints a
`shares` row first and passes its URL into the generator, which stamps it on the
card as a QR and a printed link.

ALL SIX KINDS GO THROUGH ONE HELPER, `_create_and_render`, and the other three
kinds live in their own resource routers (council.py, mirrors.py,
weekly_letters.py) and call the same one. That is deliberate: before this PR the
six endpoints already disagreed — three consulted a rate-limit counter the other
three had never heard of, so a council share was unlimited on the free tier while
a quote share was capped at three per quarter. Six copies of "limit, snapshot,
insert, track, render" would drift again within a month.

THE OLD LIMIT IS GONE. FREE_SHARE_LIMIT = 3 per 90 days applied to three of the
six kinds and only to free users. It is replaced by 20/day + 5/min for everyone,
across all six — a tightening for the three that were uncapped and a large
loosening for the three that were capped at three a quarter.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
from schemas import ShareListItem, ShareListResponse
import services.share_service as share_service
from services.analytics_service import analytics_service
from services.image_service import (
    generate_share_image,
    generate_counterview_share_image,
    generate_quote_share_image,
)

router = APIRouter(prefix="/share", tags=["share"])


class ShareScreenshotRequest(BaseModel):
    saved_line_id: UUID
    annotation: Optional[str] = Field(None, max_length=140)


class ShareCounterviewRequest(BaseModel):
    counterview_id: UUID


class ShareQuoteRequest(BaseModel):
    quote_id: UUID


# ── The one creation path, used by all six kinds ──────────────────────────────

# Three error codes, because the client has three different sentences to show and
# a bare 500 gives it nothing to choose with.
_RATE_LIMIT_CODES = {
    "daily": "share_rate_limited_daily",
    "burst": "share_rate_limited_burst",
}


async def create_and_render(
    *,
    db: AsyncSession,
    user_id: str,
    artifact_type: str,
    artifact_id: str,
    generator,
    **generator_kwargs,
) -> Response:
    """Mint the share, render the card with its link on it, return the PNG.

    Exported (no underscore) because council.py, mirrors.py and weekly_letters.py
    call it too — the three kinds whose endpoints live on their own resource
    routers. Keeping the body here rather than duplicating it there is the whole
    reason the six kinds cannot drift apart again.

    THE ROW IS CREATED BEFORE THE IMAGE, and it has to be: the card cannot carry
    a link that does not exist yet. The cost is that a generator failure leaves a
    row for a card nobody received — acceptable, because `shares` rows are cheap,
    carry no user-visible state until someone opens the link, and the alternative
    is a card whose QR leads nowhere.
    """
    try:
        share = await share_service.create_share(
            db, artifact_type=artifact_type, artifact_id=artifact_id, user_id=user_id,
        )
    except share_service.ShareRateLimited as e:
        return JSONResponse(
            status_code=429, content={"error_code": _RATE_LIMIT_CODES[e.scope]},
        )
    except share_service.ShareUnavailable:
        # Fail closed. The limiter could not be consulted, so no share is minted
        # — see share_service.ShareUnavailable for why that is the safe direction
        # here and the wrong one on the public landing route.
        return JSONResponse(
            status_code=503, content={"error_code": "share_unavailable"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    url = share_service.public_url(share.public_id)

    try:
        png_bytes = await generator(
            db=db, user_id=user_id, share_url=url, **generator_kwargs,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()

    # The share's own id travels with the event so share_created and
    # share_landing_view can be joined into a funnel. Before the shares table
    # there was nothing to join on.
    analytics_service.track(
        "share_created", user_id,
        {"artifact_type": artifact_type, "share_id": share.id},
    )

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"X-Share-Id": share.public_id, "X-Share-Url": url},
    )


@router.post("/screenshot")
async def create_share_screenshot(
    body: ShareScreenshotRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """Mint a share for a saved line and return its 1080×1350 card."""
    user, _plan = auth
    return await create_and_render(
        db=db, user_id=user.id,
        artifact_type="line", artifact_id=str(body.saved_line_id),
        generator=generate_share_image,
        saved_line_id=str(body.saved_line_id), annotation=body.annotation,
    )


@router.post("/counterview")
async def create_share_counterview(
    body: ShareCounterviewRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """Mint a share for a counterview and return its 1080×1350 card."""
    user, _plan = auth
    return await create_and_render(
        db=db, user_id=user.id,
        artifact_type="counterview", artifact_id=str(body.counterview_id),
        generator=generate_counterview_share_image,
        counterview_id=str(body.counterview_id),
    )


@router.post("/quote")
async def create_share_quote(
    body: ShareQuoteRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """Mint a share for a corpus quote and return its 1080×1350 card."""
    user, _plan = auth
    return await create_and_render(
        db=db, user_id=user.id,
        artifact_type="quote", artifact_id=str(body.quote_id),
        generator=generate_quote_share_image,
        quote_id=str(body.quote_id),
    )


# ── Your links ────────────────────────────────────────────────────────────────

@router.get("/mine", response_model=ShareListResponse)
async def list_my_shares(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> ShareListResponse:
    """The links this person has made. Revoked ones included, muted in the UI.

    THIS ROUTE EXISTS SO THAT REVOCATION DOES. Without a list, "Turn off this
    link" has nowhere to live: the share id is known to the client only in the
    moment the card is returned, so a person could revoke during that one modal
    and never again. Revocation would have been real in the API and absent from
    the product.

    It carries no view statistics, per ruling — this is an inventory, not a
    dashboard.

    DECLARED BEFORE /{public_id}/revoke ON PURPOSE. FastAPI matches routes in
    declaration order, and "mine" is a valid public_id shape; registered the
    other way round, a POST to /share/mine/revoke would be readable as a share
    whose id is the literal string "mine". It cannot happen today because the
    methods differ, but the ordering costs nothing and removes the question.
    """
    user, _plan = auth
    shares = await share_service.list_shares(db, user_id=user.id)
    return ShareListResponse(items=[
        ShareListItem(
            public_id=sh.public_id,
            url=share_service.public_url(sh.public_id),
            artifact_type=sh.artifact_type,
            created_at=sh.created_at,
            revoked=sh.revoked_at is not None,
        )
        for sh in shares
    ])


# ── Signup attribution (PR-2) ────────────────────────────────────────────────

class ShareAttributeRequest(BaseModel):
    # Length-and-alphabet only. Whether it names a real share is decided by the
    # database, not by a validator — a stricter shape here would reject some
    # forged values with a 422 and accept others with a 204, which is the
    # response difference this endpoint exists to avoid.
    share_id: str = Field(min_length=22, max_length=22, pattern=r"^[A-Za-z0-9_-]{22}$")


@router.post("/attribute", status_code=204)
async def attribute_share_signup(
    body: ShareAttributeRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """Attribute a brand-new account to the share that brought it. Always 204.

    WHY THIS IS AN ENDPOINT AND NOT PART OF SIGNUP. On the OAuth path the account
    is created in the server-to-server callback from Google — there is no browser
    at that moment, so nothing can read the localStorage the share id lives in.
    Attribution therefore has to happen after the redirect lands, and once it
    does, the same shape serves OTP for free. The two creation paths in auth.py
    and auth_oauth.py are untouched by this PR.

    It also means an attribution failure can never break a signup or a redirect,
    which is the reason the OAuth path already wraps its own analytics in a
    try/except.

    204 IN EVERY CASE, INCLUDING EVERY FAILURE. Unknown share, revoked share,
    self-referral, already-attributed, and a well-formed token that names
    nothing — all answer identically, with no body and no status difference. A
    response that varied would turn this into an oracle for probing whether a
    given share_id exists, which is exactly what an unguessable token is for.
    Reasons are logged server-side only.

    THE CLIENT DOES NOT GET TO SAY HOW IT SIGNED UP. `method` is derived from
    user.auth_provider, because a client-supplied value is attacker-controlled
    and this one lands in the funnel.
    """
    user, _plan = auth
    share = await share_service.attribute_signup(db, user=user, public_id=body.share_id)
    if share is None:
        return Response(status_code=204)

    await db.commit()

    # 'google' for OAuth accounts, NULL for OTP ones — set at creation in
    # auth_oauth.py and never written by the OTP path.
    method = "google" if user.auth_provider == "google" else "otp"
    analytics_service.track(
        "share_signup", user.id,
        {"share_id": share.id, "artifact_type": share.artifact_type, "method": method},
    )
    return Response(status_code=204)


# ── Revocation ────────────────────────────────────────────────────────────────

@router.post("/{public_id}/revoke", status_code=204)
async def revoke_share(
    public_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """Turn a share link off. Idempotent.

    WITHDRAWS THE DESTINATION, NOT THE CARD, and no copy anywhere in this feature
    may suggest otherwise. The image was handed to the OS share sheet as a FILE —
    it is in a camera roll or a message thread, and it was never ours to recall.
    What this does is make the QR on it lead to a page that says the link was
    withdrawn.

    404 rather than 403 for someone else's share: whether a given public_id
    exists is not something a caller should be able to learn by trying to revoke
    it.
    """
    user, _plan = auth
    ok = await share_service.revoke_share(db, public_id=public_id, user_id=user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Share not found")
    await db.commit()
    return Response(status_code=204)
