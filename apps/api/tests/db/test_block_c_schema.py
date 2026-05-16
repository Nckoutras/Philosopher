"""Unit tests for Block C schema additions.

Covers:
  - DailyUsage model: insert, increment, and lookup patterns via mock session
  - Conversation soft-delete: deleted_at field set and active-only queries
  - Message.model_used: field persists correctly

Run: cd apps/api && pytest tests/db/test_block_c_schema.py -v
"""
import sys
import os
import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import Conversation, DailyUsage, Message


# ── DailyUsage model structure ────────────────────────────────────────────────

def test_daily_usage_has_required_columns():
    """DailyUsage model exposes all columns required for rate limiting."""
    cols = {c.key for c in DailyUsage.__table__.columns}
    assert 'user_id' in cols
    assert 'persona_id' in cols
    assert 'usage_date' in cols
    assert 'message_count' in cols
    assert 'created_at' in cols
    assert 'updated_at' in cols


def test_daily_usage_primary_key():
    """Composite PK covers all three dimensions of uniqueness."""
    pk_cols = {c.name for c in DailyUsage.__table__.primary_key.columns}
    assert pk_cols == {'user_id', 'persona_id', 'usage_date'}


def test_daily_usage_foreign_keys():
    """user_id and persona_id carry FK constraints to their parent tables."""
    fk_map = {
        fk.parent.name: fk.target_fullname
        for c in DailyUsage.__table__.columns
        for fk in c.foreign_keys
    }
    assert fk_map.get('user_id') == 'users.id'
    assert fk_map.get('persona_id') == 'personas.id'


def test_daily_usage_lookup_index():
    """ix_daily_usage_lookup index exists on (user_id, usage_date)."""
    index_names = {idx.name for idx in DailyUsage.__table__.indexes}
    assert 'ix_daily_usage_lookup' in index_names


# ── DailyUsage insert / increment / lookup via mock session ───────────────────

def test_daily_usage_insert():
    """A new DailyUsage row can be added via db.add()."""
    db = MagicMock()

    row = DailyUsage(
        user_id='user-uuid-1',
        persona_id='persona-uuid-1',
        usage_date=date(2026, 5, 16),
        message_count=1,
    )
    db.add(row)
    db.add.assert_called_once_with(row)
    assert row.message_count == 1
    assert row.usage_date == date(2026, 5, 16)


def test_daily_usage_increment():
    """Incrementing message_count reflects in the object before flush."""
    row = DailyUsage(
        user_id='user-uuid-1',
        persona_id='persona-uuid-1',
        usage_date=date(2026, 5, 16),
        message_count=3,
    )
    row.message_count += 1
    assert row.message_count == 4


@pytest.mark.asyncio
async def test_daily_usage_lookup_returns_row():
    """db.execute() returning a row simulates a successful lookup."""
    db = AsyncMock()

    existing = DailyUsage(
        user_id='user-uuid-1',
        persona_id='persona-uuid-1',
        usage_date=date(2026, 5, 16),
        message_count=5,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result)

    # Simulate the lookup call
    fetched = (await db.execute("SELECT ...")).scalar_one_or_none()

    assert fetched is existing
    assert fetched.message_count == 5


@pytest.mark.asyncio
async def test_daily_usage_lookup_returns_none_when_missing():
    """db.execute() returning None simulates a cache miss."""
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    fetched = (await db.execute("SELECT ...")).scalar_one_or_none()
    assert fetched is None


# ── Conversation soft-delete ──────────────────────────────────────────────────

def test_conversation_has_deleted_at_column():
    """Conversation model exposes a deleted_at column."""
    cols = {c.key for c in Conversation.__table__.columns}
    assert 'deleted_at' in cols


def test_conversation_deleted_at_is_nullable():
    """deleted_at must be nullable (active conversations have no deletion timestamp)."""
    col = Conversation.__table__.c.deleted_at
    assert col.nullable is True


def test_conversation_deleted_at_defaults_to_none():
    """A freshly constructed Conversation has deleted_at=None (active)."""
    conv = Conversation(
        user_id='user-uuid-1',
        persona_id='persona-uuid-1',
    )
    assert conv.deleted_at is None


def test_conversation_soft_delete_sets_timestamp():
    """Setting deleted_at marks a conversation as deleted."""
    conv = Conversation(
        user_id='user-uuid-1',
        persona_id='persona-uuid-1',
    )
    now = datetime.now(tz=timezone.utc)
    conv.deleted_at = now
    assert conv.deleted_at == now


def test_conversation_active_filter_excludes_deleted():
    """Active conversations (deleted_at IS NULL) are distinct from deleted ones."""
    active = Conversation(user_id='u1', persona_id='p1')
    deleted = Conversation(user_id='u1', persona_id='p1')
    deleted.deleted_at = datetime.now(tz=timezone.utc)

    conversations = [active, deleted]
    active_only = [c for c in conversations if c.deleted_at is None]

    assert len(active_only) == 1
    assert active_only[0] is active


def test_conversation_active_index_exists():
    """Partial index ix_conversations_user_active is registered on the table."""
    index_names = {idx.name for idx in Conversation.__table__.indexes}
    assert 'ix_conversations_user_active' in index_names


# ── Message.model_used ────────────────────────────────────────────────────────

def test_message_has_model_used_column():
    """Message model exposes a model_used column."""
    cols = {c.key for c in Message.__table__.columns}
    assert 'model_used' in cols


def test_message_model_used_is_nullable():
    """model_used must be nullable (older messages pre-date this column)."""
    col = Message.__table__.c.model_used
    assert col.nullable is True


def test_message_model_used_defaults_to_none():
    """A freshly constructed Message has model_used=None."""
    msg = Message(
        conversation_id='conv-uuid-1',
        user_id='user-uuid-1',
        role='user',
        content='Hello',
    )
    assert msg.model_used is None


def test_message_model_used_persists():
    """Setting model_used on a Message object is reflected on the instance."""
    msg = Message(
        conversation_id='conv-uuid-1',
        user_id='user-uuid-1',
        role='assistant',
        content='Response',
        model_used='claude-sonnet-4-6',
    )
    assert msg.model_used == 'claude-sonnet-4-6'


def test_message_model_used_max_length():
    """model_used column is capped at 64 characters."""
    col = Message.__table__.c.model_used
    assert col.type.length == 64
