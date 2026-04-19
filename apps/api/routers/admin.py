from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from db.session import get_db
from models import User, Persona, SafetyEvent, Subscription
from schemas import SafetyEventOut, PersonaOut
from auth import require_admin
from personas import PERSONA_REGISTRY

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/safety-events", response_model=list[SafetyEventOut])
async def list_safety_events(
    risk_level: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = select(SafetyEvent).order_by(SafetyEvent.created_at.desc()).limit(limit)
    if risk_level:
        q = q.where(SafetyEvent.risk_level == risk_level)
    result = await db.execute(q)
    return [SafetyEventOut.model_validate(e) for e in result.scalars().all()]


@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = select(User, Subscription).outerjoin(Subscription, User.id == Subscription.user_id)
    if search:
        q = q.where(User.email.ilike(f"%{search}%"))
    q = q.order_by(User.created_at.desc()).limit(limit)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "plan": s.plan if s else "free",
            "status": s.status if s else "none",
            "created_at": u.created_at,
        }
        for u, s in rows
    ]


@router.get("/analytics/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    paying = (await db.execute(
        select(func.count(Subscription.id))
        .where(Subscription.plan != "free", Subscription.status == "active")
    )).scalar()
    high_safety = (await db.execute(
        select(func.count(SafetyEvent.id)).where(SafetyEvent.risk_level == "high")
    )).scalar()

    return {
        "total_users": total_users,
        "paying_users": paying,
        "conversion_rate": round(paying / total_users * 100, 1) if total_users else 0,
        "high_safety_events": high_safety,
    }


@router.patch("/personas/{persona_id}")
async def update_persona_config(
    persona_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Update persona config JSONB — for tuning without code deploy."""
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    persona.config = {**persona.config, **body}
    await db.flush()
    return {"id": persona.id, "slug": persona.slug, "config": persona.config}
