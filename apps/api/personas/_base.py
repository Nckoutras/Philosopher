from dataclasses import dataclass, field
from typing import Optional

from ._models import (
    CharacterAnchor,
    RegisterRange,
    AntiFlexingRules,
    ResponseLengthSpec,
    ForbiddenLexicon,
    BehavioralParameters,
    RegisterOverride,
)


@dataclass
class PersonaConfig:
    # Identity
    slug: str
    name: str
    era: str
    tradition: str
    tier: str  # free | pro | premium

    # Avatar & display
    tagline: str
    avatar_emoji: str  # placeholder until real artwork

    # Voice
    worldview: str
    tone: str
    sentence_structure: str
    vocabulary_register: str
    forbidden_phrases: list[str] = field(default_factory=list)

    # Behaviour
    questioning_pattern: str = ""
    challenge_level: int = 3          # 1=gentle 5=relentless
    challenge_style: str = ""
    response_length: str = "medium"   # short | medium | long
    uses_personal_anecdote: bool = True
    cites_own_works: bool = True

    # Retrieval
    retrieval_sources: list[str] = field(default_factory=list)
    retrieval_top_k: int = 4

    # UX
    opening_invocation: str = ""

    # System prompt fragment
    system_fragment: str = ""

    # Section 5.7 — Phase 1 schema extension (all optional, all None by default)
    character_anchors: Optional[list[CharacterAnchor]] = None
    register_range: Optional[RegisterRange] = None
    anti_flexing: Optional[AntiFlexingRules] = None
    response_length_words: Optional[ResponseLengthSpec] = None
    forbidden_lexicon_persona_specific: Optional[ForbiddenLexicon] = None
    behavioral_parameters: Optional[BehavioralParameters] = None
    behavioral_parameters_by_register: Optional[dict[str, RegisterOverride]] = None
    safety: Optional[dict] = None

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)
