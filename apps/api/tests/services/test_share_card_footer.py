"""The share-loop footer on the cards: QR and printed link (PR-1).

WHAT THIS PROTECTS. Six kinds get a per-share QR and a printed URL, added as an
OPT-IN parameter so every existing call renders exactly what it rendered before.
Two things can go wrong quietly and both are pinned here:

  - the footer silently not drawing (a missing encoder, an exception swallowed
    by the never-raises guard) — the card still renders, still looks right, and
    the loop is simply dead. Asserted by comparing pixels, not by trusting that
    the call was made.
  - the footer drawing the SAME thing for every share, which is what the old
    static qr-wiseroom.png did. A per-share QR that is not actually per-share is
    the failure this whole PR exists to fix, one layer down.
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime

import pytest

from services.image_service import (
    FONTS_DIR,
    REFLECT_QR_SIZE,
    SHARE_QR_SIZE,
    _render_reflection_canvas,
    _render_share_qr,
    _share_stamp_text,
)

URL_A = "https://thewiseroom.app/s/AbCdEfGhIjKlMnOpQrStUv"
URL_B = "https://thewiseroom.app/s/ZzZzZzZzZzZzZzZzZzZzZz"


def _require_fonts():
    if not (FONTS_DIR / "CormorantGaramond-Italic.ttf").exists():
        pytest.skip("Font files not available in test env")


def _render(**overrides) -> bytes:
    kwargs = dict(
        quote="The unexamined life is not worth living.",
        portrait_path=None,
        persona_initial="S",
        intro_text="Socrates told me",
        saved_at=datetime(2026, 6, 9),
    )
    kwargs.update(overrides)
    return _render_reflection_canvas(**kwargs)


# ── The printed link ─────────────────────────────────────────────────────────

def test_the_stamp_drops_the_scheme_and_keeps_the_path():
    """Founder-locked copy: bare, no prefix.

    The scheme is noise on a printed card and nobody types it. The PATH is kept
    because it IS the link — a reader who cannot scan must be able to type what
    they see and arrive in the same place.
    """
    assert _share_stamp_text(URL_A) == "thewiseroom.app/s/AbCdEfGhIjKlMnOpQrStUv"


def test_a_url_with_no_scheme_survives_unchanged():
    """Defensive: FRONTEND_URL is configuration and has been wrong before."""
    assert _share_stamp_text("thewiseroom.app/s/abc") == "thewiseroom.app/s/abc"


# ── The QR itself ────────────────────────────────────────────────────────────

def test_the_qr_renders_at_the_shipped_size():
    """110px, matching REFLECT_QR_SIZE — the size already in production.

    A second, different size would be a design change smuggled in beside a
    feature.
    """
    img = _render_share_qr(URL_A)
    assert img is not None
    assert img.size == (SHARE_QR_SIZE, SHARE_QR_SIZE)
    assert SHARE_QR_SIZE == REFLECT_QR_SIZE


def test_two_shares_get_two_different_codes():
    """THE ONE THAT MATTERS. The old card carried a STATIC code pointing at the
    bare host, identical on every card ever rendered. If this passes with equal
    bytes, the loop cannot attribute anything to anyone."""
    a = _render_share_qr(URL_A).tobytes()
    b = _render_share_qr(URL_B).tobytes()
    assert a != b


def test_a_failed_encoder_returns_none_rather_than_raising():
    """A card without its QR is worth shipping; a 500 on the share endpoint is
    not. Mirrors how the static asset was already handled."""
    import services.image_service as m
    real_import = __import__

    def _boom(name, *a, **kw):
        if name == "segno":
            raise ImportError("no segno here")
        return real_import(name, *a, **kw)

    import builtins
    builtins.__import__ = _boom
    try:
        assert _render_share_qr(URL_A) is None
    finally:
        builtins.__import__ = real_import


# ── The card ─────────────────────────────────────────────────────────────────

def test_a_share_url_changes_the_card():
    """The footer actually draws. Pixels, not a mock's call count.

    The QR helper never raises by design, so a broken encoder produces a card
    that renders fine and carries no loop at all. Only the bytes can tell.
    """
    _require_fonts()
    plain = _render()
    shared = _render(share_url=URL_A)
    assert plain != shared


def test_two_shares_produce_two_different_cards():
    """End to end: a per-share code has to reach the canvas, not just the helper."""
    _require_fonts()
    assert _render(share_url=URL_A) != _render(share_url=URL_B)


def test_omitting_the_share_url_is_byte_identical():
    """The opt-in safety argument, restated for this parameter.

    test_image_service.py makes the same assertion for `theme` and
    `thumbnail_labels`; this is the same guarantee for `share_url`, and it is
    what lets every non-share caller of these generators stay untouched.
    """
    _require_fonts()
    assert _render(share_url=None) == _render()
