"""Small, dependency-free text helpers shared across layers (schemas, renderers).

Kept at the API root with zero app imports so both the DTO layer (schemas) and
the image renderer can import it without creating an import cycle.
"""
import re
import unicodedata


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Normalise, and report where every output character came from.

    Returns (normalised_text, index_map) where index_map[i] is the index in
    `text` of the character that produced normalised_text[i].

    THE MAP IS WHY THIS EXISTS. Normalisation changes length — NFD splits one
    accented character into two and the combining mark is then dropped, and
    casefold can turn one character into two ('ß' -> 'ss'). So a span found in
    the normalised text cannot be applied to the original by arithmetic. Any
    caller that MATCHES on normalised text but must EDIT the original needs
    this map; see postprocessing_service._deterministic_strip, which would
    otherwise have to return de-accented text to the reader.

    Per-character rather than whole-string so the mapping is exact. A test
    pins that it agrees with normalize() on the whole safety lexicon.
    """
    out: list[str] = []
    index_map: list[int] = []
    for i, ch in enumerate(text):
        for c in unicodedata.normalize("NFD", ch.casefold()):
            if unicodedata.combining(c):
                continue
            out.append("σ" if c == "ς" else c)
            index_map.append(i)
    return "".join(out), index_map


def normalize(text: str) -> str:
    """Fold away the differences a reader does not see.

    casefold() rather than lower(): it is the aggressive form, and it already
    maps final sigma to sigma. NFD then splits accented characters into base +
    combining mark so the marks can be dropped — this is what makes `θέλω` and
    `θελω` the same string. The explicit ς→σ is redundant after casefold and
    kept deliberately: it states the intent where a reader looks for it, and it
    survives a future change to casefold's behaviour.

    Latin text is unaffected in practice — the English lexicon entries are all
    equal to their own normalised form, which safety_service's import-time
    assertion proves.

    Defined in terms of normalize_with_map so the two can never disagree: one
    algorithm, two views of its output.
    """
    return normalize_with_map(text)[0]


def shorten_source(s: str, cap: int = 35) -> str:
    """Shorten a source locator for compact display (carousel card, share PNG
    attribution). Deterministic, word-boundary aware, capped at `cap` chars.

    Returns the input unchanged when it already fits; otherwise trims to the
    last whole word within the cap, strips trailing separators, and appends an
    ellipsis. The full `source_locator` is unchanged — this is display-only.
    """
    s = (s or "").strip()
    if len(s) <= cap:
        return s
    cut = s[:cap]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;") + "…"


def dominant_language(texts: list[str]) -> str:
    """Return 'Greek' or 'English' by counting Greek vs Latin letters. Ties -> 'English'.

    Promoted here from workers/arq_worker.py, where it was written after the
    2026-08-24 incident: a weekly letter came back with its body in English and
    two fields in Greek, because no prompt stated a language and the model picked
    one per FIELD from mixed-language input.

    Characters, not words: a week's messages mix languages inside single
    sentences, and a word-splitter has to decide what a word is in two scripts.
    Codepoint ranges follow the _renderable_original precedent in
    services/image_service.py — no new dependency.

    KNOWN LIMIT, and it matters for safety routing: greeklish (Greek typed in
    latin characters, "den antexo allo") counts as Latin and returns 'English'.
    That is the accepted behaviour — a greeklish typist is reading an English UI
    already — but it means this must never be used to decide WHETHER to run a
    safety check, only which language to answer in. The gates themselves run
    every lexicon against every message regardless of what this returns.
    """
    greek = latin = 0
    for t in texts:
        for ch in t:
            if 'Ͱ' <= ch <= 'Ͽ' or 'ἀ' <= ch <= '῿':
                greek += 1
            elif ch.isascii() and ch.isalpha():
                latin += 1
    return "Greek" if greek > latin else "English"


# ── Output-language checking ──────────────────────────────────────────────────
# Promoted here from services/council_service.py (#626), where it was written for
# the display-brief guard. Same reason dominant_language was promoted out of
# arq_worker: four call sites should share ONE detector rather than grow four
# subtly different ones.
#
# WHY dominant_language IS NOT ENOUGH ON ITS OWN. It counts Greek codepoints
# against Latin ones — it answers "which script", and calls every Latin-script
# language English. The first defect it had to catch was an INDONESIAN summary
# for an English conversation, and dominant_language returns 'English' for that
# text: a check built on it alone compares 'English' to 'English', passes, and
# ships the exact string it exists to stop. So Latin-script output must also look
# like ENGLISH, by function-word ratio — crude, but it needs no dependency (there
# is no language detector in requirements) and it separates enormously on real
# data.
#
# CALIBRATED 2026-09-10 on two verbatim production strings, twelve in-register
# English ones and five Greek; re-verified unchanged on promotion:
#
#   both real Indonesian strings     0.000        (one contains "scroll")
#   twelve English strings           0.536-0.733
#   Spanish/French/German/Italian/PT 0.000-0.100
#
# 0.30 is clear of both sides by >=0.20. tests/test_council_display_brief.py
# holds the sample-by-sample calibration and a separation test.
EN_FUNCTION_WORDS = frozenset("""
i im ive id ill me my myself we our us you your he she it its they them their
a an the this that these those there here
is am are was were be been being do does did doing have has had having
can cant could will wont would should shall may might must
and or but if then than because so as while whether though although
of to in on at by for with from about into over under
between through without within against around after before
not no nor only just even still yet more most less
what which who whom whose when where why how
all any both each few some such own same too very
one other another something nothing anything everything
keep keeps feel feels know knows think thinks want wants
""".split())

EN_FUNCTION_WORD_FLOOR = 0.30


def english_function_word_ratio(text: str) -> float:
    """Share of tokens that are common English function words. 0.0 when empty."""
    tokens = [t.strip("'") for t in re.findall(r"[a-z']+", text.lower())]
    tokens = [t for t in tokens if t]
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t.replace("'", "") in EN_FUNCTION_WORDS) / len(tokens)


def language_matches(text: str, expected: str) -> bool:
    """Does `text` read as `expected` ('Greek' | 'English')?

    Greek needs only the script test — no other language the product serves is
    written in Greek script, so a Greek-script answer to a Greek input is right by
    construction. English needs both tests, for the reason above.
    """
    if dominant_language([text]) != expected:
        return False
    if expected == "English":
        return english_function_word_ratio(text) >= EN_FUNCTION_WORD_FLOOR
    return True


def language_directive(language: str) -> str:
    """The one sentence every generator appends to say which language to write in.

    APPENDED, never .format()ed. Three of the four prompts that need this carry
    literal braces (JSON shapes in MEMORY_EXTRACTION_PROMPT and
    SELF_PORTRAIT_SUMMARY_PROMPT), so a format call would raise KeyError on the
    JSON rather than fill anything. One injection style for all of them.
    """
    return (
        f"\n\nLANGUAGE: Write in {language}. Never write in any other language, and "
        f"never translate. {language} governs the whole output even if the input "
        f"mixes languages."
    )
