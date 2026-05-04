"""Section 5.7 supporting dataclasses for PersonaConfig.
 
Phase 1: schema only. No data populated yet. All fields optional
with None or empty defaults to preserve backward compatibility.
 
Phase 4: PhenomenologyBridge added as runtime per-request context
(not part of PersonaConfig — produced by phenomenology_bridge_service).
"""
from dataclasses import dataclass, field
from typing import Optional
 
 
@dataclass
class CharacterAnchor:
    id: Optional[str] = None
    rule: Optional[str] = None
    enforcement: Optional[str] = None
    critical: Optional[bool] = None
 
 
@dataclass
class RegisterRange:
    allowed: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    default: Optional[str] = None
 
 
@dataclass
class AntiFlexingRules:
    never_unprompted: list[str] = field(default_factory=list)
    permitted_only_when_user_asks: Optional[dict] = None
 
 
@dataclass
class ResponseLengthSpec:
    standard_reply_words: Optional[tuple[int, int]] = None
    reflective_reply_max_words: Optional[int] = None
    council_mode_words: Optional[tuple[int, int]] = None
    first_message_max_words: Optional[int] = None
 
 
@dataclass
class ForbiddenLexicon:
    phrases: list[str] = field(default_factory=list)
    patterns: list[dict] = field(default_factory=list)
 
 
@dataclass
class BehavioralParameters:
    question_density: Optional[float] = None
    direct_advice_level: Optional[float] = None
    contradiction_detection: Optional[float] = None
    warmth: Optional[float] = None
    irony: Optional[float] = None
    abstraction: Optional[float] = None
    moral_certainty: Optional[float] = None
    challenge_intensity: Optional[float] = None
    lyricism: Optional[float] = None
    practicality: Optional[float] = None
    emotional_soothing: Optional[float] = None
    symbolism_propensity: Optional[float] = None
    interpretation_intensity: Optional[float] = None
 
 
@dataclass
class RegisterOverride:
    sentence_length_target: Optional[tuple[int, int]] = None
    question_density: Optional[float] = None
    direct_advice_level: Optional[float] = None
    contradiction_detection: Optional[float] = None
    warmth: Optional[float] = None
    irony: Optional[float] = None
    abstraction: Optional[float] = None
    moral_certainty: Optional[float] = None
    challenge_intensity: Optional[float] = None
    lyricism: Optional[float] = None
    practicality: Optional[float] = None
    emotional_soothing: Optional[float] = None
    symbolism_propensity: Optional[float] = None
    interpretation_intensity: Optional[float] = None
 
 
# ============================================================
# Phase 4 — runtime per-request context
# ============================================================
 
@dataclass(frozen=True)
class PhenomenologyBridge:
    """Modern Phenomenology Bridge context for a single user message.
 
    Produced by phenomenology_bridge_service.lookup() when the user's
    message contains a modern term that maps to a phenomenological
    essence. Injected into the system prompt at request time.
 
    Fields:
        matched_term: The mapping_key from modern_phenomenology.json
                      (e.g. "ghosting_after_great_dates").
        essence: The phenomenological_essence string from the map.
                 This is the timeless translation of the modern term,
                 surfaced to the persona but never spoken back to the user.
        persona_shading: Persona-specific weighting/emphasis for this
                         essence. None when the persona has no shading
                         entry for this matched_term (e.g. Marcus Aurelius
                         pre-PR-Β content fill-in).
    """
    matched_term: str
    essence: str
    persona_shading: Optional[str]
