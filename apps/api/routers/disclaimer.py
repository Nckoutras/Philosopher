from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from db.session import get_db
from models import User
from schemas import DisclaimerAcceptRequest, DisclaimerAcceptOut, DisclaimerCurrentOut
from services.disclaimer_service import (
    accept,
    get_current_version,
    NoVersionAvailable,
    user_needs_acceptance,
)

router = APIRouter(prefix="/disclaimer", tags=["disclaimer"])


@router.get("/current", response_model=DisclaimerCurrentOut)
async def get_current_disclaimer(db: AsyncSession = Depends(get_db)):
    try:
        version = await get_current_version(db)
    except NoVersionAvailable:
        raise HTTPException(status_code=503, detail="No disclaimer version available")
    return DisclaimerCurrentOut(
        version_string=version.version_string,
        age_copy=version.age_copy,
        positioning_copy=version.positioning_copy,
    )


@router.post("/accept", response_model=DisclaimerAcceptOut)
async def accept_disclaimer(
    body: DisclaimerAcceptRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.confirmed_age_18:
        raise HTTPException(status_code=400, detail="Age confirmation (confirmed_age_18) is required")
    if not body.confirmed_non_therapy:
        raise HTTPException(status_code=400, detail="Non-therapy confirmation (confirmed_non_therapy) is required")

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    user_agent = request.headers.get("user-agent")

    acceptance = await accept(
        user_id=user.id,
        confirmed_age_18=body.confirmed_age_18,
        confirmed_non_therapy=body.confirmed_non_therapy,
        locale=body.locale or "en",
        ip_address=ip_address,
        user_agent=user_agent,
        db=db,
    )

    version = await get_current_version(db)
    return DisclaimerAcceptOut(
        accepted_at=acceptance.accepted_at,
        version_string=version.version_string,
    )
