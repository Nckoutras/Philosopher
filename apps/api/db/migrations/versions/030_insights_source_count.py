"""Add source_count to insights (longitudinal provenance)

Revision ID: 030_insights_source_count
Revises: 029_weekly_letters_kind
Create Date: 2026-06-20

Stores how many distinct conversations a recurring theme was noticed across when
the recurrence detector fires (distinct prior conversations + the current one).
Nullable: existing insights predate the count and stay NULL — the card only shows
the provenance line when source_count >= 2, so NULL rows simply omit it.
"""
from alembic import op

revision = '030_insights_source_count'
down_revision = '029_weekly_letters_kind'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE insights ADD COLUMN source_count INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE insights DROP COLUMN IF EXISTS source_count")
