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

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import CouncilCase, CouncilResponse, CouncilSession, Counterview, CounterviewResponse, Mirror, Quote, SavedLine, Message, Persona, WeeklyLetter
from text_utils import shorten_source

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"
FONTS_DIR = STATIC_DIR / "fonts"
PERSONAS_DIR = STATIC_DIR / "personas"
SHARE_DIR = STATIC_DIR / "share"
RITUALS_DIR = STATIC_DIR / "rituals"
HERO_PATH = SHARE_DIR / "wise-room-hero.webp"
MIRROR_HERO_PATH  = RITUALS_DIR / "mirror.webp"
COUNCIL_HERO_PATH = RITUALS_DIR / "boardroom.webp"
LETTER_HERO_PATH  = RITUALS_DIR / "sundayletter.png"
SEASON_HERO_PATH  = RITUALS_DIR / "seasonletter.png"   # pre-composed 1080×1350 monthly card base

CANVAS_WIDTH  = 1080
CANVAS_HEIGHT = 1350

BG_COLOR        = (239, 227, 204)          # Vellum #EFE3CC
INK_COLOR       = (31,  27,  20)           # #1F1B14
BRONZE_COLOR    = (184, 153, 104)          # #B89968
BRONZE_60_COLOR = (184, 153, 104, 230)     # Bronze 90% opacity — URL (PR4ag1)
BRONZE_50_COLOR = (184, 153, 104, 178)     # Bronze 70% opacity — date (PR4ag1)
WHITE_COLOR     = (255, 255, 255)

PORTRAIT_DIAMETER = 260
PORTRAIT_TOP      = 160
PORTRAIT_CENTER_X = CANVAS_WIDTH // 2     # 540

INTRO_BASELINE_Y  = 460
INTRO_FONT_SIZE   = 36

QUOTE_START_Y     = 520
QUOTE_MAX_WIDTH   = 880

DIVIDER_WIDTH     = 120

FOOTER_BOTTOM_PADDING = 50
FOOTER_BLOCK_HEIGHT   = 170
FOOTER_TOP_Y          = CANVAS_HEIGHT - FOOTER_BOTTOM_PADDING - FOOTER_BLOCK_HEIGHT  # 1130

DIVIDER_Y           = FOOTER_TOP_Y + 50   # 1180
ATTR_BASELINE_Y     = FOOTER_TOP_Y + 78   # 1208
ATTR_FONT_SIZE      = 22

WORDMARK_BASELINE_Y = FOOTER_TOP_Y + 118  # 1248
WORDMARK_FONT_SIZE  = 30

URL_BASELINE_Y      = FOOTER_TOP_Y + 150  # 1280
URL_FONT_SIZE       = 18
URL_TEXT            = "thewiseroom.app"

DATE_BASELINE_Y     = FOOTER_TOP_Y + 170  # 1300
DATE_FONT_SIZE      = 16


# ── Season (monthly) share card ───────────────────────────────────────────────
# Text drawn into the lower Vellum zone of the pre-composed seasonletter.png
# (the framed brand photo occupies the upper ~58%; text zone starts ~y810).
# All centered on x=540. Positions are tunable; the quote line-count is bounded
# at render time so it can never cross into the footer band.
SEASON_TEXT_MAX_WIDTH     = 840
SEASON_EYEBROW_FONT_SIZE  = 22
SEASON_EYEBROW_BASELINE_Y = 856
SEASON_TITLE_FONT_SIZE    = 50
SEASON_TITLE_TOP_Y        = 892
SEASON_TITLE_LINE_H       = 60
SEASON_TITLE_MAX_LINES    = 2
SEASON_DIVIDER_WIDTH      = 120
SEASON_DIVIDER_GAP        = 26
SEASON_QUOTE_FONT_SIZE    = 32
SEASON_QUOTE_LINE_H       = 46
SEASON_QUOTE_MAX_LINES    = 6
SEASON_QUOTE_FLOOR_Y      = 1212   # quote must end above this (footer band below)
SEASON_FOOTER_WORDMARK_Y  = 1252
SEASON_FOOTER_URL_Y       = 1286
SEASON_FOOTER_DATE_Y      = 1314


# ── Reflection card (redesigned PR4ah) ───────────────────────────────────────
# Top→bottom: faint hero bg · "The Wise Room" · date · portrait · "{Persona}
# told me" · auto-fit reflection (vertically centred in the leftover band) ·
# bold "thewiseroom.app" stamp. Council uses the legacy layout above.
REFLECT_HERO_OPACITY     = 0.06          # tunable — founder picks from samples

REFLECT_WORDMARK_BASELINE_Y = 88
REFLECT_WORDMARK_FONT_SIZE  = 36

REFLECT_DATE_BASELINE_Y  = 128
REFLECT_DATE_FONT_SIZE   = 22

REFLECT_PORTRAIT_DIAMETER = round(PORTRAIT_DIAMETER * 1.1)  # 260 → 286 (10% larger)
REFLECT_PORTRAIT_TOP      = 176

REFLECT_INTRO_BASELINE_Y = 530
REFLECT_INTRO_FONT_SIZE  = 38

# Reflection block lives in the band between the intro and the bottom stamp.
REFLECT_BAND_TOP    = 576
REFLECT_BAND_BOTTOM = 1232
REFLECT_QUOTE_MAX_WIDTH = 880
REFLECT_QUOTE_MAX_SIZE  = 76
REFLECT_QUOTE_MIN_SIZE  = 30
REFLECT_QUOTE_LINE_RATIO = 1.38

REFLECT_STAMP_BASELINE_Y = 1296
REFLECT_STAMP_FONT_SIZE  = 30
REFLECT_STAMP_TEXT       = "thewiseroom.app"

# Ritual share cards (Mirror / Council) reuse the reflection layout with a
# photographic ritual hero behind everything. Those backgrounds are busier than
# the chesterfield texture, so they start fainter (founder tunes from preview).
REFLECT_HERO_OPACITY_RITUAL = 0.10

# Council card: a centred row of the participating personas' portraits replaces
# the single host portrait. Sized + vertically centred to occupy the same band
# as the single portrait (top 176 → bottom 462, centre y ≈ 319).
REFLECT_THUMB_DIAMETER = 140
REFLECT_THUMB_GAP      = 26
REFLECT_THUMB_CENTER_Y = REFLECT_PORTRAIT_TOP + REFLECT_PORTRAIT_DIAMETER // 2  # 319

# Council card only — the prestige mechanism was implicit while the portraits were
# unnamed. Names sit in the clear band between the circles (bottom edge 389) and
# the "The Council" intro baseline (530).
REFLECT_THUMB_LABEL_BASELINE_Y = 416
REFLECT_THUMB_LABEL_FONT_SIZE  = 24
# A label may use its own circle plus one gap; beyond that two names touch.
REFLECT_THUMB_LABEL_MAX_WIDTH  = REFLECT_THUMB_DIAMETER + REFLECT_THUMB_GAP  # 166

# Council card only — the theme line sits directly above the verdict, so the quote
# band starts lower than REFLECT_BAND_TOP (576) to make room. The quote auto-fits,
# so it simply renders a little smaller; no other card passes band_top.
COUNCIL_THEME_BASELINE_Y = 572
COUNCIL_THEME_FONT_SIZE  = 25
COUNCIL_BAND_TOP         = 620

# Quote share card extends the reflection layout with two optional elements that
# only render when their params are set (show_qr / attribution) — every existing
# caller passes neither, so all current cards stay byte-identical:
#   · a small "— {Name}, {Source}" citation below the quote, and
#   · a centred QR above the bottom stamp (scan → thewiseroom.app).
# When either is present the auto-fit quote band ends higher (REFLECT_QR_BAND_BOTTOM)
# so the quote can never run into the citation / QR / stamp band.
REFLECT_QR_PATH         = SHARE_DIR / "qr-wiseroom.png"
REFLECT_QR_SIZE         = 110
REFLECT_QR_BOTTOM_Y     = 1258   # QR bottom edge (top = 1148), sits above the stamp
REFLECT_QR_BAND_BOTTOM  = 1060   # quote band floor when citation / QR present
REFLECT_ATTR_BASELINE_Y = 1120   # "— {Name}, {Source}" citation baseline
REFLECT_ATTR_FONT_SIZE  = 26
REFLECT_ATTR_MIN_SIZE   = 18     # shrink-to-fit floor for a long name+source


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

    # Annotation is intentionally dropped from the redesigned reflection card
    # (kept clean / reflection-focused). The `annotation` arg is still accepted
    # for API compatibility but no longer rendered.
    return _render_reflection_canvas(
        quote=msg.content,
        portrait_path=portrait_path,
        persona_initial=persona.name[0].upper(),
        intro_text=f"{persona.name} told me",
        saved_at=saved_line.saved_at,
    )


async def generate_quote_share_image(
    db: AsyncSession,
    quote_id: str,
    user_id: str,
) -> bytes:
    """
    Compose a share card for a corpus Quote: a full-bleed graded persona portrait
    under a dark scrim, the quote anchored low, its original-language phrase, a
    "— {Name}, {Source}" citation, and a QR (scan → thewiseroom.app) above the
    stamp — a server-side mirror of the carousel QuoteCard. Returns raw PNG bytes.

    `user_id` is accepted for call-site parity with the other generators (the
    router already enforced auth + rate limit); quotes are global, not user-owned.
    Raises ValueError if the quote is unknown or inactive.
    """
    quote = (
        await db.execute(
            select(Quote).where(Quote.id == quote_id, Quote.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if quote is None:
        raise ValueError("Quote not found")

    persona = (
        await db.execute(select(Persona).where(Persona.slug == quote.persona_slug))
    ).scalar_one_or_none()
    name = persona.name if persona else quote.persona_slug

    return _render_quote_card(
        quote_en=quote.text_en,
        quote_original=quote.text_original,
        portrait_path=_resolve_portrait_path(persona),
        persona_name=name,
        source_short=shorten_source(quote.source_locator),
    )


async def generate_council_share_image(
    *,
    db: AsyncSession,
    session_id: str,
    user_id: str,
    annotation: str | None = None,
) -> bytes:
    """
    Load council session, verify ownership and synthesis presence, compose image.
    Returns raw PNG bytes.
    Raises ValueError if session not found, not owned by user_id, or has no synthesis.
    """
    result = await db.execute(
        select(CouncilSession)
        .join(CouncilCase, CouncilSession.case_id == CouncilCase.id)
        .where(
            CouncilSession.id == session_id,
            CouncilCase.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session or not session.synthesis:
        raise ValueError("Council session not found or has no synthesis")

    # Participating personas (in seat order), de-duplicated, capped at 4.
    resp_result = await db.execute(
        select(CouncilResponse.persona_slug)
        .where(CouncilResponse.session_id == session_id)
        .order_by(CouncilResponse.position)
    )
    slugs: list[str] = []
    for slug in resp_result.scalars().all():
        if slug not in slugs:
            slugs.append(slug)
    slugs = slugs[:4]

    # Portraits and names are collected together and appended together, so a
    # persona whose portrait file is missing drops out of BOTH lists and the row
    # stays aligned — a name under the wrong face is worse than no names at all.
    thumbnails: list[Path] = []
    thumbnail_labels: list[str] = []
    if slugs:
        p_result = await db.execute(select(Persona).where(Persona.slug.in_(slugs)))
        by_slug = {p.slug: p for p in p_result.scalars().all()}
        for slug in slugs:
            persona = by_slug.get(slug)
            path = _resolve_portrait_path(persona)
            if path:
                thumbnails.append(path)
                thumbnail_labels.append(persona.name if persona else "")

    # The neutral context line. Read defensively: synthesis_structured is JSONB and
    # every session synthesised before this shipped simply has no `theme` key, so
    # the card must render without one. _clean_field already guarantees it is a
    # non-empty string or None when present.
    structured = session.synthesis_structured or {}
    theme = structured.get("theme") if isinstance(structured, dict) else None

    # `annotation` is accepted for API compatibility but, like the line card, the
    # redesigned ritual card no longer renders it.
    return _render_reflection_canvas(
        quote=session.synthesis,
        portrait_path=None,
        persona_initial=None,
        intro_text="The Council",
        saved_at=session.created_at,
        hero_opacity=REFLECT_HERO_OPACITY_RITUAL,
        hero_path=COUNCIL_HERO_PATH,
        thumbnails=thumbnails or None,
        thumbnail_labels=thumbnail_labels or None,
        theme=theme,
        band_top=COUNCIL_BAND_TOP if theme else None,
        use_display_date=True,
    )


async def generate_mirror_share_image(
    *,
    db: AsyncSession,
    mirror_id: str,
    user_id: str,
) -> bytes:
    """
    Load a mirror, verify ownership, and compose a share card from its closing
    reflection (payload.thread) over a faint mirror hero. Returns raw PNG bytes.
    Raises ValueError if the mirror is not found, not owned, or has no thread.
    """
    result = await db.execute(
        select(Mirror).where(Mirror.id == mirror_id, Mirror.user_id == user_id)
    )
    mirror = result.scalar_one_or_none()
    if mirror is None:
        raise ValueError("Mirror not found")

    thread = (mirror.payload or {}).get("thread")
    if not thread:
        raise ValueError("Mirror has no reflection to share")

    # Host persona (portrait + name) — optional; the mirror may be host-less.
    persona: Persona | None = None
    if mirror.host_persona_id:
        persona_result = await db.execute(
            select(Persona).where(Persona.id == mirror.host_persona_id)
        )
        persona = persona_result.scalar_one_or_none()

    portrait_path = _resolve_portrait_path(persona)
    intro_text = f"{persona.name} reflects" if persona else "The mirror reflects"

    return _render_reflection_canvas(
        quote=thread,
        portrait_path=portrait_path,
        persona_initial=(persona.name[0].upper() if persona else None),
        intro_text=intro_text,
        saved_at=mirror.created_at,
        hero_opacity=REFLECT_HERO_OPACITY_RITUAL,
        hero_path=MIRROR_HERO_PATH,
    )


async def generate_letter_share_image(
    *,
    db: AsyncSession,
    weekly_letter_id: str,
    user_id: str,
) -> bytes:
    """
    Load a Sunday Letter, verify ownership, and compose a share card from its
    pull_quote over a faint wax-seal hero. Returns raw PNG bytes.
    Raises ValueError if the letter is not found, not owned, not generated, or
    has no pull_quote.
    """
    result = await db.execute(
        select(WeeklyLetter).where(
            WeeklyLetter.id == weekly_letter_id,
            WeeklyLetter.user_id == user_id,
        )
    )
    letter = result.scalar_one_or_none()
    if letter is None or letter.status != "generated":
        raise ValueError("Letter not found")

    pull_quote = (letter.payload or {}).get("pull_quote")
    if not pull_quote:
        raise ValueError("Letter has no quote to share")

    title = (letter.payload or {}).get("title") or "The Sunday Letter"

    # Monthly 'season' letters get a distinct full-strength branded card built on
    # the pre-composed seasonletter.png (no ghosted hero, no persona portrait).
    if letter.kind == "monthly":
        return _render_season_card(
            title=(letter.payload or {}).get("title") or "A Season",
            quote=pull_quote,
            period_label=letter.period_start.strftime("%B %Y"),
            created_at=letter.created_at,
        )

    # Voice persona (portrait + name) — optional; the letter may be voice-less.
    persona: Persona | None = None
    if letter.voice_persona_id:
        persona_result = await db.execute(
            select(Persona).where(Persona.id == letter.voice_persona_id)
        )
        persona = persona_result.scalar_one_or_none()

    portrait_path = _resolve_portrait_path(persona)

    return _render_reflection_canvas(
        quote=pull_quote,
        portrait_path=portrait_path,
        persona_initial=(persona.name[0].upper() if persona else None),
        intro_text=title,
        saved_at=letter.created_at,
        hero_opacity=REFLECT_HERO_OPACITY_RITUAL,
        hero_path=LETTER_HERO_PATH,
    )


def _letterspace(s: str, sp: str = " ") -> str:
    """Light tracking for the eyebrow caps (Pillow has no native letter-spacing):
    join characters with a thin space."""
    return sp.join(list(s))


def _render_season_card(
    *,
    title: str,
    quote: str,
    period_label: str,
    created_at: datetime,
) -> bytes:
    """Monthly 'season' share card (1080×1350). Draws the season eyebrow, title,
    a bronze divider, the keepsake quote, and the branding footer into the lower
    Vellum zone of the pre-composed, FULL-STRENGTH seasonletter.png base (the
    framed brand photo is already part of that asset). No ghosting, no portrait.
    Falls back to plain Vellum if the asset is missing so it never 500s."""
    if SEASON_HERO_PATH.exists():
        try:
            canvas = Image.open(SEASON_HERO_PATH).convert("RGBA")
            if canvas.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
                canvas = canvas.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.LANCZOS)
        except Exception as e:
            logger.warning(f"Could not open season hero {SEASON_HERO_PATH}: {e}. Plain Vellum.")
            canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))
    else:
        logger.warning(f"Season hero missing: {SEASON_HERO_PATH}. Plain Vellum.")
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))

    draw = ImageDraw.Draw(canvas)
    cx = PORTRAIT_CENTER_X  # 540

    font_eyebrow = _load_font("Lora-Regular.ttf", SEASON_EYEBROW_FONT_SIZE)
    font_title   = _load_font("CormorantGaramond-Medium.ttf", SEASON_TITLE_FONT_SIZE)
    font_quote   = _load_font("CormorantGaramond-Italic.ttf", SEASON_QUOTE_FONT_SIZE)
    font_word    = _load_font("CormorantGaramond-Italic.ttf", WORDMARK_FONT_SIZE)
    font_url     = _load_font("Lora-Regular.ttf", URL_FONT_SIZE)
    font_date    = _load_font("Lora-Regular.ttf", DATE_FONT_SIZE)

    # Eyebrow — "SEASON · MONTH YEAR", lightly tracked, bronze
    draw.text(
        (cx, SEASON_EYEBROW_BASELINE_Y),
        _letterspace(f"Season · {period_label}".upper()),
        font=font_eyebrow, fill=BRONZE_COLOR, anchor="ms",
    )

    # Title — Cormorant Medium, ink, wrapped & centered
    y = SEASON_TITLE_TOP_Y
    for line in _wrap_text(title, font_title, SEASON_TEXT_MAX_WIDTH, SEASON_TITLE_MAX_LINES):
        draw.text((cx, y), line, font=font_title, fill=INK_COLOR, anchor="mt")
        y += SEASON_TITLE_LINE_H

    # Bronze divider
    y += SEASON_DIVIDER_GAP
    draw.line(
        [(cx - SEASON_DIVIDER_WIDTH // 2, y), (cx + SEASON_DIVIDER_WIDTH // 2, y)],
        fill=BRONZE_COLOR, width=1,
    )
    y += SEASON_DIVIDER_GAP

    # Keepsake quote — Cormorant Italic, ink, wrapped; line count bounded so it
    # can never run into the footer band.
    remaining = SEASON_QUOTE_FLOOR_Y - y
    max_quote_lines = max(1, min(SEASON_QUOTE_MAX_LINES, remaining // SEASON_QUOTE_LINE_H))
    for line in _wrap_text(quote, font_quote, SEASON_TEXT_MAX_WIDTH, max_quote_lines):
        draw.text((cx, y), line, font=font_quote, fill=INK_COLOR, anchor="mt")
        y += SEASON_QUOTE_LINE_H

    # Branding footer — wordmark / url / date (bronze, centered)
    draw.text((cx, SEASON_FOOTER_WORDMARK_Y), "The Wise Room", font=font_word, fill=BRONZE_COLOR, anchor="ms")
    draw.text((cx, SEASON_FOOTER_URL_Y), URL_TEXT, font=font_url, fill=BRONZE_COLOR, anchor="ms")
    draw.text((cx, SEASON_FOOTER_DATE_Y), _format_date(created_at), font=font_date, fill=BRONZE_COLOR, anchor="ms")

    out = canvas.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _format_date(dt: datetime) -> str:
    """Format as 'D MMM YYYY' — no leading zero on day (e.g. '1 May 2026')."""
    return f"{dt.day} {dt.strftime('%b %Y')}"


def _render_share_canvas(
    *,
    quote: str,
    attribution: str,
    portrait_path: Path | None,
    persona_initial: str | None = None,
    intro_text: str | None = None,
    annotation: str | None = None,
    saved_at: datetime | None = None,
) -> bytes:
    # DEPRECATED (PR-29c): the legacy portrait-top layout. No longer called —
    # both the line card and the Council/Mirror ritual cards now render through
    # _render_reflection_canvas. Retained (with _format_date) for reference;
    # safe to delete in a cleanup PR.
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

    # Portrait — skip entirely when neither portrait_path nor persona_initial is set (council)
    if portrait_path:
        _draw_circular_portrait(canvas, draw, portrait_path)
    elif persona_initial is not None:
        _draw_initial_avatar(canvas, draw, persona_initial)

    # "{Persona Name} told me:" — omitted for council
    if intro_text:
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

    # Attribution line (e.g. "— PERSONA NAME" or "— THE COUNCIL")
    draw.text(
        (PORTRAIT_CENTER_X, ATTR_BASELINE_Y),
        attribution,
        font=font_medium_attr,
        fill=BRONZE_COLOR,
        anchor="ms",
    )

    # "The Wise Room" wordmark
    draw.text(
        (PORTRAIT_CENTER_X, WORDMARK_BASELINE_Y),
        "The Wise Room",
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
            fill=BRONZE_60_COLOR,
            anchor="ms",
        )

    canvas = Image.alpha_composite(canvas, overlay)

    # Export as RGB PNG
    out = canvas.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _format_date_us(dt: datetime) -> str:
    """Format as mm/dd/yyyy with leading zeros (e.g. '05/01/2026')."""
    return dt.strftime("%m/%d/%Y")


def _load_hero_cover(opacity: float, path: Path = HERO_PATH) -> Image.Image | None:
    """
    Load a hero asset, resize-to-cover the full canvas (center-crop), and knock
    its alpha down to `opacity` so it reads as a very faint texture. `path`
    defaults to the chesterfield hero (line card); Mirror/Council pass their own
    ritual heroes. Returns None if the asset is missing (card renders on plain
    Vellum).
    """
    if not path.exists():
        logger.warning(f"Hero background missing: {path}. Rendering on plain Vellum.")
        return None
    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:
        logger.warning(f"Could not open hero {path}: {e}. Rendering on plain Vellum.")
        return None

    target_ratio = CANVAS_WIDTH / CANVAS_HEIGHT
    w, h = img.size
    ratio = w / h
    if ratio > target_ratio:
        new_h = CANVAS_HEIGHT
        new_w = round(new_h * ratio)
    else:
        new_w = CANVAS_WIDTH
        new_h = round(new_w / ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - CANVAS_WIDTH) // 2
    top  = (new_h - CANVAS_HEIGHT) // 2
    img = img.crop((left, top, left + CANVAS_WIDTH, top + CANVAS_HEIGHT))

    # Uniform faintness: source is opaque, so scale alpha to opacity*255.
    alpha = img.getchannel("A").point(lambda a: round(a * opacity))
    img.putalpha(alpha)
    return img


def _wrap_all_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap to fit max_width px, returning every line (no truncation)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_reflection(
    quote: str,
    band_height: int,
    max_width: int,
    load_quote_font,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """
    Fit-to-fill: step from MAX down to MIN font size and pick the LARGEST size
    whose fully-wrapped block fits inside band_height. Short reflections render
    big; long ones shrink. If nothing fits even at MIN, fall back to MIN with
    ellipsis-truncated wrapping. Returns (font, lines, line_height).
    """
    for size in range(REFLECT_QUOTE_MAX_SIZE, REFLECT_QUOTE_MIN_SIZE - 1, -1):
        font = load_quote_font(size)
        line_h = round(size * REFLECT_QUOTE_LINE_RATIO)
        lines = _wrap_all_lines(quote, font, max_width)
        if len(lines) * line_h <= band_height:
            return font, lines, line_h

    # Overflow at MIN size — truncate to the lines that fit, with ellipsis.
    size = REFLECT_QUOTE_MIN_SIZE
    font = load_quote_font(size)
    line_h = round(size * REFLECT_QUOTE_LINE_RATIO)
    max_lines = max(1, band_height // line_h)
    lines = _wrap_text(quote, font, max_width, max_lines)
    return font, lines, line_h


def _render_reflection_canvas(
    *,
    quote: str,
    portrait_path: Path | None,
    persona_initial: str | None,
    intro_text: str,
    saved_at: datetime | None,
    hero_opacity: float = REFLECT_HERO_OPACITY,
    hero_path: Path = HERO_PATH,
    thumbnails: list[Path] | None = None,
    attribution: str | None = None,
    show_qr: bool = False,
    thumbnail_labels: list[str] | None = None,
    theme: str | None = None,
    band_top: int | None = None,
    use_display_date: bool = False,
) -> bytes:
    """
    Redesigned reflection share card (1080×1350). Faint hero behind everything;
    "The Wise Room" + date pinned top; 10%-larger portrait; intro line; the
    reflection auto-fit and vertically centred in the leftover band; bold
    "thewiseroom.app" stamp at the bottom.

    Ritual cards reuse this layout: `hero_path` swaps the chesterfield for a
    ritual hero, and `thumbnails` (Council) replaces the single portrait with a
    centred row of participating-persona portraits.

    The quote share card adds `attribution` (a "— {Name}, {Source}" citation drawn
    below the quote) and `show_qr` (a centred QR above the stamp). When either is
    set the quote band ends higher so it can't collide with them. All three extras
    default to off, so every existing call site stays byte-stable.

    The Council card adds `thumbnail_labels` (persona names under the circles),
    `theme` (a neutral context line directly above the verdict), `band_top` (the
    quote band floor lowered to clear that line) and `use_display_date`
    ("24 Aug 2026" rather than the US format). These four default to off/None for
    the same reason: the line, mirror and letter cards share this canvas and must
    render byte-identically. `use_display_date` exists ONLY because the US format
    is still correct-by-default for those three until the date-format follow-up
    switches them too — it is not a preference, it is a scope boundary.
    """
    # Base canvas (Vellum) + faint hero composited over it.
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))
    hero = _load_hero_cover(hero_opacity, hero_path)
    if hero is not None:
        canvas = Image.alpha_composite(canvas, hero)
    draw = ImageDraw.Draw(canvas)

    # Fonts
    font_wordmark = _load_font("CormorantGaramond-Italic.ttf", REFLECT_WORDMARK_FONT_SIZE)
    font_date     = _load_font("Lora-Regular.ttf", REFLECT_DATE_FONT_SIZE)
    font_intro    = _load_font("CormorantGaramond-Medium.ttf", REFLECT_INTRO_FONT_SIZE)
    font_stamp    = _load_font("Lora-Regular.ttf", REFLECT_STAMP_FONT_SIZE)

    # 2. "The Wise Room" — pinned top
    draw.text(
        (PORTRAIT_CENTER_X, REFLECT_WORDMARK_BASELINE_Y),
        "The Wise Room",
        font=font_wordmark,
        fill=BRONZE_COLOR,
        anchor="ms",
    )

    # 3. Date — mm/dd/yyyy, or "24 Aug 2026" where the caller opts in (Council).
    if saved_at is not None:
        draw.text(
            (PORTRAIT_CENTER_X, REFLECT_DATE_BASELINE_Y),
            _format_date(saved_at) if use_display_date else _format_date_us(saved_at),
            font=font_date,
            fill=BRONZE_COLOR,
            anchor="ms",
        )

    # 4. Portrait — a single 10%-larger portrait, or (Council) a centred row of
    #    the participating personas' thumbnails in the same vertical band.
    if thumbnails:
        _draw_thumbnail_row(canvas, draw, thumbnails, labels=thumbnail_labels)
    elif portrait_path:
        _draw_circular_portrait(
            canvas, draw, portrait_path,
            diameter=REFLECT_PORTRAIT_DIAMETER, top=REFLECT_PORTRAIT_TOP,
        )
    elif persona_initial is not None:
        _draw_initial_avatar(
            canvas, draw, persona_initial,
            diameter=REFLECT_PORTRAIT_DIAMETER, top=REFLECT_PORTRAIT_TOP,
        )

    # 5. "{Persona} told me"
    draw.text(
        (PORTRAIT_CENTER_X, REFLECT_INTRO_BASELINE_Y),
        intro_text,
        font=font_intro,
        fill=INK_COLOR,
        anchor="ms",
    )

    # 5b. Theme — the Council card's context line, in the tracked bronze eyebrow
    #     treatment, sitting directly above the verdict. Drawn ONLY when the caller
    #     passes a non-empty string, so a session synthesised before this shipped
    #     (no `theme` key at all) renders exactly the card it rendered yesterday.
    if isinstance(theme, str) and theme.strip():
        draw.text(
            (PORTRAIT_CENTER_X, COUNCIL_THEME_BASELINE_Y),
            # Explicit U+0020 separator, as the counterview eyebrows do. NOT the
            # _letterspace default: that is U+2009 THIN SPACE, which Lora has no
            # glyph for and draws as a tofu box between every letter. A PNG-bytes
            # smoke test cannot see that — test_the_theme_eyebrow_is_renderable can.
            _letterspace(theme.strip().upper(), " "),
            font=_load_font("Lora-Regular.ttf", COUNCIL_THEME_FONT_SIZE),
            fill=BRONZE_COLOR,
            anchor="ms",
        )

    # 6. Reflection — auto-fit, vertically centred in the leftover band. When a
    #    citation or QR is present the band ends higher so the quote clears them.
    #    `band_top` lets the Council card start the band lower to clear its theme
    #    line; every other caller leaves it None and gets REFLECT_BAND_TOP.
    band_bottom = REFLECT_QR_BAND_BOTTOM if (show_qr or attribution) else REFLECT_BAND_BOTTOM
    band_start  = REFLECT_BAND_TOP if band_top is None else band_top
    band_height = band_bottom - band_start
    font_quote, lines, line_h = _fit_reflection(
        quote, band_height, REFLECT_QUOTE_MAX_WIDTH,
        lambda s: _load_font("CormorantGaramond-Italic.ttf", s),
    )
    block_h = len(lines) * line_h
    start_y = band_start + max(0, (band_height - block_h) // 2)
    for i, line in enumerate(lines):
        draw.text(
            (PORTRAIT_CENTER_X, start_y + i * line_h),
            line,
            font=font_quote,
            fill=INK_COLOR,
            anchor="mt",
        )

    # 6b. Citation — "— {Name}, {Source}" below the quote (quote card only). Shrunk
    #     to fit a single centred line so a long name+source never spills the width.
    if attribution:
        attr_size = REFLECT_ATTR_FONT_SIZE
        while attr_size > REFLECT_ATTR_MIN_SIZE and _load_font(
            "CormorantGaramond-Italic.ttf", attr_size
        ).getlength(attribution) > REFLECT_QUOTE_MAX_WIDTH:
            attr_size -= 2
        draw.text(
            (PORTRAIT_CENTER_X, REFLECT_ATTR_BASELINE_Y),
            attribution,
            font=_load_font("CormorantGaramond-Italic.ttf", attr_size),
            fill=BRONZE_COLOR,
            anchor="ms",
        )

    # 6c. QR — centred above the stamp (quote card only). Missing asset → skip the
    #     QR but keep the stamp, so the card never 500s.
    if show_qr:
        if REFLECT_QR_PATH.exists():
            try:
                qr = Image.open(REFLECT_QR_PATH).convert("RGBA").resize(
                    (REFLECT_QR_SIZE, REFLECT_QR_SIZE), Image.LANCZOS
                )
                qx = PORTRAIT_CENTER_X - REFLECT_QR_SIZE // 2
                qy = REFLECT_QR_BOTTOM_Y - REFLECT_QR_SIZE
                canvas.paste(qr, (qx, qy), qr)
            except Exception as e:
                logger.warning(f"Could not open QR {REFLECT_QR_PATH}: {e}. Skipping QR.")
        else:
            logger.warning(f"QR asset missing: {REFLECT_QR_PATH}. Skipping QR.")

    # 7. "thewiseroom.app" — bold, high-opacity bottom stamp.
    # No bold Lora is bundled, so simulate weight with a stroke at full opacity.
    draw.text(
        (PORTRAIT_CENTER_X, REFLECT_STAMP_BASELINE_Y),
        REFLECT_STAMP_TEXT,
        font=font_stamp,
        fill=BRONZE_COLOR,
        anchor="ms",
        stroke_width=1,
        stroke_fill=BRONZE_COLOR,
    )

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
    diameter: int = PORTRAIT_DIAMETER,
    top: int = PORTRAIT_TOP,
) -> None:
    r = diameter // 2
    left = PORTRAIT_CENTER_X - r

    try:
        portrait = Image.open(portrait_path).convert("RGBA")
        portrait = portrait.resize((diameter, diameter), Image.LANCZOS)
    except Exception as e:
        logger.warning(f"Could not open portrait {portrait_path}: {e}. Falling back to initial avatar.")
        _draw_initial_avatar(canvas, draw, "?", diameter=diameter, top=top)
        return

    # Circular mask
    mask = Image.new("L", (diameter, diameter), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([(0, 0), (diameter - 1, diameter - 1)], fill=255)

    portrait_rgba = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    portrait_rgba.paste(portrait, (0, 0), mask)
    canvas.paste(portrait_rgba, (left, top), portrait_rgba)


def _paste_circular(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    portrait_path: Path,
    left: int,
    top: int,
    diameter: int,
) -> None:
    """Circular-crop a portrait and paste it at an arbitrary (left, top).
    Falls back to a filled bronze circle if the asset can't be opened."""
    try:
        portrait = Image.open(portrait_path).convert("RGBA").resize(
            (diameter, diameter), Image.LANCZOS
        )
    except Exception as e:
        logger.warning(f"Could not open thumbnail {portrait_path}: {e}. Using bronze disc.")
        draw.ellipse([(left, top), (left + diameter, top + diameter)], fill=BRONZE_COLOR)
        return

    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (diameter - 1, diameter - 1)], fill=255)
    rgba = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    rgba.paste(portrait, (0, 0), mask)
    canvas.paste(rgba, (left, top), rgba)


def _fit_thumbnail_label(name: str | None) -> str | None:
    """The name to draw under a council portrait, or None to draw nothing.

    Falls back to the surname (last whitespace-separated token) when the full name
    overruns the per-portrait width budget — "Marcus Aurelius" does not fit at label
    size, "Aurelius" does. A single long token has nothing to fall back to and is
    returned as-is: a tight name reads better than a nameless portrait.
    """
    if not isinstance(name, str):
        return None
    text = name.strip()
    if not text:
        return None
    font = _load_font("CormorantGaramond-Medium.ttf", REFLECT_THUMB_LABEL_FONT_SIZE)
    if font.getlength(text) <= REFLECT_THUMB_LABEL_MAX_WIDTH:
        return text
    return text.split()[-1]


def _draw_thumbnail_row(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    paths: list[Path],
    *,
    diameter: int = REFLECT_THUMB_DIAMETER,
    gap: int = REFLECT_THUMB_GAP,
    center_y: int = REFLECT_THUMB_CENTER_Y,
    labels: list[str] | None = None,
) -> None:
    """Draw a centred horizontal row of circular thumbnails (Council card).

    `labels` (Council only) draws each persona's name under its circle. It is
    positional against `paths`, so a persona whose portrait failed to resolve
    takes its label with it and the row stays aligned.
    """
    n = len(paths)
    if n == 0:
        return
    row_w   = n * diameter + (n - 1) * gap
    start_x = (CANVAS_WIDTH - row_w) // 2
    top     = center_y - diameter // 2
    font_label = (
        _load_font("CormorantGaramond-Medium.ttf", REFLECT_THUMB_LABEL_FONT_SIZE)
        if labels else None
    )
    for i, path in enumerate(paths):
        left = start_x + i * (diameter + gap)
        _paste_circular(canvas, draw, path, left, top, diameter)
        if labels and i < len(labels):
            label = _fit_thumbnail_label(labels[i])
            if label:
                draw.text(
                    (left + diameter // 2, REFLECT_THUMB_LABEL_BASELINE_Y),
                    label,
                    font=font_label,
                    fill=BRONZE_COLOR,
                    anchor="ms",
                )


def _resolve_portrait_path(persona: Persona | None) -> Path | None:
    """Map a persona's stored portrait_url ('/personas/<file>') to a bundled
    static file, or None if absent/missing (caller renders a fallback)."""
    if persona is None or not persona.portrait_url:
        return None
    filename = persona.portrait_url.lstrip("/").removeprefix("personas/")
    candidate = PERSONAS_DIR / filename
    if candidate.exists():
        return candidate
    logger.warning(f"Portrait file not found for {persona.slug}: {candidate}.")
    return None


def _draw_initial_avatar(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    letter: str,
    diameter: int = PORTRAIT_DIAMETER,
    top: int = PORTRAIT_TOP,
) -> None:
    r = diameter // 2
    left = PORTRAIT_CENTER_X - r

    # Bronze filled circle
    draw.ellipse(
        [(left, top), (left + diameter, top + diameter)],
        fill=BRONZE_COLOR,
    )

    # White letter centered — scale glyph to the circle
    try:
        font = _load_font("CormorantGaramond-Medium.ttf", round(diameter * 0.37))
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


# ─────────────────────────────────────────────────────────────────────────────
# Counterview share card (4:5). Two full-bleed portraits split down the middle,
# names overlaid, and a paper "case against" box holding the anchor + the two
# verdicts. All constants tunable — coordinates verified against a sample render.
# ─────────────────────────────────────────────────────────────────────────────

CV_W, CV_H          = 1080, 1350
CV_MARGIN_X         = 72
CV_GAP              = 56
CV_PANEL_W          = (CV_W - 2 * CV_MARGIN_X - CV_GAP) // 2                                  # 440
CV_PANEL_TOP, CV_PANEL_BOT = 132, 612
CV_PANEL_L = (CV_MARGIN_X, CV_PANEL_TOP, CV_MARGIN_X + CV_PANEL_W, CV_PANEL_BOT)              # (72,132,512,612)
CV_PANEL_R = (CV_W - CV_MARGIN_X - CV_PANEL_W, CV_PANEL_TOP, CV_W - CV_MARGIN_X, CV_PANEL_BOT)  # (568,132,1008,612)
CV_PANEL_RADIUS     = 10
CV_BRACKET_INSET    = 12
CV_BRACKET_ARM      = 32
CV_CROP_BIAS_Y      = 0.32
CV_NAME_Y           = 640
CV_BOX              = (48, 728, 1032, 1302)
CV_HAIRLINE_Y       = 905
CV_VBAND_TOP, CV_VBAND_BOT = 922, 1252
PAPER_COLOR = (250, 244, 230)
SEPIA_COLOR = (138, 126, 106)
CREAM_COLOR = (245, 236, 216)          # still used by the missing-portrait fallback panel
BRONZE_DARK_COLOR = (138, 115, 64)


def _cover_paste(canvas: Image.Image, img: Image.Image, box, bias_y: float = CV_CROP_BIAS_Y, radius: int = 0) -> None:
    """object-cover: scale the image to fill `box` (preserving aspect), center
    horizontally, bias the vertical crop toward the top (bias_y), then paste.
    `radius` > 0 rounds the pasted corners via an alpha mask."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    iw, ih = img.size
    scale = max(bw / iw, bh / ih)
    new_w = max(bw, int(iw * scale + 0.999))
    new_h = max(bh, int(ih * scale + 0.999))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - bw) // 2
    top = int((new_h - bh) * bias_y)
    top = max(0, min(top, new_h - bh))
    cropped = resized.crop((left, top, left + bw, top + bh))
    if radius > 0:
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=radius, fill=255)
        canvas.paste(cropped, (x0, y0), mask)
    else:
        canvas.paste(cropped, (x0, y0))


def _cv_panel_fallback(canvas: Image.Image, draw: ImageDraw.ImageDraw, box, initial: str) -> None:
    """When a portrait is missing, fill the panel with cream and draw the
    persona's initial centered — mirrors _draw_initial_avatar in spirit."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=CREAM_COLOR)
    try:
        font = _load_font("CormorantGaramond-Medium.ttf", 200)
    except RuntimeError:
        return
    draw.text(((x0 + x1) // 2, (y0 + y1) // 2), initial, font=font, fill=BRONZE_DARK_COLOR, anchor="mm")


def _cv_diamond(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill) -> None:
    """A small filled diamond (rotated square) centered at (cx, cy)."""
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def _render_counterview_card(
    *,
    left_portrait: Path | None,
    right_portrait: Path | None,
    left_name: str,
    right_name: str,
    left_verdict: str,
    right_verdict: str,
    title: str | None,
    saved_at: datetime | None,
) -> bytes:
    """Pure render (no DB). Composes the 1080×1350 counterview share card."""
    canvas = Image.new("RGBA", (CV_W, CV_H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(canvas)
    cx = CV_W // 2
    panels = ((CV_PANEL_L, left_portrait, left_name), (CV_PANEL_R, right_portrait, right_name))

    # 1. top eyebrow + diamond (vellum → bronze-dark)
    f = _load_font("Lora-Regular.ttf", 24)
    draw.text((cx, 84), _letterspace("THE WISE ROOM", " "), font=f, fill=BRONZE_DARK_COLOR, anchor="ms")
    _cv_diamond(draw, cx, 104, 5, BRONZE_COLOR)

    # 2. two separate rounded portrait panels (cover-cropped)
    for box, portrait, name in panels:
        if portrait:
            try:
                _cover_paste(canvas, Image.open(portrait).convert("RGB"), box, radius=CV_PANEL_RADIUS)
            except Exception as e:
                logger.warning(f"CV portrait failed {portrait}: {e}.")
                _cv_panel_fallback(canvas, draw, box, (name[:1] or "?").upper())
        else:
            _cv_panel_fallback(canvas, draw, box, (name[:1] or "?").upper())

    # 3. paper case box
    draw.rounded_rectangle(CV_BOX, radius=18, fill=PAPER_COLOR)

    # 4. overlay: panel frames + brackets, box inset border, dividers
    overlay = Image.new("RGBA", (CV_W, CV_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    b = BRONZE_COLOR
    for box, _p, _n in panels:
        x0, y0, x1, y1 = box
        od.rounded_rectangle(box, radius=CV_PANEL_RADIUS, outline=b + (140,), width=2)
        i, a = CV_BRACKET_INSET, CV_BRACKET_ARM
        for (bx, by, dx, dy) in ((x0 + i, y0 + i, 1, 1), (x1 - i, y0 + i, -1, 1), (x0 + i, y1 - i, 1, -1), (x1 - i, y1 - i, -1, -1)):
            od.line([(bx, by), (bx + dx * a, by)], fill=b + (230,), width=3)
            od.line([(bx, by), (bx, by + dy * a)], fill=b + (230,), width=3)
    od.rounded_rectangle((CV_BOX[0] + 12, CV_BOX[1] + 12, CV_BOX[2] - 12, CV_BOX[3] - 12), radius=12, outline=b + (89,), width=1)
    od.line([(CV_BOX[0] + 60, CV_HAIRLINE_Y), (CV_BOX[2] - 60, CV_HAIRLINE_Y)], fill=b + (102,), width=1)
    od.line([(cx, CV_VBAND_TOP), (cx, CV_VBAND_BOT)], fill=b + (64,), width=1)
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # 5. names BELOW each panel (vellum → INK) + diamond rule
    fn = _load_font("CormorantGaramond-Medium.ttf", 40)
    for box, _p, name in panels:
        pcx = (box[0] + box[2]) // 2
        lines = _wrap_all_lines(name, fn, box[2] - box[0])[:2]
        ny = CV_NAME_Y
        for line in lines:
            draw.text((pcx, ny), line, font=fn, fill=INK_COLOR, anchor="mt")
            ny += 46
        ry = ny + 8
        draw.line([(pcx - 30, ry), (pcx - 8, ry)], fill=b, width=1)
        draw.line([(pcx + 8, ry), (pcx + 30, ry)], fill=b, width=1)
        _cv_diamond(draw, pcx, ry, 4, b)

    # 6. THE CASE AGAINST
    draw.text((cx, CV_BOX[1] + 46), _letterspace("THE CASE AGAINST", " "), font=_load_font("Lora-Regular.ttf", 22), fill=BRONZE_DARK_COLOR, anchor="ms")
    # 7. terrain title — Cormorant Medium, ink, prominent (the belief's terrain, NOT
    #    the raw confession). Old rows (title NULL) omit the line entirely; the card
    #    NEVER falls back to printing anchor_text here.
    if title:
        ft = _load_font("CormorantGaramond-Medium.ttf", 46)
        ty = CV_BOX[1] + 88
        for line in _wrap_all_lines(title, ft, CV_BOX[2] - CV_BOX[0] - 120)[:2]:
            draw.text((cx, ty), line, font=ft, fill=INK_COLOR, anchor="mt")
            ty += 52
    # 8. two verdict columns (auto-fit, ink)
    band_h = CV_VBAND_BOT - CV_VBAND_TOP
    for verdict, col_cx in ((left_verdict, 294), (right_verdict, 786)):
        if not verdict:
            continue
        fv, lines, lh = _fit_reflection(verdict, band_h, 430, lambda s: _load_font("CormorantGaramond-Medium.ttf", s))
        sy = CV_VBAND_TOP + max(0, (band_h - len(lines) * lh) // 2)
        for j, line in enumerate(lines):
            draw.text((col_cx, sy + j * lh), line, font=fv, fill=INK_COLOR, anchor="mt")
    # 9. brand
    draw.text((cx, CV_BOX[3] - 34), _letterspace(URL_TEXT, " "), font=_load_font("Lora-Regular.ttf", 24), fill=BRONZE_COLOR, anchor="ms", stroke_width=1, stroke_fill=BRONZE_COLOR)

    out = canvas.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Quote share card (4:5). A server-side mirror of the carousel QuoteCard: a
# full-bleed graded portrait, a dark ink→transparent scrim, the quote anchored
# low, the original-language phrase beneath it, and "The Wise Room" + QR branding.
# Distinct from the shared reflection canvas (vellum/circular) — quotes render
# HERE, every other share (line/council/mirror/…) still uses that canvas.
# All QUOTE_* values are starting points — tune without touching the function.
# ─────────────────────────────────────────────────────────────────────────────

# Grading — approximate the card's CSS grayscale(.35) sepia(.16) contrast(1.02)
# brightness(.97) + a bronze/10 veil.
QUOTE_GRADE_COLOR       = 0.65          # ImageEnhance.Color — the grayscale(0.35) pull
QUOTE_GRADE_CONTRAST    = 1.02
QUOTE_GRADE_BRIGHTNESS  = 0.97
QUOTE_SEPIA_COLOR       = (138, 126, 106)   # warm sepia tint blended into the portrait
QUOTE_SEPIA_STRENGTH    = 0.16          # ~sepia(0.16) blend fraction
QUOTE_BRONZE_VEIL_ALPHA = 26            # bronze/10 (~10% of 255), whole-canvas veil

# Bottom scrim — vertical ink→transparent over the lower band (from-ink via-ink/70
# to-transparent). Alpha ramps 0 at the band top to MAX_ALPHA at the bottom edge.
QUOTE_SCRIM_HEIGHT_RATIO = 0.62
QUOTE_SCRIM_MAX_ALPHA    = 235

# Top scrim — a short ink→transparent gradient behind the top wordmark so the
# bronze reads on a bright (face-biased) portrait crop.
QUOTE_TOP_SCRIM_HEIGHT_RATIO = 0.18
QUOTE_TOP_SCRIM_MAX_ALPHA    = 150

# Wordmark — "The Wise Room", Cormorant-Italic bronze, pinned top-centre.
QUOTE_WORDMARK_BASELINE_Y = 88
QUOTE_WORDMARK_FONT_SIZE  = 40

# Quote (the visual focus) — Cormorant-Medium, near-white, bottom-anchored, auto-fit.
QUOTE_TEXT_MAX_WIDTH   = 900
QUOTE_TEXT_MAX_SIZE    = 58
QUOTE_TEXT_MIN_SIZE    = 30
QUOTE_TEXT_LINE_RATIO  = 1.24           # matches the card's leading-[1.24]
QUOTE_PAPER_COLOR      = (247, 241, 227)    # near-white "paper"
QUOTE_ORIGINAL_COLOR   = (206, 198, 182)    # paper dimmed ~30% (reads as paper/70 on dark)

# Bottom stack — QR + stamp fixed at the bottom; source above them; the original
# phrase (when present) above source; the quote block bottom-anchored above that.
QUOTE_STAMP_BASELINE_Y      = 1300
QUOTE_STAMP_FONT_SIZE       = 30
QUOTE_QR_BOTTOM_Y           = 1250      # QR top = 1250 − REFLECT_QR_SIZE (110) = 1140
QUOTE_SOURCE_BASELINE_Y     = 1112
QUOTE_SOURCE_FONT_SIZE      = 26
QUOTE_ORIGINAL_BASELINE_Y   = 1074      # bottom line of the (≤2-line) original phrase
QUOTE_ORIGINAL_FONT_SIZE    = 26
QUOTE_TEXT_BOTTOM_Y         = 1040      # quote block bottom when an original phrase shows
QUOTE_TEXT_BOTTOM_Y_NO_ORIG = 1074      # quote drops toward the source when no original
QUOTE_TEXT_BAND_TOP         = 560       # top clamp for the fit loop


def _grade_portrait(img: Image.Image) -> Image.Image:
    """Approximate the carousel card's museum grade on an RGB portrait:
    desaturate, nudge contrast/brightness, and blend in a warm sepia tint."""
    img = ImageEnhance.Color(img).enhance(QUOTE_GRADE_COLOR)
    img = ImageEnhance.Contrast(img).enhance(QUOTE_GRADE_CONTRAST)
    img = ImageEnhance.Brightness(img).enhance(QUOTE_GRADE_BRIGHTNESS)
    tint = Image.new("RGB", img.size, QUOTE_SEPIA_COLOR)
    return Image.blend(img, tint, QUOTE_SEPIA_STRENGTH)


def _vertical_scrim(width: int, height: int, max_alpha: int, *, top_down: bool = False) -> Image.Image:
    """An `L`-mode alpha ramp for a vertical ink scrim. Bottom-heavy by default
    (0 at top → max_alpha at bottom); top_down flips it for a top scrim."""
    grad = Image.new("L", (1, height), 0)
    for y in range(height):
        t = y / max(1, height - 1)
        grad.putpixel((0, y), int(max_alpha * ((1 - t) if top_down else t)))
    return grad.resize((width, height))


def _wrap_cjk_chars(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    """Character-level greedy wrap for space-less scripts (e.g. CJK), where
    word-splitting yields one oversized token that can't break. Accumulates
    glyphs until the width is hit, then breaks. ≤ max_lines; '…'-truncates the
    last line on overflow. Quote-card–only — the shared wrappers stay untouched."""
    text = text.strip()
    lines: list[str] = []
    current = ""
    for ch in text:
        if not current or font.getlength(current + ch) <= max_width:
            current += ch  # always take ≥1 glyph per line to guarantee progress
        else:
            lines.append(current)
            current = ch
            if len(lines) == max_lines:
                current = ""
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if lines and sum(len(l) for l in lines) < len(text):  # overflow → ellipsize
        last = lines[-1]
        while last and font.getlength(last + "…") > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _renderable_original(s: str) -> bool:
    """True when the bundled fonts (Cormorant/Lora) can render every glyph in the
    original-language phrase. Confirmed via getmask that the bundled files cover
    ONLY Latin + common punctuation — NOT Greek or CJK, both of which render as
    tofu (□). So the card omits the phrase for Greek (Socrates / Marcus Aurelius /
    Epictetus) and CJK (Lao Tzu / Musashi) originals; the story sheet still shows
    them via the browser's system fonts. Bundling Greek/CJK-capable fonts (a
    separate PR) would let these render here."""
    for ch in s:
        if ch.isspace():
            continue
        cp = ord(ch)
        # Latin + Latin-1 + Latin Extended-A/B + General Punctuation only.
        if cp <= 0x024F or 0x2000 <= cp <= 0x206F:
            continue
        return False  # Greek, CJK, or any other unsupported script → skip the phrase
    return True


def _render_quote_card(
    *,
    quote_en: str,
    quote_original: str | None,
    portrait_path: Path | None,
    persona_name: str,
    source_short: str,
) -> bytes:
    """Full-bleed carousel-style quote share card (1080×1350). A graded portrait
    fills the canvas, a dark ink→transparent scrim anchors the quote low, the
    original-language phrase sits beneath it, and "The Wise Room" + a QR/
    thewiseroom.app stamp brand the card. Mirrors components/quotes/QuoteCard.tsx;
    independent of the shared reflection canvas. Returns raw PNG bytes."""
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))
    draw = ImageDraw.Draw(canvas)
    cx = PORTRAIT_CENTER_X
    initial = (persona_name[:1] or "?").upper()

    # 1. Full-bleed graded portrait; vellum field + centred initial when absent.
    if portrait_path:
        try:
            portrait = _grade_portrait(Image.open(portrait_path).convert("RGB"))
            _cover_paste(canvas, portrait, (0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))
        except Exception as e:
            logger.warning(f"Quote card portrait failed {portrait_path}: {e}. Using initial.")
            _draw_initial_avatar(canvas, draw, initial, diameter=REFLECT_PORTRAIT_DIAMETER, top=REFLECT_PORTRAIT_TOP)
    else:
        _draw_initial_avatar(canvas, draw, initial, diameter=REFLECT_PORTRAIT_DIAMETER, top=REFLECT_PORTRAIT_TOP)

    # 2. Bronze veil over the whole canvas (bronze/10) — final unifier.
    canvas.alpha_composite(Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BRONZE_COLOR + (QUOTE_BRONZE_VEIL_ALPHA,)))

    # 3. Top + bottom ink→transparent scrims for legibility.
    top_h = int(CANVAS_HEIGHT * QUOTE_TOP_SCRIM_HEIGHT_RATIO)
    top_layer = Image.new("RGBA", (CANVAS_WIDTH, top_h), INK_COLOR + (0,))
    top_layer.putalpha(_vertical_scrim(CANVAS_WIDTH, top_h, QUOTE_TOP_SCRIM_MAX_ALPHA, top_down=True))
    canvas.alpha_composite(top_layer, (0, 0))

    bot_h = int(CANVAS_HEIGHT * QUOTE_SCRIM_HEIGHT_RATIO)
    bot_layer = Image.new("RGBA", (CANVAS_WIDTH, bot_h), INK_COLOR + (0,))
    bot_layer.putalpha(_vertical_scrim(CANVAS_WIDTH, bot_h, QUOTE_SCRIM_MAX_ALPHA))
    canvas.alpha_composite(bot_layer, (0, CANVAS_HEIGHT - bot_h))
    draw = ImageDraw.Draw(canvas)

    # 4. "The Wise Room" — top-centre wordmark.
    draw.text(
        (cx, QUOTE_WORDMARK_BASELINE_Y), "The Wise Room",
        font=_load_font("CormorantGaramond-Italic.ttf", QUOTE_WORDMARK_FONT_SIZE),
        fill=BRONZE_COLOR, anchor="ms",
    )

    # 5. Bottom stack (drawn bottom-up): stamp, QR, source, original phrase, quote.
    # 5a. "thewiseroom.app" stamp — paper with a bronze stroke so it reads on dark.
    draw.text(
        (cx, QUOTE_STAMP_BASELINE_Y), URL_TEXT,
        font=_load_font("Lora-Regular.ttf", QUOTE_STAMP_FONT_SIZE),
        fill=QUOTE_PAPER_COLOR, anchor="ms", stroke_width=1, stroke_fill=BRONZE_COLOR,
    )

    # 5b. QR — centred above the stamp. Missing asset → skip, never 500.
    if REFLECT_QR_PATH.exists():
        try:
            qr = Image.open(REFLECT_QR_PATH).convert("RGBA").resize(
                (REFLECT_QR_SIZE, REFLECT_QR_SIZE), Image.LANCZOS
            )
            canvas.paste(qr, (cx - REFLECT_QR_SIZE // 2, QUOTE_QR_BOTTOM_Y - REFLECT_QR_SIZE), qr)
        except Exception as e:
            logger.warning(f"Could not open QR {REFLECT_QR_PATH}: {e}. Skipping QR.")
    else:
        logger.warning(f"QR asset missing: {REFLECT_QR_PATH}. Skipping QR.")

    # 5c. Source line "— {name}, {source}", bronze, shrunk to a single line.
    source_line = f"— {persona_name}, {source_short}"
    src_size = QUOTE_SOURCE_FONT_SIZE
    while src_size > 16 and _load_font("Lora-Regular.ttf", src_size).getlength(source_line) > QUOTE_TEXT_MAX_WIDTH:
        src_size -= 1
    draw.text(
        (cx, QUOTE_SOURCE_BASELINE_Y), source_line,
        font=_load_font("Lora-Regular.ttf", src_size), fill=BRONZE_COLOR, anchor="ms",
    )

    # 5d. Original phrase — italic serif (no Lora-Italic is bundled; Cormorant-Italic
    #     is the available italic), dimmed paper. Shown only when present, distinct,
    #     AND renderable by the bundled fonts — Greek (Socrates/Marcus/Epictetus) and
    #     CJK (Lao Tzu/Musashi) originals are omitted here rather than shipped as
    #     tofu; the story sheet still shows them via system fonts.
    show_original = (
        bool(quote_original) and quote_original != quote_en
        and _renderable_original(quote_original)
    )
    if show_original:
        orig_font = _load_font("CormorantGaramond-Italic.ttf", QUOTE_ORIGINAL_FONT_SIZE)
        orig_lines = _wrap_all_lines(quote_original, orig_font, QUOTE_TEXT_MAX_WIDTH)[:2]
        # Space-less scripts (e.g. Lao Tzu's Chinese) split() into one oversized
        # "word" that word-wrapping leaves overflowing — fall back to char wrapping.
        if any(orig_font.getlength(ln) > QUOTE_TEXT_MAX_WIDTH for ln in orig_lines):
            orig_lines = _wrap_cjk_chars(quote_original, orig_font, QUOTE_TEXT_MAX_WIDTH, 2)
        oy = QUOTE_ORIGINAL_BASELINE_Y
        for line in reversed(orig_lines):
            draw.text((cx, oy), line, font=orig_font, fill=QUOTE_ORIGINAL_COLOR, anchor="ms")
            oy -= round(QUOTE_ORIGINAL_FONT_SIZE * 1.2)

    # 5e. Quote (text_en) — Cormorant-Medium, near-white, auto-fit, bottom-anchored.
    quote_bottom = QUOTE_TEXT_BOTTOM_Y if show_original else QUOTE_TEXT_BOTTOM_Y_NO_ORIG
    band_height = quote_bottom - QUOTE_TEXT_BAND_TOP
    for size in range(QUOTE_TEXT_MAX_SIZE, QUOTE_TEXT_MIN_SIZE - 1, -1):
        q_font = _load_font("CormorantGaramond-Medium.ttf", size)
        q_lh = round(size * QUOTE_TEXT_LINE_RATIO)
        q_lines = _wrap_all_lines(quote_en, q_font, QUOTE_TEXT_MAX_WIDTH)
        if len(q_lines) * q_lh <= band_height:
            break
    else:
        # Even at MIN size it overflows — truncate to the lines that fit.
        q_font = _load_font("CormorantGaramond-Medium.ttf", QUOTE_TEXT_MIN_SIZE)
        q_lh = round(QUOTE_TEXT_MIN_SIZE * QUOTE_TEXT_LINE_RATIO)
        q_lines = _wrap_text(quote_en, q_font, QUOTE_TEXT_MAX_WIDTH, max(1, band_height // q_lh))
    start_y = quote_bottom - len(q_lines) * q_lh   # bottom-anchored
    for i, line in enumerate(q_lines):
        draw.text((cx, start_y + i * q_lh), line, font=q_font, fill=QUOTE_PAPER_COLOR, anchor="mt")

    out = canvas.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


async def generate_counterview_share_image(
    *,
    db: AsyncSession,
    counterview_id: str,
    user_id: str,
) -> bytes:
    """Load a generated counterview, verify ownership, and compose its share card.
    Raises ValueError if not found/owned or not in a shareable ('generated') state."""
    cv = (
        await db.execute(
            select(Counterview).where(
                Counterview.id == counterview_id,
                Counterview.user_id == user_id,
                Counterview.status == "generated",
            )
        )
    ).scalar_one_or_none()
    if cv is None:
        raise ValueError("Counterview not found or not shareable")

    responses = (
        await db.execute(
            select(CounterviewResponse)
            .where(
                CounterviewResponse.counterview_id == counterview_id,
                CounterviewResponse.round == 0,
            )
            .order_by(CounterviewResponse.position.asc())
        )
    ).scalars().all()
    if len(responses) < 2:
        raise ValueError("Counterview has no case to share")

    left, right = responses[0], responses[1]
    slugs = [left.persona_slug, right.persona_slug]
    by_slug = {
        p.slug: p
        for p in (await db.execute(select(Persona).where(Persona.slug.in_(slugs)))).scalars().all()
    }

    def _name(slug: str) -> str:
        p = by_slug.get(slug)
        return p.name if p else slug

    return _render_counterview_card(
        left_portrait=_resolve_portrait_path(by_slug.get(left.persona_slug)),
        right_portrait=_resolve_portrait_path(by_slug.get(right.persona_slug)),
        left_name=_name(left.persona_slug),
        right_name=_name(right.persona_slug),
        left_verdict=left.verdict,
        right_verdict=right.verdict,
        title=cv.title,
        saved_at=cv.created_at,
    )
