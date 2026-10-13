"""INS-001 / INS-002 / INS-003 — the three insight defects from UAT Day 2 (2026-10-13).

INS-001 (D2-002). A dilemma card was the person's own sentence, copied whole and
    shown back in quotation marks. Signal cards now rephrase: no run of more than
    five consecutive words from the source user message. One rephrase call if the
    extracted text copies; skip and log if that copies too. Evidence is always
    built from the ORIGINALLY extracted text (R4).
INS-002 (D2-003). One message typed into two conversations two seconds apart
    became "Noticed across 2 of your conversations". A recurrence card now counts
    only prior rows that are >= 24h older than the new row and come from a
    different source message. Echoes still count every raw hit.
INS-003 (D2-004). Two memory tasks both passed the 6h gate and wrote two cards
    one second apart. The gate is now asked again under a per-user advisory lock,
    at write time, for both classes.

These are the unit pins. The live checks (a real race, a real 24h filter, a
rephrased belief still retired by 'no') are in tests/db_live/test_insight_integrity_live.py.
"""
import inspect
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import services.memory_service as ms  # noqa: E402
from models import Insight  # noqa: E402
from services.memory_service import (  # noqa: E402
    MEMORY_EXTRACTION_PROMPT,
    REPHRASE_SIGNAL_PROMPT,
    card_eligible_matches,
    longest_shared_run,
    memory_service,
    signal_copies_user_words,
)

USER = "11111111-1111-1111-1111-111111111111"
CONV = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)

# The UAT Day 2 messages and cards, verbatim from production (2026-10-13).
LEAH = (
    "My closest friend, Leah, has started cancelling plans at the last minute. She says "
    "work is overwhelming, and I believe her, but this has happened five times in two "
    "months. I'm hurt and angry, yet I don't want to make her life harder. I'm torn "
    "between saying nothing and telling her that the friendship is starting to feel "
    "one-sided. How would you think about it?"
)
LEAH_CARD = ("I'm torn between saying nothing and telling her that the friendship is "
             "starting to feel one-sided.")
AMSTERDAM = (
    "My company has offered me a promotion in Amsterdam. I'd gain more influence and "
    "money, but I'd have to leave Bristol, where my sister and closest friends are. I "
    "keep telling myself career growth matters, but I'm not sure whether I want the "
    "role or the proof that I was chosen. How would you think about it?"
)
AMSTERDAM_CARDS = [
    "I'm weighing whether to accept a promotion that offers career growth and financial "
    "gain in Amsterdam, or stay in Bristol where my closest relationships are.",
    "I'm torn between accepting a promotion in Amsterdam that offers career growth and "
    "financial gain, versus staying in Bristol near my sister and closest friends.",
]


# ═══ INS-001: the five-word test ═════════════════════════════════════════════

def test_the_uat_card_fails_and_the_two_paraphrases_pass():
    """D2-002 was PARTIALLY confirmed: 1 of 3. The check must agree with that
    finding exactly — red on the copied card, green on both Amsterdam cards."""
    assert longest_shared_run(LEAH_CARD, LEAH) == 17  # one-sided -> one, sided
    assert signal_copies_user_words(LEAH_CARD, LEAH)
    for card in AMSTERDAM_CARDS:
        assert not signal_copies_user_words(card, AMSTERDAM), card


def test_five_shared_words_pass_and_six_fail():
    msg = "one two three four five six seven"
    assert not signal_copies_user_words("zero one two three four five eight", msg)
    assert signal_copies_user_words("zero one two three four five six eight", msg)


def test_case_and_the_typographic_apostrophe_do_not_hide_a_copy():
    msg = "I’M TORN BETWEEN STAYING AND LEAVING the city"
    assert signal_copies_user_words("i'm torn between staying and leaving", msg)


def test_greek_is_counted_in_words_too():
    msg = "Δεν ξέρω αν θέλω τη θέση ή την απόδειξη ότι με διάλεξαν."
    assert signal_copies_user_words("Δεν ξέρω αν θέλω τη θέση ή κάτι άλλο.", msg)
    assert not signal_copies_user_words("Αναρωτιέμαι τι θέλω πραγματικά από αυτή τη θέση.", msg)


def test_the_extraction_prompt_asks_every_signal_type_to_rephrase():
    """R1 + R3: only the three signal lines changed, and each carries the rule."""
    lines = {
        t: next(l for l in MEMORY_EXTRACTION_PROMPT.splitlines() if l.startswith(f'- "{t}":'))
        for t in ("dilemma", "belief", "aspiration")
    }
    for t, line in lines.items():
        assert "five consecutive words" in line, t
    assert "verbatim)" not in lines["dilemma"], "the dilemma line no longer asks for a verbatim field"


def test_the_rephrase_prompt_is_the_approved_text():
    """R2 approved this prompt verbatim. A paraphrase of it is a change."""
    assert REPHRASE_SIGNAL_PROMPT == (
        "You rewrite one sentence a person said about themselves so it keeps the same "
        "meaning in different words.\n"
        "- One sentence, first person, in the person's own voice.\n"
        "- Keep the meaning exactly: the same two sides of a decision, the same claim of "
        "a belief, the same direction of an aspiration. Add nothing; soften nothing.\n"
        "- Never reuse more than five consecutive words from the ORIGINAL MESSAGE.\n"
        "\n"
        "Return only the sentence, without quotation marks."
    )


def test_user_text_is_required_so_the_check_cannot_be_forgotten():
    p = inspect.signature(memory_service.promote_signal_insight).parameters["user_text"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


# ── promote_signal_insight: one rephrase, then skip ──────────────────────────

class _Db:
    """A plain recorder (C-06): the order of statements is what the lock tests read."""

    def __init__(self):
        self.added = []
        self.log = []
        self.flush = AsyncMock()
        self.commit = AsyncMock(side_effect=lambda: self.log.append("commit"))

    def add(self, row):
        self.log.append(("add", type(row).__name__))
        self.added.append(row)

    async def execute(self, stmt, params=None, *a, **k):
        self.log.append(("execute", str(stmt), params))
        return MagicMock()


def _gate(answer=None, log=None):
    async def gate(db, user_id, conversation_id, *, kind):
        if log is not None:
            log.append(("gate", kind))
        return answer
    return gate


async def _promote(signals, user_text, *, rephrase=None, saved_rows=None, language="English"):
    db = _Db()
    complete = AsyncMock(return_value=rephrase)
    with patch("services.memory_service.output_is_unsafe", new=AsyncMock(return_value=False)), \
         patch("services.memory_service.llm_client.complete", new=complete), \
         patch.object(memory_service, "_insight_gate_blocked", new=_gate(None, db.log)):
        written = await memory_service.promote_signal_insight(
            db, USER, CONV, "p1", signals, language,
            saved_rows=saved_rows, source_message_ids=["u1", "a1"], user_text=user_text,
        )
    return written, db, complete


@pytest.mark.asyncio
async def test_a_card_that_does_not_copy_is_written_as_extracted_with_no_extra_call():
    card = AMSTERDAM_CARDS[0]
    written, db, complete = await _promote(
        [{"type": "dilemma", "content": card, "confidence": 0.9}], AMSTERDAM,
    )
    assert written is True
    assert db.added[0].content == card
    complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_copying_card_is_rephrased_once_and_the_rephrase_is_written():
    rephrased = "I can't decide whether to keep quiet about it or tell her I feel taken for granted."
    written, db, complete = await _promote(
        [{"type": "dilemma", "content": LEAH_CARD, "confidence": 0.9}], LEAH,
        rephrase=rephrased,
    )
    assert written is True
    assert db.added[0].content == rephrased
    assert complete.await_count == 1
    kw = complete.await_args.kwargs
    assert kw["system"].startswith(REPHRASE_SIGNAL_PROMPT)
    assert LEAH_CARD in kw["user"] and LEAH in kw["user"]


@pytest.mark.asyncio
async def test_quotation_marks_around_the_rephrase_are_stripped():
    written, db, _ = await _promote(
        [{"type": "dilemma", "content": LEAH_CARD, "confidence": 0.9}], LEAH,
        rephrase="“I can't decide whether to keep quiet or tell her how it feels.”",
    )
    assert db.added[0].content == "I can't decide whether to keep quiet or tell her how it feels."


@pytest.mark.asyncio
@pytest.mark.parametrize("rephrase, reason", [
    (LEAH_CARD, "still_copies"),
    ("", "empty"),
    ("Δεν μπορώ να αποφασίσω αν θα της μιλήσω ή αν θα σωπάσω.", "language"),
])
async def test_a_failed_rephrase_writes_no_card_logs_why_and_never_retries_twice(caplog, rephrase, reason):
    caplog.set_level(logging.WARNING, logger="services.memory_service")
    written, db, complete = await _promote(
        [{"type": "dilemma", "content": LEAH_CARD, "confidence": 0.9}], LEAH, rephrase=rephrase,
    )
    assert written is False and db.added == []
    assert complete.await_count == 1, "ONE retry, never two"
    failed = [r for r in caplog.records if r.getMessage() == "signal_rephrase_failed"]
    assert [r.reason for r in failed] == [reason]


@pytest.mark.asyncio
async def test_a_rephrased_belief_still_cites_its_own_row_by_the_original_text():
    """R4. The belief's memory row holds the ORIGINALLY extracted text. Evidence
    built from the rephrased text would match no row, and a 'no' would silently
    stop retiring it. The live twin drives the 'no' through the real handler."""
    original = "I'm hurt and angry, yet I don't want to make her life harder."
    own_row = SimpleNamespace(id="row-belief", entry_type="belief", content=original)
    other = SimpleNamespace(id="row-other", entry_type="struggle", content="Something else.")
    written, db, _ = await _promote(
        [{"type": "belief", "content": original, "confidence": 0.9}], LEAH,
        rephrase="Being angry with her feels like it would only add to her load.",
        saved_rows=[own_row, other],
    )
    assert written is True
    card = db.added[0]
    assert card.content != original
    assert card.evidence["memory_entry_ids"] == ["row-belief"]


# ═══ INS-002: what a recurrence card may count ════════════════════════════════

def _m(mid, conv="conv-a"):
    return SimpleNamespace(id=mid, conversation_id=conv, content=f"row {mid}", score=0.9)


def _prov(created_at, md5):
    return {"created_at": created_at, "user_md5": md5}


def test_the_same_message_sent_twice_never_counts():
    """D2-003 exactly: the anchor's message has the new row's md5."""
    prov = {"new": _prov(NOW, "aaa"), "old": _prov(NOW - timedelta(days=3), "aaa")}
    assert card_eligible_matches("new", [_m("old")], prov) == []


def test_a_prior_row_younger_than_24h_never_counts():
    prov = {"new": _prov(NOW, "aaa"),
            "young": _prov(NOW - timedelta(hours=23, minutes=59), "bbb"),
            "exact": _prov(NOW - timedelta(hours=24), "ccc")}
    kept = card_eligible_matches("new", [_m("young"), _m("exact")], prov)
    assert [m.id for m in kept] == ["exact"], "24h counts; a minute short does not"


def test_a_row_with_no_source_message_is_exempt_from_a_but_not_from_b():
    prov = {"new": _prov(NOW, "aaa"),
            "old_null": _prov(NOW - timedelta(days=2), None),
            "young_null": _prov(NOW - timedelta(hours=1), None)}
    kept = card_eligible_matches("new", [_m("old_null"), _m("young_null")], prov)
    assert [m.id for m in kept] == ["old_null"]


def test_a_new_row_with_no_source_message_compares_nothing_by_md5():
    prov = {"new": _prov(NOW, None), "old": _prov(NOW - timedelta(days=2), None)}
    assert [m.id for m in card_eligible_matches("new", [_m("old")], prov)] == ["old"]


def test_a_row_whose_age_cannot_be_read_does_not_count():
    prov = {"new": _prov(NOW, "aaa")}
    assert card_eligible_matches("new", [_m("missing")], prov) == []
    assert card_eligible_matches("absent", [_m("x")], {"x": _prov(NOW - timedelta(days=9), "b")}) == []


def test_the_original_order_is_kept():
    prov = {"new": _prov(NOW, "n"), **{k: _prov(NOW - timedelta(days=2), k) for k in "abc"}}
    assert [m.id for m in card_eligible_matches("new", [_m("c"), _m("a"), _m("b")], prov)] == ["c", "a", "b"]


# ── detect_recurrence: card from survivors, echoes from everything ───────────

def _evidence_for(entry, matches):
    return {
        "recurring_entry": {"memory_entry_id": entry.id, "text": entry.content,
                            "conversation_id": entry.conversation_id},
        "prior_matches": [{"memory_entry_id": m.id, "text": m.content,
                           "conversation_id": m.conversation_id, "score": m.score}
                          for m in matches],
        "shown_to_classifier": len(matches[:5]),
        "detector": {"threshold": 0.75, "limit": 20, "window": None},
    }


async def _detect(entries_and_matches, provenance, *, locked_answer=None):
    db = _Db()
    found = {e.id: (ms_, _evidence_for(e, ms_)) for e, ms_ in entries_and_matches}
    echoes = AsyncMock(return_value=0)
    classify = AsyncMock(return_value=json.dumps(
        {"insight_type": "pattern", "content": "The same question about home keeps coming back."}))
    gate_answers = iter([None, locked_answer])

    async def gate(db_, user_id, conversation_id, *, kind):
        db.log.append(("gate", kind))
        return next(gate_answers)

    async def find(db_, user_id, entry, *, exclude_conversation=None):
        return found.get(entry.id)

    async def prov(db_, ids):
        return provenance

    with patch.object(ms, "find_recurrences", new=find), \
         patch.object(ms, "match_provenance", new=prov), \
         patch.object(memory_service, "_record_echoes", new=echoes), \
         patch.object(memory_service, "_insight_gate_blocked", new=gate), \
         patch("services.memory_service.output_is_unsafe", new=AsyncMock(return_value=False)), \
         patch("services.memory_service.llm_client.complete", new=classify):
        await memory_service.detect_recurrence(
            db=db, user_id=USER, conversation_id=CONV, persona_id="p1",
            new_entries=[e for e, _ in entries_and_matches], language="English",
        )
    return db, echoes, classify


def _entry(eid):
    return SimpleNamespace(id=eid, content=f"new {eid}", embedding=[0.1] * 8, conversation_id=CONV)


@pytest.mark.asyncio
async def test_when_every_match_is_filtered_echoes_still_count_and_no_card_is_written():
    e1 = _entry("e1")
    raw = [_m("same-msg")]
    db, echoes, classify = await _detect(
        [(e1, raw)],
        {"e1": _prov(NOW, "x"), "same-msg": _prov(NOW - timedelta(seconds=2), "x")},
    )
    (handed,) = echoes.await_args.args[2]
    assert handed[1] == raw, "B4 counts the RAW hit"
    assert db.added == []
    classify.assert_not_awaited()


@pytest.mark.asyncio
async def test_evidence_source_count_and_the_classifier_see_only_the_survivors():
    e1 = _entry("e1")
    old, young = _m("old", "conv-a"), _m("young", "conv-b")
    db, _, classify = await _detect(
        [(e1, [old, young])],
        {"e1": _prov(NOW, "n"), "old": _prov(NOW - timedelta(days=4), "o"),
         "young": _prov(NOW - timedelta(hours=2), "y")},
    )
    (card,) = db.added
    assert [p["memory_entry_id"] for p in card.evidence["prior_matches"]] == ["old"]
    assert card.evidence["shown_to_classifier"] == 1
    assert card.evidence["detector"]["window"] == "24h"
    assert card.evidence["kind"] == "recurrence"
    assert card.source_count == 2, "conv-a plus this one; conv-b's young row is not counted"
    prompt = classify.await_args.kwargs["user"]
    assert "row old" in prompt and "row young" not in prompt


@pytest.mark.asyncio
async def test_the_card_comes_from_the_first_row_with_a_surviving_match():
    e1, e2 = _entry("e1"), _entry("e2")
    db, _, _ = await _detect(
        [(e1, [_m("too-young")]), (e2, [_m("old")])],
        {"e1": _prov(NOW, "a"), "e2": _prov(NOW, "b"),
         "too-young": _prov(NOW - timedelta(hours=1), "c"),
         "old": _prov(NOW - timedelta(days=2), "d")},
    )
    (card,) = db.added
    assert card.evidence["recurring_entry"]["memory_entry_id"] == "e2"


# ═══ INS-003: the gate is asked again under a lock, at write time ═════════════

def _lock_statements(db):
    return [e for e in db.log if e[0] == "execute" and "pg_advisory_xact_lock" in e[1]]


@pytest.mark.asyncio
async def test_the_recurrence_write_locks_then_re_gates_then_writes_then_commits():
    e1 = _entry("e1")
    db, _, _ = await _detect(
        [(e1, [_m("old")])],
        {"e1": _prov(NOW, "a"), "old": _prov(NOW - timedelta(days=2), "b")},
    )
    seq = [e if e[0] != "execute" else ("lock",) for e in db.log]
    assert seq == [("gate", "recurrence"), ("lock",), ("gate", "recurrence"),
                   ("add", "Insight"), "commit"]
    (lock,) = _lock_statements(db)
    assert lock[2] == {"key": f"insight_gate:{USER}"}


@pytest.mark.asyncio
async def test_a_card_written_meanwhile_blocks_the_write_and_the_lock_is_released():
    """The D2-004 proof case, in miniature: the early gate said allowed, another
    task wrote while the classifier ran, the locked re-gate says throttle."""
    e1 = _entry("e1")
    db, _, _ = await _detect(
        [(e1, [_m("old")])],
        {"e1": _prov(NOW, "a"), "old": _prov(NOW - timedelta(days=2), "b")},
        locked_answer="throttle",
    )
    assert db.added == []
    assert db.log[-1] == "commit", "the transaction must end, or the lock is held"


@pytest.mark.asyncio
async def test_the_signal_write_locks_before_its_gate_on_the_same_key():
    written, db, _ = await _promote(
        [{"type": "dilemma", "content": AMSTERDAM_CARDS[0], "confidence": 0.9}], AMSTERDAM,
    )
    assert written is True
    seq = [e if e[0] != "execute" else ("lock",) for e in db.log]
    assert seq == [("lock",), ("gate", "signal"), ("add", "Insight")]
    (lock,) = _lock_statements(db)
    assert lock[2] == {"key": f"insight_gate:{USER}"}, "one key for both classes"
