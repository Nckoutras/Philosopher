"""Add persona_id column to messages for per-message speaker attribution

Revision ID: 016_message_persona_id
Revises: 015_add_fk_indexes
Create Date: 2026-05-29
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision = '016_message_persona_id'
down_revision = '015_add_fk_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('messages', sa.Column(
        'persona_id',
        UUID(as_uuid=False),
        sa.ForeignKey('personas.id'),
        nullable=True,
    ))
    op.create_index('ix_messages_persona_id', 'messages', ['persona_id'], if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_messages_persona_id', table_name='messages', if_exists=True)
    op.drop_column('messages', 'persona_id')
