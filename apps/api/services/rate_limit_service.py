"""
Rate limiting utilities.

Redis-backed atomic counters for OTP/auth flows (check_and_increment).
DB-backed daily message limits per (user, persona) for free tier (check_rate_limit).
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from models import DailyUsage

_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _pool


async def check_and_increment(
    key: str,
    max_count: int,
    window_seconds: int,
) -> bool:
    """
    Increment the counter at `key`. Set TTL on first hit.

    Returns True if the request is within the limit (count <= max_count).
    Returns False if the limit has been exceeded.
    """
    r = await get_redis()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window_seconds)
    return count <= max_count


# ── Daily message rate limit (free tier) ──────────────────────────────────────

FREE_DAILY_LIMIT_PER_PERSONA = 5


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: datetime
    limit: int


def next_utc_midnight() -> datetime:
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)


async def check_rate_limit(
    db: AsyncSession,
    user_id: UUID,
    persona_id: UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Check whether the user may send another message to this persona today.

    Passes user_tier through to avoid a redundant DB query when the caller
    has already fetched the tier (e.g. for the persona-access check).
    """
    if user_tier is None:
        from services.tier_service import get_user_tier
        user_tier = await get_user_tier(db, user_id)

    if user_tier in ("pro", "premium"):
        return RateLimitResult(
            allowed=True,
            remaining=-1,
            limit=-1,
            reset_at=next_utc_midnight(),
        )

    result = await db.execute(
        select(DailyUsage).where(
            DailyUsage.user_id == str(user_id),
            DailyUsage.persona_id == str(persona_id),
            DailyUsage.usage_date == date.today(),
        )
    )
    usage = result.scalar_one_or_none()
    count = usage.message_count if usage is not None else 0
    remaining = max(0, FREE_DAILY_LIMIT_PER_PERSONA - count)

    return RateLimitResult(
        allowed=count < FREE_DAILY_LIMIT_PER_PERSONA,
        remaining=remaining,
        limit=FREE_DAILY_LIMIT_PER_PERSONA,
        reset_at=next_utc_midnight(),
    )
