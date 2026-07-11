"""Tests for the quote-nudge ranker (PR-5b ranking + PR-5d 3a signal priority).

Pure, synthetic, no DB / no async. `candidate_themes` and `rank_suggested_quotes`
do no I/O — the router loads the quotes and resolves the signal theme, then passes
both in. These tests pin the priority contract:

  3a (PR-5d): a live `signal_theme` match ranks FIRST, ahead of quotes with more
              questionnaire/onboarding overlap.
  3b/1 (PR-5b): with no signal (or no quote matching it), order is
              overlap desc → persona-affinity desc → quote.id asc, unchanged.

Persona affinity is monkeypatched into the ranker namespace so the affinity tier
is deterministic and independent of the real PERSONA_AFFINITIES table.

Run: cd apps/api && pytest tests/services/test_quote_suggest.py -v
"""
from types import SimpleNamespace

import pytest

import services.quote_suggest as qs
from services.quote_suggest import candidate_themes, rank_suggested_quotes


def _prefs(*, themes=None, answers=None):
    """Minimal UserPreference stub: only the fields candidate_themes reads.

    profile=None (answers=None) ⇒ empty questionnaire ⇒ onboarding `themes` drive
    the candidate set, which keeps these tests independent of themes_from_answers.
    """
    profile = {"answers": answers} if answers is not None else None
    return SimpleNamespace(profile=profile, themes=list(themes or []))


def _quote(qid, themes, *, persona_slug="zero", is_active=True):
    return SimpleNamespace(id=qid, themes=list(themes), persona_slug=persona_slug, is_active=is_active)


@pytest.fixture(autouse=True)
def _affinity(monkeypatch):
    """Deterministic persona affinity: 'hi' outweighs 'lo'; 'zero' contributes 0."""
    monkeypatch.setattr(qs, "PERSONA_AFFINITIES", {
        "hi": {"themes": {"freedom": 5, "work": 5, "grief": 5}},
        "lo": {"themes": {"freedom": 1, "work": 1, "grief": 1}},
        "zero": {"themes": {}},
    })


# ── 1. Signal theme wins over MORE questionnaire overlap (3a) ──────────────────

def test_signal_match_ranks_first_over_larger_overlap():
    prefs = _prefs(themes=["work", "grief", "freedom"])
    more_overlap = _quote("A", ["work", "grief"])          # overlap 2, no signal
    signal_hit = _quote("B", ["anxiety"])                   # overlap 1, signal match
    ranked = rank_suggested_quotes(
        prefs, [more_overlap, signal_hit], signal_theme="anxiety", limit=5
    )
    ids = [q.id for q, _ in ranked]
    assert ids[0] == "B"                                    # 3a wins despite less overlap
    assert ids == ["B", "A"]
    # matched_themes is the sorted overlap that drove each match.
    assert dict((q.id, mt) for q, mt in ranked) == {"B": ["anxiety"], "A": ["grief", "work"]}


# ── 2. No signal ⇒ identical to pre-5d (overlap → affinity → id) ───────────────

def test_no_signal_preserves_5b_order():
    prefs = _prefs(themes=["work", "freedom"])
    quotes = [
        _quote("big", ["work", "freedom"], persona_slug="zero"),  # overlap 2 → first
        _quote("hi", ["freedom"], persona_slug="hi"),             # overlap 1, aff 5
        _quote("lo", ["freedom"], persona_slug="lo"),             # overlap 1, aff 1
        _quote("b", ["work"], persona_slug="zero"),               # overlap 1, aff 0, id 'b'
        _quote("a", ["work"], persona_slug="zero"),               # overlap 1, aff 0, id 'a'
    ]
    ranked = rank_suggested_quotes(prefs, quotes, signal_theme=None, limit=5)
    assert [q.id for q, _ in ranked] == ["big", "hi", "lo", "a", "b"]


# ── 3. Signal present but NO quote matches it ⇒ fall through (fail-soft) ───────

def test_signal_with_no_matching_quote_falls_through_to_overlap():
    prefs = _prefs(themes=["work", "freedom"])
    quotes = [
        _quote("big", ["work", "freedom"], persona_slug="zero"),  # overlap 2
        _quote("hi", ["freedom"], persona_slug="hi"),             # overlap 1, aff 5
        _quote("lo", ["freedom"], persona_slug="lo"),             # overlap 1, aff 1
    ]
    # 'anxiety' is a valid candidate (prepended) but no quote carries it →
    # matches_signal is 0 for all, so ranking is exactly the 5b overlap/affinity order.
    ranked = rank_suggested_quotes(prefs, quotes, signal_theme="anxiety", limit=5)
    assert [q.id for q, _ in ranked] == ["big", "hi", "lo"]


# ── 4. candidate_themes: signal prepend + dedup, and signal-only ──────────────

def test_candidate_themes_prepends_new_signal():
    prefs = _prefs(themes=["work", "grief"])
    assert candidate_themes(prefs, "anxiety") == ["anxiety", "work", "grief"]


def test_candidate_themes_dedups_signal_already_present():
    prefs = _prefs(themes=["work", "grief"])
    cand = candidate_themes(prefs, "work")                  # 'work' already a candidate
    assert cand == ["work", "grief"]                        # moved to front, not duplicated
    assert cand.count("work") == 1


def test_candidate_themes_signal_only_when_no_other_themes():
    prefs = _prefs(themes=[])                               # empty questionnaire + onboarding
    assert candidate_themes(prefs, "grief") == ["grief"]    # signal alone drives it


def test_candidate_themes_no_signal_uses_onboarding():
    prefs = _prefs(themes=["work"])
    assert candidate_themes(prefs) == ["work"]


# ── 5. Fail-quiet: no candidates at all ⇒ [] ──────────────────────────────────

def test_no_candidates_returns_empty():
    prefs = _prefs(themes=[])                               # nothing anywhere, no signal
    quotes = [_quote("A", ["work"]), _quote("B", ["grief"])]
    assert rank_suggested_quotes(prefs, quotes, signal_theme=None, limit=5) == []


def test_inactive_quotes_excluded():
    prefs = _prefs(themes=["work"])
    quotes = [_quote("A", ["work"], is_active=False), _quote("B", ["work"])]
    ranked = rank_suggested_quotes(prefs, quotes, limit=5)
    assert [q.id for q, _ in ranked] == ["B"]
