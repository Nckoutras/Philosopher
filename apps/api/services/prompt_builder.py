from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Optional

from personas._base import PersonaConfig
from personas._models import PhenomenologyBridge
from models import MemoryEntry, SourceChunk
from datetime import date

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Prompt-cache split marker. Emitted into the rendered system prompt (via the
# {{ cache_sentinel }} slot in system_base.jinja2) ONLY when a caller passes
# include_cache_sentinel=True. split_system_for_cache() splits on it to place a
# cache_control breakpoint after the static per-persona blocks. It is an
# artificial token that can never occur in rendered persona content, and its
# removal reconstructs the sentinel-free render byte-for-byte (the template
# line's own newline lives in the suffix — see split_system_for_cache).
CACHE_SPLIT_SENTINEL = "<<<PHILOSOPHER_CACHE_BREAKPOINT>>>"

jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=select_autoescape([]),
    trim_blocks=True,
    lstrip_blocks=True,
)


class PromptBuilder:
    def build_system(
        self,
        persona: PersonaConfig,
        memories: list[MemoryEntry] = None,
        passages: list[SourceChunk] = None,
        phenomenology_bridge: Optional[PhenomenologyBridge] = None,
        profile: Optional[dict] = None,
        include_cache_sentinel: bool = False,
    ) -> str:
        # include_cache_sentinel emits CACHE_SPLIT_SENTINEL into the {{ cache_sentinel }}
        # slot (after the static per-persona blocks). Defaults False, so every caller
        # NOT opting in (async tasks, counterview, mirror, letters, portrait, the
        # reading-revisit opener, scripts, tests) gets a sentinel-free string — the
        # split helper then no-ops on it. When False the render is byte-identical to
        # the pre-caching output (the slot emits "").
        template = jinja_env.get_template("system_base.jinja2")
        return template.render(
            persona=persona,
            memories=memories or [],
            passages=passages or [],
            phenomenology_bridge=phenomenology_bridge,
            profile=profile,
            current_date=date.today().strftime("%B %d, %Y"),
            cache_sentinel=CACHE_SPLIT_SENTINEL if include_cache_sentinel else "",
        )

    def split_system_for_cache(self, system: str) -> "str | list[dict]":
        """Split a rendered system prompt into a cached prefix + uncached suffix at
        the sentinel, so the API caches the static per-persona blocks. Guarantee:
        prefix + suffix == the sentinel-free render, byte-for-byte (the template
        line's newline sits in the suffix). If no sentinel is present — any caller
        that did not opt in — the string is returned unchanged (a safe no-op). This
        adds a cache_control breakpoint only; the exact same bytes reach the model.
        """
        if CACHE_SPLIT_SENTINEL not in system:
            return system
        assert system.count(CACHE_SPLIT_SENTINEL) == 1, "cache sentinel must appear exactly once"
        prefix, suffix = system.split(CACHE_SPLIT_SENTINEL, 1)
        return [
            {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": suffix},
        ]

    def cache_whole_system(self, system: str) -> list[dict]:
        """Wrap a fully-static system prompt as a single cached block — breakpoint at
        the END. Used for Council member calls, whose system prompt is static per
        (persona, role) with no per-turn content, so the whole prompt is cacheable.
        Same bytes reach the model; only a cache_control breakpoint is added.
        """
        return [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ]

    def build_safety_response(self, level: str = "high") -> str:
        """Render the generic app-voice safety response. No persona, no user context."""
        template = jinja_env.get_template("safety_response.jinja2")
        return template.render(level=level).strip()

    def build_ritual_opener(self, ritual_template: str, user_name: str | None = None) -> str:
        """Render a ritual prompt template."""
        template = jinja_env.from_string(ritual_template)
        return template.render(user_name=user_name, current_date=date.today().strftime("%B %d, %Y"))


prompt_builder = PromptBuilder()
