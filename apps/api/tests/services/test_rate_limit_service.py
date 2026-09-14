"""Tests for rate_limit_service.check_rate_limit — the free tier's GLOBAL daily
reply allowance.

A2, 2026-09-14 (Blueprint §3.4). This file used to pin a 5/day PER-PERSONA cap.
The founder-locked rule is now 10/day GLOBAL across every persona, and the tests
below were amended deliberately rather than deleted — each amended one says A2
and the date in its docstring, so a reader can tell an intentional change of rule
from a test that was quietly relaxed to go green.

THE ONE THAT INVERTED. `test_different_personas_tracked_separately` asserted that
Socrates at the cap left Marcus untouched. Under A2 that is exactly what must NOT
happen, so it became `test_two_personas_share_one_budget`. It is the same
scenario with the opposite expectation, which is the honest way to record a rule
change: the case did not disappear, its answer did.

THE MOCK CHANGED SHAPE, AND IT HAD TO (C-06). check_rate_limit no longer selects
a DailyUsage row via scalar_one_or_none(); it reads
coalesce(sum(message_count), 0) via scalar_one(). A helper still returning a row
would leave every test here passing against a call the service no longer makes —
the mock would answer a question nobody asks and stay silent about the one they
do. `_make_db` now returns the SUM.

All DB interactions are mocked; get_user_tier is bypassed via the user_tier kwarg.

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
    FREE_DAILY_LIMIT,
    FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA,
    check_go_deeper_limit,
    check_rate_limit,
    next_utc_midnight,
)

USER_A = UUID("aaaaaaaa-0000-0000-0000-000000000001")
USER_B = UUID("aaaaaaaa-0000-0000-0000-000000000002")
PERSONA_SOCRATES = UUID("bbbbbbbb-0000-0000-0000-000000000001")
PERSONA_MARCUS = UUID("bbbbbbbb-0000-0000-0000-000000000002")


def _make_db(total_messages=0):
    """Mock DB whose execute() returns the SUM of message_count for the day.

    A2: the shape follows the service. check_rate_limit reads
    coalesce(sum(...), 0) with scalar_one() — never a row — so this returns a
    scalar. coalesce means the no-rows case is 0 rather than None, and the
    default here says so: there is no `None` total to represent.
    """
    db = AsyncMock()
    r = MagicMock()
    r.scalar_one.return_value = total_messages
    db.execute = AsyncMock(return_value=r)
    return db


def _make_go_deeper_db(go_deeper_count=None):
    """Mock DB returning a DailyUsage ROW — the per-persona shape go-deeper reads.

    Kept deliberately different from _make_db above. Go-deeper is the one budget
    A2 did not make global, and a shared helper would hide that.
    """
    db = AsyncMock()
    r = MagicMock()
    if go_deeper_count is None:
        r.scalar_one_or_none.return_value = None
    else:
        usage = MagicMock()
        usage.go_deeper_count = go_deeper_count
        r.scalar_one_or_none.return_value = usage
    db.execute = AsyncMock(return_value=r)
    return db


# ── Free tier: the global budget ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_cap_is_ten_and_it_is_global():
    """A2, 2026-09-14: 10/day across ALL personas, replacing 5/day/persona."""
    assert FREE_DAILY_LIMIT == 10


@pytest.mark.asyncio
async def test_free_0_messages_allowed():
    """A2, 2026-09-14: remaining is now 10, not 5."""
    db = _make_db(total_messages=0)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 10
    assert result.limit == FREE_DAILY_LIMIT


@pytest.mark.asyncio
async def test_free_3_messages_allowed():
    """A2, 2026-09-14: 3 spent leaves 7, where it used to leave 2."""
    db = _make_db(total_messages=3)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 7
    assert result.limit == FREE_DAILY_LIMIT


@pytest.mark.asyncio
async def test_the_tenth_reply_is_allowed():
    """A2, 2026-09-14. The boundary from below: 9 spent means the 10th may be
    sent. `count` is the PRE-increment total, so 9 < 10 allows one more."""
    db = _make_db(total_messages=9)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is True
    assert result.remaining == 1


@pytest.mark.asyncio
async def test_the_eleventh_reply_is_refused():
    """A2, 2026-09-14. The boundary from above, and the test this file exists
    for: 10 spent is the cap, not one short of it."""
    db = _make_db(total_messages=10)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_over_the_limit_reports_zero_not_a_negative():
    """Defensive: a count past the cap (concurrent writes, or a cap lowered
    under existing usage) must clamp at 0 rather than render a negative
    allowance to the client."""
    db = _make_db(total_messages=14)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


# ── Pro tier ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pro_is_unaffected_by_the_global_cap():
    """A2 changes the FREE budget only. Pro returns the unlimited sentinel and
    never reads the table — asserted, because the early return is what makes the
    cap free-tier-only and a refactor could quietly drop it."""
    db = _make_db(total_messages=0)
    result = await check_rate_limit(db, USER_A, user_tier="pro")
    assert result.allowed is True
    assert result.remaining == -1
    assert result.limit == -1
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_pro_far_past_the_free_cap_is_still_unlimited():
    db = _make_db(total_messages=1000)
    result = await check_rate_limit(db, USER_A, user_tier="pro")
    assert result.allowed is True
    assert result.remaining == -1
    db.execute.assert_not_called()


# ── The rule that inverted ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_personas_share_one_budget():
    """A2, 2026-09-14. WAS test_different_personas_tracked_separately, which
    asserted the opposite: Socrates at the cap left Marcus with a full
    allowance.

    Amended rather than deleted, because the scenario still matters — it is the
    single most likely thing to regress if someone reintroduces a persona filter
    into the WHERE clause. The service now sums every persona row for the day, so
    6 with Socrates and 4 with Marcus is 10 spent and the next reply is refused
    whichever mind it is addressed to.
    """
    db = _make_db(total_messages=6 + 4)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is False
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_the_query_is_not_scoped_to_a_persona():
    """The other half of the test above, at the query rather than the arithmetic.

    A sum that still carried `persona_id == ...` would produce a per-persona cap
    of 10 and pass every count-based assertion here. So the WHERE clause is read:
    it filters on user and date, and on nothing else.
    """
    db = _make_db(total_messages=0)
    await check_rate_limit(db, USER_A, user_tier="free")

    sql = str(db.execute.await_args.args[0])
    assert "persona_id" not in sql
    assert "user_id" in sql and "usage_date" in sql
    assert "sum(" in sql.lower()


@pytest.mark.asyncio
async def test_check_rate_limit_takes_no_persona_argument():
    """A2 removed the parameter rather than leaving it unused. An accepted-but-
    ignored persona_id would imply a per-persona rule to every future caller and
    silently swallow one passed in good faith."""
    import inspect

    params = list(inspect.signature(check_rate_limit).parameters)
    assert "persona_id" not in params
    assert params == ["db", "user_id", "user_tier"]


# ── User isolation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_different_users_tracked_separately():
    """Unchanged by A2 — the budget went global across personas, not across
    people."""
    db_a = _make_db(total_messages=10)
    db_b = _make_db(total_messages=0)

    result_a = await check_rate_limit(db_a, USER_A, user_tier="free")
    result_b = await check_rate_limit(db_b, USER_B, user_tier="free")

    assert result_a.allowed is False
    assert result_b.allowed is True


# ── Go-deeper stays per persona ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_go_deeper_is_still_per_persona_and_still_three():
    """A2 did NOT touch this, and the brief said so explicitly. Pinned here
    because the two limits live side by side in one module and now read
    differently — the next person to "make them consistent" should fail a test
    rather than ship a product change.

    Go-deeper measures how far ONE thread has been pressed, so it belongs to the
    thread. The reply budget measures a day, so it belongs to the day.
    """
    assert FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA == 3

    db = _make_go_deeper_db(go_deeper_count=0)
    result = await check_go_deeper_limit(
        db, USER_A, PERSONA_SOCRATES, user_tier="free",
    )
    assert result.allowed is True
    assert result.limit == 3

    import inspect
    assert "persona_id" in inspect.signature(check_go_deeper_limit).parameters


# ── reset_at ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_at_is_next_utc_midnight():
    """Unchanged by A2. The window is still the UTC day; only its size changed."""
    db = _make_db(total_messages=0)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.reset_at == next_utc_midnight()
    assert result.reset_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_reset_at_is_the_same_for_a_blocked_user():
    """The client renders this on the paywall, so it must be present and correct
    on the refusal path — the one path where it is actually read."""
    db = _make_db(total_messages=10)
    result = await check_rate_limit(db, USER_A, user_tier="free")
    assert result.allowed is False
    assert result.reset_at == next_utc_midnight()


def test_next_utc_midnight_is_future():
    assert next_utc_midnight() > datetime.now(timezone.utc)
