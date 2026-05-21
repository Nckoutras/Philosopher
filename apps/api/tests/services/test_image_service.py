"""Tests for image_service.generate_share_image and helpers."""

import pytest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image, ImageFont

from services.image_service import (
    _wrap_text,
    _compose_canvas,
    FONTS_DIR,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
)


# ── _wrap_text ──────────────────────────────────────────────────────────────

def _dummy_font(size: int = 14):
    """Load a real font for pixel-accurate wrap tests."""
    path = FONTS_DIR / "CormorantGaramond-Italic.ttf"
    if not path.exists():
        pytest.skip("Font file not available in test env")
    return ImageFont.truetype(str(path), size)


def test_wrap_text_short_string_fits_one_line():
    font = _dummy_font(38)
    lines = _wrap_text("Short quote.", font, max_width=880, max_lines=8)
    assert len(lines) == 1
    assert lines[0] == "Short quote."
    assert not lines[0].endswith("…")


def test_wrap_text_truncates_at_max_lines_with_ellipsis():
    font = _dummy_font(38)
    # 300 words should exceed 8 lines at 880px
    long_text = " ".join(["word"] * 300)
    lines = _wrap_text(long_text, font, max_width=880, max_lines=8)
    assert len(lines) <= 8
    assert lines[-1].endswith("…")


def test_wrap_text_respects_max_width():
    font = _dummy_font(38)
    text = "The unexamined life is not worth living, and yet we spend most of our days in comfortable distraction."
    lines = _wrap_text(text, font, max_width=880, max_lines=8)
    for line in lines:
        # Each line should fit within max_width (with a small tolerance for ellipsis)
        assert font.getlength(line.rstrip("…")) <= 880 + 5


def test_wrap_text_single_word_per_line():
    font = _dummy_font(38)
    # Very narrow max_width forces one word per line
    lines = _wrap_text("one two three four", font, max_width=1, max_lines=8)
    # Each line should be a single word (no wrapping possible within 1px)
    assert all(len(line.split()) == 1 or line.endswith("…") for line in lines)


# ── _compose_canvas ─────────────────────────────────────────────────────────

def test_compose_canvas_returns_valid_png():
    if not (FONTS_DIR / "CormorantGaramond-Italic.ttf").exists():
        pytest.skip("Font files not available in test env")

    png_bytes = _compose_canvas(
        quote="The unexamined life is not worth living.",
        persona_name="Socrates",
        portrait_path=None,  # triggers initial-avatar fallback
    )
    assert isinstance(png_bytes, bytes)
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    assert len(png_bytes) > 20_000
    img = Image.open(BytesIO(png_bytes))
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_compose_canvas_with_portrait(tmp_path):
    if not (FONTS_DIR / "CormorantGaramond-Italic.ttf").exists():
        pytest.skip("Font files not available in test env")

    portrait = Image.new("RGB", (100, 100), (128, 64, 32))
    portrait_path = tmp_path / "test_portrait.png"
    portrait.save(str(portrait_path))

    png_bytes = _compose_canvas(
        quote="He who thinks great thoughts, often makes great errors.",
        persona_name="Heidegger",
        portrait_path=portrait_path,
    )
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    assert len(png_bytes) > 20_000
    img = Image.open(BytesIO(png_bytes))
    assert img.size == (CANVAS_WIDTH, CANVAS_HEIGHT)


def test_compose_canvas_byte_size_range():
    if not (FONTS_DIR / "CormorantGaramond-Italic.ttf").exists():
        pytest.skip("Font files not available in test env")

    png_bytes = _compose_canvas(
        quote="The unexamined life is not worth living.",
        persona_name="Socrates",
        portrait_path=None,
    )
    assert 15_000 < len(png_bytes) < 300_000


# ── generate_share_image ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_share_image_wrong_user_raises():
    """Saved line owned by different user → ValueError."""
    from services.image_service import generate_share_image

    mock_db = AsyncMock()
    # Simulate SavedLine not found (wrong user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ValueError, match="Saved line not found"):
        await generate_share_image(
            db=mock_db,
            saved_line_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000099",
        )
