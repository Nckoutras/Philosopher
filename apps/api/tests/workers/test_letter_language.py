"""Tests for the weekly/monthly letter language directive.

The 2026-08-24 incident: a production weekly letter rendered its body in English
while practical_takeaway and ritual_proposal came back in Greek — mixed languages
inside one letter, and the Greek was ungrammatical ("Θα σε κάλεσα").

Cause: neither prompt stated a language for the letter. LETTER_PROMPT's only
language reference sat on ritual_proposal ("the SAME language as the rest of this
letter"), which presupposes a letter language nothing established; MONTHLY_PROMPT
carried no language reference at all. With no anchor the model chose per FIELD.

Two things are covered here, because either one alone leaves the hole open:
  1. _dominant_language computes the period's language from the person's own words.
  2. Both prompts carry the {language} directive AND both .format() call sites
     actually pass it — a placeholder no caller fills renders as a KeyError, and a
     caller that fills a placeholder no prompt declares is silently ignored.

Run: cd apps/api && pytest tests/workers/test_letter_language.py -v
"""
import string
from pathlib import Path

from workers.arq_worker import (
    LETTER_PROMPT,
    MONTHLY_PROMPT,
    _dominant_language,
)

# A Greek-dominant week and an English-dominant week, as the person would write them.
GREEK_WEEK = [
    "Σκέφτομαι συνέχεια αν έκανα το σωστό με τη δουλειά.",
    "Δεν ξέρω γιατί με απασχολεί τόσο πολύ αυτό το θέμα.",
    "Μίλησα με τον αδερφό μου και ένιωσα καλύτερα.",
]
ENGLISH_WEEK = [
    "I keep wondering whether I made the right call about work.",
    "I do not know why this keeps bothering me so much.",
    "I spoke to my brother and felt better afterwards.",
]


def _format(prompt, language):
    """Compose a prompt exactly as the task call sites do."""
    return prompt.format(
        persona_name="Epictetus",
        persona_tradition_clause=", Stoic",
        user_first_name="Nikos",
        other_persona_slugs="seneca, nietzsche, marcus-aurelius",
        language=language,
    )


# ── _dominant_language ────────────────────────────────────────────────────────

def test_a_greek_dominant_period_returns_greek():
    assert _dominant_language(GREEK_WEEK) == "Greek"


def test_an_english_dominant_period_returns_english():
    assert _dominant_language(ENGLISH_WEEK) == "English"


def test_no_words_at_all_returns_english():
    # A ritual-only period can reach the letter with zero chat messages (A18).
    assert _dominant_language([]) == "English"
    assert _dominant_language(["", "   "]) == "English"


def test_an_exact_tie_returns_english():
    # Documented tie-break: English wins, so the default is never a coin flip.
    assert _dominant_language(["abcd", "αβγδ"]) == "English"


def test_a_mixed_period_follows_the_character_majority():
    # The real shape of the incident: a mostly-Greek week carrying English words.
    mixed = GREEK_WEEK + ["ok", "deadline"]
    assert _dominant_language(mixed) == "Greek"
    assert _dominant_language(ENGLISH_WEEK + ["ναι"]) == "English"


def test_punctuation_digits_and_emoji_do_not_vote():
    # Only letters count, so "2026-08-24!!! :)" cannot tip a period either way.
    assert _dominant_language(["2026-08-24 !!! ... 😀 —"]) == "English"
    assert _dominant_language(["2026 !!! 😀 αβγ"]) == "Greek"


def test_polytonic_greek_counts_as_greek():
    # Greek Extended (U+1F00-U+1FFF), not just the basic block: a person quoting
    # ancient text is still writing Greek.
    assert _dominant_language(["ἀρετὴ καὶ εὐδαιμονία"]) == "Greek"


def test_a_long_english_message_outweighs_a_short_greek_one():
    # Characters, not messages: one throwaway "ναι" cannot flip an English week.
    assert _dominant_language(["ναι", ENGLISH_WEEK[0]]) == "English"


# ── The directive reaches the prompt ──────────────────────────────────────────

def test_both_prompts_declare_the_language_placeholder():
    for name, prompt in (("LETTER_PROMPT", LETTER_PROMPT), ("MONTHLY_PROMPT", MONTHLY_PROMPT)):
        fields = {f for _, f, _, _ in string.Formatter().parse(prompt) if f}
        assert "language" in fields, f"{name} does not declare {{language}}"


def test_the_weekly_prompt_names_the_computed_language():
    prompt = _format(LETTER_PROMPT, _dominant_language(GREEK_WEEK))
    assert "in Greek" in prompt
    assert "Greek still governs every field" in prompt


def test_the_weekly_prompt_names_english_for_an_english_week():
    prompt = _format(LETTER_PROMPT, _dominant_language(ENGLISH_WEEK))
    assert "in English" in prompt
    assert "English still governs every field" in prompt


def test_the_monthly_prompt_names_the_computed_language():
    prompt = _format(MONTHLY_PROMPT, _dominant_language(GREEK_WEEK))
    assert "in Greek" in prompt
    assert "Greek still governs every field" in prompt


def test_the_monthly_prompt_names_english_for_an_english_month():
    prompt = _format(MONTHLY_PROMPT, _dominant_language(ENGLISH_WEEK))
    assert "in English" in prompt
    assert "English still governs every field" in prompt


def test_both_prompts_forbid_mixing_languages_between_fields():
    # The incident was not a wrong language — it was two languages in one letter.
    for prompt in (LETTER_PROMPT, MONTHLY_PROMPT):
        composed = _format(prompt, "Greek")
        assert "Never mix languages between fields" in composed


def _language_directive(prompt, language):
    """The LANGUAGE paragraph alone — it runs from the marker to the JSON shape.

    Sliced deliberately: the field names also appear further down in each prompt's
    own field specs, so asserting against the whole composed prompt would pass
    whether or not the directive itself names them.
    """
    return _format(prompt, language).split("LANGUAGE:")[1].split("Return JSON only")[0]


def test_the_weekly_directive_covers_the_fields_that_drifted():
    # practical_takeaway and ritual_proposal are the two that came back in the
    # wrong language; the rule must name them, not just "the letter".
    directive = _language_directive(LETTER_PROMPT, "Greek")
    assert "practical_takeaway" in directive
    assert "ritual_proposal" in directive


def test_the_monthly_directive_lists_the_monthly_fields_not_the_weekly_ones():
    # The two directives are deliberately NOT byte-identical. The monthly letter's
    # JSON has no ritual_proposal field, so naming it there would point the voice at
    # something that does not exist. Do not "fix" these two back into sync — the
    # schemas differ, so the field lists differ.
    directive = _language_directive(MONTHLY_PROMPT, "Greek")
    assert "practical_takeaway" in directive
    assert "ritual_proposal" not in directive


def test_the_monthly_schema_really_has_no_ritual_proposal():
    # The reason the directives diverge, asserted rather than assumed: if a future
    # PR adds ritual_proposal to the monthly letter, this fails and points at the
    # directive that then needs the field back.
    assert "ritual_proposal" not in MONTHLY_PROMPT
    assert "ritual_proposal" in LETTER_PROMPT


def test_the_ritual_proposal_language_sentence_is_retained():
    # It is now consistent with the global rule rather than dangling from nothing.
    assert "SAME language as the rest of this letter" in LETTER_PROMPT


# ── Both call sites pass it ───────────────────────────────────────────────────
#
# Source-scanning, in the style of tests/services/test_safety_event_log.py: a
# prompt that declares {language} while a call site omits it raises KeyError at
# letter time, in a worker, for one user — invisible until the letter goes missing.

def _worker_source() -> str:
    path = Path(__file__).resolve().parents[2] / "workers" / "arq_worker.py"
    return path.read_text(encoding="utf-8")


def _format_call_block(src: str, const: str) -> str:
    start = src.index(const + ".format(")
    out = []
    for line in src[start:].split("\n"):
        out.append(line)
        if line.strip() == ")":
            break
    return "\n".join(out)


def test_each_prompt_has_exactly_one_format_call_site():
    src = _worker_source()
    assert src.count("LETTER_PROMPT.format(") == 1
    assert src.count("MONTHLY_PROMPT.format(") == 1


def test_both_format_call_sites_pass_the_language():
    src = _worker_source()
    for const in ("LETTER_PROMPT", "MONTHLY_PROMPT"):
        block = _format_call_block(src, const)
        assert "language=" in block, f"{const}.format() does not pass language="


def test_the_language_passed_is_computed_from_the_period_not_hardcoded():
    src = _worker_source()
    for const in ("LETTER_PROMPT", "MONTHLY_PROMPT"):
        block = _format_call_block(src, const)
        assert "language=letter_language" in block, (
            f"{const}.format() must pass the computed language, not a literal"
        )
