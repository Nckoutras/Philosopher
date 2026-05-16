"""Tests for rate_limit_service.check_rate_limit (daily message limits).

All DB interactions are mocked; get_user_tier is bypassed via user_tier kwarg.

Run: cd apps/api && pytest tests/services/test_rate_limit_service.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from services.rate_limit_service import (
    FREE_DAILY_LIMIT_PER_PERSONA,
    check_rate_limit,
    next_utc_midnight,
)

USER_A = UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_B = UUID("aaaaaaaa-0000-0000-0000-000000000002")
PERSONA_SOCRATES = UUID("bbbbbbbb-0000-0000-0000-000000000001")
PERSONA_MARCUS = UUID("bbbbbbbb-0000-0000-0000-000000000002")


def _make_db(message_count=None):
    """Mock DB returning a DailyUsage row with the given count, or None if count is None."""
    db = AsyncMock()
    r = MagicMock()
    if message_count is None:
        r.scalar_one_or_none.return_value = None
    else:
        usage = MagicMock()
        usage.message_count = message_count
        r.scalar_one_or_none.return_value = usage
    db.execute = AsyncMock(return_value=r)
    return db


# ── Free tier ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_0_messages_allowed():
    """Free user with 0 messages today: allowed, remaining=5."""
    db = _make_db(message_count=None)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 5
    assert result.limit == FREE_DAILY_LIMIT_PER_PERSONA


@pytest.mark.asyncio
async def test_free_3_messages_allowed():
    """Free user with 3 messages today: allowed, remaining=2."""
    db = _make_db(message_count=3)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 2
    assert result.limit == FREE_DAILY_LIMIT_PER_PERSONA


@pytest.mark.asyncio
async def test_free_exactly_5_messages_blocked():
    """Free user with exactly 5 messages today: NOT allowed, remaining=0."""
    db = _make_db(message_count=5)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_free_over_limit_blocked():
    """Free user with 7 messages (over limit): NOT allowed, remaining=0 (defensive)."""
    db = _make_db(message_count=7)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


# ── Pro tier ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pro_0_messages_unlimited():
    """Pro user with 0 messages: allowed, remaining=-1, limit=-1."""
    db = _make_db(message_count=None)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="pro")
    assert result.allowed is True
    assert result.remaining == -1
    assert result.limit == -1
    db.execute.assert_not_called()  # pro tier skips DB query


@pytest.mark.asyncio
async def test_pro_1000_messages_unlimited():
    """Pro user with 1000 messages: still allowed, no cap."""
    db = _make_db(message_count=1000)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="pro")
    assert result.allowed is True
    assert result.remaining == -1
    db.execute.assert_not_called()


# ── Persona isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_different_personas_tracked_separately():
    """Socrates at 5 (blocked) does not affect Marcus (0 messages)."""
    db_socrates = _make_db(message_count=5)
    db_marcus = _make_db(message_count=None)

    result_s = await check_rate_limit(db_socrates, USER_A, PERSONA_SOCRATES, user_tier="free")
    result_m = await check_rate_limit(db_marcus, USER_A, PERSONA_MARCUS, user_tier="free")

    assert result_s.allowed is False
    assert result_m.allowed is True
    assert result_m.remaining == 5


# ── User isolation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_different_users_tracked_separately():
    """User A maxed out does not affect User B."""
    db_a = _make_db(message_count=5)
    db_b = _make_db(message_count=0)

    result_a = await check_rate_limit(db_a, USER_A, PERSONA_SOCRATES, user_tier="free")
    result_b = await check_rate_limit(db_b, USER_B, PERSONA_SOCRATES, user_tier="free")

    assert result_a.allowed is False
    assert result_b.allowed is True


# ── reset_at ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_at_is_next_utc_midnight():
    """reset_at points to next UTC midnight."""
    db = _make_db(message_count=None)
    result = await check_rate_limit(db, USER_A, PERSONA_SOCRATES, user_tier="free")

    now_utc = datetime.now(timezone.utc)
    assert result.reset_at.tzinfo == timezone.utc
    assert result.reset_at > now_utc
    assert result.reset_at.hour == 0
    assert result.reset_at.minute == 0
    assert result.reset_at.second == 0


def test_next_utc_midnight_is_future():
    """next_utc_midnight() always returns a datetime in the future."""
    midnight = next_utc_midnight()
    assert midnight > datetime.now(timezone.utc)
    assert midnight.hour == 0
    assert midnight.minute == 0
    assert midnight.second == 0
    assert midnight.tzinfo == timezone.utc
