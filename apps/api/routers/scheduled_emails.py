"""POST / GET / PATCH / DELETE /api/v1/scheduled-emails"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models import ScheduledEmail, SavedLine, Persona, User
from schemas import (
    ScheduledEmailCreate,
    ScheduledEmailOut,
    ScheduledEmailListItem,
    ScheduledEmailDetail,
    ScheduledEmailReviewIn,
)
from auth import get_current_user
from services.tier_service import get_user_tier
from services.safety_service import safety_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled-emails", tags=["scheduled-emails"])


@router.post("", response_model=ScheduledEmailOut, status_code=201)
async def create_scheduled_email(
    body: ScheduledEmailCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScheduledEmailOut:
    """Pro only. Creates a pending scheduled_emails row.

    persona_id is derived server-side from saved_line.persona_id — never
    accepted from the client to prevent mismatches.
    """
    tier = await get_user_tier(db, UUID(user.id))
    if tier == "free":
        raise HTTPException(status_code=403, detail="Pro subscription required")

    sl_result = await db.execute(
        select(SavedLine).where(
            SavedLine.id == body.saved_line_id,
            SavedLine.user_id == user.id,
            SavedLine.deleted_at.is_(None),
        )
    )
    saved_line = sl_result.scalar_one_or_none()
    if saved_line is None:
        raise HTTPException(status_code=404, detail="Saved line not found")

    recipient = body.recipient_email or user.email

    # Optional prediction (043): a guess about the future, surfaced only on the
    # in-app arrived screen. Safety-gated before persist — unlike the note, which
    # is unchecked, a prediction is a durable self-statement we don't want to store
    # if it trips the distress gate.
    prediction = (body.prediction or "").strip() or None
    if prediction is not None:
        res = await safety_service.check_input(prediction, user.id)
        if res.should_suppress_persona:
            return JSONResponse(status_code=422, content={"error_code": "unsafe_prediction"})

    row = ScheduledEmail(
        user_id=user.id,
        saved_line_id=body.saved_line_id,
        persona_id=saved_line.persona_id,
        note=body.note,
        prediction=prediction,
        recipient_email=recipient,
        scheduled_for=body.scheduled_for,
        status="pending",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("Scheduled email created id=%s user=%s for=%s", row.id, user.id, row.scheduled_for)

    # The note is the user's OWN words to their future self — distil it into a
    # confidence-1.0 memory (safety-gated + word-filtered inside the task). Async,
    # NOTE only (never the prediction or letter metadata). Fire-and-forget; an
    # enqueue failure must never break letter creation.
    note = (body.note or "").strip()
    if note:
        arq_queue = getattr(request.app.state, "arq_queue", None)
        if arq_queue is not None:
            try:
                await arq_queue.enqueue_job(
                    "distill_user_text_to_memory_task",
                    str(user.id),
                    None,
                    note,
                    "future_self_note",
                )
            except Exception as exc:
                logger.error("Future-self note enqueue failed user=%s: %s", user.id, exc)

    return ScheduledEmailOut.model_validate(row)


@router.get("", response_model=list[ScheduledEmailListItem])
async def list_scheduled_emails(
    status: Optional[str] = Query(None, pattern="^(pending|sent|failed|cancelled)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ScheduledEmailListItem]:
    """All tiers. Returns only the caller's own rows, joined with persona."""
    q = (
        select(
            ScheduledEmail.id,
            ScheduledEmail.persona_id,
            Persona.name.label("persona_name"),
            Persona.portrait_url.label("persona_portrait_url"),
            ScheduledEmail.scheduled_for,
            ScheduledEmail.status,
            ScheduledEmail.sent_at,
            ScheduledEmail.created_at,
        )
        .join(Persona, ScheduledEmail.persona_id == Persona.id)
        .where(ScheduledEmail.user_id == user.id)
        .order_by(ScheduledEmail.scheduled_for.asc())
    )
    if status:
        q = q.where(ScheduledEmail.status == status)

    result = await db.execute(q)
    rows = result.mappings().all()
    return [ScheduledEmailListItem.model_validate(dict(row)) for row in rows]


@router.get("/{email_id}", response_model=ScheduledEmailDetail)
async def get_scheduled_email(
    email_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScheduledEmailDetail:
    """The in-app arrived-letter screen. Owner-scoped and DELIVERED-only.

    404 unless the row belongs to the caller AND status='sent' — a pending row
    is invisible as a detail (peek prevention: the note never surfaces before
    delivery). Joins persona for the attribution + thumbnail.
    """
    q = (
        select(
            ScheduledEmail.id,
            ScheduledEmail.persona_id,
            Persona.name.label("persona_name"),
            Persona.portrait_url.label("persona_portrait_url"),
            ScheduledEmail.note,
            ScheduledEmail.prediction,
            ScheduledEmail.review_text,
            ScheduledEmail.review_at,
            ScheduledEmail.scheduled_for,
            ScheduledEmail.status,
            ScheduledEmail.sent_at,
            ScheduledEmail.created_at,
        )
        .join(Persona, ScheduledEmail.persona_id == Persona.id)
        .where(
            ScheduledEmail.id == email_id,
            ScheduledEmail.user_id == user.id,
            ScheduledEmail.status == "sent",
        )
    )
    result = await db.execute(q)
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Scheduled email not found")
    return ScheduledEmailDetail.model_validate(dict(row))


@router.patch("/{email_id}/review", response_model=ScheduledEmailDetail)
async def review_scheduled_email(
    email_id: str,
    body: ScheduledEmailReviewIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The reader's review on open ("what happened"). Owner-scoped and
    DELIVERED-only (404 unless the row belongs to the caller AND status='sent').
    No tier check. One review per letter — re-submitting overwrites. Empty→422.
    Safety-gated before persist. No LLM. Returns the updated detail.
    """
    text = body.text.strip()
    if not text:
        return JSONResponse(status_code=422, content={"error_code": "empty_review"})

    res = await safety_service.check_input(text, user.id)
    if res.should_suppress_persona:
        return JSONResponse(status_code=422, content={"error_code": "unsafe_review"})

    result = await db.execute(
        select(ScheduledEmail).where(
            ScheduledEmail.id == email_id,
            ScheduledEmail.user_id == user.id,
            ScheduledEmail.status == "sent",
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return JSONResponse(status_code=404, content={"error_code": "not_found"})

    row.review_text = text
    row.review_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Future-self review saved id=%s user=%s", email_id, user.id)

    # Re-read with the persona join so the response matches GET /{id} exactly.
    detail_q = (
        select(
            ScheduledEmail.id,
            ScheduledEmail.persona_id,
            Persona.name.label("persona_name"),
            Persona.portrait_url.label("persona_portrait_url"),
            ScheduledEmail.note,
            ScheduledEmail.prediction,
            ScheduledEmail.review_text,
            ScheduledEmail.review_at,
            ScheduledEmail.scheduled_for,
            ScheduledEmail.status,
            ScheduledEmail.sent_at,
            ScheduledEmail.created_at,
        )
        .join(Persona, ScheduledEmail.persona_id == Persona.id)
        .where(ScheduledEmail.id == email_id)
    )
    detail_row = (await db.execute(detail_q)).mappings().one()
    return ScheduledEmailDetail.model_validate(dict(detail_row))


@router.delete("/{email_id}", status_code=204)
async def cancel_scheduled_email(
    email_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Soft-cancel: sets status='cancelled'. Preserves audit trail.

    404 if not found or belongs to another user.
    409 if status is not 'pending'.
    """
    result = await db.execute(
        select(ScheduledEmail).where(
            ScheduledEmail.id == email_id,
            ScheduledEmail.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Scheduled email not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending emails can be cancelled")
    row.status = "cancelled"
    await db.commit()
    logger.info("Scheduled email cancelled id=%s user=%s", email_id, user.id)
