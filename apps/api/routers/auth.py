import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Subscription
from schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut, OtpRequest, OtpVerifyRequest, UpdateMeRequest
from auth import hash_password, verify_password, create_token, get_current_user
from services.analytics_service import analytics_service
from services.otp_service import (
    create_and_send_otp,
    verify_otp,
    OtpInvalid,
    OtpExpired,
    OtpLocked,
)
from services.rate_limit_service import check_and_increment
from services.disclaimer_service import user_needs_acceptance
import stripe
from config import config

router = APIRouter(prefix="/auth", tags=["auth"])
stripe.api_key = config.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    # Create Stripe customer
    customer = stripe.Customer.create(email=body.email, name=body.full_name or "")

    # Create free subscription record
    sub = Subscription(
        user_id=user.id,
        stripe_customer_id=customer.id,
        plan="free",
        status="active",
    )
    db.add(sub)
    await db.commit()

    analytics_service.identify(user.id, {"email": user.email, "plan": "free"})
    analytics_service.track("user_registered", user.id, {"plan": "free"})

    token = create_token(user.id, user.email)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    user_out = UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})
    return TokenResponse(access_token=token, user=user_out)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.email)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    user_out = UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})
    return TokenResponse(access_token=token, user=user_out)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    return UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.full_name = body.full_name
    await db.commit()
    await db.refresh(user)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    return UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})


@router.post("/otp/request", status_code=202)
async def otp_request(body: OtpRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    rate_key = f"otp_request:{email}"

    allowed = await check_and_increment(rate_key, max_count=5, window_seconds=3600)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again in an hour.",
        )

    try:
        await create_and_send_otp(db, email)
    except Exception as e:
        logger.exception(f"OTP request failed for {email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not send code. Please try again.",
        )

    return {"status": "sent"}


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(body: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()

    try:
        await verify_otp(db, email, body.code)
    except OtpLocked:
        raise HTTPException(
            status_code=423,
            detail="Too many wrong attempts. Please request a new code.",
        )
    except OtpExpired:
        raise HTTPException(
            status_code=410,
            detail="Code expired. Please request a new code.",
        )
    except OtpInvalid:
        raise HTTPException(status_code=401, detail="Invalid code.")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=email, hashed_password=None, full_name=None)
        db.add(user)
        await db.flush()
        customer = stripe.Customer.create(email=email)
        sub = Subscription(
            user_id=user.id,
            stripe_customer_id=customer.id,
            plan="free",
            status="active",
        )
        db.add(sub)
        await db.commit()
        analytics_service.identify(user.id, {"email": email, "plan": "free"})
        analytics_service.track("user_registered", user.id, {"plan": "free", "method": "otp"})
    else:
        analytics_service.track("user_signed_in", user.id, {"method": "otp"})

    token = create_token(user.id, user.email)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    user_out = UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})
    return TokenResponse(access_token=token, user=user_out)
