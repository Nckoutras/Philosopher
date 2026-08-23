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

# PHASE_3_MIGRATED_PERSONAS (a hardcoded set of 6 slugs) was retired here.
#
# It was transitional bookkeeping: tests skipped it to assert "unmigrated
# personas SKIP". Nobody updated it as personas were migrated or added, so by
# the time the registry reached 11 the list was wrong in both directions and the
# tests that depended on it failed for reasons unrelated to the code they check.
#
# Nothing hardcoded replaces it. Migration state is read from the persona config
# itself below, which cannot drift from reality by construction.


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

def test_every_registered_persona_has_response_length_words():
    """C-03 checklist item 1, as an executable check.

    This test used to assert the opposite — that unmigrated personas SKIP —
    against a hardcoded list of the 6 then-migrated slugs. The brevity migration
    has since completed for all 11 personas, so the unmigrated set is empty and
    the old test asserted something that can no longer be true.

    Inverted, it earns its place: it fails the moment a persona is added without
    response_length_words, which the checklist requires and nothing else
    enforces.
    """
    missing = [
        slug for slug, persona in PERSONA_REGISTRY.items()
        if check_brevity("Some reply.", persona).action == CheckAction.SKIP
    ]
    assert not missing, (
        f"personas missing response_length_words: {missing}. "
        "Every persona must populate it — see CLAUDE.md C-03."
    )


# test_check_brevity_is_active_for_migrated_personas was removed here: it
# asserted "the 6 listed personas do not SKIP", which
# test_every_registered_persona_has_response_length_words now covers for all 11
# without a list to maintain. Keeping both would be duplicate coverage anchored
# to the same retired constant.


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

def test_check_persona_forbidden_skips_exactly_the_personas_lacking_a_lexicon():
    """SKIP iff forbidden_lexicon_persona_specific is unpopulated.

    NOT inverted like the brevity test above, because this migration is genuinely
    incomplete — some personas still carry no persona-specific lexicon, and that
    is a real state, not stale bookkeeping. The old test asserted the same thing
    but decided which personas to expect via the hardcoded PHASE_3 list, which
    had drifted from the configs.

    Reading the expectation off the config makes the test self-maintaining: it
    tracks the migration as it proceeds instead of needing an edit per persona,
    and it still fails if the SKIP behaviour itself regresses.
    """
    for slug, persona in PERSONA_REGISTRY.items():
        has_lexicon = persona.forbidden_lexicon_persona_specific is not None
        r = check_persona_forbidden("Some reply.", persona)
        if has_lexicon:
            assert r.action != CheckAction.SKIP, (
                f"{slug}: has a persona lexicon but the check SKIPped it"
            )
        else:
            assert r.action == CheckAction.SKIP, (
                f"{slug}: has no persona lexicon; expected SKIP, got {r.action}"
            )


# test_check_persona_forbidden_is_active_for_migrated_personas was removed here:
# its assertion ("a persona with a lexicon does not SKIP") is the `if has_lexicon`
# half of
# test_check_persona_forbidden_skips_exactly_the_personas_lacking_a_lexicon,
# which derives the set from the configs instead of the retired constant.


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

    Enforced at the call site in conversation_service.py, not in
    postprocessing_service.py. This is a TRIPWIRE, not proof: it is a cheap
    structural check over the source text, and manual review at PR time remains
    the real safeguard. Its job is to make a refactor that postprocesses safety
    replies fail loudly enough that someone has to confront the invariant.

    It used to grep for `regenerate_or_trim`. That function still exists in
    postprocessing_service.py, but conversation_service.py stopped calling it —
    the wiring was reimplemented inline as check_universal_forbidden /
    check_brevity / _build_regen_directive plus a streaming correction. So the
    tripwire failed on a rename while the invariant it guards was intact, which
    is the worst thing a tripwire can do: cry wolf and get muted.

    It now checks the structure that actually enforces the invariant, and names
    no function that could be renamed out from under it.
    """
    from pathlib import Path
    cs_path = Path(__file__).resolve().parent.parent / "services" / "conversation_service.py"
    lines = cs_path.read_text(encoding="utf-8").split("\n")

    def _find(pred):
        return [i for i, ln in enumerate(lines) if pred(ln)]

    # 1. The post-generation safety branch and the postprocessing branch must be
    #    mutually exclusive — postprocessing hangs off an `elif`, so a suppressed
    #    reply cannot reach it.
    postproc = _find(lambda ln: ln.strip().startswith("elif POSTPROCESSING_ENABLED"))
    assert postproc, (
        "postprocessing is no longer guarded by `elif POSTPROCESSING_ENABLED`. "
        "If it moved to its own `if`, a safety-override reply can now reach it — "
        "confront the invariant before changing this test."
    )

    # POST-generation suppression is keyed on safety_out; PRE-generation on
    # safety_in. Matching the bare attribute would also catch branches in other
    # methods (the revisit path has its own safety_out block), so both checks
    # name the variable they mean.
    post_gen = _find(
        lambda ln: "safety_out.should_suppress_persona" in ln and ln.strip().startswith("if ")
    )
    assert post_gen, "post-generation safety-suppression branch missing entirely"

    # The elif must attach to a safety branch that opens BEFORE it, at the same
    # indentation — that adjacency is the whole mechanism.
    elif_line = postproc[0]
    guarding_if = [i for i in post_gen if i < elif_line]
    assert guarding_if, (
        "`elif POSTPROCESSING_ENABLED` no longer follows a safety_out suppression "
        "branch — the mutual exclusion that keeps safety replies out of "
        "postprocessing is gone. See Decision D."
    )
    assert (len(lines[elif_line]) - len(lines[elif_line].lstrip())) == (
        len(lines[guarding_if[-1]]) - len(lines[guarding_if[-1]].lstrip())
    ), "the postprocessing elif is not at the safety branch's indentation level"

    # 2. The PRE-generation safety branch returns outright, long before any of
    #    the above is reached — a suppressed input never gets generated for.
    pre_gen = _find(
        lambda ln: "safety_in.should_suppress_persona" in ln and ln.strip().startswith("if ")
    )
    assert pre_gen, "pre-generation safety branch missing"
    assert pre_gen[0] < elif_line, "pre-generation safety branch moved after postprocessing"
    window = lines[pre_gen[0]:pre_gen[0] + 20]
    assert any(ln.strip() == "return" for ln in window), (
        "the pre-generation safety branch no longer returns; a suppressed reply "
        "could now fall through into generation and postprocessing."
    )


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
