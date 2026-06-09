"""Minimal smoke tests for the redesigned reflection share card.

Covers _render_reflection_canvas: renders without error, output is the
expected 1080×1350 PNG, and the hero-missing fallback still renders.
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from services import image_service
from services.image_service import (
    _render_reflection_canvas,
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
