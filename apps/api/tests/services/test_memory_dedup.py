"""MEM2-B5: write-time dedup in the memory service, against a mocked session.

What a mock CAN pin, and is therefore here; the SQL's effect on real rows is in
tests/db_live/test_dedup_judge_live.py.

1. CANDIDATE GATING. The judge is asked only about candidates at >=
   DUPLICATE_SIM_THRESHOLD, at most DEDUP_CANDIDATE_LIMIT per new row, and only
   for a new row that is itself a system_inferred chat row. The candidate SQL
   names the provenance and surface it is limited to.
2. ONE RETIREMENT PER NEW ROW, the RATCHET GUARD, and chain_depth on the line.
3. FAIL-OPEN: a failed verdict writes nothing; a database error rolls back the
   row's SAVEPOINT, never the session.
4. MECHANISM 1: a within-call duplicate at >= 0.90 is dropped before it is stored.
5. THE HOOK: the memory task runs extract -> dedup -> recurrence -> signal.

Every mock sets every field the code reads (C-06): candidates and entries are
plain SimpleNamespace objects, so an unset attribute raises instead of answering.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.memory_service as ms
from services import dedup_judge as dj
from services.memory_service import (
    DEDUP_CANDIDATE_LIMIT,
    DEDUP_CANDIDATE_SQL,
    DUPLICATE_SIM_THRESHOLD,
    ExtractionResult,
    inherited_echo,
    memory_service,
)

USER = "11111111-1111-1111-1111-111111111111"
CONV = "22222222-2222-2222-2222-222222222222"
OTHER_CONV = "33333333-3333-3333-3333-333333333333"


def _entry(**kw):
    base = dict(id=str(uuid.uuid4()), embedding=[0.1] * 4, content="new row",
                provenance="system_inferred", source_surface="chat", conversation_id=CONV)
    base.update(kw)
    return SimpleNamespace(**base)


def _cand(score, *, supersedes=None, conv=OTHER_CONV, echo=None, last=None):
    return SimpleNamespace(id=str(uuid.uuid4()), content=f"stored {score}",
                           conversation_id=conv, supersedes_memory_id=supersedes,
                           echo_count=echo, last_echo_at=last, score=score)


def _v(verdict, spec="new", failed=False):
    return dj.DedupVerdict(verdict=verdict, more_specific=spec, failed=failed,
                           fail_kind="error" if failed else None, latency_ms=1)


class FakeDB:
    """Answers the candidate SELECT with `candidates`, the chain-depth query with
    `depth`, and every UPDATE with rowcount 1 (or `fail_on_update` raises)."""

    def __init__(self, candidates=(), depth=1, fail_on_update=False):
        self.candidates = list(candidates)
        self.depth = depth
        self.fail_on_update = fail_on_update
        self.statements = []
        self.params = []
        self.savepoints = []
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def begin_nested(self):
        sp = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
        self.savepoints.append(sp)
        return sp

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        self.statements.append(sql)
        # An ORM update() carries its values in the statement, not in `params`.
        self.params.append(params if params is not None else dict(stmt.compile().params))
        if "WITH RECURSIVE" in sql:
            return SimpleNamespace(scalar_one=lambda: self.depth)
        if "provenance = 'system_inferred'" in sql:
            return SimpleNamespace(fetchall=lambda: list(self.candidates))
        if self.fail_on_update:
            raise RuntimeError("update failed")
        return SimpleNamespace(rowcount=1)

    @property
    def updates(self):
        return [s for s in self.statements if s.lstrip().upper().startswith("UPDATE")]


async def _dedup(db, entries, verdicts, enabled=True):
    judge = AsyncMock(side_effect=list(verdicts))
    with patch.object(ms.dedup_judge, "judge_pair", judge), \
         patch.object(dj.config, "MEMORY_DEDUP_ENABLED", enabled):
        n = await memory_service.dedup_new_entries(db, USER, entries)
    return n, judge


# ── 1. Candidate gating ──────────────────────────────────────────────────────

def test_the_candidate_sql_is_limited_to_system_inferred_chat_rows():
    sql = " ".join(DEDUP_CANDIDATE_SQL.split())
    assert "AND provenance = 'system_inferred'" in sql
    assert "AND source_surface = 'chat'" in sql
    assert "AND is_active = TRUE" in sql
    assert "AND id <> ALL(:exclude_ids)" in sql
    assert sql.endswith(f"LIMIT {DEDUP_CANDIDATE_LIMIT}") and DEDUP_CANDIDATE_LIMIT == 3


@pytest.mark.asyncio
async def test_the_kill_switch_touches_nothing():
    db = FakeDB([_cand(0.95)])
    n, judge = await _dedup(db, [_entry()], [], enabled=False)
    assert n == 0 and db.statements == [] and db.savepoints == []
    judge.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("override", [
    {"provenance": "user_stated"},
    {"provenance": "user_selected"},
    {"source_surface": "self_portrait"},
    {"embedding": None},
    {"id": None},
])
async def test_a_new_row_that_is_not_a_system_inferred_chat_row_is_never_judged(override):
    db = FakeDB([_cand(0.95)])
    n, judge = await _dedup(db, [_entry(**override)], [])
    assert n == 0 and db.statements == []
    judge.assert_not_awaited()


@pytest.mark.asyncio
async def test_only_candidates_at_or_over_the_gate_reach_the_judge():
    below = DUPLICATE_SIM_THRESHOLD - 0.001
    cands = [_cand(0.90), _cand(DUPLICATE_SIM_THRESHOLD), _cand(below)]
    db = FakeDB(cands)
    entry = _entry()
    n, judge = await _dedup(db, [entry], [_v("DISTINCT"), _v("DISTINCT")])
    assert n == 0 and db.updates == []
    assert [c.args for c in judge.await_args_list] == [
        (cands[0].content, entry.content), (cands[1].content, entry.content),
    ], "stored row first, new row second — the measured order"


@pytest.mark.asyncio
async def test_this_calls_own_rows_are_excluded_from_every_search():
    a, b = _entry(), _entry()
    db = FakeDB([])
    await _dedup(db, [a, b], [])
    selects = [p for p in db.params if p and "exclude_ids" in p]
    assert len(selects) == 2
    for p in selects:
        assert p["exclude_ids"] == [uuid.UUID(a.id), uuid.UUID(b.id)]
        assert p["user_id"] == USER


# ── 2. One retirement per row, the ratchet guard, chain depth ────────────────

@pytest.mark.asyncio
async def test_a_new_row_stops_after_its_first_retirement():
    db = FakeDB([_cand(0.92), _cand(0.88)], depth=1)
    n, judge = await _dedup(db, [_entry()], [_v("RESTATEMENT", "new")])
    assert n == 1 and judge.await_count == 1
    assert len(db.updates) == 2  # retire the old row, link + echo on the survivor
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_old_survives_when_it_is_more_specific():
    db = FakeDB([_cand(0.92)])
    n, _ = await _dedup(db, [_entry()], [_v("RESTATEMENT", "earlier")])
    assert n == 1
    link, retire = db.updates
    assert "supersedes_memory_id" in link and "is_active=false" not in link.replace(" ", "").lower()
    assert "inactive_reason" in retire


@pytest.mark.asyncio
async def test_ratchet_guard_keeps_both_when_the_stored_row_already_superseded_something(caplog):
    """Amendment 1: RESTATEMENT + "earlier" on a row that already carries a link
    is treated as DISTINCT before any write, and the next candidate is still read."""
    guarded = _cand(0.93, supersedes=str(uuid.uuid4()))
    nxt = _cand(0.80)
    db = FakeDB([guarded, nxt])
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        n, judge = await _dedup(db, [_entry()], [_v("RESTATEMENT", "earlier"), _v("DISTINCT")])
    assert n == 0 and db.updates == []
    assert judge.await_count == 2, "the guard skips the pair, not the row"
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("dedup_judge ")]
    assert any(f"candidate={guarded.id}" in l and "kept=both" in l and "retired=none" in l
               and "note=dedup_ratchet_guard" in l for l in lines)


@pytest.mark.asyncio
async def test_ratchet_guard_does_not_block_the_new_row_from_winning():
    """The guard is about the OLD row absorbing again. A linked old row may still
    be retired by a more specific new one: the chain then runs new -> old -> ..."""
    db = FakeDB([_cand(0.93, supersedes=str(uuid.uuid4()))], depth=2)
    n, _ = await _dedup(db, [_entry()], [_v("RESTATEMENT", "new")])
    assert n == 1 and len(db.updates) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("spec, kept, retired", [("new", "new", "old"), ("earlier", "old", "new")])
async def test_every_retirement_logs_chain_depth_on_the_one_template(spec, kept, retired, caplog):
    cand = _cand(0.91)
    entry = _entry()
    db = FakeDB([cand], depth=3)
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        await _dedup(db, [entry], [_v("RESTATEMENT", spec)])
    (line,) = [r.getMessage() for r in caplog.records if r.getMessage().startswith("dedup_judge ")]
    assert line == (
        f"dedup_judge verdict=RESTATEMENT kept={kept} retired={retired} user={USER}"
        f" new={entry.id} candidate={cand.id} score=0.910 more_specific={spec}"
        f" chain_depth=3 note=-"
    )
    survivor = entry.id if kept == "new" else cand.id
    (depth_params,) = [p for p in db.params if p and "survivor_id" in p]
    assert depth_params == {"survivor_id": survivor}


@pytest.mark.asyncio
async def test_a_contradiction_keeps_both_and_is_flagged_at_warning(caplog):
    db = FakeDB([_cand(0.85)])
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        n, _ = await _dedup(db, [_entry()], [_v("CONTRADICTION", "same")])
    assert n == 0 and db.updates == []
    (rec,) = [r for r in caplog.records if r.getMessage().startswith("dedup_judge ")]
    assert rec.levelno == logging.WARNING
    assert "verdict=CONTRADICTION kept=both retired=none" in rec.getMessage()
    assert "chain_depth=-" in rec.getMessage()


# ── 3. Fail-open ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_failed_verdict_retires_nothing_and_stops_that_row(caplog):
    db = FakeDB([_cand(0.95), _cand(0.90)])
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        n, judge = await _dedup(db, [_entry()], [_v(None, None, failed=True)])
    assert n == 0 and db.updates == [] and judge.await_count == 1
    assert any("dedup_judge verdict=error kept=both retired=none" in r.getMessage()
               for r in caplog.records)


@pytest.mark.asyncio
async def test_a_database_error_rolls_back_the_savepoint_not_the_session(caplog):
    db = FakeDB([_cand(0.95)], fail_on_update=True)
    with caplog.at_level(logging.ERROR, logger="services.memory_service"):
        n, _ = await _dedup(db, [_entry(), _entry()], [_v("RESTATEMENT", "new")])
    assert n == 0
    (sp,) = db.savepoints  # stopped after the first row
    sp.rollback.assert_awaited_once()
    sp.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()  # a session rollback would expire the new rows
    errs = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert any(r.exc_info for r in errs)


# ── Echo inheritance (pure) ──────────────────────────────────────────────────

T1 = datetime(2026, 9, 1, tzinfo=timezone.utc)
T2 = T1 + timedelta(days=3)
NOW = T1 + timedelta(days=30)


@pytest.mark.parametrize("args, expected", [
    ((None, None, None, None), (None, None)),          # never echoed stays NULL
    ((None, None, 2, T1), (2, T1)),                    # the loser's strength carries over
    ((1, T2, 2, T1), (3, T2)),                         # counts add, later stamp wins
    ((None, None, None, None, NOW), (1, NOW)),         # the B4 echo the retirement hid
    ((None, None, 2, T1, NOW), (3, NOW)),
])
def test_inherited_echo(args, expected):
    assert inherited_echo(*args) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("conv, carried", [(OTHER_CONV, 3), (CONV, 2), (None, 2)])
async def test_the_b4_echo_is_carried_only_for_a_cross_conversation_old_row(conv, carried):
    db = FakeDB([_cand(0.9, conv=conv, echo=2, last=T1)])
    await _dedup(db, [_entry()], [_v("RESTATEMENT", "new")])
    survivor_update = [p for p in db.params if p and "echo_count" in p]
    assert survivor_update and survivor_update[0]["echo_count"] == carried


# ── 4. Mechanism 1: within-call drop ─────────────────────────────────────────

EXTRACTION = json.dumps([
    {"type": "struggle", "content": "User feels stuck at work.", "confidence": 0.85},
    {"type": "pattern", "content": "User keeps feeling stuck at work.", "confidence": 0.8},
])


def _recording_db():
    added = []
    db = AsyncMock()
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.flush = AsyncMock()
    return db, added


A = [1.0, 0.0, 0.0]
NEAR_A = [0.95, (1 - 0.95 ** 2) ** 0.5, 0.0]     # cosine 0.95 with A
APART = [0.85, (1 - 0.85 ** 2) ** 0.5, 0.0]      # cosine 0.85: under 0.90, kept


@pytest.mark.asyncio
@pytest.mark.parametrize("second, enabled, stored", [
    (NEAR_A, True, 1),     # >= 0.90 in one call: dropped
    (A, True, 1),
    (APART, True, 2),      # 0.75..0.90 inside one call is NOT judged, and not dropped
    (NEAR_A, False, 2),    # switch off: the pre-B5 path exactly
])
async def test_a_within_call_duplicate_is_dropped_before_it_is_stored(second, enabled, stored):
    db, added = _recording_db()
    with patch("services.memory_service.llm_client.complete", new=AsyncMock(return_value=EXTRACTION)), \
         patch("services.memory_service.embedding_client.embed", new=AsyncMock(side_effect=[A, second])), \
         patch.object(dj.config, "MEMORY_DEDUP_ENABLED", enabled):
        result = await memory_service.extract_and_store(
            db, USER, CONV, "p1", "I feel stuck.", "reply", promote_signal=False,
        )
    assert len(result) == stored == len(added)
    assert added[0].content == "User feels stuck at work.", "the earlier item is kept"


# ── 5. The hook ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_task_runs_dedup_after_the_commit_and_before_recurrence():
    from workers import arq_worker as aw

    order = []
    result = ExtractionResult([_entry()])
    result.signals, result.language, result.safety_ok = [], "English", True

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock(side_effect=lambda: order.append("commit"))

    async def extract(**kw):
        order.append("extract")
        return result

    async def dedup(db, user_id, entries):
        order.append("dedup")
        assert entries == list(result)
        return 0

    async def recurrence(**kw):
        order.append("recurrence")

    async def promote(*a, **kw):
        order.append("signal")
        return False

    with patch("db.session.AsyncSessionLocal", return_value=session), \
         patch.object(ms.memory_service, "extract_and_store", new=extract), \
         patch.object(ms.memory_service, "dedup_new_entries", new=dedup), \
         patch.object(ms.memory_service, "detect_recurrence", new=recurrence), \
         patch.object(ms.memory_service, "promote_signal_insight", new=promote):
        await aw.extract_memory_task({}, USER, CONV, "p1", "text", "reply", 1, True, None)

    assert order == ["extract", "commit", "dedup", "recurrence", "signal"]


def test_dedup_is_not_gated_by_the_insight_budgets():
    import inspect
    src = inspect.getsource(memory_service.dedup_new_entries) + inspect.getsource(memory_service._dedup_one)
    assert "_insight_gate_blocked" not in src


# ── 6. The silent path (B5.1) ────────────────────────────────────────────────

def _silent_lines(caplog):
    return [r for r in caplog.records if "verdict=no_candidates" in r.getMessage()]


@pytest.mark.asyncio
async def test_a_run_with_no_judge_call_logs_exactly_one_summary_line(caplog):
    """rows= counts the new rows that were searched: the user_stated row is not."""
    db = FakeDB([_cand(DUPLICATE_SIM_THRESHOLD - 0.001)])
    entries = [_entry(), _entry(), _entry(provenance="user_stated")]
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        n, judge = await _dedup(db, entries, [])
    assert n == 0
    judge.assert_not_awaited()
    (rec,) = [r for r in caplog.records if r.getMessage().startswith("dedup_judge ")]
    assert rec.levelno == logging.INFO
    assert rec.getMessage() == (
        f"dedup_judge verdict=no_candidates kept=all retired=none user={USER} rows=2"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", [_v("DISTINCT"), _v(None, None, failed=True)])
async def test_a_run_with_a_judge_call_does_not_log_the_summary_line(verdict, caplog):
    db = FakeDB([_cand(0.90)])
    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        _, judge = await _dedup(db, [_entry()], [verdict])
    assert judge.await_count == 1
    assert _silent_lines(caplog) == []


@pytest.mark.asyncio
async def test_the_kill_switch_logs_nothing(caplog):
    db = FakeDB([_cand(0.10)])
    with caplog.at_level(logging.DEBUG, logger="services.memory_service"):
        await _dedup(db, [_entry()], [], enabled=False)
    assert [r for r in caplog.records if r.name == "services.memory_service"] == []


@pytest.mark.asyncio
async def test_a_run_that_fails_before_any_judge_call_does_not_claim_no_candidates(caplog):
    """A failed run is not "ran and found nothing": its error line covers it."""
    class FailingSelect(FakeDB):
        async def execute(self, stmt, params=None):
            raise RuntimeError("select failed")

    with caplog.at_level(logging.INFO, logger="services.memory_service"):
        n, _ = await _dedup(FailingSelect(), [_entry()], [])
    assert n == 0
    assert _silent_lines(caplog) == []
    assert any("verdict=error" in r.getMessage() for r in caplog.records)
