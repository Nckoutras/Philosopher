"""MEM2-C-1 — the draft CALLBACK directive. Eval-only; it is NOT production copy.

WHAT THIS IS. Phase C (rulings locked 2026-10-05, IMPLEMENTATION_BACKLOG_v29.md
§ MEM2-C) lets a persona make at most ONE explicit callback per turn to something
the person wrote in an earlier conversation, when a deterministic gate offers a
candidate. Ruling #6 ("never announce that you remember") stays the default and
stays in the prompt: this block is rendered IMMEDIATELY AFTER it, as the one named
exception, and only on a turn whose gate offered a candidate.

WHY IT LIVES IN evals/ AND NOT prompts/. C-1 measures before anything speaks.
Nothing under services/ or prompts/ imports this module, and a test pins that.
If C-2 ships it, the production copy is a separate change with its own parity test
(the arm E precedent, tests/test_shipped_directive_is_arm_e.py).

THE COPY WAS APPROVED BEFORE IT WAS WRITTEN HERE (founder, 2026-10-05: STEP 1
approved with three edits). Any edit to DIRECTIVE is new copy and needs a new
approval and a new run; tests/test_callback_directive.py pins it byte-for-byte so
a reworded string cannot quietly change what a stored run measured.

The three approved edits, so a reader can see why the text is shaped as it is:
  1. The example phrasings use the given {when} — "You said {when} that…",
     "{When} you wrote that…" — so the model is never handed a timing word that
     can conflict with the bucket.
  2. The under-7-days bucket reads "a few days ago", not "earlier this week":
     calendar-week wording is a fidelity trap across a week boundary.
  3. "If they agree with it, that changes nothing: …" — Ruling 9, anti-laundering.

THE GREEK VARIANT (MEM2-C ruling C1-d; copy approved 2026-10-05, C-2 STEP 0(b),
with one edit: 56–120 days reads "πριν από ένα-δυο μήνες", not "κάνα δυο" —
register). Same prose, same cut points; only the {when} text and the two example
phrasings are Greek. C-1 rendered the ENGLISH bucket inside Greek conversations;
this variant is what a Greek conversation gets from C-2 on. DIRECTIVE_EL is
derived from DIRECTIVE by one checked substitution, so the prose cannot drift
between the two; tests pin both byte-for-byte.

{when} IS DETERMINISTIC AND COARSE. Five fixed buckets computed from the row's
age in whole days. Never an exact date: a wrong "last Tuesday" would be a fidelity
failure the model did not cause.
"""
from __future__ import annotations

import hashlib

# (inclusive upper bound in whole days, text). Approved 2026-10-05.
#   < 7      a few days ago
#   7–13     last week
#   14–55    a few weeks ago
#   56–120   a couple of months ago
#   > 120    some months ago
WHEN_BUCKETS: tuple[tuple[int | None, str], ...] = (
    (6, "a few days ago"),
    (13, "last week"),
    (55, "a few weeks ago"),
    (120, "a couple of months ago"),
    (None, "some months ago"),
)

# The same cut points, in Greek. Approved 2026-10-05 (C-2 STEP 0(b)).
WHEN_BUCKETS_EL: tuple[tuple[int | None, str], ...] = (
    (6, "πριν από λίγες μέρες"),
    (13, "την προηγούμενη εβδομάδα"),
    (55, "πριν από μερικές εβδομάδες"),
    (120, "πριν από ένα-δυο μήνες"),
    (None, "πριν από αρκετούς μήνες"),
)

HEADER_RULE = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# The approved copy. {when}, {When} and {original} are the only slots.
DIRECTIVE = (
    HEADER_RULE + "\n"
    "ONE THING THEY SAID BEFORE\n"
    + HEADER_RULE + "\n"
    "In an earlier conversation, {when}, this person wrote:\n"
    "\"{original}\"\n"
    "\n"
    "This is the one exception to the rule above. You may refer to it once in this "
    "reply, only if it sharpens what you are saying about what they brought today. "
    "If it does not clearly fit, leave it unused; not using it is always acceptable.\n"
    "\n"
    "If you use it:\n"
    "- One short clause, as something they said before: \"You said {when} that…\", "
    "\"{When} you wrote that…\". Never say where or to whom they said it, and never "
    "claim to remember more than these words.\n"
    "- Stay faithful to their words. Do not add to them, sharpen them, or make them "
    "more certain than they were. Never turn them into a pattern or a trait: no "
    "\"you always\", \"you never\", \"you tend to\", \"you are someone who\".\n"
    "- Treat it as what they said then, not as what is true of them now. They may "
    "see it differently today.\n"
    "- If they agree with it, that changes nothing: it is no more certain and no "
    "more general than it was.\n"
    "- Quote only words that appear above, exactly, in straight double quotation "
    "marks; otherwise paraphrase plainly. If their earlier words are in a different "
    "language from today's conversation, paraphrase in today's language instead of "
    "quoting.\n"
    "- Do not ask them to confirm it, and do not ask whether it is still true.\n"
    "- It counts toward your length. The reply stays within its usual length."
)

# The Greek variant: DIRECTIVE with only the example phrasings swapped.
_EXAMPLES_EN = "\"You said {when} that…\", \"{When} you wrote that…\""
_EXAMPLES_EL = "\"Είπες {when} ότι…\", \"{When} έγραψες ότι…\""
assert DIRECTIVE.count(_EXAMPLES_EN) == 1, "the EN example clause moved"
DIRECTIVE_EL = DIRECTIVE.replace(_EXAMPLES_EN, _EXAMPLES_EL)


def _variant(lang: str) -> tuple[str, tuple[tuple[int | None, str], ...]]:
    # Read at call time, not bound at import: a monkeypatched DIRECTIVE must move
    # the hash (test_hash_moves_with_the_copy).
    if lang == "en":
        return DIRECTIVE, WHEN_BUCKETS
    if lang == "el":
        return DIRECTIVE_EL, WHEN_BUCKETS_EL
    raise ValueError(f"no callback directive for language {lang!r}")


def when_bucket(days: int, lang: str = "en") -> str:
    """Whole days since the row was written -> the approved coarse phrase."""
    if days < 0:
        raise ValueError(f"a memory cannot be from the future: days={days}")
    for upper, text in _variant(lang)[1]:
        if upper is None or days <= upper:
            return text
    raise AssertionError("unreachable: the last bucket is open-ended")


def render_block(original: str, days: int, lang: str = "en") -> str:
    """The block exactly as the callback arm inserts it.

    `original` is the person's ORIGINAL message text (Ruling 2), never the stored
    row: fidelity is judged against what they typed, so it is what they are shown.
    `lang` is the conversation's language ("en" | "el"), which picks the variant.
    Plain str.replace, not .format(): the person's words may carry braces.
    """
    directive, _ = _variant(lang)
    when = when_bucket(days, lang)
    return (
        directive
        .replace("{When}", when[0].upper() + when[1:])
        .replace("{when}", when)
        .replace("{original}", original.strip())
    )


def directive_hash(lang: str = "en") -> str:
    """Recorded in the run manifest: a re-run after a copy edit is detectable.
    The EN payload is unchanged from C-1, so its hash still matches that run."""
    directive, buckets = _variant(lang)
    payload = directive + "\x00" + repr(buckets)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
