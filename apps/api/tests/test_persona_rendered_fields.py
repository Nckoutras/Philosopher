"""The PersonaConfig docstring's RENDERED list must match what the template reads.

WHY THIS TEST EXISTS. On 2026-09-23 four persona diffs were written, reviewed and
approved as a voice fix. All four edited `character_anchors`, which `system_base.jinja2`
never mentions, so all four were inert — the run's `persona_config_hash` came back
byte-identical to the baseline it was meant to change. Nobody checked whether the field
was rendered, because nothing in the codebase said which fields are (TD-94).

The fix was a docstring naming them. **A docstring is a doc claim**, and this file's own
protocol says a doc claim repeated without re-verification is evidence about the previous
doc rather than about the system. So the list is pinned here instead of trusted: add a
`persona.<field>` to the template without updating the docstring, or drop one from the
template, and this fails.

It reads the template and the docstring as text. It makes no API calls and it does not
render a prompt, so it is cheap and runs in CI with everything else.
"""
from __future__ import annotations

import re
from pathlib import Path

from personas._base import PersonaConfig

TEMPLATE = Path(__file__).resolve().parents[1] / "prompts" / "system_base.jinja2"


def _template_fields() -> set[str]:
    """Every `persona.<field>` the template actually reads."""
    return set(re.findall(r"persona\.([a-z_]+)", TEMPLATE.read_text(encoding="utf-8")))


def _docstring_rendered_block() -> set[str]:
    """The names listed under the docstring's RENDERED heading.

    Parsed from the text rather than imported from a constant on purpose: the thing
    under test is what a human editing a persona will READ.
    """
    doc = PersonaConfig.__doc__ or ""
    start = doc.index("RENDERED —")
    end = doc.index("NOT RENDERED, but read by code elsewhere")
    block = doc[start:end]
    known = {f for f in PersonaConfig.__dataclass_fields__}
    return {w for w in re.findall(r"[a-z_]+", block) if w in known}


def test_docstring_rendered_list_matches_the_template() -> None:
    documented = _docstring_rendered_block()
    actual = _template_fields() & set(PersonaConfig.__dataclass_fields__)

    missing = actual - documented
    extra = documented - actual
    assert not missing, (
        "system_base.jinja2 renders persona fields the PersonaConfig docstring does not "
        f"list as RENDERED: {sorted(missing)}. Add them — an editor reading that "
        "docstring would believe changing them is a no-op."
    )
    assert not extra, (
        "the PersonaConfig docstring lists fields as RENDERED that the template does not "
        f"read: {sorted(extra)}. This is the TD-94 failure exactly — a config field that "
        "looks load-bearing and is not."
    )


def test_character_anchors_is_still_unrendered() -> None:
    """Pins the TD-94 ruling: anchors are documentation, not enforcement.

    If anchors are deliberately wired into the prompt later, this test SHOULD fail —
    and its failure is the reminder that doing so invalidates every stored §8.2
    baseline and surfaces eleven latent anchor/fragment contradictions at once. Delete
    it as part of that decision, not on the way past.
    """
    assert "character_anchors" not in _template_fields(), (
        "character_anchors is now rendered into the system prompt. That is a real "
        "decision with real consequences (TD-94): every stored §8.2 baseline becomes "
        "incomparable, and anchors that contradict their own system_fragment — Marcus's "
        "does — start fighting inside the same prompt. If this was intended, remove this "
        "test in the same change and say so."
    )
