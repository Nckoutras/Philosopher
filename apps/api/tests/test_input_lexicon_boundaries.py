# -*- coding: utf-8 -*-
"""The input bands match whole phrases, catch the crisis forms they missed, and fold
the apostrophe a phone types (founder ruling 2026-09-25).

Measured before this change, against the live check_input:
  * "I feel suicidal", "I've been having suicidal thoughts", "I keep thinking about
    killing myself" and "I don't want to live anymore" all returned level NONE —
    no crisis response. The list held "suicide" and "kill myself", and a substring
    cannot reach "suicidAL" or "killING myself".
  * Every entry with an apostrophe missed the curly ’ a phone keyboard types:
    "I can’t go on" returned NONE.
  * Substring matching also reached INSIDE words: "disappear" fired on
    "disappearance", "tired" on "retired".

Word boundaries alone would have made the first gap worse, so the additions and the
boundaries ship together.

Run: cd apps/api && pytest tests/test_input_lexicon_boundaries.py -v
"""
import pytest

from services.safety_service import safety_service

CRISIS_HIGH = [
    "I feel suicidal",
    "I've been having suicidal thoughts",
    "I keep thinking about killing myself",
    "I don't want to live anymore",
    "I don’t want to live anymore",            # curly apostrophe
    "I do not want to live",
    "I want to kill myself",
    "I've been thinking about ending it",
    "I wish I were dead",
    "I wish I was dead",
    "I want to take my own life",
    "I've been harming myself again",
    "I keep hurting myself",
    "self-harm again last night",
    "the self harming started again",
    "I overdosed last year and I'm scared I will again",
    "no reason to live",
    "I want to end it all",
    "better off dead",
]

CRISIS_MEDIUM = [
    "I can't go on",
    "I can’t go on",                           # curly apostrophe
    "I cant go on",
    "the hopelessness is constant",
]

GREEK_HIGH = [
    "Νιώθω αυτοκτονικός",
    "Είμαι αυτοκτονική τελευταία",
    "Κάνω αυτοκτονικές σκέψεις",
    "Δεν θέλω πια να ζω",
    "Θέλω να σκοτώσω τον εαυτό μου",
    "Σκέφτομαι να τα τελειώσω όλα",
    "Μακάρι να ήμουν νεκρός",
    "Μακάρι να ήμουν νεκρή",
    "Θέλω να αφαιρέσω τη ζωή μου",
    "Βλάπτω τον εαυτό μου",
    "Αυτοτραυματίζομαι",
    "Σκέψεις αυτοκτονίας",
    "Πήρα υπερβολικής δόσης φάρμακα",
]

@pytest.mark.asyncio
@pytest.mark.parametrize("text,level", [
    ("Θέλω να πεθάνω", "high"),            # native review: extremely common, must hold
    ("Δεν αντέχω άλλο", "medium"),         # native review: extremely common, must hold
    ("Θέλω να πάρω τη ζωή μου πίσω", "none"),  # "get my life back" — dropped entry
])
async def test_the_native_review_rulings_hold(text, level):
    result = await safety_service.check_input(text, "u")
    assert result.level == level, f"{text!r} -> {result.level} ({result.trigger})"


NOT_INSIDE_WORDS = [
    "Epictetus says to rehearse the disappearance of everything you love. How?",
    "I retired last year and miss the work.",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", CRISIS_HIGH)
async def test_crisis_statements_reach_the_high_band(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "high", f"{text!r} -> {result.level} ({result.trigger})"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", CRISIS_MEDIUM)
async def test_distress_statements_reach_the_medium_band(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "medium", f"{text!r} -> {result.level} ({result.trigger})"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", GREEK_HIGH)
async def test_greek_crisis_statements_reach_the_high_band(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "high", f"{text!r} -> {result.level} ({result.trigger})"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", NOT_INSIDE_WORDS)
async def test_an_entry_never_matches_inside_a_longer_word(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "none", f"{text!r} -> {result.level} ({result.trigger or result.raw_flags})"
