"""Add daily_usage.deep_mode_count (free daily deep-mode metering)

Revision ID: 050_deep_mode_count
Revises: 049_quotes_expand
Create Date: 2026-07-18

Additive, NOT NULL DEFAULT 0. Per-(user, persona, day) count of replies that got
deep-mode treatment while the sender was FREE. Mirrors go_deeper_count in shape;
the free daily allowance (5/day) is metered on the GLOBAL SUM across personas
(see rate_limit_service.check_deep_mode_limit). Pro/premium never increment it.
Existing rows backfill to 0 via the server default — pure no-op for current data.
"""
import sqlalchemy as sa
from alembic import op

revision = '050_deep_mode_count'
down_revision = '049_quotes_expand'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'daily_usage',
        sa.Column('deep_mode_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('daily_usage', 'deep_mode_count')
