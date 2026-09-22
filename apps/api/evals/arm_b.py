"""Arm B — the tightened directive, appended last.

WHAT ARM B IS, AND WHAT IT REPLACED. The first arm B was length-only: sentence
counts, on the theory that the shipped replies were too long. A blind read of
run 1 killed it. Shown eleven pairs of the same prompt answered by Haiku and by
Sonnet, with no labels, the founder chose the LONGER reply in 6 of 7 decided
pairs, and two of the three "neither" marks asked for MORE length. The one
shorter pick came with a reason about the question, not the brevity.

So the target moved. Arm B is now about STYLE, and the numbers move UP rather
than down. What the two readings pointed at:

  - the founder's own comments: less poetic, less oracular ("B is like a fortune
    cookie"), natural answerable questions, the question not always a closing
    seal, an explicit observation with a stance ("loved the 'What strikes me is'
    part")
  - measured over all 220 run-1 completions: 71% of replies end on a question,
    the hidden-thing move appears in 16% by regex and in 86% by a second
    reader's judgement, and the explicit stance marker appears in 6%
  - the second reader independently: `self_talk` no on 22/22, and `ideal_words`
    above the old first_message cap in 19 of 22

THE DIRECTIVE TEXT BELOW IS FOUNDER-APPROVED COPY. It is reproduced verbatim;
only {lo}, {hi}, {deep_lo} and {deep_hi} are substituted. Do not reword it,
tighten it, or fix its punctuation. If it needs to change, it changes by a
founder ruling and this docstring records the new one.

INTERPRETATION IS NOT FORBIDDEN, CONCEALMENT-ACCUSATION IS. Freud and Jung were
the only two personas a blind reader identified every single time (4/4 each,
against five personas at 0/4). Their identifiability IS interpretation. The rule
forbids telling the user they are hiding, avoiding or not naming something; it
does not forbid reading beneath the surface, and a future edit that blurs those
two is a regression.

PLACEMENT. Appended after everything else, so it is the last thing in the system
prompt — after HARD RULE 8, and after `_deepen_directive` on a deep sample.
Arm "baseline" appends nothing at all and is byte-identical to run 1, which
tests/test_harness_parity.py asserts.
"""
from __future__ import annotations

# ── Per-persona word ranges (founder-approved 2026-09-22) ────────────────────
#
# Derived by scaling each persona's CURRENT standard band midpoint by 1.7742, so
# the mean target across the eleven is 75 words, preserving their relative
# order; {lo} = 0.8 x target and {hi} = 1.2 x target, rounded to 5. DEEP target
# is 1.6 x standard target, same +/-20%.
#
# ONE PERSONA IS NOT ON THAT CURVE. miyamoto_musashi scales to 75-110 / 120-180,
# and was moved by founder ruling to the 55-80 / 85-130 group. His shipped band
# is (30, 75) — the second widest of the eleven — which contradicts his own
# anchor_cuts_the_unnecessary ("strips the user's excess to the single thing
# that matters") and his system_fragment ("Short lines. One point per reply —
# cut the rest"). Scaling a band faithfully inherits whatever is wrong with it,
# and that band was already wrong. The move drops the mean standard target from
# 75.0 to 72.6, which the founder accepted.
#
# FIRST MESSAGE USES THE SAME RANGE AS STANDARD. The separate
# first_message_max_words (35-50) never reached any prompt — its only readers
# are check_brevity and _compute_max_tokens — so there was never a first-message
# instruction for a tighter range to tighten. The harness still SCORES against
# that cap so BREV-002 stays visible; expect arm B's fm_over to approach 100% by
# construction, which is an artefact of the design and not a regression.
BANDS: dict[str, dict[str, tuple[int, int]]] = {
    "lao_tzu":             {"standard": (45, 65),  "deep": (70, 100)},
    "marcus_aurelius":     {"standard": (55, 80),  "deep": (85, 130)},
    "socrates":            {"standard": (55, 80),  "deep": (85, 130)},
    "epictetus":           {"standard": (55, 80),  "deep": (85, 130)},
    "oscar_wilde":         {"standard": (55, 80),  "deep": (85, 130)},
    "miyamoto_musashi":    {"standard": (55, 80),  "deep": (85, 130)},   # moved, see above
    "carl_jung":           {"standard": (60, 90),  "deep": (95, 145)},
    "sigmund_freud":       {"standard": (60, 90),  "deep": (95, 145)},
    "niccolo_machiavelli": {"standard": (60, 90),  "deep": (95, 145)},
    "simone_de_beauvoir":  {"standard": (65, 100), "deep": (110, 160)},
    "george_orwell":       {"standard": (80, 120), "deep": (130, 195)},
}

# ── FOUNDER-APPROVED COPY. Verbatim. Placeholders only. ──────────────────────

FIRST_MESSAGE = (
    "FIRST MESSAGE\n"
    "Write between {lo} and {hi} words. Respond specifically to what this person has actually "
    "said: name something meaningful you notice, and take a clear but proportionate position "
    "on it. You may offer an interpretation, but offer it tentatively and ground it in their "
    "own words; never tell them, directly or by implication, that they are hiding, avoiding, "
    "or failing to name something. Leave an easy opening to continue — usually one natural, "
    "answerable question, which may sit anywhere in the reply and is never a closing seal. "
    "Keep your own voice. Plain, intelligent language; no decorative aphorisms or "
    "fortune-cookie phrasing."
)

STANDARD = (
    "STANDARD\n"
    "Write between {lo} and {hi} words. Move the conversation forward rather than merely "
    "reflecting it back. Say what you genuinely notice in their words and take a position "
    "where the evidence supports one. You may offer an interpretation, but offer it "
    "tentatively and ground it in their own words; never tell them, directly or by "
    "implication, that they are hiding, avoiding, or failing to name something. Leave an easy "
    "opening to continue — usually one natural, answerable question, which may sit anywhere "
    "in the reply and is never a closing seal. Keep your own voice. Prefer clear speech over "
    "poetic or oracular phrasing."
)

DEEP = (
    "DEEP\n"
    "Write between {deep_lo} and {deep_hi} words. Go materially deeper: connect the person's "
    "own details, develop an interpretation, or move toward a conclusion their words "
    "reasonably support — and make clear which parts are evident and which are your reading. "
    "Never tell them, directly or by implication, that they are hiding, avoiding, or failing "
    "to name something. Leave room to respond — a natural, concrete question or an inviting "
    "statement, never a closing seal. Keep your own voice; no decorative profundity."
)

# "b2" lives in arm_b2.py. Arm B's own text is FROZEN — it has been run and its
# numbers are on the record; an edit here would silently invalidate that run.
ARMS = ("baseline", "tightened", "b2", "b2clean", "b3")


def directive(persona_slug: str, *, deep: bool, first_message: bool = True) -> str:
    """The arm-B block for one sample, with the numbers substituted.

    Every sample in the §8.2 suite is a first message, so `first_message`
    defaults True; STANDARD exists for the mid-session arms that Distinctiveness
    and Listening will need.
    """
    bands = BANDS[persona_slug]
    if deep:
        lo, hi = bands["deep"]
        return DEEP.format(deep_lo=lo, deep_hi=hi)
    lo, hi = bands["standard"]
    template = FIRST_MESSAGE if first_message else STANDARD
    return template.format(lo=lo, hi=hi)


def bands_note() -> str:
    """One line per persona, for the run manifest — so a reader of the results
    never has to go to the source to find out what the arm actually asked for."""
    return "; ".join(
        f"{s} std {b['standard'][0]}-{b['standard'][1]} deep {b['deep'][0]}-{b['deep'][1]}"
        for s, b in BANDS.items()
    )
