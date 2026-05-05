"""Tests for Section 5.7 postprocessing service.

Run: cd apps/api && pytest tests/test_postprocessing.py -v
"""
import pytest
from services.postprocessing_service import (
    check_universal_forbidden,
    check_brevity,
    check_persona_forbidden,
    regenerate_or_trim,
    CheckAction,
    CheckHit,
    CheckResult,
    POSTPROCESSING_ENABLED,
    _UNIVERSAL_FORBIDDEN,
    _deterministic_strip,
)
from personas import PERSONA_REGISTRY, get_persona

# Personas migrated to Phase 3 structured data. Append slugs as each persona
# is migrated. See HANDOFF_BRIEF_v3 §16.2 Phase 3 implementation status.
PHASE_3_MIGRATED_PERSONAS = {"socrates", "epictetus", "sigmund_freud", "carl_jung", "simone_de_beauvoir", "marcus_aurelius"}


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

def test_check_brevity_returns_skip_for_unmigrated_personas():
    """Personas without response_length_words populated → SKIP.

    Migrated personas (Phase 3) are excluded — see PHASE_3_MIGRATED_PERSONAS.
    """
    for slug, persona in PERSONA_REGISTRY.items():
        if slug in PHASE_3_MIGRATED_PERSONAS:
            continue
        r = check_brevity("Some reply.", persona)
        assert r.action == CheckAction.SKIP, f"{slug}: expected SKIP, got {r.action}"


def test_check_brevity_is_active_for_migrated_personas():
    """Personas with response_length_words populated → check is active (not SKIP)."""
    from personas import get_persona
    for slug in PHASE_3_MIGRATED_PERSONAS:
        persona = get_persona(slug)
        assert persona is not None, f"{slug}: persona not in registry"
        r = check_brevity("Some reply.", persona)
        assert r.action != CheckAction.SKIP, \
            f"{slug}: brevity check should not SKIP after migration, got {r.action}"


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

def test_check_persona_forbidden_returns_skip_for_unmigrated_personas():
    """Personas without forbidden_lexicon_persona_specific populated → SKIP."""
    for slug, persona in PERSONA_REGISTRY.items():
        if slug in PHASE_3_MIGRATED_PERSONAS:
            continue
        r = check_persona_forbidden("Some reply.", persona)
        assert r.action == CheckAction.SKIP, f"{slug}: expected SKIP, got {r.action}"


def test_check_persona_forbidden_is_active_for_migrated_personas():
    """Personas with forbidden_lexicon_persona_specific populated → check is active."""
    from personas import get_persona
    for slug in PHASE_3_MIGRATED_PERSONAS:
        persona = get_persona(slug)
        assert persona is not None, f"{slug}: persona not in registry"
        r = check_persona_forbidden("Some reply.", persona)
        assert r.action != CheckAction.SKIP, \
            f"{slug}: persona forbidden check should not SKIP after migration, got {r.action}"


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


def test_deterministic_strip_brevity_trims_at_last_sentence():
    """Brevity hit: reply trimmed to last full sentence ending within max_words."""
    def _sentence(word, n):
        return " ".join([word] * (n - 1)) + f" {word}."

    s1 = _sentence("alpha", 20)    # 20 words, ends "alpha."
    s2 = _sentence("beta", 20)     # 20 words, ends "beta."
    s3 = _sentence("gamma", 20)    # 20 words, ends "gamma."
    s4 = _sentence("delta", 25)    # 25 words — extends past word 80, "delta." at word 85
    s5 = _sentence("epsilon", 15)  # 15 words
    reply = f"{s1} {s2} {s3} {s4} {s5}"  # 100 words total

    results = [
        CheckResult(
            check_name="brevity",
            passed=False,
            action=CheckAction.REGENERATE,
            word_count=100,
            target_band=(40, 80),
        )
    ]
    stripped = _deterministic_strip(reply, results)

    # words[:80] = s1+s2+s3 (60 words) + first 20 of s4 (no period).
    # Last terminator in prefix is "." ending s3.
    assert stripped == f"{s1} {s2} {s3}"
    assert stripped.endswith(".")
    assert "delta" not in stripped
    assert "epsilon" not in stripped


def test_deterministic_strip_brevity_no_terminator_falls_back_to_word_trim(caplog):
    """No sentence terminator in prefix — falls back to hard word-boundary cut and logs."""
    import logging

    # 100-word reply: first 80 words are terminator-free, period only after word 80
    no_term = " ".join(["running"] * 80)
    tail = " " + " ".join(["ending"] * 19) + " done."  # 20 words
    reply = no_term + tail  # 100 words

    results = [
        CheckResult(
            check_name="brevity",
            passed=False,
            action=CheckAction.REGENERATE,
            word_count=100,
            target_band=(40, 80),
        )
    ]
    with caplog.at_level(logging.WARNING):
        stripped = _deterministic_strip(reply, results)

    assert stripped == no_term
    assert any(r.msg == "hard_cut_no_sentence_boundary" for r in caplog.records)


def test_deterministic_strip_brevity_handles_markdown_emphasis():
    """Trim point correctly includes a closing asterisk after the sentence terminator."""
    # 72-word reply: preamble (67 words) + "*That is so.*" (3 words) + "more text" (2 words)
    # max_words=70 captures the closing asterisk but not "more text"
    preamble = " ".join(["intro"] * 67)   # 67 words, no terminators
    closing = "*That is so.*"              # 3 words: "*That", "is", "so.*"
    extra = "more text"                    # 2 words
    reply = f"{preamble} {closing} {extra}"  # 72 words total

    results = [
        CheckResult(
            check_name="brevity",
            passed=False,
            action=CheckAction.REGENERATE,
            word_count=72,
            target_band=(40, 70),
        )
    ]
    stripped = _deterministic_strip(reply, results)

    # words[:70] = preamble(67) + "*That"(1) + "is"(1) + "so.*"(1) = 70 words.
    # Pattern [.!?][\"\')\]\*]* matches ".*" in "so.*", end includes the asterisk.
    assert stripped.endswith("*")
    assert "more" not in stripped
    assert "text" not in stripped


def test_deterministic_strip_brevity_within_band_returns_unchanged():
    """Defensive: brevity result present but word count already <= max_words — no trim."""
    reply = " ".join(["word"] * 50)  # 50 words

    results = [
        CheckResult(
            check_name="brevity",
            passed=False,
            action=CheckAction.REGENERATE,
            word_count=50,
            target_band=(40, 90),
        )
    ]
    stripped = _deterministic_strip(reply, results)

    # len(words)=50 <= max_words=90 → no trim branch entered
    assert stripped == reply


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


# ──────────────────────────────────────────────────────────────────
# Layer 3 observability — brevity_passed_but_mid_sentence
# ──────────────────────────────────────────────────────────────────

async def test_brevity_passed_but_mid_sentence_logs_warning(caplog):
    """Layer 3: warning fires when brevity passes but reply ends without a sentence terminator."""
    from unittest.mock import patch
    import logging

    persona = get_persona("marcus_aurelius")
    reply = "A mid-sentence reply fragment without any terminal punctuation"

    passing_brevity = CheckResult(
        check_name="brevity",
        passed=True,
        action=CheckAction.PASS,
        word_count=10,
        target_band=(10, 90),
    )
    passing_universal = CheckResult(
        check_name="universal_forbidden",
        passed=True,
        action=CheckAction.PASS,
    )
    passing_persona = CheckResult(
        check_name="persona_forbidden",
        passed=True,
        action=CheckAction.SKIP,
    )

    with caplog.at_level(logging.WARNING), \
         patch("services.postprocessing_service.check_universal_forbidden",
               return_value=passing_universal), \
         patch("services.postprocessing_service.check_brevity",
               return_value=passing_brevity), \
         patch("services.postprocessing_service.check_persona_forbidden",
               return_value=passing_persona):
        await regenerate_or_trim(
            reply=reply,
            persona=persona,
            system_prompt="system",
            user_text="user",
        )

    assert any(r.msg == "brevity_passed_but_mid_sentence" for r in caplog.records)
