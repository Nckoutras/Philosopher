import logging

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
logger = logging.getLogger(__name__)

# Single Pro tier. STRIPE_PRICE_PREMIUM_MONTHLY still exists in config (removing a
# config key is a deploy change) but is deliberately no longer read.
PLANS = {
    "pro_monthly":     config.STRIPE_PRICE_PRO_MONTHLY,
    "pro_yearly":      config.STRIPE_PRICE_PRO_YEARLY,
}


async def _resolve_customer_id(db: AsyncSession, user: User, sub: Subscription) -> str:
    """Return a customer id that is usable against the CURRENT Stripe keys.

    Every stripe_customer_id created before the live-key switch belongs to test
    mode and does not exist in live mode; passing one to checkout/portal raises
    InvalidRequestError and the user sees a 500. This heals the row instead:
    verify the stored id, and if Stripe does not know it, create a fresh customer
    and persist it.

    Any other Stripe failure is logged and surfaced as 502 — never swallowed, and
    never allowed to look like a successful checkout.
    """
    cid = sub.stripe_customer_id

    if cid:
        try:
            customer = stripe.Customer.retrieve(cid)
            # A DELETED customer is returned as an object with deleted=True rather
            # than raising, and checkout against it fails. Treat it as missing.
            if not getattr(customer, "deleted", False):
                return cid
        except stripe.error.InvalidRequestError:
            # No such customer under the current keys — fall through and re-create.
            logger.warning(
                "Stripe customer %s not found for user %s; creating a replacement",
                cid, user.id,
            )
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe customer lookup failed for user %s (customer %s): %s",
                user.id, cid, e, exc_info=True,
            )
            raise HTTPException(status_code=502, detail="Billing is temporarily unavailable")

    try:
        customer = stripe.Customer.create(email=user.email)
    except stripe.error.StripeError as e:
        logger.error(
            "Stripe customer creation failed for user %s: %s", user.id, e, exc_info=True,
        )
        raise HTTPException(status_code=502, detail="Billing is temporarily unavailable")

    # COMMIT BEFORE the checkout/portal call, not after. stripe_customer_id is the
    # lookup key for the checkout.session.completed and customer.subscription.*
    # webhook handlers; if Stripe emits an event before this id is persisted, the
    # handler finds no row and the payment is silently not applied. Do not move
    # this commit to the end of the calling endpoint.
    sub.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


@router.get("/plans")
async def get_plans():
    return {"plans": PLAN_FEATURES}


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if config.BETA_GRANT_PRO_TO_ALL:
        return SubscriptionOut(
            plan="pro",
            status="active",
            current_period_end=None,
            cancel_at_period_end=False,
        )
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

    customer_id = await _resolve_customer_id(db, user, sub)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{config.FRONTEND_URL}/app/account?checkout=success",
        cancel_url=f"{config.FRONTEND_URL}/app/account",
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

    customer_id = await _resolve_customer_id(db, user, sub)

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{config.FRONTEND_URL}/app/account",
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
        case "checkout.session.completed":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == obj["customer"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                # The linkage id is safe to store on its own — it is not a grant, and
                # it lets invoice.* handlers and the reconcile cron find this row.
                stripe_sub_id = obj.get("subscription")
                sub.stripe_subscription_id = stripe_sub_id

                # NEVER grant Pro from the session alone. The session carries no
                # period end, and a NULL current_period_end means "manual comp grant,
                # no expiry" (tier_service) — so a missed customer.subscription.*
                # event would hand out permanent Pro for one payment. Read the real
                # subscription and derive every field with the same helpers the
                # customer.subscription.updated handler uses.
                if stripe_sub_id:
                    try:
                        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                    except stripe.error.StripeError as e:
                        # Leave plan/status untouched. customer.subscription.created
                        # still sets them; better a delayed grant than an eternal one.
                        logger.error(
                            "checkout.session.completed: could not retrieve subscription "
                            "%s for user %s: %s", stripe_sub_id, sub.user_id, e, exc_info=True,
                        )
                    else:
                        sub.plan = _plan_from_stripe(stripe_sub)
                        sub.status = stripe_sub["status"]
                        sub.current_period_end = _ts(_period_end_from_stripe(stripe_sub))
                        sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
                        analytics_service.track(
                            "subscription_activated", sub.user_id, {"plan": sub.plan}
                        )

        case "invoice.payment_succeeded":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj.get("subscription"))
            )
            sub = result.scalar_one_or_none()
            if sub and sub.status != "active":
                sub.status = "active"

        case "customer.subscription.created" | "customer.subscription.updated":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == obj["customer"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.stripe_subscription_id = obj["id"]
                sub.plan = _plan_from_stripe(obj)
                sub.status = obj["status"]
                sub.current_period_end = _ts(_period_end_from_stripe(obj))
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
    """Infer plan name from Stripe subscription price ID. Single Pro tier —
    STRIPE_PRICE_PREMIUM_MONTHLY is intentionally not consulted."""
    price_ids = [item["price"]["id"] for item in sub_obj.get("items", {}).get("data", [])]
    if config.STRIPE_PRICE_PRO_MONTHLY in price_ids or config.STRIPE_PRICE_PRO_YEARLY in price_ids:
        return "pro"
    return "free"


def _period_end_from_stripe(sub_obj: dict) -> "int | None":
    """current_period_end moved onto subscription items in recent Stripe API
    versions; fall back to the legacy top-level field for older versions."""
    items = sub_obj.get("items", {}).get("data", [])
    if items and items[0].get("current_period_end"):
        return items[0]["current_period_end"]
    return sub_obj.get("current_period_end")


def _ts(unix_ts) -> "datetime | None":
    if not unix_ts:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
