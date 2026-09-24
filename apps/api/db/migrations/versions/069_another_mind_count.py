"""Add daily_usage.another_mind_count (counts another-mind toward the Pro caps)

Revision ID: 069_another_mind_count
Revises: 068_signup_share
Create Date: 2026-09-24

Additive, NOT NULL DEFAULT 0. Per-(user, persona, day) count of successful
another-mind replies, written on the RESPONDING persona's row. Existing rows
backfill to 0 via the server default — a pure no-op for current data.

WHY A NEW COLUMN AND NOT message_count. another-mind wrote no daily_usage row at
all, so it was refused at the Pro fair-use caps but never counted toward them
(TD-100). message_count would have been the obvious place, and the wrong one:
check_rate_limit sums message_count for the FREE daily allowance, so reusing it
would have silently tightened a free limit inside a cost change. This column is
read by check_fair_use_limit ONLY (Pro/premium), alongside message_count and
go_deeper_count. Same shape as 050_deep_mode_count.

NO ROW LEVEL SECURITY statement: this adds a column to an existing table, which
already has RLS enabled (052_enable_rls). C-05 applies to migrations that CREATE
a public table.

Self-contained per C-01: no application import.
"""
import sqlalchemy as sa
from alembic import op

revision = '069_another_mind_count'
down_revision = '068_signup_share'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'daily_usage',
        sa.Column('another_mind_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('daily_usage', 'another_mind_count')
