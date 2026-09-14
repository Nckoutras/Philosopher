from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
import services.rate_limit_service as rate_limit_service
from models import CouncilCase, CouncilSave, CouncilSession
from schemas import CouncilCreate
from services.council_service import council_service, _iso_week_start
from services.analytics_service import analytics_service
from services.image_service import generate_council_share_image

FREE_SHARE_LIMIT  = 3
SHARE_WINDOW_SECS = 90 * 24 * 60 * 60   # 90 days rolling


class CouncilShareRequest(BaseModel):
    annotation: Optional[str] = Field(None, max_length=140)

router = APIRouter(prefix="/council", tags=["council"])

MATTER_MAX_CHARS = 600


@router.post("")
async def create_council(
    request: Request,
    body: CouncilCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth

    # Pro gate (council is Pro-only; BETA flag makes everyone "pro" for now)
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    matter = (body.matter or "").strip()
    if not matter:
        return JSONResponse(status_code=400, content={"error_code": "empty_matter"})

    if len(matter) > MATTER_MAX_CHARS:
        return JSONResponse(status_code=400, content={"error_code": "matter_too_long"})

    source = body.source if body.source in ("direct", "mirror", "chat", "nudge") else "direct"

    # Weekly rate limit: 1 per source per week. Admins bypass (for testing).
    # Reset is the start of the NEXT ISO week — same Monday-00:00-UTC boundary the
    # limit itself counts from, reused from the service rather than recomputed here.
    reset_at = _iso_week_start() + timedelta(days=7)
    remaining = None
    if not user.is_admin:
        remaining = await council_service.weekly_remaining(db, user.id, source)
        if remaining <= 0:
            # The sixth cap call site. cap_kind is "council", NOT "pro_fair_use":
            # this is a different ceiling with different semantics — one council
            # per source per week, a product shape rather than a cost control —
            # and constants.py keeps cap_kind precisely so two ceilings that mean
            # different things never average together in the dashboard. `tier` is
            # the resolved plan from get_current_user_plan, the same value the
            # other five sites pass. Admins bypass the limit entirely, so they
            # emit nothing here, exactly as they trigger nothing.
            analytics_service.track("usage_cap_hit", user.id, {
                "tier": plan,
                "cap_kind": "council",
                "path": "council",
            })
            return JSONResponse(
                status_code=429,
                content={"error_code": "council_weekly_limit"},
                headers={
                    "X-RateLimit-Limit": "1",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": reset_at.isoformat(),
                },
            )

    response_headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    if remaining is not None:
        response_headers["X-RateLimit-Limit"] = "1"
        response_headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        response_headers["X-RateLimit-Reset"] = reset_at.isoformat()

    # AFTER every refusal path, and after the normalisation above — both
    # deliberate, and both fixes to this line rather than incidental placement.
    #
    # It used to fire before the 400 (matter_too_long) and the 429, so every
    # refused attempt counted as a started council. The funnel this event exists
    # to feed is council_started -> council_completed, and a numerator inflated
    # by requests the server never even attempted makes that ratio read as a
    # generation failure. A started council now means one that started.
    #
    # And it sends the NORMALISED `source`, not `body.source`. The raw field is
    # client-supplied — the web writes it from sessionStorage — so the event used
    # to carry whatever arrived, while the DB and the rate limiter saw the
    # membership-checked value two lines up. The event now agrees with them.
    #
    # `matter` is the user's question, in their own words. It is the single most
    # sensitive string on this route and it NEVER becomes a property — not
    # truncated, not hashed, not "just the first few words". source is the whole
    # payload.
    # `used_memory` is deliberately NOT here. council_service passes
    # memories=[] unconditionally (council_service.py:227) — the council never
    # consults memory — so the property would be a hardcoded False on every
    # event. A constant is not a measurement; worse, a dashboard reading
    # "used_memory: false, 100%" invites the conclusion that memory does not
    # help the council, when the truth is that the council never asks.
    # used_memory returns with Memory v2 (P1), when the council actually
    # consults memory.
    analytics_service.track("council_started", user.id, {"source": source})

    arq_queue = getattr(request.app.state, "arq_queue", None)

    return StreamingResponse(
        council_service.stream_council(
            db=db,
            user_id=user.id,
            matter=matter,
            source=source,
            mirror_id=body.mirror_id,
            conversation_id=body.conversation_id,
            matter_edited=body.matter_edited,
            arq_queue=arq_queue,
        ),
        media_type="text/event-stream",
        headers=response_headers,
    )


@router.get("/brief/{conversation_id}")
async def council_display_brief(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """Display-only summary of a chat conversation, first-person in the user's voice,
    for prefilling the Council matter textarea. Pro-gated soft-null (mirrors
    /quotes/suggested): free users get {"brief": null}. Never changes what the
    council members deliberate. Returns {"brief": string | null}."""
    user, plan = auth
    if plan not in ("pro", "premium"):
        return {"brief": None}
    brief = await council_service.display_brief(db, user.id, conversation_id)
    return {"brief": brief}


@router.post("/{session_id}/save")
async def save_council_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, _plan = auth

    # Verify the session belongs to a case owned by this user
    result = await db.execute(
        select(CouncilSession)
        .join(CouncilCase, CouncilSession.case_id == CouncilCase.id)
        .where(
            CouncilSession.id == session_id,
            CouncilCase.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        return JSONResponse(status_code=404, content={"error_code": "session_not_found"})

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active
    existing = await db.execute(
        select(CouncilSave).where(
            CouncilSave.user_id == user.id,
            CouncilSave.session_id == session_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(CouncilSave(user_id=user.id, session_id=session_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    analytics_service.track("council_saved", user.id, {})
    return {"saved": True}


@router.delete("/{session_id}/save")
async def unsave_council_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, _plan = auth

    result = await db.execute(
        select(CouncilSave).where(
            CouncilSave.user_id == user.id,
            CouncilSave.session_id == session_id,
            CouncilSave.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}


@router.post("/{session_id}/share")
async def share_council_session(
    session_id: str,
    body: CouncilShareRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """
    Generate a share image for a council session synthesis.
    Returns raw image/png bytes.
    Free tier: max 3 per 90-day rolling window (shared counter with line shares).
    Pro/premium: unlimited.
    """
    user, plan = auth

    if plan not in ("pro", "premium"):
        allowed = await rate_limit_service.check_and_increment(
            key=f"share_screenshot:{user.id}",
            max_count=FREE_SHARE_LIMIT,
            window_seconds=SHARE_WINDOW_SECS,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error_code": "share_limit_reached"},
            )

    try:
        png_bytes = await generate_council_share_image(
            db=db,
            session_id=session_id,
            user_id=user.id,
            annotation=body.annotation,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # See routers/share.py for why artifact_type is the only property.
    analytics_service.track("share_created", user.id, {"artifact_type": "council"})

    return Response(content=png_bytes, media_type="image/png")
