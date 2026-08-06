"""Tests for the reconcile_stripe_subscriptions cron function.

The job used to treat stripe.error.InvalidRequestError as "the customer
cancelled" and write status=canceled / plan=free. That was always wrong: Stripe
RETAINS cancelled subscriptions and returns them with status="canceled" on
retrieve, so InvalidRequestError only ever means "this id is not recognised
under the current key" — a test-mode id after a live key switch, a synthetic
comp-grant id, or a typo. These tests pin the new behaviour: never downgrade on
an unrecognised id, always log it at ERROR, and keep genuine cancellations
working through the status sync.

Extracts the inner async function from setup_cron and exercises it directly,
matching tests/services/test_cron_pending_emails.py.

Run: cd apps/api && pytest tests/services/test_cron_stripe_reconcile.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import stripe
from unittest.mock import AsyncMock, MagicMock, patch


USER_ID  = "37f8b510-f7cc-4f08-9e41-652ab432b2da"
STALE_ID = "sub_1Te9YaRoxAlioi1dWVTwYFgU"   # real shape of a test-mode id
LIVE_ID  = "sub_1LiveAbcdefghijklmnop"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sub(sub_id=STALE_ID, plan="pro", status="active"):
    s = MagicMock()
    s.user_id = USER_ID
    s.stripe_subscription_id = sub_id
    s.plan = plan
    s.status = status
    return s


def _make_db(subs):
    """AsyncSession mock usable as `async with AsyncSessionLocal() as db`."""
    db = AsyncMock()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = subs
    result = MagicMock()
    result.scalars.return_value = scalars_mock

    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return db


def _get_cron_fn():
    """Call setup_cron with a dummy queue and capture the registered
    'stripe_reconcile' job function from APScheduler."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from workers.cron import setup_cron

    dummy_queue = MagicMock()
    scheduler = AsyncIOScheduler()

    import workers.cron as cron_mod
    original_scheduler = cron_mod.scheduler
    cron_mod.scheduler = scheduler

    try:
        setup_cron(dummy_queue)
        job = scheduler.get_job("stripe_reconcile")
        fn = job.func
        scheduler.shutdown(wait=False)
    finally:
        cron_mod.scheduler = original_scheduler
        cron_mod.shutdown_cron()

    return fn


# PATCH TARGETS — deliberately NOT the module-level ones. Unlike
# send_pending_future_self_emails, reconcile_stripe_subscriptions RE-IMPORTS
# AsyncSessionLocal inside the function body (workers/cron.py), so the local name
# shadows workers.cron.AsyncSessionLocal and patching that module attribute would
# be silently ineffective — the test would pass against the real session factory.
# Patch db.session directly, and stripe.Subscription.retrieve on the stripe module
# the function imports. Do not "fix" these back to workers.cron.*.


# ── Unrecognised id → never downgrade ────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_subscription_id_does_not_downgrade_and_logs_error():
    """The four production rows carry test-mode ids. After a live-key switch
    retrieve raises InvalidRequestError — the row must be left alone."""
    sub = _make_sub(sub_id=STALE_ID, plan="pro", status="active")
    db = _make_db([sub])

    not_found = stripe.error.InvalidRequestError("No such subscription", "id")

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", side_effect=not_found),
        patch("workers.cron.logger") as m_logger,
    ):
        await _get_cron_fn()()

    # Row untouched — both fields.
    assert sub.status == "active"
    assert sub.plan == "pro"
    db.commit.assert_not_awaited()

    # ERROR carries the subscription id and the user id.
    m_logger.error.assert_called_once()
    args = m_logger.error.call_args.args
    assert STALE_ID in args
    assert USER_ID in args
    assert "NO downgrade" in args[0]


@pytest.mark.asyncio
async def test_synthetic_comp_grant_id_is_not_downgraded():
    """Manual grants are written with synthetic ids ('admin_override',
    'sub_beta_<uuid>'). retrieve raises for them, and an active comp grant must
    survive the reconcile untouched. This is the regression that protects
    future manual grants."""
    sub = _make_sub(sub_id="admin_override", plan="pro", status="active")
    db = _make_db([sub])

    not_found = stripe.error.InvalidRequestError("No such subscription", "id")

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", side_effect=not_found),
        patch("workers.cron.logger") as m_logger,
    ):
        await _get_cron_fn()()

    assert sub.status == "active"
    assert sub.plan == "pro"
    db.commit.assert_not_awaited()
    m_logger.error.assert_called_once()


# ── Genuine cancellation → downgrade ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_genuinely_cancelled_subscription_downgrades_status_and_plan():
    """Stripe returns cancelled subscriptions with status='canceled'. That is
    the real cancellation signal, and it downgrades both fields."""
    sub = _make_sub(sub_id=LIVE_ID, plan="pro", status="active")
    db = _make_db([sub])

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", return_value=MagicMock(status="canceled")),
        patch("workers.cron.logger"),
    ):
        await _get_cron_fn()()

    assert sub.status == "canceled"
    assert sub.plan == "free"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_past_due_sync_does_not_touch_plan():
    """Only a 'canceled' status downgrades the plan. Any other transition syncs
    status alone."""
    sub = _make_sub(sub_id=LIVE_ID, plan="pro", status="active")
    db = _make_db([sub])

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", return_value=MagicMock(status="past_due")),
        patch("workers.cron.logger"),
    ):
        await _get_cron_fn()()

    assert sub.status == "past_due"
    assert sub.plan == "pro"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unchanged_status_writes_nothing():
    sub = _make_sub(sub_id=LIVE_ID, plan="pro", status="active")
    db = _make_db([sub])

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", return_value=MagicMock(status="active")),
        patch("workers.cron.logger") as m_logger,
    ):
        await _get_cron_fn()()

    assert sub.status == "active"
    assert sub.plan == "pro"
    db.commit.assert_not_awaited()

    summary = m_logger.info.call_args.args
    assert summary[1] == 0   # synced
    assert summary[2] == 0   # skipped


# ── Summary log separates synced from skipped ────────────────────────────────

@pytest.mark.asyncio
async def test_summary_counts_synced_and_skipped_separately():
    """A founder reading the logs must be able to tell '1 status synced' from
    '2 subscriptions unrecognised' at a glance."""
    cancelled = _make_sub(sub_id=LIVE_ID, plan="pro", status="active")
    stale_a = _make_sub(sub_id=STALE_ID, plan="pro", status="active")
    stale_b = _make_sub(sub_id="admin_override", plan="pro", status="active")
    db = _make_db([cancelled, stale_a, stale_b])

    not_found = stripe.error.InvalidRequestError("No such subscription", "id")

    def _retrieve(sub_id):
        if sub_id == LIVE_ID:
            return MagicMock(status="canceled")
        raise not_found

    with (
        patch("db.session.AsyncSessionLocal", return_value=db),
        patch("config.config.STRIPE_SECRET_KEY", "sk_test_dummy"),
        patch("stripe.Subscription.retrieve", side_effect=_retrieve),
        patch("workers.cron.logger") as m_logger,
    ):
        await _get_cron_fn()()

    # Only the genuinely cancelled row moved.
    assert cancelled.status == "canceled" and cancelled.plan == "free"
    assert stale_a.status == "active" and stale_a.plan == "pro"
    assert stale_b.status == "active" and stale_b.plan == "pro"

    # Both unrecognised rows logged individually at ERROR.
    assert m_logger.error.call_count == 2

    # Summary reports 1 synced and 2 skipped as distinct numbers.
    summary = m_logger.info.call_args.args
    assert summary[1] == 1   # synced
    assert summary[2] == 2   # skipped
