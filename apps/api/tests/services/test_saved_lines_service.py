"""Tests for SavedLinesService — create / list / delete / count / tier enforcement.

All DB interactions mocked; tier_service.get_user_tier patched at the service
module level so each test controls tier independently.

Run: cd apps/api && pytest tests/services/test_saved_lines_service.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from services.saved_lines_service import (
    SavedLinesService,
    FreeSavesLimitError,
    SavedLineNotFoundError,
    MessageNotFoundError,
    MessageRoleError,
    SavedLineAlreadyExistsError,
    FREE_SAVE_LIMIT,
)

USER_ID    = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER_ID   = "aaaaaaaa-0000-0000-0000-000000000002"
MSG_ID     = "bbbbbbbb-0000-0000-0000-000000000001"
CONV_ID    = "cccccccc-0000-0000-0000-000000000001"
PERSONA_ID = "dddddddd-0000-0000-0000-000000000001"
LINE_ID    = "eeeeeeee-0000-0000-0000-000000000001"

svc = SavedLinesService()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_message(role="assistant", user_id=USER_ID, conv_id=CONV_ID):
    m = MagicMock()
    m.id = MSG_ID
    m.role = role
    m.user_id = user_id
    m.conversation_id = conv_id
    m.content = "Test content"
    return m


def _make_conversation(persona_id=PERSONA_ID, user_id=USER_ID):
    c = MagicMock()
    c.id = CONV_ID
    c.persona_id = persona_id
    c.user_id = user_id
    return c


def _make_saved_line(deleted_at=None):
    sl = MagicMock()
    sl.id = LINE_ID
    sl.user_id = USER_ID
    sl.message_id = MSG_ID
    sl.persona_id = PERSONA_ID
    sl.source_type = "manual_save"
    sl.saved_at = datetime.now(timezone.utc)
    sl.deleted_at = deleted_at
    return sl


def _or_none(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _scalar(val):
    r = MagicMock()
    r.scalar_one.return_value = val
    return r


def _make_db(*execute_returns, add_ok=True):
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(side_effect=list(execute_returns))
    return db


# ── create() ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_success():
    msg = _make_message()
    conv = _make_conversation()
    db = _make_db(
        _or_none(msg),   # select(Message)
        _or_none(conv),  # select(Conversation)
        _or_none(None),  # no existing save
        _scalar(1),      # count_active (free, count=1 < 3)
    )
    with patch("services.saved_lines_service.tier_service.get_user_tier", AsyncMock(return_value="free")):
        result = await svc.create(db, USER_ID, MSG_ID)

    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    assert result.user_id == USER_ID
    assert result.message_id == MSG_ID
    assert result.persona_id == PERSONA_ID
    assert result.source_type == "manual_save"


@pytest.mark.asyncio
async def test_create_message_not_found():
    db = _make_db(_or_none(None))  # message not found
    with pytest.raises(MessageNotFoundError):
        await svc.create(db, USER_ID, MSG_ID)


@pytest.mark.asyncio
async def test_create_message_belongs_to_different_user():
    msg = _make_message(user_id=OTHER_ID)
    db = _make_db(_or_none(msg))
    with pytest.raises(MessageNotFoundError):
        await svc.create(db, USER_ID, MSG_ID)


@pytest.mark.asyncio
async def test_create_rejects_user_role_message():
    msg = _make_message(role="user")
    db = _make_db(_or_none(msg))
    with pytest.raises(MessageRoleError):
        await svc.create(db, USER_ID, MSG_ID)


@pytest.mark.asyncio
async def test_create_already_saved():
    msg = _make_message()
    conv = _make_conversation()
    existing = _make_saved_line()
    db = _make_db(
        _or_none(msg),      # select(Message)
        _or_none(conv),     # select(Conversation)
        _or_none(existing), # existing active save found
    )
    with pytest.raises(SavedLineAlreadyExistsError):
        await svc.create(db, USER_ID, MSG_ID)


@pytest.mark.asyncio
async def test_create_free_tier_limit_reached():
    msg = _make_message()
    conv = _make_conversation()
    db = _make_db(
        _or_none(msg),   # select(Message)
        _or_none(conv),  # select(Conversation)
        _or_none(None),  # no existing save
        _scalar(3),      # count_active = 3 (at limit)
    )
    with patch("services.saved_lines_service.tier_service.get_user_tier", AsyncMock(return_value="free")):
        with pytest.raises(FreeSavesLimitError) as exc_info:
            await svc.create(db, USER_ID, MSG_ID)

    assert exc_info.value.limit == FREE_SAVE_LIMIT
    assert exc_info.value.current_count == 3


@pytest.mark.asyncio
async def test_create_pro_user_unlimited():
    """Pro users skip the count query entirely and can save beyond limit."""
    msg = _make_message()
    conv = _make_conversation()
    db = _make_db(
        _or_none(msg),   # select(Message)
        _or_none(conv),  # select(Conversation)
        _or_none(None),  # no existing save
        # no count query — pro tier skips it
    )
    with patch("services.saved_lines_service.tier_service.get_user_tier", AsyncMock(return_value="pro")):
        result = await svc.create(db, USER_ID, MSG_ID)

    assert result.source_type == "manual_save"
    # count_active was NOT called (only 3 execute calls, not 4)
    assert db.execute.call_count == 3


# ── count_active() ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_count_active_returns_correct_count():
    db = _make_db(_scalar(2))
    count = await svc.count_active(db, USER_ID)
    assert count == 2


@pytest.mark.asyncio
async def test_count_active_zero():
    db = _make_db(_scalar(0))
    count = await svc.count_active(db, USER_ID)
    assert count == 0


# ── list_for_user() ───────────────────────────────────────────────────────────

def _make_list_row(
    sl_id=LINE_ID,
    message_id=MSG_ID,
    persona_id=PERSONA_ID,
    source_type="manual_save",
    saved_at=None,
    message_content="Quote text",
    conversation_id=CONV_ID,
    persona_slug="marcus-aurelius",
    persona_display_name="Marcus Aurelius",
):
    row = MagicMock()
    row._asdict.return_value = {
        "id": sl_id,
        "message_id": message_id,
        "persona_id": persona_id,
        "source_type": source_type,
        "saved_at": saved_at or datetime.now(timezone.utc),
        "message_content": message_content,
        "conversation_id": conversation_id,
        "persona_slug": persona_slug,
        "persona_display_name": persona_display_name,
    }
    return row


@pytest.mark.asyncio
async def test_list_returns_items_newest_first():
    t1 = datetime.now(timezone.utc) - timedelta(hours=2)
    t2 = datetime.now(timezone.utc)
    rows = [_make_list_row(sl_id=LINE_ID, saved_at=t2), _make_list_row(sl_id="ffffffff-0000-0000-0000-000000000001", saved_at=t1)]

    result_mock = MagicMock()
    result_mock.all.return_value = rows
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    items = await svc.list_for_user(db, USER_ID)
    assert len(items) == 2
    assert items[0]["saved_at"] == t2
    assert items[1]["saved_at"] == t1


@pytest.mark.asyncio
async def test_list_empty():
    result_mock = MagicMock()
    result_mock.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    items = await svc.list_for_user(db, USER_ID)
    assert items == []


@pytest.mark.asyncio
async def test_list_persona_filter_passes_through():
    """Verifies that a persona_id filter is applied (query is built and executed)."""
    result_mock = MagicMock()
    result_mock.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    await svc.list_for_user(db, USER_ID, persona_id=PERSONA_ID)
    db.execute.assert_awaited_once()


# ── delete() ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success():
    saved_line = _make_saved_line()
    db = _make_db(_or_none(saved_line))

    await svc.delete(db, USER_ID, LINE_ID)

    assert saved_line.deleted_at is not None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_already_soft_deleted_returns_not_found():
    # Query returns None because WHERE deleted_at IS NULL filters it out
    db = _make_db(_or_none(None))
    with pytest.raises(SavedLineNotFoundError):
        await svc.delete(db, USER_ID, LINE_ID)


@pytest.mark.asyncio
async def test_delete_non_owned_row_returns_not_found():
    # Query returns None because WHERE user_id = USER_ID filters it out
    db = _make_db(_or_none(None))
    with pytest.raises(SavedLineNotFoundError):
        await svc.delete(db, USER_ID, LINE_ID)


# ── Schema guard tests ────────────────────────────────────────────────────────

def test_message_model_has_user_id_column():
    """Guard: Message.user_id must exist for the ownership check in create()."""
    from models import Message
    assert 'user_id' in Message.__table__.columns, (
        "Message.user_id column not found — saved_lines ownership check requires it"
    )


def test_persona_model_has_slug_and_name_columns():
    """Guard: Persona.slug and Persona.name must exist for list_for_user() JOIN."""
    from models import Persona
    assert 'slug' in Persona.__table__.columns, "Persona.slug column not found"
    assert 'name' in Persona.__table__.columns, "Persona.name column not found"


@pytest.mark.asyncio
async def test_create_conversation_user_mismatch_raises_not_found():
    """Defense-in-depth: conversation.user_id mismatch raises MessageNotFoundError."""
    msg = _make_message()
    conv = _make_conversation(user_id=OTHER_ID)  # conversation belongs to a different user
    db = _make_db(
        _or_none(msg),   # select(Message) — passes (message.user_id == USER_ID)
        _or_none(conv),  # select(Conversation) — fails ownership check
    )
    with pytest.raises(MessageNotFoundError):
        await svc.create(db, USER_ID, MSG_ID)
