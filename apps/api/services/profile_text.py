"""Single source of truth for turning the onboarding profile (raw pill slugs)
into human-readable text.

Used by BOTH:
  - the persona <what_we_know> prompt block (profile_to_display), and
  - the seeded memory rows + instant reflection (profile_to_statements).

Keeping the wording here means the enum->phrase mapping never drifts between the
prompt the persona sees and the memory/reflection text. A raw slug like
"probe_their_view" must NEVER reach a prompt — it always becomes a clean phrase.
"""
from __future__ import annotations

# Value slugs are already clean single words, but they are mapped through here
# too so the option list and the prompt wording share one authority.
VALUE_LABELS: dict[str, str] = {
    "honesty": "honesty",
    "freedom": "freedom",
    "loyalty": "loyalty",
    "justice": "justice",
    "growth": "growth",
    "security": "security",
    "connection": "connection",
    "achievement": "achievement",
}

# Disagreement slugs MUST become human phrases — never surface the raw slug.
DISAGREEMENT_LABELS: dict[str, str] = {
    "stand_firm": "stand firm in their position",
    "seek_the_middle": "look for the middle ground",
    "avoid_conflict": "step back from the conflict",
    "probe_their_view": "probe the other person's view",
    "heat_then_reflect": "react with heat, then reflect",
}


def _join_human(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _value_phrases(profile: dict | None) -> list[str]:
    vals = (profile or {}).get("values") or []
    return [VALUE_LABELS.get(v, v) for v in vals]


def _disagreement_phrase(profile: dict | None) -> str | None:
    slug = (profile or {}).get("disagreement_style")
    if not slug:
        return None
    return DISAGREEMENT_LABELS.get(slug, slug)


def profile_to_display(profile: dict | None) -> dict | None:
    """Humanized view for the <what_we_know> prompt block. Returns None when there
    is nothing to show, so the template block hides entirely."""
    values = _value_phrases(profile)
    disagreement = _disagreement_phrase(profile)
    if not values and not disagreement:
        return None
    return {"values": values, "disagreement_style": disagreement}


def profile_to_statements(profile: dict | None) -> list[str]:
    """Second-person-ready self-statements built from the profile. Shared by the
    memory-seed task and the instant-reflection endpoint so the two never diverge."""
    out: list[str] = []
    values = _value_phrases(profile)
    if values:
        out.append(f"Values {_join_human(values)}.")
    disagreement = _disagreement_phrase(profile)
    if disagreement:
        out.append(f"When they disagree, they tend to {disagreement}.")
    return out
