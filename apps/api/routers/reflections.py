from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from db.session import get_db
from models import User
from schemas import ReflectionsFeedResponse
from services.reflections_feed_service import reflections_feed_service

router = APIRouter(prefix="/reflections", tags=["reflections"])


@router.get("/feed", response_model=ReflectionsFeedResponse)
async def get_reflections_feed(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unified, saved_at-desc feed of saved lines + saved Mirror/Council verdicts."""
    items = await reflections_feed_service.get_feed(db, user.id)
    return ReflectionsFeedResponse(items=items)
