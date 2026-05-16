"""Block C schema additions: conversations.deleted_at, messages.model_used, daily_usage table

Revision ID: 007_block_c_schema
Revises: 006_add_new_personas
Create Date: 2026-05-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision = '007_block_c_schema'
down_revision = '006_add_new_personas'
branch_labels = None
depends_on = None


def upgrade():
    # 1. conversations.deleted_at — soft-delete timestamp
    op.add_column(
        'conversations',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_conversations_user_active',
        'conversations',
        ['user_id'],
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # 2. messages.model_used — track which LLM tier handled the response
    op.add_column(
        'messages',
        sa.Column('model_used', sa.String(64), nullable=True),
    )

    # 3. daily_usage table — per-user-per-persona-per-day message counts
    op.create_table(
        'daily_usage',
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('persona_id', UUID(as_uuid=False), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'persona_id', 'usage_date'),
    )
    op.create_index(
        'ix_daily_usage_lookup',
        'daily_usage',
        ['user_id', 'usage_date'],
    )


def downgrade():
    op.drop_index('ix_daily_usage_lookup', table_name='daily_usage')
    op.drop_table('daily_usage')

    op.drop_column('messages', 'model_used')

    op.drop_index('ix_conversations_user_active', table_name='conversations')
    op.drop_column('conversations', 'deleted_at')
