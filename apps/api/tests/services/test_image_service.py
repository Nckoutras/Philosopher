"""Minimal smoke tests for the redesigned reflection share card.

Covers _render_reflection_canvas: renders without error, output is the
expected 1080×1350 PNG, and the hero-missing fallback still renders.
"""

import ast
import inspect
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from services import image_service
from services.image_service import (
    _render_reflection_canvas,
    _fit_thumbnail_label,
    COUNCIL_THEME_FONT_SIZE,
    _load_font,
    REFLECT_THUMB_LABEL_FONT_SIZE,
    REFLECT_THUMB_LABEL_MAX_WIDTH,
    _format_date,
    COUNCIL_BAND_TOP,
    _letterspace,
    _render_season_card,
    SEASON_EYEBROW_FONT_SIZE,
    PERSONAS_DIR,
    FONTS_DIR,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
)


def _require_fonts():
    if not (FONTS_DIR / "CormorantGaramond-Italic.ttf").exists():
        pytest.skip("Font files not available in test env")


def _render(**overrides) -> bytes:
    kwargs = dict(
        quote="The unexamined life is not worth living.",
        portrait_path=None,          # exercises the initial-avatar path
        persona_initial="S",
        intro_text="Socrates told me",
        saved_at=datetime(2026, 6, 9),
    )
    kwargs.update(overrides)
    return _render_reflection_canvas(**kwargs)


def test_reflection_canvas_renders_valid_png():
    _require_fonts()
    png = _render()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_reflection_canvas_is_1080x1350():
    _require_fonts()
    img = Image.open(BytesIO(_render()))
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_reflection_canvas_hero_missing_fallback(monkeypatch):
    """Missing hero asset → render on plain Vellum, still 1080×1350."""
    _require_fonts()
    monkeypatch.setattr(image_service, "HERO_PATH", Path("/nonexistent/hero.webp"))
    img = Image.open(BytesIO(_render()))
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


# ── Council card: theme line, persona names, display date ─────────────────────
#
# All three are OPT-IN parameters on the shared canvas, because the same canvas
# renders the line, mirror and letter cards. Every assertion below that says
# "unchanged" is guarding those three, not the council card.

COUNCIL_KW = dict(
    quote="The council splits on timing, not on direction.",
    portrait_path=None,
    persona_initial=None,
    intro_text="The Council",
    saved_at=datetime(2026, 8, 24),
)


def _council(**overrides) -> bytes:
    kwargs = dict(COUNCIL_KW)
    kwargs.update(overrides)
    return _render_reflection_canvas(**kwargs)


def test_council_card_renders_with_a_theme():
    _require_fonts()
    png = _council(theme="Leaving a stable job", band_top=COUNCIL_BAND_TOP)
    assert png.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10]))  # PNG magic
    assert Image.open(BytesIO(png)).size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_council_card_renders_without_a_theme():
    # Every session generated before this PR. None and empty string both skip.
    _require_fonts()
    for value in (None, "", "   "):
        png = _council(theme=value)
        assert Image.open(BytesIO(png)).size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_a_theme_actually_changes_the_pixels():
    # Guards against the line silently not drawing: same card, theme vs no theme.
    _require_fonts()
    assert _council(theme=None) != _council(theme="Leaving a stable job", band_top=COUNCIL_BAND_TOP)


def _portraits(*slugs) -> list[Path]:
    """Real bundled portraits — an EMPTY thumbnails list makes _draw_thumbnail_row
    return before it draws anything, so a names test built on [] would assert
    nothing at all."""
    paths = [PERSONAS_DIR / f"{s}.webp" for s in slugs]
    if not all(p.exists() for p in paths):
        pytest.skip("Persona portraits not available in test env")
    return paths


def test_council_card_renders_names_under_the_portraits():
    _require_fonts()
    paths = _portraits("socrates", "marcus_aurelius")
    with_names = _render_reflection_canvas(
        **COUNCIL_KW, thumbnails=paths, thumbnail_labels=["Socrates", "Marcus Aurelius"]
    )
    without = _render_reflection_canvas(**COUNCIL_KW, thumbnails=paths)
    assert Image.open(BytesIO(with_names)).size == (CANVAS_WIDTH, CANVAS_HEIGHT)
    # The labels must actually reach the canvas, not just be accepted as a kwarg.
    assert with_names != without


def test_a_portrait_that_fails_to_resolve_takes_its_label_with_it():
    # The row is positional: labels are indexed against paths, so a persona whose
    # portrait is missing must drop out of BOTH lists or every later name lands
    # under the wrong face. This asserts the two-name row differs from the row
    # where only the first name is supplied.
    _require_fonts()
    paths = _portraits("socrates", "marcus_aurelius")
    both = _render_reflection_canvas(
        **COUNCIL_KW, thumbnails=paths, thumbnail_labels=["Socrates", "Marcus Aurelius"]
    )
    first_only = _render_reflection_canvas(
        **COUNCIL_KW, thumbnails=paths, thumbnail_labels=["Socrates"]
    )
    assert both != first_only


def test_a_long_name_falls_back_to_its_surname():
    # Measured against the bundled Cormorant Medium at label size, not assumed:
    # these three of the eleven live personas overrun the 166px circle+gap budget.
    # The fallback is what keeps two adjacent labels from touching.
    _require_fonts()
    assert _fit_thumbnail_label("Miyamoto Musashi") == "Musashi"
    assert _fit_thumbnail_label("Simone de Beauvoir") == "Beauvoir"
    assert _fit_thumbnail_label("Niccolo Machiavelli") == "Machiavelli"


def test_names_that_fit_are_left_whole():
    # "Marcus Aurelius" measures 155px against the 166px budget, so it renders in
    # full — the fallback triggers on measurement, never on word count. (The brief
    # assumed this one would truncate; it does not at this size.)
    _require_fonts()
    assert _fit_thumbnail_label("Marcus Aurelius") == "Marcus Aurelius"
    assert _fit_thumbnail_label("George Orwell") == "George Orwell"
    assert _fit_thumbnail_label("Socrates") == "Socrates"


def test_every_live_persona_name_fits_after_the_fallback():
    # The row is only safe if EVERY name the council can seat fits once resolved.
    _require_fonts()
    font = _load_font("CormorantGaramond-Medium.ttf", REFLECT_THUMB_LABEL_FONT_SIZE)
    for name in [
        "Carl Jung", "Epictetus", "George Orwell", "Lao Tzu", "Marcus Aurelius",
        "Miyamoto Musashi", "Niccolo Machiavelli", "Oscar Wilde", "Sigmund Freud",
        "Simone de Beauvoir", "Socrates",
    ]:
        label = _fit_thumbnail_label(name)
        assert font.getlength(label) <= REFLECT_THUMB_LABEL_MAX_WIDTH, name


def test_a_single_long_name_with_no_surname_is_still_returned():
    # Nothing to fall back to — draw it rather than dropping the label. Better a
    # tight fit than a nameless portrait.
    assert _fit_thumbnail_label("Wollstonecraft") == "Wollstonecraft"


def test_a_blank_label_is_skipped_not_drawn_as_empty():
    assert _fit_thumbnail_label("") is None
    assert _fit_thumbnail_label(None) is None


def test_the_display_date_format_is_the_agreed_one():
    assert _format_date(datetime(2026, 8, 24)) == "24 Aug 2026"


def test_format_date_is_the_only_date_helper_the_canvas_can_reach():
    """Every card on this canvas — line, mirror, letter, council — shows one date
    format. Asserted by walking the function's AST rather than by rendering,
    because two date helpers produce different pixels but equally valid PNGs, so a
    render smoke cannot tell them apart.

    The docstring is deliberately excluded from the scan: it names the removed
    helper as history, and a raw text search cannot tell prose from a call. The
    claim here is about reachable CODE.

    Replaces test_the_other_cards_keep_the_us_date_in_this_pr, whose own docstring
    named this change as its successor.
    """
    src = (Path(__file__).resolve().parents[2] / "services" / "image_service.py").read_text(encoding="utf-8")
    fn = next(
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef) and n.name == "_render_reflection_canvas"
    )
    called = {
        n.func.id for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    referenced = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert "_format_date" in called
    assert "_format_date_us" not in called, "the canvas still calls the US date helper"
    assert "use_display_date" not in referenced, "the per-caller date switch is back"


def test_the_us_date_helper_is_gone_from_the_module():
    src = (Path(__file__).resolve().parents[2] / "services" / "image_service.py").read_text(encoding="utf-8")
    assert "def _format_date_us" not in src


def test_the_dead_citation_and_qr_params_are_gone_from_the_canvas():
    """attribution / show_qr had zero call sites for their whole life. The quote
    card's own QR lives in _render_quote_card and keeps REFLECT_QR_PATH/SIZE, so
    this asserts the canvas is clean WITHOUT asserting the constants are gone."""
    sig = inspect.signature(_render_reflection_canvas).parameters
    assert "attribution" not in sig
    assert "show_qr" not in sig
    assert "use_display_date" not in sig
    # Still live, and still needed by the quote card:
    from services.image_service import REFLECT_QR_PATH, REFLECT_QR_SIZE  # noqa: F401


def test_the_non_council_cards_are_byte_identical_without_the_new_params():
    # The whole safety argument for opt-in params, asserted: the line card with
    # no new arguments renders exactly as it did before.
    _require_fonts()
    baseline = _render()
    assert _render(theme=None, thumbnail_labels=None) == baseline


def test_the_theme_eyebrow_is_renderable():
    """The theme line must not use _letterspace's default separator.

    That default is U+2009 THIN SPACE. Lora-Regular has no glyph for it and draws
    a tofu box, so the first rendered sample came out as
    "L#E#A#V#I#N#G# #A# #S#T#A#B#L#E# #J#O#B". Every PNG-bytes assertion in this
    file passed while that was on screen — bytes-valid is not the same as legible,
    which is the whole reason this test measures glyphs instead.
    """
    _require_fonts()
    font = _load_font("Lora-Regular.ttf", COUNCIL_THEME_FONT_SIZE)
    thin = chr(0x2009)
    assert font.getmask(thin).getbbox() is not None, (
        "U+2009 now renders blank in Lora — the hazard this test guards is gone"
    )
    assert font.getmask(" ").getbbox() is None
    src = (Path(__file__).resolve().parents[2] / "services" / "image_service.py").read_text(encoding="utf-8")
    call = [ln for ln in src.splitlines() if "_letterspace(theme" in ln]
    assert call, "the theme _letterspace call moved"
    assert thin not in call[0], "the theme eyebrow passes the tofu-rendering thin space"
    assert call[0].rstrip().endswith('" "),'), "the theme eyebrow must pass an explicit U+0020"


def test_the_letterspace_default_is_renderable():
    """The DEFAULT separator must be a glyph Lora can draw invisibly.

    Measured against the live default via inspect.signature — NOT against a
    hardcoded " " — so reverting the default to U+2009 fails here instead of
    shipping tofu. U+2009 was the default until 2026-08-24: Lora-Regular has no
    glyph for it and drew a visible box between every character, which is what the
    season card's eyebrow rendered as for its whole life. The three counterview
    call sites and the council theme line escaped it only by passing an explicit
    " " that overrode the default.
    """
    _require_fonts()
    default_sep = inspect.signature(_letterspace).parameters["sp"].default
    assert _letterspace("AB") == "A" + default_sep + "B"
    for font_name, size in (
        ("Lora-Regular.ttf", SEASON_EYEBROW_FONT_SIZE),
        ("Lora-Regular.ttf", COUNCIL_THEME_FONT_SIZE),
    ):
        font = _load_font(font_name, size)
        assert font.getmask(default_sep).getbbox() is None, (
            f"{font_name}@{size} draws the _letterspace default separator "
            f"(U+{ord(default_sep):04X}) as a visible box — it will tofu every eyebrow"
        )


def test_the_season_eyebrow_renders_without_tofu():
    """The call site this fix was raised for. It passes NO separator, so it is the
    one that inherits the default — which is the whole point of fixing the default
    rather than the call site."""
    _require_fonts()
    eyebrow = _letterspace("SEASON . AUGUST 2026")
    font = _load_font("Lora-Regular.ttf", SEASON_EYEBROW_FONT_SIZE)
    for ch in set(eyebrow):
        mask = font.getmask(ch).getbbox()
        if ch.isspace():
            assert mask is None, f"whitespace {hex(ord(ch))} renders as a visible box"
        else:
            assert mask is not None, f"{ch!r} renders as nothing"


def test_the_season_card_renders():
    _require_fonts()
    png = _render_season_card(
        title="The month you stopped bracing",
        quote="You have been holding a door shut that no one was pushing on.",
        period_label="August 2026",
        created_at=datetime(2026, 8, 24),
    )
    assert png.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10]))  # PNG magic
    assert Image.open(BytesIO(png)).size == (CANVAS_WIDTH, CANVAS_HEIGHT)
