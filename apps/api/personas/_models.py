"""Section 5.7 supporting dataclasses for PersonaConfig.

Phase 1: schema only. No data populated yet. All fields optional
with None or empty defaults to preserve backward compatibility.
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
