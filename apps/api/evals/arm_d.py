"""Arm D — the three SHAPE clauses removed from the first-message directive.

THE QUESTION THIS ARM EXISTS TO SETTLE. §8.2's distinctiveness run found one reply
shape across all eleven personas: acknowledge -> interpret -> open question. TD-95
showed that shape is not emergent — it is WRITTEN DOWN, in
`reply_directive.FIRST_MESSAGE`, shared verbatim by all eleven, and appended LAST
(94% of the prompt, against the persona's own voice block at 7%).

Persona-level repair has been tried and has answered its own question. Marcus
received the strongest available persona change — rewritten FIRST MOVE, removed
contradiction, explicit licence — and went 0/10 -> 0/10, moving from one attractor
(Epictetus) to another (Beauvoir) without gaining a diagonal. Musashi's move had to
be WEAKENED to fit the directive and still moved 0/10 -> 2/10. Founder ruling
2026-09-23: stop persona-level voice fixes, run one arm against the directive.

WHAT IS REMOVED — the three SHAPE clauses, and nothing else:

  1. ": name something meaningful you notice, and take a clear but proportionate
     position on it"                                              (beats 1-2)
  2. "You may offer an interpretation, but offer it tentatively and ground it in
     their own words; "                                           (beat 2)
  3. "Leave an easy opening to continue — usually one natural, answerable question,
     which may sit anywhere in the reply and"                     (beat 3)

WHAT IS KEPT — all five quality clauses, which map one-to-one onto the listening
judge's criteria, plus the length sentence and the register clause:

  "Respond specifically to what this person has actually said"    -> (d)
  CONCEAL_BAN                                                     -> (a)
  CHALLENGE                                                       -> (e)
  "never a closing seal"                                          -> (b)
  "no decorative aphorisms or fortune-cookie phrasing"            -> (c)
  REGISTER, and the {lo}/{hi}/{target} length sentence            -> unchanged

TWO CLAUSES ARE NOT BYTE-VERBATIM, AND BOTH REWRITES ARE FORCED BY THE DELETIONS
RATHER THAN CHOSEN. Stating them because "kept verbatim" was the instruction and
these two are the exceptions:

  * CONCEAL_BAN begins lowercase ("never tell them…") because in production it
    follows a semicolon. Clause 2 carried that semicolon. With clause 2 gone the
    ban starts a sentence, so its "n" is capitalised. One character.

  * The closing-seal ban lives INSIDE clause 3 — "usually one natural, answerable
    question … and is never a closing seal". Deleting the prescription to ask a
    question would delete the ban on sealing with it, which is criterion (b) and a
    quality clause. It is therefore restated so it can stand alone WITHOUT
    mandating a question: "If you end on a question, it must open rather than
    close — never a closing seal." The constraint is identical; what is dropped is
    the instruction that there BE a question.

If the arm reads as "shape removed" on the distinctiveness judge while density on
(a)/(c) does not worsen, the shape clauses come out for everyone and no per-persona
exemption mechanism is needed (TD-95's option). If distinctiveness is flat, the
directive is exonerated and §8.2 closes.

NOT TOUCHED: `services/reply_directive.py`. This arm is a harness-local string. The
production directive is unchanged and ships as it did.

ONLY FIRST_MESSAGE DIFFERS. STANDARD and DEEP are re-exported from production
unchanged — every §8.2 sample is a first message, so they are not exercised by this
run, and re-exporting rather than copying keeps them honest if that ever changes.
"""
from __future__ import annotations

from personas import PERSONA_REGISTRY
from services import reply_directive

from .arm_b import BANDS          # same ranges as B, B2 and B3
from .arm_b2 import TARGETS       # same midpoints

# Re-exported unchanged; see the docstring's last paragraph.
STANDARD = reply_directive.STANDARD
DEEP = reply_directive.DEEP
REGISTER = reply_directive.REGISTER
CHALLENGE = reply_directive.CHALLENGE

# The two forced rewrites, as data, so a test can assert what changed rather than
# trusting this comment. CONCEAL_BAN_CAPPED must differ from production's only in
# its first character.
CONCEAL_BAN_CAPPED = (
    reply_directive.CONCEAL_BAN[0].upper() + reply_directive.CONCEAL_BAN[1:]
)
SEAL_BAN = (
    "If you end on a question, it must open rather than close — never a closing seal."
)

# The three deletions, as data, so `tests` can assert none of them survives.
REMOVED_SHAPE_CLAUSES = (
    ": name something meaningful you notice, and take a clear but proportionate "
    "position on it",
    "You may offer an interpretation, but offer it tentatively and ground it in "
    "their own words; ",
    "Leave an easy opening to continue — usually one natural, answerable question, "
    "which may sit anywhere in the reply and",
)

FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said. " + CONCEAL_BAN_CAPPED + " " + CHALLENGE
    + " " + SEAL_BAN + " Keep your own voice. " + REGISTER
    + "; no decorative aphorisms or fortune-cookie phrasing."
)

ARM = "d"


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    """Production's band logic, this arm's first-message text.

    The bands are READ FROM THE PERSONA, exactly as `reply_directive.directive`
    reads them — not duplicated here. An arm that changed the wording AND the
    numbers would confound the two, and the numbers are not what is being tested.

    deep, or a non-first message, delegates to production untouched: those paths
    are not part of this arm and must not silently become part of it.
    """
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
