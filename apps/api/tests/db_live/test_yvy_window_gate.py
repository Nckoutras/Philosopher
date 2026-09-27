"""You-vs-You's crisis gate queries, against real rows (ruling 2026-09-25).

WHY THIS NEEDS A LIVE DATABASE. Both helpers are SQL with a time boundary and a join,
and a mocked session returns whatever it is told. What can go wrong is the boundary
(13 days vs 15), the level set (high/critical but not medium), whose messages count
(this person's, not another's), and NULL handling on conversation_id.

Run: cd apps/api && pytest tests/db_live/test_yvy_window_gate.py -v
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from services.self_comparison_service import self_comparison_service


async def _user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(text("INSERT INTO users (id, email) VALUES (:id, :e)"),
                     {"id": uid, "e": f"{uid}@example.test"})
    return uid


async def _conversation(db, uid) -> str:
    pid = str((await db.execute(text("SELECT id FROM personas LIMIT 1"))).scalar_one())
    cid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO conversations (id, user_id, persona_id) VALUES (:c, :u, :p)"),
        {"c": cid, "u": uid, "p": pid},
    )
    return cid


async def _message(db, uid, cid, level, days_ago):
    await db.execute(
        text("INSERT INTO messages (id, conversation_id, user_id, role, content, "
             "safety_level, created_at) VALUES (:id, :c, :u, 'user', 'text', :l, :t)"),
        {"id": str(uuid.uuid4()), "c": cid, "u": uid, "l": level,
         "t": datetime.now(timezone.utc) - timedelta(days=days_ago)},
    )


@pytest.mark.asyncio
async def test_a_high_flag_thirteen_days_ago_is_recent(db):
    uid = await _user(db)
    await _message(db, uid, await _conversation(db, uid), "high", 13)
    assert await self_comparison_service._recent_crisis(db, uid) is True


@pytest.mark.asyncio
async def test_a_critical_flag_fifteen_days_ago_is_not_recent(db):
    uid = await _user(db)
    await _message(db, uid, await _conversation(db, uid), "critical", 15)
    assert await self_comparison_service._recent_crisis(db, uid) is False


@pytest.mark.asyncio
async def test_a_medium_flag_yesterday_is_not_a_crisis(db):
    uid = await _user(db)
    await _message(db, uid, await _conversation(db, uid), "medium", 1)
    assert await self_comparison_service._recent_crisis(db, uid) is False


@pytest.mark.asyncio
async def test_another_persons_flag_does_not_count(db):
    uid, other = await _user(db), await _user(db)
    await _message(db, other, await _conversation(db, other), "high", 1)
    assert await self_comparison_service._recent_crisis(db, uid) is False


@pytest.mark.asyncio
async def test_flagged_conversations_are_every_thread_with_a_high_or_critical_message(db):
    uid = await _user(db)
    c_old = await _conversation(db, uid)
    c_clean = await _conversation(db, uid)
    c_medium = await _conversation(db, uid)
    await _message(db, uid, c_old, "high", 200)
    await _message(db, uid, c_clean, "none", 5)
    await _message(db, uid, c_medium, "medium", 5)
    flagged = await self_comparison_service._flagged_conversation_ids(db, uid)
    assert flagged == {c_old}


async def _memory(db, uid, cid, content, days_ago):
    await db.execute(
        text("INSERT INTO memory_entries (id, user_id, conversation_id, entry_type, "
             "content, confidence, created_at) VALUES (:id, :u, :c, 'struggle', :t, 0.9, :at)"),
        {"id": str(uuid.uuid4()), "u": uid, "c": cid, "t": content,
         "at": datetime.now(timezone.utc) - timedelta(days=days_ago)},
    )


@pytest.mark.asyncio
async def test_an_old_flagged_conversations_memory_is_absent_from_both_windows(db):
    """End to end on real rows, through the real types: the flagged set comes from
    _flagged_conversation_ids (asyncpg uuid -> ORM str), the entries from build()'s
    own query, and the exclusion must drop the flagged thread's rows from THEN and
    NOW while the unlock gate still counts them."""
    from services.self_model_service import self_model_service

    uid = await _user(db)
    flagged, clean = await _conversation(db, uid), await _conversation(db, uid)
    await _message(db, uid, flagged, "high", 200)          # old: excludes, never refuses
    await _memory(db, uid, flagged, "FLAGGED EARLIEST", 90)  # would be first in THEN
    await _memory(db, uid, flagged, "FLAGGED LATEST", 1)     # would be last in NOW
    for i in range(22):
        await _memory(db, uid, clean, f"clean {i}", 80 - i * 3)
    await db.flush()

    assert await self_comparison_service._recent_crisis(db, uid) is False
    excluded = await self_comparison_service._flagged_conversation_ids(db, uid)
    model = await self_model_service.build(db, uid, exclude_conversation_ids=excluded)

    assert model["unlocked"] is True
    assert model["total_signals"] == 24, "the gate counts the flagged rows too"
    shown = [s for w in ("then", "now") for v in model[w]["by_type"].values() for s in v]
    assert "FLAGGED EARLIEST" not in shown and "FLAGGED LATEST" not in shown
    assert "clean 0" in shown
