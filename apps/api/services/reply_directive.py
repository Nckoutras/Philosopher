"""The reply-length and stance directive, appended last to every system prompt.

THIS IS PRODUCTION CODE THAT THE EVAL HARNESS IMPORTS, not a copy of it. That
direction matters: `evals/arm_b3.py` re-exports these strings, so the arm that
was measured and the prompt that ships are the same object, and
tests/test_harness_parity.py proves it by byte comparison rather than by
inspection.

WHERE THE TEXT CAME FROM. Four measured arms over 880 completions, 2026-09-22:

    baseline   the shipped prompt. Sonnet 7% in-band, 47.0 mean words.
    arm B      this text minus the three changes below. Sonnet 57%, 64.3w.
    arm B2     arm B plus a positive question rule. Sonnet 59%, 66.1w — and a
               blind reader preferred arm B over it 16 votes to 6.
    arm B3     this text. Sonnet 76% in-band, 93.8w; a blind reader split
               11:11 against arm B, i.e. could not tell them apart.

B2's question rule ("in most replies the last sentence is a statement") is NOT
here. It moved the metric hard — Sonnet 88% -> 52% ending on a question — and
the reader still preferred arm B; of the six B2 replies the reader did prefer,
all six ended on a question. Three readings now show that readers do not dislike
a closing question. Sealing and unnatural questions are a Listening-judge
criterion, not a directive-wording problem.

WHAT THE THREE SENTENCES DO, each traceable to a measurement:

  the register clause   the one universal-lexicon hit in 440 completions was
                        Jung saying "it's giving"; it did not recur once the
                        clause was added
  challenge/speculate   arm B's concealment ban collides with Beauvoir's
                        anchor_bad_faith_attentive and Socrates' elenchus, both
                        of which press a STATED claim. Under arm B she produced
                        the persona-lexicon hit "you had no choice" — saying the
                        line FOR the user instead of examining theirs
  the target number     ranges alone left Sonnet at 57% in-band; with a target,
                        76%

THE BANDS ARE THE PERSONA'S OWN, read from PersonaConfig rather than duplicated
here. They moved in the same change that added this file: the old
standard_reply_words were authored, never measured against a reader, and a blind
read chose the LONGER reply in 6 of 7 decided pairs (MODEL-001).
"""
from __future__ import annotations

import logging

from personas._base import PersonaConfig

logger = logging.getLogger(__name__)

# Slugs already reported. The fallback is per-turn, the log is per-persona:
# a registered persona losing its band would otherwise emit one line per reply.
_DEGRADED_REPORTED: set[str] = set()


def _report_degraded(persona: PersonaConfig, why: str) -> None:
    slug = getattr(persona, "slug", "<unknown>")
    if slug in _DEGRADED_REPORTED:
        return
    _DEGRADED_REPORTED.add(slug)
    logger.error(
        "reply_directive_degraded",
        extra={"persona_slug": slug, "reason": why,
               "effect": "reply shipped with NO length or stance directive"},
    )

# The three sentences that distinguish this from arm B, kept as named constants
# so tests can assert their presence without re-typing them.
REGISTER = (
    "Plain, precise language in your own register — never contemporary slang"
)
CHALLENGE = (
    "You may challenge what they have said; do not speculate about what they have not."
)
CONCEAL_BAN = (
    "never tell them, directly or by implication, that they are hiding, avoiding, "
    "or failing to name something."
)

# THE SEAL BAN, STANDING ALONE — 2026-09-23, arm E.
#
# Criterion (b)'s constraint used to live INSIDE the question prescription:
# "…usually one natural, answerable question, which may sit anywhere in the reply
# and is never a closing seal." Arm E removes the prescription, which would have
# removed the ban with it. It is restated here so the constraint survives WITHOUT
# mandating that a reply contain a question. Same constraint, no instruction to ask.
SEAL_BAN = (
    "If you end on a question, it must open rather than close — never a closing seal."
)

# FIRST_MESSAGE IS ARM E — founder ruling 2026-09-23, §8.2 test 1 (BUG-009).
#
# WHAT CHANGED: two SHAPE clauses removed, and nothing else.
#   1. ": name something meaningful you notice, and take a clear but proportionate
#      position on it"
#   3. "Leave an easy opening to continue — usually one natural, answerable
#      question, which may sit anywhere in the reply and"
#
# WHAT IS KEPT, byte-for-byte: the length sentence, "Respond specifically to what
# this person has actually said", clause 2's HEDGE ("offer it tentatively and ground
# it in their own words"), CONCEAL_BAN, CHALLENGE, REGISTER, the aphorism ban, and —
# via SEAL_BAN above — criterion (b).
#
# WHY. The directive is appended LAST to every persona's system prompt (94% of the
# way through it, against the persona's own voice block at 7%) and was identical for
# all eleven. It prescribed one reply shape — acknowledge, interpret, open question —
# and that shape was what §8.2 measured as eleven personas collapsing into three.
# Measured, 77 replies per arm, against a control that differs ONLY in this string:
#
#   three personas NEVER named in 154 judgements   1 -> 15   (p=0.0004)
#   personas never proposed at all                 2 -> 0
#   recognition, all eleven                   29.9% -> 41.6%
#   Socrates attractor, share of all guesses     32% -> 19%
#   (a) over-interpretation per 100 words       1.68 -> 1.87
#   (c) oracular per 100 words                  1.16 -> 1.23
#
# THE COST IS REAL AND IS NOT HIDDEN: (a) rose 11.3%. It missed a pre-set 10% gate
# by 1.3 instances — 114 against 112.7 permitted — on a measure with ONE read per
# reply and p=0.453. Founder override, 2026-09-23: "refusing a real gain over a
# non-significant miss serves the threshold, not the product." The override and its
# reasoning are recorded in evals/results/2026-09-23_armE/armE_record.md, including
# that the gate would have passed at 112.
#
# STANDARD AND DEEP ARE UNTOUCHED, AND ALSO UNMEASURED. They carry their own shape
# clauses. Every §8.2 sample is a first message, so NO ARM HAS EVER EXERCISED THEM —
# they are not "kept because they tested well", they are kept because nothing tested
# them at all. That is logged open-and-deferred, not closed.
FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words — about {target}. Respond specifically to what "
    "this person has actually said. You may offer an interpretation, but offer "
    "it tentatively and ground it in their own words; " + CONCEAL_BAN + " " + CHALLENGE
    + " " + SEAL_BAN + " Keep your own "
    "voice. " + REGISTER + "; no decorative aphorisms or fortune-cookie phrasing."
)

STANDARD = (
    "STANDARD\n"
    "Write between {lo} and {hi} words — about {target}. Move the conversation forward "
    "rather than merely reflecting it back. Say what you genuinely notice in their words "
    "and take a position where the evidence supports one. You may offer an "
    "interpretation, but offer it tentatively and ground it in their own words; "
    + CONCEAL_BAN + " " + CHALLENGE + " Leave an easy opening to continue — usually "
    "one natural, answerable question, which may sit anywhere in the reply and is never "
    "a closing seal. Keep your own voice. " + REGISTER + "; prefer clear speech over "
    "poetic or oracular phrasing."
)

DEEP = (
    "DEEP\n"
    "Write between {lo} and {hi} words — about {target}. Go materially deeper: connect "
    "the person's own details, develop an interpretation, or move toward a conclusion "
    "their words reasonably support — and make clear which parts are evident and which "
    "are your reading. Never tell them, directly or by implication, that they are "
    "hiding, avoiding, or failing to name something. " + CHALLENGE + " Leave room to "
    "respond — a natural, concrete question or an inviting statement, never a closing "
    "seal. Keep your own voice. " + REGISTER + "; no decorative profundity."
)


# The DEEP band's floor, per persona. Its ceiling is the persona's own
# reflective_reply_max_words; only the floor needs storing.
#
# IT IS A TABLE AND NOT A FORMULA, because no formula round-trips. The deep
# bands were computed from unrounded targets before the standard bands were
# rounded to 5 and before Musashi was moved, so deriving the floor from either
# the standard band or the ceiling gives the measured value for 8 of 11 personas
# and the wrong one for simone_de_beauvoir (105 vs 110), lao_tzu (65 vs 70) and
# george_orwell (190 vs 195). Three wrong prompts is worse than eleven numbers.
#
# tests/test_arm_b3.py::test_deep_floor_matches_the_arm_that_was_run pins
# every entry against the arm that ran, so this cannot drift from what was
# measured.
DEEP_FLOOR = {
    "lao_tzu": 70, "marcus_aurelius": 85, "socrates": 85, "epictetus": 85,
    "oscar_wilde": 85, "miyamoto_musashi": 85, "carl_jung": 95,
    "sigmund_freud": 95, "niccolo_machiavelli": 95, "simone_de_beauvoir": 110,
    "george_orwell": 130,
}


def _target(lo: int, hi: int) -> int:
    """Midpoint rounded to 5, ties up. Two land above centre (67.5 -> 70,
    82.5 -> 85), which nudges upward — the direction the blind read asked for."""
    return int((lo + hi) / 10 + 0.5) * 5


def directive(persona: PersonaConfig, *, first_message: bool, deep: bool,
              band: tuple[int, int] | None = None) -> str:
    """The block appended last to this persona's system prompt.

    Returns "" when the persona carries no response_length_words, so a persona
    added without one degrades to the pre-existing prompt rather than raising.

    `band` overrides the persona's standard band. It carries the ADAPTIVE range
    when `_adaptive_band_for_input` fires, so the reply still gets exactly ONE
    length sentence — adaptive's numbers inside this directive, rather than a
    second "LENGTH FOR THIS REPLY" paragraph beside it. Adaptive wins when it
    fires; otherwise the persona band. Ignored on the deep path, which has its
    own ceiling.

    ON THE DEEP PATH THIS IS THE SECOND LENGTH SENTENCE, BY DECISION.
    `_deepen_directive` already says "up to about N words" and this block says
    "Write between M and N words". Both cite the SAME ceiling
    (reflective_reply_max_words), so it is redundancy rather than contradiction,
    and it is exactly what arm B3's 33 deep samples ran.
    tests/test_arm_b3.py pins that they agree. Folding the two together is a
    logged follow-up, to be measured before it ships.

    ADAPTIVE IS THE COMMON CASE MID-SESSION, NOT AN EDGE. Measured on Oregon:
    it fires on 364 of 445 eligible turns (81.8%), and 358 of those are the
    SHORT tier. So this directive's STANDARD band governs roughly one
    mid-session turn in five; the rest carry adaptive's compressed range.

    ONLY THE FIRST-MESSAGE PATH HAS BEEN MEASURED. Every sample in the §8.2
    suite is a first message, so STANDARD and DEEP ship on the strength of
    FIRST_MESSAGE's numbers plus one sentence each that no run has exercised.
    """
    spec = getattr(persona, "response_length_words", None)
    if spec is None:
        _report_degraded(persona, "response_length_words is None")
        return ""
    if deep:
        hi = spec.reflective_reply_max_words
        lo = DEEP_FLOOR.get(persona.slug)
        if hi is None or lo is None:
            _report_degraded(persona, "no reflective ceiling or DEEP_FLOOR entry")
            return ""
        return DEEP.format(lo=lo, hi=hi, target=_target(lo, hi))
    pair = band if band is not None else spec.standard_reply_words
    # Graceful degradation, the same shape check_brevity uses for spec is None:
    # a persona whose band is missing or malformed falls back to the
    # pre-existing prompt rather than raising inside the reply path.
    try:
        lo, hi = pair
        lo, hi = int(lo), int(hi)
    except (TypeError, ValueError):
        _report_degraded(persona, "standard band missing or malformed")
        return ""
    template = FIRST_MESSAGE if first_message else STANDARD
    return template.format(lo=lo, hi=hi, target=_target(lo, hi))
