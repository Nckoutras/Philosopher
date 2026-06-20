"""Add insight_id to mirrors + allow kind='insight' (insight-seeded mirror)

Revision ID: 031_mirrors_insight_id
Revises: 030_insights_source_count
Create Date: 2026-06-20

Links an on-demand, insight-seeded mirror to the insight that triggered it.

- insight_id: nullable FK → insights(id) ON DELETE SET NULL. Weekly/preview
  mirrors leave it NULL; an insight mirror carries its trigger.
- ck_mirrors_kind: the original check allowed only ('weekly', 'preview'); a
  kind='insight' INSERT would violate it, so we drop and recreate it to include
  'insight'.
- uq_mirrors_insight: partial unique index enforcing at most one mirror per
  insight (DB-level dedup against a double-tap race; only constrains the
  insight-mirror rows, weekly/preview NULLs are unaffected).
"""
from alembic import op

revision = '031_mirrors_insight_id'
down_revision = '030_insights_source_count'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE mirrors ADD COLUMN insight_id UUID "
        "REFERENCES insights(id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE mirrors DROP CONSTRAINT IF EXISTS ck_mirrors_kind")
    op.execute(
        "ALTER TABLE mirrors ADD CONSTRAINT ck_mirrors_kind "
        "CHECK (kind IN ('weekly', 'preview', 'insight'))"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mirrors_insight ON mirrors (insight_id) "
        "WHERE insight_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_mirrors_insight")
    op.execute("ALTER TABLE mirrors DROP CONSTRAINT IF EXISTS ck_mirrors_kind")
    op.execute(
        "ALTER TABLE mirrors ADD CONSTRAINT ck_mirrors_kind "
        "CHECK (kind IN ('weekly', 'preview'))"
    )
    op.execute("ALTER TABLE mirrors DROP COLUMN IF EXISTS insight_id")
