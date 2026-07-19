"""Tests for conversation_service dedup behavior (Prompt 1.5 fix).

Verifies that POST /conversations reuses an existing empty conversation
rather than creating duplicate rows.

Run: cd apps/api && pytest tests/test_conversations.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.conversation_service import ConversationService


@pytest.fixture
def service():
    return ConversationService()


def _mock_persona_db(slug="marcus_aurelius", persona_id="persona-uuid-1"):
    p = MagicMock()
    p.id = persona_id
    p.slug = slug
    return p


def _mock_conv(conv_id="conv-uuid-existing", message_count=0):
    c = MagicMock()
    c.id = conv_id
    c.message_count = message_count
    return c


def _make_db(*, persona_db, dedup_conv, ritual=None):
    """Mock AsyncSession. execute() sequence:

    [ritual lookup — only when `ritual` is provided (ritual_id validation)]
    → persona lookup → dedup conversation lookup.
    """
    db = AsyncMock()

    results = []
    if ritual is not None:
        ritual_result = MagicMock()
        ritual_result.scalar_one_or_none.return_value = ritual
        results.append(ritual_result)

    persona_result = MagicMock()
    persona_result.scalar_one_or_none.return_value = persona_db

    dedup_result = MagicMock()
    dedup_result.scalar_one_or_none.return_value = dedup_conv

    results += [persona_result, dedup_result]

    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


# ── a) Dedup returns existing empty conversation ──────────────────────────────

@pytest.mark.asyncio
async def test_create_returns_existing_empty_conversation(service):
    """Calling create() when an empty conversation already exists returns it."""
    persona_db = _mock_persona_db("marcus_aurelius")
    existing = _mock_conv("conv-uuid-existing", message_count=0)
    db = _make_db(persona_db=persona_db, dedup_conv=existing)

    result = await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    assert result.id == "conv-uuid-existing"


# ── b) New conversation created when existing has messages ────────────────────

@pytest.mark.asyncio
async def test_create_returns_new_after_messages_sent(service):
    """When no empty conversation exists (dedup miss), a new row is created."""
    persona_db = _mock_persona_db("marcus_aurelius")
    # Dedup returns None — the existing conv has messages so it wasn't returned
    db = _make_db(persona_db=persona_db, dedup_conv=None)

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    assert db.add.called


# ── c) No second opening invocation on dedup hit ─────────────────────────────

@pytest.mark.asyncio
async def test_create_does_not_duplicate_opening_invocation(service):
    """When dedup returns an existing conv, no Message is added to the DB."""
    persona_db = _mock_persona_db("marcus_aurelius")
    existing = _mock_conv("conv-uuid-existing", message_count=0)
    db = _make_db(persona_db=persona_db, dedup_conv=existing)

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    db.add.assert_not_called()


# ── d) ritual_id scopes the dedup — different ritual = new conversation ───────

@pytest.mark.asyncio
async def test_create_dedup_respects_ritual_id(service):
    """A plain conv (ritual_id=None) is not reused for a call with ritual_id set."""
    persona_db = _mock_persona_db("marcus_aurelius")
    # ritual_id validation now runs first — supply a valid free ritual so the call
    # proceeds; the dedup (ritual-scoped) then misses (None) and a new conv is made.
    db = _make_db(persona_db=persona_db, dedup_conv=None, ritual=MagicMock(tier="free"))

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
        ritual_id="ritual-uuid-99",
    )

    assert db.add.called


# ── e) Persona scopes the dedup — different persona = new conversation ────────

@pytest.mark.asyncio
async def test_create_dedup_respects_persona_slug(service):
    """A conversation for persona A is never returned as a dedup hit for persona B."""
    persona_db = _mock_persona_db("epictetus", persona_id="persona-uuid-2")
    # No empty conv found for epictetus
    db = _make_db(persona_db=persona_db, dedup_conv=None)

    # user_plan="pro" so the plan-access check passes for epictetus (pro-tier persona)
    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="epictetus",
        user_plan="pro",
    )

    assert db.add.called
