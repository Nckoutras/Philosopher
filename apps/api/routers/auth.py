import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Subscription
from schemas import TokenResponse, UserOut, OtpRequest, OtpVerifyRequest, UpdateMeRequest
from auth import create_token, get_current_user
from services.analytics_service import analytics_service
from services.otp_service import (
    create_and_send_otp,
    verify_otp,
    OtpInvalid,
    OtpExpired,
    OtpLocked,
)
from services.rate_limit_service import check_and_increment, check_deep_mode_limit
from services.disclaimer_service import user_needs_acceptance
import stripe
from config import config

router = APIRouter(prefix="/auth", tags=["auth"])
stripe.api_key = config.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Slide the session: mint a fresh token for an already-authenticated user.

    A11. JWT expiry runs from ISSUE, not from last use, and there is no refresh
    anywhere — so a user who opens the app every day is still logged out on day 7
    and has to fetch an email code. In a habit product that is a churn event on
    roughly the cadence of the ritual itself.

    Authentication is get_current_user and nothing more: it already 401s on an
    expired or malformed token and already confirms the user still exists, so a
    deleted user cannot refresh and an expired one must sign in again. No new
    validation, no schema, no revocation semantics (see A16).

    The response is the SAME TokenResponse the four mint sites return, so the
    frontend feeds it straight into the existing setToken() — which updates the
    in-memory token, localStorage, AND the middleware cookie in one place.
    """
    token = create_token(user.id, user.email, user.token_version)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    user_out = UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})
    return TokenResponse(access_token=token, user=user_out)


@router.post("/signout-all", status_code=204)
async def signout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke every token this user holds, on every device (A16).

    Increments users.token_version. Both validators compare a token's "ver" claim
    against that column, so from the next request onward every previously-issued
    token 401s — including pre-A16 tokens, whose missing claim reads as 0 and no
    longer matches.

    THIS KILLS THE CALLING TOKEN TOO. There is no "all except this one" here: the
    token used to authorise this call is dead the moment it returns. A client must
    treat 204 as "you are now signed out locally as well" and clear its own state.

    NO UI CALLS THIS IN v1 — deliberately, there is no button. It exists for
    security response (lost device, suspected leak) via a direct authenticated
    call. A signed-out-everywhere UX is a separate decision.
    """
    user.token_version += 1
    await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    # Global free daily deep-mode allowance for the initial-load meter (A2). -1 for
    # pro/premium/unlimited. Tier resolves via get_user_tier inside the helper.
    deep = await check_deep_mode_limit(db, user.id)
    return UserOut.model_validate(user).model_copy(
        update={"needs_disclaimer": needs_disclaimer, "deep_remaining": deep.remaining}
    )


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

    # Whether THIS request created the account, taken from the branch that already
    # decides it — no new lookup, no restructuring of the handler.
    is_new_account = user is None

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
        # No email property: distinct_id is the internal user id and person
        # profiles carry no direct identifier (data minimization, GDPR Art. 5(1)(c)).
        analytics_service.identify(user.id, {"plan": "free"})
        analytics_service.track("signup_completed", user.id, {"plan": "free", "method": "otp"})
    else:
        analytics_service.track("user_signed_in", user.id, {"method": "otp"})

    token = create_token(user.id, user.email, user.token_version)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    user_out = UserOut.model_validate(user).model_copy(update={"needs_disclaimer": needs_disclaimer})
    return TokenResponse(access_token=token, user=user_out, is_new_account=is_new_account)
