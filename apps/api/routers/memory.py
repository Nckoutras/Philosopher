from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, MemoryEntry, Insight
from schemas import MemoryEntryOut, MemoryEntryUpdate, InsightOut, MirrorOut
from auth import get_current_user
from services.insight_mirror_service import generate_insight_mirror
# Reuse the mirrors router's serializer + persona loader so the insight-mirror
# response stays a 1:1 match with /mirrors (one source of truth, no drift).
from routers.mirrors import _mirror_out, _load_persona

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
    conversation_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Insight)
        .where(Insight.user_id == user.id, Insight.is_dismissed == False)
    )
    if conversation_id is not None:
        query = query.where(Insight.conversation_id == conversation_id)
    query = query.order_by(Insight.created_at.desc()).limit(20)
    result = await db.execute(query)
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


@insights_router.post("/{insight_id}/reflect", response_model=MirrorOut)
async def reflect_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate (or return the existing) insight-seeded mirror for this insight.
    Synchronous — the caller waits for generation. Status 'empty'/'suppressed'
    is returned as a clean 200 (with null payload) for the frontend to handle,
    not an error."""
    try:
        mirror = await generate_insight_mirror(db, user.id, insight_id)
    except ValueError:
        raise HTTPException(status_code=404)

    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)
