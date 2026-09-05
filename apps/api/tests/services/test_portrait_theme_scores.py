"""Answer-sensitive octagon scoring: per-pill weights, share-of-achievable.

WHAT WAS WRONG. portrait_theme_scores counted each answered question's theme_tags
and never read the chosen pill, so the polygon was a function of WHICH questions a
person answered, not HOW. The free slice is a fixed 15 questions, so every free user
who completed it drew the byte-identical octagon no matter what they answered
(MEMORY_V2_INVESTIGATION_2026-09-03 §2a, defect 1). The prose half of that symptom
was fixed by the fingerprint PR (#595); this is the shape half.

The scoring is pure and bank-driven, so unlike most of the memory domain it is fully
testable without a database (TD-57 does not bite here).
"""
import json

import pytest

from services import self_portrait as sp
from services.self_portrait import (
    PORTRAIT_AXES,
    _load_bank,
    free_question_ids,
    portrait_theme_scores,
)

AXIS_KEYS = [key for key, _label, _tags in PORTRAIT_AXES]
FREE = sorted(free_question_ids())


def _vec(scores):
    return [d["score"] for d in scores]


def _top(scores):
    """Highest-scoring axis, frozen order breaking ties — the same rule the frontend
    caption and topAxisKey use."""
    return max(scores, key=lambda d: (d["score"], -AXIS_KEYS.index(d["key"])))["key"]


def _all_pill(index):
    """Answer every free-slice question with pill `index`, clamped to that question's
    pill count so the set is always valid."""
    return {
        qid: min(index, len(sp._BANK[qid]["pills"]) - 1)
        for qid in FREE
    }


# ── (a) Archetype separation — THE REGRESSION ────────────────────────────────

def test_two_archetypes_produce_different_vectors_and_different_top_axes():
    """MUST FAIL PRE-FIX: before per-pill weights these two were byte-identical,
    because the answered-question SET is the same in both."""
    first = portrait_theme_scores(_all_pill(0))
    second = portrait_theme_scores(_all_pill(1))

    assert _vec(first) != _vec(second)
    assert _top(first) != _top(second)


@pytest.mark.parametrize("a,b", [(0, 1), (0, 2), (1, 2), (2, 3), (0, 3)])
def test_every_archetype_pair_is_distinguishable(a, b):
    """Not just one lucky pair — no two uniform answer styles collapse together."""
    assert _vec(portrait_theme_scores(_all_pill(a))) != _vec(portrait_theme_scores(_all_pill(b)))


def test_the_pre_fix_behaviour_is_genuinely_gone():
    """Pins the defect itself: the score vector must NOT be a function of the
    answered-question set alone. Same keys in both, different values."""
    same_questions_different_answers = (_all_pill(0), _all_pill(3))
    a, b = same_questions_different_answers
    assert set(a) == set(b)
    assert _vec(portrait_theme_scores(a)) != _vec(portrait_theme_scores(b))


# ── (b) Re-answer sensitivity ────────────────────────────────────────────────

def test_changing_one_answer_moves_the_axes_that_question_scores():
    """conflict_001 scores power/resentment/control (axes meaning/connection/fear).
    Pill 0 is power=2, resentment=0, control=1; pill 1 is power=0, resentment=2,
    control=1 — so flipping it must move meaning and connection."""
    base = _all_pill(0)
    before = portrait_theme_scores(base)

    revised = dict(base)
    revised["conflict_001"] = 1
    after = portrait_theme_scores(revised)

    assert len(revised) == len(base)  # a re-answer, not an addition
    assert _vec(before) != _vec(after)

    by_key_before = {d["key"]: d["score"] for d in before}
    by_key_after = {d["key"]: d["score"] for d in after}
    # resentment (connection) gains, power (meaning) loses — before normalization at
    # least one of the two must visibly move.
    assert by_key_before["connection"] != by_key_after["connection"]


def test_a_single_answer_change_is_visible_on_a_minimal_answer_set():
    """With one question answered, the whole octagon is that question's shape, so the
    change is unambiguous and does not depend on normalization interplay."""
    one_way = portrait_theme_scores({"solitude_001": 0})   # loneliness 0, freedom 2, desire 0
    other_way = portrait_theme_scores({"solitude_001": 3})  # loneliness 2, freedom 0, desire 1

    by_a = {d["key"]: d["score"] for d in one_way}
    by_b = {d["key"]: d["score"] for d in other_way}
    assert by_a["freedom"] == 1.0 and by_a["connection"] == 0.0
    assert by_b["connection"] == 1.0 and by_b["freedom"] == 0.0


# ── (c) Fallback equivalence for unweighted questions ────────────────────────

def test_an_unweighted_question_contributes_its_legacy_per_tag_count():
    """The 345 unauthored questions must keep contributing exactly what they do
    today: weight 1 per theme_tag, the same for every pill, on BOTH sides of the
    ratio. Equal numerator and achievable per axis ⇒ share 1.0 on every axis the
    question touches, and identical whichever pill was chosen."""
    unweighted = next(
        qid for qid in sorted(sp._BANK) if "pill_weights" not in sp._BANK[qid]
    )
    q = sp._BANK[unweighted]
    touched = {sp._TAG_TO_AXIS[t] for t in q["theme_tags"] if t in sp._TAG_TO_AXIS}

    per_pill = [
        {d["key"]: d["score"] for d in portrait_theme_scores({unweighted: i})}
        for i in range(len(q["pills"]))
    ]
    # Pill-invariant, which is precisely what "no authored weights" should mean.
    assert all(p == per_pill[0] for p in per_pill)
    for key, score in per_pill[0].items():
        assert score == (1.0 if key in touched else 0.0)


def test_the_fallback_contributes_to_the_achievable_max_too_not_just_the_numerator():
    """If the fallback fed only the numerator, adding an unweighted question would
    inflate its axes without inflating the denominator. Mixing one weighted and one
    unweighted question must leave the unweighted question's axes at full share."""
    unweighted = next(
        qid for qid in sorted(sp._BANK)
        if "pill_weights" not in sp._BANK[qid]
        and not ({sp._TAG_TO_AXIS[t] for t in sp._BANK[qid]["theme_tags"] if t in sp._TAG_TO_AXIS}
                 & {"freedom", "connection", "desire"})
    )
    mixed = portrait_theme_scores({unweighted: 0, "solitude_001": 0})
    by_key = {d["key"]: d["score"] for d in mixed}

    touched = {sp._TAG_TO_AXIS[t] for t in sp._BANK[unweighted]["theme_tags"] if t in sp._TAG_TO_AXIS}
    for key in touched:
        # share == raw/achievable == 1.0 for a pill-invariant question, and the final
        # max-normalize divides by 1.0 since freedom also reaches 1.0 here.
        assert by_key[key] == 1.0


# ── (d) The output contract the frontend depends on ─────────────────────────

def test_axes_come_back_in_frozen_order_with_labels():
    scores = portrait_theme_scores(_all_pill(0))
    assert [d["key"] for d in scores] == AXIS_KEYS
    assert [d["label"] for d in scores] == [label for _k, label, _t in PORTRAIT_AXES]
    assert all(set(d) == {"key", "label", "score"} for d in scores)


@pytest.mark.parametrize("index", [0, 1, 2, 3])
def test_scores_are_bounded_and_the_strongest_axis_is_exactly_one(index):
    """The frame-filling contract: max == 1.0 for any non-empty answer set, and no
    score ever leaves [0, 1]."""
    scores = portrait_theme_scores(_all_pill(index))
    values = _vec(scores)
    assert all(0.0 <= v <= 1.0 for v in values)
    assert max(values) == 1.0


def test_an_empty_answer_set_is_all_zero_so_the_frontend_draws_bare_spokes():
    """portraitHasSignal = scores.some(s => s.score > 0). All-zero must survive."""
    assert _vec(portrait_theme_scores({})) == [0.0] * len(AXIS_KEYS)
    assert _vec(portrait_theme_scores(None)) == [0.0] * len(AXIS_KEYS)


def test_no_raw_counts_cross_the_wire():
    """The no-count rule: only the normalized score is emitted."""
    for d in portrait_theme_scores(_all_pill(0)):
        assert isinstance(d["score"], float)
        assert 0.0 <= d["score"] <= 1.0


def test_unknown_question_ids_are_skipped():
    assert _vec(portrait_theme_scores({"no_such_question_999": 0})) == [0.0] * len(AXIS_KEYS)


@pytest.mark.parametrize("bad", [99, -1, "0", None, True])
def test_an_out_of_range_or_non_int_answer_is_skipped_from_both_sides(bad, caplog):
    """Skip, not clamp: clamping would attribute an answer the user never gave, and
    skipping only the numerator would inflate a denominator it cannot feed. A skipped
    question must leave the octagon exactly as if it were absent."""
    with_bad = portrait_theme_scores({"solitude_001": 0, "conflict_001": bad})
    without = portrait_theme_scores({"solitude_001": 0})
    assert _vec(with_bad) == _vec(without)


def test_the_skip_is_logged_rather_than_silent(caplog):
    """A dropped answer is a real event — it must not vanish quietly."""
    import logging

    with caplog.at_level(logging.WARNING, logger="services.self_portrait"):
        portrait_theme_scores({"conflict_001": 99})

    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("conflict_001" in m and "99" in m for m in messages), messages


# ── (e) Loader validation — malformed weights must fail at load ─────────────

def _bank_file(tmp_path, question):
    p = tmp_path / "bank.json"
    p.write_text(json.dumps({"questions": [question]}), encoding="utf-8")
    return p


BASE_Q = {
    "id": "t_001",
    "category": "conflict",
    "question": "A question?",
    "pills": ["a", "b"],
    "theme_tags": ["power", "doubt"],
}


def test_a_well_formed_pill_weights_block_loads(tmp_path):
    q = dict(BASE_Q, pill_weights=[{"power": 2}, {"power": 0, "doubt": 1}])
    bank = _load_bank(_bank_file(tmp_path, q))
    assert bank["t_001"]["pill_weights"][0] == {"power": 2}


def test_a_question_without_pill_weights_still_loads(tmp_path):
    """Absent is legal — that is the whole fallback contract."""
    assert "t_001" in _load_bank(_bank_file(tmp_path, dict(BASE_Q)))


def test_wrong_length_pill_weights_raises(tmp_path):
    q = dict(BASE_Q, pill_weights=[{"power": 1}])  # 1 entry, 2 pills
    with pytest.raises(ValueError, match="pill_weights entries but 2 pills"):
        _load_bank(_bank_file(tmp_path, q))


def test_a_weight_key_outside_the_questions_theme_tags_raises(tmp_path):
    q = dict(BASE_Q, pill_weights=[{"power": 1}, {"grief": 1}])
    with pytest.raises(ValueError, match="not in its theme_tags"):
        _load_bank(_bank_file(tmp_path, q))


@pytest.mark.parametrize("value", [3, -1, 1.5, "2", None, True])
def test_an_out_of_range_or_non_int_weight_raises(tmp_path, value):
    q = dict(BASE_Q, pill_weights=[{"power": value}, {"power": 1}])
    with pytest.raises(ValueError, match="expected one of"):
        _load_bank(_bank_file(tmp_path, q))


def test_a_non_object_pill_weights_entry_raises(tmp_path):
    q = dict(BASE_Q, pill_weights=[["power", 1], {"power": 1}])
    with pytest.raises(ValueError, match="expected an object"):
        _load_bank(_bank_file(tmp_path, q))


def test_pill_weights_that_is_not_a_list_raises(tmp_path):
    q = dict(BASE_Q, pill_weights={"power": 1})
    with pytest.raises(ValueError, match="pill_weights entries but 2 pills"):
        _load_bank(_bank_file(tmp_path, q))


# ── (f) Weights integrity — the approved table, pinned ──────────────────────
#
# The founder approved this data explicitly and checked the bank hunk verbatim. A
# later silent edit to question_bank.json — a nudged 2, a swapped pill order — would
# change what the octagon says about a person with nothing else failing. This is the
# literal comparison that makes such an edit fail the suite.

APPROVED_PILL_WEIGHTS = {
    "conflict_001": [{"power": 2, "resentment": 0, "control": 1}, {"power": 0, "resentment": 2, "control": 1}, {"power": 1, "resentment": 2, "control": 2}, {"power": 0, "resentment": 1, "control": 2}],
    "conflict_002": [{"power": 2, "control": 2, "resentment": 0}, {"power": 0, "control": 2, "resentment": 2}, {"power": 1, "control": 0, "resentment": 1}, {"power": 1, "control": 2, "resentment": 2}],
    "desire_001": [{"desire": 2, "guilt": 0, "identity": 2}, {"desire": 1, "guilt": 2, "identity": 0}, {"desire": 2, "guilt": 2, "identity": 0}, {"desire": 1, "guilt": 1, "identity": 2}],
    "desire_002": [{"desire": 1, "discipline": 2, "control": 2}, {"desire": 2, "discipline": 0, "control": 0}, {"desire": 2, "discipline": 1, "control": 1}, {"desire": 2, "discipline": 1, "control": 0}],
    "family_001": [{"parents": 1, "guilt": 0, "duty": 0}, {"parents": 2, "guilt": 1, "duty": 1}, {"parents": 2, "guilt": 2, "duty": 2}, {"parents": 2, "guilt": 0, "duty": 1}],
    "family_002": [{"parents": 1, "identity": 2, "doubt": 0}, {"parents": 2, "identity": 1, "doubt": 1}, {"parents": 2, "identity": 1, "doubt": 2}, {"parents": 1, "identity": 2, "doubt": 0}],
    "fear_001": [{"fear": 1, "control": 1, "doubt": 0}, {"fear": 2, "control": 0, "doubt": 2}, {"fear": 2, "control": 1, "doubt": 2}, {"fear": 1, "control": 2, "doubt": 1}],
    "friendship_001": [{"friendship": 2, "loneliness": 0, "doubt": 0}, {"friendship": 0, "loneliness": 1, "doubt": 1}, {"friendship": 1, "loneliness": 2, "doubt": 2}, {"friendship": 1, "loneliness": 1, "doubt": 2}],
    "identity_001": [{"identity": 2, "loneliness": 0, "doubt": 0}, {"identity": 1, "loneliness": 1, "doubt": 0}, {"identity": 2, "loneliness": 1, "doubt": 0}, {"identity": 2, "loneliness": 1, "doubt": 2}],
    "meaning_001": [{"meaning": 1, "doubt": 0, "freedom": 2}, {"meaning": 1, "doubt": 1, "freedom": 0}, {"meaning": 2, "doubt": 2, "freedom": 1}, {"meaning": 2, "doubt": 1, "freedom": 0}],
    "money_001": [{"freedom": 2, "guilt": 0, "dilemma": 0}, {"freedom": 1, "guilt": 1, "dilemma": 1}, {"freedom": 0, "guilt": 2, "dilemma": 2}, {"freedom": 1, "guilt": 1, "dilemma": 1}],
    "mortality_001": [{"death": 1, "fear": 0, "meaning": 2}, {"death": 2, "fear": 2, "meaning": 0}, {"death": 2, "fear": 2, "meaning": 1}, {"death": 1, "fear": 0, "meaning": 2}],
    "relationships_001": [{"fear": 0, "identity": 2, "loneliness": 0}, {"fear": 2, "identity": 1, "loneliness": 1}, {"fear": 2, "identity": 1, "loneliness": 1}, {"fear": 1, "identity": 2, "loneliness": 2}],
    "solitude_001": [{"loneliness": 0, "freedom": 2, "desire": 0}, {"loneliness": 1, "freedom": 0, "desire": 2}, {"loneliness": 0, "freedom": 2, "desire": 1}, {"loneliness": 2, "freedom": 0, "desire": 1}],
    "work_and_ambition_001": [{"power": 1, "resentment": 0, "doubt": 1}, {"power": 0, "resentment": 2, "doubt": 2}, {"power": 2, "resentment": 1, "doubt": 1}, {"power": 1, "resentment": 1, "doubt": 0}],
}


def test_the_bank_carries_exactly_the_approved_weights():
    for qid, expected in APPROVED_PILL_WEIGHTS.items():
        assert sp._BANK[qid].get("pill_weights") == expected, qid


# Pro authoring, batch 1 of 8 (Ruling #3, "οι 345 αργότερα, σταδιακά"):
# work_and_ambition 002-030, founder-approved 2026-09-05. Listed as a range rather
# than 29 literals because the batch IS the contiguous range — a gap here would be
# a real finding, not a formatting choice.
BATCH1_WORK = {f"work_and_ambition_{n:03d}" for n in range(2, 31)}


def test_weights_are_authored_for_the_free_slice_and_the_batches_landed_so_far():
    """Scope pin. It read "…and nothing else yet" until Pro authoring began, with a
    docstring saying "When Pro weights are authored this test is the one that must be
    updated, which is the point — the scope change becomes explicit rather than
    incidental." This is that update, and the property is unchanged: authoring scope
    is stated here explicitly, so every batch is a visible edit to this line rather
    than a number that quietly drifts.

    15 free + 29 in batch 1 = 44 authored, 316 still on the legacy per-tag fallback.
    """
    weighted = {qid for qid, q in sp._BANK.items() if "pill_weights" in q}
    assert weighted == set(FREE) | BATCH1_WORK
    assert len(sp._BANK) - len(weighted) == 316


def test_the_free_slice_is_still_exactly_the_verbatim_pinned_table():
    """The batches must not disturb the 15. APPROVED_PILL_WEIGHTS covers the free
    slice only — see the note above it — so this is what keeps "we added Pro weights"
    from silently meaning "we also nudged a free one"."""
    assert set(APPROVED_PILL_WEIGHTS) == set(FREE)
    assert not (set(APPROVED_PILL_WEIGHTS) & BATCH1_WORK)


def test_every_authored_weight_block_agrees_with_its_questions_pills_and_tags():
    """Belt-and-braces over the loader: one dict per pill, keys within theme_tags."""
    for qid in APPROVED_PILL_WEIGHTS:
        q = sp._BANK[qid]
        assert len(q["pill_weights"]) == len(q["pills"]), qid
        for entry in q["pill_weights"]:
            assert set(entry) <= set(q["theme_tags"]), qid
            assert all(v in (0, 1, 2) for v in entry.values()), qid
