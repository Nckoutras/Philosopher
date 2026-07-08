from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models import User, SelfComparison, SelfComparisonSave
from schemas import SelfModelStatusOut
from auth import get_current_user, get_current_user_plan
from services.self_model_service import self_model_service
from services.self_comparison_service import self_comparison_service, weekly_limit

router = APIRouter(prefix="/self-comparison", tags=["self-comparison"])

PROMPT_MAX_CHARS = 600


class SelfComparisonCreate(BaseModel):
    prompt: str = Field(..., max_length=PROMPT_MAX_CHARS)


class RingTrueUpdate(BaseModel):
    ring_true: str = Field(..., max_length=10)
    note: Optional[str] = Field(None, max_length=280)


@router.get("/status", response_model=SelfModelStatusOut)
async def get_self_comparison_status(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    data = await self_model_service.build(db, user.id, bypass_gate=user.is_admin)
    data["plan"] = plan
    if data.get("unlocked"):
        data["weekly_remaining"] = await self_comparison_service.weekly_remaining(db, user.id, plan)
        data["weekly_limit"] = weekly_limit(plan)
    elif data.get("forming_preview"):
        # Surface a warm, short, second-person reflection instead of the raw
        # third-person memory signals (which read robotically and say "user").
        data["forming_preview"] = await self_comparison_service.forming_reflection(data["forming_preview"])
    return SelfModelStatusOut(**data)


@router.post("")
async def create_self_comparison(
    body: SelfComparisonCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    if plan not in ("pro", "premium") and not user.is_admin:
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    prompt = (body.prompt or "").strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"error_code": "empty_prompt"})

    if not user.is_admin:
        remaining = await self_comparison_service.weekly_remaining(db, user.id, plan)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"error_code": "weekly_limit"},
                headers={"X-RateLimit-Limit": str(weekly_limit(plan)), "X-RateLimit-Remaining": "0"},
            )

    return StreamingResponse(
        self_comparison_service.stream(db=db, user_id=user.id, prompt=prompt, bypass_gate=user.is_admin),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.patch("/{comparison_id}/ring-true", status_code=204)
async def set_ring_true(
    comparison_id: str,
    body: RingTrueUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SelfComparison).where(
            SelfComparison.id == comparison_id,
            SelfComparison.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404)
    row.ring_true = body.ring_true
    row.ring_true_note = body.note
    row.ring_true_at = datetime.now(timezone.utc)


@router.post("/{comparison_id}/save")
async def save_self_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify the comparison belongs to this user (mirrors counterview save).
    result = await db.execute(
        select(SelfComparison).where(
            SelfComparison.id == comparison_id,
            SelfComparison.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404)

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active.
    existing = await db.execute(
        select(SelfComparisonSave).where(
            SelfComparisonSave.user_id == user.id,
            SelfComparisonSave.self_comparison_id == comparison_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(SelfComparisonSave(user_id=user.id, self_comparison_id=comparison_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    return {"saved": True}


@router.delete("/{comparison_id}/save")
async def unsave_self_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SelfComparisonSave).where(
            SelfComparisonSave.user_id == user.id,
            SelfComparisonSave.self_comparison_id == comparison_id,
            SelfComparisonSave.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}
