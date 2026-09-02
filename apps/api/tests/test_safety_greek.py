"""Greek and greeklish safety gates.

WHY THIS FILE EXISTS. Before this, `θέλω να αυτοκτονήσω` returned level="none".
Not "matched weakly" — none. should_suppress_persona was False, so a Greek
speaker in crisis received full persona immersion instead of the grounded crisis
mode spec §10.3 mandates. Greeklish (`den antexo allo`) passed too. The product's
first real audience was the one it could not hear.

The English tests in test_safety.py call themselves "the most important tests in
the codebase". These are the same tests in two more scripts.

FOUR THINGS ARE PINNED HERE, and they fail independently:

  1. Greek fixtures fire. Remove the normaliser and the accented ones die;
     remove the Greek lists and all of them die.
  2. Greeklish fixtures fire. Remove the greeklish lists and only these die —
     which is why they are separate cases and not mixed into the Greek ones.
  3. The normaliser itself collapses the four spellings of one word. This is
     asserted directly rather than only through the gates, because it is the
     piece that silently degrades: a normaliser that stopped stripping accents
     would still pass every unaccented fixture.
  4. Zero false positives against this repository's own English prose. The
     greeklish lists are latin substrings, and a careless entry like `den` would
     fire inside "sudden" and "garden". 719k characters of persona prompts and
     letter prompts is a real corpus, and the assertion is zero — not "few".

The asymmetry, restated because it decides every close call in the lexicon: a
false positive shows a caring message to someone safe; a false negative leaves
someone in crisis with Nietzsche. Fixtures below therefore include phrasings a
cautious reviewer might call borderline, and they are expected to fire.
"""
import pathlib
import unicodedata

import pytest

from services.safety_service import SafetyService, _normalize
from services.safety_lexicons import (
    ALL_BANDS,
    GREEK_BANDS,
    GREEKLISH_BANDS,
    LOW_SIGNALS_EN,
)


@pytest.fixture
def safety():
    return SafetyService()


# ── 1. Greek script ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "θέλω να αυτοκτονήσω",                 # accented, as a Greek keyboard types it
    "θελω να αυτοκτονησω",                 # unaccented, as people actually type
    "ΘΕΛΩ ΝΑ ΑΥΤΟΚΤΟΝΗΣΩ",                 # caps
    "Θέλω να πεθάνω",                      # sentence case + accents
    "δεν θέλω να ζω άλλο",                 # embedded in a longer sentence
    "σκέφτομαι να αυτοκτονήσω τελευταία",  # with trailing words
    "καλύτερα νεκρός",                     # final sigma after lowercasing
    "μακάρι να πέθαινα",
    "δεν αξίζει να ζω",
    "χαράζομαι όταν είμαι μόνος",          # the common Greek term for self-harm
    "θέλω να δώσω τέλος στη ζωή μου",
    "είμαι έτοιμος να πεθάνω",
])
async def test_greek_high_risk_suppresses_persona(safety, text):
    result = await safety.check_input(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True
    assert result.category == "self_harm"


@pytest.mark.parametrize("text", [
    "δεν αντέχω άλλο",
    "δεν έχει νόημα τίποτα",
    "τίποτα δεν έχει νόημα πια",
    "θέλω να εξαφανιστώ",
    "κουράστηκα να ζω",
    "όλοι θα ήταν καλύτερα χωρίς εμένα",
    "νιώθω αόρατος",
])
async def test_greek_medium_risk_suppresses_persona(safety, text):
    result = await safety.check_input(text)
    assert result.level == "medium", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


@pytest.mark.parametrize("text", [
    "είμαι κουρασμένος",
    "νιώθω βάρος για όλους",
    "κανείς δεν νοιάζεται",
    "είμαι μόνη",
])
async def test_greek_low_signals_log_without_suppressing(safety, text):
    result = await safety.check_input(text)
    assert result.level == "low", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is False
    assert result.should_log is True


# ── 2. Greeklish ──────────────────────────────────────────────────────────────
# Separate cases from the Greek ones on purpose: deleting the greeklish lists
# must fail HERE and nowhere else, so the mutation is diagnostic.

@pytest.mark.parametrize("text", [
    "thelo na pethano",
    "thelw na pethanw",
    "8elw na pe8anw",                  # 8 for theta — standard phone greeklish
    "den thelo na zo allo",
    "kalytera nekros",
    "makari na pethaina",
    "na dwsw telos sti zoi mou",
    "xarazomai otan eimai monos",
])
async def test_greeklish_high_risk_suppresses_persona(safety, text):
    result = await safety.check_input(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


@pytest.mark.parametrize("text", [
    "den antexo allo",
    "den antexw allo re file",
    "den exei noima tipota",
    "thelo na eksafanisto",
    "kourastika na zo",
])
async def test_greeklish_medium_risk_suppresses_persona(safety, text):
    result = await safety.check_input(text)
    assert result.level == "medium", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


# ── 3. Output gate ────────────────────────────────────────────────────────────
# A persona answers in the language it was addressed in, so Greek method-detail
# would have walked straight through an English-only output list.

@pytest.mark.parametrize("text", [
    "ο πιο ανώδυνος τρόπος είναι",
    "μια θανατηφόρα δόση θα ήταν",
    "ο ευκολότερος τρόπος να πεθάνεις",
    "anodynos tropos einai",
])
async def test_greek_output_harm_is_caught(safety, text):
    result = await safety.check_output(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.category == "output_harm"


# ── 4. Benign text must not fire ──────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "σήμερα πήγα βόλτα στη θάλασσα",
    "μου αρέσει πολύ αυτό το βιβλίο",
    "σκέφτομαι να αλλάξω δουλειά",
    "simera pigа volta sti thalassa",
    "today was a good day at work",
])
async def test_benign_text_does_not_fire(safety, text):
    result = await safety.check_input(text)
    assert result.level == "none", f"{text!r} falsely fired: {result.trigger or result.raw_flags}"


# ── 5. Bilingual input ────────────────────────────────────────────────────────

async def test_a_bilingual_sentence_is_checked_against_every_lexicon(safety):
    """Real users switch scripts mid-sentence. A design that routed by detected
    language would check one half and drop the other — which is exactly why
    dominant_language does not gate the checks."""
    result = await safety.check_input("I'm fine really, but δεν αντέχω άλλο")
    assert result.level == "medium"
    assert result.should_suppress_persona is True


# ── 6. The normaliser itself ──────────────────────────────────────────────────

def test_the_normaliser_collapses_every_spelling_of_one_word():
    """Asserted directly, not only through the gates. A normaliser that stopped
    stripping accents would still pass every unaccented fixture above, so the
    gates alone cannot detect that regression."""
    spellings = ["Θέλω", "θέλω", "θελω", "ΘΕΛΩ"]
    normalised = {_normalize(s) for s in spellings}
    assert len(normalised) == 1, normalised
    assert normalised == {"θελω"}


def test_the_normaliser_folds_final_sigma():
    # 'ΟΔΟΣ'.lower() yields a FINAL sigma; a lexicon entry written with a medial
    # sigma would never match it. casefold folds them together.
    assert _normalize("ΝΕΚΡΟΣ") == _normalize("νεκρός") == _normalize("νεκρος")


def test_the_normaliser_leaves_english_untouched():
    for phrase in LOW_SIGNALS_EN + ["don't want to be alive", "can't keep living"]:
        assert _normalize(phrase) == phrase, phrase


def test_every_lexicon_entry_is_prenormalised():
    """The import-time assertion, restated as a test so the failure is readable.

    An entry that is not equal to its own normalised form can never match, and
    that failure is invisible at runtime — the gate simply does not fire.
    """
    offenders = [
        f"{band}: {entry!r}"
        for band, entries in ALL_BANDS.items()
        for entry in entries
        if entry != _normalize(entry)
    ]
    assert offenders == [], offenders


def test_no_band_contains_duplicates():
    """Reviewable content: a duplicate is harmless to the matcher and confusing
    to the Greek speaker reading the list line by line. Caught here because the
    first draft of the greeklish list had one."""
    from collections import Counter
    for band, entries in ALL_BANDS.items():
        dupes = [e for e, n in Counter(entries).items() if n > 1]
        assert dupes == [], f"{band}: {dupes}"


def test_greek_entries_contain_no_combining_marks():
    """A stricter statement of the same rule, aimed at the specific mistake:
    typing an accented Greek phrase into the lexicon."""
    for band, entries in GREEK_BANDS.items():
        for entry in entries:
            decomposed = unicodedata.normalize("NFD", entry)
            assert not any(unicodedata.combining(c) for c in decomposed), f"{band}: {entry!r}"


# ── 7. False positives against real English prose ─────────────────────────────

def test_no_greek_or_greeklish_entry_fires_on_this_repos_english_prose():
    """The greeklish lists are latin substrings matched without word boundaries,
    so a careless entry (`den`) would fire inside "sudden" and "garden".

    The corpus is this repository's own persona system prompts, letter prompts
    and service prompts — roughly 700k characters of natural English written
    without any thought for this test. The two self-documenting safety modules
    are excluded because their docstrings quote the phrases on purpose.

    The assertion is ZERO, not "few". A single hit here means a lexicon entry is
    firing on ordinary English, and the entry must be lengthened rather than the
    threshold loosened.
    """
    self_documenting = {"safety_lexicons.py", "safety_service.py"}
    root = pathlib.Path(__file__).resolve().parents[1]

    corpus = []
    for folder in ("personas", "services", "workers", "prompts"):
        for path in (root / folder).rglob("*"):
            if (
                path.suffix in (".py", ".jinja2")
                and "__pycache__" not in str(path)
                and path.name not in self_documenting
            ):
                corpus.append((path.name, _normalize(path.read_text(encoding="utf-8"))))

    assert len(corpus) > 30, "corpus collapsed — the scan would pass vacuously"

    hits = [
        f"{band}: {entry!r} fires inside {name}"
        for band, entries in list(GREEK_BANDS.items()) + list(GREEKLISH_BANDS.items())
        for entry in entries
        for name, text in corpus
        if entry in text
    ]
    assert hits == [], hits
