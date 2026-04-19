from dataclasses import dataclass, field
from typing import Optional
import logging
from constants import RISK_LEVELS
from config import config

logger = logging.getLogger(__name__)

# ── Safe response text ────────────────────────────────────────────────────────

SAFE_RESPONSE_HIGH = """What you're carrying sounds serious — more serious than reflection alone can hold.

Before we continue: if you're in immediate distress, please reach out now.

**988 Suicide & Crisis Lifeline** — call or text **988** (US)
**Crisis Text Line** — text HOME to **741741** (US/UK/CA)
**International** — findahelpline.com

I'm here to think alongside you, and I will be. But right now, you may need more than a philosophical conversation. Please reach out to someone who can actually be present with you.

When you're ready to return, I'll be here."""

SAFE_RESPONSE_MEDIUM = """I want to be honest with you: what you're describing sounds like it's heavier than a single conversation can carry.

I'm a reflective companion, not a therapist. I can think with you, but I can't provide the kind of sustained support this might call for.

If things feel overwhelming, please consider speaking with someone — a counsellor, a trusted person in your life, or a crisis line if needed (text 741741 or call 988 in the US).

With that said — I'm listening. What's at the centre of this for you?"""

# ── Risk phrase lists ─────────────────────────────────────────────────────────

RISK_HIGH = [
    "kill myself", "end my life", "ending my life", "suicide", "want to die",
    "take my life", "taking my life", "don't want to be alive", "wish i was dead",
    "self harm", "cutting myself", "hurt myself", "overdose",
    "not worth living", "better off dead", "can't keep living",
    "planning to end", "goodbye forever", "end it all", "ending it all",
    "no reason to live", "ready to die", "want it to be over",
]

RISK_MEDIUM = [
    "can't go on", "no point anymore", "no point to anything", "hopeless",
    "disappear", "nothing matters", "can't take it anymore", "want to disappear",
    "everyone would be better without me", "so done with everything",
    "exhausted with living", "tired of existing", "don't see the point",
    "feel invisible", "world would be better without me",
]

OUTPUT_RISK_PHRASES = [
    "lethal dose", "how to jump", "best method", "painless way",
    "painless method", "want to jump", "where to buy",
    "most effective way to", "easiest way to die", "least painful",
    "method would be", "way to end", "how to end your life",
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class SafetyResult:
    level: str = "none"              # none | low | medium | high | critical
    category: Optional[str] = None  # self_harm | crisis | output_harm | other
    trigger: Optional[str] = None
    raw_flags: list[str] = field(default_factory=list)
    safe_response: Optional[str] = None

    @property
    def should_suppress_persona(self) -> bool:
        return self.level in ("high", "critical")

    @property
    def should_log(self) -> bool:
        return self.level != "none"


# ── Safety service ────────────────────────────────────────────────────────────

class SafetyService:

    VALID_LEVELS = RISK_LEVELS

    async def check_input(self, text: str, user_id: Optional[str] = None) -> SafetyResult:
        """Pre-generation check on user input."""
        text_lower = text.lower()

        # High risk — immediate suppression
        for phrase in RISK_HIGH:
            if phrase in text_lower:
                logger.warning(f"Safety HIGH [{phrase[:20]}] user={user_id}")
                return SafetyResult(
                    level="high",
                    category="self_harm",
                    trigger=phrase,
                    safe_response=SAFE_RESPONSE_HIGH,
                )

        # Medium risk — redirect with support signpost
        for phrase in RISK_MEDIUM:
            if phrase in text_lower:
                logger.info(f"Safety MEDIUM [{phrase[:20]}] user={user_id}")
                return SafetyResult(
                    level="medium",
                    category="potential_distress",
                    trigger=phrase,
                    safe_response=SAFE_RESPONSE_MEDIUM,
                )

        # Low risk signals — log, continue with persona intact
        low_signals = ["tired", "exhausted", "burden", "alone", "no one cares", "failure", "worthless"]
        flags = [s for s in low_signals if s in text_lower]
        if flags:
            return SafetyResult(level="low", category="distress_signal", raw_flags=flags)

        return SafetyResult(level="none")

    async def check_output(self, response_text: str) -> SafetyResult:
        """Post-generation check on LLM response."""
        text_lower = response_text.lower()
        flags = [p for p in OUTPUT_RISK_PHRASES if p in text_lower]

        if flags:
            logger.error(f"Safety POST-GEN flags: {flags}")
            return SafetyResult(
                level="high",
                category="output_harm",
                raw_flags=flags,
                safe_response=SAFE_RESPONSE_HIGH,
            )

        return SafetyResult(level="none")


safety_service = SafetyService()
