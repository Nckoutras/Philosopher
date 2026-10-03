"""MEM2-B5 against a real Postgres: what the dedup write does to real rows.

Each test runs the REAL extract_memory_task — extraction, the B5 hook, B4's
recurrence, in their real order on one real session. The LLM, the embedder and
the judge are the only things stubbed; the judge's verdict is the input under
test, and its own calibration is pinned elsewhere (test_dedup_judge.py).

1. SUPERSESSION, BOTH DIRECTIONS. The loser is retired as 'superseded' and the
   SURVIVOR carries supersedes_memory_id = loser, whichever row survived.
2. ECHO INHERITANCE. Strength survives supersession, and both outcomes end at the
   same total: when the new row survives it carries the B4 echo the retirement
   hid; when the old row survives, B4 stamps it itself.
3. PROVENANCE GUARD. Only system_inferred chat rows are candidates: user_stated,
   user_selected and other surfaces are never judged, whatever their similarity.
4. FAIL-OPEN. A failed verdict retires nothing; a database error mid-write rolls
   back that row's savepoint, and the task's later steps still run on the session.
5. THE RATCHET GUARD, CHAIN DEPTH (CHAIN_DEPTH_SQL executed by a driver), and the
   within-call drop.

All of these are the FIRST RUN of new live checks (TD-45's corollary): an
assertion reaching a real database for the first time is unverified text.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_dedup_judge_live.py -v
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `live` is a fixture: importing it into this module makes it available here.
from test_memory_epistemic_core import _alembic, live  # noqa: E402,F401
from test_memory_recall_and_cascades import _make_conversation, _unit, _vec  # noqa: E402

from services import dedup_judge as dj  # noqa: E402

OLD = _unit(1.0, 0.0)
NEW = _unit(0.8, 0.6)           # 0.80 to OLD: over the 0.75 gate
NEWER = _unit(0.6, 0.8)         # 0.96 to NEW, 0.60 to OLD
T1 = datetime(2026, 9, 1, tzinfo=timezone.utc)   # a datetime, never an ISO string (TD-76)

OLD_TEXT = "User is grappling with how to manage grief."
NEW_TEXT = "User is processing grief over the loss of their grandmother."
NEWER_TEXT = "User grieves their grandmother and the home she kept."


def _v(verdict, spec="same", failed=False):
    return dj.DedupVerdict(verdict=verdict, more_specific=spec, failed=failed,
                           fail_kind="error" if failed else None, latency_ms=1)


async def _conv(live, uid):
    async with live.Session() as s:
        cid = await _make_conversation(s, uid)
        await s.commit()
    return cid


async def _stored(live, uid, conv, content, vec, *, provenance="system_inferred",
                  surface="chat", entry_type="struggle", echo=None, last=None,
                  supersedes=None, active=True, reason=None) -> str:
    mid = str(uuid.uuid4())
    async with live.Session() as s:
        await s.execute(
            text(
                "INSERT INTO memory_entries (id, user_id, conversation_id, entry_type,"
                " content, embedding, confidence, provenance, source_surface,"
                " echo_count, last_echo_at, supersedes_memory_id, is_active, inactive_reason)"
                f" VALUES (:id, :uid, :cid, :etype, :content, '{_vec(vec)}'::vector, 0.9,"
                " :prov, :surface, :echo, :last, :sup, :active, :reason)"
            ),
            {"id": mid, "uid": uid, "cid": conv, "etype": entry_type, "content": content,
             "prov": provenance, "surface": surface, "echo": echo, "last": last,
             "sup": supersedes, "active": active, "reason": reason},
        )
        await s.commit()
    return mid


async def _task(live, uid, conv, extracted, vectors, judge):
    """The real memory task, B5 switched on. `vectors` answer the embedder in
    order; `judge` stands in for dedup_judge.judge_pair."""
    from workers.arq_worker import extract_memory_task

    with patch("services.memory_service.llm_client.complete",
               AsyncMock(return_value=json.dumps(extracted))), \
         patch("services.memory_service.embedding_client.embed",
               AsyncMock(side_effect=list(vectors))), \
         patch("services.memory_service.output_is_unsafe", AsyncMock(return_value=False)), \
         patch.object(dj, "judge_pair", judge), \
         patch.object(dj.config, "MEMORY_DEDUP_ENABLED", True):
        await extract_memory_task({}, uid, conv, None, "I miss her.", "Tell me about her.",
                                  1, False, None)


def _one(content):
    return [{"type": "struggle", "content": content, "confidence": 0.85}]


async def _rows(live, uid):
    async with live.Session() as s:
        return {
            r.content: r for r in await s.execute(
                text(
                    "SELECT id::text AS id, content, is_active, inactive_reason,"
                    " supersedes_memory_id::text AS supersedes, echo_count, last_echo_at,"
                    " provenance, source_surface"
                    " FROM memory_entries WHERE user_id = :u"
                ),
                {"u": uid},
            )
        }


# ── 1 + 2. Supersession and echo inheritance ─────────────────────────────────

@pytest.mark.asyncio
async def test_the_new_row_survives_when_more_specific_and_inherits_the_old_rows_strength(live):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    old_id = await _stored(live, uid, conv_a, OLD_TEXT, OLD, echo=2, last=T1)
    judge = AsyncMock(return_value=_v("RESTATEMENT", "new"))
    before = datetime.now(timezone.utc)

    await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW], judge)

    judge.assert_awaited_once_with(OLD_TEXT, NEW_TEXT)
    rows = await _rows(live, uid)
    old, new = rows[OLD_TEXT], rows[NEW_TEXT]
    assert (old.is_active, old.inactive_reason) == (False, "superseded")
    assert (new.is_active, new.inactive_reason, new.supersedes) == (True, None, old_id)
    assert (new.provenance, new.source_surface) == ("system_inferred", "chat")
    # 2 inherited + the 1 that B4 would have stamped on the old row as an anchor.
    assert new.echo_count == 3
    assert new.last_echo_at >= before - timedelta(seconds=5)


@pytest.mark.asyncio
async def test_the_old_row_survives_when_more_specific_and_the_total_is_the_same(live):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    await _stored(live, uid, conv_a, NEW_TEXT, OLD, echo=2, last=T1)   # the specific one is old
    judge = AsyncMock(return_value=_v("RESTATEMENT", "earlier"))

    await _task(live, uid, conv_b, _one(OLD_TEXT), [NEW], judge)

    rows = await _rows(live, uid)
    survivor, loser = rows[NEW_TEXT], rows[OLD_TEXT]
    assert (loser.is_active, loser.inactive_reason) == (False, "superseded")
    assert (survivor.is_active, survivor.supersedes) == (True, loser.id), \
        "the survivor links to the row it replaced, even when the survivor is the old row"
    # 2 of its own, stamped +1 by B4: the retired new row still searches as a
    # query and finds it in another conversation. Same total as the test above.
    assert survivor.echo_count == 3


@pytest.mark.asyncio
async def test_a_same_conversation_old_row_carries_no_extra_echo_and_null_stays_null(live):
    uid = await live.make_user()
    conv = await _conv(live, uid)
    await _stored(live, uid, conv, OLD_TEXT, OLD)                 # never echoed
    await _task(live, uid, conv, _one(NEW_TEXT), [NEW],
                AsyncMock(return_value=_v("RESTATEMENT", "same")))
    rows = await _rows(live, uid)
    assert rows[OLD_TEXT].is_active is False
    assert (rows[NEW_TEXT].echo_count, rows[NEW_TEXT].last_echo_at) == (None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["DISTINCT", "CONTRADICTION"])
async def test_distinct_and_contradiction_keep_both_rows_untouched(live, verdict):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    await _stored(live, uid, conv_a, OLD_TEXT, OLD)
    await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW], AsyncMock(return_value=_v(verdict, "new")))
    rows = await _rows(live, uid)
    for r in rows.values():
        assert (r.is_active, r.inactive_reason, r.supersedes) == (True, None, None)


# ── 3. Provenance guard ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_only_system_inferred_chat_rows_are_ever_candidates(live):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    # Every one is IDENTICAL to the new row (similarity 1.0) and none may be judged.
    guarded = {
        "stated": dict(provenance="user_stated", surface="council", entry_type="stated"),
        "portrait": dict(provenance="user_selected", surface="self_portrait",
                         entry_type="self_portrait"),
        "shift": dict(provenance="system_inferred", surface="self_portrait",
                      entry_type="self_portrait_shift"),
        "belief": dict(provenance="user_stated", surface="counterview_belief",
                       entry_type="counterview_belief"),
        "legacy": dict(provenance=None, surface=None),
    }
    for name, kw in guarded.items():
        await _stored(live, uid, conv_a, f"guarded {name}", NEW, **kw)
    judge = AsyncMock(return_value=_v("RESTATEMENT", "new"))

    await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW], judge)

    judge.assert_not_awaited()
    for r in (await _rows(live, uid)).values():
        assert (r.is_active, r.inactive_reason, r.supersedes) == (True, None, None)


# ── 4. Fail-open ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_failed_verdict_retires_nothing(live):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    await _stored(live, uid, conv_a, OLD_TEXT, OLD)
    await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW],
                AsyncMock(return_value=_v(None, None, failed=True)))
    rows = await _rows(live, uid)
    assert set(rows) == {OLD_TEXT, NEW_TEXT}, "the new row is stored normally"
    for r in rows.values():
        assert (r.is_active, r.inactive_reason, r.supersedes) == (True, None, None)


@pytest.mark.asyncio
async def test_a_database_error_mid_write_rolls_back_the_savepoint_and_the_task_goes_on(live):
    """The first UPDATE (retire the old row) lands, then the write fails. The
    savepoint must undo the retirement, and B4 must still run on the same session
    afterwards — its +1 on the old row is the proof the session survived."""
    from services.memory_service import MemoryService

    original = MemoryService._supersede

    async def half_then_fail(self, db, user_id, entry, cand, loser):
        await db.execute(
            text("UPDATE memory_entries SET is_active = FALSE, inactive_reason = 'superseded'"
                 " WHERE id = :id"),
            {"id": cand.id},
        )
        raise RuntimeError("simulated failure after a partial write")

    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    await _stored(live, uid, conv_a, OLD_TEXT, OLD, echo=2, last=T1)
    with patch.object(MemoryService, "_supersede", half_then_fail):
        await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW],
                    AsyncMock(return_value=_v("RESTATEMENT", "new")))
    assert MemoryService._supersede is original

    rows = await _rows(live, uid)
    old, new = rows[OLD_TEXT], rows[NEW_TEXT]
    assert (old.is_active, old.inactive_reason) == (True, None), "the savepoint undid the retirement"
    assert (new.is_active, new.supersedes) == (True, None)
    assert old.echo_count == 3, "B4 ran after the failure, on the same session"


# ── 5. Ratchet guard, chain depth, within-call drop ──────────────────────────

@pytest.mark.asyncio
async def test_the_ratchet_guard_keeps_both_when_the_old_row_already_superseded_something(live):
    uid = await live.make_user()
    conv_a, conv_b = await _conv(live, uid), await _conv(live, uid)
    earlier = await _stored(live, uid, conv_a, "an even earlier restatement", _unit(0.0, 1.0),
                            active=False, reason="superseded")
    await _stored(live, uid, conv_a, OLD_TEXT, OLD, supersedes=earlier)
    await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW],
                AsyncMock(return_value=_v("RESTATEMENT", "earlier")))
    rows = await _rows(live, uid)
    assert (rows[OLD_TEXT].is_active, rows[OLD_TEXT].supersedes) == (True, earlier)
    assert (rows[NEW_TEXT].is_active, rows[NEW_TEXT].inactive_reason) == (True, None)


@pytest.mark.asyncio
async def test_chain_depth_is_logged_from_the_real_chain(live, caplog):
    uid = await live.make_user()
    conv_a, conv_b, conv_c = await _conv(live, uid), await _conv(live, uid), await _conv(live, uid)
    await _stored(live, uid, conv_a, OLD_TEXT, OLD)
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        await _task(live, uid, conv_b, _one(NEW_TEXT), [NEW],
                    AsyncMock(return_value=_v("RESTATEMENT", "new")))
        await _task(live, uid, conv_c, _one(NEWER_TEXT), [NEWER],
                    AsyncMock(return_value=_v("RESTATEMENT", "new")))
    lines = [r.getMessage() for r in caplog.records
             if r.getMessage().startswith("dedup_judge verdict=RESTATEMENT")]
    assert [l.split("chain_depth=")[1].split()[0] for l in lines] == ["1", "2"]
    rows = await _rows(live, uid)
    assert rows[NEWER_TEXT].supersedes == rows[NEW_TEXT].id
    assert rows[NEW_TEXT].supersedes == rows[OLD_TEXT].id


@pytest.mark.asyncio
async def test_a_within_call_duplicate_is_never_stored(live):
    uid = await live.make_user()
    conv = await _conv(live, uid)
    judge = AsyncMock()
    await _task(live, uid, conv, [
        {"type": "struggle", "content": NEW_TEXT, "confidence": 0.85},
        {"type": "pattern", "content": NEWER_TEXT, "confidence": 0.8},
    ], [NEW, NEW], judge)
    assert set(await _rows(live, uid)) == {NEW_TEXT}
    judge.assert_not_awaited()
