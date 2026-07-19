"""Tests for ritual_id validation in ConversationService.create (PR-OPT-3).

Closes the free rate-limit bypass: ritual conversations are exempt from the
daily chat cap, and ritual_id had no FK / no validation — so a free user could
stamp any conversation as a "ritual". create() now rejects a fake/inaccessible
ritual_id. DB is mocked; get_persona uses the real (free) Marcus persona.

Run: cd apps/api && pytest tests/services/test_ritual_id_validation.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversation_service import ConversationService

FREE_PERSONA = "marcus_aurelius"          # a free-tier persona (accessible to free)
RITUAL_ID = "11111111-0000-0000-0000-000000000001"


def _result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ── (1) fake / nonexistent ritual_id → ValueError (router → 404) ──────────────

@pytest.mark.asyncio
async def test_nonexistent_ritual_id_raises_valueerror():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(None))  # ritual lookup → None
    with pytest.raises(ValueError, match="Ritual not found"):
        await ConversationService().create(
            db=db, user_id="u", persona_slug=FREE_PERSONA,
            ritual_id=RITUAL_ID, user_plan="free",
        )


# ── (2) free user + Pro ritual → PermissionError (router → 403 upgrade) ───────

@pytest.mark.asyncio
async def test_free_user_pro_ritual_raises_permissionerror():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(MagicMock(tier="pro")))
    with pytest.raises(PermissionError, match="Upgrade required"):
        await ConversationService().create(
            db=db, user_id="u", persona_slug=FREE_PERSONA,
            ritual_id=RITUAL_ID, user_plan="free",
        )


# ── (3) free user + free ritual → created, ritual_id stamped ──────────────────

@pytest.mark.asyncio
async def test_free_user_free_ritual_creates_and_stamps():
    db = AsyncMock()
    # execute order: ritual lookup → persona lookup → dedup lookup
    db.execute = AsyncMock(side_effect=[
        _result(MagicMock(tier="free")),        # ritual: exists, free
        _result(MagicMock(id="persona-uuid")),  # persona DB row
        _result(None),                          # dedup: no existing empty conv
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()

    conv = await ConversationService().create(
        db=db, user_id="u", persona_slug=FREE_PERSONA,
        ritual_id=RITUAL_ID, user_plan="free",
    )
    assert conv.ritual_id == RITUAL_ID


# ── (4) no ritual_id → unchanged path, zero ritual queries ────────────────────

@pytest.mark.asyncio
async def test_no_ritual_id_skips_ritual_query():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result(MagicMock(id="persona-uuid")),  # persona DB row
        _result(None),                          # dedup: no existing
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()

    conv = await ConversationService().create(
        db=db, user_id="u", persona_slug=FREE_PERSONA,
        ritual_id=None, user_plan="free",
    )
    assert conv.ritual_id is None
    # No executed statement targets the rituals table.
    for call in db.execute.call_args_list:
        assert "rituals" not in str(call.args[0]).lower()
