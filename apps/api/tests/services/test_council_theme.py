"""Tests for the council synthesis `theme` field (share-card context line).

The council share card rendered a verdict with no context: the owner forgets
what they asked within days, and a viewer has no hook at all. The matter's
context already existed in synthesis_structured, but `real_question` is a
verbatim reading of something personal — too personal for a surface built to
be shared. `theme` is the neutral, sharable alternative, generated in the SAME
structured synthesis call (no extra LLM round-trip).

Covered here: the prompt asks for it, and the parse treats it exactly like the
other grounded-or-null beats — capped, safety-gated, null-safe, and absent
without breaking anything (old rows simply have no `theme` key).

Run: cd apps/api && pytest tests/services/test_council_theme.py -v
"""
import json
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, patch

from services.council_prompts import COUNCIL_SYNTHESIS_PROMPT
from services.council_service import _clean_field, _parse_synthesis

THEME_CAP_WORDS = 8


# ── The prompt asks for it ────────────────────────────────────────────────────

def test_the_synthesis_prompt_declares_theme_in_its_json_shape():
    # The shape line is what the model copies; a field described in prose but
    # missing from the shape gets omitted from the reply.
    shape_line = [ln for ln in COUNCIL_SYNTHESIS_PROMPT.split("\n") if '"verdict"' in ln]
    assert shape_line, "could not find the JSON shape line in the synthesis prompt"
    assert '"theme"' in shape_line[0]


def test_the_synthesis_prompt_specifies_theme_as_neutral_and_capped():
    spec = [ln for ln in COUNCIL_SYNTHESIS_PROMPT.split("\n") if ln.startswith("- theme:")]
    assert spec, "the synthesis prompt has no `- theme:` field spec"
    spec = spec[0]
    assert "3-6 words" in spec, "the theme spec must state its 3-6 word range"
    assert "On ..." in spec, "the theme spec must give the On-... title form"
    assert "null" in spec, "the theme spec must allow null when nothing honest fits"


def test_the_theme_spec_names_territory_not_the_persons_situation():
    # The whole point of a separate field: real_question is the private reading,
    # theme is what a stranger may see. The spec must rule out the situation
    # ITSELF, not merely ask for neutrality — "be neutral" alone gets restated as
    # the decision the person is facing, which is the thing that must not ship.
    spec = " ".join(
        ln for ln in COUNCIL_SYNTHESIS_PROMPT.splitlines()
        if ln.strip().startswith('"- theme:') or "TERRITORY" in ln
        or "identifying detail" in ln or "Same language as the verdict" in ln
    )
    assert "neutral" in spec
    assert "TERRITORY" in spec
    assert "identifying detail" in spec
    assert "Same language as the verdict" in spec


def test_the_theme_examples_are_titles_not_situations():
    # The spec previously gave a noun-phrase example ("Leaving a stable job")
    # while forbidding the situation — the example WAS the situation. Both
    # examples must now be On-... titles, or the model follows the example.
    spec = " ".join(
        ln for ln in COUNCIL_SYNTHESIS_PROMPT.splitlines() if "e.g." in ln and "On " in ln
    )
    assert "On permission and asking" in spec
    assert "On leaving well" in spec


def test_the_existing_beats_are_untouched():
    # theme is additive — the four beats the card and the feed already read must
    # keep their specs, or this PR silently changes the synthesis everyone sees.
    for field in ('"real_question"', '"tension"', '"verdict"', '"next_move"'):
        assert field in COUNCIL_SYNTHESIS_PROMPT
    for spec in ("- real_question:", "- tension:", "- verdict:", "- next_move:"):
        assert spec in COUNCIL_SYNTHESIS_PROMPT


# ── The parse handles it ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_grounded_theme_survives_the_clean_path():
    with patch("services.council_service.safety_service") as safety:
        safety.check_output = AsyncMock(return_value=type("R", (), {"should_suppress_persona": False})())
        assert await _clean_field("On permission and asking", cap_words=THEME_CAP_WORDS) == (
            "On permission and asking"
        )


@pytest.mark.asyncio
async def test_an_over_long_theme_is_nulled_not_truncated():
    # Same gross guard as real_question / next_move: >= 1.5x the cap nulls the
    # field rather than shipping a half sentence onto a share card.
    long_theme = " ".join(["word"] * (THEME_CAP_WORDS * 2))
    with patch("services.council_service.safety_service") as safety:
        safety.check_output = AsyncMock(return_value=type("R", (), {"should_suppress_persona": False})())
        assert await _clean_field(long_theme, cap_words=THEME_CAP_WORDS) is None


@pytest.mark.asyncio
async def test_a_marginal_theme_still_ships():
    # 1.5x is deliberately gross: 9-10 words is over the stated cap but reads
    # fine on the card, so it ships rather than leaving the card contextless.
    marginal = " ".join(["word"] * (THEME_CAP_WORDS + 2))
    with patch("services.council_service.safety_service") as safety:
        safety.check_output = AsyncMock(return_value=type("R", (), {"should_suppress_persona": False})())
        assert await _clean_field(marginal, cap_words=THEME_CAP_WORDS) == marginal


@pytest.mark.asyncio
async def test_null_absent_and_non_string_themes_all_become_none():
    with patch("services.council_service.safety_service") as safety:
        safety.check_output = AsyncMock(return_value=type("R", (), {"should_suppress_persona": False})())
        for value in (None, "", "   ", "null", "NULL", 42, [], {}):
            assert await _clean_field(value, cap_words=THEME_CAP_WORDS) is None


@pytest.mark.asyncio
async def test_a_flagged_theme_is_nulled_without_taking_the_card_down():
    # The output-safety gate nulls the field only; the verdict still renders.
    with patch("services.council_service.safety_service") as safety:
        safety.check_output = AsyncMock(return_value=type("R", (), {"should_suppress_persona": True})())
        assert await _clean_field("something the gate dislikes", cap_words=THEME_CAP_WORDS) is None


def test_a_synthesis_payload_carrying_theme_parses():
    raw = json.dumps({
        "real_question": "Are you staying for the work or the safety?",
        "tension": "One path costs money, the other costs years.",
        "verdict": "The council splits on timing, not on direction.",
        "next_move": "Name the number that would make leaving safe.",
        "theme": "On leaving well",
    })
    assert _parse_synthesis(raw)["theme"] == "On leaving well"


def test_a_synthesis_payload_without_theme_still_parses():
    # Every council session generated before this PR. The card must render from
    # these unchanged — .get('theme') is None and the theme line is skipped.
    raw = json.dumps({
        "real_question": "Are you staying for the work or the safety?",
        "tension": "One path costs money, the other costs years.",
        "verdict": "The council splits on timing, not on direction.",
        "next_move": "Name the number that would make leaving safe.",
    })
    parsed = _parse_synthesis(raw)
    assert parsed is not None
    assert parsed.get("theme") is None


# ── The service stores it ─────────────────────────────────────────────────────

def _synthesis_payload_source() -> str:
    """The payload dict literal built in stream_council, as source text."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "services" / "council_service.py").read_text(encoding="utf-8")
    start = src.index("payload = {")
    return src[start:src.index("}", start)]


def test_the_stored_payload_includes_theme_through_the_clean_path():
    block = _synthesis_payload_source()
    assert '"theme"' in block, "synthesis_structured payload does not carry theme"
    assert "_clean_field(structured.get(\"theme\")" in block, (
        "theme must go through _clean_field, not be stored raw"
    )
    assert f"cap_words={THEME_CAP_WORDS}" in block


def test_theme_does_not_gate_the_payload():
    # verdict is the only required beat. A missing theme must never turn a good
    # synthesis into a synthesis_error.
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "services" / "council_service.py").read_text(encoding="utf-8")
    gate = [ln for ln in src.split("\n") if "if verdict_text:" in ln]
    assert gate, "the verdict gate moved — re-check what now gates the payload"
    assert "if theme" not in src
