from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import User
from schemas import SavedLineCreate, SavedLineOut, SavedLineRead, SavedLineListResponse
from auth import get_current_user
from services.saved_lines_service import (
    saved_lines_service,
    FreeSavesLimitError,
    SavedLineNotFoundError,
    MessageNotFoundError,
    MessageRoleError,
    SavedLineAlreadyExistsError,
    FREE_SAVE_LIMIT,
)
from services.tier_service import get_user_tier

router = APIRouter(prefix="/saved-lines", tags=["saved-lines"])


@router.post("", response_model=SavedLineOut, status_code=201)
async def create_saved_line(
    body: SavedLineCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        saved_line = await saved_lines_service.create(db, user.id, body.message_id)
    except MessageNotFoundError:
        raise HTTPException(status_code=404, detail="Message not found")
    except MessageRoleError:
        raise HTTPException(status_code=400, detail="Only persona replies can be saved")
    except SavedLineAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Already saved")
    except FreeSavesLimitError as e:
        return JSONResponse(
            status_code=402,
            content={
                "detail": "Free tier save limit reached",
                "code": "free_saves_limit",
                "limit": e.limit,
                "current_count": e.current_count,
            },
        )
    return SavedLineOut.model_validate(saved_line)


@router.get("", response_model=SavedLineListResponse)
async def list_saved_lines(
    persona_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items_raw = await saved_lines_service.list_for_user(db, user.id, persona_id=persona_id)
    items = [SavedLineRead.model_validate(item) for item in items_raw]
    tier = await get_user_tier(db, UUID(user.id))
    return SavedLineListResponse(
        items=items,
        total_count=len(items),
        free_tier_limit=FREE_SAVE_LIMIT if tier == "free" else None,
    )


@router.delete("/{saved_line_id}", status_code=204)
async def delete_saved_line(
    saved_line_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await saved_lines_service.delete(db, user.id, saved_line_id)
    except SavedLineNotFoundError:
        raise HTTPException(status_code=404, detail="Saved line not found")
