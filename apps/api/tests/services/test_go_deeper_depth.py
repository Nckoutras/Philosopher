"""Tests for go-deeper depth + free daily limit + Pro sticky deep mode.

Covers:
- _deepen_directive targets the persona's deeper reflective band (exceeds U).
- check_go_deeper_limit: free under/at limit, Pro/premium unlimited.
- Confirmation A (defense-in-depth): the stream_response deep-mode read site is
  Pro-gated, so a stale deep_mode on a downgraded account is inert.
- Confirmation B: free and Pro per-tap go-deeper use the IDENTICAL depth
  directive (the free limit is quantity-only, never quality).

Run: cd apps/api && pytest tests/services/test_go_deeper_depth.py -v
"""
import inspect
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.conversation_service as cs
from services.conversation_service import _deepen_directive
from services.rate_limit_service import (
    check_go_deeper_limit,
    FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA,
)
from personas import get_persona

USER_ID = "11111111-1111-1111-1111-111111111111"
PERSONA_ID = "22222222-2222-2222-2222-222222222222"


# ── _deepen_directive: deeper band, exceeds the normal ceiling U ──────────────

def test_deepen_directive_targets_reflective_band_above_ceiling():
    for slug in ("marcus_aurelius", "carl_jung", "lao_tzu", "george_orwell"):
        persona = get_persona(slug)
        spec = persona.response_length_words
        reflective = spec.reflective_reply_max_words
        _, standard_upper = spec.standard_reply_words
        # The deeper band must exceed the normal standard ceiling — that's the
        # whole point of go-deeper.
        assert reflective > standard_upper
        directive = _deepen_directive(persona)
        assert str(reflective) in directive


def test_deepen_directive_falls_back_when_no_reflective_band():
    persona = MagicMock()
    persona.response_length_words = MagicMock(reflective_reply_max_words=None)
    directive = _deepen_directive(persona)
    assert str(cs._DEEPEN_FALLBACK_WORDS) in directive


# ── check_go_deeper_limit ─────────────────────────────────────────────────────

def _db_with_go_deeper_count(count):
    db = AsyncMock()
    usage = MagicMock()
    usage.go_deeper_count = count
    result = MagicMock()
    result.scalar_one_or_none.return_value = usage
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_free_under_limit_allowed():
    db = _db_with_go_deeper_count(FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA - 1)
    r = await check_go_deeper_limit(db, USER_ID, PERSONA_ID, user_tier="free")
    assert r.allowed is True
    assert r.remaining == 1


@pytest.mark.asyncio
async def test_free_at_limit_blocked():
    db = _db_with_go_deeper_count(FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA)
    r = await check_go_deeper_limit(db, USER_ID, PERSONA_ID, user_tier="free")
    assert r.allowed is False
    assert r.remaining == 0
    assert r.limit == FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA


@pytest.mark.asyncio
async def test_free_no_usage_row_allowed():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    r = await check_go_deeper_limit(db, USER_ID, PERSONA_ID, user_tier="free")
    assert r.allowed is True
    assert r.remaining == FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["pro", "premium"])
async def test_pro_unlimited_no_db_read(tier):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=AssertionError("must not query DB for Pro/premium"))
    r = await check_go_deeper_limit(db, USER_ID, PERSONA_ID, user_tier=tier)
    assert r.allowed is True
    assert r.limit == -1


# ── Confirmation A: deep-mode read site is Pro-gated (downgrade-safe) ──────────

def test_deep_mode_read_site_is_pro_gated():
    src = inspect.getsource(cs.ConversationService.stream_response)
    assert "conv.deep_mode" in src
    # The read site MUST require Pro/premium so a stale flag on a downgraded
    # account yields no depth.
    assert 'user_plan in ("pro", "premium")' in src
    # And distress must still win (level == none).
    assert 'safety_in.level == "none"' in src


# ── Confirmation B: free and Pro per-tap use the SAME depth directive ─────────

def test_per_tap_depth_directive_is_tier_independent():
    # _deepen_directive takes only the persona — no tier/plan argument — so the
    # depth is identical for free and Pro per-tap go-deeper.
    sig = inspect.signature(_deepen_directive)
    assert list(sig.parameters) == ["persona"]
    # stream_go_deeper builds the prompt from _deepen_directive for everyone.
    src = inspect.getsource(cs.ConversationService.stream_go_deeper)
    assert "_deepen_directive(persona)" in src
