"""MEM2-B3 + B4 against a real Postgres (migration 073).

What needs the server, and is therefore here rather than behind a mock:

1. 073'S SCHEMA. Two nullable columns of the right types, and a down-and-up that
   actually removes and restores them.
2. B3 END TO END. A belief extracted by the real memory task becomes a card whose
   evidence cites ITS OWN ROW ONLY, and a 'no' through the real ring-true handler
   retires that row and none of the rows written beside it; a 'yes' returns it
   (B2, unchanged, now reached through the new shape). A dilemma card cites no
   row, and a 'no' on it retires nothing.
3. B4'S COUNT. The UPDATE is real SQL against real rows: +1 per anchor per call
   however many new rows matched it, NULL until the first echo, a same-conversation
   row never counted, a dissimilar row never counted, and the count taken while
   the insight gate is CLOSED, which is the ruling's whole point.
4. THE RECURRENCE CARD'S kind, written by the real detector.

All of these are the FIRST RUN of new live checks (TD-45's corollary): an
assertion reaching a real database for the first time is unverified text.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_signal_evidence_echo_live.py -v
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `live` is a fixture: importing it into this module makes it available here.
from test_memory_epistemic_core import FAKE_EMBEDDING, _alembic, live  # noqa: E402,F401
from test_memory_recall_and_cascades import _make_conversation, _make_memory  # noqa: E402

FAR = [1.0] + [0.0] * 1535  # cosine with FAKE_EMBEDDING ~0.026: never a match
NO_QUEUE = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(arq_queue=None)))


# ── 1. Schema ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_073_adds_two_nullable_columns(db):
    cols = {
        r.column_name: (r.data_type, r.is_nullable)
        for r in await db.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = 'memory_entries'"
            " AND column_name IN ('echo_count', 'last_echo_at')"
        ))
    }
    assert cols == {
        "echo_count": ("integer", "YES"),
        "last_echo_at": ("timestamp with time zone", "YES"),
    }


def _073_columns(url: str) -> set[str]:
    async def fetch():
        conn = await asyncpg.connect(url.replace("+asyncpg", ""))
        try:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_schema = 'public' AND table_name = 'memory_entries'"
                " AND column_name IN ('echo_count', 'last_echo_at')"
            )
            return {r["column_name"] for r in rows}
        finally:
            await conn.close()

    return asyncio.run(fetch())


def test_073_downgrades_cleanly_and_upgrades_again(schema):
    """Always returned to head, so a failure cannot leave the session on 072."""
    try:
        _alembic(schema, "downgrade", "072_verdict_history_shift")
        assert _073_columns(schema) == set(), "073 downgrade left a column behind"
    finally:
        _alembic(schema, "upgrade", "head")
    assert _073_columns(schema) == {"echo_count", "last_echo_at"}


# ── 2. B3 end to end ─────────────────────────────────────────────────────────

BELIEF = "If I don't handle everything myself, it won't be done right."
STRUGGLE = "User is weighing a hard decision about work."
DILEMMA = "I'm weighing whether to leave a secure job for one that feels meaningful."


async def _run_memory_task(live, uid, conv, extracted, msg_ids):
    """The real extract_memory_task: extraction, recurrence, then promotion. The
    LLM and the embedder are the only things stubbed, plus the output gate (its
    own live tests exist; here it must simply pass the card)."""
    from workers.arq_worker import extract_memory_task

    with patch("services.memory_service.llm_client.complete",
               AsyncMock(return_value=json.dumps(extracted))), \
         patch("services.memory_service.embedding_client.embed",
               AsyncMock(return_value=FAKE_EMBEDDING)), \
         patch("services.memory_service.output_is_unsafe", AsyncMock(return_value=False)):
        await extract_memory_task(
            {}, uid, conv, None, "I keep thinking I have to do it all myself.",
            "That is a heavy thing to carry.", 1, True, msg_ids,
        )


async def _verdict(live, uid, iid, verdict):
    from routers.memory import set_insight_ring_true
    from schemas import InsightRingTrueRequest

    with patch("routers.memory.analytics_service"):
        async with live.Session() as s:
            await set_insight_ring_true(
                iid, InsightRingTrueRequest(ring_true=verdict), request=NO_QUEUE,
                db=s, user=SimpleNamespace(id=uid),
            )


async def _memory(live, uid):
    async with live.Session() as s:
        return {
            r.content: r for r in await s.execute(
                text(
                    "SELECT id::text AS id, entry_type, content, is_active, inactive_reason,"
                    " echo_count, last_echo_at, conversation_id::text AS conversation_id"
                    " FROM memory_entries WHERE user_id = :u"
                ),
                {"u": uid},
            )
        }


async def _insights(live, uid):
    async with live.Session() as s:
        return list(await s.execute(
            text("SELECT id::text AS id, insight_type, evidence FROM insights WHERE user_id = :u"),
            {"u": uid},
        ))


@pytest.mark.asyncio
async def test_a_belief_card_cites_its_own_row_and_a_no_retires_only_that_row(live):
    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await s.commit()
    msg_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    await _run_memory_task(live, uid, conv, [
        {"type": "struggle", "content": STRUGGLE, "confidence": 0.85},
        {"type": "belief", "content": BELIEF, "confidence": 0.9, "theme": "work"},
    ], msg_ids)

    rows = await _memory(live, uid)
    assert set(rows) == {STRUGGLE, BELIEF}
    (card,) = await _insights(live, uid)
    assert card.insight_type == "belief"
    assert card.evidence == {
        "kind": "signal",
        "source_message_ids": msg_ids,
        "memory_entry_ids": [rows[BELIEF].id],
    }

    await _verdict(live, uid, card.id, "no")
    rows = await _memory(live, uid)
    assert (rows[BELIEF].is_active, rows[BELIEF].inactive_reason) == (False, "user_rejected")
    assert (rows[STRUGGLE].is_active, rows[STRUGGLE].inactive_reason) == (True, None), \
        "a 'no' on a belief must not retire the row written beside it (Q1)"

    await _verdict(live, uid, card.id, "yes")
    rows = await _memory(live, uid)
    assert (rows[BELIEF].is_active, rows[BELIEF].inactive_reason) == (True, None), \
        "B2 reactivation reaches the belief through the signal shape"


@pytest.mark.asyncio
async def test_a_dilemma_card_cites_no_row_and_a_no_retires_nothing(live):
    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await s.commit()
    msg_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    await _run_memory_task(live, uid, conv, [
        {"type": "struggle", "content": STRUGGLE, "confidence": 0.85},
        {"type": "dilemma", "content": DILEMMA, "confidence": 0.9, "theme": "work"},
    ], msg_ids)

    (card,) = await _insights(live, uid)
    assert card.insight_type == "dilemma"
    assert card.evidence == {"kind": "signal", "source_message_ids": msg_ids}

    await _verdict(live, uid, card.id, "no")
    rows = await _memory(live, uid)
    assert set(rows) == {STRUGGLE}, "a dilemma writes no memory row"
    assert (rows[STRUGGLE].is_active, rows[STRUGGLE].inactive_reason) == (True, None)


# ── 3. B4: the echo count ────────────────────────────────────────────────────

async def _recent_pattern_card(s, uid, conv):
    """Closes the recurrence window: the gate will answer "throttle"."""
    await s.execute(
        text(
            "INSERT INTO insights (id, user_id, conversation_id, content, insight_type, created_at)"
            " VALUES (:i, :u, :c, 'an earlier card', 'pattern', :t)"
        ),
        {"i": str(uuid.uuid4()), "u": uid, "c": conv,
         "t": datetime.now(timezone.utc) - timedelta(minutes=5)},
    )


def _entry(mid, content, conversation_id):
    return SimpleNamespace(id=mid, content=content, embedding=FAKE_EMBEDDING,
                           conversation_id=conversation_id)


async def _detect(live, uid, conv, entries, *, llm=None):
    from services.memory_service import memory_service

    llm = llm or AsyncMock(side_effect=AssertionError("the gate was closed"))
    with patch("services.memory_service.llm_client.complete", llm), \
         patch("services.memory_service.output_is_unsafe", AsyncMock(return_value=False)):
        async with live.Session() as s:
            await memory_service.detect_recurrence(
                db=s, user_id=uid, conversation_id=conv, persona_id=None,
                new_entries=entries, language="English",
            )


@pytest.mark.asyncio
async def test_echoes_are_counted_while_the_gate_is_closed(live):
    uid = await live.make_user()
    async with live.Session() as s:
        old_conv = await _make_conversation(s, uid)
        new_conv = await _make_conversation(s, uid)
        await _make_memory(s, uid, "the anchor", FAKE_EMBEDDING, old_conv)
        await _make_memory(s, uid, "unrelated", FAR, old_conv)
        await _make_memory(s, uid, "same conversation", FAKE_EMBEDDING, new_conv)
        new_a = await _make_memory(s, uid, "new a", FAKE_EMBEDDING, new_conv)
        new_b = await _make_memory(s, uid, "new b", FAKE_EMBEDDING, new_conv)
        await _recent_pattern_card(s, uid, old_conv)
        await s.commit()

    # Two new rows, both matching the anchor: one call, so +1, not +2.
    await _detect(live, uid, new_conv, [
        _entry(new_a, "new a", new_conv), _entry(new_b, "new b", new_conv),
    ])

    rows = await _memory(live, uid)
    assert rows["the anchor"].echo_count == 1
    assert rows["the anchor"].last_echo_at is not None
    assert rows["unrelated"].echo_count is None, "below the threshold: never counted"
    assert rows["same conversation"].echo_count is None, "same conversation: never counted"
    assert rows["new a"].echo_count is None and rows["new b"].echo_count is None
    assert len(await _insights(live, uid)) == 1, "the gate was closed: no new card"

    first_echo = rows["the anchor"].last_echo_at
    await _detect(live, uid, new_conv, [_entry(new_a, "new a", new_conv)])
    rows = await _memory(live, uid)
    assert rows["the anchor"].echo_count == 2, "a second call counts again"
    assert rows["the anchor"].last_echo_at >= first_echo


@pytest.mark.asyncio
async def test_a_conversation_less_row_echoes_every_row_but_itself(live):
    """The counterview path: no conversation, so the search excludes only the
    row itself, and an anchor in any conversation, or none, counts (ruling)."""
    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await _make_memory(s, uid, "in a conversation", FAKE_EMBEDDING, conv)
        await _make_memory(s, uid, "no conversation", FAKE_EMBEDDING, None)
        belief = await _make_memory(s, uid, "typed belief", FAKE_EMBEDDING, None,
                                    entry_type="counterview_belief")
        await _recent_pattern_card(s, uid, None)
        await s.commit()

    await _detect(live, uid, None, [_entry(belief, "typed belief", None)])

    rows = await _memory(live, uid)
    assert rows["in a conversation"].echo_count == 1
    assert rows["no conversation"].echo_count == 1
    assert rows["typed belief"].echo_count is None, "a row never echoes itself"


@pytest.mark.asyncio
async def test_another_persons_rows_are_never_counted(live):
    uid = await live.make_user()
    other = await live.make_user()
    async with live.Session() as s:
        their_conv = await _make_conversation(s, other)
        new_conv = await _make_conversation(s, uid)
        await _make_memory(s, other, "theirs", FAKE_EMBEDDING, their_conv)
        new_a = await _make_memory(s, uid, "new a", FAKE_EMBEDDING, new_conv)
        await s.commit()

    await _detect(live, uid, new_conv, [_entry(new_a, "new a", new_conv)],
                  llm=AsyncMock(return_value="unused"))
    assert (await _memory(live, other))["theirs"].echo_count is None


# ── 4. The recurrence card's kind ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_recurrence_card_records_kind_recurrence_and_still_counts(live):
    from services.memory_service import cited_memory_ids

    uid = await live.make_user()
    async with live.Session() as s:
        old_conv = await _make_conversation(s, uid)
        new_conv = await _make_conversation(s, uid)
        anchor = await _make_memory(s, uid, "the anchor", FAKE_EMBEDDING, old_conv)
        new_a = await _make_memory(s, uid, "new a", FAKE_EMBEDDING, new_conv)
        await s.commit()

    classify = AsyncMock(return_value=json.dumps(
        {"insight_type": "pattern", "content": "The same question has come back again."}
    ))
    await _detect(live, uid, new_conv, [_entry(new_a, "new a", new_conv)], llm=classify)

    (card,) = await _insights(live, uid)
    assert card.insight_type == "pattern"
    assert card.evidence["kind"] == "recurrence"
    assert card.evidence["recurring_entry"]["memory_entry_id"] == new_a
    assert cited_memory_ids(card.evidence) == [new_a, anchor]
    assert (await _memory(live, uid))["the anchor"].echo_count == 1
