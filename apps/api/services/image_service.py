"""
Server-side share image generation.

Produces a 1080×1350 PNG (4:5 portrait) with persona portrait, italic quote,
and app branding. All assets are bundled in apps/api/static/ — no network calls
at render time.

Layout (portrait y=120, 38px quote font, 8-line max):
  Portrait circle   : top=120, center_x=540, diameter=200  (bottom=320)
  Intro text        : baseline y=380
  Quote             : starts y=440, line_h=53px, max 8 lines (bottom≤864)
  Footer top        : y=1130  (CANVAS_HEIGHT − 50 − 170)
  Divider           : y=1180  (footer_top + 50)
  Attribution       : baseline y=1208  (footer_top + 78)
  Wordmark          : baseline y=1248  (footer_top + 118)
  URL               : baseline y=1280  (footer_top + 150, Lora 14px, bronze 60%)
  Date              : baseline y=1300  (footer_top + 170, Lora 12px, bronze 50%)
"""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import SavedLine, Message, Persona

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"
FONTS_DIR = STATIC_DIR / "fonts"
PERSONAS_DIR = STATIC_DIR / "personas"

CANVAS_WIDTH  = 1080
CANVAS_HEIGHT = 1350

BG_COLOR        = (239, 227, 204)          # Vellum #EFE3CC
INK_COLOR       = (26,  26,  26)           # #1A1A1A
BRONZE_COLOR    = (184, 153, 104)          # #B89968
BRONZE_60_COLOR = (184, 153, 104, 153)     # Bronze 60% opacity — URL
BRONZE_50_COLOR = (184, 153, 104, 128)     # Bronze 50% opacity — date
WHITE_COLOR     = (255, 255, 255)

PORTRAIT_DIAMETER = 200
PORTRAIT_TOP      = 120
PORTRAIT_CENTER_X = CANVAS_WIDTH // 2     # 540

INTRO_BASELINE_Y  = 380
INTRO_FONT_SIZE   = 32

QUOTE_START_Y     = 440
QUOTE_MAX_WIDTH   = 880

DIVIDER_WIDTH     = 120

FOOTER_BOTTOM_PADDING = 50
FOOTER_BLOCK_HEIGHT   = 170
FOOTER_TOP_Y          = CANVAS_HEIGHT - FOOTER_BOTTOM_PADDING - FOOTER_BLOCK_HEIGHT  # 1130

DIVIDER_Y           = FOOTER_TOP_Y + 50   # 1180
ATTR_BASELINE_Y     = FOOTER_TOP_Y + 78   # 1208
ATTR_FONT_SIZE      = 22

WORDMARK_BASELINE_Y = FOOTER_TOP_Y + 118  # 1248
WORDMARK_FONT_SIZE  = 24

URL_BASELINE_Y      = FOOTER_TOP_Y + 150  # 1280
URL_FONT_SIZE       = 14
URL_TEXT            = "thegreatminds.app"

DATE_BASELINE_Y     = FOOTER_TOP_Y + 170  # 1300
DATE_FONT_SIZE      = 12


def dynamic_font_size(char_count: int) -> float:
    MIN_CHARS, MAX_CHARS = 15, 350
    MAX_SIZE, MIN_SIZE = 64.0, 28.0
    clamped = max(MIN_CHARS, min(MAX_CHARS, char_count))
    return MAX_SIZE + (MIN_SIZE - MAX_SIZE) * (clamped - MIN_CHARS) / (MAX_CHARS - MIN_CHARS)


def _strip_emoji(text: str) -> str:
    import emoji as _emoji_lib
    return _emoji_lib.replace_emoji(text, replace='').strip()


async def generate_share_image(
    db: AsyncSession,
    saved_line_id: str,
    user_id: str,
    annotation: str | None = None,
) -> bytes:
    """
    Load saved line data from DB, verify ownership, compose image.
    Returns raw PNG bytes.
    Raises ValueError if the saved line is not found or not owned by user_id.
    Raises RuntimeError if a required font file is missing.
    """
    # Load saved line + verify ownership
    sl_result = await db.execute(
        select(SavedLine).where(
            SavedLine.id == saved_line_id,
            SavedLine.user_id == user_id,
            SavedLine.deleted_at.is_(None),
        )
    )
    saved_line = sl_result.scalar_one_or_none()
    if not saved_line:
        raise ValueError("Saved line not found")

    # Load message content
    msg_result = await db.execute(
        select(Message).where(Message.id == saved_line.message_id)
    )
    msg = msg_result.scalar_one_or_none()
    if not msg:
        raise ValueError("Source message not found")

    # Load persona
    persona_result = await db.execute(
        select(Persona).where(Persona.id == saved_line.persona_id)
    )
    persona = persona_result.scalar_one()

    # Resolve portrait path (DB stores "/personas/filename.ext")
    portrait_path: Path | None = None
    if persona.portrait_url:
        filename = persona.portrait_url.lstrip("/").removeprefix("personas/")
        candidate = PERSONAS_DIR / filename
        if candidate.exists():
            portrait_path = candidate
        else:
            logger.warning(
                f"Portrait file not found for {persona.slug}: {candidate}. Using initial avatar."
            )

    clean_annotation = _strip_emoji(annotation) if annotation else None
    return _compose_canvas(
        quote=msg.content,
        persona_name=persona.name,
        portrait_path=portrait_path,
        saved_at=saved_line.saved_at,
        annotation=clean_annotation or None,
    )


def _format_date(dt: datetime) -> str:
    """Format as 'D MMM YYYY' — no leading zero on day (e.g. '1 May 2026')."""
    return f"{dt.day} {dt.strftime('%b %Y')}"


def _compose_canvas(
    quote: str,
    persona_name: str,
    portrait_path: Path | None,
    saved_at: datetime | None = None,
    annotation: str | None = None,
) -> bytes:
    quote_font_size = round(dynamic_font_size(len(quote)))
    quote_line_h    = round(quote_font_size * 1.4)
    quote_max_lines = max(4, round(8 * (38 / quote_font_size)))

    # Load fonts — fail loud if missing (deploy-time misconfiguration)
    font_medium_intro = _load_font("CormorantGaramond-Medium.ttf", INTRO_FONT_SIZE)
    font_italic_quote = _load_font("CormorantGaramond-Italic.ttf", quote_font_size)
    font_medium_attr  = _load_font("CormorantGaramond-Medium.ttf", ATTR_FONT_SIZE)
    font_italic_word  = _load_font("CormorantGaramond-Italic.ttf", WORDMARK_FONT_SIZE)
    font_lora_url     = _load_font("Lora-Regular.ttf", URL_FONT_SIZE)
    font_lora_date    = _load_font("Lora-Regular.ttf", DATE_FONT_SIZE)

    # Create canvas
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))
    draw = ImageDraw.Draw(canvas)

    # Portrait
    if portrait_path:
        _draw_circular_portrait(canvas, draw, portrait_path)
    else:
        _draw_initial_avatar(canvas, draw, persona_name[0].upper())

    # "{Persona Name} told me:"
    intro_text = f"{persona_name} told me:"
    draw.text(
        (PORTRAIT_CENTER_X, INTRO_BASELINE_Y),
        intro_text,
        font=font_medium_intro,
        fill=INK_COLOR,
        anchor="ms",  # middle-baseline
    )

    # Quote (wrapped, dynamic font size and line count)
    lines = _wrap_text(quote, font_italic_quote, QUOTE_MAX_WIDTH, quote_max_lines)
    for i, line in enumerate(lines):
        y = QUOTE_START_Y + i * quote_line_h
        draw.text(
            (PORTRAIT_CENTER_X, y),
            line,
            font=font_italic_quote,
            fill=INK_COLOR,
            anchor="mt",  # middle-top
        )

    # Annotation (user-authored caption in the gap zone between quote and footer)
    if annotation:
        ANNOTATION_FONT_SIZE = 22
        ANNOTATION_LINE_H    = round(ANNOTATION_FONT_SIZE * 1.4)
        ANNOTATION_MAX_LINES = 3
        ANNOTATION_Y         = 960

        font_lora_annotation = _load_font("Lora-Regular.ttf", ANNOTATION_FONT_SIZE)
        annotation_text      = f'“{annotation}”'
        annotation_lines     = _wrap_text(annotation_text, font_lora_annotation, QUOTE_MAX_WIDTH, ANNOTATION_MAX_LINES)
        for i, line in enumerate(annotation_lines):
            y = ANNOTATION_Y + i * ANNOTATION_LINE_H
            draw.text(
                (PORTRAIT_CENTER_X, y),
                line,
                font=font_lora_annotation,
                fill=BRONZE_COLOR,
                anchor="mt",
            )

    # Bronze divider
    x0 = PORTRAIT_CENTER_X - DIVIDER_WIDTH // 2
    x1 = PORTRAIT_CENTER_X + DIVIDER_WIDTH // 2
    draw.line([(x0, DIVIDER_Y), (x1, DIVIDER_Y)], fill=BRONZE_COLOR, width=1)

    # "— PERSONA NAME" attribution
    attr_text = f"— {persona_name.upper()}"
    draw.text(
        (PORTRAIT_CENTER_X, ATTR_BASELINE_Y),
        attr_text,
        font=font_medium_attr,
        fill=BRONZE_COLOR,
        anchor="ms",
    )

    # "Great Minds" wordmark
    draw.text(
        (PORTRAIT_CENTER_X, WORDMARK_BASELINE_Y),
        "Great Minds",
        font=font_italic_word,
        fill=BRONZE_COLOR,
        anchor="ms",
    )

    # URL and date — rendered on a transparent overlay to support opacity
    overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    overlay_draw.text(
        (PORTRAIT_CENTER_X, URL_BASELINE_Y),
        URL_TEXT,
        font=font_lora_url,
        fill=BRONZE_60_COLOR,
        anchor="ms",
    )

    if saved_at is not None:
        date_str = _format_date(saved_at)
        overlay_draw.text(
            (PORTRAIT_CENTER_X, DATE_BASELINE_Y),
            date_str,
            font=font_lora_date,
            fill=BRONZE_50_COLOR,
            anchor="ms",
        )

    canvas = Image.alpha_composite(canvas, overlay)

    # Export as RGB PNG
    out = canvas.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / filename
    if not path.exists():
        raise RuntimeError(f"Required font missing: {path}")
    return ImageFont.truetype(str(path), size)


def _draw_circular_portrait(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    portrait_path: Path,
) -> None:
    r = PORTRAIT_DIAMETER // 2
    left = PORTRAIT_CENTER_X - r
    top = PORTRAIT_TOP

    try:
        portrait = Image.open(portrait_path).convert("RGBA")
        portrait = portrait.resize((PORTRAIT_DIAMETER, PORTRAIT_DIAMETER), Image.LANCZOS)
    except Exception as e:
        logger.warning(f"Could not open portrait {portrait_path}: {e}. Falling back to initial avatar.")
        _draw_initial_avatar(canvas, draw, "?")
        return

    # Circular mask
    mask = Image.new("L", (PORTRAIT_DIAMETER, PORTRAIT_DIAMETER), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([(0, 0), (PORTRAIT_DIAMETER - 1, PORTRAIT_DIAMETER - 1)], fill=255)

    portrait_rgba = Image.new("RGBA", (PORTRAIT_DIAMETER, PORTRAIT_DIAMETER), (0, 0, 0, 0))
    portrait_rgba.paste(portrait, (0, 0), mask)
    canvas.paste(portrait_rgba, (left, top), portrait_rgba)


def _draw_initial_avatar(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    letter: str,
) -> None:
    r = PORTRAIT_DIAMETER // 2
    left = PORTRAIT_CENTER_X - r
    top = PORTRAIT_TOP

    # Bronze filled circle
    draw.ellipse(
        [(left, top), (left + PORTRAIT_DIAMETER, top + PORTRAIT_DIAMETER)],
        fill=BRONZE_COLOR,
    )

    # White letter centered
    try:
        font = _load_font("CormorantGaramond-Medium.ttf", 96)
    except RuntimeError:
        return

    cx = PORTRAIT_CENTER_X
    cy = top + r
    draw.text((cx, cy), letter, font=font, fill=WHITE_COLOR, anchor="mm")


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    """
    Word-wrap text to fit max_width px. Returns ≤ max_lines lines.
    Last line is truncated with "…" if text overflows.
    """
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = (current + " " + word).strip()
        w = font.getlength(candidate)
        if w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            if len(lines) == max_lines:
                break
            current = word

    if current and len(lines) < max_lines:
        lines.append(current)

    # Truncate to max_lines with ellipsis on overflow
    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if lines and len(words) > 0:
        # Check if full text fit; if not, add ellipsis to last line
        full_rejoined = " ".join(lines)
        original = text.strip()
        if full_rejoined != original:
            last = lines[-1]
            # Trim last line to fit "…"
            ellipsis = "…"
            while last and font.getlength(last + ellipsis) > max_width:
                last = last.rsplit(" ", 1)[0]
            lines[-1] = last + ellipsis

    return lines
