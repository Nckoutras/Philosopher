from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from personas._base import PersonaConfig
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
        user_name: str | None = None,
    ) -> str:
        template = jinja_env.get_template("system_base.jinja2")
        return template.render(
            persona=persona,
            memories=memories or [],
            passages=passages or [],
            user_name=user_name,
            current_date=date.today().strftime("%B %d, %Y"),
        )

    def build_ritual_opener(self, ritual_template: str, user_name: str | None = None) -> str:
        """Render a ritual prompt template."""
        template = jinja_env.from_string(ritual_template)
        return template.render(user_name=user_name, current_date=date.today().strftime("%B %d, %Y"))


prompt_builder = PromptBuilder()
