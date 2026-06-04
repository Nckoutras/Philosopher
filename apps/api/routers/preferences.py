from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from db.session import get_db
from models import User
from schemas import PreferenceUpsertRequest, PreferenceOut, MatchOut
from services.preferences_service import (
    get_user_preferences,
    upsert_preferences,
)
from services.matching_service import compute_matches

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.post("", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
async def upsert_user_preferences(
    body: PreferenceUpsertRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save (insert or replace) the current user's onboarding preferences."""
    record = await upsert_preferences(
        user_id=user.id,
        themes=body.themes,
        other_text=body.other_text,
        need_most=body.need_most,
        db=db,
    )
    return record


@router.get("", response_model=PreferenceOut)
async def read_user_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's preferences, or 404 if not yet set."""
    record = await get_user_preferences(user_id=user.id, db=db)
    if record is None:
        raise HTTPException(status_code=404, detail="Preferences not set")
    return record


@router.get(
    "/matches",
    response_model=list[MatchOut],
    summary="Get top 3 persona matches based on saved preferences",
)
async def get_matches(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MatchOut]:
    """Compute persona matches based on the user's saved preferences.

    Returns 404 if the user hasn't completed the questionnaire yet.
    """
    prefs = await get_user_preferences(user_id=user.id, db=db)
    if prefs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete the questionnaire first to see your matches.",
        )

    matches = compute_matches(
        user_themes=prefs.themes,
        user_need_most=prefs.need_most,
        top_n=9,
    )

    return [
        MatchOut(slug=m.slug, score=m.score, reason=m.reason)
        for m in matches
    ]
