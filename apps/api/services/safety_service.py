"""The safety gates. Spec §10.3 — the crisis ladder — and §10.4, which is why:
"A beautiful persona response is worthless if it is unsafe."

WHAT CHANGED, AND THE FAILURE IT CLOSES. These gates matched English phrases
against `text.lower()`. Greek — the product's first real audience — passed every
one of them. `θέλω να αυτοκτονήσω` returned level="none", which means
should_suppress_persona was False, which means a person in crisis got full
persona immersion instead of the grounded crisis mode §10.3 mandates. Greeklish
(`den antexo allo`) passed too. This was measured before the fix, not assumed.

THREE THINGS MAKE GREEK WORK, and they are separable on purpose:

  1. _normalize(), below. casefold + NFD + drop combining marks + final sigma.
     Greek is written with accents that users routinely omit — `θέλω` and
     `θελω` are the same word to a reader and different strings to Python — and
     `.lower()` does not touch them. Without this, a lexicon would catch only
     the exact accentuation a contributor happened to type.

  2. Greek-script lexicons stored PRE-NORMALISED, with an import-time assertion
     that every entry equals its own normalised form. A contributor who adds
     `θέλω να πεθάνω` with accents gets an ImportError naming the entry, not a
     phrase that silently never fires.

  3. Separate greeklish lists. The normaliser does not transliterate, so Greek
     typed in latin characters is a third vocabulary and is enumerated as one.

WHERE NORMALISATION LIVES, and why it is not at the call sites. There are nine
check_input callers and eleven check_output callers. Normalising at any of them
would mean twenty places to get right and one silent bypass per mistake. It
happens here, once, at the top of each check, on text nobody else has touched.

LANGUAGE DETECTION IS NOT A GATE. text_utils.dominant_language decides which
language to ANSWER in. It never decides whether to check: every message is
matched against every lexicon regardless, because a bilingual user writes
`I can't do this anymore, δεν αντέχω` in one sentence and a detector that
routed that to one lexicon would drop the other half.

COST. Measured at 6.2 microseconds per call on a 576-character message before
this change; the added lexicons are a longer loop over the same normalised
string, not a new I/O path. This runs on every message and must never be able to
time out, rate-limit, or be prompt-injected — which is the whole argument for a
lexicon over an LLM classifier here.
"""
from dataclasses import dataclass, field
from typing import Optional
import logging
import unicodedata

from constants import RISK_LEVELS
from config import config
from services.safety_lexicons import (
    ALL_BANDS,
    GREEK_BANDS,
    LOW_SIGNALS,
    OUTPUT_RISK_PHRASES,
    RISK_HIGH,
    RISK_MEDIUM,
)

logger = logging.getLogger(__name__)


# ── Normalisation ─────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Fold away the differences a reader does not see.

    casefold() rather than lower(): it is the aggressive form, and it already
    maps final sigma to sigma. NFD then splits accented characters into base +
    combining mark so the marks can be dropped — this is what makes `θέλω` and
    `θελω` the same string. The explicit ς→σ at the end is redundant after
    casefold and kept deliberately: it states the intent where a reader looks
    for it, and it survives a future change to casefold's behaviour.

    Latin text is unaffected in practice — the English lexicon entries are all
    equal to their own normalised form, which the assertion below proves.
    """
    folded = unicodedata.normalize("NFD", text.casefold())
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return stripped.replace("ς", "σ")


def _assert_lexicons_are_prenormalised() -> None:
    """Fail at import if any entry would never match.

    An entry that is not equal to its own normalised form is dead: incoming text
    is normalised, the entry is not, and they can never be equal. That failure is
    completely invisible at runtime — the gate simply does not fire — so it is
    converted into a crash at startup, naming the band and the entry.
    """
    bad: list[str] = []
    for band_name, entries in ALL_BANDS.items():
        for entry in entries:
            if entry != _normalize(entry):
                bad.append(f"{band_name}: {entry!r} -> {_normalize(entry)!r}")
    if bad:
        raise ImportError(
            "Safety lexicon entries are not pre-normalised and would never "
            "match. Store them casefolded, without accents, with final sigma "
            "folded to sigma:\n  " + "\n  ".join(bad)
        )


_assert_lexicons_are_prenormalised()


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class SafetyResult:
    level: str = "none"              # none | low | medium | high | critical
    category: Optional[str] = None  # self_harm | crisis | output_harm | other
    trigger: Optional[str] = None
    raw_flags: list[str] = field(default_factory=list)

    @property
    def should_suppress_persona(self) -> bool:
        return self.level in ("medium", "high", "critical")

    @property
    def should_log(self) -> bool:
        return self.level != "none"


# ── Safety service ────────────────────────────────────────────────────────────

class SafetyService:

    VALID_LEVELS = RISK_LEVELS

    async def check_input(self, text: str, user_id: Optional[str] = None) -> SafetyResult:
        """Pre-generation check on user input.

        Every band is matched against every message. See the module docstring on
        why language detection does not gate this.
        """
        normalized = _normalize(text)

        # High risk — immediate suppression
        for phrase in RISK_HIGH:
            if phrase in normalized:
                logger.warning(f"Safety HIGH [{phrase[:20]}] user={user_id}")
                return SafetyResult(
                    level="high",
                    category="self_harm",
                    trigger=phrase,
                )

        # Medium risk — redirect with support signpost
        for phrase in RISK_MEDIUM:
            if phrase in normalized:
                logger.info(f"Safety MEDIUM [{phrase[:20]}] user={user_id}")
                return SafetyResult(
                    level="medium",
                    category="potential_distress",
                    trigger=phrase,
                )

        # Low risk signals — log, continue with persona intact
        flags = [s for s in LOW_SIGNALS if s in normalized]
        if flags:
            return SafetyResult(level="low", category="distress_signal", raw_flags=flags)

        return SafetyResult(level="none")

    async def check_output(self, response_text: str) -> SafetyResult:
        """Post-generation check on LLM response.

        Greek matters here as much as on input: a persona answers in the language
        it was addressed in, so a Greek reply containing method detail would have
        walked straight through the English-only list.
        """
        normalized = _normalize(response_text)
        flags = [p for p in OUTPUT_RISK_PHRASES if p in normalized]

        if flags:
            logger.error(f"Safety POST-GEN flags: {flags}")
            return SafetyResult(
                level="high",
                category="output_harm",
                raw_flags=flags,
            )

        return SafetyResult(level="none")


safety_service = SafetyService()
