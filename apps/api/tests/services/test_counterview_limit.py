"""Tests for rate_limit_service.check_counterview_limit (free daily counterview cap).

DB is mocked; get_user_tier is bypassed via the user_tier kwarg. Mirrors
test_rate_limit_service.py in style.

Run: cd apps/api && pytest tests/services/test_counterview_limit.py -v
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
    FREE_DAILY_COUNTERVIEW_LIMIT,
    check_counterview_limit,
)

USER_A = UUID("aaaaaaaa-0000-0000-0000-000000000001")


def _make_db(count: int):
    """Mock DB whose count query returns `count` (via scalar_one, like func.count())."""
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one.return_value = count
    db.execute = AsyncMock(return_value=r)
    return db


# ── Free tier ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_0_allowed():
    result = await check_counterview_limit(_make_db(0), USER_A, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 2
    assert result.limit == FREE_DAILY_COUNTERVIEW_LIMIT


@pytest.mark.asyncio
async def test_free_1_allowed():
    result = await check_counterview_limit(_make_db(1), USER_A, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 1


@pytest.mark.asyncio
async def test_free_exactly_2_blocked():
    """3rd direct create today (2 already used) → blocked, remaining=0."""
    result = await check_counterview_limit(_make_db(2), USER_A, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_free_over_limit_blocked():
    result = await check_counterview_limit(_make_db(5), USER_A, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


# ── Pro / premium unlimited (no DB query) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_pro_unlimited():
    db = _make_db(100)
    result = await check_counterview_limit(db, USER_A, user_tier="pro")
    assert result.allowed is True
    assert result.remaining == -1
    assert result.limit == -1
    db.execute.assert_not_called()  # pro skips the count query


@pytest.mark.asyncio
async def test_premium_unlimited():
    db = _make_db(100)
    result = await check_counterview_limit(db, USER_A, user_tier="premium")
    assert result.allowed is True
    assert result.remaining == -1
    db.execute.assert_not_called()


# ── reset_at ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_at_is_next_utc_midnight():
    result = await check_counterview_limit(_make_db(0), USER_A, user_tier="free")
    now_utc = datetime.now(timezone.utc)
    assert result.reset_at.tzinfo == timezone.utc
    assert result.reset_at > now_utc
    assert result.reset_at.hour == 0
    assert result.reset_at.minute == 0


# ── Query shape: only source='direct' rows from today are counted ─────────────
# This is what guarantees insight-path counterviews don't consume the allowance
# (source filter) and that the count resets at the day boundary (created_at filter).

@pytest.mark.asyncio
async def test_count_query_filters_direct_source_and_today():
    db = _make_db(0)
    await check_counterview_limit(db, USER_A, user_tier="free")

    stmt = db.execute.call_args.args[0]
    compiled = stmt.compile()
    sql = str(compiled).lower()
    assert "counterviews" in sql
    assert "source" in sql
    assert "created_at" in sql
    assert "user_id" in sql
    # The source filter binds the literal 'direct' (excludes source='insight').
    assert "direct" in [str(v) for v in compiled.params.values()]
