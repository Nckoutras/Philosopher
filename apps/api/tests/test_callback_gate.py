"""MEM2-C-1: the eval's callback gate encodes the 2026-10-05 rulings exactly.

Each test names the ruling it pins. These are the first statement of the rules
in code; C-2's production gate should be held to the same cases.

NO API CALLS.
"""
from dataclasses import replace

import pytest

from evals import callback_gate as gate
from evals.callback_samples import MemoryRow

ME = "socrates"
CONV = "conv:current"


def row(**kw) -> MemoryRow:
    base = dict(
        id="m1", kind="candidate", entry_type="struggle", content="User ...",
        provenance="system_inferred", persona_slug=ME, conversation_id="conv:prior",
        source_message_ids=("u1", "a1"), original="I said ...", days_ago=10,
    )
    base.update(kw)
    return MemoryRow(**base)


def offer(rows, **kw):
    return gate.offer(rows, responder_slug=ME, current_conversation_id=CONV, **kw)


def test_an_eligible_row_is_offered():
    r = row()
    assert offer([r]) is r


@pytest.mark.parametrize("change,reason", [
    (dict(source_message_ids=None), "no_source_message_ids"),        # Ruling 2
    (dict(source_message_ids=()), "no_source_message_ids"),          # Ruling 2
    (dict(is_active=False), "inactive"),                             # Ruling 2
    (dict(conversation_id=CONV), "same_or_no_conversation"),         # Ruling 2
    (dict(conversation_id=None), "same_or_no_conversation"),         # Ruling 2
    (dict(persona_slug="carl_jung"), "other_persona"),               # Rulings 2, 3
    (dict(persona_slug=None), "other_persona"),                      # Rulings 2, 3
    (dict(flagged_conversation=True), "flagged_conversation"),       # Ruling 6
    (dict(elicited_by_callback=True), "elicited_by_callback"),       # Ruling 9
])
def test_each_rule_excludes(change, reason):
    r = replace(row(), **change)
    assert gate.why_ineligible(r, responder_slug=ME, current_conversation_id=CONV) == reason
    assert offer([r]) is None


@pytest.mark.parametrize("entry_type", ["onboarding_profile", "self_portrait"])
def test_taps_are_excluded_by_the_message_id_rule_not_a_type_list(entry_type):
    """Ruling 2 excludes them because they carry no source_message_ids. A row of
    the same TYPE that somehow carried ids would pass — and that is deliberate:
    a type list would hide a future writer that stamped ids onto a tap."""
    tap = row(entry_type=entry_type, source_message_ids=None, persona_slug=None,
              conversation_id=None)
    assert gate.why_ineligible(tap, responder_slug=ME,
                               current_conversation_id=CONV) == "no_source_message_ids"


@pytest.mark.parametrize("outcome,level", [
    ("DISTRESS", "none"), ("DISCUSSING", "low"), ("NORMAL", "low"), ("CRISIS", "high"),
])
def test_only_normal_none_turns_are_offered_anything(outcome, level):  # Ruling 6
    assert offer([row()], turn_outcome=outcome, safety_level=level) is None


def test_already_offered_in_this_conversation_is_not_offered_again():
    r = row()
    assert offer([r], offered_in_conversation=["m1"]) is None


def test_at_most_one_candidate_highest_score_first():  # Ruling 1
    a = row(id="a", score=0.4)
    b = row(id="b", score=0.6)
    assert offer([a, b]) is b


def test_ties_break_newest_then_id():
    old = row(id="a", score=0.5, days_ago=30)
    new = row(id="b", score=0.5, days_ago=3)
    assert offer([old, new]) is new
    x = row(id="x", score=0.5, days_ago=3)
    y = row(id="y", score=0.5, days_ago=3)
    assert offer([y, x]) is x
