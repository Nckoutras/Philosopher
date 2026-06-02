from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models import User
from schemas import SelfModelStatusOut
from auth import get_current_user, get_current_user_plan
from services.self_model_service import self_model_service
from services.self_comparison_service import self_comparison_service

router = APIRouter(prefix="/self-comparison", tags=["self-comparison"])

PROMPT_MAX_CHARS = 600


class SelfComparisonCreate(BaseModel):
    prompt: str = Field(..., max_length=PROMPT_MAX_CHARS)


@router.get("/status", response_model=SelfModelStatusOut)
async def get_self_comparison_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await self_model_service.build(db, user.id)
    return SelfModelStatusOut(**data)


@router.post("")
async def create_self_comparison(
    body: SelfComparisonCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    prompt = (body.prompt or "").strip()
    if not prompt:
        return JSONResponse(status_code=400, content={"error_code": "empty_prompt"})

    if not user.is_admin:
        remaining = await self_comparison_service.weekly_remaining(db, user.id)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"error_code": "weekly_limit"},
                headers={"X-RateLimit-Limit": str(5), "X-RateLimit-Remaining": "0"},
            )

    return StreamingResponse(
        self_comparison_service.stream(db=db, user_id=user.id, prompt=prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
