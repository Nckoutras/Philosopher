"""The insight-path conversation safety gate, from both sides (F-15).

WHY THIS FILE EXISTS. generate_counterview runs a SECOND safety check on the
insight path: the distilled insight text may read clean while the conversation it
came from carried a high/critical user message, so the gate loads that
conversation's user messages and suppresses on them
(services/counterview_service.py, "Insight path:" block).

That gate was guarded on `insight.conversation_id is not None`, which meant an
insight with no conversation SKIPPED it. Today that cannot happen — the FK is
ON DELETE CASCADE, so deleting a thread destroys its insights and this endpoint
404s. Migration 057 changes the FK to SET NULL
(MEMORY_V2_DESIGN_2026-09-03 §0b/§4c), and from that point an orphaned insight is
reachable: GET /insights filters only user_id and is_dismissed, and
POST /insights/{id}/counterview resolves by id + user_id alone.

So the guard now FAILS CLOSED, and these tests pin both halves:

  1. conversation_id IS NULL      -> suppressed, before any LLM call and without
                                     ever querying for messages.
  2. conversation_id is NOT NULL  -> the message query still runs and still
                                     suppresses on a flagged message. This is the
                                     inverse regression: a guard that suppresses
                                     everything would also pass test 1.
  3. conversation_id is NOT NULL, messages clean -> generation proceeds, so the
                                     new branch has not over-suppressed the
                                     ordinary path.

This PR ships AHEAD of 057 deliberately: the guard must exist before the
migration makes orphans possible, never after.

The DB session is mocked in the house style of test_counterview_rebuttal.py
(sequenced execute()), so each test documents the exact execute() order it
expects — and the COUNT is the assertion that proves the message query did not
happen. The LLM and safety_service are mocked; nothing here makes a live call.

Run: cd apps/api && pytest tests/services/test_counterview_orphan_insight.py -v
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.counterview_service as cs
from services.counterview_service import generate_counterview

USER_ID = "11111111-1111-1111-1111-111111111111"
INSIGHT_ID = "22222222-2222-2222-2222-222222222222"
CONV_ID = "33333333-3333-3333-3333-333333333333"


# ── helpers (house style: see test_counterview_rebuttal.py) ──────────────────

_SENTINEL = object()


def _result(*, scalar=_SENTINEL, all_=_SENTINEL):
    """A canned execute() result configured only for the accessor a step uses."""
    r = MagicMock()
    if scalar is not _SENTINEL:
        r.scalar_one_or_none.return_value = scalar
    if all_ is not _SENTINEL:
        r.scalars.return_value.all.return_value = all_
    return r


def _db(results):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _insight(conversation_id):
    """A real namespace, not a MagicMock (C-06). The service reads .content and
    .conversation_id; an unset attribute must raise here rather than silently
    resolve to a Mock that is neither None nor a str."""
    return SimpleNamespace(
        id=INSIGHT_ID,
        user_id=USER_ID,
        content="User keeps postponing a decision they have already made.",
        conversation_id=conversation_id,
    )


def _message(safety_level):
    return SimpleNamespace(role="user", safety_level=safety_level)


def _safety(suppress):
    """BOTH fields the caller reads, explicitly (C-06). should_log is not
    incidental: a MagicMock without it is truthy, which would fire
    log_safety_event and add DB calls this file's execute() counts depend on."""
    return MagicMock(should_suppress_persona=suppress, should_log=False)


@pytest.fixture
def patch_safety_llm(monkeypatch):
    """Default-safe anchor-text gate + an LLM returning one valid generated pair.
    The anchor gate passing is what makes these tests about the CONVERSATION gate
    rather than the text gate."""
    monkeypatch.setattr(cs.safety_service, "check_input", AsyncMock(return_value=_safety(False)))
    monkeypatch.setattr(cs.safety_service, "check_output", AsyncMock(return_value=_safety(False)))
    monkeypatch.setattr(
        cs.llm_client,
        "complete",
        AsyncMock(return_value=(
            '{"status":"generated","verdicts":['
            '{"persona":"miyamoto_musashi","verdict":"Waiting is fear in a calmer coat."},'
            '{"persona":"niccolo_machiavelli","verdict":"You already chose; you are buying comfort."}'
            '],"still_stands":null,"title":"The cost of delay"}'
        )),
    )
    return monkeypatch


# ── 1. The orphan: fail closed ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_an_orphaned_insight_is_suppressed_before_any_llm_call(patch_safety_llm):
    """F-15. conversation_id IS NULL -> status='suppressed', no LLM call.

    execute() order: (1) load the insight, (2) the insight-path dedup lookup.
    Exactly two. A THIRD would be the message query, and the whole point is that
    it cannot run — there is no conversation to query."""
    db = _db([
        _result(scalar=_insight(conversation_id=None)),
        _result(scalar=None),  # no existing counterview for this insight
    ])

    cv = await generate_counterview(
        db, USER_ID, insight_id=INSIGHT_ID, source="insight"
    )

    assert cv.status == "suppressed"
    assert cs.llm_client.complete.await_count == 0
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_the_orphan_suppression_is_persisted_against_the_insight(patch_safety_llm):
    """The suppression is a written row, not an in-memory return: the dedup at the
    top of the insight path reads it back on the next tap, so the endpoint stays
    idempotent instead of re-deciding on every request."""
    db = _db([
        _result(scalar=_insight(conversation_id=None)),
        _result(scalar=None),
    ])

    cv = await generate_counterview(
        db, USER_ID, insight_id=INSIGHT_ID, source="insight"
    )

    assert db.add.call_count == 1
    assert db.commit.await_count == 1
    added = db.add.call_args.args[0]
    assert added is cv
    assert added.insight_id == INSIGHT_ID
    assert added.status == "suppressed"
    assert added.source == "insight"


# ── 2. The boundary: a surviving thread is still checked ─────────────────────

@pytest.mark.asyncio
async def test_a_flagged_conversation_still_suppresses_when_the_thread_survives(patch_safety_llm):
    """THE INVERSE REGRESSION. A guard that suppressed every insight would pass the
    orphan test above and quietly delete this behaviour. So: conversation_id set,
    one critical user message -> the message query DOES run (three execute calls)
    and the counterview is suppressed."""
    db = _db([
        _result(scalar=_insight(conversation_id=CONV_ID)),
        _result(scalar=None),
        _result(all_=[_message("none"), _message("critical")]),
    ])

    cv = await generate_counterview(
        db, USER_ID, insight_id=INSIGHT_ID, source="insight"
    )

    assert cv.status == "suppressed"
    assert cs.llm_client.complete.await_count == 0
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_a_clean_surviving_conversation_still_generates(patch_safety_llm):
    """The new branch must not over-suppress. Conversation present, every message
    clean -> the gate falls through and generation runs exactly as before."""
    db = _db([
        _result(scalar=_insight(conversation_id=CONV_ID)),
        _result(scalar=None),
        _result(all_=[_message("none"), _message("low")]),
    ])

    cv = await generate_counterview(
        db, USER_ID, insight_id=INSIGHT_ID, source="insight"
    )

    assert cv.status == "generated"
    assert cs.llm_client.complete.await_count == 1
    assert db.execute.await_count == 3
