"""MEM2-B2 — verdict reversal against a real Postgres (migration 072).

What needs the server, and is therefore here rather than behind a mock:

1. 072'S SCHEMA. The two columns, the FK's ON DELETE SET NULL, the partial index,
   and a down-and-up that actually removes and restores them.
2. verdict_history IS WRITTEN. A JSONB column is not mutation-tracked; an
   in-place append would pass against a mock and never reach the row.
3. REACTIVATION'S PREDICATE. Only 'user_rejected' rows return. 'superseded' and
   'user_removed' never do, another person's rows are never touched, a row another
   insight retired returns (Q5), and a dismissed insight returns nothing.
4. THE 72h GUARD, through the real handler with its clock pinned: exactly 72h
   enqueues the shift task, one second under does not, and the legacy fallback
   reads ring_true_at.
5. THE SHIFT TASK'S ROW, committed and read back with a fresh session: its
   metadata, its supersession of the previous shift, its refusal to write when
   the verdict has gone back to 'no', and the later 'no' that retires it.
6. THE TWO EXCLUSIONS. A shift row neither counts toward the You-vs-You unlock
   nor reaches the self-portrait summary's signals.

Several of these are the FIRST RUN of new live checks (TD-45's corollary): an
assertion reaching a real database for the first time is unverified text.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_verdict_shift_live.py -v
"""
import asyncio
import os
from contextlib import nullcontext
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `live` is a fixture: importing it into this module makes it available here.
from test_memory_epistemic_core import (  # noqa: E402,F401
    FAKE_EMBEDDING, _alembic, _evidence, _insert_row, _insight, _rows, live,
)

SHIFT = "insight_verdict_shift"
T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def _request(queue=None):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(arq_queue=queue)))


def _queue():
    return SimpleNamespace(enqueue_job=AsyncMock())


async def _verdict(live, uid, iid, verdict, *, at=None, queue=None):
    """The real handler, with its clock pinned to `at` when given."""
    from routers.memory import set_insight_ring_true
    from schemas import InsightRingTrueRequest

    clock = patch("routers.memory._utcnow", return_value=at) if at else nullcontext()
    with patch("routers.memory.analytics_service"), clock:
        async with live.Session() as s:
            return await set_insight_ring_true(
                iid, InsightRingTrueRequest(ring_true=verdict), request=_request(queue),
                db=s, user=SimpleNamespace(id=uid),
            )


async def _scalar(live, sql, **params):
    async with live.Session() as s:
        return (await s.execute(text(sql), params)).scalar_one()


def _shift_calls(queue):
    return [c for c in queue.enqueue_job.await_args_list if c.args[0] == "record_verdict_shift_task"]


# ── 1. Schema ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_072_adds_two_nullable_columns_with_a_set_null_fk_and_a_partial_index(db):
    cols = {
        (r.table_name, r.column_name): (r.data_type, r.is_nullable)
        for r in await db.execute(text(
            "SELECT table_name, column_name, data_type, is_nullable"
            " FROM information_schema.columns WHERE table_schema = 'public'"
            " AND (table_name, column_name) IN"
            " (('insights', 'verdict_history'), ('memory_entries', 'source_insight_id'))"
        ))
    }
    assert cols == {
        ("insights", "verdict_history"): ("jsonb", "YES"),
        ("memory_entries", "source_insight_id"): ("uuid", "YES"),
    }

    rule = (await db.execute(text(
        "SELECT rc.delete_rule FROM information_schema.referential_constraints rc"
        " WHERE rc.constraint_name = 'fk_memory_entries_source_insight'"
    ))).scalar_one()
    assert rule == "SET NULL"

    indexdef = (await db.execute(text(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_memory_entries_source_insight_id'"
    ))).scalar_one()
    assert "(source_insight_id)" in indexdef
    assert "WHERE (source_insight_id IS NOT NULL)" in indexdef


@pytest.mark.asyncio
async def test_deleting_an_insight_unlinks_its_shift_row_rather_than_deleting_it(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        mid = await _insert_row(s, uid, SHIFT, source_insight_id=iid)
        await s.commit()
    async with live.Session() as s:
        await s.execute(text("DELETE FROM insights WHERE id = :i"), {"i": iid})
        await s.commit()

    link = await _scalar(
        live, "SELECT source_insight_id FROM memory_entries WHERE id = :m", m=mid,
    )
    assert link is None


def _072_columns(url: str) -> set[tuple[str, str]]:
    async def fetch():
        conn = await asyncpg.connect(url.replace("+asyncpg", ""))
        try:
            rows = await conn.fetch(
                "SELECT table_name, column_name FROM information_schema.columns"
                " WHERE table_schema = 'public' AND column_name IN"
                " ('verdict_history', 'source_insight_id')"
            )
            return {(r["table_name"], r["column_name"]) for r in rows}
        finally:
            await conn.close()

    return asyncio.run(fetch())


def test_072_downgrades_cleanly_and_upgrades_again(schema):
    """Always returned to head, so a failure cannot leave the session on 071."""
    expected = {("insights", "verdict_history"), ("memory_entries", "source_insight_id")}
    try:
        _alembic(schema, "downgrade", "071_memory_provenance_backfill")
        assert _072_columns(schema) == set(), "072 downgrade left a column behind"
    finally:
        _alembic(schema, "upgrade", "head")
    assert _072_columns(schema) == expected


# ── 2. verdict_history ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_every_verdict_is_appended_to_history_in_order(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()

    times = [T0, T0 + timedelta(hours=1), T0 + timedelta(hours=2)]
    for verdict, at in zip(["yes", "partly", "no"], times):
        await _verdict(live, uid, iid, verdict, at=at)

    async with live.Session() as s:
        row = (await s.execute(
            text("SELECT verdict_history, ring_true, ring_true_at FROM insights WHERE id = :i"),
            {"i": iid},
        )).one()
    assert row.verdict_history == [
        {"verdict": "yes", "at": "2026-09-01T09:00:00Z"},
        {"verdict": "partly", "at": "2026-09-01T10:00:00Z"},
        {"verdict": "no", "at": "2026-09-01T11:00:00Z"},
    ]
    assert (row.ring_true, row.ring_true_at) == ("no", times[-1]), "current state is the last"


@pytest.mark.asyncio
async def test_a_legacy_insight_starts_its_history_at_the_first_verdict_after_072(live):
    """No backfill: a verdict given before 072 is not reconstructed into history."""
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.execute(
            text("UPDATE insights SET ring_true = 'yes', ring_true_at = :t WHERE id = :i"),
            {"i": iid, "t": T0},
        )
        await s.commit()

    await _verdict(live, uid, iid, "partly", at=T0 + timedelta(days=1))
    history = await _scalar(live, "SELECT verdict_history FROM insights WHERE id = :i", i=iid)
    assert history == [{"verdict": "partly", "at": "2026-09-02T09:00:00Z"}]


# ── 3. Reactivation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yes_returns_only_user_rejected_rows_of_this_person(live):
    uid = await live.make_user()
    other = await live.make_user()
    async with live.Session() as s:
        recurring = await _insert_row(s, uid, "struggle")
        prior = await _insert_row(s, uid, "pattern")
        superseded = await _insert_row(s, uid, "self_portrait", is_active=False,
                                       inactive_reason="superseded")
        removed = await _insert_row(s, uid, "belief", is_active=False,
                                    inactive_reason="user_removed")
        theirs = await _insert_row(s, other, "struggle", is_active=False,
                                   inactive_reason="user_rejected")
        iid = await _insight(s, uid, _evidence(recurring, prior, superseded, removed, theirs))
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "no", at=T0, queue=queue)
    mine = {r.id: r for r in await _rows(live.Session, uid)}
    assert (mine[recurring].is_active, mine[recurring].inactive_reason) == (False, "user_rejected")

    # An instant flip: plain reactivation, no shift record.
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(minutes=2), queue=queue)

    mine = {r.id: r for r in await _rows(live.Session, uid)}
    assert (mine[recurring].is_active, mine[recurring].inactive_reason) == (True, None)
    assert (mine[prior].is_active, mine[prior].inactive_reason) == (True, None)
    assert (mine[superseded].is_active, mine[superseded].inactive_reason) == (False, "superseded")
    assert (mine[removed].is_active, mine[removed].inactive_reason) == (False, "user_removed")
    (their_row,) = await _rows(live.Session, other)
    assert (their_row.is_active, their_row.inactive_reason) == (False, "user_rejected"), \
        "never another person's row"

    assert _shift_calls(queue) == [], "under 72h is plain reactivation"
    assert [r for r in await _rows(live.Session, uid) if r.entry_type == SHIFT] == []


@pytest.mark.asyncio
async def test_a_yes_on_another_insight_citing_the_row_brings_it_back(live):
    """Q5: insight X retires the row, insight Y also cites it, a 'yes' on Y
    returns it, although Y never had a 'no'."""
    uid = await live.make_user()
    async with live.Session() as s:
        shared = await _insert_row(s, uid, "struggle")
        x = await _insight(s, uid, _evidence(shared))
        y = await _insight(s, uid, _evidence(shared))
        await s.commit()

    await _verdict(live, uid, x, "no", at=T0)
    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (False, "user_rejected")

    queue = _queue()
    await _verdict(live, uid, y, "yes", at=T0 + timedelta(days=5), queue=queue)
    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (True, None)
    assert _shift_calls(queue) == [], "Y had no 'no': no pair on the SAME insight"


@pytest.mark.asyncio
async def test_a_dismissed_insight_reactivates_nothing(live):
    uid = await live.make_user()
    async with live.Session() as s:
        row = await _insert_row(s, uid, "struggle", is_active=False,
                                inactive_reason="user_rejected")
        iid = await _insight(s, uid, _evidence(row))
        await s.execute(text("UPDATE insights SET is_dismissed = true WHERE id = :i"), {"i": iid})
        await s.commit()

    await _verdict(live, uid, iid, "yes", at=T0)
    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (False, "user_rejected")


@pytest.mark.asyncio
async def test_a_dismissed_insight_owes_no_shift_entry(live):
    """A dismissed card is silent everywhere (founder ruling 2026-10-03): a no→yes
    pair well past 72h enqueues nothing and writes no row. The verdict and its
    history are still recorded."""
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "no", at=T0, queue=queue)
    async with live.Session() as s:
        await s.execute(text("UPDATE insights SET is_dismissed = true WHERE id = :i"), {"i": iid})
        await s.commit()
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=10), queue=queue)

    assert _shift_calls(queue) == []
    assert await _shift_rows(live, uid) == []
    history = await _scalar(live, "SELECT verdict_history FROM insights WHERE id = :i", i=iid)
    assert [h["verdict"] for h in history] == ["no", "yes"]


@pytest.mark.asyncio
async def test_partly_reactivates_nothing(live):
    uid = await live.make_user()
    async with live.Session() as s:
        row = await _insert_row(s, uid, "struggle", is_active=False,
                                inactive_reason="user_rejected")
        iid = await _insight(s, uid, _evidence(row))
        await s.commit()

    await _verdict(live, uid, iid, "partly", at=T0)
    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (False, "user_rejected")


# ── 4. The 72h guard ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("gap, owed", [
    (timedelta(hours=72), True),
    (timedelta(hours=72) - timedelta(seconds=1), False),
])
async def test_the_guard_at_its_boundary(live, gap, owed):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "no", at=T0, queue=queue)
    await _verdict(live, uid, iid, "yes", at=T0 + gap, queue=queue)

    calls = _shift_calls(queue)
    if owed:
        (call,) = calls
        assert call.args == ("record_verdict_shift_task", uid, iid, 3)
    else:
        assert calls == []


@pytest.mark.asyncio
async def test_no_partly_yes_is_anchored_on_the_no(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "no", at=T0, queue=queue)
    await _verdict(live, uid, iid, "partly", at=T0 + timedelta(days=2), queue=queue)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=4), queue=queue)

    (call,) = _shift_calls(queue)
    assert call.args[-1] == 4


@pytest.mark.asyncio
async def test_a_legacy_no_anchors_on_ring_true_at(live):
    """No history (the 'no' predates 072): ring_true_at loaded in-request anchors."""
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.execute(
            text("UPDATE insights SET ring_true = 'no', ring_true_at = :t WHERE id = :i"),
            {"i": iid, "t": T0},
        )
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=10), queue=queue)
    (call,) = _shift_calls(queue)
    assert call.args == ("record_verdict_shift_task", uid, iid, 10)


@pytest.mark.asyncio
async def test_a_repeated_yes_owes_no_second_shift(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()

    queue = _queue()
    await _verdict(live, uid, iid, "no", at=T0, queue=queue)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=3), queue=queue)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=9), queue=queue)
    assert len(_shift_calls(queue)) == 1


# ── 5. The shift task ────────────────────────────────────────────────────────

async def _run_task(uid, iid, days):
    from workers.arq_worker import record_verdict_shift_task

    with patch("services.embedding_client.embedding_client.embed",
               AsyncMock(return_value=FAKE_EMBEDDING)):
        await record_verdict_shift_task({}, uid, iid, days)


async def _shift_rows(live, uid):
    async with live.Session() as s:
        return list(await s.execute(
            text(
                "SELECT id::text AS id, content, confidence, is_active, inactive_reason,"
                " provenance, source_surface, source_insight_id::text AS source_insight_id,"
                " supersedes_memory_id::text AS supersedes, persona_id, conversation_id,"
                " embedding IS NOT NULL AS embedded"
                " FROM memory_entries WHERE user_id = :u AND entry_type = :t"
                " ORDER BY created_at, id"
            ),
            {"u": uid, "t": SHIFT},
        ))


@pytest.mark.asyncio
async def test_the_shift_row_carries_the_ruled_metadata(live):
    from services.memory_service import STANDING_TYPES

    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()
    await _verdict(live, uid, iid, "no", at=T0)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=12))

    await _run_task(uid, iid, 12)

    (row,) = await _shift_rows(live, uid)
    assert row.content == (
        "They came to accept, after 12 days, an observation they had first "
        "rejected: “This theme keeps returning.”"
    )
    assert row.provenance == "system_inferred"
    assert row.source_surface == "insight"
    assert row.source_insight_id == iid
    assert row.confidence == pytest.approx(0.8)
    assert (row.is_active, row.inactive_reason, row.supersedes) == (True, None, None)
    assert (row.persona_id, row.conversation_id) == (None, None)
    assert row.embedded, "its own embed, or recall can never find it"
    assert SHIFT not in STANDING_TYPES, "Lane B by the catch-all"


@pytest.mark.asyncio
async def test_a_newer_shift_supersedes_the_previous_one_for_the_same_insight(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        other_iid = await _insight(s, uid, None)
        other_shift = await _insert_row(s, uid, SHIFT, source_insight_id=other_iid)
        await s.execute(text("UPDATE insights SET ring_true = 'yes' WHERE id = :i"), {"i": iid})
        await s.commit()

    await _run_task(uid, iid, 4)
    await _run_task(uid, iid, 20)

    rows = {r.id: r for r in await _shift_rows(live, uid)}
    mine = [r for r in rows.values() if r.source_insight_id == iid]
    (old,) = [r for r in mine if "after 4 days" in r.content]
    (new,) = [r for r in mine if "after 20 days" in r.content]
    assert (old.is_active, old.inactive_reason) == (False, "superseded")
    assert (new.is_active, new.supersedes) == (True, old.id)
    assert rows[other_shift].is_active, "another insight's shift row is not touched"


@pytest.mark.asyncio
async def test_the_task_writes_nothing_once_the_verdict_has_gone_back_to_no(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()
    await _verdict(live, uid, iid, "no", at=T0)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=5))
    await _verdict(live, uid, iid, "no", at=T0 + timedelta(days=5, minutes=1))

    await _run_task(uid, iid, 5)
    assert await _shift_rows(live, uid) == []


@pytest.mark.asyncio
async def test_the_task_writes_nothing_once_the_card_is_dismissed(live):
    """Dismissed between the enqueue and the run: still silent."""
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.execute(
            text("UPDATE insights SET ring_true = 'yes', is_dismissed = true WHERE id = :i"),
            {"i": iid},
        )
        await s.commit()

    await _run_task(uid, iid, 5)
    assert await _shift_rows(live, uid) == []


@pytest.mark.asyncio
async def test_the_task_never_writes_for_another_persons_insight(live):
    uid = await live.make_user()
    other = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, other, None)
        await s.execute(text("UPDATE insights SET ring_true = 'yes' WHERE id = :i"), {"i": iid})
        await s.commit()

    await _run_task(uid, iid, 5)
    assert await _shift_rows(live, uid) == []
    assert await _shift_rows(live, other) == []


@pytest.mark.asyncio
async def test_a_later_no_retires_the_active_shift_row(live):
    uid = await live.make_user()
    async with live.Session() as s:
        iid = await _insight(s, uid, None)
        await s.commit()
    await _verdict(live, uid, iid, "no", at=T0)
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=3))
    await _run_task(uid, iid, 3)

    await _verdict(live, uid, iid, "no", at=T0 + timedelta(days=8))
    (row,) = await _shift_rows(live, uid)
    assert (row.is_active, row.inactive_reason) == (False, "user_rejected")

    # And a 'yes' does not bring it back: it is linked, not cited.
    await _verdict(live, uid, iid, "yes", at=T0 + timedelta(days=8, minutes=1))
    (row,) = await _shift_rows(live, uid)
    assert (row.is_active, row.inactive_reason) == (False, "user_rejected")


# ── 6. The exclusions ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_shift_row_neither_unlocks_you_vs_you_nor_reaches_the_summary(live):
    from services.self_model_service import SelfModelService
    from services.self_portrait_summary import _recent_signals

    uid = await live.make_user()
    async with live.Session() as s:
        for _ in range(3):
            await _insert_row(s, uid, SHIFT, source_insight_id=await _insight(s, uid, None))
        await s.commit()

    async with live.Session() as s:
        model = await SelfModelService().build(s, uid, bypass_gate=True)
        signals = await _recent_signals(s, uid)
    assert model["total_signals"] == 0
    assert signals == []
