from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
from models import CouncilCase, CouncilSave, CouncilSession
from schemas import CouncilCreate
from services.council_service import council_service

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

    source = body.source if body.source in ("direct", "mirror") else "direct"

    # Weekly rate limit: 1 per source per week. Admins bypass (for testing).
    remaining = None
    if not user.is_admin:
        remaining = await council_service.weekly_remaining(db, user.id, source)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"error_code": "council_weekly_limit"},
                headers={
                    "X-RateLimit-Limit": "1",
                    "X-RateLimit-Remaining": "0",
                },
            )

    response_headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    if remaining is not None:
        response_headers["X-RateLimit-Limit"] = "1"
        response_headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))

    return StreamingResponse(
        council_service.stream_council(
            db=db,
            user_id=user.id,
            matter=matter,
            source=source,
            mirror_id=body.mirror_id,
        ),
        media_type="text/event-stream",
        headers=response_headers,
    )


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
