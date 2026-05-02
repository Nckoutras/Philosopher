"""Section 5.7 post-generation quality checks.

Runs on every assistant reply AFTER the LLM stream completes,
BEFORE the buffered text is yielded to the client. Three checks:
universal forbidden lexicon, brevity, persona-specific forbidden.

On hit: regenerate up to 3 times. On persistent failure:
deterministic strip + log + send.

Feature flag: POSTPROCESSING_ENABLED env var (default true).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time as _time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from personas._base import PersonaConfig

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Brain JSON loading (cached at module import time)
# ──────────────────────────────────────────────────────────────────

BRAIN_DIR = Path(__file__).resolve().parent.parent / "philosopher_brain"
UNIVERSAL_FORBIDDEN_PATH = BRAIN_DIR / "maps" / "universal_forbidden_lexicon.json"


def _load_universal_forbidden() -> dict:
    """Load and cache the universal forbidden lexicon JSON.

    Called once at import time. Failures are logged and an empty
    dict is returned, so service degrades gracefully if the brain
    file is missing or malformed (postprocessing is then a no-op).
    """
    try:
        with open(UNIVERSAL_FORBIDDEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(
            f"Loaded universal forbidden lexicon: "
            f"{len(data.get('categories', {}))} categories"
        )
        return data
    except FileNotFoundError:
        logger.error(f"Universal forbidden lexicon not found at {UNIVERSAL_FORBIDDEN_PATH}")
        return {"categories": {}, "_meta_implementation": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Universal forbidden lexicon malformed: {e}")
        return {"categories": {}, "_meta_implementation": {}}


_UNIVERSAL_FORBIDDEN = _load_universal_forbidden()


# Feature flag (read once at import time, not per-request)
POSTPROCESSING_ENABLED = os.getenv("POSTPROCESSING_ENABLED", "true").lower() == "true"

# Hard cap on regeneration attempts before deterministic strip
MAX_REGEN_ATTEMPTS = 3


# ──────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────

class CheckAction(str, Enum):
    PASS = "pass"
    REGENERATE = "regenerate"
    STRIP = "strip"
    SKIP = "skip"  # field is None, check skipped (Phase 3 will populate)


@dataclass
class CheckHit:
    """Single forbidden-pattern hit within a check."""
    category: Optional[str] = None         # e.g. "ai_tells", "modern_brands"
    matched_text: Optional[str] = None     # the actual matched string
    pattern: Optional[str] = None          # the regex or phrase that matched
    reason: Optional[str] = None           # human-readable from JSON


@dataclass
class CheckResult:
    """Outcome of a single check (brevity / universal_fb / persona_fb)."""
    check_name: str                        # "brevity" | "universal_forbidden" | "persona_forbidden"
    passed: bool                           # True = no issues found
    action: CheckAction = CheckAction.PASS
    hits: list[CheckHit] = field(default_factory=list)
    word_count: Optional[int] = None       # populated by brevity check only
    target_band: Optional[tuple[int, int]] = None  # populated by brevity check only


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

def check_universal_forbidden(reply: str) -> CheckResult:
    """Scan reply against universal forbidden lexicon.

    Loads from philosopher_brain/maps/universal_forbidden_lexicon.json
    (cached at import). Checks both `phrases` (case-insensitive substring)
    and `patterns` (regex) per category.

    Returns CheckResult with action=REGENERATE if any hit, else PASS.
    """
    hits: list[CheckHit] = []
    reply_lower = reply.lower()
    categories = _UNIVERSAL_FORBIDDEN.get("categories", {})

    for category_name, category_data in categories.items():
        # Phrases: case-insensitive substring match
        for phrase in category_data.get("phrases", []):
            if phrase.lower() in reply_lower:
                hits.append(CheckHit(
                    category=category_name,
                    matched_text=phrase,
                    pattern=phrase,
                    reason=category_data.get("description", ""),
                ))

        # Patterns: regex match
        for pattern_obj in category_data.get("patterns", []):
            regex_str = pattern_obj.get("regex", "")
            if not regex_str:
                continue
            try:
                # Use IGNORECASE for consistency with phrase matching
                match = re.search(regex_str, reply, flags=re.IGNORECASE)
            except re.error as e:
                logger.warning(
                    f"Invalid regex in universal forbidden category "
                    f"'{category_name}': {regex_str} ({e})"
                )
                continue
            if match:
                hits.append(CheckHit(
                    category=category_name,
                    matched_text=match.group(0),
                    pattern=regex_str,
                    reason=pattern_obj.get("reason", ""),
                ))

    return CheckResult(
        check_name="universal_forbidden",
        passed=(len(hits) == 0),
        action=CheckAction.PASS if len(hits) == 0 else CheckAction.REGENERATE,
        hits=hits,
    )


def check_brevity(reply: str, persona: PersonaConfig,
                  conversation_position: str = "mid_session") -> CheckResult:
    """Check word count against persona's brevity targets.

    Phase 1 schema field: persona.response_length_words: Optional[ResponseLengthSpec]
    All 6 personas currently have this as None (Phase 3 will populate).

    Graceful degradation when None: returns action=SKIP, passed=True.

    conversation_position: "first_message" | "mid_session" | "late_session"
    Used to select target band:
      first_message → first_message_max_words (hard ceiling, no lower bound)
      mid_session   → standard_reply_words (tuple lower/upper)
      late_session  → standard_reply_words (same)
    """
    spec = persona.response_length_words

    # Graceful degradation: Phase 3 hasn't populated this yet
    if spec is None:
        return CheckResult(
            check_name="brevity",
            passed=True,
            action=CheckAction.SKIP,
            word_count=None,
            target_band=None,
        )

    word_count = len(reply.split())

    # Select target based on conversation position
    if conversation_position == "first_message" and spec.first_message_max_words is not None:
        # First message: hard ceiling, no lower bound
        upper = spec.first_message_max_words
        lower = 0
    elif spec.standard_reply_words is not None:
        # Standard: tuple of (lower, upper)
        lower, upper = spec.standard_reply_words
    else:
        # Spec exists but neither relevant field populated
        return CheckResult(
            check_name="brevity",
            passed=True,
            action=CheckAction.SKIP,
            word_count=word_count,
            target_band=None,
        )

    target_band = (lower, upper)

    # Pass if within band (lower <= count <= upper)
    # Per spec section 5.6.5: hard ceiling on upper. Lower is soft (under-count
    # is OK, the persona may be appropriately terse).
    passed = word_count <= upper

    return CheckResult(
        check_name="brevity",
        passed=passed,
        action=CheckAction.PASS if passed else CheckAction.REGENERATE,
        word_count=word_count,
        target_band=target_band,
    )


def check_persona_forbidden(reply: str, persona: PersonaConfig) -> CheckResult:
    """Scan reply against persona-specific forbidden lexicon.

    Phase 1 schema field: persona.forbidden_lexicon_persona_specific:
    Optional[ForbiddenLexicon] with .phrases and .patterns.

    All 6 personas currently have this as None (Phase 3 will populate).

    Graceful degradation when None: returns action=SKIP, passed=True.

    Note: this is SEPARATE from the existing persona.forbidden_phrases
    legacy field (which is already enforced at prompt level). This new
    check uses the structured Section 5.7 field.
    """
    lex = persona.forbidden_lexicon_persona_specific

    if lex is None:
        return CheckResult(
            check_name="persona_forbidden",
            passed=True,
            action=CheckAction.SKIP,
        )

    hits: list[CheckHit] = []
    reply_lower = reply.lower()

    # Phrases (case-insensitive substring)
    for phrase in lex.phrases or []:
        if phrase.lower() in reply_lower:
            hits.append(CheckHit(
                category="persona_specific",
                matched_text=phrase,
                pattern=phrase,
                reason=f"persona-specific forbidden phrase ({persona.slug})",
            ))

    # Patterns (regex with reason metadata)
    for pattern_obj in lex.patterns or []:
        # ForbiddenLexicon.patterns is list[dict] (Phase 1 schema)
        regex_str = pattern_obj.get("regex", "") if isinstance(pattern_obj, dict) else ""
        if not regex_str:
            continue
        try:
            match = re.search(regex_str, reply, flags=re.IGNORECASE)
        except re.error as e:
            logger.warning(
                f"Invalid regex in persona '{persona.slug}' forbidden lexicon: "
                f"{regex_str} ({e})"
            )
            continue
        if match:
            hits.append(CheckHit(
                category="persona_specific",
                matched_text=match.group(0),
                pattern=regex_str,
                reason=pattern_obj.get("reason", "") if isinstance(pattern_obj, dict) else "",
            ))

    return CheckResult(
        check_name="persona_forbidden",
        passed=(len(hits) == 0),
        action=CheckAction.PASS if len(hits) == 0 else CheckAction.REGENERATE,
        hits=hits,
    )


async def regenerate_or_trim(
    reply: str,
    persona: PersonaConfig,
    system_prompt: str,
    user_text: str,
    conversation_position: str = "mid_session",
    max_attempts: int = MAX_REGEN_ATTEMPTS,
) -> tuple[str, list[CheckResult]]:
    """Run all checks. Regenerate up to max_attempts. Return final reply + history."""
    start_ts = _time.monotonic()
    history: list[CheckResult] = []
    current = reply

    for attempt in range(max_attempts + 1):
        # Run all three checks
        results = [
            check_universal_forbidden(current),
            check_brevity(current, persona, conversation_position),
            check_persona_forbidden(current, persona),
        ]
        history.extend(results)

        # If all pass (PASS or SKIP), we're done
        all_ok = all(r.action in (CheckAction.PASS, CheckAction.SKIP) for r in results)
        if all_ok:
            duration_ms = int((_time.monotonic() - start_ts) * 1000)
            hit_categories = sorted(set(
                h.category for r in history for h in r.hits if h.category
            ))
            logger.info(
                "postprocessing_outcome",
                extra={
                    "postprocessing_enabled": True,
                    "persona_slug": persona.slug,
                    "attempt_count": attempt,
                    "final_action": "pass" if attempt == 0 else "regenerated",
                    "duration_ms": duration_ms,
                    "hit_categories": hit_categories,
                },
            )
            return current, history

        # Hit detected. If we've used all attempts, deterministic strip
        if attempt >= max_attempts:
            duration_ms = int((_time.monotonic() - start_ts) * 1000)
            hit_categories = sorted(set(
                h.category for r in history for h in r.hits if h.category
            ))
            logger.warning(
                "postprocessing_exhausted",
                extra={
                    "postprocessing_enabled": True,
                    "persona_slug": persona.slug,
                    "attempt_count": attempt,
                    "final_action": "stripped",
                    "duration_ms": duration_ms,
                    "hit_categories": hit_categories,
                },
            )
            current = _deterministic_strip(current, results)
            return current, history

        # Build regen directive based on results + attempt number
        directive = _build_regen_directive(results, attempt, persona)

        # Regenerate via non-streaming complete()
        # Local import here (not module-level) to avoid circular dependency
        try:
            from services.llm_client import llm_client
            current = await llm_client.complete(
                system=system_prompt + "\n\n" + directive,
                user=user_text,
                max_tokens=_compute_max_tokens(persona, conversation_position, attempt),
            )
        except Exception as e:
            duration_ms = int((_time.monotonic() - start_ts) * 1000)
            hit_categories = sorted(set(
                h.category for r in history for h in r.hits if h.category
            ))
            logger.error(
                "postprocessing_failed_open",
                extra={
                    "postprocessing_enabled": True,
                    "persona_slug": persona.slug,
                    "attempt_count": attempt,
                    "final_action": "failed_open",
                    "duration_ms": duration_ms,
                    "hit_categories": hit_categories,
                    "error": str(e)[:200],
                },
            )
            return current, history

    return current, history


def _build_regen_directive(
    results: list[CheckResult],
    attempt: int,
    persona: PersonaConfig,
) -> str:
    """Build the corrective directive for the next regeneration attempt.

    Per Section 5.7 spec _meta_implementation:
      Attempt 0 → 1: remove specific offending phrases
      Attempt 1 → 2: tightening directive added
    """
    directives = ["REGENERATION DIRECTIVE — your previous reply had issues."]

    # Collect specific hits to mention
    forbidden_hits = []
    for r in results:
        if r.check_name in ("universal_forbidden", "persona_forbidden") and r.hits:
            for h in r.hits:
                forbidden_hits.append(h.matched_text)

    if forbidden_hits:
        # Quote the literal phrases so the model knows what to avoid
        formatted = ", ".join(f'"{p}"' for p in forbidden_hits[:5])
        directives.append(
            f"Remove these forbidden phrases from your reply: {formatted}. "
            f"Generate a new reply that conveys the same meaning without them."
        )

    brevity = next((r for r in results if r.check_name == "brevity"), None)
    if brevity and not brevity.passed and brevity.target_band:
        lower, upper = brevity.target_band
        directives.append(
            f"Your reply was {brevity.word_count} words. Target: {lower}-{upper} words. "
            f"Be more concise."
        )

    if attempt >= 1:
        directives.append(
            "TIGHTEN: cut all throat-clearing, all summarization of what the user "
            "just said, all closing flourishes. One idea per response. End when "
            "the point ends."
        )

    return " ".join(directives)


def _compute_max_tokens(
    persona: PersonaConfig,
    conversation_position: str,
    attempt: int,
) -> int:
    """Compute max_tokens for regeneration call.

    Tighter on each retry. Fallback to 1024 if persona has no spec.
    """
    spec = persona.response_length_words
    if spec is None:
        # Phase 3 not populated — fall back to default
        return 1024 if attempt == 0 else 700

    # Approximate: 1 word ≈ 1.4 tokens (English)
    if conversation_position == "first_message" and spec.first_message_max_words:
        target_words = spec.first_message_max_words
    elif spec.standard_reply_words:
        _, target_words = spec.standard_reply_words
    else:
        return 1024 if attempt == 0 else 700

    # Add headroom; tighten on retries
    headroom = 1.4 if attempt == 0 else 1.2 if attempt == 1 else 1.0
    return int(target_words * 1.4 * headroom)


def _deterministic_strip(reply: str, results: list[CheckResult]) -> str:
    """Last-resort: remove forbidden substrings from reply mechanically.

    Only handles phrase hits. Pattern hits (regex) are left in place
    because mechanical regex stripping is unsafe (could cut sentences
    in half). If a pattern hits after 3 regens, we send the reply with
    a logged warning rather than mangling it.
    """
    stripped = reply
    for r in results:
        if r.check_name not in ("universal_forbidden", "persona_forbidden"):
            continue
        for h in r.hits:
            if h.matched_text and h.pattern == h.matched_text:
                # This was a phrase hit (pattern == matched_text)
                # Use case-insensitive replace
                pat = re.escape(h.matched_text)
                stripped = re.sub(pat, "", stripped, flags=re.IGNORECASE)
    # Collapse double spaces created by stripping
    stripped = re.sub(r"\s{2,}", " ", stripped).strip()
    return stripped
