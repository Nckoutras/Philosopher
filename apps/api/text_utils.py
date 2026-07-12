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
