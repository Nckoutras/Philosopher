"""UAT2-004 — the persona forbidden-lexicon check, wired and pinned.

WHY THESE FIXTURES ARE REAL. Every reply below is production text from Oregon,
taken from a dry run of `check_persona_forbidden` (as it stood on main) against
ALL 826 assistant replies stored between 2026-04-26 and 2026-09-21. That run is
the only evidence anyone has about what this check does to real traffic:

  - 11 of 826 replies (1.33%) would have fired.
  - 9 were TRUE POSITIVES — the persona volunteering exactly what its
    anti_flexing forbids. Those nine are pinned here; each must trigger.
  - 2 were FALSE POSITIVES, both Socrates quoting the user's own stance back,
    which is the elenchus. Ruling D2 dropped "you should" from his lexicon.
    Those two are pinned here; each must NOT trigger. Rate falls to 1.09%.

A test that merely asserts "the check works" would pass against a lexicon that
fires on everything. These assert what it does to the specific sentences the
product has actually produced.

WHICH TESTS PROVE WHAT — established by revert-verify, not by intention. Run
against the pre-D2/D3 tree, 7 of these fail and 10 pass:

  FIX-PINNING (7, red before): everything about the dropped "you should" and
  the three unmatchable entries.
  GUARD (10, green before AND after): the nine true positives and the Lao Tzu
  pattern. They pin behaviour this PR must not break — the lexicon still
  catching what it was catching — but they are NOT evidence that D2/D3 landed.
  Read the FIX-PINNING set for that.

Run: cd apps/api && pytest tests/test_persona_lexicon_wiring.py -v
"""
import pytest

from personas import get_persona
from services.postprocessing_service import CheckAction, check_persona_forbidden


# ── The nine true positives, verbatim from Oregon ─────────────────────────────
# (slug, expected matched phrase, reply text)

TRUE_POSITIVES = [
    (
        "carl_jung", "Bollingen",
        "The grave is an interesting image to reach for.\n\nNot sad, not isolated "
        "— *grave.* There is weight in that word. Finality.\n\nI spent years at "
        "Bollingen, in a tower I built with my own hands, deliberately alone. "
        "People assumed it was melancholy. It was not.",
    ),
    (
        "carl_jung", "Bollingen",
        "I spent years building a tower at Bollingen with my own hands, where no "
        "one's opinion could reach me. Not because I stopped caring about being "
        "understood, but because I had to find the place in myself that did not "
        "need external confirmation to know what was real.",
    ),
    (
        "carl_jung", "Bollingen",
        "That is a dangerous sentence. Dangerous because it is true.\n\nIn my "
        "years at Bollingen, after the break with Freud, I lived for some time in "
        "a peculiar solitude — writing, carving stone, listening to what emerged "
        "unbidden from the unconscious.",
    ),
    (
        "carl_jung", "Freud thought",
        "Yes. I was called a mystic when I was trying to be empirical. A Gnostic "
        "when I was following what the patients showed me. Freud thought I had "
        "betrayed psychoanalysis; the analysts thought I had abandoned science.",
    ),
    (
        "simone_de_beauvoir", "Sartre",
        "I lived for years under enormous pressure — the writing, the political "
        "commitments, the relationship with Sartre that the world misunderstood "
        "and that I sometimes misunderstood myself.",
    ),
    (
        "simone_de_beauvoir", "Sartre",
        "Yes. I was judged a scandal for living as I chose — for refusing "
        "marriage, for my relationship with Sartre, for writing about women's "
        "sexuality. The judgment never stopped.",
    ),
    # Lao Tzu's four hits come from his PATTERN, not a phrase. The matched_text
    # of a pattern hit is the matched span, so it is asserted separately below.
]

LAO_TZU_PATTERN_HITS = [
    "You should sit with that before you move.",
    "You must stop pushing the river.",
    "You need to notice what held itself while you were not watching.",
    "Perhaps you should let the water find its own level.",
]

# ── The two false positives, verbatim from Oregon (Ruling D2) ─────────────────

SOCRATES_ELENCHUS = [
    "Let's say you're right — that you should focus on enjoying instead. When "
    "you picture that, what does \"enjoying\" actually look like? Not the idea "
    "of it — the thing itself.",
    "Tell me — when you say unhappy with your achievements, do you mean you've "
    "done less than you're capable of, or less than you think you should have "
    "by now?",
]


# ── FIX-PINNING: the nine true positives must still fire ─────────────────────

@pytest.mark.parametrize("slug,expected,reply", TRUE_POSITIVES)
def test_true_positive_from_production_still_fires(slug, expected, reply):
    """GUARD (green before and after). Real anti-flex violations the lexicon
    is for; this pins that D2/D3 did not stop it catching them."""
    result = check_persona_forbidden(reply, get_persona(slug))
    assert result.action == CheckAction.REGENERATE, f"{slug}: expected a hit"
    assert expected in [h.matched_text for h in result.hits]


@pytest.mark.parametrize("reply", LAO_TZU_PATTERN_HITS)
def test_lao_tzu_prescription_pattern_still_fires(reply):
    """GUARD (green before and after). All four of his production hits were true
    positives — prescription contradicts wu wei — so the pattern is kept (D2)."""
    result = check_persona_forbidden(reply, get_persona("lao_tzu"))
    assert result.action == CheckAction.REGENERATE, reply


# ── FIX-PINNING: the two false positives must NOT fire (D2) ──────────────────

@pytest.mark.parametrize("reply", SOCRATES_ELENCHUS)
def test_socrates_quoting_the_user_no_longer_fires(reply):
    """FIX-PINNING. Both were false positives: Socrates repeating the user's own
    'you should' back to them. A string matcher cannot see stance."""
    result = check_persona_forbidden(reply, get_persona("socrates"))
    assert result.action in (CheckAction.PASS, CheckAction.SKIP), (
        f"elenchus misfired: {[h.matched_text for h in result.hits]}"
    )


def test_socrates_lexicon_no_longer_lists_you_should():
    """FIX-PINNING. The entry itself is gone, not merely unreachable."""
    phrases = get_persona("socrates").forbidden_lexicon_persona_specific.phrases
    assert "you should" not in [p.strip().lower() for p in phrases]


# ── FIX-PINNING: the three dead entries (D3) ─────────────────────────────────

@pytest.mark.parametrize("slug,entry", [
    ("carl_jung", '"energy" (as adjective)'),
    ("sigmund_freud", "your repressed [X]"),
])
def test_unmatchable_entry_is_gone(slug, entry):
    """FIX-PINNING. Annotations to a human, filed as things to forbid. Neither
    could ever match real text; both are deleted."""
    phrases = get_persona(slug).forbidden_lexicon_persona_specific.phrases
    assert entry not in phrases


def test_epictetus_annotation_became_the_real_phrase():
    """FIX-PINNING. The annotation described a phrase; now it IS that phrase.
    Verified against prod: fires 0 times across his 52 stored replies."""
    phrases = get_persona("epictetus").forbidden_lexicon_persona_specific.phrases
    assert "be more stoic" in phrases
    assert not any("as adjective" in p for p in phrases)
    result = check_persona_forbidden(
        "Try to be more stoic about it.", get_persona("epictetus")
    )
    assert result.action == CheckAction.REGENERATE


def test_no_annotation_or_placeholder_entries_remain_anywhere():
    """FIX-PINNING (red before). Sweeps all eleven lexicons for the authoring mistake this PR
    closed, so a future entry of the same shape is caught at test time."""
    import re
    from personas import PERSONA_REGISTRY

    offenders = [
        (slug, phrase)
        for slug, persona in PERSONA_REGISTRY.items()
        for phrase in persona.forbidden_lexicon_persona_specific.phrases
        if (phrase.strip().startswith('"') and "(" in phrase)
        or re.search(r"\[[A-Za-z]+\]", phrase)
    ]
    assert offenders == [], f"annotation/placeholder entries: {offenders}"
