"""Add council_sessions.matter_edited (user edited the auto-filled matter)

Revision ID: 051_council_matter_edited
Revises: 050_deep_mode_count
Create Date: 2026-07-18

Additive, NOT NULL DEFAULT false. True when a chat-sourced Council matter was
user-edited before submit (so the members deliberated the EDITED text, not a
fresh re-distillation). Persisted for future mining. Existing rows backfill to
false via the server default — pure no-op for current data.
"""
import sqlalchemy as sa
from alembic import op

revision = '051_council_matter_edited'
down_revision = '050_deep_mode_count'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'council_sessions',
        sa.Column('matter_edited', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade():
    op.drop_column('council_sessions', 'matter_edited')
