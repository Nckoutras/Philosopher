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


def _make_sub(status="active", current_period_end=None):
    sub = MagicMock()
    sub.status = status
    sub.current_period_end = current_period_end
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
async def test_past_due_subscription_returns_free():
    sub = _make_sub(status="past_due", current_period_end=_future())
    db = _make_db(sub)
    assert await get_user_tier(db, USER_ID) == "free"
