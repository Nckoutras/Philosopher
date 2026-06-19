"""Add kind to weekly_letters + make the per-period unique index kind-aware

Revision ID: 029_weekly_letters_kind
Revises: 028_user_weekly_email_opt_out
Create Date: 2026-06-19

Adds a `kind` column ('weekly' | 'monthly') so the weekly-letter engine can also
produce monthly "season" letters in the same table. Existing rows → 'weekly'.

CRITICAL: the unique index must include `kind`. A monthly letter's period_start
is the 1st of the month at 00:00; a weekly letter's period_start is a Sunday at
00:00. When a month's 1st falls on a Sunday these collide, so the old
(user_id, period_start) unique index would reject the monthly insert. We recreate
it as (user_id, period_start, kind).
"""
from alembic import op

revision = '029_weekly_letters_kind'
down_revision = '028_user_weekly_email_opt_out'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE weekly_letters ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'weekly'"
    )
    op.execute(
        "ALTER TABLE weekly_letters "
        "ADD CONSTRAINT ck_weekly_letters_kind CHECK (kind IN ('weekly', 'monthly'))"
    )
    op.execute("DROP INDEX IF EXISTS uq_weekly_letters_user_period")
    op.execute(
        "CREATE UNIQUE INDEX uq_weekly_letters_user_period "
        "ON weekly_letters (user_id, period_start, kind)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_weekly_letters_user_period")
    op.execute(
        "CREATE UNIQUE INDEX uq_weekly_letters_user_period "
        "ON weekly_letters (user_id, period_start)"
    )
    op.execute("ALTER TABLE weekly_letters DROP CONSTRAINT IF EXISTS ck_weekly_letters_kind")
    op.execute("ALTER TABLE weekly_letters DROP COLUMN IF EXISTS kind")
