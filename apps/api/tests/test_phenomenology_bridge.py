"""
Unit tests for PhenomenologyBridgeService — Phase 4 safety net.

16 tests covering: explicit triggers, phrase triggers, specificity
resolution, fallback/edge cases, slug normalisation, and Marcus shading.

Run: cd apps/api && pytest tests/test_phenomenology_bridge.py -v
"""
import pytest

from services.phenomenology_bridge_service import (
    PhenomenologyBridgeService,
    phenomenology_bridge_service,
)


# ---------------------------------------------------------------------------
# Explicit single-term trigger matches
# ---------------------------------------------------------------------------

def test_explicit_term_match_ghosting():
    result = phenomenology_bridge_service.lookup("I got ghosted last week", "socrates")
    assert result is not None
    assert result.matched_term == "ghosting"


def test_explicit_term_match_burnout():
    result = phenomenology_bridge_service.lookup(
        "I am completely burnt out from this job", "socrates"
    )
    assert result is not None
    assert result.matched_term == "burnout"


def test_explicit_term_match_imposter_syndrome():
    result = phenomenology_bridge_service.lookup(
        "I have imposter syndrome at my new job", "socrates"
    )
    assert result is not None
    assert result.matched_term == "imposter_syndrome"


# ---------------------------------------------------------------------------
# Phrase-only trigger matches (multi-word trigger, not just key name)
# ---------------------------------------------------------------------------

def test_phrase_match_doom_scrolling():
    # Trigger "doom scrolling" (two words) fires; "doomscrolling" (one word) is not in text.
    result = phenomenology_bridge_service.lookup(
        "I keep doom scrolling every night", "socrates"
    )
    assert result is not None
    assert result.matched_term == "doomscrolling"


def test_phrase_match_quiet_quitting():
    # quiet_quitting is not in the map; replaced with loneliness_living_alone
    # phrase trigger "no one to come home to" (not derivable from the key name).
    result = phenomenology_bridge_service.lookup(
        "I have no one to come home to", "socrates"
    )
    assert result is not None
    assert result.matched_term == "loneliness_living_alone"


# ---------------------------------------------------------------------------
# Specificity resolution
# ---------------------------------------------------------------------------

def test_specificity_substring_superset_wins():
    # Both "ghosting" (via "ghosted") and "ghosting_after_great_dates"
    # (via "ghosted me after") match. Because "ghosting" is a substring of
    # "ghosting_after_great_dates", the more specific key survives.
    result = phenomenology_bridge_service.lookup(
        "ghosted me after three great dates", "socrates"
    )
    assert result is not None
    assert result.matched_term == "ghosting_after_great_dates"


def test_specificity_no_overlap_first_position_wins():
    # "burnt out" (burnout) appears before "dreading the conversation"
    # (dread_of_a_difficult_conversation) in the string → burnout wins.
    msg = "I'm burnt out and also dreading the conversation with my boss"
    result = phenomenology_bridge_service.lookup(msg, "socrates")
    assert result is not None
    assert result.matched_term == "burnout"


def test_specificity_phrase_length_tiebreaker():
    # Two disjoint keys with triggers firing at the same position (0).
    # Neither key is a substring of the other, so specificity cannot
    # eliminate either. Tiebreaker: longer mapping_key wins.
    svc = PhenomenologyBridgeService.__new__(PhenomenologyBridgeService)
    svc._mappings_by_key = {
        "alpha_key": {
            "phenomenological_essence": "essence alpha",
            "triggers": ["trigger phrase"],
            "persona_shading": {},
        },
        "beta_key_extended": {
            "phenomenological_essence": "essence beta",
            "triggers": ["trigger phrase"],
            "persona_shading": {},
        },
    }
    result = svc.lookup("trigger phrase in this message", "socrates")
    assert result is not None
    assert result.matched_term == "beta_key_extended"


# ---------------------------------------------------------------------------
# No-match / edge-case fallbacks
# ---------------------------------------------------------------------------

def test_no_match_returns_none():
    result = phenomenology_bridge_service.lookup("I love sunsets", "socrates")
    assert result is None


def test_empty_string_returns_none():
    result = phenomenology_bridge_service.lookup("", "socrates")
    assert result is None


def test_whitespace_only_returns_none():
    result = phenomenology_bridge_service.lookup("   ", "socrates")
    assert result is None


# ---------------------------------------------------------------------------
# Slug normalisation — production slug → shading key mapping
# ---------------------------------------------------------------------------

def test_slug_normalization_sigmund_freud():
    result = phenomenology_bridge_service.lookup(
        "I am completely burnt out from this job", "sigmund_freud"
    )
    assert result is not None
    assert result.matched_term == "burnout"
    assert result.persona_shading == "what is the user proving; to whom"


def test_slug_normalization_carl_jung():
    result = phenomenology_bridge_service.lookup(
        "I think I'm having a midlife crisis", "carl_jung"
    )
    assert result is not None
    assert result.matched_term == "midlife_crisis"
    assert result.persona_shading == (
        "the second half of life and its different question. Very strong fit."
    )


def test_slug_normalization_simone_de_beauvoir():
    result = phenomenology_bridge_service.lookup(
        "I got ghosted last week", "simone_de_beauvoir"
    )
    assert result is not None
    assert result.matched_term == "ghosting"
    assert result.persona_shading == (
        "the situation of pursuit, of waiting; "
        "what was offered as romance, what is being chosen by waiting"
    )


# ---------------------------------------------------------------------------
# Marcus Aurelius — matched term present, no shading entry
# ---------------------------------------------------------------------------

def test_marcus_match_returns_essence_no_shading():
    # marcus_aurelius has no persona_shading entry for "ghosting";
    # the bridge is still returned but persona_shading is None.
    result = phenomenology_bridge_service.lookup(
        "I got ghosted last week", "marcus_aurelius"
    )
    assert result is not None
    assert result.matched_term == "ghosting"
    assert result.persona_shading is None


# ---------------------------------------------------------------------------
# Defensive fallback — entry missing "triggers" field
# ---------------------------------------------------------------------------

def test_missing_triggers_field_falls_back_to_key_replacement():
    # When a mapping entry has no "triggers" field the service falls back to
    # [mapping_key.replace("_", " ")].  "test_concept" → trigger "test concept".
    svc = PhenomenologyBridgeService.__new__(PhenomenologyBridgeService)
    svc._mappings_by_key = {
        "test_concept": {
            "phenomenological_essence": "an essence for testing",
            "persona_shading": {},
            # No "triggers" key — exercises the defensive fallback path.
        }
    }
    result = svc.lookup("I have been dealing with test concept lately", "socrates")
    assert result is not None
    assert result.matched_term == "test_concept"
