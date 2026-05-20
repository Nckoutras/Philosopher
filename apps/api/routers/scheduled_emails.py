"""POST / GET / DELETE /api/v1/scheduled-emails"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models import ScheduledEmail, SavedLine, Persona, User
from schemas import ScheduledEmailCreate, ScheduledEmailOut, ScheduledEmailListItem
from auth import get_current_user
from services.tier_service import get_user_tier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled-emails", tags=["scheduled-emails"])


@router.post("", response_model=ScheduledEmailOut, status_code=201)
async def create_scheduled_email(
    body: ScheduledEmailCreate,
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

    row = ScheduledEmail(
        user_id=user.id,
        saved_line_id=body.saved_line_id,
        persona_id=saved_line.persona_id,
        note=body.note,
        recipient_email=recipient,
        scheduled_for=body.scheduled_for,
        status="pending",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("Scheduled email created id=%s user=%s for=%s", row.id, user.id, row.scheduled_for)
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
