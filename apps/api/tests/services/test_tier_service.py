"""Tests for tier_service.get_user_tier.

Verifies tier resolution from the subscriptions table without hitting
a real database — all DB interactions are mocked.

Run: cd apps/api && pytest tests/services/test_tier_service.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from services.tier_service import get_user_tier


USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def _future():
    return datetime.now(timezone.utc) + timedelta(days=30)


def _past():
    return datetime.now(timezone.utc) - timedelta(days=1)


def _make_db(sub):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sub
    db.execute = AsyncMock(return_value=result)
    return db


def _make_sub(status="active", current_period_end=None, plan="pro"):
    sub = MagicMock()
    sub.status = status
    sub.current_period_end = current_period_end
    sub.plan = plan
    return sub


# ── Active subscription ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_subscription_returns_pro():
    sub = _make_sub(status="active", current_period_end=_future())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "pro"


# ── No subscription ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_subscription_returns_free():
    db = _make_db(None)
    assert await get_user_tier(db, USER_ID) == "free"


# ── Manually-granted / comp access (current_period_end=NULL) ─────────────────

@pytest.mark.asyncio
async def test_comp_grant_null_period_end_returns_pro():
    # Stripe always sets current_period_end; NULL means manual grant with no expiry.
    sub = _make_sub(status="active", current_period_end=None, plan="pro")
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "pro"


# ── Cancelled subscription ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancelled_subscription_returns_free():
    sub = _make_sub(status="canceled", current_period_end=_future())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "free"


# ── Expired subscription (current_period_end in the past) ────────────────────

@pytest.mark.asyncio
async def test_expired_subscription_returns_free():
    sub = _make_sub(status="active", current_period_end=_past())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "free"


# ── past_due subscription ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_past_due_keeps_pro_during_dunning():
    """INVERTED from test_past_due_subscription_returns_free.

    A failed payment used to drop a paying user to free mid-cycle, silently and
    with no email — a recoverable card problem turned into a churn event. Stripe
    is still retrying at this point; access continues until Stripe gives up and
    sends customer.subscription.deleted.
    """
    sub = _make_sub(status="past_due", current_period_end=_future())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "pro"


@pytest.mark.asyncio
async def test_past_due_keeps_pro_even_after_the_period_end_has_passed():
    """THE CASE THAT MAKES GRACE REAL, and the one a status-tuple-only change
    would have missed. Stripe does not advance current_period_end on a failed
    renewal, so a dunning row's period end is already in the past. If the expiry
    gate applied here, grace would last hours instead of the dunning window."""
    sub = _make_sub(status="past_due", current_period_end=_past())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "pro"


@pytest.mark.asyncio
async def test_past_due_on_a_free_row_is_still_free():
    """Grace extends a Pro entitlement; it does not invent one."""
    sub = _make_sub(status="past_due", current_period_end=_future(), plan="free")
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "free"


@pytest.mark.asyncio
async def test_canceled_after_dunning_ends_access():
    """The bound on the grace above: when Stripe gives up it cancels, the
    deleted webhook writes status='canceled', and access ends."""
    sub = _make_sub(status="canceled", current_period_end=_future())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "free"


@pytest.mark.asyncio
async def test_trialing_subscription_returns_plan():
    sub = _make_sub(status="trialing", current_period_end=_future(), plan="pro")
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "pro"


@pytest.mark.asyncio
async def test_premium_subscription_returns_premium():
    sub = _make_sub(status="active", current_period_end=_future(), plan="premium")
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "premium"
