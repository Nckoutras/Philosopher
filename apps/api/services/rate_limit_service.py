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
from sqlalchemy import select, func

from config import config
from models import Counterview, DailyUsage

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

# Free users get a taste of depth: N go-deepers per persona per day, then a
# gentle upgrade wall. Pro/premium are unlimited. Quantity only — the depth of
# each free go-deeper is identical to Pro (see _deepen_directive).
FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA = 3

# Free sticky deep-mode allowance. Unlike go-deeper (per-persona), this is a
# GLOBAL daily budget across ALL personas — 5 deep replies/day, then normal
# replies (the flag can stay on; it simply stops deepening). Pro/premium unlimited.
FREE_DAILY_DEEP_MODE_LIMIT = 5

# Free daily cap on DIRECT (user-typed) counterviews. GLOBAL per user (not
# per-persona — counterview has no user-chosen persona). Pro/premium unlimited.
FREE_DAILY_COUNTERVIEW_LIMIT = 2


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


async def check_go_deeper_limit(
    db: AsyncSession,
    user_id: UUID,
    persona_id: UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Check whether the (free) user may go deeper with this persona again today.

    Mirrors check_rate_limit but reads daily_usage.go_deeper_count and the
    go-deeper limit. Pro/premium are unlimited. Does NOT increment — the caller
    bumps go_deeper_count on a successful generation.
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
    count = usage.go_deeper_count if usage is not None else 0
    remaining = max(0, FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA - count)

    return RateLimitResult(
        allowed=count < FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA,
        remaining=remaining,
        limit=FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA,
        reset_at=next_utc_midnight(),
    )


async def check_deep_mode_limit(
    db: AsyncSession,
    user_id: str | UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Free daily deep-mode allowance — GLOBAL across all personas (not per-persona).

    Reads SUM(daily_usage.deep_mode_count) for this user TODAY and compares against
    FREE_DAILY_DEEP_MODE_LIMIT. Pro/premium are unlimited (remaining -1). Does NOT
    increment — the caller bumps deep_mode_count on the per-persona row after a
    successful deep reply. `remaining` is the PRE-increment allowance; the streaming
    caller derives the predictive post-reply value from it.
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
        select(func.coalesce(func.sum(DailyUsage.deep_mode_count), 0)).where(
            DailyUsage.user_id == str(user_id),
            DailyUsage.usage_date == date.today(),
        )
    )
    count = int(result.scalar_one() or 0)
    remaining = max(0, FREE_DAILY_DEEP_MODE_LIMIT - count)

    return RateLimitResult(
        allowed=count < FREE_DAILY_DEEP_MODE_LIMIT,
        remaining=remaining,
        limit=FREE_DAILY_DEEP_MODE_LIMIT,
        reset_at=next_utc_midnight(),
    )


async def check_counterview_limit(
    db: AsyncSession,
    user_id: str | UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Free daily cap on DIRECT (user-typed) counterviews. Pro/premium unlimited.

    Counts today's (UTC) counterview rows with source='direct' for this user —
    the row insert IS the counter (all statuses count; each direct POST writes
    exactly one row). Does NOT increment: the caller blocks BEFORE generation
    when not allowed, so a capped call costs zero LLM. The insight path
    (source='insight', app-deduped one-per-insight) never consumes this
    allowance. Mirrors check_rate_limit's shape.
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

    # next_utc_midnight() is tomorrow 00:00 UTC; minus a day = today 00:00 UTC.
    today_start = next_utc_midnight() - timedelta(days=1)
    result = await db.execute(
        select(func.count()).select_from(Counterview).where(
            Counterview.user_id == str(user_id),
            Counterview.source == "direct",
            Counterview.created_at >= today_start,
        )
    )
    count = int(result.scalar_one() or 0)
    remaining = max(0, FREE_DAILY_COUNTERVIEW_LIMIT - count)

    return RateLimitResult(
        allowed=count < FREE_DAILY_COUNTERVIEW_LIMIT,
        remaining=remaining,
        limit=FREE_DAILY_COUNTERVIEW_LIMIT,
        reset_at=next_utc_midnight(),
    )
