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

from .arm_b import BANDS          # same ranges as B and B2
from .arm_b2 import TARGETS       # same midpoints, rounded to 5, ties up

# The three substitutions, as data, so the test and the text cannot disagree.
REGISTER_OLD = "Plain, intelligent language"
REGISTER_NEW = "Plain, precise language in your own register — never contemporary slang"
CHALLENGE = (
    " You may challenge what they have said; do not speculate about what they have not."
)
CONCEAL_END = "they are hiding, avoiding, or failing to name something."

FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said: name something meaningful you notice, and take a "
    "clear but proportionate position on it. You may offer an interpretation, but offer "
    "it tentatively and ground it in their own words; never tell them, directly or by "
    "implication, that they are hiding, avoiding, or failing to name something. You may "
    "challenge what they have said; do not speculate about what they have not. Leave an "
    "easy opening to continue — usually one natural, answerable question, which may sit "
    "anywhere in the reply and is never a closing seal. Keep your own voice. Plain, "
    "precise language in your own register — never contemporary slang; no decorative "
    "aphorisms or fortune-cookie phrasing."
)

STANDARD = (
    "STANDARD\n"
    "Write between {lo} and {hi} words — about {target}. Move the conversation forward "
    "rather than merely reflecting it back. Say what you genuinely notice in their words "
    "and take a position where the evidence supports one. You may offer an "
    "interpretation, but offer it tentatively and ground it in their own words; never "
    "tell them, directly or by implication, that they are hiding, avoiding, or failing "
    "to name something. You may challenge what they have said; do not speculate about "
    "what they have not. Leave an easy opening to continue — usually one natural, "
    "answerable question, which may sit anywhere in the reply and is never a closing "
    "seal. Keep your own voice. Prefer clear speech over poetic or oracular phrasing."
)

DEEP = (
    "DEEP\n"
    "Write between {deep_lo} and {deep_hi} words — about {deep_target}. Go materially "
    "deeper: connect the person's own details, develop an interpretation, or move toward "
    "a conclusion their words reasonably support — and make clear which parts are "
    "evident and which are your reading. Never tell them, directly or by implication, "
    "that they are hiding, avoiding, or failing to name something. You may challenge "
    "what they have said; do not speculate about what they have not. Leave room to "
    "respond — a natural, concrete question or an inviting statement, never a closing "
    "seal. Keep your own voice; no decorative profundity."
)

# ── the prompt-level ban ─────────────────────────────────────────────────────
#
# These go into every persona's `forbidden_phrases`, which system_base.jinja2
# renders as "DO NOT USE: ...". PROMPT LEVEL, not the post-check: nothing in
# postprocessing_service is touched, so the phrases are discouraged, never
# stripped or regenerated.
#
# WHY A BAN AT ALL. The instruction route has been tried twice and moved
# nothing. B2 struck the sample wordings from the stance sentence precisely so
# "What I notice" would stop being example one, and the rate did not budge:
#
#     baseline  Sonnet 3.6%   Haiku 4.5%
#     arm B     Sonnet 12.7%  Haiku 6.4%
#     arm B2    Sonnet 12.7%  Haiku 6.4%   <- identical, to the reply
#
# The formula is the model's default for "take a stance", not an artefact of
# being named. So B3 names it as forbidden instead.
#
# THE RISK THIS RUN MEASURES: a banned tic is usually replaced, not dropped.
# stance_variety is the instrument, and the decision rule stops the ship if a
# single replacement family exceeds 30% of stance hits.
NOTICE_BAN = (
    "what I notice",
    "here's what I notice",
    "here is what I notice",
    "what strikes me",
)

ARM = "b3"


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    lo, hi = BANDS[persona_slug]["deep" if deep else "standard"]
    t = TARGETS[persona_slug]["deep" if deep else "standard"]
    if deep:
        return DEEP.format(deep_lo=lo, deep_hi=hi, deep_target=t)
    return (FIRST_MESSAGE if first_message else STANDARD).format(lo=lo, hi=hi, target=t)


def bands_note() -> str:
    return "; ".join(
        f"{s} std {BANDS[s]['standard'][0]}-{BANDS[s]['standard'][1]}"
        f"(~{TARGETS[s]['standard']}) deep {BANDS[s]['deep'][0]}-{BANDS[s]['deep'][1]}"
        f"(~{TARGETS[s]['deep']})"
        for s in BANDS
    )
