import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from db.session import get_db
from models import User, Subscription, StripeEvent, SubscriptionEvent
from schemas import CheckoutRequest, CheckoutResponse, PortalResponse, SubscriptionOut
from auth import get_current_user
from services.analytics_service import analytics_service
from constants import PLAN_FEATURES, TIER_ORDER
from config import config

def _tenure_days(sub) -> int | None:
    """Whole days of PAID tenure, from pro_since to now. None when never paid.

    NOT created_at. That column is stamped at signup, when every subscriptions
    row is created on the free plan, so a tenure computed from it measured
    account age — which is the exact distinction this number exists to make. A
    cancel at day 3 of paying and a cancel at day 300 of paying are different
    products failing, and both looked identical when the user had held a free
    account for a year first.

    NULL pro_since means the row never became paying Pro, or predates the column
    (no backfill — see migration 055). None, not zero: zero days of tenure is a
    real and different answer.

    Analytics-only, and never allowed to raise: a webhook that 500s because a
    tenure could not be computed would cost a real subscription update.
    """
    try:
        started = sub.pro_since
        if started is None:
            return None
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - started).days)
    except Exception:
        return None


def _source_of(obj) -> str | None:
    """The paywall that produced this subscription, from Stripe metadata.

    Works for both webhook shapes: the checkout Session carries it in its own
    metadata, the Subscription carries the copy that subscription_data made.
    None when the checkout predates this field or carried no source — analytics
    only, and never allowed to raise inside a webhook.
    """
    try:
        return ((obj or {}).get("metadata") or {}).get("source") or None
    except Exception:
        return None


def _interval_of(stripe_sub) -> str | None:
    """'month' | 'year' from the Stripe subscription's first price. None if the
    payload shape is not what we expect — same fail-quiet rule as above."""
    try:
        items = (stripe_sub or {}).get("items", {}).get("data", [])
        if not items:
            return None
        return items[0].get("price", {}).get("recurring", {}).get("interval")
    except Exception:
        return None


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

    # BOTH metadata bags, and ONLY when there is a source to put in them.
    #
    # Why both: Stripe hands the two webhook cases different objects.
    # `checkout.session.completed` receives the SESSION, so it reads session
    # metadata. `customer.subscription.created|updated` receives the
    # SUBSCRIPTION, which never sees session metadata — subscription_data is
    # what Stripe copies onto the subscription at creation. Both cases fire
    # subscription_activated, so a version that sets only one is silently
    # half-instrumented.
    #
    # Why conditional: a checkout with no source must go to Stripe exactly as it
    # did before this change. Passing metadata={} would alter the request for
    # every existing caller to buy nothing.
    checkout_kwargs: dict = {}
    if body.source:
        checkout_kwargs["metadata"] = {"source": body.source}
        checkout_kwargs["subscription_data"] = {"metadata": {"source": body.source}}

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{config.FRONTEND_URL}/app/account?checkout=success",
        cancel_url=f"{config.FRONTEND_URL}/app/account",
        allow_promotion_codes=True,
        **checkout_kwargs,
    )

    analytics_service.track("checkout_started", user.id, {
        "plan": body.plan,
        "interval": body.interval,
        "source": body.source,
    })
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
    except ValueError:
        # Malformed body — not JSON, or not the shape construct_event expects.
        # A 400 rather than an unhandled 500: Stripe retries a 5xx, and retrying
        # garbage forever costs deliveries against a payload that can never be
        # parsed. Nothing is recorded, because there is no event id to record.
        raise HTTPException(status_code=400, detail="Invalid payload")

    obj = event["data"]["object"]
    event_id = event.get("id")
    event_created = _ts(event.get("created"))

    # ── IDEMPOTENCY ─────────────────────────────────────────────────────────
    # Stripe retries on any non-2xx and guarantees at-least-once, not
    # exactly-once. Before this, a retried delivery re-ran every side effect:
    # a duplicate checkout.session.completed fired subscription_activated twice,
    # and a retried subscription.deleted could land after a newer .updated and
    # flip a paying user to free.
    #
    # The INSERT is the lock, and it must FLUSH before any processing. Without
    # the flush, two concurrent deliveries of the same event both pass this
    # point and both run their side effects; one then dies at commit — after the
    # damage. With it, the loser hits the primary key here and returns 200
    # having done nothing.
    stripe_event = StripeEvent(
        id=event_id,
        type=event["type"],
        created=event_created or datetime.now(timezone.utc),
    )
    db.add(stripe_event)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("Duplicate Stripe delivery ignored: event=%s type=%s", event_id, event["type"])
        return {"received": True, "duplicate": True}

    try:
        result = await _process_webhook_event(db, event, obj, event_id, event_created, request)
    except Exception:
        # Delete the row so Stripe's retry gets a clean insert rather than a
        # permanent duplicate-conflict that can never be processed. Then re-raise
        # for the 500 that asks Stripe to retry at all.
        await db.rollback()
        await db.execute(delete(StripeEvent).where(StripeEvent.id == event_id))
        await db.commit()
        logger.error(
            "Stripe webhook processing failed, row deleted for retry: event=%s type=%s",
            event_id, event["type"], exc_info=True,
        )
        raise

    stripe_event.processed_at = datetime.now(timezone.utc)
    stripe_event.skipped = result.get("skipped", False)
    await db.commit()
    return {"received": True}


# The fixed vocabulary for last_14d_features, and the single place the mapping
# lives. feature_key -> (model, user column, time column, extra filter).
#
# self_portrait has no table of its own: answers merge into
# user_preferences.profile.answers, a JSONB blob with no per-answer timestamp.
# The ARQ seed writes one memory_entries row per answered question instead
# (arq_worker: entry_type="self_portrait"), which IS timestamped. It lands
# seconds after the answer — immaterial in a 14-day window.
FEATURE_WINDOW_DAYS = 14


def _feature_sources():
    """Imported lazily so this module keeps its current import surface."""
    from models import (
        Message, CouncilCase, Counterview, Mirror, SelfComparison,
        WeeklyLetter, MemoryEntry, ScheduledEmail,
    )
    return [
        ("chat", Message, Message.created_at, Message.role == "user"),
        ("council", CouncilCase, CouncilCase.created_at, None),
        ("counterview", Counterview, Counterview.created_at, None),
        ("mirror", Mirror, Mirror.created_at, None),
        ("you_vs_you", SelfComparison, SelfComparison.created_at, None),
        ("letter", WeeklyLetter, WeeklyLetter.created_at, None),
        ("self_portrait", MemoryEntry, MemoryEntry.created_at,
         MemoryEntry.entry_type == "self_portrait"),
        ("future_self", ScheduledEmail, ScheduledEmail.created_at, None),
    ]


FEATURE_VOCABULARY = (
    "chat", "council", "counterview", "letter", "mirror",
    "self_portrait", "future_self", "you_vs_you",
)


async def _last_14d_features(db, user_id) -> list:
    """Sorted distinct feature keys with activity in the last 14 days.

    From OUR database, not PostHog: this must be true at the moment of
    cancellation, and it must be answerable for a user who never consented to
    analytics. An EMPTY LIST is a valid and interesting answer — it says they
    cancelled having used nothing, which is the most actionable churn signal
    there is, and it must never be confused with "we failed to look".

    Values come only from FEATURE_VOCABULARY, never from user content. Analytics
    only, and never allowed to raise inside a webhook.
    """
    from datetime import timedelta

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=FEATURE_WINDOW_DAYS)
        found = []
        for key, model, time_col, extra in _feature_sources():
            conditions = [model.user_id == str(user_id), time_col >= cutoff]
            if extra is not None:
                conditions.append(extra)
            row = await db.execute(select(model.id).where(*conditions).limit(1))
            if row.first() is not None:
                found.append(key)
        return sorted(found)
    except Exception:
        logger.error("last_14d_features failed for user=%s", user_id, exc_info=True)
        return []


async def _send_recovery_email(request, db, user_id) -> None:
    """Queue the dunning recovery email, or send it inline if there is no queue.

    ARQ first so a slow Resend cannot add latency to a Stripe webhook and turn a
    successful billing update into a retry.

    The fallback is a SYNCHRONOUS send, not a silent drop: a misconfigured queue
    must not quietly eat a revenue-recovery email. Both paths log ERROR on
    failure and return normally — this function never raises, because the
    webhook has already applied a billing state change by the time it runs.
    """
    queue = getattr(request.app.state, "arq_queue", None)
    if queue is not None:
        try:
            await queue.enqueue_job("send_payment_recovery_email_task", str(user_id))
            return
        except Exception as e:
            logger.error(
                "Payment recovery email: enqueue failed for user=%s, falling back "
                "to a synchronous send: %s", user_id, e, exc_info=True,
            )

    try:
        from models import User
        from services.email_service import send_email
        from services.template_service import (
            render_payment_recovery_email, PAYMENT_RECOVERY_SUBJECT,
        )

        result = await db.execute(select(User).where(User.id == str(user_id)))
        user = result.scalar_one_or_none()
        if user is None or not user.email:
            logger.error("Payment recovery email: no user/email for %s", user_id)
            return
        send_email(
            to=user.email,
            subject=PAYMENT_RECOVERY_SUBJECT,
            html=render_payment_recovery_email(
                portal_link=f"{config.FRONTEND_URL.rstrip('/')}/app/account",
            ),
        )
    except Exception as e:
        logger.error(
            "Payment recovery email FAILED for user=%s: %s", user_id, e, exc_info=True,
        )


def _cancel_reason(obj) -> str:
    """Why Stripe says this subscription ended, as one of three enum values.

    Stripe's cancellation_details.reason is
    Literal["cancellation_requested", "payment_disputed", "payment_failed"].
    Both payment shapes collapse to payment_failed — a dispute and a decline are
    the same story for churn analysis.

    NEVER reads cancellation_details.comment, which is free text the customer
    typed and sits one attribute away from here.
    """
    try:
        details = (obj or {}).get("cancellation_details") or {}
        reason = details.get("reason")
    except Exception:
        return "other"
    if reason in ("payment_failed", "payment_disputed"):
        return "payment_failed"
    if reason == "cancellation_requested":
        return "user_requested"
    return "other"


def _cancel_feedback(obj) -> str | None:
    """The customer's survey answer, passed through verbatim.

    Safe to pass through because it is a CLOSED Stripe enum — customer_service,
    low_quality, missing_features, other, switched_service, too_complex,
    too_expensive, unused — with zero free text. Its sibling `comment` is the
    free-text field and is never read.
    """
    try:
        return ((obj or {}).get("cancellation_details") or {}).get("feedback") or None
    except Exception:
        return None


def _record_transition(
    db, sub, stripe_event_id, event_type, *,
    to_status=None, to_plan=None, interval=None,
):
    """Append one row to subscription_events. Captures from_* BEFORE the caller
    mutates the row, so every call site must invoke this first.

    A transition where from == to is still recorded: "Stripe told us again" is
    information, and dropping it would make a retry storm invisible.
    """
    db.add(SubscriptionEvent(
        user_id=sub.user_id,
        subscription_id=sub.id,
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        from_status=sub.status,
        to_status=to_status if to_status is not None else sub.status,
        from_plan=sub.plan,
        to_plan=to_plan if to_plan is not None else sub.plan,
        interval=interval if interval is not None else sub.interval,
    ))


def _is_stale(sub, event_created) -> bool:
    """True when this event predates the newest one already applied to the row.

    NULL last_stripe_event_at means APPLY, never skip. The 6-hourly reconcile
    cron (workers/cron.py) writes `status` without going through the webhook, so
    a row it has touched has no baseline and never will; treating NULL as
    "everything is stale" would freeze those rows permanently.

    Equal timestamps apply. Stripe's `created` has one-second resolution, so two
    genuinely distinct events can share it, and refusing the second would drop a
    real transition to save a redundant one.
    """
    if event_created is None or sub.last_stripe_event_at is None:
        return False
    last = sub.last_stripe_event_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return event_created < last


def _mark_applied(sub, event_created) -> None:
    """Advance the ordering baseline. Only ever moves forward."""
    if event_created is None:
        return
    last = sub.last_stripe_event_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or event_created > last:
        sub.last_stripe_event_at = event_created


def _mark_pro_since(sub) -> None:
    """Stamp the start of PAID tenure, once, on the first transition into an
    active Pro state. Idempotent: a later .updated on an already-Pro row must not
    restart the clock, or every renewal would reset the tenure to zero."""
    if sub.plan == "pro" and sub.status == "active" and sub.pro_since is None:
        sub.pro_since = datetime.now(timezone.utc)


async def _process_webhook_event(db, event, obj, event_id, event_created, request) -> dict:
    """Apply one verified, de-duplicated Stripe event. Returns {"skipped": bool}.

    Split out of stripe_webhook so the idempotency and crash handling above read
    as one thing, and so an exception anywhere in here reaches exactly one place.
    """
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
                        if _is_stale(sub, event_created):
                            logger.warning(
                                "Stale checkout.session.completed ignored: event=%s "
                                "created=%s is older than last applied %s (subscription=%s)",
                                event_id, event_created, sub.last_stripe_event_at, sub.id,
                            )
                            return {"skipped": True}
                        new_plan = _plan_from_stripe(stripe_sub)
                        new_interval = _interval_of(stripe_sub)
                        _record_transition(
                            db, sub, event_id, event["type"],
                            to_status=stripe_sub["status"], to_plan=new_plan,
                            interval=new_interval,
                        )
                        sub.plan = new_plan
                        sub.status = stripe_sub["status"]
                        sub.current_period_end = _ts(_period_end_from_stripe(stripe_sub))
                        sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
                        sub.interval = new_interval
                        _mark_pro_since(sub)
                        _mark_applied(sub, event_created)
                        analytics_service.track(
                            "subscription_activated", sub.user_id, {
                                "plan": sub.plan,
                                "interval": _interval_of(stripe_sub),
                                # `obj` is the checkout Session here, so this is
                                # the session metadata set at create_checkout.
                                "source": _source_of(obj),
                            },
                        )

        case "invoice.payment_succeeded":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj.get("subscription"))
            )
            sub = result.scalar_one_or_none()
            if sub:
                if _is_stale(sub, event_created):
                    logger.warning(
                        "Stale invoice.payment_succeeded ignored: event=%s created=%s "
                        "is older than last applied %s (subscription=%s)",
                        event_id, event_created, sub.last_stripe_event_at, sub.id,
                    )
                    return {"skipped": True}

                if sub.status != "active":
                    # Status heal only, exactly as before. current_period_end keeps
                    # its SINGLE writer in customer.subscription.*, which already
                    # carries the whole renewal — a second writer here would be two
                    # paths to the field this codebase deliberately kept to one.
                    _record_transition(db, sub, event_id, event["type"], to_status="active")
                    sub.status = "active"

                # OUTSIDE the status check, deliberately. An event that was applied
                # and found nothing to change is still an event applied to this row,
                # and the baseline must move or a later stale delivery would be
                # judged against a stale high-water mark.
                _mark_applied(sub, event_created)

        case "customer.subscription.created" | "customer.subscription.updated":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == obj["customer"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                if _is_stale(sub, event_created):
                    logger.warning(
                        "Stale customer.subscription.%s ignored: event=%s created=%s "
                        "is older than last applied %s (subscription=%s)",
                        event["type"].rsplit(".", 1)[-1], event_id, event_created,
                        sub.last_stripe_event_at, sub.id,
                    )
                    return {"skipped": True}

                new_plan = _plan_from_stripe(obj)
                new_interval = _interval_of(obj)
                _record_transition(
                    db, sub, event_id, event["type"],
                    to_status=obj["status"], to_plan=new_plan, interval=new_interval,
                )
                sub.stripe_subscription_id = obj["id"]
                sub.plan = new_plan
                sub.status = obj["status"]
                sub.interval = new_interval

                # This handler carries the ENTIRE renewal: invoice.payment_succeeded
                # only heals status, and the 6-hourly reconcile cron syncs status
                # only — neither writes a period end. So what happens here when the
                # payload has no period end decides which way a renewal fails.
                #
                # FAIL-CLOSED BY CHOICE. A NULL current_period_end means "manual comp
                # grant, no expiry" to tier_service, so writing NULL over a good date
                # grants permanent Pro for free — silently, with nothing to correct
                # it. Keeping the stale date can instead cost a paying user access at
                # that date, which is loud: they complain, and the error below is in
                # the log waiting. We take the loud, recoverable failure over the
                # silent, unrecoverable one.
                #
                # Not hypothetical: Stripe already moved this field once (top-level ->
                # items), which _period_end_from_stripe absorbs. A second move lands
                # here.
                period_end = _ts(_period_end_from_stripe(obj))
                if period_end is not None:
                    sub.current_period_end = period_end
                elif sub.current_period_end is not None:
                    logger.error(
                        "customer.subscription.%s carried no period end — KEEPING the "
                        "existing current_period_end=%s. subscription=%s event=%s "
                        "user=%s. Check the Stripe API version and the payload shape: "
                        "the user loses access at the stale date.",
                        event["type"].rsplit(".", 1)[-1], sub.current_period_end,
                        obj["id"], event.get("id"), sub.user_id,
                    )
                # An already-NULL row is a deliberate comp grant. Leave it NULL —
                # inventing a date here would revoke access somebody chose to give.

                sub.cancel_at_period_end = obj.get("cancel_at_period_end", False)
                _mark_pro_since(sub)
                _mark_applied(sub, event_created)
                # interval comes off the Stripe price, not the local row: the row
                # records WHAT was bought, the price records HOW OFTEN. `source`
                # is absent by design — PR #3 stashes it in the checkout session
                # metadata, which is where this webhook will read it from.
                analytics_service.track("subscription_activated", sub.user_id, {
                    "plan": sub.plan,
                    "interval": _interval_of(obj),
                    # `obj` is the Subscription here — this reads the metadata
                    # that subscription_data carried over at creation.
                    "source": _source_of(obj),
                })

        case "customer.subscription.deleted":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
            )
            sub = result.scalar_one_or_none()
            if sub:
                if _is_stale(sub, event_created):
                    logger.warning(
                        "Stale customer.subscription.deleted ignored: event=%s created=%s "
                        "is older than last applied %s (subscription=%s). This is the "
                        "delivery that used to flip a paying user to free.",
                        event_id, event_created, sub.last_stripe_event_at, sub.id,
                    )
                    return {"skipped": True}

                canceled_plan = sub.plan
                # tenure_days is read from pro_since BEFORE it is cleared below.
                tenure = _tenure_days(sub)
                _record_transition(
                    db, sub, event_id, event["type"],
                    to_status="canceled", to_plan="free",
                )
                sub.status = "canceled"
                sub.plan = "free"
                # Cleared so a re-subscribe starts a fresh tenure rather than
                # inheriting the length of the subscription they already ended.
                sub.pro_since = None
                _mark_applied(sub, event_created)
                # tenure_days is the whole point of the event: a cancel at day 3
                # and a cancel at day 300 are different products failing. Read
                # BEFORE plan is overwritten to "free" above would be wrong —
                # the plan they cancelled is what we want, so it is captured
                # into a local first.
                #
                # reason, cancel_feedback and last_14d_features all land here.
                # reason and cancel_feedback are Stripe enums; the free-text
                # sibling cancellation_details.comment is never read.
                features = await _last_14d_features(db, sub.user_id)
                analytics_service.track("subscription_canceled", sub.user_id, {
                    "plan": canceled_plan,
                    "tenure_days": tenure,
                    "reason": _cancel_reason(obj),
                    "cancel_feedback": _cancel_feedback(obj),
                    "last_14d_features": features,
                })

        case "invoice.payment_failed":
            result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == obj.get("subscription"))
            )
            sub = result.scalar_one_or_none()
            if sub:
                # THE SAME BUG CLASS AS THE CANCEL PATH, and just as expensive.
                # Without this guard: payment_failed(t1) -> subscription.updated
                # past_due(t2) -> card fixed -> subscription.updated active(t3) ->
                # Stripe retries payment_failed from t1 at t4, and an active paying
                # subscriber is marked past_due by a delivery about a payment that
                # was already resolved.
                if _is_stale(sub, event_created):
                    logger.warning(
                        "Stale invoice.payment_failed ignored: event=%s created=%s "
                        "is older than last applied %s (subscription=%s). This is the "
                        "delivery that used to past_due an already-recovered account.",
                        event_id, event_created, sub.last_stripe_event_at, sub.id,
                    )
                    return {"skipped": True}

                # ONE EMAIL PER DUNNING EPISODE. Stripe retries a failed payment
                # several times and sends payment_failed each time; a row already
                # past_due has been told, so only the entering transition sends.
                # Duplicate DELIVERIES of one event are already dead at the
                # stripe_events lock — this guards the different case of several
                # DISTINCT failures within one episode.
                entering_dunning = sub.status != "past_due"

                _record_transition(db, sub, event_id, event["type"], to_status="past_due")
                sub.status = "past_due"
                _mark_applied(sub, event_created)

                if entering_dunning:
                    await _send_recovery_email(request, db, sub.user_id)

    return {"skipped": False}


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
