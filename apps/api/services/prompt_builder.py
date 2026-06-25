from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Optional

from personas._base import PersonaConfig
from personas._models import PhenomenologyBridge
from models import MemoryEntry, SourceChunk
from datetime import date

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

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
    ) -> str:
        template = jinja_env.get_template("system_base.jinja2")
        return template.render(
            persona=persona,
            memories=memories or [],
            passages=passages or [],
            phenomenology_bridge=phenomenology_bridge,
            profile=profile,
            current_date=date.today().strftime("%B %d, %Y"),
        )

    def build_safety_response(self, level: str = "high") -> str:
        """Render the generic app-voice safety response. No persona, no user context."""
        template = jinja_env.get_template("safety_response.jinja2")
        return template.render(level=level).strip()

    def build_ritual_opener(self, ritual_template: str, user_name: str | None = None) -> str:
        """Render a ritual prompt template."""
        template = jinja_env.from_string(ritual_template)
        return template.render(user_name=user_name, current_date=date.today().strftime("%B %d, %Y"))


prompt_builder = PromptBuilder()
