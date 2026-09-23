"""Arm B3 — arm B, plus the three B2 changes that were not about questions.

WHY ARM B IS THE BASE AND NOT B2. Two clean ChatGPT readings of the same eleven
B-vs-B2 pairs — reading 2 on the swapped file, reading 3 on the original, each in
a fresh chat — agreed on the same TEXT in 9 of 11 pairs with positions reversed.
That clears position bias and makes the preference real. Translated into key
sides, the picks were:

    arm B 16 votes, arm B2 6, out of 22.

The reader preferred the EARLIER arm, 73-27. An earlier record claimed "no arm
signal"; that came from a contaminated reading (both files pasted into one chat)
and does not survive. Founder ruling 2026-09-22: **the reader's preference
stands, arm B is the base.**

WHAT IS NOT IN B3, DELIBERATELY. B2's question rule — "in most replies the last
sentence is a statement" — is WITHDRAWN. It worked on the metric (Sonnet 88% ->
52% ending on a question) and the reader still preferred arm B. And of the six
B2 replies the reader did prefer, **all six end on a question**, which is the
opposite of what that rule was for.

Sealing questions and oracular phrasing are not to be attacked by directive
wording again. They become Listening-judge criteria (b) and (c). Arm B's own
opening/question sentence stays exactly as it was, including "never a closing
seal" — that sentence is part of the base, not part of the withdrawn rule.

THE THREE CHANGES, and each is carried over from B2 for a reason that is not
about questions:

1. REGISTER. "Plain, intelligent language" -> "Plain, precise language in your
   own register — never contemporary slang". The single universal-lexicon hit in
   440 completions was Jung saying "it's giving"; the looser phrasing plausibly
   invited it, and it did not recur under B2.

2. CHALLENGE, NOT SPECULATE. "You may challenge what they have said; do not
   speculate about what they have not." Arm B's concealment ban collides with
   two personas: Beauvoir's anchor_bad_faith_attentive REQUIRES her to examine
   "I had no choice" when the user says it, and Socrates' elenchus presses a
   stated claim. Under arm B, Beauvoir produced the persona-lexicon hit "you had
   no choice" — she said the line FOR the user instead of examining theirs.

3. A TARGET NUMBER. "Write between {lo} and {hi} words — about {target}",
   replacing arm B's range-only form.

THE REGISTER CHANGE LANDS IN FIRST_MESSAGE ONLY, and that is the ruling applied
strictly rather than loosely. It is defined as a REPLACEMENT for "Plain,
intelligent language" — and that string exists only in arm B's FIRST_MESSAGE.
STANDARD ends "Prefer clear speech over poetic or oracular phrasing" and DEEP
ends "no decorative profundity"; neither has anything to replace. B2 had ADDED
the register clause to all three, but B3's brief says "arm B text, verbatim,
with exactly these changes", and adding a sentence where none existed is not a
replacement.

Moot for this run — every sample in the suite is a first message — but it
matters for production, where the STANDARD and DEEP paths would then carry no
slang ban. Flagged for the founder rather than decided here.

"VERBATIM" IS CHECKABLE, NOT ASSERTED. tests/test_arm_b3.py derives this text
from arm_b's by applying exactly those three substitutions and asserts equality.
If someone edits a comma here, that test fails rather than the claim quietly
becoming untrue.
"""
from __future__ import annotations

from personas import PERSONA_REGISTRY
from services import reply_directive

from .arm_b import BANDS          # same ranges as B and B2
from .arm_b2 import TARGETS       # same midpoints, rounded to 5, ties up

# FIRST_MESSAGE IS NOW A FROZEN LITERAL, AND THAT IS A CHANGE — 2026-09-23.
#
# It used to be `reply_directive.FIRST_MESSAGE`, re-exported, on the reasoning that
# "the arm that was measured and the prompt that ships are the same object, so
# tests/test_harness_parity.py compares production against itself and cannot drift."
# That reasoning was sound for exactly as long as production never moved.
#
# Production has now moved: §8.2 shipped ARM E's first-message text
# (services/reply_directive.py, 2026-09-23). Re-exporting would have silently
# redefined what `--arm b3` means — every stored B3 run would have become
# unreproducible, and `--arm b3` would have generated arm E's replies under B3's
# name. Nothing would have failed loudly; the arm would simply have started lying.
#
# So the string is FROZEN as an immutable inline snapshot, byte-identical to what
# production carried when B3 was run and measured. This is convention C-01 —
# "a migration must not import app code; freeze the payload as an inline literal" —
# applied to an eval arm, and for the same reason: **runtime app code drifts, and a
# record of what was measured must reproduce forever.**
#
# STANDARD and DEEP are still re-exported, deliberately: arm E changed
# FIRST_MESSAGE only, so those two are still byte-identical to production and
# re-exporting keeps them honest if production ever changes them. If a future
# change touches STANDARD or DEEP, they must be frozen here too, for this reason.
FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said: name something meaningful you notice, and take a "
    "clear but proportionate position on it. You may offer an interpretation, but offer "
    "it tentatively and ground it in their own words; " + reply_directive.CONCEAL_BAN
    + " " + reply_directive.CHALLENGE
    + " Leave an easy opening to continue — usually one natural, answerable question, "
    "which may sit anywhere in the reply and is never a closing seal. Keep your own "
    "voice. " + reply_directive.REGISTER
    + "; no decorative aphorisms or fortune-cookie phrasing."
)
STANDARD = reply_directive.STANDARD
DEEP = reply_directive.DEEP
REGISTER_NEW = reply_directive.REGISTER
CHALLENGE = " " + reply_directive.CHALLENGE
CONCEAL_END = "they are hiding, avoiding, or failing to name something."
REGISTER_OLD = "Plain, intelligent language"

NOTICE_BAN = (
    "what I notice",
    "here's what I notice",
    "here is what I notice",
    "what strikes me",
)

ARM = "b3"


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    """Delegates to production. The harness cannot measure a different string."""
    return reply_directive.directive(
        PERSONA_REGISTRY[persona_slug], first_message=first_message, deep=deep)


def bands_note() -> str:
    return "; ".join(
        f"{s} std {BANDS[s]['standard'][0]}-{BANDS[s]['standard'][1]}"
        f"(~{TARGETS[s]['standard']}) deep {BANDS[s]['deep'][0]}-{BANDS[s]['deep'][1]}"
        f"(~{TARGETS[s]['deep']})"
        for s in BANDS
    )
