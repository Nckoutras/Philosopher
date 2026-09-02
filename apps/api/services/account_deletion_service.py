"""Account deletion — GDPR Art. 17, and the promise the privacy policy makes.

HARD delete, not soft. The user asks, the rows go. Migration 056 gave the
database the four ON DELETE clauses that were missing, so the destruction
itself is one statement and the SCHEMA decides what happens to each dependent
row — not the order of writes in this function.

ORDER, and why it is this order:

  1. Cancel the Stripe subscription, if one is active.
  2. Anonymise the safety-event audit trail.
  3. DELETE FROM users — one statement, 21 tables cascade.
  4. Analytics, best effort, never blocking.

Stripe FIRST because the two failure directions are not symmetric. If the
local delete succeeded and the Stripe cancel then failed, a person who no
longer has an account keeps being charged, and neither they nor we can see the
subscription that is doing it — there is no row left to find it by. That is
the one unrecoverable outcome here, so a Stripe failure ABORTS with 502 and
nothing is deleted. The reverse — subscription cancelled, delete then fails —
leaves a live account on the free tier, which is visible, reversible, and
costs the user nothing.

A cancelled subscription fires customer.subscription.deleted, which arrives
AFTER the user row is gone. That is fine and was verified rather than assumed:
every subscription lookup in the webhook uses scalar_one_or_none() behind an
`if sub:` guard (routers/billing.py), so the delivery finds nothing, changes
nothing, and still records its stripe_events row — Stripe's ledger, which we
keep deliberately.

WHAT SURVIVES A DELETION:
  stripe_events    — Stripe's ledger. Keyed by Stripe ids, holds no user
                     content, and is the record of what was billed.
  safety_events    — anonymised, not deleted. See migration 056 for the
                     reasoning and for the raw_flags audit it depends on.
Everything else owned by the user is destroyed by cascade.

NOT a soft delete, and deliberately no grace period: the recovery window the
old policy text described would require the account to stay functional-but-
locked, which is a different feature. The policy sentence is being amended to
match what this does.
"""
import logging

import stripe
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import SafetyEvent, Subscription, User
from services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

# Statuses that mean Stripe would bill this subscription again. "canceled" and
# "incomplete_expired" are already terminal; there is nothing to cancel and
# calling Stripe would 404. Listed explicitly rather than inferred so a new
# Stripe status defaults to "try to cancel" rather than to "silently skip".
BILLABLE_STATUSES = frozenset({
    "active", "trialing", "past_due", "unpaid", "incomplete",
})

# The distinct_id for account_deleted. NOT the user id: the point of the event
# is the churn count, and attaching the id of the person we just erased to a
# new analytics record would undo the erasure it is reporting. The person
# profile stops accumulating; the count survives.
DELETED_DISTINCT_ID = "deleted_account"


class StripeCancelFailed(Exception):
    """Stripe would not cancel a billable subscription. Nothing was deleted."""


async def _cancel_stripe_subscription(db: AsyncSession, user_id: str) -> bool:
    """Cancel at Stripe if a billable subscription exists. Returns whether it did.

    Raises StripeCancelFailed rather than swallowing: the caller must abort.
    """
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()

    if sub is None or not sub.stripe_subscription_id:
        return False
    if sub.status not in BILLABLE_STATUSES:
        logger.info(
            "Account deletion: subscription %s is %s, nothing to cancel (user=%s)",
            sub.stripe_subscription_id, sub.status, user_id,
        )
        return False

    try:
        stripe.Subscription.cancel(sub.stripe_subscription_id)
    except Exception as e:
        # Deliberately not swallowed. See the module docstring: a deleted
        # account that keeps charging is the one outcome nobody can undo.
        logger.error(
            "Account deletion ABORTED: Stripe cancel failed for subscription=%s "
            "user=%s: %s", sub.stripe_subscription_id, user_id, e, exc_info=True,
        )
        raise StripeCancelFailed(str(e)) from e

    logger.info(
        "Account deletion: cancelled Stripe subscription %s (user=%s)",
        sub.stripe_subscription_id, user_id,
    )
    return True


async def _anonymise_safety_events(db: AsyncSession, user_id: str) -> int:
    """Null the identifiers on this user's safety events. Returns rows touched.

    Done EXPLICITLY here rather than left to 056's ON DELETE SET NULL, for two
    reasons. It is the same result either way, but this states the intent at the
    place a reader looks for it; and it does not depend on the constraint being
    the version 056 installed, which matters because these rows are the one
    thing that outlives the account.

    message_id and conversation_id are nulled too: an id pointing at a deleted
    row is not useful, and a dangling id is still a link back to a person.
    raw_flags is left ALONE — audited 2026-09-02, it carries only the matcher
    constants from safety_service, never user text. See migration 056.
    """
    result = await db.execute(
        update(SafetyEvent)
        .where(SafetyEvent.user_id == user_id)
        .values(user_id=None, message_id=None, conversation_id=None)
        .returning(SafetyEvent.id)
    )
    rows = len(result.fetchall())
    if rows:
        logger.info("Account deletion: anonymised %d safety events (user=%s)", rows, user_id)
    return rows


async def delete_account(db: AsyncSession, user: User, *, plan: str) -> dict:
    """Delete this user and everything they own. Returns a summary for logging.

    Raises StripeCancelFailed if a billable subscription could not be cancelled,
    having deleted NOTHING.
    """
    user_id = user.id

    # Read what the analytics event needs BEFORE the rows are gone.
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    tenure_days = _tenure_days(sub)

    had_active_subscription = await _cancel_stripe_subscription(db, user_id)
    anonymised = await _anonymise_safety_events(db, user_id)

    # One statement. Migration 056 means every dependent row is now handled by
    # the schema: 21 tables CASCADE, safety_events SET NULL.
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    logger.info(
        "Account deleted: user=%s had_active_subscription=%s safety_events_anonymised=%d",
        user_id, had_active_subscription, anonymised,
    )

    # Best effort, after the commit, never able to block or undo the deletion.
    # analytics_service.track already swallows its own failures.
    analytics_service.track(
        "account_deleted",
        DELETED_DISTINCT_ID,
        {
            "plan": plan,
            "tenure_days": tenure_days,
            "had_active_subscription": had_active_subscription,
        },
    )

    return {
        "had_active_subscription": had_active_subscription,
        "safety_events_anonymised": anonymised,
        "tenure_days": tenure_days,
    }


def _tenure_days(sub: Subscription | None) -> int | None:
    """Paid tenure in whole days, or None. Delegates to the billing module.

    NOT reimplemented here. routers/billing.py already owns this calculation and
    its semantics are load-bearing in a way a second copy would quietly lose:
    it returns None rather than 0 when a row never became paying, because "zero
    days of tenure" is a real and different answer from "never paid". Two
    functions of the same name feeding the same registry property under
    different rules is exactly the drift the analytics registries exist to stop.

    Imported inside the function to keep the module-level import graph one-way
    (routers import services, not the reverse); this is the one place that
    borrows back, and it borrows a pure function of its argument. A shared home
    for this helper is a future refactor, not this PR.
    """
    if sub is None:
        return None
    from routers.billing import _tenure_days as billing_tenure_days
    return billing_tenure_days(sub)
