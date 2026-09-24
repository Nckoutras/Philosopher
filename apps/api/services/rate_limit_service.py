"""
Rate limiting utilities.

Redis-backed atomic counters for OTP/auth flows (check_and_increment).
DB-backed daily limits for the free tier, read from daily_usage.

WHICH BUDGETS ARE GLOBAL AND WHICH ARE PER-PERSONA — the distinction is the thing
to get right when adding another, so it is stated once here rather than inferred
from four function bodies:

  check_rate_limit        replies       GLOBAL per user/day  (A2, was per-persona)
  check_deep_mode_limit   deep replies  GLOBAL per user/day
  check_counterview_limit counterviews  GLOBAL per user/day  (no persona exists)
  check_go_deeper_limit   go-deepers    PER PERSONA per day

Go-deeper is the odd one out on purpose: it measures how far a single thread has
been pressed, which belongs to the thread. Everything else is a budget for the
day. daily_usage remains keyed (user_id, persona_id, usage_date) either way —
global budgets SUM those rows, they do not replace them.
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

# A2 (Blueprint §3.4, founder-locked 2026-09-14). GLOBAL across all personas —
# 10 replies/day, not 5 per persona. There is no monthly cap.
#
# WHAT CHANGED, IN BOTH DIRECTIONS, because "10 replacing 5" sounds purely like a
# loosening and for one case it is not. There are 3 free personas, so the old
# ceiling was 3 x 5 = 15/day for someone spreading across all of them, and 5/day
# for someone staying with one mind. The new ceiling is 10 either way: DOUBLE for
# the single-mind user, and a third less for the sampler. That is the intended
# shape — the product's value is depth with one mind, not breadth across three,
# and a ceiling that paid out for spreading thin was rewarding the wrong thing.
# 10 still allows 3+3+4 across three personas for anyone who wants it.
#
# NOBODY LIVING IS AFFECTED. Measured against production 2026-09-14: no free user
# has ever exceeded 9 messages in a day (6 free user-days on record, heaviest 9),
# and every user-day above 10 belongs to a Pro account, which this cap never
# touches.
FREE_DAILY_LIMIT = 10

# Free users get a taste of depth: N go-deepers per persona per day, then a
# gentle upgrade wall. Pro/premium are unlimited. Quantity only — the depth of
# each free go-deeper is identical to Pro (see _deepen_directive).
#
# STILL PER-PERSONA, deliberately, and A2 did not touch it: the go-deeper budget
# is about how far one thread can be pressed, so it belongs to the thread rather
# than to the day.
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
    # Which window this result describes. Only check_fair_use_limit ever sets
    # "month"; every other budget in this module is daily and keeps the default.
    period: str = "day"


def next_utc_midnight() -> datetime:
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)


def utc_month_start() -> date:
    """The first day of the current UTC month — where a monthly budget begins."""
    return utc_today().replace(day=1)


def next_utc_month_start() -> datetime:
    """00:00 UTC on the first of next month — when a monthly budget resets."""
    first = utc_month_start()
    year, month = (first.year + 1, 1) if first.month == 12 else (first.year, first.month + 1)
    return datetime(year, month, 1, tzinfo=timezone.utc)


def utc_today() -> date:
    """Today's date in UTC — the day a quota belongs to.

    Replaces date.today(), which returns the SERVER's local date. Every reset in
    this module is computed as next_utc_midnight(), so a host on any non-UTC
    clock counted usage against one day and reset it on another: for up to the
    length of the offset each midnight, a user could be told their allowance had
    reset while the counter it reads was still yesterday's, or the reverse.
    Render runs UTC today, which is why nobody has seen it — the bug is latent,
    not absent, and it costs one function to remove.

    Read and write MUST agree: services/conversation_service.py increments
    daily_usage with this same helper.
    """
    return datetime.now(timezone.utc).date()


# ── Pro fair-use cap ──────────────────────────────────────────────────────────
# Cost protection, not a product limit. Measured 2026-09-02: the heaviest real
# user-day was 81 messages / 36k tokens, and an extreme-but-human daily user
# costs EUR 5-9/month against EUR 11.99 of revenue. A bot on a compromised Pro
# session costs whatever it likes. This cap makes the worst case a support
# conversation instead of an unbounded bill.
#
# 150 is ~1.85x the heaviest day ever observed and ~4x the average. The
# asymmetry runs opposite to the safety lexicon's: a false positive here BLOCKS
# A PAYING CUSTOMER, so the number is deliberately generous and the copy
# deliberately non-punitive.
PRO_DAILY_FAIR_USE_LIMIT = 150

# The monthly ceiling (founder ruling 2026-09-24). THIS is the cost cap; the daily
# one above stays generous so an intense day is never refused on its own account.
#
# Per calendar month in UTC, not per billing period: subscriptions carries no
# period start, a yearly plan's billing period is a year (400 a YEAR is not the
# ruling), and comp grants have no period at all. The cost of the choice is that
# a user who subscribes on the 28th gets a fresh 400 on the 1st.
#
# WHAT 400 COSTS, measured 2026-09-24 against the 66 production replies that
# carry token components (2026-08-28..09-23): per Pro reply 1430 input + 1113
# cache-write + 1089 cache-read + 76 output tokens = $0.0099 at Sonnet 4.6 rates
# ($3 / $3.75 / $0.30 / $15 per MTok). 400 replies = $3.97/month ($4.35 at p90
# reply size), against EUR 11.99 monthly or ~EUR 8.33 on the yearly plan. For
# comparison, 150/day x 30 with no monthly cap was $44.69. The heaviest real
# month on record is 137 messages (~$1.36).
#
# Replies only: memory extraction, embeddings and counterviews are NOT priced in.
# A counterview counts as one unit here but is five generations, and their tokens
# are not stored — so a month spent entirely on counterviews is unmeasured.
PRO_MONTHLY_FAIR_USE_LIMIT = 400


async def check_rate_limit(
    db: AsyncSession,
    user_id: str | UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Free daily reply allowance — GLOBAL across all personas (A2).

    Reads SUM(daily_usage.message_count) for this user TODAY and compares against
    FREE_DAILY_LIMIT. Pro/premium are unlimited (remaining -1). Does NOT
    increment — conversation_service bumps message_count on the per-persona row
    after a successful reply.

    THE WRITE PATH IS UNCHANGED AND STAYS PER-PERSONA. daily_usage is keyed
    (user_id, persona_id, usage_date) and still is; A2 changed only how the rows
    are READ. Per-persona rows are what daily_usage is for elsewhere — go-deeper
    meters one of them, and the export renders them — so collapsing the table
    would have cost those for nothing.

    NO persona_id PARAMETER, deliberately. It was here when the limit was
    per-persona; a global check that still accepted one would be an unused
    argument implying a per-persona rule, which is the exact confusion A2
    removes. The signature now matches check_deep_mode_limit, the sibling this
    mirrors — that one has been a global daily budget over the same table since
    035.

    The sum runs on ix_daily_usage_lookup (user_id, usage_date), which already
    existed for precisely this shape of read.
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
        select(func.coalesce(func.sum(DailyUsage.message_count), 0)).where(
            DailyUsage.user_id == str(user_id),
            DailyUsage.usage_date == utc_today(),
        )
    )
    count = int(result.scalar_one() or 0)
    remaining = max(0, FREE_DAILY_LIMIT - count)

    return RateLimitResult(
        allowed=count < FREE_DAILY_LIMIT,
        remaining=remaining,
        limit=FREE_DAILY_LIMIT,
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
            DailyUsage.usage_date == utc_today(),
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
            DailyUsage.usage_date == utc_today(),
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


async def check_fair_use_limit(
    db: AsyncSession,
    user_id: str | UUID,
    user_tier: str | None = None,
) -> RateLimitResult:
    """Pro/premium caps — daily, then monthly — across the paths that spend tokens.

    FREE USERS ARE UNAFFECTED and return allowed unconditionally — they are
    already bounded by check_rate_limit, check_go_deeper_limit,
    check_deep_mode_limit and check_counterview_limit, and stacking a second
    ceiling on the tier that cannot exceed the first would only add a way to be
    wrong.

    COUNTS TWO SOURCES, because one is not enough:
      daily_usage.message_count + go_deeper_count + another_mind_count, SUMMED
        across personas — the per-(user, persona, day) rows the chat paths
        write. Each path has its own column: send-message bumps message_count,
        go-deeper go_deeper_count, another-mind another_mind_count (069). All
        three are added here; before 2026-09-24 only the first was, and the
        other two were refused at the cap without ever moving it.
        The free limits read none of the latter two — which is why another-mind
        got a column of its own rather than a message_count bump.
      counterviews — five persona generations each, in their own table,
        counted nowhere else. Left out, the cap has an uncapped door beside it,
        and an abuse channel that exists is the one that gets used.

    THE SAME TWO SOURCES over two windows: today (PRO_DAILY_FAIR_USE_LIMIT) and
    the UTC calendar month (PRO_MONTHLY_FAIR_USE_LIMIT). The day is checked
    first, so a refusal names the window that will reset soonest. When both
    allow, the DAILY result is returned — the month is a ceiling, not the budget
    a user sees from one day to the next.

    Because both windows read the same counters, the monthly cap inherits every
    exemption the daily one has: a crisis message, a ritual reply and a failed
    generation increment nothing, so they consume nothing from either.

    NOT counted: rituals (cron-seeded, and the chat increment already skips
    them), letters and mirrors (cron-driven, not user-triggerable), council and
    self-comparison (already bounded weekly for every tier, including Pro).

    Reads only. The counters are written by the paths themselves, so a call that
    is refused costs nothing and consumes nothing.
    """
    if user_tier is None:
        from services.tier_service import get_user_tier
        user_tier = await get_user_tier(db, user_id)

    if user_tier not in ("pro", "premium"):
        return RateLimitResult(
            allowed=True, remaining=-1, limit=-1, reset_at=next_utc_midnight(),
        )

    # next_utc_midnight() is tomorrow 00:00 UTC; minus a day is today 00:00 UTC.
    # Same expression check_counterview_limit uses, so the two agree on the day.
    today_start = next_utc_midnight() - timedelta(days=1)
    day_used = await _fair_use_units(
        db, user_id,
        DailyUsage.usage_date == utc_today(),
        Counterview.created_at >= today_start,
    )
    daily = RateLimitResult(
        allowed=day_used < PRO_DAILY_FAIR_USE_LIMIT,
        remaining=max(0, PRO_DAILY_FAIR_USE_LIMIT - day_used),
        limit=PRO_DAILY_FAIR_USE_LIMIT,
        reset_at=next_utc_midnight(),
    )
    if not daily.allowed:
        return daily

    month_start = utc_month_start()
    month_used = await _fair_use_units(
        db, user_id,
        DailyUsage.usage_date >= month_start,
        Counterview.created_at >= datetime(
            month_start.year, month_start.month, 1, tzinfo=timezone.utc
        ),
    )
    if month_used >= PRO_MONTHLY_FAIR_USE_LIMIT:
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=PRO_MONTHLY_FAIR_USE_LIMIT,
            reset_at=next_utc_month_start(),
            period="month",
        )
    return daily


async def _fair_use_units(db: AsyncSession, user_id, usage_window, counterview_window) -> int:
    """Units the fair-use caps count, over one window. See check_fair_use_limit."""
    chat_used = (await db.execute(
        select(func.coalesce(
            func.sum(
                DailyUsage.message_count
                + DailyUsage.go_deeper_count
                + DailyUsage.another_mind_count
            ), 0
        )).where(
            DailyUsage.user_id == str(user_id),
            usage_window,
        )
    )).scalar_one()
    counterviews_used = (await db.execute(
        select(func.count()).select_from(Counterview).where(
            Counterview.user_id == str(user_id),
            counterview_window,
        )
    )).scalar_one()
    return int(chat_used) + int(counterviews_used)
