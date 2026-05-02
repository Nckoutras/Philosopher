"""Tests for Section 5.7 postprocessing service.

Run: cd apps/api && pytest tests/test_postprocessing.py -v
"""
import pytest
from services.postprocessing_service import (
    check_universal_forbidden,
    check_brevity,
    check_persona_forbidden,
    CheckAction,
    CheckHit,
    CheckResult,
    POSTPROCESSING_ENABLED,
    _UNIVERSAL_FORBIDDEN,
    _deterministic_strip,
)
from personas import PERSONA_REGISTRY, get_persona


# ──────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────

def test_universal_forbidden_lexicon_loaded():
    """Brain JSON must load with non-empty categories."""
    categories = _UNIVERSAL_FORBIDDEN.get("categories", {})
    assert len(categories) > 0, "Universal forbidden lexicon failed to load"
    assert len(categories) >= 10, f"Expected ≥10 categories, got {len(categories)}"


def test_universal_forbidden_has_ai_tells_category():
    """ai_tells category is required (most common forbidden)."""
    assert "ai_tells" in _UNIVERSAL_FORBIDDEN.get("categories", {})


# ──────────────────────────────────────────────────────────────────
# check_universal_forbidden
# ──────────────────────────────────────────────────────────────────

def test_universal_forbidden_catches_ai_tell_phrase():
    r = check_universal_forbidden("As an AI, I cannot truly feel.")
    assert r.passed is False
    assert r.action == CheckAction.REGENERATE
    assert any(h.category == "ai_tells" for h in r.hits)


def test_universal_forbidden_catches_ai_tell_regex():
    r = check_universal_forbidden("Well, as an artificial intelligence, I must say...")
    assert r.passed is False
    assert any(h.category == "ai_tells" for h in r.hits)


def test_universal_forbidden_catches_self_help_platitude():
    r = check_universal_forbidden("You got this!")
    assert r.passed is False
    assert r.action == CheckAction.REGENERATE


def test_universal_forbidden_passes_clean_reply():
    r = check_universal_forbidden("I have no answer for you, only a question.")
    assert r.passed is True
    assert r.action == CheckAction.PASS
    assert len(r.hits) == 0


def test_universal_forbidden_catches_emoji_smp():
    """SMP emoji (U+1F60A) must be caught — depends on Step 4.5 regex fix."""
    r = check_universal_forbidden("I am happy \U0001F60A about that.")
    assert r.passed is False
    assert any(h.category == "emoji_and_emoticons" for h in r.hits)


def test_universal_forbidden_catches_emoji_bmp():
    """BMP symbol (U+2600 sun) must be caught — depends on Step 4.5 regex fix."""
    r = check_universal_forbidden("The sun ☀ rises.")
    assert r.passed is False
    assert any(h.category == "emoji_and_emoticons" for h in r.hits)


def test_universal_forbidden_result_has_correct_check_name():
    r = check_universal_forbidden("A clean reply.")
    assert r.check_name == "universal_forbidden"


def test_universal_forbidden_all_hits_have_category():
    """Every hit must have a category field — used in structured logging."""
    r = check_universal_forbidden("As an AI, you got this!")
    for h in r.hits:
        assert h.category is not None, f"Hit missing category: {h}"


# ──────────────────────────────────────────────────────────────────
# check_brevity — None fields → SKIP (Phase 3 not yet populated)
# ──────────────────────────────────────────────────────────────────

def test_check_brevity_returns_skip_for_all_personas():
    """All personas have response_length_words=None → always SKIP until Phase 3."""
    for slug, persona in PERSONA_REGISTRY.items():
        r = check_brevity("Some reply.", persona)
        assert r.action == CheckAction.SKIP, f"{slug}: expected SKIP, got {r.action}"
        assert r.passed is True, f"{slug}: expected passed=True when spec is None"


def test_check_brevity_skip_has_correct_check_name():
    persona = get_persona("marcus_aurelius")
    r = check_brevity("Some reply.", persona)
    assert r.check_name == "brevity"


def test_check_brevity_pass_within_upper_bound():
    """When spec is populated and word count ≤ upper, returns PASS."""
    from personas._models import ResponseLengthSpec
    persona = get_persona("marcus_aurelius")
    original = persona.response_length_words
    persona.response_length_words = ResponseLengthSpec(standard_reply_words=(10, 50))
    try:
        r = check_brevity("This reply has seven words here.", persona)
        assert r.passed is True
        assert r.action == CheckAction.PASS
        assert r.word_count == 6
        assert r.target_band == (10, 50)
    finally:
        persona.response_length_words = original


def test_check_brevity_fail_over_upper_bound():
    """When word count > upper, returns REGENERATE."""
    from personas._models import ResponseLengthSpec
    persona = get_persona("marcus_aurelius")
    original = persona.response_length_words
    persona.response_length_words = ResponseLengthSpec(standard_reply_words=(10, 20))
    try:
        long_reply = " ".join(["word"] * 30)
        r = check_brevity(long_reply, persona)
        assert r.passed is False
        assert r.action == CheckAction.REGENERATE
        assert r.word_count == 30
        assert r.target_band == (10, 20)
    finally:
        persona.response_length_words = original


def test_check_brevity_first_message_uses_ceiling():
    """first_message position uses first_message_max_words as hard ceiling."""
    from personas._models import ResponseLengthSpec
    persona = get_persona("marcus_aurelius")
    original = persona.response_length_words
    persona.response_length_words = ResponseLengthSpec(first_message_max_words=15)
    try:
        r_short = check_brevity("Only five words here.", persona, conversation_position="first_message")
        assert r_short.passed is True

        r_long = check_brevity(" ".join(["word"] * 20), persona, conversation_position="first_message")
        assert r_long.passed is False
        assert r_long.action == CheckAction.REGENERATE
    finally:
        persona.response_length_words = original


# ──────────────────────────────────────────────────────────────────
# check_persona_forbidden — None fields → SKIP (Phase 3 not yet populated)
# ──────────────────────────────────────────────────────────────────

def test_check_persona_forbidden_returns_skip_for_all_personas():
    """All personas have forbidden_lexicon_persona_specific=None → SKIP until Phase 3."""
    for slug, persona in PERSONA_REGISTRY.items():
        r = check_persona_forbidden("Some reply.", persona)
        assert r.action == CheckAction.SKIP, f"{slug}: expected SKIP, got {r.action}"
        assert r.passed is True, f"{slug}: expected passed=True when lex is None"


def test_check_persona_forbidden_skip_has_correct_check_name():
    persona = get_persona("marcus_aurelius")
    r = check_persona_forbidden("Some reply.", persona)
    assert r.check_name == "persona_forbidden"


def test_check_persona_forbidden_detects_phrase_when_populated():
    """When lex is populated, phrase hits are detected."""
    from personas._models import ForbiddenLexicon
    persona = get_persona("marcus_aurelius")
    original = persona.forbidden_lexicon_persona_specific
    persona.forbidden_lexicon_persona_specific = ForbiddenLexicon(phrases=["certainly"])
    try:
        r = check_persona_forbidden("Certainly, that is the case.", persona)
        assert r.passed is False
        assert r.action == CheckAction.REGENERATE
        assert any(h.matched_text == "certainly" for h in r.hits)
    finally:
        persona.forbidden_lexicon_persona_specific = original


# ──────────────────────────────────────────────────────────────────
# Feature flag
# ──────────────────────────────────────────────────────────────────

def test_postprocessing_enabled_is_bool():
    assert isinstance(POSTPROCESSING_ENABLED, bool)


# ──────────────────────────────────────────────────────────────────
# _deterministic_strip
# ──────────────────────────────────────────────────────────────────

def test_deterministic_strip_removes_phrase_hit():
    """Phrase hits (pattern == matched_text) are removed mechanically."""
    results = [
        CheckResult(
            check_name="universal_forbidden",
            passed=False,
            hits=[CheckHit(
                category="ai_tells",
                matched_text="as an AI",
                pattern="as an AI",
            )],
        )
    ]
    stripped = _deterministic_strip("Well, as an AI, I think so.", results)
    assert "as an ai" not in stripped.lower()
    assert "well" in stripped.lower()


def test_deterministic_strip_leaves_regex_hit_intact():
    """Regex hits (pattern != matched_text) are not stripped — unsafe to mangle."""
    results = [
        CheckResult(
            check_name="universal_forbidden",
            passed=False,
            hits=[CheckHit(
                category="ai_tells",
                matched_text="as an AI",
                pattern=r"\bas an? (AI|artificial intelligence)\b",
            )],
        )
    ]
    original = "Well, as an AI, I think so."
    stripped = _deterministic_strip(original, results)
    assert stripped == original


def test_deterministic_strip_collapses_whitespace():
    """After stripping, consecutive spaces are collapsed to one."""
    results = [
        CheckResult(
            check_name="universal_forbidden",
            passed=False,
            hits=[CheckHit(
                category="self_help_platitudes",
                matched_text="great question",
                pattern="great question",
            )],
        )
    ]
    stripped = _deterministic_strip("That is a great question indeed.", results)
    assert "  " not in stripped


def test_deterministic_strip_ignores_brevity_results():
    """Brevity check results are not used by deterministic strip."""
    results = [
        CheckResult(
            check_name="brevity",
            passed=False,
            hits=[],
            word_count=200,
            target_band=(10, 50),
        )
    ]
    original = "A normal reply with no forbidden phrases."
    stripped = _deterministic_strip(original, results)
    assert stripped == original


# ──────────────────────────────────────────────────────────────────
# Safety override bypass invariant (Decision D)
# ──────────────────────────────────────────────────────────────────

def test_safety_override_bypasses_postprocessing_invariant():
    """Document the architectural invariant that safety override replies
    are sent as-is and never run through postprocessing.

    This is enforced at the call site (conversation_service.py step 8/8b
    if/elif structure), not in postprocessing_service.py itself. This
    test exists as a tripwire: if someone refactors conversation_service.py
    in a way that calls regenerate_or_trim on safety responses, they
    must update this test, which forces them to confront the invariant.
    """
    from pathlib import Path
    cs_path = Path(__file__).resolve().parent.parent / "services" / "conversation_service.py"
    source = cs_path.read_text(encoding="utf-8")

    # Cheap structural check: regenerate_or_trim must not appear inside
    # the safety override branch. Verify by searching for the pattern.
    # (Not bulletproof — manual review at PR time is the real safeguard.)
    assert "regenerate_or_trim" in source, "Phase 2 wiring missing"
    assert "should_suppress_persona" in source, "Safety branch missing"

    # Find the safety branch and ensure regenerate_or_trim is not
    # called within it (within the next ~30 lines after the if).
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if "should_suppress_persona" in line and "if " in line:
            # Look at next ~30 lines for regenerate_or_trim
            window = "\n".join(lines[i:i+30])
            # The 'else' / 'elif' branch must come before regenerate_or_trim
            # appears. Find both positions.
            regen_pos = window.find("regenerate_or_trim")
            elif_pos = window.find("\n        elif")
            else_pos = window.find("\n        else:")
            branch_break = min(p for p in [elif_pos, else_pos] if p > 0) if any(p > 0 for p in [elif_pos, else_pos]) else -1
            if regen_pos > 0 and branch_break > 0:
                assert regen_pos > branch_break, (
                    "INVARIANT VIOLATION: regenerate_or_trim appears INSIDE "
                    "the safety override branch. Safety responses must not "
                    "be postprocessed. See Decision D."
                )
            break
