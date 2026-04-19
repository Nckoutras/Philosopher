"""
Tests for persona configuration integrity.

Ensures new personas can't be added with missing required fields
or configs that would break the system.

Run: cd apps/api && pytest tests/test_personas.py -v
"""
import pytest
from personas import PERSONA_REGISTRY, get_persona, list_personas, is_persona_accessible
from personas._base import PersonaConfig


def test_all_registered_personas_have_required_fields():
    for slug, persona in PERSONA_REGISTRY.items():
        assert persona.slug, f"{slug}: missing slug"
        assert persona.name, f"{slug}: missing name"
        assert persona.tier in ("free", "pro", "premium"), f"{slug}: invalid tier '{persona.tier}'"
        assert persona.worldview, f"{slug}: missing worldview"
        assert persona.tone, f"{slug}: missing tone"
        assert persona.system_fragment, f"{slug}: missing system_fragment"
        assert persona.opening_invocation, f"{slug}: missing opening_invocation"
        assert isinstance(persona.challenge_level, int), f"{slug}: challenge_level must be int"
        assert 1 <= persona.challenge_level <= 5, f"{slug}: challenge_level must be 1-5"


def test_at_least_one_free_persona():
    free = [p for p in PERSONA_REGISTRY.values() if p.tier == "free"]
    assert len(free) >= 1, "Must have at least one free persona for onboarding"


def test_persona_forbidden_phrases_not_empty():
    for slug, persona in PERSONA_REGISTRY.items():
        assert len(persona.forbidden_phrases) > 0, f"{slug}: forbidden_phrases cannot be empty"
        # Check for the absolute worst offenders
        for phrase in ["absolutely", "great question", "that's valid"]:
            assert phrase in [p.lower() for p in persona.forbidden_phrases], \
                f"{slug}: '{phrase}' should be in forbidden_phrases"


def test_marcus_aurelius_is_free():
    persona = get_persona("marcus_aurelius")
    assert persona is not None
    assert persona.tier == "free"


def test_get_persona_returns_none_for_unknown():
    assert get_persona("plato_nonexistent_12345") is None


def test_list_personas_returns_all():
    all_p = list_personas()
    assert len(all_p) == len(PERSONA_REGISTRY)


def test_accessibility_rules():
    assert is_persona_accessible(get_persona("marcus_aurelius"), "free") is True
    assert is_persona_accessible(get_persona("simone_de_beauvoir"), "free") is False
    assert is_persona_accessible(get_persona("simone_de_beauvoir"), "pro") is True
    assert is_persona_accessible(get_persona("simone_de_beauvoir"), "premium") is True


def test_persona_to_dict_serializable():
    import json
    for slug, persona in PERSONA_REGISTRY.items():
        d = persona.to_dict()
        try:
            json.dumps(d)
        except (TypeError, ValueError) as e:
            pytest.fail(f"{slug}: to_dict() not JSON-serializable: {e}")


def test_system_fragment_has_behaviour_section():
    """Each persona's system fragment must contain behavioural instructions."""
    for slug, persona in PERSONA_REGISTRY.items():
        assert "BEHAVIOUR" in persona.system_fragment or "behaviour" in persona.system_fragment.lower(), \
            f"{slug}: system_fragment must contain a BEHAVIOUR section"


def test_no_duplicate_slugs():
    slugs = [p.slug for p in PERSONA_REGISTRY.values()]
    assert len(slugs) == len(set(slugs)), "Duplicate persona slugs found"
