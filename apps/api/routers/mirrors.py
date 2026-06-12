from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user, get_current_user_plan
from db.session import get_db
from models import Mirror, MirrorSave, Persona, User
from schemas import MirrorOut, RingTrueRequest, MirrorHostOut, MirrorHostsResponse, SetMirrorHostRequest

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


@router.get("/hosts", response_model=MirrorHostsResponse)
async def get_mirror_hosts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Persona).where(Persona.is_active == True))
    personas = result.scalars().all()
    eligible = [p for p in personas if p.config.get("mirror_capable")]
    jung_first = [p for p in eligible if p.slug == "carl_jung"]
    others = sorted([p for p in eligible if p.slug != "carl_jung"], key=lambda p: p.name)
    ordered = jung_first + others
    hosts = [MirrorHostOut(slug=p.slug, name=p.name, portrait_url=p.portrait_url or None) for p in ordered]
    return MirrorHostsResponse(hosts=hosts, selected=user.mirror_host_slug, default="carl_jung")


@router.post("/host", response_model=dict)
async def set_mirror_host(
    body: SetMirrorHostRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Persona).where(Persona.is_active == True))
    personas = result.scalars().all()
    eligible_slugs = {p.slug for p in personas if p.config.get("mirror_capable")}
    if body.host_slug not in eligible_slugs:
        raise HTTPException(status_code=400, detail="Not an eligible mirror host")
    user.mirror_host_slug = body.host_slug
    await db.flush()
    return {"host_slug": body.host_slug}


@router.post("/{mirror_id}/save")
async def save_mirror(
    mirror_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify the mirror belongs to this user
    result = await db.execute(
        select(Mirror).where(Mirror.id == mirror_id, Mirror.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404)

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active
    existing = await db.execute(
        select(MirrorSave).where(
            MirrorSave.user_id == user.id,
            MirrorSave.mirror_id == mirror_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(MirrorSave(user_id=user.id, mirror_id=mirror_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    return {"saved": True}


@router.delete("/{mirror_id}/save")
async def unsave_mirror(
    mirror_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MirrorSave).where(
            MirrorSave.user_id == user.id,
            MirrorSave.mirror_id == mirror_id,
            MirrorSave.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}
