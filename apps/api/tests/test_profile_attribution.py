"""The onboarding-profile block must not be framed as something the person SAID.

WHY THIS FILE EXISTS (PROMPT-002). On 2026-09-22 a P-04 smoke produced:

    "You value freedom — you said so yourself."

to a person who, in that conversation, had said three things and none of them
that. The claim was GROUNDED — the profile was written 109 seconds earlier and
six memory rows carried it — so this was never hallucination. The prompt told
the model the value was self-reported, and the persona cited it back as speech.
Four instances across three personas and three months.

The fix is a wording change, and a wording change is exactly the kind of thing
that gets undone by a later edit that means well. These tests pin the two halves
of it: the SPEECH framing must stay out, and the non-attribution clause must stay
in.

No API calls. Run: cd apps/api && pytest tests/test_profile_attribution.py -v
"""
import pytest

from personas import PERSONA_REGISTRY, get_persona
from services.prompt_builder import prompt_builder
from services.profile_text import profile_to_display

PROFILE = {"values": ["freedom"], "disagreement_style": "stand_firm"}


@pytest.fixture
def rendered():
    return prompt_builder.build_system(
        persona=get_persona("socrates"), profile=profile_to_display(PROFILE))


def _profile_block(rendered: str) -> str:
    """Just the WHAT WE KNOW block, because the speech rule is about THIS block.

    Scoping matters: the conversational-moves section legitimately says "name a
    contradiction between two things they said", which refers to real
    conversation content. A whole-prompt search for speech verbs flags it, and a
    test that flags correct text is a test that gets deleted.
    """
    start = rendered.index("WHAT WE KNOW ABOUT THIS PERSON")
    end = rendered.index(chr(10) * 2, rendered.index("Material to hold"))
    return rendered[start:end]


def test_the_block_is_not_framed_as_speech(rendered):
    """"They told us this themselves" is the phrase that licensed "you said so
    yourself". It reads as speech because it IS a speech verb."""
    block = _profile_block(rendered).lower()
    assert "told us this themselves" not in block
    for phrase in ("they told us", "they said", "as they put it", "in their words"):
        assert phrase not in block, phrase
    assert "not something they have said to you" in block


def test_the_non_attribution_clause_is_present(rendered):
    assert "never cite it back as their own words" in rendered


def test_the_epistemic_status_survives(rendered):
    """The one thing the old wording got RIGHT, and the reason the block is not
    simply merged into memories below it: the profile is self-reported and
    guaranteed, where memories are inferred and cosine-recalled. Losing this
    distinction would be a worse bug than the one being fixed."""
    assert "self-reported, not inferred" in rendered


def test_the_values_still_reach_the_prompt(rendered):
    """The regression risk of this change is a persona that now IGNORES the
    profile. The material must still be there to hold."""
    assert "They value: freedom." in rendered
    assert "stand firm in their position" in rendered
    assert "stand_firm" not in rendered, "raw slug must never reach a prompt"


def test_no_profile_means_no_block():
    """The block hides entirely, which is why this change cannot move
    persona_config_hash — the §8.2 harness renders with no profile."""
    r = prompt_builder.build_system(persona=get_persona("socrates"))
    assert "WHAT WE KNOW ABOUT THIS PERSON" not in r


def test_persona_config_hash_is_untouched_by_this_change():
    """Pinned to the value the three stored §8.2 runs were measured at
    (baseline/B3 and the H1/H2 placement arms all carry be4c9e3d3d7e7959).
    If this fails, the stored runs are no longer comparable to a new one."""
    from evals.run import persona_config_hash
    assert persona_config_hash() == "be4c9e3d3d7e7959"


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
def test_every_persona_gets_the_guard(slug):
    r = prompt_builder.build_system(
        persona=get_persona(slug), profile=profile_to_display(PROFILE))
    assert "never cite it back as their own words" in r
    assert "told us this themselves" not in r


def test_the_memories_block_still_has_its_own_guard():
    """The precedent this change was modelled on. If it ever disappears, the
    profile guard is no longer 'the same rule the neighbouring block has'."""
    r = prompt_builder.build_system(
        persona=get_persona("socrates"),
        memories=[type("M", (), {"entry_type": "value", "content": "x"})()])
    assert "never announce that you remember" in r
