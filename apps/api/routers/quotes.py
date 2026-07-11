from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
