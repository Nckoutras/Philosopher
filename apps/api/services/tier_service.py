from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from models import Subscription


async def get_user_tier(db: AsyncSession, user_id: UUID) -> Literal["free", "pro", "premium"]:
    if config.BETA_GRANT_PRO_TO_ALL:
        return "pro"

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == str(user_id))
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return "free"
    # ── GRACE DURING DUNNING ─────────────────────────────────────────────────
    # THIS LINE GRANTS UNPAID ACCESS, deliberately. `past_due` means Stripe took
    # a payment attempt and it failed; before this, that dropped a paying user to
    # free mid-cycle, silently, with no email — a recoverable card problem became
    # a churn event.
    #
    # WHAT BOUNDS IT. Not a timer of ours: two independent Stripe-driven clocks.
    #   1. customer.subscription.deleted — when Stripe gives up on dunning it
    #      cancels the subscription, and that webhook sets status='canceled',
    #      which is not in the tuple below, so access ends.
    #   2. The 6-hourly reconcile cron (workers/cron.py) re-reads status from
    #      Stripe for every past_due row, so a MISSED deleted webhook still ends
    #      access within six hours.
    # Worst case is therefore Stripe's dunning window, not indefinite.
    #
    # past_due is checked BEFORE the expiry gate below because a failed renewal
    # leaves current_period_end at the old, already-passed date — Stripe only
    # advances it on a successful payment. Running the expiry check on a past_due
    # row would end grace within hours of it starting, which is no grace at all.
    if sub.plan in ("pro", "premium") and sub.status == "past_due":
        return sub.plan

    if sub.status not in ("active", "trialing"):
        return "free"
    # NULL current_period_end = manual/comp grant with no expiry. Stripe-managed
    # subscriptions always set current_period_end, so NULL only ever occurs for
    # manually-granted access. Only an explicit past expiry downgrades to free.
    if sub.current_period_end is not None and sub.current_period_end <= datetime.now(timezone.utc):
        return "free"
    if sub.plan not in ("pro", "premium"):
        return "free"
    return sub.plan
