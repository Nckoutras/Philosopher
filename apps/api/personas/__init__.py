from ._base import PersonaConfig
from .marcus_aurelius import MARCUS_AURELIUS
from .simone_de_beauvoir import SIMONE_DE_BEAUVOIR
from .carl_jung import CARL_JUNG

# Registry: slug → config
PERSONA_REGISTRY: dict[str, PersonaConfig] = {
    MARCUS_AURELIUS.slug: MARCUS_AURELIUS,
    SIMONE_DE_BEAUVOIR.slug: SIMONE_DE_BEAUVOIR,
    CARL_JUNG.slug: CARL_JUNG,
    # ADD NEW PERSONAS HERE — no other file needs to change
    # EPICTETUS.slug: EPICTETUS,
    # SOCRATES.slug: SOCRATES,
    # SIGMUND_FREUD.slug: SIGMUND_FREUD,
}


def get_persona(slug: str) -> PersonaConfig | None:
    return PERSONA_REGISTRY.get(slug)


def list_personas(tier_filter: str | None = None) -> list[PersonaConfig]:
    personas = list(PERSONA_REGISTRY.values())
    if tier_filter:
        personas = [p for p in personas if p.tier == tier_filter]
    return personas


TIER_ORDER = {"free": 0, "pro": 1, "premium": 2}


def is_persona_accessible(persona: PersonaConfig, user_plan: str) -> bool:
    return TIER_ORDER.get(persona.tier, 99) <= TIER_ORDER.get(user_plan, 0)
