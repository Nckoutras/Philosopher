"""Persona guards — the SAFETY-001 ruling of 2026-09-24, pinned.

WHAT THEY ARE. Prompt text drawn from the seven `critical: true` promises in
philosopher_brain/personas/*.yaml, rendered as the LAST block before the cache
sentinel under a heading that overrides every instruction above it. They exist
because nothing else is in the path: the ten disclosures in
tests/test_safety_detection_gaps.py all clear the safety gate at level="none", so
the persona answers and nothing intercepts.

WHAT THEY ARE NOT. A gate. A guard changes what the persona says; it cannot stop
the persona from being called, and three of the seven approximate in text a yaml
ACTION (pause, handoff) that no mechanism performs.

THE RULINGS THESE TESTS HOLD:
  - precedence by placement AND wording: last in the cached block, heading states
    the override, persona lines untouched;
  - guards say what to do, never which line they cancel (those references live in
    code comments beside each guard);
  - no crisis number (2026-09-02) — so no digits at all;
  - no other philosopher named — redirecting a person in crisis to another surface
    is a UX decision, not a safety one;
  - the six personas without guards render byte-identically to before.

Run: cd apps/api && pytest tests/test_persona_guards.py -v
"""
import re

import pytest

from personas import PERSONA_REGISTRY
from services.prompt_builder import CACHE_SPLIT_SENTINEL, prompt_builder

HEADING = "WHEN SOMEONE IS BEING HARMED, OR IS IN CRISIS"
OVERRIDE = (
    "What follows overrides every instruction above in this prompt, including this "
    "persona's own. Where a line above tells you to do something this section "
    "forbids, this section wins."
)

EXPECTED_COUNTS = {
    "simone_de_beauvoir": 1,
    "epictetus": 1,
    "carl_jung": 1,
    "marcus_aurelius": 3,
    "miyamoto_musashi": 1,
}

# The guard the P-04 smoke judges ("he controls the money"). Approved copy,
# 2026-09-24 — changing it is a copy change that needs founder approval again.
BEAUVOIR = (
    "If the person describes someone controlling, threatening or harming them "
    "— their money, their phone, where they may go, whether they are safe at "
    "home — do not examine their choices; here freedom and bad faith are the "
    "wrong instruments. Say plainly what is being done to them, treat the "
    "constraint as real, and tell them support outside this conversation "
    "exists. What they chose can wait until they are safe."
)


def _render(slug, sentinel=True):
    return prompt_builder.build_system(PERSONA_REGISTRY[slug], include_cache_sentinel=sentinel)


def _all_guards():
    return [(slug, g) for slug, p in PERSONA_REGISTRY.items() for g in p.guards]


def test_exactly_the_seven_approved_guards_on_the_five_personas():
    counts = {slug: len(p.guards) for slug, p in PERSONA_REGISTRY.items() if p.guards}
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 7


def test_the_beauvoir_guard_is_the_approved_copy():
    assert PERSONA_REGISTRY["simone_de_beauvoir"].guards == [BEAUVOIR]


def test_the_self_harm_guard_names_a_category_not_a_number():
    """2026-09-02: a published crisis number needs phone verification first, so
    guard #4 points to a category of help instead."""
    self_harm = PERSONA_REGISTRY["marcus_aurelius"].guards[0]
    assert "someone they trust, or their local emergency services" in self_harm


def test_no_guard_carries_a_number():
    for slug, guard in _all_guards():
        assert not re.search(r"\d", guard), f"{slug}: a digit in a guard — {guard!r}"


def test_no_guard_names_a_philosopher():
    """Ruled 2026-09-24: 'point to outside support' covers the need; sending a
    person in crisis to another persona is a UX decision, kept out of guards."""
    names = set()
    for p in PERSONA_REGISTRY.values():
        names.add(p.name.lower())
        names.update(part.lower() for part in p.name.split() if len(part) > 3)
    for slug, guard in _all_guards():
        low = guard.lower()
        hit = [n for n in names if re.search(rf"\b{re.escape(n)}\b", low)]
        assert not hit, f"{slug}: guard names {hit}"


def test_guards_say_what_to_do_not_which_line_they_cancel():
    """The heading asserts precedence; the guard carries the instruction. The
    overridden-line references live in code comments, not in the prompt."""
    for slug, guard in _all_guards():
        assert "does not apply" not in guard and "above" not in guard, slug
        assert len(guard.split()) <= 75, f"{slug}: {len(guard.split())} words"


@pytest.mark.parametrize("slug", sorted(EXPECTED_COUNTS))
def test_the_section_is_last_in_the_cached_block(slug):
    """Precedence by placement: nothing persona-specific follows the guards before
    the sentinel, and the guards sit inside the CACHED prefix (static per persona,
    so the cache holds)."""
    system = _render(slug)
    head = system.index(HEADING)
    sentinel = system.index(CACHE_SPLIT_SENTINEL)
    assert head < sentinel
    assert system.index(OVERRIDE) > head
    between = system[head:sentinel]
    for guard in PERSONA_REGISTRY[slug].guards:
        assert guard in between
    # Nothing after the last guard but whitespace before the sentinel.
    last = PERSONA_REGISTRY[slug].guards[-1]
    assert system[system.index(last) + len(last):sentinel].strip() == ""
    # And the persona's own fragment comes BEFORE the section it is outranked by.
    assert system.index(PERSONA_REGISTRY[slug].system_fragment.strip()[:80]) < head

    cached, _uncached = prompt_builder.split_system_for_cache(system)
    assert HEADING in cached["text"]


@pytest.mark.parametrize("slug", sorted(set(PERSONA_REGISTRY) - set(EXPECTED_COUNTS)))
def test_personas_without_guards_render_no_section(slug):
    """Lao Tzu, Wilde and Machiavelli have no authored promises (TD-106); Socrates,
    Freud and Orwell have no critical one. No heading, no empty section."""
    assert PERSONA_REGISTRY[slug].guards == []
    assert HEADING not in _render(slug)
    assert HEADING not in _render(slug, sentinel=False)
