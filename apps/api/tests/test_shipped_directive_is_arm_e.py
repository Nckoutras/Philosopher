"""The shipped first-message directive IS arm E, and arm B3 is frozen apart from it.

WHY THIS FILE EXISTS. On 2026-09-23 §8.2 shipped arm E's first-message text to
production. Two things must stay true afterwards, and neither is self-enforcing:

  1. **What ships is what was measured.** Arm E's numbers describe one exact string.
     If production drifts from it by a word, the evidence in
     `evals/results/2026-09-23_armE/armE_record.md` stops describing the product and
     nothing says so.

  2. **Arm B3 must keep reproducing B3.** `arm_b3.FIRST_MESSAGE` used to be
     `reply_directive.FIRST_MESSAGE`, re-exported. Had it stayed that way, shipping
     arm E would have silently redefined `--arm b3` — it would have generated arm E's
     replies under B3's name and every stored B3 run would have become
     unreproducible, with nothing failing. It is now a frozen literal (C-01 applied
     to an eval arm). This file is what keeps it frozen.

STANDARD AND DEEP ARE DELIBERATELY NOT ASSERTED CLEAN. They still carry their own
shape clauses, and that is not an oversight: every §8.2 sample is a first message, so
**no arm has ever exercised them.** They are untouched because nothing tested them,
not because they tested well. The test below pins that they still contain the
prescription, so that this stays visible rather than being quietly assumed handled.
"""
from __future__ import annotations

import pytest

from evals import arm_b3, arm_e
from services import reply_directive as rd

# ── the two clauses arm E REMOVED ───────────────────────────────────────────
REMOVED = (
    ": name something meaningful you notice, and take a clear but proportionate "
    "position on it",
    "Leave an easy opening to continue — usually one natural, answerable question, "
    "which may sit anywhere in the reply and",
)

# ── every clause arm E KEPT, as literals ────────────────────────────────────
KEPT = (
    "Write between {lo} and {hi} words — about {target}.",           # length
    "Respond specifically to what this person has actually said.",   # criterion (d)
    "You may offer an interpretation, but offer it tentatively and "
    "ground it in their own words;",                                 # the HEDGE
    "never tell them, directly or by implication, that they are hiding, "
    "avoiding, or failing to name something.",                       # (a) CONCEAL_BAN
    "You may challenge what they have said; do not speculate about "
    "what they have not.",                                           # (e) CHALLENGE
    "If you end on a question, it must open rather than close — never a "
    "closing seal.",                                                 # (b) SEAL_BAN
    "Plain, precise language in your own register — never contemporary slang",
    "no decorative aphorisms or fortune-cookie phrasing.",           # (c)
)


def test_production_first_message_is_exactly_arm_e():
    """The parity assertion. Arm E's measured result describes THIS string."""
    assert rd.FIRST_MESSAGE == arm_e.FIRST_MESSAGE


@pytest.mark.parametrize("clause", REMOVED)
def test_the_two_shape_clauses_are_gone(clause):
    assert clause not in rd.FIRST_MESSAGE


@pytest.mark.parametrize("clause", KEPT)
def test_every_kept_clause_survives(clause):
    """Listed as literals rather than derived, so a reword shows up here as a diff
    a reviewer reads — not as a passing test that derived itself from the change."""
    assert clause in rd.FIRST_MESSAGE


def test_the_hedge_is_byte_identical_to_what_it_always_was():
    """Arm D removed this clause and (a) rose 19.6%; arm E put it back and (a) fell
    to 11.3%. It is the clause that constrains HOW an interpretation is offered, and
    it is the reason arm E shipped rather than arm D."""
    assert arm_e.HEDGE in rd.FIRST_MESSAGE


def test_criterion_b_survived_the_deletion_that_contained_it():
    """The seal ban lived INSIDE the question prescription. Deleting the
    prescription must not have taken the ban with it."""
    assert "never a closing seal" in rd.FIRST_MESSAGE
    assert "usually one natural, answerable question" not in rd.FIRST_MESSAGE


# ── arm B3 stays frozen ─────────────────────────────────────────────────────

def test_arm_b3_first_message_is_frozen_and_differs_from_production():
    assert arm_b3.FIRST_MESSAGE != rd.FIRST_MESSAGE
    assert "usually one natural, answerable question" in arm_b3.FIRST_MESSAGE
    assert ": name something meaningful you notice" in arm_b3.FIRST_MESSAGE


def test_arm_b3_still_re_exports_standard_and_deep():
    """Only FIRST_MESSAGE was frozen, because only FIRST_MESSAGE diverged. If a
    future change touches STANDARD or DEEP, this test fails and they must be frozen
    in arm_b3 the same way — otherwise B3 silently stops being B3 again."""
    assert arm_b3.STANDARD == rd.STANDARD
    assert arm_b3.DEEP == rd.DEEP


# ── the deferred item, pinned so it cannot be quietly assumed handled ───────

# The shape prescriptions that survive on the two unmeasured paths. They are NOT
# the same text as FIRST_MESSAGE's were, which is itself worth knowing: DEEP asks
# for "a natural, concrete question or an inviting statement" where STANDARD asks
# for "usually one natural, answerable question". Three paths, three wordings, one
# of them now measured.
UNMEASURED_SHAPE = {
    "STANDARD": ("Say what you genuinely notice in their words and take a position",
                 "usually one natural, answerable question"),
    "DEEP": ("develop an interpretation",
             "Leave room to respond — a natural, concrete question or an "
             "inviting statement"),
}


@pytest.mark.parametrize("name", sorted(UNMEASURED_SHAPE))
def test_standard_and_deep_still_carry_their_own_shape_clauses(name):
    """NOT A PASS — A RECORD. §8.2 shipped a first-message change only. These two
    paths still prescribe a shape and NO arm has ever measured them, because every
    §8.2 sample is a first message. When someone tests them, this test is what they
    delete, and its failure is the reminder that the work was never done.
    """
    text = getattr(rd, name)
    for clause in UNMEASURED_SHAPE[name]:
        assert clause in text, (
            f"{name} no longer carries this shape clause: {clause!r}. If that was "
            "deliberate AND measured, delete this test and cite the arm that "
            "measured it. If it was incidental, it is an unmeasured change to a "
            "path §8.2 never exercised."
        )
