"""MEM2-B1: two insight budgets, recurrence first (founder rulings 2026-10-03).

WHAT STARVED RECURRENCE. One throttle counted every non-dismissed insight, and the
memory task wrote the signal card before it looked for a recurrence. Production,
read 2026-10-03: 32 insights, 28 signals, 4 patterns — all 4 older than evidence
(060), so no recurrence card had been written since #642.

THREE PINS. (1) The gate filters by CLASS: the SQL it issues for kind="recurrence"
names pattern/shift and not belief, and vice versa — asserted on the compiled
statement, not on a docstring. (2) extract_and_store writes no card when asked to
defer, and returns what the deferred promotion needs. (3) The task calls the three
steps in the order extract → recurrence → signal.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

import services.memory_service as ms
from services.memory_service import (
    INSIGHT_CLASSES,
    RECURRENCE_INSIGHT_TYPES,
    SIGNAL_INSIGHT_TYPES,
    ExtractionResult,
    memory_service,
)

USER = "11111111-1111-1111-1111-111111111111"
CONV = "22222222-2222-2222-2222-222222222222"


def _compile(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def _db_answering(first_hit: bool, second_hit: bool):
    """A session whose two gate SELECTs answer in order; the statements are kept."""
    db = AsyncMock()
    seen = []

    async def execute(stmt, *a, **kw):
        seen.append(stmt)
        res = MagicMock()
        hit = first_hit if len(seen) == 1 else second_hit
        res.scalar_one_or_none.return_value = "some-id" if hit else None
        return res

    db.execute = execute
    return db, seen


# ── (1) the two budgets ──────────────────────────────────────────────────────

def test_the_classes_partition_the_types_the_product_writes():
    assert set(RECURRENCE_INSIGHT_TYPES) == {"pattern", "shift"}
    assert set(SIGNAL_INSIGHT_TYPES) == {"dilemma", "belief", "aspiration"}
    assert not set(RECURRENCE_INSIGHT_TYPES) & set(SIGNAL_INSIGHT_TYPES)
    assert set(INSIGHT_CLASSES) == {"recurrence", "signal"}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind, present, absent", [
    ("recurrence", ("pattern", "shift"), ("belief", "dilemma", "aspiration")),
    ("signal", ("belief", "dilemma", "aspiration"), ("pattern", "shift")),
])
async def test_the_gate_counts_only_its_own_class(kind, present, absent):
    db, seen = _db_answering(first_hit=False, second_hit=False)
    blocked = await memory_service._insight_gate_blocked(db, USER, CONV, kind=kind)
    assert blocked is None
    assert len(seen) == 2, "throttle query, then the per-conversation query"
    for stmt in seen:
        sql = _compile(stmt)
        assert "insight_type IN" in sql
        for t in present:
            assert f"'{t}'" in sql
        for t in absent:
            assert f"'{t}'" not in sql
    assert "is_dismissed" in _compile(seen[0]), "the 6h window still counts only non-dismissed rows"


@pytest.mark.asyncio
async def test_a_hit_in_the_window_is_a_throttle():
    db, _ = _db_answering(first_hit=True, second_hit=False)
    assert await memory_service._insight_gate_blocked(db, USER, CONV, kind="recurrence") == "throttle"


@pytest.mark.asyncio
async def test_a_hit_in_the_conversation_is_per_conversation():
    db, _ = _db_answering(first_hit=False, second_hit=True)
    assert await memory_service._insight_gate_blocked(db, USER, CONV, kind="signal") == "per_conversation"


@pytest.mark.asyncio
async def test_a_null_conversation_skips_the_per_conversation_rule():
    db, seen = _db_answering(first_hit=False, second_hit=True)
    assert await memory_service._insight_gate_blocked(db, USER, None, kind="signal") is None
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_an_unknown_kind_is_a_programming_error_not_a_silent_allow():
    db, _ = _db_answering(first_hit=False, second_hit=False)
    with pytest.raises(KeyError):
        await memory_service._insight_gate_blocked(db, USER, CONV, kind="everything")


# ── (2) deferral: extract_and_store writes no card when asked not to ────────

EXTRACTION = json.dumps([
    {"type": "belief", "content": "I need to prove myself to have worth.", "confidence": 0.9},
    {"type": "struggle", "content": "User struggles with proving themselves.", "confidence": 0.8},
])


def _recording_db():
    added = []
    db = AsyncMock()
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.flush = AsyncMock()
    return db, added


@pytest.mark.asyncio
async def test_deferred_extraction_saves_rows_writes_no_card_and_carries_the_signals():
    db, added = _recording_db()
    with patch("services.memory_service.llm_client.complete", new=AsyncMock(return_value=EXTRACTION)), \
         patch("services.memory_service.embedding_client.embed", new=AsyncMock(return_value=[0.0] * 1536)), \
         patch.object(memory_service, "_insight_gate_blocked", new=AsyncMock(return_value=None)) as gate:
        result = await memory_service.extract_and_store(
            db, USER, CONV, "p1", "I need to prove myself.", "reply",
            source_turn=1, safety_ok=True, promote_signal=False,
        )
    assert isinstance(result, ExtractionResult) and isinstance(result, list)
    # belief and struggle are both memory-row types (only dilemma/aspiration are
    # insight-only), so two rows — and no Insight, because promotion was deferred.
    assert [type(o).__name__ for o in added] == ["MemoryEntry", "MemoryEntry"]
    assert len(result) == 2
    assert result.safety_ok is True and result.language
    assert [s["type"] for s in result.signals] == ["belief", "struggle"]
    gate.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_extraction_still_promotes_inline_for_every_other_caller():
    db, added = _recording_db()
    with patch("services.memory_service.llm_client.complete", new=AsyncMock(return_value=EXTRACTION)), \
         patch("services.memory_service.embedding_client.embed", new=AsyncMock(return_value=[0.0] * 1536)), \
         patch("services.memory_service.output_is_unsafe", new=AsyncMock(return_value=False)), \
         patch.object(memory_service, "_insight_gate_blocked", new=AsyncMock(return_value=None)) as gate:
        await memory_service.extract_and_store(
            db, USER, CONV, "p1", "I need to prove myself.", "reply", source_turn=1, safety_ok=True,
        )
    assert [type(o).__name__ for o in added] == ["MemoryEntry", "MemoryEntry", "Insight"]
    assert gate.await_args.kwargs == {"kind": "signal"}


@pytest.mark.asyncio
async def test_promotion_spends_the_signal_budget_and_reports_the_write():
    db, added = _recording_db()
    signals = json.loads(EXTRACTION)
    with patch("services.memory_service.output_is_unsafe", new=AsyncMock(return_value=False)), \
         patch.object(memory_service, "_insight_gate_blocked", new=AsyncMock(return_value=None)) as gate:
        written = await memory_service.promote_signal_insight(db, USER, CONV, "p1", signals, "English")
    assert written is True
    assert [type(o).__name__ for o in added] == ["Insight"]
    assert added[0].insight_type == "belief"
    # MEM2-B3: a signal card carries evidence. No saved rows were passed here, so
    # the belief cites none, and no message ids were passed, so they are NULL.
    assert added[0].evidence == {
        "kind": "signal", "source_message_ids": None, "memory_entry_ids": [],
    }
    assert gate.await_args.kwargs == {"kind": "signal"}


@pytest.mark.asyncio
async def test_a_blocked_promotion_writes_nothing_and_says_so():
    db, added = _recording_db()
    with patch("services.memory_service.output_is_unsafe", new=AsyncMock(return_value=False)), \
         patch.object(memory_service, "_insight_gate_blocked", new=AsyncMock(return_value="throttle")):
        written = await memory_service.promote_signal_insight(
            db, USER, CONV, "p1", json.loads(EXTRACTION), "English",
        )
    assert written is False and added == []


# ── (3) the task: extract → recurrence → signal ─────────────────────────────

@pytest.mark.asyncio
async def test_the_task_runs_recurrence_before_the_signal_promotion():
    from workers import arq_worker as aw

    order = []
    result = ExtractionResult([])
    result.signals = json.loads(EXTRACTION)
    result.language = "English"
    result.safety_ok = True

    async def extract(**kw):
        order.append(("extract", kw["promote_signal"]))
        return result

    async def recurrence(**kw):
        order.append(("recurrence", None))

    async def promote(db, user_id, conversation_id, persona_id, signals, language,
                      *, saved_rows=None, source_message_ids=None):
        order.append(("signal", signals))
        handed.update(saved_rows=saved_rows, source_message_ids=source_message_ids)
        return True

    handed = {}

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("db.session.AsyncSessionLocal", return_value=session), \
         patch.object(ms.memory_service, "extract_and_store", new=extract), \
         patch.object(ms.memory_service, "detect_recurrence", new=recurrence), \
         patch.object(ms.memory_service, "promote_signal_insight", new=promote):
        await aw.extract_memory_task({}, USER, CONV, "p1", "text", "reply", 1, True, ["m1", "m2"])

    assert [o[0] for o in order] == ["extract", "recurrence", "signal"]
    assert order[0][1] is False, "the task defers the signal write to itself"
    assert order[2][1] == result.signals
    # MEM2-B3: the promotion is handed what its evidence needs.
    assert handed == {"saved_rows": list(result), "source_message_ids": ["m1", "m2"]}


@pytest.mark.asyncio
async def test_the_task_skips_promotion_when_the_exchange_was_not_safety_clean():
    from workers import arq_worker as aw

    result = ExtractionResult([])
    result.signals, result.language, result.safety_ok = [], "English", False
    promote = AsyncMock(return_value=True)
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("db.session.AsyncSessionLocal", return_value=session), \
         patch.object(ms.memory_service, "extract_and_store", new=AsyncMock(return_value=result)), \
         patch.object(ms.memory_service, "detect_recurrence", new=AsyncMock()), \
         patch.object(ms.memory_service, "promote_signal_insight", new=promote):
        await aw.extract_memory_task({}, USER, CONV, "p1", "text", "reply", 1, False, None)
    promote.assert_not_awaited()
