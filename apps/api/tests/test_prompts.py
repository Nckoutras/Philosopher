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


def test_system_prompt_contains_safety_instruction(builder, marcus):
    prompt = builder.build_system(persona=marcus)
    assert "crisis" in prompt.lower() or "therapist" in prompt.lower()


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
