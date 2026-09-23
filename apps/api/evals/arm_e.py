"""Arm E — shape clauses 1 and 3 removed, the HEDGE kept. The last §8.2 arm.

WHY THIS ARM EXISTS. Arm D removed all three SHAPE clauses and produced a split
result: the three personas the directive was erasing became nameable (named 1 time
in 154 -> 10, p=0.0104; every column non-empty for the first time), while (a)
over-interpretation rose 1.68 -> 2.01 per 100 words.

Of the three clauses D removed, **exactly one bears on (a)**:

    "You may offer an interpretation, but offer it tentatively and ground it in
     their own words"

That is the hedging instruction — it constrains HOW an interpretation is offered.
The other two build the SHAPE and have nothing to do with over-interpretation:

    1. ": name something meaningful you notice, and take a clear but proportionate
       position on it"                                            (beats 1-2)
    3. "Leave an easy opening to continue — usually one natural, answerable
       question, which may sit anywhere in the reply and"          (beat 3)

Arm D's Socrates marginal fell 32% -> 19% of all guesses, which traces to clause 3
specifically: it is the clause that mandates an open question, and Socrates is the
attractor built out of question-asking.

**THE HYPOTHESIS: the distinctiveness gain is carried by 1 and 3, and the (a) cost
by 2.** If so, this arm keeps the gain and gives back the cost. Arm D cannot
separate them — it removed all three at once.

ONE FORCED REWRITE, not two. Arm D needed CONCEAL_BAN capitalised because deleting
clause 2 removed the semicolon it follows. **Arm E keeps clause 2 verbatim,
including its trailing semicolon, so CONCEAL_BAN is byte-identical to production
here.** The only non-verbatim text is the closing-seal ban, for the same reason as
in arm D: criterion (b)'s constraint lives INSIDE clause 3's question prescription
("…answerable question … and is never a closing seal"), so deleting the
prescription would delete the quality clause with it. It is restated to stand alone
without mandating a question. See `SEAL_BAN`, imported from arm_d so the two arms
cannot drift apart on the one string they share.

DECISION RULE, FIXED BEFORE THE RUN (founder, 2026-09-23):

    the three dead personas named at a rate >= arm D's
      AND (a) density within 10% of control
        -> ship the arm E directive to production, separate PR, parity, P-04 smoke
    otherwise
        -> ship nothing; §8.2 closes with the finding recorded

Control is the same spliced set arm D used (63 B3 + 14 voicefix_v2), and its
distinctiveness and density judgements are already stored — this arm re-judges
only itself.

NOT TOUCHED: `services/reply_directive.py`. Harness-local string, as arm D.
ONLY FIRST_MESSAGE DIFFERS; STANDARD and DEEP are re-exported from production.
"""
from __future__ import annotations

from personas import PERSONA_REGISTRY
from services import reply_directive

from .arm_b import BANDS          # same ranges as B, B2, B3, D
from .arm_b2 import TARGETS       # same midpoints
from .arm_d import SEAL_BAN       # the one shared rewrite, imported not copied

STANDARD = reply_directive.STANDARD
DEEP = reply_directive.DEEP
REGISTER = reply_directive.REGISTER
CHALLENGE = reply_directive.CHALLENGE
CONCEAL_BAN = reply_directive.CONCEAL_BAN          # byte-identical, unlike arm D

# KEPT VERBATIM — this is the clause arm E exists to put back. Sourced by slicing
# production's own string rather than retyping it, so a reworded production
# directive cannot leave a stale copy here pretending to be "verbatim".
HEDGE = (
    "You may offer an interpretation, but offer it tentatively and ground it in "
    "their own words; "
)
assert HEDGE in reply_directive.FIRST_MESSAGE, (
    "arm E's HEDGE is no longer a substring of the production directive — it was "
    "reworded. This arm's whole claim is that the clause is kept verbatim."
)

# The two deletions, as data, so a test can assert neither survives.
REMOVED_SHAPE_CLAUSES = (
    ": name something meaningful you notice, and take a clear but proportionate "
    "position on it",
    "Leave an easy opening to continue — usually one natural, answerable question, "
    "which may sit anywhere in the reply and",
)

FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said. " + HEDGE + CONCEAL_BAN + " " + CHALLENGE
    + " " + SEAL_BAN + " Keep your own voice. " + REGISTER
    + "; no decorative aphorisms or fortune-cookie phrasing."
)

ARM = "e"


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    """Production's band logic, this arm's first-message text. See arm_d.directive —
    deep and non-first-message delegate to production untouched."""
    persona = PERSONA_REGISTRY[persona_slug]
    if deep or not first_message:
        return reply_directive.directive(
            persona, first_message=first_message, deep=deep)
    spec = getattr(persona, "response_length_words", None)
    if spec is None:
        return ""
    try:
        lo, hi = spec.standard_reply_words
        lo, hi = int(lo), int(hi)
    except (TypeError, ValueError):
        return ""
    return FIRST_MESSAGE.format(
        lo=lo, hi=hi, target=reply_directive._target(lo, hi))


def bands_note() -> str:
    return "; ".join(
        f"{s} std {BANDS[s]['standard'][0]}-{BANDS[s]['standard'][1]}"
        f"(~{TARGETS[s]['standard']}) deep {BANDS[s]['deep'][0]}-{BANDS[s]['deep'][1]}"
        f"(~{TARGETS[s]['deep']})"
        for s in BANDS
    )
