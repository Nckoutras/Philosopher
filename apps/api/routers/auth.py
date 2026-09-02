import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Subscription
from schemas import TokenResponse, UserOut, OtpRequest, OtpVerifyRequest, UpdateMeRequest
from auth import create_token, get_current_user, get_current_user_plan
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
from services.account_deletion_service import delete_account, StripeCancelFailed
from services.data_export_service import build_export, count_messages
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


# Above the guard so both the limit and the cap are visible at the top of the
# route rather than buried in it.
EXPORT_MAX_MESSAGES = 25_000
EXPORT_RATE_LIMIT_PER_HOUR = 1
EXPORT_TOO_LARGE_DETAIL = (
    "Your data export is too large for automatic download. Contact "
    "support@thewiseroom.app and we will prepare it for you."
)


@router.get("/me/export")
async def export_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everything we hold about this user, as one JSON document. GDPR Art. 15/20.

    Synchronous. Measured against production, the heaviest real user holds 380
    messages and 68KB of content, so there is no case for a background job, an
    email, or object storage — each of which would add a failure mode to a right
    that currently has none.

    RATE LIMITED to one per hour. This endpoint dumps an entire account in one
    response; without a limit it is the cheapest way to generate load and the
    cheapest way to exfiltrate a compromised session's full history. Same
    mechanism as otp_request, and fail-CLOSED for the same reason: if Redis is
    unreachable check_and_increment raises, the request 500s, and one behaviour
    covers both routes. An export delayed by an infra incident is a delayed
    right; an unbounded dump endpoint during one is a worse problem.

    413 above EXPORT_MAX_MESSAGES rather than a hung request. The cap is 65x
    above the current heaviest user — it exists for the SHAPE of the problem
    (messages dominate the payload and grow without bound) so that the failure,
    if it ever arrives, is an error a person can act on rather than a timeout.
    """
    allowed = await check_and_increment(
        f"data_export:{user.id}",
        max_count=EXPORT_RATE_LIMIT_PER_HOUR,
        window_seconds=3600,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You can download your data once an hour. Please try again shortly.",
        )

    # Counted BEFORE assembling anything: the guard exists to avoid building a
    # payload we cannot send, so checking after the build would defeat it.
    message_count = await count_messages(db, user.id)
    if message_count > EXPORT_MAX_MESSAGES:
        logger.warning(
            "Data export refused as too large: user=%s messages=%d cap=%d",
            user.id, message_count, EXPORT_MAX_MESSAGES,
        )
        raise HTTPException(status_code=413, detail=EXPORT_TOO_LARGE_DETAIL)

    payload = await build_export(db, user)

    analytics_service.track("data_exported", user.id, {
        "conversation_count": len(payload["conversations"]),
        "record_count": _export_record_count(payload),
        "size_bucket": _export_size_bucket(payload),
    })
    return payload


def _export_record_count(payload: dict) -> int:
    """Total rows across every list section. Counts only — nothing here reads a
    value, so no content can reach the event through this path."""
    return sum(len(v) for v in payload.values() if isinstance(v, list))


def _export_size_bucket(payload: dict) -> str:
    """Coarse bucket, not a byte count — the registry rule is ids, enums, counts
    and buckets, and the decision this informs is "is synchronous still viable",
    which a bucket answers."""
    import json
    size = len(json.dumps(payload, default=str))
    if size < 1_000_000:
        return "under_1mb"
    if size < 5_000_000:
        return "1_5mb"
    if size < 10_000_000:
        return "5_10mb"
    return "over_10mb"


@router.delete("/me", status_code=204)
async def delete_me(
    user_and_plan: tuple[User, str] = Depends(get_current_user_plan),
    db: AsyncSession = Depends(get_db),
):
    """Delete this account and everything it owns. GDPR Art. 17.

    HARD delete. There is no grace period and no recovery: 21 tables cascade
    from a single DELETE, and the safety-event audit trail is anonymised rather
    than destroyed (migration 056 explains why).

    NO token_version bump is needed and none is done. get_current_user loads the
    user row and 401s with "User not found" before it ever reaches the "ver"
    check, so the row's absence revokes every token on every device by
    construction. Incrementing a column on a row we are about to delete would be
    theatre.

    502, not 500, when Stripe refuses to cancel a billable subscription: nothing
    has been deleted at that point, the account is intact, and the failure is
    upstream. A deleted account that keeps charging is the one outcome that
    cannot be undone, so this route declines to create it.

    Depends on get_current_user_plan rather than get_current_user because the
    account_deleted event carries the plan, and it has to be read while the
    subscription row still exists.
    """
    user, plan = user_and_plan
    try:
        await delete_account(db, user, plan=plan)
    except StripeCancelFailed as e:
        raise HTTPException(
            status_code=502,
            detail="Could not cancel your subscription with our payment provider. "
                   "Your account has NOT been deleted. Please try again shortly.",
        ) from e
    return Response(status_code=204)


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
        # Domain, not the address: no user row exists yet at this point, and the
        # domain is what distinguishes a provider-wide delivery outage from one
        # bad address. Logs carry ids only — and this line becomes a Sentry
        # issue TITLE via LoggingIntegration.
        logger.exception("OTP request failed for domain=%s: %s", email.rsplit("@", 1)[-1], e)
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
