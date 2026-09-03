"""
Tests for prompt builder — ensures the system prompt template
renders without errors and contains required sections.

Run: cd apps/api && pytest tests/test_prompts.py -v
"""
import pytest
from services.prompt_builder import PromptBuilder
from personas import get_persona


@pytest.fixture
def builder():
    return PromptBuilder()


@pytest.fixture
def marcus():
    return get_persona("marcus_aurelius")


class FakeMemory:
    entry_type = "struggle"
    content = "User struggles with procrastination"


class FakePassage:
    source_title = "Meditations"
    source_type = "primary_text"
    page_ref = "Book IV.3"
    content = "Men seek retreats for themselves..."


def test_system_prompt_renders_without_error(builder, marcus):
    prompt = builder.build_system(persona=marcus)
    assert len(prompt) > 100


def test_system_prompt_contains_persona_fragment(builder, marcus):
    prompt = builder.build_system(persona=marcus)
    assert "Marcus Aurelius" in prompt


def test_system_prompt_contains_hard_rules(builder, marcus):
    prompt = builder.build_system(persona=marcus)
    assert "HARD RULES" in prompt
    assert "fabricate" in prompt.lower()


def test_system_prompt_contains_therapist_disclaimer(builder, marcus):
    """Preamble must disclaim clinical role; crisis handling is the safety layer's job."""
    prompt = builder.build_system(persona=marcus)
    assert "therapist" in prompt.lower()


def test_system_prompt_no_crisis_exit_instruction(builder, marcus):
    """Crisis handling must not be delegated to the LLM — safety layer intercepts first."""
    prompt = builder.build_system(persona=marcus)
    assert "exit persona immediately" not in prompt.lower()
    assert "provide crisis resources" not in prompt.lower()


def test_system_prompt_with_memories(builder, marcus):
    memories = [FakeMemory()]
    prompt = builder.build_system(persona=marcus, memories=memories)
    assert "procrastination" in prompt
    assert "WHAT YOU KNOW" in prompt


def test_system_prompt_without_memories_has_no_memory_section(builder, marcus):
    prompt = builder.build_system(persona=marcus, memories=[])
    assert "WHAT YOU KNOW" not in prompt


# ── The memory use-directive (Memory-v2 Ruling #6) ───────────────────────────
#
# WHAT WAS WRONG. The memory block's only instruction was
# "(Extracted from prior conversations. Hold probabilistically.)" — a hedge, and
# the sole guidance the model got about memory. The adjacent GROUNDING PASSAGES
# block carried three explicit use directives by comparison, so the one section
# describing the person was also the one the model was told to hold loosely.
# MEMORY_V2_INVESTIGATION_2026-09-03 §2b traced part of the "council/chat feels
# generic" finding to exactly this asymmetry.
#
# THIS IS FOUNDER-APPROVED COPY. The literal below is deliberately a SECOND,
# independent copy of the string rather than an import of whatever the template
# holds — an assertion that imported its subject could not detect a rewording,
# because both sides would move together. A silent edit to system_base.jinja2
# fails here. If the copy is ever revised, it is revised in both places, on
# purpose, with the founder's sign-off — which is the point.
APPROVED_MEMORY_DIRECTIVE = (
    "These are things you know of this person from earlier conversations. Let them inform "
    "how you meet what they bring today. Never recite them, never list them, never announce "
    "that you remember — familiarity shows in how you speak, not in repeating what was said."
)


def test_the_memory_block_carries_the_approved_use_directive_verbatim(builder, marcus):
    """Character-for-character. A paraphrase is a copy change, and copy changes on
    this surface are the founder's call, not a refactor's side effect."""
    prompt = builder.build_system(persona=marcus, memories=[FakeMemory()])
    assert APPROVED_MEMORY_DIRECTIVE in prompt


def test_the_memory_block_no_longer_tells_the_model_to_hold_memory_loosely(builder, marcus):
    """THE REGRESSION. The dampening instruction must be gone, not merely joined."""
    prompt = builder.build_system(persona=marcus, memories=[FakeMemory()])
    assert "probabilistic" not in prompt.lower()
    assert "Hold probabilistically" not in prompt
    assert "Extracted from prior conversations" not in prompt


def test_the_dampening_phrasing_survives_nowhere_in_the_prompt_templates(builder):
    """Not just in one render — the phrasing is gone from the prompt source itself,
    so it cannot return through a template this test does not happen to compose."""
    from pathlib import Path

    from services.prompt_builder import PROMPTS_DIR

    for template in Path(PROMPTS_DIR).glob("*.jinja2"):
        text = template.read_text(encoding="utf-8")
        assert "probabilistic" not in text.lower(), template.name


def test_the_directive_appears_only_when_there_is_memory_to_direct(builder, marcus):
    """The instruction lives inside the {% if memories %} block, so a turn that
    recalled nothing must not carry an instruction about memories it does not have."""
    prompt = builder.build_system(persona=marcus, memories=[])
    assert APPROVED_MEMORY_DIRECTIVE not in prompt


def test_the_directive_does_not_leak_into_councils_memory_free_prompt(builder, marcus):
    """Council passes memories=[] unconditionally (council_service.py:245); its
    memory is a separate ruling and a separate PR. Pinned here so this change is
    provably inert for that path."""
    prompt = builder.build_system(persona=marcus, memories=[], passages=[])
    assert "WHAT YOU KNOW" not in prompt
    assert APPROVED_MEMORY_DIRECTIVE not in prompt


def test_the_memory_block_still_renders_the_memories_themselves(builder, marcus):
    """The directive replaced an instruction, not the content: entries still land."""
    prompt = builder.build_system(persona=marcus, memories=[FakeMemory()])
    assert "procrastination" in prompt
    assert "[STRUGGLE]" in prompt


def test_system_prompt_with_passages(builder, marcus):
    passages = [FakePassage()]
    prompt = builder.build_system(persona=marcus, passages=passages)
    assert "Meditations" in prompt
    assert "GROUNDING PASSAGES" in prompt


def test_system_prompt_without_passages_has_no_grounding_section(builder, marcus):
    prompt = builder.build_system(persona=marcus, passages=[])
    assert "GROUNDING PASSAGES" not in prompt


def test_system_prompt_includes_forbidden_phrases(builder, marcus):
    prompt = builder.build_system(persona=marcus)
    assert "Absolutely" in prompt or "absolutely" in prompt.lower()


def test_ritual_prompt_renders(builder):
    template = "Today is {{ current_date }}. Reflect on {{ user_name or 'your practice' }}."
    result = builder.build_ritual_opener(template, user_name="Alex")
    assert "Alex" in result
    assert "Today is" in result


def test_ritual_prompt_without_user_name(builder):
    template = "Begin with {{ user_name or 'silence' }}."
    result = builder.build_ritual_opener(template)
    assert "silence" in result


# ── build_safety_response ─────────────────────────────────────────────────────

def test_safety_response_renders_without_error(builder):
    response = builder.build_safety_response(level="high")
    assert len(response) > 20


def test_safety_response_single_copy_for_all_suppression_levels(builder):
    """v1 uses one copy regardless of level — no persona-differentiated copy."""
    assert builder.build_safety_response(level="medium") == builder.build_safety_response(level="high")
    assert builder.build_safety_response(level="critical") == builder.build_safety_response(level="high")


def test_safety_response_no_country_specific_numbers(builder):
    response = builder.build_safety_response()
    assert "988" not in response
    assert "741741" not in response
    assert "findahelpline" not in response.lower()


def test_safety_response_no_first_person_voice(builder):
    """No 'I' — response must not carry persona or app self-reference."""
    response = builder.build_safety_response()
    assert " I " not in response
    assert not response.startswith("I ")
    assert "I'm" not in response
    assert "I am" not in response


def test_safety_response_no_persona_name(builder):
    """No philosopher signature in the safety response."""
    response = builder.build_safety_response()
    for name in ["Marcus", "Socrates", "Nietzsche", "Freud", "Jung", "Beauvoir", "Epictetus"]:
        assert name not in response, f"Persona name '{name}' leaked into safety response"


def test_safety_response_neutral_crisis_language(builder):
    """Must reference crisis support without naming any country's services."""
    response = builder.build_safety_response()
    assert "crisis" in response.lower()
    assert "mental health" in response.lower()


def test_safety_response_no_user_name_injection(builder):
    """build_safety_response accepts no user_name parameter — name cannot leak."""
    import inspect
    sig = inspect.signature(builder.build_safety_response)
    assert "user_name" not in sig.parameters
