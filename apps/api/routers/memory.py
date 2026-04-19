from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, MemoryEntry, Insight
from schemas import MemoryEntryOut, MemoryEntryUpdate, InsightOut
from auth import get_current_user

memory_router = APIRouter(prefix="/memory", tags=["memory"])
insights_router = APIRouter(prefix="/insights", tags=["insights"])


# ── Memory ────────────────────────────────────────────────────────────────────

@memory_router.get("", response_model=list[MemoryEntryOut])
async def get_memory(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user.id, MemoryEntry.is_active == True)
        .order_by(MemoryEntry.created_at.desc())
        .limit(100)
    )
    return [MemoryEntryOut.model_validate(m) for m in result.scalars().all()]


@memory_router.patch("/{memory_id}", response_model=MemoryEntryOut)
async def update_memory(
    memory_id: str,
    body: MemoryEntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == memory_id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404)
    if body.content is not None:
        entry.content = body.content
    if body.is_active is not None:
        entry.is_active = body.is_active
    await db.flush()
    return MemoryEntryOut.model_validate(entry)


@memory_router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == memory_id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404)
    entry.is_active = False


# ── Insights ──────────────────────────────────────────────────────────────────

@insights_router.get("", response_model=list[InsightOut])
async def get_insights(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user.id, Insight.is_dismissed == False)
        .order_by(Insight.created_at.desc())
        .limit(20)
    )
    return [InsightOut.model_validate(i) for i in result.scalars().all()]


@insights_router.patch("/{insight_id}/dismiss", status_code=204)
async def dismiss_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404)
    insight.is_dismissed = True
