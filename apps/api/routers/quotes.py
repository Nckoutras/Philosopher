from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.session import get_db
from models import Quote
from schemas import QuoteOut
from auth import get_current_user_plan

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("", response_model=list[QuoteOut])
async def list_quotes(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    # Auth required (same as personas); no tier gate. No ordering — the client shuffles.
    result = await db.execute(select(Quote).where(Quote.is_active == True))
    return result.scalars().all()


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
