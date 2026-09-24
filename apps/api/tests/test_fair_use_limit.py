"""The Pro fair-use cap, and the two things it must never do.

WHY IT EXISTS. Cost protection, not a product limit. Measured 2026-09-02: the
heaviest real user-day was 81 messages / 36k tokens; an extreme-but-human daily
user costs EUR 5-9/month against EUR 11.99 of revenue. A bot on a compromised
Pro session costs whatever it likes. The cap turns the worst case into a support
conversation instead of a bill.

THE TWO THINGS IT MUST NEVER DO, both pinned below:

  1. Block a crisis message. #591 put the safety gate ahead of the rate limit
     because a person in crisis was being shown a paywall. Adding a second
     ceiling behind that gate must not quietly undo it — so the cap is checked
     only when the input did NOT trip safety, and a crisis message at 150/150
     still reaches the service.

  2. Touch a free user. Free accounts are already bounded four ways
     (check_rate_limit, go_deeper, deep_mode, counterview) and cannot approach
     150. Stacking a ceiling on the tier that cannot reach it would only add a
     way to be wrong.

COUNTING is option B: daily_usage.message_count + go_deeper_count summed across
personas (message_count is send-message only; go-deeper was uncounted until
2026-09-24; another-mind writes no daily_usage row and is still uncounted) PLUS
today's counterview rows. Counterviews are five
persona generations each and live in their own table; a cap that counted them
but did not enforce on them — or enforced without counting — would have an open
door beside it.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.rate_limit_service import (
    PRO_DAILY_FAIR_USE_LIMIT,
    check_fair_use_limit,
    next_utc_midnight,
    utc_today,
)


def _db(chat_used: int, counterviews_used: int):
    """A session that answers the check's two counting queries by shape."""
    db = MagicMock()

    async def execute(stmt, *a, **kw):
        text = str(stmt)
        result = MagicMock()
        if "daily_usage" in text:
            result.scalar_one.return_value = chat_used
        else:
            result.scalar_one.return_value = counterviews_used
        return result

    db.execute = AsyncMock(side_effect=execute)
    return db


# ── Free users are untouched ──────────────────────────────────────────────────

@pytest.mark.parametrize("tier", ["free", None, "unknown_future_tier"])
async def test_a_non_pro_tier_is_never_capped(tier):
    """Returns allowed unconditionally, and does not even count."""
    db = _db(chat_used=10_000, counterviews_used=10_000)
    result = await check_fair_use_limit(db, "u1", user_tier=tier or "free")
    assert result.allowed is True
    assert result.limit == -1
    db.execute.assert_not_awaited()


# ── The cap itself ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tier", ["pro", "premium"])
async def test_a_pro_user_under_the_cap_is_allowed(tier):
    db = _db(chat_used=80, counterviews_used=5)
    result = await check_fair_use_limit(db, "u1", user_tier=tier)
    assert result.allowed is True
    assert result.limit == PRO_DAILY_FAIR_USE_LIMIT == 150
    assert result.remaining == 150 - 85


async def test_exactly_at_the_cap_is_refused():
    """`used < limit` — the 150th message is allowed, the 151st is not."""
    at_cap = await check_fair_use_limit(_db(150, 0), "u1", user_tier="pro")
    assert at_cap.allowed is False
    assert at_cap.remaining == 0

    one_below = await check_fair_use_limit(_db(149, 0), "u1", user_tier="pro")
    assert one_below.allowed is True
    assert one_below.remaining == 1


async def test_counterviews_count_toward_the_same_cap():
    """The mutation: drop the counterview term and this fails.

    A direct counterview is five persona generations. Counted here because a
    path that spends tokens and is not counted becomes the way around the cap.
    """
    chat_only = await check_fair_use_limit(_db(140, 0), "u1", user_tier="pro")
    assert chat_only.allowed is True

    with_counterviews = await check_fair_use_limit(_db(140, 15), "u1", user_tier="pro")
    assert with_counterviews.allowed is False, (
        "counterviews are not being counted toward the fair-use cap"
    )


async def test_the_cap_is_generous_against_measured_reality():
    """81 messages was the heaviest real user-day ever recorded. A cap that
    refused it would be a bug in the number, not in the mechanism."""
    heaviest_real_day = await check_fair_use_limit(_db(81, 0), "u1", user_tier="pro")
    assert heaviest_real_day.allowed is True
    assert PRO_DAILY_FAIR_USE_LIMIT >= 81 * 1.5


async def test_the_reset_is_midnight_utc():
    result = await check_fair_use_limit(_db(0, 0), "u1", user_tier="pro")
    assert result.reset_at == next_utc_midnight()
    assert result.reset_at.tzinfo == timezone.utc
    assert (result.reset_at.hour, result.reset_at.minute) == (0, 0)


async def test_the_check_only_reads():
    """A refused call must cost nothing and consume nothing — the counters are
    written by the paths themselves."""
    db = _db(200, 0)
    await check_fair_use_limit(db, "u1", user_tier="pro")
    for call in db.execute.await_args_list:
        assert str(call.args[0]).lstrip().upper().startswith("SELECT")
    assert not db.commit.called


# ── utc_today: the latent midnight bug ────────────────────────────────────────

def test_utc_today_is_utc_not_server_local():
    assert utc_today() == datetime.now(timezone.utc).date()


def test_utc_today_follows_utc_and_not_the_server_clock():
    """The bug this replaces, demonstrated rather than described.

    date.today() reads the SERVER's clock. Under a non-UTC offset it can name a
    different day than the one the reset is computed against, so a user is told
    their allowance reset while the counter still reads yesterday's — or the
    reverse. Render runs UTC, which is why nobody has seen it.

    BOTH names are patched so they genuinely disagree. Patching only `datetime`
    let a `return date.today()` mutant survive: it never touched the patched
    name, and the host clock happened to agree with UTC.
    """
    import services.rate_limit_service as rls

    UTC_INSTANT = datetime(2026, 9, 2, 23, 30, tzinfo=timezone.utc)
    LOCAL_DAY = date(2026, 9, 3)          # what a UTC+13 host would call today

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return UTC_INSTANT

    class FakeDate(date):
        @classmethod
        def today(cls):
            return LOCAL_DAY

    with patch.object(rls, "datetime", FakeDatetime),          patch.object(rls, "date", FakeDate):
        got = rls.utc_today()

    assert got == date(2026, 9, 2), (
        f"utc_today() returned {got}, the SERVER's local day, not the UTC day"
    )
    assert got != LOCAL_DAY


def test_read_and_write_use_the_same_helper():
    """The read side (rate_limit_service) and the write side
    (conversation_service) must agree on which day a message belongs to. Pinned
    as source, because a divergence is invisible except for one hour a day on a
    host nobody is looking at."""
    import pathlib
    import services.conversation_service as cs

    src = pathlib.Path(cs.__file__).read_text(encoding="utf-8")
    assert "today = utc_today()" in src
    assert "today = date.today()" not in src, (
        "a daily_usage write still uses the server-local date"
    )


# ── The monthly ceiling (founder ruling 2026-09-24) ──────────────────────────
# 400 units per UTC calendar month over the same two sources. The daily cap is
# unchanged at 150 — the month is the cost ceiling, the day stays generous.

from services.rate_limit_service import (  # noqa: E402
    PRO_MONTHLY_FAIR_USE_LIMIT,
    next_utc_month_start,
)

TODAY = date(2026, 9, 24)
TOMORROW_MIDNIGHT = datetime(2026, 9, 25, tzinfo=timezone.utc)
MONTH_START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _db_windows(day_chat=0, day_cv=0, month_chat=0, month_cv=0):
    """Answers each counting query by table AND window. The window is read from
    the statement itself: the daily_usage day query compares usage_date with
    '=', the month one with '>='; the counterview queries differ by the bound
    lower edge (today 00:00 vs the 1st 00:00). TODAY is pinned mid-month so the
    two edges can never coincide."""
    db = MagicMock()
    seen = []

    async def execute(stmt, *a, **kw):
        text = str(stmt)
        params = stmt.compile().params
        result = MagicMock()
        if "daily_usage" in text:
            seen.append(text)
            monthly = "usage_date >=" in text
            result.scalar_one.return_value = month_chat if monthly else day_chat
        else:
            monthly = MONTH_START in params.values()
            result.scalar_one.return_value = month_cv if monthly else day_cv
        return result

    db.execute = AsyncMock(side_effect=execute)
    db.seen_daily_usage_sql = seen
    return db


@pytest.fixture
def pinned_today():
    with patch("services.rate_limit_service.utc_today", return_value=TODAY), \
         patch("services.rate_limit_service.next_utc_midnight", return_value=TOMORROW_MIDNIGHT):
        yield


async def test_the_daily_cap_is_still_150():
    """The 2026-09-24 ruling revised this back: 40/day would have refused a real
    subscriber twice (44 and 81 messages) without protecting anything the
    monthly cap does not."""
    assert PRO_DAILY_FAIR_USE_LIMIT == 150
    assert PRO_MONTHLY_FAIR_USE_LIMIT == 400


async def test_the_month_refuses_when_the_day_would_not(pinned_today):
    db = _db_windows(day_chat=10, month_chat=395, month_cv=5)   # 400 this month
    result = await check_fair_use_limit(db, "u1", user_tier="pro")
    assert result.allowed is False
    assert result.period == "month"
    assert result.limit == 400
    assert result.remaining == 0
    assert result.reset_at == datetime(2026, 10, 1, tzinfo=timezone.utc)


async def test_one_below_the_monthly_cap_is_allowed_and_reports_the_day(pinned_today):
    """Under both ceilings the DAILY result comes back — the month is a ceiling,
    not the budget a user sees day to day."""
    db = _db_windows(day_chat=10, month_chat=399)
    result = await check_fair_use_limit(db, "u1", user_tier="pro")
    assert result.allowed is True
    assert result.period == "day"
    assert result.limit == 150
    assert result.remaining == 140


async def test_the_day_is_named_first_when_both_are_exhausted(pinned_today):
    """The refusal names the window that resets soonest."""
    db = _db_windows(day_chat=150, month_chat=500)
    result = await check_fair_use_limit(db, "u1", user_tier="pro")
    assert result.allowed is False
    assert result.period == "day"
    assert result.reset_at == TOMORROW_MIDNIGHT


async def test_counterviews_count_toward_the_month(pinned_today):
    """The mutation: drop the counterview term from the month and this fails."""
    db = _db_windows(month_chat=390, month_cv=10)
    result = await check_fair_use_limit(db, "u1", user_tier="pro")
    assert result.period == "month" and result.allowed is False


async def test_go_deeper_is_counted_in_both_windows(pinned_today):
    """go-deeper bumps go_deeper_count and never message_count, so until
    2026-09-24 it spent tokens at the cap without moving the counter. Both the
    day and the month sums must include it."""
    db = _db_windows()
    await check_fair_use_limit(db, "u1", user_tier="pro")
    assert len(db.seen_daily_usage_sql) == 2
    for sql in db.seen_daily_usage_sql:
        assert "go_deeper_count" in sql, sql
        assert "message_count" in sql, sql


async def test_another_mind_is_counted_in_both_windows(pinned_today):
    """TD-100: another-mind wrote no daily_usage row and was refused at the cap
    without moving it. It now has its own column (069), summed here."""
    db = _db_windows()
    await check_fair_use_limit(db, "u1", user_tier="pro")
    assert len(db.seen_daily_usage_sql) == 2
    for sql in db.seen_daily_usage_sql:
        assert "another_mind_count" in sql, sql


async def test_the_free_allowance_does_not_read_the_pro_only_counters():
    """The reason another-mind got a column instead of a message_count bump: the
    FREE daily allowance sums message_count. If it ever read another_mind_count
    (or go_deeper_count), a Pro cost change would have tightened a free limit."""
    from services.rate_limit_service import check_rate_limit

    seen = []
    db = MagicMock()

    async def execute(stmt, *a, **kw):
        seen.append(str(stmt))
        result = MagicMock()
        result.scalar_one.return_value = 0
        return result

    db.execute = AsyncMock(side_effect=execute)
    await check_rate_limit(db, "u1", user_tier="free")
    assert len(seen) == 1
    assert "message_count" in seen[0]
    assert "another_mind_count" not in seen[0]
    assert "go_deeper_count" not in seen[0]


async def test_a_free_user_is_not_counted_monthly_either():
    db = _db_windows(month_chat=10_000)
    result = await check_fair_use_limit(db, "u1", user_tier="free")
    assert result.allowed is True
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("today,expected", [
    (date(2026, 9, 24), datetime(2026, 10, 1, tzinfo=timezone.utc)),
    (date(2026, 12, 31), datetime(2027, 1, 1, tzinfo=timezone.utc)),
    (date(2027, 1, 1), datetime(2027, 2, 1, tzinfo=timezone.utc)),
])
def test_the_month_resets_at_the_first_00_00_utc(today, expected):
    with patch("services.rate_limit_service.utc_today", return_value=today):
        assert next_utc_month_start() == expected
