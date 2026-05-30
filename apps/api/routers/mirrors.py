from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user, get_current_user_plan
from db.session import get_db
from models import Mirror, Persona, User
from schemas import MirrorOut, RingTrueRequest

router = APIRouter(prefix="/mirrors", tags=["mirrors"])


def _mirror_out(mirror: Mirror, persona: Persona | None) -> MirrorOut:
    return MirrorOut(
        id=mirror.id,
        kind=mirror.kind,
        status=mirror.status,
        period_start=mirror.period_start,
        period_end=mirror.period_end,
        host_persona_slug=persona.slug if persona else None,
        host_persona_name=persona.name if persona else None,
        payload=mirror.payload,
        ring_true=mirror.ring_true,
        ring_true_note=mirror.ring_true_note,
        created_at=mirror.created_at,
    )


async def _load_persona(db: AsyncSession, persona_id: str | None) -> Persona | None:
    if not persona_id:
        return None
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    return result.scalar_one_or_none()


@router.get("/latest", response_model=MirrorOut | None)
async def get_latest_mirror(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    stmt = (
        select(Mirror)
        .where(Mirror.user_id == user.id, Mirror.status == "generated")
        .order_by(Mirror.created_at.desc())
        .limit(1)
    )
    if plan == "free":
        stmt = stmt.where(Mirror.kind == "preview")
    result = await db.execute(stmt)
    mirror = result.scalar_one_or_none()
    if mirror is None:
        return None
    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)


@router.post("/{mirror_id}/ring-true", response_model=MirrorOut)
async def set_ring_true(
    mirror_id: str,
    body: RingTrueRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Mirror).where(Mirror.id == mirror_id, Mirror.user_id == user.id)
    )
    mirror = result.scalar_one_or_none()
    if mirror is None:
        raise HTTPException(status_code=404)
    mirror.ring_true = body.ring_true
    mirror.ring_true_note = body.note
    mirror.ring_true_at = datetime.now(timezone.utc)
    await db.flush()
    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)
