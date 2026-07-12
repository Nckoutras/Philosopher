from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.session import get_db
from models import Quote, Insight, SavedQuote
from schemas import QuoteOut, SuggestedQuoteOut
from auth import get_current_user_plan
from services.preferences_service import get_user_preferences
from services.quote_suggest import rank_suggested_quotes

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("", response_model=list[QuoteOut])
async def list_quotes(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Auth required (same as personas); no tier gate. No ordering — the client shuffles.
    result = await db.execute(select(Quote).where(Quote.is_active == True))
    return result.scalars().all()


# Registered BEFORE the '/{quote_id}/...' routes so 'suggested' is never captured
# as a quote_id path param.
@router.get("/suggested", response_model=list[SuggestedQuoteOut])
async def suggested(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    # Pro-gated nudge: free users get NO personalized suggestion.
    if plan not in ("pro", "premium"):
        return []
    prefs = await get_user_preferences(user_id=user.id, db=db)
    if prefs is None:
        return []
    # Live chat-signal theme (3a): the most recent non-dismissed Insight with a
    # theme in the last 14 days. None → the ranker falls back to 5b/5c behaviour.
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    sig = await db.execute(
        select(Insight.theme).where(
            Insight.user_id == user.id,
            Insight.is_dismissed == False,
            Insight.theme.isnot(None),
            Insight.created_at >= cutoff,
        ).order_by(Insight.created_at.desc()).limit(1)
    )
    signal_theme = sig.scalar_one_or_none()
    quotes = (await db.execute(select(Quote).where(Quote.is_active == True))).scalars().all()
    ranked = rank_suggested_quotes(prefs, quotes, signal_theme=signal_theme, limit=5)
    return [
        SuggestedQuoteOut(**QuoteOut.model_validate(q).model_dump(), matched_themes=mt)
        for q, mt in ranked
    ]


@router.get("/saved", response_model=list[str])
async def list_saved_quote_ids(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Registered BEFORE the '/{quote_id}/...' routes so 'saved' is never captured
    # as a quote_id. Returns the user's active (non-soft-deleted) saved quote ids
    # for the button's saved-state. Saving is free — no tier gate.
    user, _plan = auth
    result = await db.execute(
        select(SavedQuote.quote_id).where(
            SavedQuote.user_id == user.id,
            SavedQuote.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.post("/{quote_id}/discuss", status_code=204)
async def increment_discuss(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Single atomic UPDATE (column self-reference) — no read-modify-write, no race.
    # Auth present, no tier gate: any authenticated tap is a valid demand signal.
    # Order: execute → check rowcount → 404 BEFORE commit. A miss is a no-op UPDATE
    # (nothing written), so the 404 path needs no commit and no rollback.
    result = await db.execute(
        update(Quote)
        .where(Quote.id == quote_id)
        .values(discuss_count=Quote.discuss_count + 1)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="quote_not_found")
    await db.commit()


@router.post("/{quote_id}/story", status_code=204)
async def increment_story(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    result = await db.execute(
        update(Quote)
        .where(Quote.id == quote_id)
        .values(story_count=Quote.story_count + 1)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="quote_not_found")
    await db.commit()


@router.post("/{quote_id}/save")
async def save_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Saving is free (no tier gate). Quotes are global, so verify EXISTENCE only
    # (no ownership check) → 404 if the quote is missing.
    user, _plan = auth
    exists = await db.execute(select(Quote.id).where(Quote.id == quote_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="quote_not_found")

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active.
    existing = await db.execute(
        select(SavedQuote).where(
            SavedQuote.user_id == user.id,
            SavedQuote.quote_id == quote_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        db.add(SavedQuote(user_id=user.id, quote_id=quote_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    return {"saved": True}


@router.delete("/{quote_id}/save")
async def unsave_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Soft-delete the active save. Idempotent: unsaving a not-saved quote is a no-op.
    user, _plan = auth
    result = await db.execute(
        select(SavedQuote).where(
            SavedQuote.user_id == user.id,
            SavedQuote.quote_id == quote_id,
            SavedQuote.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}
