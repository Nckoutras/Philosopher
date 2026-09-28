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


# 2026-09-25 (founder ruling): a continuation INSIDE the core. Each returned NONE
# before; a whole-phrase list only sees the forms it holds.
CONTINUATION_HIGH = [
    "Δεν θέλω πλέον να ζω",
    "Δε θέλω πλέον να ζω",
    "Δεν θέλω άλλο να ζω",
    "Δε θέλω άλλο να ζω",
    "Κουράστηκα πια να ζω",
    "Κουράστηκα πλέον να ζω",
    "Βαρέθηκα πια να ζω",
    "Βαρέθηκα πλέον να ζω",
    "den thelo pia na zo",
    "den thelw pia na zw",
    "den thelo pleon na zo",
    "den thelw pleon na zw",
    "den thelo allo na zo",
    "den thelw allo na zw",
    "kourastika pia na zo",
    "kourastika pia na zw",
    "vare8ika pia na zo",
    "barethika pia na zo",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", CONTINUATION_HIGH)
async def test_a_continuation_inside_the_core_reaches_the_high_band(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "high", f"{text!r} -> {result.level} ({result.trigger})"


@pytest.mark.asyncio
async def test_a_locative_after_the_core_is_still_high_today():
    """NOT A BUG. Today the lexicon has no notion of a locative: "…to live in this
    city" is still the phrase "I don't want to live", so it is HIGH. SAFETY-002
    will DEMOTE it to Tier B (default HIGH, judged) — never to none. Until the
    judge ships, there is no demotion, and HIGH is the correct answer."""
    result = await safety_service.check_input("Δεν θέλω πια να ζω σε αυτή την πόλη", "u")
    assert result.level == "high", f"-> {result.level} ({result.trigger})"


# 2026-09-28 (SAFETY-002 B5, founder ruling): the continuation sweep over EVERY
# '<verb> να ζω' / '<verb> να υπαρχω' core. Found by the second reader: "Δεν αντέχω
# πια να ζω." and "Δεν θέλω πια να υπάρχω." landed nowhere. Each form below returned
# NONE before (the άλλο forms of αντέχω only MEDIUM, via "δεν αντεχω αλλο").
CONTINUATION_SWEEP_HIGH = [
    # δεν αντεχω να ζω
    'Δεν αντέχω πια να ζω',
    'Δεν αντέχω πλέον να ζω',
    'Δεν αντέχω άλλο να ζω',
    'Δε αντέχω πια να ζω',
    'Δε αντέχω πλέον να ζω',
    'Δε αντέχω άλλο να ζω',
    # δεν αξιζει να ζω
    'Δεν αξίζει πια να ζω',
    'Δεν αξίζει πλέον να ζω',
    'Δεν αξίζει άλλο να ζω',
    'Δε αξίζει πια να ζω',
    'Δε αξίζει πλέον να ζω',
    'Δε αξίζει άλλο να ζω',
    # δεν θελω να υπαρχω
    'Δεν θέλω πια να υπάρχω',
    'Δεν θέλω πλέον να υπάρχω',
    'Δεν θέλω άλλο να υπάρχω',
    'Δε θέλω πια να υπάρχω',
    'Δε θέλω πλέον να υπάρχω',
    'Δε θέλω άλλο να υπάρχω',
    # κουραστηκα να ζω
    'Κουράστηκα άλλο να ζω',
    # βαρεθηκα να ζω
    'Βαρέθηκα άλλο να ζω',
    # den thelo na zo
    'de thelo pia na zo',
    'de thelo pleon na zo',
    'de thelo allo na zo',
    # den thelw na zw
    'de thelw pia na zw',
    'de thelw pleon na zw',
    'de thelw allo na zw',
    # den antexo na zo
    'den antexo pia na zo',
    'den antexo pleon na zo',
    'den antexo allo na zo',
    'de antexo pia na zo',
    'de antexo pleon na zo',
    'de antexo allo na zo',
    # den antexw na zw
    'den antexw pia na zw',
    'den antexw pleon na zw',
    'den antexw allo na zw',
    'de antexw pia na zw',
    'de antexw pleon na zw',
    'de antexw allo na zw',
    # den axizei na zo
    'den axizei pia na zo',
    'den axizei pleon na zo',
    'den axizei allo na zo',
    'de axizei pia na zo',
    'de axizei pleon na zo',
    'de axizei allo na zo',
    # den axizei na zw
    'den axizei pia na zw',
    'den axizei pleon na zw',
    'den axizei allo na zw',
    'de axizei pia na zw',
    'de axizei pleon na zw',
    'de axizei allo na zw',
    # kourastika na zo
    'kourastika pleon na zo',
    'kourastika allo na zo',
    # kourastika na zw
    'kourastika pleon na zw',
    'kourastika allo na zw',
    # vare8ika na zo
    'vare8ika pleon na zo',
    'vare8ika allo na zo',
    # barethika na zo
    'barethika pleon na zo',
    'barethika allo na zo',
]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", CONTINUATION_SWEEP_HIGH)
async def test_the_continuation_sweep_reaches_the_high_band(text):
    result = await safety_service.check_input(text, "u")
    assert result.level == "high", f"{text!r} -> {result.level} ({result.trigger})"

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
