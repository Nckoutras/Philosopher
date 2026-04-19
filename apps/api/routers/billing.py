import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Subscription
from schemas import CheckoutRequest, CheckoutResponse, PortalResponse, SubscriptionOut
from auth import get_current_user
from services.analytics_service import analytics_service
from constants import PLAN_FEATURES, TIER_ORDER
from config import config

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = config.STRIPE_SECRET_KEY

PLANS = {
    "pro_monthly":     config.STRIPE_PRICE_PRO_MONTHLY,
    "pro_yearly":      config.STRIPE_PRICE_PRO_YEARLY,
    "premium_monthly": config.STRIPE_PRICE_PREMIUM_MONTHLY,
}


@router.get("/plans")
async def get_plans():
    return {"plans": PLAN_FEATURES}


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")
    return SubscriptionOut.model_validate(sub)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=400, detail="No billing record")

    price_key = f"{body.plan}_{body.interval}"
    price_id = PLANS.get(price_key)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan/interval: {price_key}")

    session = stripe.checkout.Session.create(
        customer=sub.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{config.BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{config.BASE_URL}/upgrade",
        subscription_data={"trial_period_days": 7},
        allow_promotion_codes=True,
    )

    analytics_service.track("checkout_started", user.id, {"plan": body.plan, "interval": body.interval})
    return CheckoutResponse(checkout_url=session.url)


@router.post("/portal", response_model=PortalResponse)
async def customer_portal(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=400)

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{config.BASE_URL}/settings",
    )
    return PortalResponse(portal_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, config.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    obj = event["data"]["object"]

    match event["type"]:
        case "customer.subscription.created" | "customer.subscription.updated":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == obj["customer"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.stripe_subscription_id = obj["id"]
                sub.plan = _plan_from_stripe(obj)
                sub.status = obj["status"]
                sub.current_period_end = _ts(obj.get("current_period_end"))
                sub.cancel_at_period_end = obj.get("cancel_at_period_end", False)
                analytics_service.track("subscription_activated", sub.user_id, {"plan": sub.plan})

        case "customer.subscription.deleted":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = "canceled"
                sub.plan = "free"
                analytics_service.track("subscription_canceled", sub.user_id, {"plan": sub.plan})

        case "invoice.payment_failed":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj.get("subscription"))
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = "past_due"

    await db.commit()
    return {"received": True}


def _plan_from_stripe(sub_obj: dict) -> str:
    """Infer plan name from Stripe subscription price ID."""
    price_ids = [item["price"]["id"] for item in sub_obj.get("items", {}).get("data", [])]
    if config.STRIPE_PRICE_PREMIUM_MONTHLY in price_ids:
        return "premium"
    if config.STRIPE_PRICE_PRO_MONTHLY in price_ids or config.STRIPE_PRICE_PRO_YEARLY in price_ids:
        return "pro"
    return "free"


def _ts(unix_ts) -> "datetime | None":
    if not unix_ts:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
