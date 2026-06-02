from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from models import User
from schemas import SelfModelStatusOut
from auth import get_current_user
from services.self_model_service import self_model_service

router = APIRouter(prefix="/self-comparison", tags=["self-comparison"])


@router.get("/status", response_model=SelfModelStatusOut)
async def get_self_comparison_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await self_model_service.build(db, user.id)
    return SelfModelStatusOut(**data)
