"""Adaptive length — now a BAND, and the one-length-sentence invariant.

`_length_directive_for_input` used to return a whole paragraph beginning
"LENGTH FOR THIS REPLY:". That paragraph was a SECOND length instruction sitting
beside the one `reply_directive` appends — the same contradiction the stale
"Keep responses between L-U words" fragment lines were removed to end. It now
returns `(lo, hi)` and the caller substitutes that band INTO reply_directive's
own sentence.

THE INVARIANT THIS FILE EXISTS FOR: exactly one length sentence reaches the
model, in all three states. Adaptive wins when it fires; otherwise the persona
band.

Adaptive is the common mid-session path, not an edge case. Measured on Oregon:
364 of 445 eligible turns (81.8%) fire it, 358 of them the short tier.

Run: cd apps/api && pytest tests/services/test_adaptive_length.py -v
"""
import re
from types import SimpleNamespace

import pytest

from personas import get_persona
from personas._models import ResponseLengthSpec
from services import reply_directive
from services.conversation_service import (
    ADAPTIVE_LENGTH_LONG_MIN_WORDS,
    ADAPTIVE_LENGTH_SHORT_MAX_WORDS,
    _adaptive_band_for_input,
)

# Every way a length instruction can currently reach the model.
LENGTH_SENTENCE = re.compile(
    r"Write between \d+ and \d+ words"
    r"|LENGTH FOR THIS REPLY"
    r"|Keep responses between"
    r"|up to about \d+ words",
    re.I,
)


def _words(n):
    return " ".join(["w"] * n)


def _persona(band):
    return SimpleNamespace(
        slug="socrates",
        response_length_words=ResponseLengthSpec(standard_reply_words=band),
    )


# ── the band function ───────────────────────────────────────────────────────

def test_no_spec_means_no_band():
    assert _adaptive_band_for_input(
        "anything", SimpleNamespace(response_length_words=None)) is None


def test_no_standard_band_means_no_band():
    spec = SimpleNamespace(response_length_words=ResponseLengthSpec(standard_reply_words=None))
    assert _adaptive_band_for_input("anything", spec) is None


def test_medium_input_uses_the_personas_own_band():
    assert _adaptive_band_for_input(_words(16), _persona((55, 80))) is None
    assert _adaptive_band_for_input(_words(49), _persona((55, 80))) is None


def test_short_input_compresses_toward_the_floor():
    lo, hi = _adaptive_band_for_input(_words(15), _persona((55, 80)))
    assert (lo, hi) == (55, 63)
    assert hi < 80, "the short tier must sit below the persona ceiling"


def test_long_input_reaches_the_ceiling():
    lo, hi = _adaptive_band_for_input(_words(50), _persona((55, 80)))
    assert (lo, hi) == (67, 80)
    assert lo > 55


@pytest.mark.parametrize("n,fires", [
    (ADAPTIVE_LENGTH_SHORT_MAX_WORDS, True),
    (ADAPTIVE_LENGTH_SHORT_MAX_WORDS + 1, False),
    (ADAPTIVE_LENGTH_LONG_MIN_WORDS - 1, False),
    (ADAPTIVE_LENGTH_LONG_MIN_WORDS, True),
])
def test_the_boundaries_are_inclusive_as_documented(n, fires):
    assert (_adaptive_band_for_input(_words(n), _persona((55, 80))) is not None) is fires


# ── the invariant: exactly one length sentence, in all three states ─────────

def _assembled(band, *, first_message=False, deep=False):
    """The directive as the call site builds it, for a real persona."""
    p = get_persona("socrates")
    return reply_directive.directive(
        p, first_message=first_message, deep=deep, band=band)


def test_state_1_no_adaptive_uses_the_persona_band_once():
    d = _assembled(None)
    assert len(LENGTH_SENTENCE.findall(d)) == 1
    lo, hi = get_persona("socrates").response_length_words.standard_reply_words
    assert f"Write between {lo} and {hi} words" in d


def test_state_2_short_input_substitutes_the_adaptive_band_once():
    band = _adaptive_band_for_input(_words(5), get_persona("socrates"))
    d = _assembled(band)
    assert len(LENGTH_SENTENCE.findall(d)) == 1
    assert f"Write between {band[0]} and {band[1]} words" in d
    assert "LENGTH FOR THIS REPLY" not in d, "the second paragraph must be gone"


def test_state_3_long_input_substitutes_the_adaptive_band_once():
    band = _adaptive_band_for_input(_words(80), get_persona("socrates"))
    d = _assembled(band)
    assert len(LENGTH_SENTENCE.findall(d)) == 1
    assert f"Write between {band[0]} and {band[1]} words" in d


def test_adaptive_wins_over_the_persona_band_when_it_fires():
    band = _adaptive_band_for_input(_words(5), get_persona("socrates"))
    persona_band = get_persona("socrates").response_length_words.standard_reply_words
    assert band != persona_band
    assert f"Write between {band[0]} and {band[1]}" in _assembled(band)


def test_the_deep_path_ignores_the_adaptive_band():
    """Deep has its own ceiling; adaptive is gated off it at the call site, and
    the directive ignores the argument even if one is passed."""
    assert _assembled((10, 20), deep=True) == _assembled(None, deep=True)
    assert len(LENGTH_SENTENCE.findall(_assembled(None, deep=True))) == 1


def test_no_persona_fragment_still_carries_a_length_line():
    """The stale "Keep responses between L-U words" bullets were removed from all
    eleven fragments. If one returns, every mid-session reply gets two length
    rules again and this whole file stops meaning anything."""
    from personas import PERSONA_REGISTRY
    for slug, p in PERSONA_REGISTRY.items():
        assert "Keep responses between" not in p.system_fragment, slug
