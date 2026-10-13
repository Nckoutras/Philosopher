"""INS-001 / INS-002 / INS-003 against a real Postgres. The unit pins are in
tests/services/test_insight_integrity.py; this file holds the parts only a server
can answer.

1. THE D2-004 PROOF CASE. Two memory tasks for one person, concurrent, each on
   its own connection, both past the early gate before either writes. Before
   INS-003 both wrote a card (production, 2026-10-13 08:56:59 and 08:57:00).
   Now exactly one card exists, and the second task's locked re-gate answered
   "throttle". A second test shows the lock itself blocks: a task asking the
   locked gate waits until the holder's transaction ends.
2. THE 24h FILTER AND THE md5 FILTER, through match_provenance's real SQL: the
   md5-of-the-source-user-message subquery, `= ANY(source_message_ids)` over a
   uuid[], and real timestamps. Γ-5's lesson applies: a query is not verified
   until a driver has executed it, and this one never had.
3. R4. A belief card that was rephrased still retires its own memory row when the
   person answers 'no', through the real memory task and the real verdict handler.

ALL OF THESE ARE FIRST RUNS (TD-45's corollary): an assertion reaching a real
database for the first time is unverified text. Hence the ⛔ WAIT FOR REPORT title.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_insight_integrity_live.py -v
"""
import asyncio
import json
import os
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `live` is a fixture: importing it into this module makes it available here.
from test_memory_epistemic_core import FAKE_EMBEDDING, live  # noqa: E402,F401
from test_memory_recall_and_cascades import _make_conversation, _make_memory  # noqa: E402

pytestmark = pytest.mark.asyncio

CLASSIFIED = json.dumps(
    {"insight_type": "pattern", "content": "The same question about the friendship keeps coming back."}
)


async def _age(s, memory_id, hours):
    await s.execute(
        text("UPDATE memory_entries SET created_at = now() - make_interval(hours => :h) WHERE id = :id"),
        {"h": hours, "id": memory_id},
    )


async def _message(s, uid, conv, content):
    mid = str(uuid.uuid4())
    await s.execute(
        text("INSERT INTO messages (id, conversation_id, user_id, role, content, safety_level)"
             " VALUES (:id, :c, :u, 'user', :t, 'none')"),
        {"id": mid, "c": conv, "u": uid, "t": content},
    )
    return mid


async def _cite(s, memory_id, message_id):
    await s.execute(
        text("UPDATE memory_entries SET source_message_ids = ARRAY[CAST(:m AS uuid)] WHERE id = :id"),
        {"m": message_id, "id": memory_id},
    )


def _entry(mid, content, conv):
    return SimpleNamespace(id=mid, content=content, embedding=FAKE_EMBEDDING, conversation_id=conv)


async def _cards(live, uid):
    async with live.Session() as s:
        return list(await s.execute(
            text("SELECT id::text AS id, insight_type, source_count, evidence, conversation_id::text AS conv"
                 " FROM insights WHERE user_id = :u ORDER BY created_at"),
            {"u": uid},
        ))


async def _echo(live, memory_id):
    async with live.Session() as s:
        return (await s.execute(
            text("SELECT echo_count FROM memory_entries WHERE id = :id"), {"id": memory_id},
        )).scalar_one()


async def _detect(live, uid, conv, entry, *, llm=None):
    from services.memory_service import memory_service

    with patch("services.memory_service.llm_client.complete", llm or AsyncMock(return_value=CLASSIFIED)), \
         patch("services.memory_service.output_is_unsafe", AsyncMock(return_value=False)):
        async with live.Session() as s:
            await memory_service.detect_recurrence(
                db=s, user_id=uid, conversation_id=conv, persona_id=None,
                new_entries=[entry], language="English",
            )


# ── 1. The race ──────────────────────────────────────────────────────────────

async def test_two_concurrent_tasks_write_exactly_one_card_and_the_second_is_throttled(live):
    """D2-004's shape: two conversations, one new row each, both matching an old
    anchor, both tasks inside the classifier call at the same moment."""
    from services.memory_service import memory_service

    uid = await live.make_user()
    async with live.Session() as s:
        old_conv = await _make_conversation(s, uid)
        conv_a = await _make_conversation(s, uid)
        conv_b = await _make_conversation(s, uid)
        anchor = await _make_memory(s, uid, "the anchor", FAKE_EMBEDDING, old_conv)
        await _age(s, anchor, 48)
        row_a = await _make_memory(s, uid, "row a", FAKE_EMBEDDING, conv_a)
        row_b = await _make_memory(s, uid, "row b", FAKE_EMBEDDING, conv_b)
        await s.commit()

    # Neither classifier call returns until BOTH tasks are inside it: so both have
    # passed the early gate, unlocked, before either can write. That is the
    # production interleaving, made deterministic.
    arrived, both_in = [], asyncio.Event()

    async def classify(**kw):
        arrived.append(1)
        if len(arrived) == 2:
            both_in.set()
        await asyncio.wait_for(both_in.wait(), timeout=10)
        return CLASSIFIED

    decisions = []
    real_gate = memory_service._insight_gate_blocked

    async def recording_gate(db, user_id, conversation_id, *, kind):
        d = await real_gate(db, user_id, conversation_id, kind=kind)
        decisions.append((conversation_id, d))
        return d

    with patch.object(memory_service, "_insight_gate_blocked", recording_gate):
        await asyncio.gather(
            _detect(live, uid, conv_a, _entry(row_a, "row a", conv_a), llm=classify),
            _detect(live, uid, conv_b, _entry(row_b, "row b", conv_b), llm=classify),
        )

    cards = await _cards(live, uid)
    assert len(cards) == 1, f"the gate allows ONE recurrence card per 6h; got {len(cards)}"
    assert len(decisions) == 4, decisions
    early, locked = decisions[:2], decisions[2:]
    assert [d for _, d in early] == [None, None], "both tasks passed the early gate"
    assert sorted([d for _, d in locked], key=str) == [None, "throttle"], \
        "one locked re-gate allowed, the other waited and was throttled"
    winner = next(c for c, d in locked if d is None)
    assert cards[0].conv == winner


async def test_the_locked_gate_waits_for_the_holders_transaction_to_end(live):
    from services.memory_service import memory_service

    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await s.commit()

    async with live.Session() as holder, live.Session() as waiter:
        assert await memory_service._insight_gate_locked(holder, uid, conv, kind="signal") is None
        task = asyncio.create_task(
            memory_service._insight_gate_locked(waiter, uid, conv, kind="signal")
        )
        await asyncio.sleep(0.5)
        assert not task.done(), "a second locked gate for the same person must wait"
        await holder.commit()
        assert await asyncio.wait_for(task, timeout=5) is None
        await waiter.commit()


async def test_another_persons_lock_does_not_block(live):
    from services.memory_service import memory_service

    uid, other = await live.make_user(), await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        conv_o = await _make_conversation(s, other)
        await s.commit()

    async with live.Session() as holder, live.Session() as them:
        await memory_service._insight_gate_locked(holder, uid, conv, kind="signal")
        assert await asyncio.wait_for(
            memory_service._insight_gate_locked(them, other, conv_o, kind="signal"), timeout=2,
        ) is None
        await them.commit()
        await holder.commit()


# ── 2. The filters, through the real provenance query ───────────────────────

async def _pair(live, *, anchor_age_hours, same_message=False, cite=True):
    """An anchor in one conversation and a new row in another, matching. Returns
    (uid, new_conv, anchor_id, new_row_id)."""
    uid = await live.make_user()
    async with live.Session() as s:
        old_conv = await _make_conversation(s, uid)
        new_conv = await _make_conversation(s, uid)
        anchor = await _make_memory(s, uid, "the anchor", FAKE_EMBEDDING, old_conv)
        new = await _make_memory(s, uid, "the new row", FAKE_EMBEDDING, new_conv)
        if cite:
            text_old = "My closest friend keeps cancelling on me."
            text_new = text_old if same_message else "She cancelled again tonight."
            await _cite(s, anchor, await _message(s, uid, old_conv, text_old))
            await _cite(s, new, await _message(s, uid, new_conv, text_new))
        await _age(s, anchor, anchor_age_hours)
        await s.commit()
    return uid, new_conv, anchor, new


async def test_a_prior_row_23h_old_earns_no_card_but_still_echoes(live):
    uid, conv, anchor, new = await _pair(live, anchor_age_hours=23)
    await _detect(live, uid, conv, _entry(new, "the new row", conv),
                  llm=AsyncMock(side_effect=AssertionError("no card, so no classifier call")))
    assert await _cards(live, uid) == []
    assert await _echo(live, anchor) == 1, "B4 counts the raw hit"


async def test_a_prior_row_25h_old_earns_a_card_that_records_the_window(live):
    uid, conv, anchor, new = await _pair(live, anchor_age_hours=25)
    await _detect(live, uid, conv, _entry(new, "the new row", conv))
    (card,) = await _cards(live, uid)
    assert card.insight_type == "pattern"
    assert card.source_count == 2
    assert card.evidence["detector"]["window"] == "24h"
    assert [p["memory_entry_id"] for p in card.evidence["prior_matches"]] == [anchor]


async def test_the_same_message_in_two_conversations_earns_no_card_however_old(live):
    """D2-003 exactly, with the anchor aged far past the window so only (a) can
    stop it. The md5 is computed by Postgres from the stored messages."""
    uid, conv, anchor, new = await _pair(live, anchor_age_hours=72, same_message=True)
    await _detect(live, uid, conv, _entry(new, "the new row", conv),
                  llm=AsyncMock(side_effect=AssertionError("no card, so no classifier call")))
    assert await _cards(live, uid) == []
    assert await _echo(live, anchor) == 1


async def test_a_different_message_of_the_same_age_does_earn_the_card(live):
    """The control for the test above: same shape, different text, one card. So
    the no-card result above is the md5 filter's doing and nothing else's."""
    uid, conv, anchor, new = await _pair(live, anchor_age_hours=72, same_message=False)
    await _detect(live, uid, conv, _entry(new, "the new row", conv))
    assert len(await _cards(live, uid)) == 1


async def test_rows_with_no_source_message_are_exempt_from_the_md5_filter_only(live):
    uid, conv, _, new = await _pair(live, anchor_age_hours=72, cite=False)
    await _detect(live, uid, conv, _entry(new, "the new row", conv))
    assert len(await _cards(live, uid)) == 1, "NULL ids: (a) cannot apply, (b) passes"

    uid2, conv2, _, new2 = await _pair(live, anchor_age_hours=2, cite=False)
    await _detect(live, uid2, conv2, _entry(new2, "the new row", conv2),
                  llm=AsyncMock(side_effect=AssertionError("no card")))
    assert await _cards(live, uid2) == [], "NULL ids: (b) still applies"


# ── 3. R4: a rephrased belief still retires its row ─────────────────────────

BELIEF = "I'm hurt and angry, yet I don't want to make her life harder."
USER_TEXT = ("My closest friend keeps cancelling. " + BELIEF
             + " I'm torn about whether to say anything.")
REPHRASED = "Being angry with her feels like it would only add to what she is carrying."


async def test_a_rephrased_belief_card_still_retires_its_own_row_on_no(live):
    from services.memory_service import MEMORY_EXTRACTION_PROMPT, REPHRASE_SIGNAL_PROMPT
    from workers.arq_worker import extract_memory_task
    from routers.memory import set_insight_ring_true
    from schemas import InsightRingTrueRequest

    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await s.commit()

    async def complete(*, system, user, **kw):
        if system.startswith(MEMORY_EXTRACTION_PROMPT):
            return json.dumps([{"type": "belief", "content": BELIEF, "confidence": 0.9}])
        if system.startswith(REPHRASE_SIGNAL_PROMPT):
            return REPHRASED
        raise AssertionError("unexpected model call")

    with patch("services.memory_service.llm_client.complete", new=complete), \
         patch("services.memory_service.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)), \
         patch("services.memory_service.output_is_unsafe", AsyncMock(return_value=False)):
        await extract_memory_task(
            {}, uid, conv, None, USER_TEXT, "That sounds heavy.", 1, True,
            [str(uuid.uuid4()), str(uuid.uuid4())],
        )

    async with live.Session() as s:
        row = (await s.execute(
            text("SELECT id::text AS id, content, is_active FROM memory_entries WHERE user_id = :u"),
            {"u": uid},
        )).one()
    (card,) = await _cards(live, uid)
    async with live.Session() as s:
        content = (await s.execute(
            text("SELECT content FROM insights WHERE id = :i"), {"i": card.id},
        )).scalar_one()
    assert row.content == BELIEF, "the memory row keeps the extracted text"
    assert content == REPHRASED, "the card shows the rephrase"
    assert card.evidence["memory_entry_ids"] == [row.id], "R4: cited by the ORIGINAL text"

    no_queue = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(arq_queue=None)))
    with patch("routers.memory.analytics_service"):
        async with live.Session() as s:
            await set_insight_ring_true(
                card.id, InsightRingTrueRequest(ring_true="no"), request=no_queue,
                db=s, user=SimpleNamespace(id=uid),
            )
    async with live.Session() as s:
        after = (await s.execute(
            text("SELECT is_active, inactive_reason FROM memory_entries WHERE id = :i"), {"i": row.id},
        )).one()
    assert (after.is_active, after.inactive_reason) == (False, "user_rejected")
