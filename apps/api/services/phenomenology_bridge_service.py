"""Modern Phenomenology Bridge service.

Phase 4 of Section 5.7 framework. When a user's message contains a modern
term (e.g. "ghosting", "burnout", "imposter syndrome"), this service maps
it to a timeless phenomenological essence + persona-specific shading.
The orchestration layer injects the result into the system prompt at the
MODERN PHENOMENOLOGY BRIDGE slot, so the persona engages with the
underlying experience without naming the modern term back to the user.

Source of truth: apps/api/philosopher_brain/maps/modern_phenomenology.json
"""
import json
import logging
from pathlib import Path
from typing import Optional

from personas._models import PhenomenologyBridge

logger = logging.getLogger(__name__)

# Path to the brain map JSON. Resolved at import time.
_MAP_PATH = (
    Path(__file__).parent.parent
    / "philosopher_brain"
    / "maps"
    / "modern_phenomenology.json"
)


class PhenomenologyBridgeService:
    """Loads modern_phenomenology.json once at startup and provides
    a lookup() method for per-request bridge resolution.

    Matching strategy:
        1. Substring match on each entry's "triggers" list (case-insensitive).
        2. Specificity resolution: if mapping_key A contains mapping_key B
           as a substring, A wins (e.g. ghosting_after_great_dates over
           ghosting).
        3. First-match-wins for disjoint surviving matches by earliest
           position in user_text. Tiebreaker: longer mapping_key wins.

    Fallback: if nothing matches, lookup() returns None — no bridge injection.
    """

    # Production persona slug → modern_phenomenology.json shading key
    _NORMALIZED_SLUG_MAP = {
        "sigmund_freud": "freud",
        "carl_jung": "jung",
        "simone_de_beauvoir": "de_beauvoir",
        "epictetus": "epictetus",
        "socrates": "socrates",
        "marcus_aurelius": "marcus_aurelius",
    }

    def __init__(self, map_path: Path = _MAP_PATH) -> None:
        self._map_path = map_path
        self._mappings_by_key: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load and cache mappings from the JSON file. Called once at init."""
        try:
            with self._map_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._mappings_by_key = data.get("mappings", {})
            logger.info(
                f"PhenomenologyBridgeService loaded {len(self._mappings_by_key)} "
                f"mappings from {self._map_path.name}"
            )
        except FileNotFoundError:
            logger.error(
                f"Phenomenology map file not found at {self._map_path}. "
                f"Service will return None for all lookups."
            )
            self._mappings_by_key = {}
        except json.JSONDecodeError as e:
            logger.error(
                f"Phenomenology map JSON parse error: {e}. "
                f"Service will return None for all lookups."
            )
            self._mappings_by_key = {}

    def lookup(
        self,
        user_message: str,
        persona_slug: str,
    ) -> Optional[PhenomenologyBridge]:
        """Resolve a user message to a phenomenology bridge if any mapping
        triggers fire.

        Args:
            user_message: The raw user input text.
            persona_slug: The production persona slug (e.g. "sigmund_freud").

        Returns:
            A PhenomenologyBridge if a mapping fired, None otherwise.
            Never raises — all internal errors are swallowed and logged.
        """
        # 1. INPUT VALIDATION
        if not user_message or not user_message.strip():
            return None

        if not self._mappings_by_key:
            # Map failed to load at init; nothing to do.
            return None

        try:
            return self._do_lookup(user_message, persona_slug)
        except Exception as e:
            # Defensive: never let bridge lookup break a conversation.
            logger.warning(
                f"PhenomenologyBridgeService.lookup() failed unexpectedly "
                f"for persona={persona_slug}: {e}. Returning None."
            )
            return None

    def _do_lookup(
        self,
        user_message: str,
        persona_slug: str,
    ) -> Optional[PhenomenologyBridge]:
        """Core matching logic. Wrapped in try/except by lookup()."""
        lowered_text = user_message.lower()

        # 2. COLLECT ALL MATCHED MAPPING_KEYS
        # A mapping_key is "matched" if any of its triggers appears as a
        # substring in lowered_text. We record the leftmost position the
        # key surfaces at in the text.
        matched: dict[str, int] = {}  # mapping_key -> earliest_position_in_text
        for mapping_key, entry in self._mappings_by_key.items():
            triggers = entry.get("triggers", [])
            # Defensive fallback (should not occur with v4 schema):
            if not triggers:
                triggers = [mapping_key.replace("_", " ")]

            earliest: Optional[int] = None
            for trigger in triggers:
                pos = lowered_text.find(trigger.lower())
                if pos != -1 and (earliest is None or pos < earliest):
                    earliest = pos

            if earliest is not None:
                matched[mapping_key] = earliest

        # 3. NO MATCHES → FALLBACK PER _implementation_notes
        if not matched:
            return None

        # 4. SPECIFICITY RESOLUTION (substring containment ON MAPPING_KEYS)
        # If mapping_key A contains mapping_key B as substring (and A != B),
        # A is more specific → drop B from candidates.
        # Example: "ghosting_after_great_dates" contains "ghosting" → drop "ghosting".
        surviving = set(matched.keys())
        for key_a in list(surviving):
            for key_b in list(surviving):
                if key_a == key_b:
                    continue
                if key_b in key_a:  # key_a is superset of key_b
                    surviving.discard(key_b)

        if not surviving:
            # Defensive; should not happen if matched was non-empty.
            return None

        # 5. FIRST-MATCH-WINS FOR DISJOINT SURVIVORS
        # Sort surviving keys by their earliest position in text (ascending).
        # Tiebreaker: by mapping_key string length (longer key wins, since a
        # longer mapping_key represents a more specific concept).
        chosen_key = min(
            surviving,
            key=lambda k: (matched[k], -len(k)),
        )

        # 6. SLUG NORMALIZATION & SHADING LOOKUP
        shading_key = self._NORMALIZED_SLUG_MAP.get(persona_slug, persona_slug)
        entry = self._mappings_by_key[chosen_key]
        shading = entry.get("persona_shading", {}).get(shading_key)
        # shading is None when persona has no entry (e.g., marcus_aurelius)

        # 7. RETURN
        essence = entry.get("phenomenological_essence", "")
        if not essence:
            # Malformed entry; nothing useful to inject.
            logger.warning(
                f"Mapping {chosen_key} has empty phenomenological_essence. "
                f"Skipping bridge injection."
            )
            return None

        return PhenomenologyBridge(
            matched_term=chosen_key,
            essence=essence,
            persona_shading=shading,
        )


# Module-level singleton, matching the pattern used by prompt_builder,
# memory_service, retrieval_service, etc.
phenomenology_bridge_service = PhenomenologyBridgeService()
