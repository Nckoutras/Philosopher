"""TD-100 — another-mind's counter, against real rows (migration 069).

WHY THIS NEEDS A LIVE DATABASE. The counter is an INSERT ... ON CONFLICT DO
UPDATE on daily_usage's composite primary key. A mocked session accepts any
statement and returns whatever it is told, so the parts that can actually break
here are invisible to it: whether the conflict target matches the real key,
whether the increment reads the EXISTING row, and what a new row holds in the
columns the statement does not name. A query is not verified until a driver has
executed it (CLAUDE.md, 2026-09-15).

WHAT IS PINNED:
  1. First write creates the row at 1; a second increments it — no PK collision,
     which the select-then-add pattern elsewhere can hit.
  2. It lands on a row a send-message already wrote and moves ONLY
     another_mind_count. message_count is what the free allowance sums.
  3. The Pro fair-use check counts it; the free check does not.

Run: cd apps/api && pytest tests/db_live/test_another_mind_count.py -v
"""
import uuid

import pytest
from sqlalchemy import text

from services.conversation_service import another_mind_usage_upsert
from services.rate_limit_service import (
    PRO_DAILY_FAIR_USE_LIMIT,
    check_fair_use_limit,
    check_rate_limit,
    utc_today,
)


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _any_persona_id(db) -> str:
    """Any row satisfies the FK; the migration chain inserts at least six."""
    row = (await db.execute(text("SELECT id FROM personas ORDER BY slug LIMIT 1"))).first()
    assert row is not None, "the migration chain inserted no personas"
    return str(row[0])


async def _counters(db, uid, pid):
    return (await db.execute(
        text(
            "SELECT message_count, go_deeper_count, deep_mode_count, another_mind_count "
            "FROM daily_usage WHERE user_id = :u AND persona_id = :p AND usage_date = :d"
        ),
        {"u": uid, "p": pid, "d": utc_today()},
    )).all()


@pytest.mark.asyncio
async def test_first_write_creates_the_row_and_the_second_increments_it(db):
    uid, pid = await _make_user(db), await _any_persona_id(db)

    await db.execute(another_mind_usage_upsert(uid, pid, utc_today()))
    assert await _counters(db, uid, pid) == [(0, 0, 0, 1)]

    await db.execute(another_mind_usage_upsert(uid, pid, utc_today()))
    assert await _counters(db, uid, pid) == [(0, 0, 0, 2)]


@pytest.mark.asyncio
async def test_it_joins_a_send_message_row_without_touching_message_count(db):
    uid, pid = await _make_user(db), await _any_persona_id(db)
    await db.execute(
        text(
            "INSERT INTO daily_usage (user_id, persona_id, usage_date, message_count) "
            "VALUES (:u, :p, :d, 3)"
        ),
        {"u": uid, "p": pid, "d": utc_today()},
    )

    await db.execute(another_mind_usage_upsert(uid, pid, utc_today()))

    assert await _counters(db, uid, pid) == [(3, 0, 0, 1)]


@pytest.mark.asyncio
async def test_the_pro_cap_counts_it_and_the_free_allowance_does_not(db):
    uid, pid = await _make_user(db), await _any_persona_id(db)
    await db.execute(
        text(
            "INSERT INTO daily_usage (user_id, persona_id, usage_date, message_count) "
            "VALUES (:u, :p, :d, 3)"
        ),
        {"u": uid, "p": pid, "d": utc_today()},
    )
    for _ in range(4):
        await db.execute(another_mind_usage_upsert(uid, pid, utc_today()))

    pro = await check_fair_use_limit(db, uid, user_tier="pro")
    assert pro.remaining == PRO_DAILY_FAIR_USE_LIMIT - (3 + 4)

    free = await check_rate_limit(db, uid, user_tier="free")
    assert free.remaining == free.limit - 3   # another-mind is not a free-tier unit
