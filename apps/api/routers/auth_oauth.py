import logging
import secrets
from urllib.parse import urlencode

import httpx
import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_token
from config import config
from db.session import get_db
from models import Subscription, User
from services.analytics_service import analytics_service
from services.disclaimer_service import user_needs_acceptance
from services.rate_limit_service import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

stripe.api_key = config.STRIPE_SECRET_KEY

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/methods")
async def auth_methods():
    return {
        "google": config.GOOGLE_OAUTH_ENABLED and bool(config.GOOGLE_CLIENT_ID)
    }


@router.get("/oauth/google")
async def google_oauth_start():
    if not config.GOOGLE_OAUTH_ENABLED or not config.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=404, detail="Google OAuth not enabled")

    state = secrets.token_urlsafe(32)
    r = await get_redis()
    await r.set(f"oauth_state:{state}", "1", ex=300)

    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": config.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    frontend_error_url = f"{config.FRONTEND_URL}/auth?error="

    # User cancelled or Google returned an error
    if error or not code or not state:
        return RedirectResponse(f"{frontend_error_url}oauth_cancelled", status_code=302)

    # Verify and consume state token (CSRF protection)
    r = await get_redis()
    stored = await r.get(f"oauth_state:{state}")
    if not stored:
        return RedirectResponse(f"{frontend_error_url}oauth_invalid_state", status_code=302)
    await r.delete(f"oauth_state:{state}")

    # Exchange code for access_token, then fetch verified user info
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": config.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            if token_resp.status_code != 200:
                logger.warning(
                    f"Google token exchange failed: {token_resp.status_code} {token_resp.text}"
                )
                return RedirectResponse(
                    f"{frontend_error_url}oauth_exchange_failed", status_code=302
                )
            access_token = token_resp.json()["access_token"]

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                logger.warning(f"Google userinfo failed: {userinfo_resp.status_code}")
                return RedirectResponse(
                    f"{frontend_error_url}oauth_userinfo_failed", status_code=302
                )
            userinfo = userinfo_resp.json()
    except httpx.RequestError as exc:
        logger.exception(f"Google OAuth network error: {exc}")
        return RedirectResponse(f"{frontend_error_url}oauth_network_error", status_code=302)

    email: str = userinfo.get("email", "").lower()
    google_sub: str = userinfo.get("sub", "")
    full_name: str | None = userinfo.get("name")

    if not email or not google_sub:
        return RedirectResponse(f"{frontend_error_url}oauth_missing_email", status_code=302)

    # Find existing user — by oauth_provider_id first (handles Google-side email change),
    # then by email (handles existing OTP users signing in with Google for the first time)
    result = await db.execute(select(User).where(User.oauth_provider_id == google_sub))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    is_new_user = user is None

    if is_new_user:
        # Mirror the user creation pattern from otp/verify (auth.py:126-143):
        # User + Stripe customer + Subscription must all succeed or all roll back.
        try:
            user = User(
                email=email,
                hashed_password=None,
                full_name=full_name,
                auth_provider="google",
                oauth_provider_id=google_sub,
            )
            db.add(user)
            await db.flush()
            customer = stripe.Customer.create(email=email, name=full_name or "")
            sub = Subscription(
                user_id=user.id,
                stripe_customer_id=customer.id,
                plan="free",
                status="active",
            )
            db.add(sub)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(f"OAuth user creation failed for {email}")
            return RedirectResponse(
                f"{frontend_error_url}oauth_signup_failed", status_code=302
            )

        # Analytics fires after commit — never blocks auth flow
        try:
            analytics_service.identify(user.id, {"email": email, "plan": "free"})
            analytics_service.track(
                "user_registered", user.id, {"plan": "free", "method": "google"}
            )
        except Exception:
            logger.warning("OAuth signup analytics failed (non-fatal)", exc_info=True)
    else:
        try:
            analytics_service.track("user_signed_in", user.id, {"method": "google"})
        except Exception:
            logger.warning("OAuth sign-in analytics failed (non-fatal)", exc_info=True)

    token = create_token(user.id, user.email, user.token_version)
    needs_disclaimer = await user_needs_acceptance(user.id, db)
    nd_param = "1" if needs_disclaimer else "0"

    # new_account tells the finish page THIS callback created the account (A8b). The
    # value has existed at :125 since the flow was written and was never surfaced, so a
    # Google sign-in with an unrecognised address produced a second, empty account in
    # silence — the same defect A8 fixed on the OTP path.
    #
    # The EMAIL is deliberately not added: /auth/welcome reads it from the store. A
    # boolean adds no exposure the token in this same query string does not already have.
    finish_qs = urlencode({
        "token": token,
        "needs_disclaimer": nd_param,
        "new_account": "1" if is_new_user else "0",
    })
    finish_url = f"{config.FRONTEND_URL}/auth/oauth/finish?{finish_qs}"
    return RedirectResponse(finish_url, status_code=302)
