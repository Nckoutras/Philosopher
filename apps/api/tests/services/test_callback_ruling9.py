"""MEM2-C-2, Ruling 9 (anti-laundering) and D7 — the write side of a callback.

Ruling 9: "a callback cannot upgrade the epistemic status of the memory it
references. User replies elicited by a callback do not count as independent
recurrence, confirmation, echo or dedup-survivor evidence."

THE TWO PAIRS OF A CALLBACK, and what each gets:

  offer pair  [user message, reply that CARRIED the callback]. The user message
              predates the callback and stays evidence; the reply paraphrases the
              memory, so extraction sees the user turn ALONE (D7). Rows unmarked.
  reply pair  [the user's answer to the callback, next reply]. Every row is
              marked elicited_by_callback: no echo stamp, no recurrence card, no
              dedup either way, no signal promotion, never itself a callback.

Named shortcut (approved): the "unless independently stated" exception is not
implemented — every row of a reply pair is marked. First C-3 fix.

The SQL that decides which pair is which runs against Postgres in
tests/db_live/test_memory_callbacks_live.py.
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import callback_service as cs
from services import dedup_judge as dj
from services import memory_service as ms
from services.memory_service import DEDUP_CANDIDATE_SQL, ExtractionResult, find_recurrences, memory_service

USER = "11111111-1111-1111-1111-111111111111"
CONV = "22222222-2222-2222-2222-222222222222"
IDS = ["33333333-3333-3333-3333-333333333333", "44444444-4444-4444-4444-444444444444"]


# ── The worker: which pair, and what it is handed ────────────────────────────

async def _run_task(role, *, safety_ok=True):
    from workers import arq_worker as aw

    result = ExtractionResult([])
    result.signals, result.language, result.safety_ok = [], "English", safety_ok
    extract = AsyncMock(return_value=result)
    promote = AsyncMock(return_value=False)
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("db.session.AsyncSessionLocal", return_value=session), \
         patch.object(cs, "callback_turn_role", AsyncMock(return_value=role)) as turn, \
         patch.object(ms.memory_service, "extract_and_store", new=extract), \
         patch.object(ms.memory_service, "dedup_new_entries", new=AsyncMock()), \
         patch.object(ms.memory_service, "detect_recurrence", new=AsyncMock()), \
         patch.object(ms.memory_service, "promote_signal_insight", new=promote):
        await aw.extract_memory_task({}, USER, CONV, "p1", "text", "reply", 1, safety_ok, IDS)
    return extract.await_args.kwargs, promote, turn


async def test_an_ordinary_pair_is_extracted_as_before():
    kw, promote, turn = await _run_task((False, False))
    assert (kw["elicited_by_callback"], kw["omit_assistant"]) == (False, False)
    assert turn.await_args.args[1] == IDS
    promote.assert_awaited_once()


async def test_the_offer_pair_hides_the_reply_and_keeps_its_rows_as_evidence():
    """D7: the user message predates the callback; only the reply is contaminated."""
    kw, promote, _ = await _run_task((True, False))
    assert (kw["elicited_by_callback"], kw["omit_assistant"]) == (False, True)
    promote.assert_awaited_once()


async def test_the_reply_pair_is_marked_and_promotes_no_signal():
    kw, promote, _ = await _run_task((False, True))
    assert (kw["elicited_by_callback"], kw["omit_assistant"]) == (True, False)
    promote.assert_not_awaited()


# ── A failed extraction runs the rest of the task (Sentry PHILOSOPHER-API-F) ──
#
# The harness above hands the task a ready-made ExtractionResult, so it could not
# see that the REAL extract_and_store returned a bare list when the model's output
# did not parse — and the task then crashed on `entries.safety_ok`. Here the real
# extract_and_store runs, fed malformed JSON.

@pytest.mark.parametrize("role", [(False, False), (False, True)], ids=["ordinary", "reply_turn"])
async def test_a_failed_extraction_runs_the_rest_of_the_task(role, caplog):
    from workers import arq_worker as aw

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    recur, promote = AsyncMock(), AsyncMock(return_value=False)
    with (
        patch("db.session.AsyncSessionLocal", return_value=session),
        patch.object(cs, "callback_turn_role", AsyncMock(return_value=role)),
        patch("services.memory_service.llm_client.complete",
              new=AsyncMock(return_value="Sure! Here are the memories: [")),
        patch.object(ms.memory_service, "dedup_new_entries", new=AsyncMock()),
        patch.object(ms.memory_service, "detect_recurrence", new=recur),
        patch.object(ms.memory_service, "promote_signal_insight", new=promote),
        caplog.at_level("INFO"),
    ):
        await aw.extract_memory_task({}, USER, CONV, "p1", "text", "reply", 1, True, IDS)

    assert "Memory extraction failed" in caplog.text
    assert "Memory task failed" not in caplog.text      # the task's catch-all never fired
    assert recur.await_args.kwargs["new_entries"] == []
    if role[1]:
        promote.assert_not_awaited()                     # Ruling 9: a reply turn promotes nothing
    else:
        promote.assert_awaited_once()
        assert promote.await_args.args[4] == []          # nothing extracted, nothing to promote


async def test_every_extract_and_store_return_is_an_extraction_result():
    with patch("services.memory_service.llm_client.complete", new=AsyncMock(return_value="{not json")):
        out = await memory_service.extract_and_store(
            db=_db(), user_id=USER, conversation_id=CONV, persona_id="p1",
            user_text="Δεν ξέρω.", assistant_text="reply", safety_ok=True, promote_signal=False,
        )
    assert isinstance(out, ExtractionResult) and list(out) == []
    assert (out.signals, out.language, out.safety_ok) == ([], "Greek", True)


# ── extract_and_store: D7's input, and the mark on every row ─────────────────

def _db():
    db = MagicMock()
    db.added = []
    db.add = lambda row: db.added.append(row)
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


async def _extract(**kw):
    captured = {}

    async def fake_complete(system, user, model=None, max_tokens=512):
        captured["user"] = user
        return json.dumps([{"type": "struggle", "content": "User doubts the job.",
                            "confidence": 0.9},
                           {"type": "value", "content": "User values candour.",
                            "confidence": 0.9}])

    db = _db()
    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(side_effect=[[1.0, 0.0], [0.0, 1.0]])):
        await memory_service.extract_and_store(
            db=db, user_id=USER, conversation_id=CONV, persona_id="p1",
            user_text="I doubt my job.", assistant_text="You said a few weeks ago that…",
            source_message_ids=IDS, promote_signal=False, **kw,
        )
    return captured["user"], db.added


async def test_by_default_the_model_sees_the_whole_pair_and_rows_are_unmarked():
    user, rows = await _extract()
    assert user == "USER: I doubt my job.\n\nASSISTANT: You said a few weeks ago that…"
    assert [r.elicited_by_callback for r in rows] == [False, False]


async def test_omit_assistant_shows_the_user_turn_alone():
    user, rows = await _extract(omit_assistant=True)
    assert user == "USER: I doubt my job."
    assert "ASSISTANT" not in user and "You said" not in user
    assert [r.elicited_by_callback for r in rows] == [False, False]


async def test_an_elicited_call_marks_every_row():
    _, rows = await _extract(elicited_by_callback=True)
    assert len(rows) == 2 and all(r.elicited_by_callback is True for r in rows)


# ── B5: an elicited row is neither subject nor candidate ─────────────────────

def test_the_dedup_candidate_sql_excludes_elicited_rows():
    assert "AND elicited_by_callback = FALSE" in " ".join(DEDUP_CANDIDATE_SQL.split())


async def test_an_elicited_new_row_is_never_a_dedup_subject():
    db = MagicMock(begin_nested=AsyncMock(), execute=AsyncMock(), commit=AsyncMock())
    entry = SimpleNamespace(id="55555555-5555-5555-5555-555555555555", embedding=[0.1] * 4, content="x",
                            provenance="system_inferred", source_surface="chat",
                            conversation_id=CONV, elicited_by_callback=True)
    with patch.object(dj.config, "MEMORY_DEDUP_ENABLED", True), \
         patch.object(ms.dedup_judge, "judge_pair", AsyncMock()) as judge:
        n = await memory_service.dedup_new_entries(db, USER, [entry])
    assert n == 0
    db.begin_nested.assert_not_awaited()
    db.execute.assert_not_awaited()
    judge.assert_not_awaited()


# ── B4: an elicited row is neither query nor anchor ──────────────────────────

async def test_an_elicited_new_row_searches_nothing_and_stamps_nothing():
    plain = SimpleNamespace(id="e1", embedding=[0.1], elicited_by_callback=False)
    elicited = SimpleNamespace(id="e2", embedding=[0.1], elicited_by_callback=True)
    found = AsyncMock(return_value=None)
    echoes = AsyncMock()
    with patch.object(ms, "find_recurrences", found), \
         patch.object(memory_service, "_record_echoes", echoes), \
         patch.object(memory_service, "_insight_gate_blocked", AsyncMock(return_value="throttle")):
        await memory_service.detect_recurrence(
            db=MagicMock(), user_id=USER, conversation_id=CONV, persona_id="p1",
            new_entries=[plain, elicited], language="English",
        )
    assert [c.args[2].id for c in found.await_args_list] == ["e1"]
    assert echoes.await_args.args[2] == []


@pytest.mark.parametrize("exclude", [CONV, None])
async def test_no_elicited_row_is_ever_an_anchor(exclude):
    """Both exclusion branches — a chat source and a NULL-conversation source."""
    db = AsyncMock()
    rows = MagicMock()
    rows.fetchall.return_value = []
    db.execute = AsyncMock(return_value=rows)
    entry = SimpleNamespace(id="e1", content="c", embedding=[0.1] * 4, conversation_id=exclude)
    await find_recurrences(db, USER, entry, exclude_conversation=exclude)
    sql = str(db.execute.await_args.args[0])
    assert "AND elicited_by_callback = FALSE" in sql
