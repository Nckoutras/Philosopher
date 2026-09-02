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

COUNTING is option B: daily_usage.message_count summed across personas (chat,
another-mind, go-deeper) PLUS today's counterview rows. Counterviews are five
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
