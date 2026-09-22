"""Arm B2 — arm B, with the four things arm B got wrong or left flat.

ARM B'S RESULT, WHICH IS WHAT THIS ARM IS BUILT FROM. Measured over 220
completions against the rescored baseline:

  in-band (arm B's own ranges)  Sonnet  7% -> 57%    Haiku 25% -> 43%
  ends with a question                 71% -> 86%    (the directive asked for the opposite)
  stance marker                         6% -> 14%    (doubled, but 80% one phrase)
  hidden-thing, either family          16% -> 16%    (Sonnet 12->7, Haiku 20->25)
  universal lexicon                      0 -> 1      (carl_jung, "it's giving")

So B2 changes four things and nothing else. Arm B's text is frozen in arm_b.py;
it has been run and its numbers are on the record.

1. QUESTION PLACEMENT, stated positively. Arm B said "never a closing seal" and
   the closing-question rate went UP fifteen points. Reading the replies, the
   likely cause is the sentence beside it — "usually one natural, answerable
   question" removed the silent replies (21% -> 9%) and every new question
   landed at the end. B2 names the wanted state (the last sentence is a
   statement) rather than the unwanted one, and promotes the inviting statement
   from an aside to a full substitute.

2. REGISTER. The single universal-lexicon hit in 440 completions was Jung saying
   "it's giving". "Plain, intelligent language" plausibly invited it. "In your
   own register — never contemporary slang" closes that without asking for
   stiffness.

3. A TARGET NUMBER beside the range. Arm B gave a range only; Sonnet landed at
   57% in-band and Haiku at 43%.

4. FOUR STANCE FORMS, NAMED BUT NOT QUOTED (founder edit). Arm B's stance rate
   doubled, but 80% of the hits were the "notice" family and "what I notice"
   alone was 50%. The first draft of this directive offered sample wordings; the
   founder struck them, because giving "What I notice is..." as example one is
   how the formula survives being told to vary.

ONE SENTENCE IS NEW RATHER THAN CHANGED, and it exists to stop this arm
colliding with two personas' anchors:

    "You may challenge what they have said; do not speculate about what they
     have not."

Arm B's concealment ban is aimed at the move where a persona implies the user is
withholding something. But Beauvoir's `anchor_bad_faith_attentive` requires her
to examine "I had no choice" when the user SAYS it, and Socrates' elenchus is
built on pressing a stated claim. Under arm B, Beauvoir produced the persona
lexicon hit "you had no choice" — she said the line for the user rather than
examining theirs. The sentence separates challenging a stated claim (permitted,
and for two personas required) from insinuating about an unstated one (banned).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .arm_b import BANDS  # identical ranges; B2 changes the wording, not the numbers


def _target(lo: int, hi: int) -> int:
    """Midpoint, rounded to 5, ties UP (founder ruling).

    Two land above centre — 67.5 -> 70 and 82.5 -> 85 — which nudges upward.
    That is the direction arm B wanted and Haiku resisted, so the tie-break is
    doing work rather than being arbitrary.
    """
    return int(Decimal((lo + hi) / 2 / 5).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * 5


TARGETS: dict[str, dict[str, int]] = {
    slug: {"standard": _target(*b["standard"]), "deep": _target(*b["deep"])}
    for slug, b in BANDS.items()
}

# ── FOUNDER-APPROVED COPY. Verbatim. Placeholders only. ──────────────────────
#
# Changes from arm B are: the "— about {target}" clause, the varied-stance
# sentence (forms named, NOT quoted), the challenge/speculate sentence, the
# positive question-placement rule, and "in your own register — never
# contemporary slang". Everything else is arm B's approved text unchanged.

_STANCE = (
    "Vary how you do that — a plain observation, a direct claim about them, a "
    "distinction they have not drawn, or a reading you offer as yours. Do not reach "
    "for the same opening every time."
)
_CONCEAL = (
    "You may offer an interpretation, but offer it tentatively and ground it in their "
    "own words; never tell them, directly or by implication, that they are hiding, "
    "avoiding, or failing to name something. You may challenge what they have said; do "
    "not speculate about what they have not."
)
_OPENING = (
    "Leave an easy opening to continue. In most replies the last sentence is a "
    "statement, not a question; if you ask a question, put it earlier in the reply, and "
    "an inviting statement may take its place entirely."
)

FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said: name something meaningful you notice, and take a "
    "clear but proportionate position on it. " + _STANCE + " " + _CONCEAL + " "
    + _OPENING + " Keep your own voice. Plain, precise language in your own register — "
    "never contemporary slang; no decorative aphorisms or fortune-cookie phrasing."
)

STANDARD = (
    "STANDARD\n"
    "Write between {lo} and {hi} words — about {target}. Move the conversation forward "
    "rather than merely reflecting it back. Say what you genuinely notice in their "
    "words and take a position where the evidence supports one. " + _STANCE + " "
    + _CONCEAL + " " + _OPENING + " Keep your own voice. Plain, precise language in "
    "your own register — never contemporary slang; prefer clear speech over poetic or "
    "oracular phrasing."
)

DEEP = (
    "DEEP\n"
    "Write between {deep_lo} and {deep_hi} words — about {deep_target}. Go materially "
    "deeper: connect the person's own details, develop an interpretation, or move "
    "toward a conclusion their words reasonably support — and make clear which parts "
    "are evident and which are your reading. Never tell them, directly or by "
    "implication, that they are hiding, avoiding, or failing to name something. You may "
    "challenge what they have said; do not speculate about what they have not. Leave "
    "room to respond. In most replies the last sentence is a statement, not a question; "
    "a question, if you ask one, sits earlier, and an inviting statement may take its "
    "place. Keep your own voice. Plain, precise language in your own register — never "
    "contemporary slang; no decorative profundity."
)


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    lo, hi = BANDS[persona_slug]["deep" if deep else "standard"]
    t = TARGETS[persona_slug]["deep" if deep else "standard"]
    if deep:
        return DEEP.format(deep_lo=lo, deep_hi=hi, deep_target=t)
    template = FIRST_MESSAGE if first_message else STANDARD
    return template.format(lo=lo, hi=hi, target=t)


def bands_note() -> str:
    return "; ".join(
        f"{s} std {BANDS[s]['standard'][0]}-{BANDS[s]['standard'][1]}"
        f"(~{TARGETS[s]['standard']}) deep {BANDS[s]['deep'][0]}-{BANDS[s]['deep'][1]}"
        f"(~{TARGETS[s]['deep']})"
        for s in BANDS
    )
