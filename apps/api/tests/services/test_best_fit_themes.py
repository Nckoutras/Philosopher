"""Best-fit themes read the CHOSEN pill (founder ruling 2026-09-24).

themes_from_answers used to count the tags of the answered QUESTIONS and never
read the answer, so the three themes — and the two best-fit personas they feed —
were a function of which questions were answered. Every free user who finished the
fixed 15 got the same pair (Socrates + Orwell), whatever they chose; measured over
2,000 random free profiles: 1 theme set, 1 pair.

It now scores the SAME founder-approved pill_weights the radar reads, through the
locked bridge map, as share-of-achievable — the radar's own semantics. These tests
run against the real bank, the real bridge and the real compute_matches, so they
pin the outcome a user sees, not a restatement of the formula.

The ruling's own test: "a fix that still gives everyone the same two philosophers
is not a fix". The spread tests below are that sentence.

Run: cd apps/api && pytest tests/services/test_best_fit_themes.py -v
"""
import random
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from services import self_portrait as sp
from services import self_portrait_summary as sps
from services.matching_service import compute_matches
from services.self_portrait_summary import answers_fingerprint, themes_from_answers

FREE = [sp.get_question(q["id"]) for q in sp.visible_questions(False)]


def _pair(answers, need="challenge"):
    return tuple(m.slug for m in compute_matches(themes_from_answers(answers), need, top_n=2))


def _leaning(axis):
    """Each free question answered with the pill putting most weight on a radar
    axis — a person who leans that way. Ties go to the earlier pill."""
    tags = dict((k, t) for k, _l, t in sp.PORTRAIT_AXES)[axis]
    return {
        q["id"]: max(range(len(q["pills"])),
                     key=lambda i: (sum(q["pill_weights"][i].get(t, 0) for t in tags), -i))
        for q in FREE
    }


def test_the_free_slice_is_the_fifteen_this_was_measured_on():
    assert len(FREE) == 15
    assert all(q.get("pill_weights") for q in FREE)


def test_the_chosen_pill_changes_the_themes():
    """Same questions, different answers, different themes. Under the tag count
    all three were ['doubt', 'freedom', 'purpose']."""
    first = themes_from_answers({q["id"]: 0 for q in FREE})
    second = themes_from_answers({q["id"]: 1 for q in FREE})
    last = themes_from_answers({q["id"]: len(q["pills"]) - 1 for q in FREE})
    assert len({tuple(first), tuple(second), tuple(last)}) == 3


def test_three_answer_patterns_give_three_different_best_fit_pairs():
    pairs = {
        _pair({q["id"]: 0 for q in FREE}),
        _pair({q["id"]: 1 for q in FREE}),
        _pair({q["id"]: len(q["pills"]) - 1 for q in FREE}),
    }
    assert len(pairs) == 3, pairs


@pytest.mark.parametrize("axis,theme", [
    ("fear", "fear"),
    ("connection", "relationships"),
    ("duty", "work"),
])
def test_a_person_who_leans_one_way_gets_that_theme(axis, theme):
    """The lean shows: answering toward an axis puts its matching theme in the top
    three. (Raw weight sums failed this for connection and fear — identity, the
    most frequent tag, swamped them.)"""
    assert theme in themes_from_answers(_leaning(axis))


def test_random_free_profiles_no_longer_share_one_pair():
    """2,000 random completions of the free 15. Before: 1 theme set, 1 pair (100%).
    Measured after, at authoring: 592 theme sets, 35 pairs, top pair 16.7%."""
    rng = random.Random(7)
    sets, pairs = Counter(), Counter()
    for _ in range(2000):
        answers = {q["id"]: rng.randrange(len(q["pills"])) for q in FREE}
        sets[tuple(themes_from_answers(answers))] += 1
        pairs[_pair(answers)] += 1
    assert len(sets) > 100
    assert len(pairs) >= 20
    assert pairs.most_common(1)[0][1] / 2000 < 0.30


def test_a_theme_no_chosen_pill_reached_is_never_returned():
    """Share is only meaningful where the answers put weight; a zero-raw theme
    must not ride in on a tie."""
    answers = {FREE[0]["id"]: 0}
    q = FREE[0]
    chosen = sps._pill_theme_weights(q, 0)
    for theme in themes_from_answers(answers):
        assert chosen[theme] > 0


def test_unknown_ids_and_bad_pill_indices_are_skipped():
    good = {FREE[0]["id"]: 0}
    noisy = {**good, "no_such_question": 0, FREE[1]["id"]: 99, FREE[2]["id"]: True}
    assert themes_from_answers(noisy) == themes_from_answers(good)
    assert themes_from_answers({}) == []
    assert themes_from_answers(None) == []


# ── The cache follows the rule ────────────────────────────────────────────────

def test_the_scoring_version_is_part_of_the_cache_key():
    """Every portrait cached before this change holds best-fit personas chosen
    without reading an answer. Versioning the fingerprint makes each one stale, so
    it regenerates once on its next open (founder ruling: three users, three calls)."""
    answers = {FREE[0]["id"]: 0, FREE[1]["id"]: 2}
    current = answers_fingerprint(answers)
    with patch.object(sps, "PORTRAIT_SCORING_VERSION", sps.PORTRAIT_SCORING_VERSION - 1):
        older = answers_fingerprint(answers)
    assert current != older
    assert sps.PORTRAIT_SCORING_VERSION >= 2


# ── One definition of the person's themes ────────────────────────────────────

def test_the_quote_nudge_reads_the_same_answer_sensitive_themes():
    """quote_suggest.candidate_themes uses themes_from_answers, so the Today quote
    nudge follows the answers too — intended (founder ruling 2026-09-24), and pinned
    so nobody rediscovers it as a surprise."""
    from services.quote_suggest import candidate_themes

    for answers in ({q["id"]: 0 for q in FREE}, _leaning("fear")):
        prefs = MagicMock()
        prefs.profile = {"answers": answers}
        prefs.themes = ["work"]
        assert candidate_themes(prefs) == themes_from_answers(answers)
