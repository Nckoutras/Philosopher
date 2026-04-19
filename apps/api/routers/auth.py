from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Subscription
from schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
from auth import hash_password, verify_password, create_token, get_current_user
from services.analytics_service import analytics_service
import stripe
from config import config

router = APIRouter(prefix="/auth", tags=["auth"])
stripe.api_key = config.STRIPE_SECRET_KEY


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
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
