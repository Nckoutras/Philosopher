"""Add message_kind column to messages

Revision ID: 023_add_message_kind
Revises: 022_create_weekly_letters
Create Date: 2026-06-07
"""
import sqlalchemy as sa
from alembic import op

revision = '023_add_message_kind'
down_revision = '022_create_weekly_letters'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'messages',
        sa.Column('message_kind', sa.String(20), nullable=False, server_default='standard'),
    )


def downgrade() -> None:
    op.drop_column('messages', 'message_kind')
