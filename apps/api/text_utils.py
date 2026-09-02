"""Small, dependency-free text helpers shared across layers (schemas, renderers).

Kept at the API root with zero app imports so both the DTO layer (schemas) and
the image renderer can import it without creating an import cycle.
"""


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
