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
