"""Greek in the postprocessing voice checks (TD-60).

WHY THIS FILE EXISTS. #589 taught the SAFETY gates to read Greek. The
voice-quality checks in the same reply path were not touched and kept matching
with `.lower()`, which does not fold accents — so a Greek reply could not trip
the forbidden-lexicon check at all, whatever was in it. Not "matched weakly":
`.lower()` leaves `Θέλω` and `θελω` as different strings, and every Greek entry
part 2 adds would have been dead on arrival.

THREE THINGS ARE PINNED HERE, and they fail independently:

  1. Detection folds accents, case and final sigma — a Greek phrase is found in
     an accented reply, an unaccented one, and a ς/σ variant.
  2. What was FOUND is what gets STRIPPED. The check matches normalised text, so
     the phrase present in the reply may be an accented form of the lexicon
     entry. Stripping `re.escape(entry)` with IGNORECASE cannot remove that —
     IGNORECASE folds case, never accents — so the reply would ship with the
     forbidden phrase in it while the log said it was stripped.
  3. The reply the reader receives is NOT normalised. Stripping from a
     normalised copy would be simpler and would deliver `ο σωκρατησ` where the
     persona wrote `Ο Σωκράτης`.

Plus regressions: the English phrases and the four regex patterns that
normalisation could have broken still match exactly what they matched before.

The Greek entries here are TEST-INJECTED. No Greek is added to the shipped
lexicons in this PR — that is part 2 — so these tests describe the mechanism
rather than the content, and will not need editing when the content lands.
"""
import pytest

from personas import get_persona
from personas._models import ForbiddenLexicon
from services.postprocessing_service import (
    CheckAction,
    CheckHit,
    CheckResult,
    _deterministic_strip,
    check_persona_forbidden,
    check_universal_forbidden,
)
from text_utils import normalize, normalize_with_map
from services.safety_lexicons import ALL_BANDS


@pytest.fixture
def greek_persona():
    """marcus_aurelius with one Greek forbidden phrase, restored afterwards.

    Stored unaccented, the way a contributor would write it and the way the
    safety lexicons store Greek (#589).
    """
    persona = get_persona("marcus_aurelius")
    original = persona.forbidden_lexicon_persona_specific
    persona.forbidden_lexicon_persona_specific = ForbiddenLexicon(
        phrases=["ελπιζω να βοηθησα"]  # "I hope I helped" — an AI-tell in Greek
    )
    try:
        yield persona
    finally:
        persona.forbidden_lexicon_persona_specific = original


# ── 1. Detection folds what a reader does not see ─────────────────────────────

@pytest.mark.parametrize("reply", [
    "Ελπίζω να βοήθησα με αυτό.",          # accented, as a Greek keyboard types
    "ελπιζω να βοηθησα με αυτο.",          # unaccented, as people actually type
    "ΕΛΠΙΖΩ ΝΑ ΒΟΗΘΗΣΑ.",                  # caps
    "Ελπίζω να βοήθησα",                   # no trailing punctuation
])
def test_a_greek_phrase_is_detected_however_it_is_written(greek_persona, reply):
    r = check_persona_forbidden(reply, greek_persona)
    assert r.passed is False, f"{reply!r} did not trip the check"
    assert r.action == CheckAction.REGENERATE
    assert any(h.matched_text == "ελπιζω να βοηθησα" for h in r.hits)


def test_final_sigma_folds_to_sigma():
    """ς and σ are the same letter to a reader and different bytes to Python.

    The lexicon stores σ; a reply ends the word with ς. Without the fold this
    is a miss, and it is the single most common way a Greek entry dies.
    """
    persona = get_persona("marcus_aurelius")
    original = persona.forbidden_lexicon_persona_specific
    persona.forbidden_lexicon_persona_specific = ForbiddenLexicon(
        phrases=["ο σωκρατησ"]
    )
    try:
        r = check_persona_forbidden("Όπως έλεγε ο Σωκράτης, το ξέρω.", persona)
        assert r.passed is False
    finally:
        persona.forbidden_lexicon_persona_specific = original


def test_a_greek_reply_without_the_phrase_passes(greek_persona):
    r = check_persona_forbidden("Σκέψου το ξανά, με ησυχία.", greek_persona)
    assert r.passed is True


# ── 2. What was found is what gets stripped ───────────────────────────────────

def test_an_accented_greek_hit_is_actually_removed():
    """The gap this PR closes. Detection alone is not enough.

    The entry is unaccented; the reply is accented. re.sub(re.escape(entry))
    with IGNORECASE would find nothing and silently leave the phrase in place.
    """
    reply = "Ελπίζω να βοήθησα. Σκέψου το ξανά."
    results = [CheckResult(
        check_name="persona_forbidden",
        passed=False,
        action=CheckAction.REGENERATE,
        hits=[CheckHit(
            category="persona_specific",
            matched_text="ελπιζω να βοηθησα",
            pattern="ελπιζω να βοηθησα",
        )],
    )]
    stripped = _deterministic_strip(reply, results)
    assert "Ελπίζω" not in stripped
    assert "βοήθησα" not in stripped
    assert "Σκέψου το ξανά." in stripped


def test_the_stripped_reply_keeps_its_accents_and_case():
    """The reader gets the persona's text, not a normalised copy of it.

    This is why the strip maps a normalised span back onto the raw reply rather
    than stripping from normalised text.
    """
    reply = "Ελπίζω να βοήθησα. Όπως έλεγε ο Σωκράτης, η ψυχή θέλει ησυχία."
    results = [CheckResult(
        check_name="persona_forbidden", passed=False, action=CheckAction.REGENERATE,
        hits=[CheckHit(category="persona_specific",
                       matched_text="ελπιζω να βοηθησα",
                       pattern="ελπιζω να βοηθησα")],
    )]
    stripped = _deterministic_strip(reply, results)
    assert "Ο Σωκράτης" in stripped or "ο Σωκράτης" in stripped
    assert "ψυχή" in stripped
    assert "σωκρατησ" not in stripped, "the reply was normalised on its way out"


def test_every_occurrence_is_removed_not_only_the_first():
    reply = "Ελπίζω να βοήθησα. Πάλι: ελπιζω να βοηθησα."
    results = [CheckResult(
        check_name="persona_forbidden", passed=False, action=CheckAction.REGENERATE,
        hits=[CheckHit(category="persona_specific",
                       matched_text="ελπιζω να βοηθησα",
                       pattern="ελπιζω να βοηθησα")],
    )]
    stripped = _deterministic_strip(reply, results)
    assert "ελπιζω" not in stripped.lower()
    assert "Ελπίζω" not in stripped


# ── 3. Regressions: English behaves exactly as before ─────────────────────────

def test_an_english_phrase_still_trips():
    r = check_universal_forbidden("Well, as an AI I cannot say.")
    assert r.passed is False
    assert any(h.category == "ai_tells" for h in r.hits)


def test_an_english_phrase_hit_still_carries_the_entry_as_matched_text():
    """The CheckHit contract the strip depends on: pattern == matched_text
    identifies a phrase hit, and both are the lexicon entry."""
    r = check_universal_forbidden("Well, as an AI I cannot say.")
    phrase_hits = [h for h in r.hits if h.pattern == h.matched_text]
    assert phrase_hits, "no phrase hit — the strip would find nothing to remove"
    assert all(h.matched_text and h.matched_text == h.pattern for h in phrase_hits)


def test_a_clean_english_reply_still_passes():
    r = check_universal_forbidden("The question is older than either of us.")
    assert r.passed is True
    assert len(r.hits) == 0


# ── 4. The four regex patterns normalisation could have broken ────────────────
# Patterns are matched against the normalised reply but are NOT themselves
# normalised: casefold lowercases regex metacharacters and hex escapes, which
# turns \U0001F300 into  + "f300" and \S into \s. These four are the ones
# that would have died. See the module docstring in postprocessing_service.

@pytest.mark.parametrize("reply, category", [
    ("That is a fine thought 🔥", "emoji_and_emoticons"),      # \U0001F300-\U0001F9FF
    ("Consider this :D", "emoji_and_emoticons"),               # [:;]-?[\)\(D/\\PpO]
    ("## A heading", "list_formatting_in_replies"),         # ^#{1,6}\s+\S
])
def test_regex_patterns_still_match_what_they_matched_before(reply, category):
    r = check_universal_forbidden(reply)
    assert r.passed is False, f"{reply!r} no longer trips any pattern"
    assert any(h.category == category for h in r.hits), [h.category for h in r.hits]


def test_an_uppercase_emoticon_still_matches():
    """`:P` and `:O` live in a character class as literal uppercase letters.

    Normalising the PATTERN would casefold them out of the class. This is the
    case that proves patterns are left alone.
    """
    r = check_universal_forbidden("Fine :P")
    assert r.passed is False
    assert any(h.category == "emoji_and_emoticons" for h in r.hits)


# -- 5. The two views of the normaliser cannot drift ---------------------------

def test_normalize_agrees_with_normalize_with_map_on_the_whole_safety_lexicon():
    """normalize() is defined as normalize_with_map()[0]; this keeps that true
    if either is ever reimplemented for speed.

    The safety lexicon is the corpus that matters: its Greek entries are stored
    PRE-NORMALISED against this function (#589), so a normaliser that drifted
    would silently kill entries the import-time assertion still accepts.
    """
    entries = [w for band in ALL_BANDS.values() for w in band]
    assert len(entries) > 200, "lexicon collapsed - this would pass vacuously"
    for entry in entries:
        assert normalize(entry) == normalize_with_map(entry)[0], entry


@pytest.mark.parametrize("text", [
    "Ο Σωκράτης",
    "Θέλω να πεθάνω",
    "straße",
    "Café",
    "",
])
def test_the_index_map_is_one_entry_per_normalised_character(text):
    """Every mapped index must be a valid position in the ORIGINAL string.

    This is the property _deterministic_strip relies on to cut the raw reply:
    an off-by-one here would delete the wrong characters of a persona's answer.
    """
    norm, index_map = normalize_with_map(text)
    assert len(index_map) == len(norm)
    assert all(0 <= i < len(text) for i in index_map)
    assert index_map == sorted(index_map), "map must be non-decreasing"
