from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
import services.rate_limit_service as rate_limit_service
from services.image_service import generate_share_image, generate_counterview_share_image

router = APIRouter(prefix="/share", tags=["share"])

FREE_SHARE_LIMIT   = 3
SHARE_WINDOW_SECS  = 90 * 24 * 60 * 60   # 90 days rolling


class ShareScreenshotRequest(BaseModel):
    saved_line_id: UUID
    annotation: Optional[str] = Field(None, max_length=140)


class ShareCounterviewRequest(BaseModel):
    counterview_id: UUID


@router.post("/screenshot")
async def create_share_screenshot(
    body: ShareScreenshotRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """
    Generate a 1080×1080 share image for the given saved line.
    Returns raw image/png bytes.
    Free tier: max 3 per 90-day rolling window (Redis counter).
    Pro/premium: unlimited.
    """
    user, plan = auth

    if plan not in ("pro", "premium"):
        allowed = await rate_limit_service.check_and_increment(
            key=f"share_screenshot:{user.id}",
            max_count=FREE_SHARE_LIMIT,
            window_seconds=SHARE_WINDOW_SECS,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error_code": "share_limit_reached"},
            )

    try:
        png_bytes = await generate_share_image(
            db=db,
            saved_line_id=str(body.saved_line_id),
            user_id=user.id,
            annotation=body.annotation,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(content=png_bytes, media_type="image/png")


@router.post("/counterview")
async def create_share_counterview(
    body: ShareCounterviewRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """
    Generate a 1080×1350 share image for the given counterview.
    Returns raw image/png bytes.
    Free tier: max 3 per 90-day rolling window (shared counter with line shares).
    Pro/premium: unlimited.
    """
    user, plan = auth

    if plan not in ("pro", "premium"):
        allowed = await rate_limit_service.check_and_increment(
            key=f"share_screenshot:{user.id}",
            max_count=FREE_SHARE_LIMIT,
            window_seconds=SHARE_WINDOW_SECS,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error_code": "share_limit_reached"},
            )

    try:
        png_bytes = await generate_counterview_share_image(
            db=db,
            counterview_id=str(body.counterview_id),
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(content=png_bytes, media_type="image/png")
