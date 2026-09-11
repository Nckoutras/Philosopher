"""Signal insights whose text lands in the user's own input box.

WHY THIS IS STRICTER THAN THE REST OF EXTRACTION. The memory-language work that
preceded this made every extraction write log-only: a row in the wrong language
is still a true fact about the person, and dropping it would lose the fact as
well as the language. That reasoning does not survive contact with one case.

A `dilemma` signal becomes an Insight whose content is written to
sessionStorage 'council_prefill' and then straight into the Council matter
TEXTAREA — the box the person types their own words into. A sentence they never
wrote, sitting in their own input field, ready to submit without them noticing,
is exactly what made the council display-brief defect a P0. So dilemma is
dropped on a language mismatch; everything else keeps logging.

EDITABLE INPUT IS THE LINE, AND ONLY DILEMMA CROSSES IT. `belief` becomes the
Counterview anchor, which is generated from server-side and rendered read-only
in a <p> labelled "Your insight" — the page's own `belief` state is written only
when the user types. `aspiration` routes to the Future Self ritual carrying no
content at all. Both stay log-only, and a test below pins that so a later "make
it consistent" pass has to argue with the reason rather than the symmetry.

THE CHECK LIVES INSIDE THE SELECTION, not after it, and that is the whole design.
Filtering a chosen signal afterwards would collapse the promotion whenever the
top-priority candidate failed: a mismatching dilemma would take the slot and be
discarded, and a perfectly good Greek belief behind it would never be reached.
test_the_priority_order_still_advances_past_a_dropped_dilemma is that case.

THE COST IS NOT RECOVERABLE. A dropped dilemma is not deferred or retried — the
exchange has passed and the Council door is lost until the same dilemma comes up
again. Accepted trade, recorded here so it is not rediscovered as a bug.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import Insight, MemoryEntry
from services.memory_service import VERBATIM_INPUT_SIGNAL_TYPES, memory_service

GREEK_TURN = (
    "Δεν ξέρω αν πρέπει να φύγω από τη δουλειά μου ή να μείνω και να "
    "προσπαθήσω κι άλλο."
)
ENGLISH_TURN = (
    "I do not know whether I should leave my job or stay and try a while longer."
)

EN_DILEMMA = "I'm weighing whether to leave a secure job for one that means something."
EL_DILEMMA = "Ζυγίζω αν να αφήσω μια σίγουρη δουλειά για μία που έχει νόημα."
EN_BELIEF = "If I don't handle everything myself, it won't be done right."
EL_BELIEF = "Αν δεν τα κάνω όλα μόνος μου, δεν θα γίνουν σωστά."
EN_STRUGGLE = "User is torn between security and meaning at work."
EL_STRUGGLE = "Ο χρήστης είναι διχασμένος ανάμεσα στη σιγουριά και το νόημα."
EL_VALUE = "Ο χρήστης εκτιμά τη σταθερότητα πάνω από το ρίσκο."


def _db():
    """Records adds so Insight and MemoryEntry writes can be told apart.

    A plain recorder, not a MagicMock: the test asserts on the TYPE and the
    content of what was added, and a MagicMock would accept every attribute
    write and make "was an Insight persisted?" unanswerable (C-06).
    """
    db = MagicMock()
    db.added = []
    db.add = lambda row: db.added.append(row)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


async def _extract(user_text, entries):
    """extract_and_store with the LLM, embeddings and the insight throttle stubbed.

    safety_ok=True because the signal-insight block runs only on a clean
    exchange; the throttle is forced open so the test measures the language
    decision rather than the dedup gate.
    """
    import json as _json

    async def fake_complete(system, user, model=None, max_tokens=512):
        return _json.dumps(entries)

    db = _db()
    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(return_value=[0.0] * 1536)), \
         patch.object(memory_service, "_insight_gate_blocked",
                      new=AsyncMock(return_value=None)):
        saved = await memory_service.extract_and_store(
            db, "u1", "conv-1", "p1", user_text, "assistant reply",
            source_turn=1, safety_ok=True,
        )
    insights = [r for r in db.added if isinstance(r, Insight)]
    rows = [r for r in db.added if isinstance(r, MemoryEntry)]
    return saved, rows, insights


def _mk(type_, content, confidence=0.9):
    return {"type": type_, "content": content, "confidence": confidence}


# ── Only dilemma is dropped ───────────────────────────────────────────────────

def test_only_the_input_field_type_is_listed_as_droppable():
    """If a type is added here, it is because its content reaches a box the user
    types into — not because it is merely displayed."""
    assert VERBATIM_INPUT_SIGNAL_TYPES == ("dilemma",)


@pytest.mark.asyncio
async def test_an_english_dilemma_on_a_greek_turn_is_dropped_and_the_rest_survive():
    """The brief's matrix. The dilemma never becomes an Insight; the English
    struggle is still persisted, because a memory row in the wrong language is
    still a fact and nothing else records it."""
    entries = [
        _mk("dilemma", EN_DILEMMA),
        _mk("struggle", EN_STRUGGLE),
        _mk("value", EL_VALUE),
    ]
    with patch("services.memory_service.logger") as log:
        saved, rows, insights = await _extract(GREEK_TURN, entries)

    assert insights == [], "an English dilemma reached the Council prefill"
    contents = {r.content for r in rows}
    assert EN_STRUGGLE in contents, "the wrong-language struggle must still be written"
    assert EL_VALUE in contents
    assert len(saved) == 2, "dilemma is never a memory row; the other two are"

    dropped = [c for c in log.warning.call_args_list
               if c.kwargs.get("extra", {}).get("dropped")]
    assert len(dropped) == 1
    assert dropped[0].kwargs["extra"]["entry_type"] == "dilemma"
    assert dropped[0].kwargs["extra"]["expected_language"] == "Greek"


@pytest.mark.asyncio
async def test_the_kept_row_logs_without_the_dropped_marker():
    """The two behaviours have to be distinguishable in the logs, or the only way
    to tell a dropped signal from a kept row is to read the code."""
    entries = [_mk("struggle", EN_STRUGGLE)]
    with patch("services.memory_service.logger") as log:
        _, rows, _ = await _extract(GREEK_TURN, entries)

    assert len(rows) == 1
    warned = [c for c in log.warning.call_args_list
              if c.kwargs.get("extra", {}).get("site") == "extract_and_store"]
    assert len(warned) == 1
    assert warned[0].kwargs["extra"].get("dropped") is not True


@pytest.mark.asyncio
async def test_a_greek_dilemma_on_a_greek_turn_is_promoted():
    entries = [_mk("dilemma", EL_DILEMMA), _mk("struggle", EL_STRUGGLE)]
    with patch("services.memory_service.logger") as log:
        _, rows, insights = await _extract(GREEK_TURN, entries)

    assert len(insights) == 1
    assert insights[0].insight_type == "dilemma"
    assert insights[0].content == EL_DILEMMA
    assert len(rows) == 1
    assert not any(c.kwargs.get("extra", {}).get("dropped")
                   for c in log.warning.call_args_list)


@pytest.mark.asyncio
async def test_an_english_turn_is_unchanged():
    """The English path is the overwhelming majority of traffic and must not move."""
    entries = [_mk("dilemma", EN_DILEMMA), _mk("struggle", EN_STRUGGLE)]
    _, rows, insights = await _extract(ENGLISH_TURN, entries)

    assert len(insights) == 1
    assert insights[0].insight_type == "dilemma"
    assert insights[0].content == EN_DILEMMA
    assert len(rows) == 1


# ── The selection must fall through, not collapse ─────────────────────────────

@pytest.mark.asyncio
async def test_the_priority_order_still_advances_past_a_dropped_dilemma():
    """THE CASE THAT DECIDES WHERE THE CHECK GOES.

    Rejecting after selection would let the English dilemma take the slot and
    then be discarded, promoting nothing. Rejecting inside the predicate lets the
    loop advance to `belief`, which is the behaviour the priority order already
    promises for every other reason a candidate can fail.
    """
    entries = [_mk("dilemma", EN_DILEMMA), _mk("belief", EL_BELIEF)]
    _, _, insights = await _extract(GREEK_TURN, entries)

    assert len(insights) == 1, "the promotion collapsed instead of advancing"
    assert insights[0].insight_type == "belief"
    assert insights[0].content == EL_BELIEF


@pytest.mark.asyncio
async def test_a_second_well_formed_dilemma_is_reached_when_the_first_is_dropped():
    """Fall-through works within a type too, not only between types."""
    entries = [_mk("dilemma", EN_DILEMMA), _mk("dilemma", EL_DILEMMA)]
    _, _, insights = await _extract(GREEK_TURN, entries)

    assert len(insights) == 1
    assert insights[0].content == EL_DILEMMA


# ── Display-only types keep the log-only path ─────────────────────────────────

@pytest.mark.asyncio
async def test_an_english_belief_on_a_greek_turn_is_still_promoted():
    """belief is the Counterview ANCHOR — rendered read-only, never placed in an
    input. It keeps the log-only treatment deliberately; making this symmetric
    with dilemma would drop a usable insight for a cosmetic reason."""
    entries = [_mk("belief", EN_BELIEF)]
    _, rows, insights = await _extract(GREEK_TURN, entries)

    assert len(insights) == 1
    assert insights[0].insight_type == "belief"
    assert insights[0].content == EN_BELIEF
    assert len(rows) == 1, "belief is also a memory row and must still be written"


@pytest.mark.asyncio
async def test_an_english_aspiration_on_a_greek_turn_is_still_promoted():
    """aspiration routes to the Future Self ritual carrying no content at all."""
    entries = [_mk("aspiration", "I want to become someone who finishes things.", 0.8)]
    _, _, insights = await _extract(GREEK_TURN, entries)

    assert len(insights) == 1
    assert insights[0].insight_type == "aspiration"


# ── Pre-existing gates still hold ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_low_confidence_dilemma_is_still_rejected_on_confidence():
    """The language test is added to the predicate, not substituted for it."""
    entries = [_mk("dilemma", EL_DILEMMA, confidence=0.5)]
    _, _, insights = await _extract(GREEK_TURN, entries)
    assert insights == []


@pytest.mark.asyncio
async def test_no_insight_is_written_when_the_throttle_blocks():
    """Unchanged: a blocked gate is a routine zero-insight outcome, which is why
    dropping a dilemma needs no new downstream handling."""
    import json as _json

    async def fake_complete(system, user, model=None, max_tokens=512):
        return _json.dumps([_mk("dilemma", EL_DILEMMA)])

    db = _db()
    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(return_value=[0.0] * 1536)), \
         patch.object(memory_service, "_insight_gate_blocked",
                      new=AsyncMock(return_value="throttled")):
        await memory_service.extract_and_store(
            db, "u1", "conv-1", "p1", GREEK_TURN, "assistant reply",
            source_turn=1, safety_ok=True,
        )
    assert [r for r in db.added if isinstance(r, Insight)] == []


@pytest.mark.asyncio
async def test_an_unsafe_exchange_promotes_nothing():
    """safety_ok=False skips the whole signal block, language notwithstanding."""
    entries = [_mk("dilemma", EL_DILEMMA)]
    import json as _json

    async def fake_complete(system, user, model=None, max_tokens=512):
        return _json.dumps(entries)

    db = _db()
    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(return_value=[0.0] * 1536)):
        await memory_service.extract_and_store(
            db, "u1", "conv-1", "p1", GREEK_TURN, "assistant reply",
            source_turn=1, safety_ok=False,
        )
    assert [r for r in db.added if isinstance(r, Insight)] == []
