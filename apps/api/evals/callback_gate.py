"""MEM2-C-1 — the callback gate, as the eval models it. Pure; no I/O.

THIS IS A MODEL OF A RULING, NOT THE C-2 IMPLEMENTATION. It encodes the
eligibility the founder locked on 2026-10-05 so the harness offers a candidate on
exactly the samples where production would. C-2 writes the real gate beside
`compose_recall`; this one exists so C-1 can measure the behaviour that gate
would license, and its tests are the first statement of the rules in code.

THE RULES, each with the ruling it comes from:

    Ruling 2   source_message_ids present
               is_active
               conversation_id differs from the current conversation
               persona_id equals the responder's
    Ruling 6   the turn is NORMAL with safety level "none"
               the row comes from a NON-flagged conversation
               (no floor here: the floor is MEASURED in C-1, not assumed)
    Ruling 9   a row extracted from a reply that a callback elicited is not
               independent evidence, so it is never itself a candidate
    Ruling 1   at most ONE candidate per turn
    ledger     a row already offered in THIS conversation is not offered again
               (the within-conversation half of Ruling 4's scarcity; the
               cross-conversation half is what C-1 measures for X/Y)

ORDER: highest relevance score first, then newest, then id — the same
lexicographic tie-break `memory_service._ordered` uses, so identical inputs
offer an identical candidate.

WHAT THIS DELIBERATELY DOES NOT DO. No entry_type list. `onboarding_profile` and
`self_portrait` rows never carry source_message_ids (they are written with
none), so Ruling 2 excludes them already; adding a type list would hide a future
writer that stamped message ids onto a tap. The tests pin that they are excluded
BY the source_message_ids rule.
"""
from __future__ import annotations

from typing import Iterable

ELIGIBLE_OUTCOME = "NORMAL"
ELIGIBLE_LEVEL = "none"


def why_ineligible(row, *, responder_slug: str, current_conversation_id: str,
                   offered_in_conversation: Iterable[str] = ()) -> str | None:
    """The FIRST rule a row fails, or None if it is eligible. Named reasons, so a
    report can say which rule excluded what rather than only that something was."""
    if not getattr(row, "source_message_ids", None):
        return "no_source_message_ids"
    if not getattr(row, "is_active", True):
        return "inactive"
    if row.conversation_id is None or row.conversation_id == current_conversation_id:
        return "same_or_no_conversation"
    if row.persona_slug != responder_slug:
        return "other_persona"
    if getattr(row, "flagged_conversation", False):
        return "flagged_conversation"
    if getattr(row, "elicited_by_callback", False):
        return "elicited_by_callback"
    if str(row.id) in {str(x) for x in offered_in_conversation}:
        return "already_offered_this_conversation"
    return None


def offer(rows: list, *, responder_slug: str, current_conversation_id: str,
          turn_outcome: str = ELIGIBLE_OUTCOME, safety_level: str = ELIGIBLE_LEVEL,
          offered_in_conversation: Iterable[str] = ()):
    """The single candidate this turn would be offered, or None."""
    if turn_outcome != ELIGIBLE_OUTCOME or safety_level != ELIGIBLE_LEVEL:
        return None
    offered = tuple(offered_in_conversation)
    eligible = [
        r for r in rows
        if why_ineligible(r, responder_slug=responder_slug,
                          current_conversation_id=current_conversation_id,
                          offered_in_conversation=offered) is None
    ]
    if not eligible:
        return None
    # Three stable sorts, least significant first — memory_service._ordered's
    # shape, so a tie resolves the same way the recall block orders it.
    xs = sorted(eligible, key=lambda r: str(r.id))
    xs.sort(key=lambda r: r.days_ago)                 # newest first
    xs.sort(key=lambda r: r.score, reverse=True)
    return xs[0]
