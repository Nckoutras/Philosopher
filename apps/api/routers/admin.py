from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from db.session import get_db
from models import User, Persona, SafetyEvent, Subscription, Conversation, Message
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


@router.post("/backfill-titles")
async def backfill_titles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """One-shot: enqueue title generation for all conversations missing a title.

    W1 confirmed: uses existing require_admin dependency (user.is_admin column exists).
    Run once after deploy via: POST /admin/backfill-titles with admin JWT.
    """
    arq_queue = getattr(request.app.state, "arq_queue", None)
    if arq_queue is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ARQ queue not available")

    result = await db.execute(
        select(Conversation.id)
        .where(
            Conversation.message_count >= 6,
            Conversation.title.is_(None),
        )
    )
    conv_ids = [str(row[0]) for row in result.all()]

    for conv_id in conv_ids:
        await arq_queue.enqueue_job("generate_conversation_title", conv_id)

    return {"queued": len(conv_ids)}


@router.post("/mirror/generate")
async def trigger_mirror_generate(
    request: Request,
    user_id: str = Query(...),
    persona_slug: str = Query(...),
    days: int = Query(7),
    _: User = Depends(require_admin),
):
    arq_queue = getattr(request.app.state, "arq_queue", None)
    if arq_queue is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ARQ queue not available")
    await arq_queue.enqueue_job("generate_weekly_mirror_task", user_id, persona_slug, "weekly", days)
    return {"enqueued": True, "user_id": user_id, "persona_slug": persona_slug}


@router.post("/generate-weekly-letter")
async def trigger_weekly_letter_generate(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger immediate weekly-letter generation for the current admin user.

    Determines the voice persona by the same most-conversed-this-week logic as the
    Sunday cron. Falls back to enqueueing with no slug (task will produce 'empty')
    when the admin has no messages in the last 7 days.
    """
    from datetime import datetime, timezone, timedelta
    from fastapi import HTTPException

    arq_queue = getattr(request.app.state, "arq_queue", None)
    if arq_queue is None:
        raise HTTPException(status_code=503, detail="ARQ queue not available")

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(
            Conversation.persona_id,
            func.count(Message.id).label("msg_count"),
        )
        .join(Message, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == admin.id,
            Message.role == "user",
            Message.created_at >= cutoff,
        )
        .group_by(Conversation.persona_id)
        .order_by(func.count(Message.id).desc(), Conversation.persona_id.asc())
        .limit(1)
    )
    row = result.first()

    voice_persona_slug = None
    if row:
        p_result = await db.execute(select(Persona.slug).where(Persona.id == str(row.persona_id)))
        voice_persona_slug = p_result.scalar_one_or_none()

    if voice_persona_slug is None:
        voice_persona_slug = "carl_jung"  # safe fallback; task will gate on <5 messages

    await arq_queue.enqueue_job("generate_weekly_letter_task", str(admin.id), voice_persona_slug)
    return {"enqueued": True, "voice_persona_slug": voice_persona_slug}


@router.post("/generate-monthly-letter")
async def trigger_monthly_letter_generate(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger immediate monthly 'season' letter generation for the current admin.

    Picks the voice persona by most-conversed-this-CALENDAR-MONTH (mirrors the
    last-of-month cron). The task gates on MONTHLY_MIN_MESSAGES, so a thin month
    yields an 'empty' letter and no email.
    """
    from datetime import datetime, timezone
    from fastapi import HTTPException

    arq_queue = getattr(request.app.state, "arq_queue", None)
    if arq_queue is None:
        raise HTTPException(status_code=503, detail="ARQ queue not available")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(
            Conversation.persona_id,
            func.count(Message.id).label("msg_count"),
        )
        .join(Message, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == admin.id,
            Message.role == "user",
            Message.created_at >= month_start,
        )
        .group_by(Conversation.persona_id)
        .order_by(func.count(Message.id).desc(), Conversation.persona_id.asc())
        .limit(1)
    )
    row = result.first()

    voice_persona_slug = None
    if row:
        p_result = await db.execute(select(Persona.slug).where(Persona.id == str(row.persona_id)))
        voice_persona_slug = p_result.scalar_one_or_none()

    if voice_persona_slug is None:
        voice_persona_slug = "marcus_aurelius"  # safe fallback; task gates on MONTHLY_MIN_MESSAGES

    await arq_queue.enqueue_job("generate_monthly_letter_task", str(admin.id), voice_persona_slug)
    return {"enqueued": True, "voice_persona_slug": voice_persona_slug}


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
