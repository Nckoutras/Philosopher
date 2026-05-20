"""Jinja2 template rendering helpers.

Single Environment for the whole API — add render_* functions here as new
email types are introduced. Callers are responsible for passing resolved
absolute URLs (portrait_url should already be prefixed before calling).
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_future_self_email(
    *,
    persona_name: str,
    persona_portrait_url: str,
    quote_content: str | None,
    note: str | None,
    scheduled_for_display: str,
    public_base_url: str,
) -> str:
    """Render the future-self HTML email body.

    persona_portrait_url must be an absolute URL (or empty string).
    public_base_url is rendered in the footer link.
    """
    template = _env.get_template("future_self_email.html")
    return template.render(
        persona_name=persona_name,
        persona_portrait_url=persona_portrait_url,
        quote_content=quote_content,
        note=note,
        scheduled_for_display=scheduled_for_display,
        public_base_url=public_base_url,
    )
