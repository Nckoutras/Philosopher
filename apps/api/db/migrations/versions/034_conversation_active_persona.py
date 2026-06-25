"""Add active_persona_id to conversations (sticky guest mind)

Revision ID: 034_conversation_active_persona
Revises: 033_create_counterview_saves
Create Date: 2026-06-25

Additive, schema-only. `conversations.active_persona_id` is NULLABLE: NULL means
"no sticky guest" and the conversation behaves exactly as today (responder, quota,
header, thumbnails all fall back to the immutable `persona_id`). All existing rows
default to NULL, so this migration is a pure no-op for current behaviour. ON DELETE
SET NULL so deleting a persona row cleanly reverts affected conversations to origin.
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision = '034_conversation_active_persona'
down_revision = '033_create_counterview_saves'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column(
        'active_persona_id',
        UUID(as_uuid=False),
        sa.ForeignKey('personas.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.create_index(
        'ix_conversations_active_persona_id', 'conversations',
        ['active_persona_id'], if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index('ix_conversations_active_persona_id', table_name='conversations', if_exists=True)
    op.drop_column('conversations', 'active_persona_id')
