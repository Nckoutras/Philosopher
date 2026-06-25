"""Tests for adaptive response length (§ adaptive-length brief).

Covers the pure helper `_length_directive_for_input` (short / medium / long /
no-spec) and a structural assertion that the caller gates the directive behind
distress and the first-message cap.

Run: cd apps/api && pytest tests/services/test_adaptive_length.py -v
"""
import inspect
from types import SimpleNamespace

from personas._models import ResponseLengthSpec
from personas import get_persona
import services.conversation_service as cs
from services.conversation_service import _length_directive_for_input


def _persona(band):
    """Minimal persona stub: only the field the helper reads."""
    return SimpleNamespace(response_length_words=ResponseLengthSpec(standard_reply_words=band))


def _words(n: int) -> str:
    return " ".join(["word"] * n)


# ── No spec → no directive (graceful) ─────────────────────────────────────────

def test_no_spec_returns_none():
    assert _length_directive_for_input("anything", SimpleNamespace(response_length_words=None)) is None


def test_spec_without_standard_band_returns_none():
    spec = SimpleNamespace(response_length_words=ResponseLengthSpec(standard_reply_words=None))
    assert _length_directive_for_input("anything", spec) is None


# ── Medium input → no directive (typical case unchanged) ──────────────────────

def test_medium_input_returns_none():
    # 16..49 words inclusive is the medium band → no directive
    assert _length_directive_for_input(_words(16), _persona((20, 55))) is None
    assert _length_directive_for_input(_words(49), _persona((20, 55))) is None


# ── Short input → shorter band, capped at U ───────────────────────────────────

def test_short_input_emits_short_band():
    d = _length_directive_for_input(_words(15), _persona((20, 55)))
    assert d is not None
    # span = 35; upper = 20 + round(35 * 0.34) = 20 + 12 = 32
    assert "20–32 words" in d
    assert "Never exceed 55 words" in d


def test_short_threshold_boundary():
    # 15 = short; 16 = medium
    assert _length_directive_for_input(_words(15), _persona((20, 55))) is not None
    assert _length_directive_for_input(_words(16), _persona((20, 55))) is None


# ── Long input → fuller band, upper == existing ceiling U (never exceeds) ─────

def test_long_input_emits_long_band_capped_at_ceiling():
    d = _length_directive_for_input(_words(50), _persona((20, 55)))
    assert d is not None
    # lower = 20 + round(35 * 0.5) = 20 + 18 = 38; upper = U = 55
    assert "38–55 words" in d
    assert "never exceed 55 words" in d


def test_long_threshold_boundary():
    # 49 = medium; 50 = long
    assert _length_directive_for_input(_words(49), _persona((20, 55))) is None
    assert _length_directive_for_input(_words(50), _persona((20, 55))) is not None


def test_long_tier_never_exceeds_ceiling_for_real_personas():
    """For every populated persona, the long-tier upper bound == standard U."""
    for slug in ("marcus_aurelius", "carl_jung", "lao_tzu", "george_orwell"):
        persona = get_persona(slug)
        _, upper = persona.response_length_words.standard_reply_words
        d = _length_directive_for_input(_words(80), persona)
        assert d is not None
        # The stated ceiling in the directive is exactly U, not higher.
        assert f"never exceed {upper} words" in d


# ── Structural: caller gates behind distress + first message ──────────────────

def test_caller_gates_directive_behind_distress_and_first_message():
    """The append in stream_response must require level=="none" and history_len>1."""
    src = inspect.getsource(cs.ConversationService.stream_response)
    assert "_length_directive_for_input(user_text, persona)" in src
    # The directive append must be guarded by both gates.
    assert 'history_len > 1 and safety_in.level == "none"' in src
