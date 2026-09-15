"""Add insight_id to council_cases (insight-seeded council keeps its trigger)

Revision ID: 065_council_insight_id
Revises: 064_self_comparison_ring_true
Create Date: 2026-09-15

Γ-7-lite. Three rituals can be opened from an insight card — the Mirror, the
Counterview and the Council. Two of them record which insight sent the person
there; the Council did not, and the link was simply lost.

The door already exists and already works: useInsightDoors routes a `dilemma`
insight to /app/council with the insight's CONTENT prefilled and
council_source='nudge'. What it never carried was the insight's ID, so a
nudge-sourced case recorded that it came from *an* insight and never which one.

THE SHAPE IS COPIED, NOT INVENTED. mirrors.insight_id (031) and
counterviews.insight_id (032) are both a nullable FK with ON DELETE SET NULL and
a partial unique index. This is the third instance of one pattern:

- insight_id: nullable FK → insights(id) ON DELETE SET NULL. Direct-, chat- and
  mirror-sourced councils leave it NULL; a nudge council carries its trigger.
  SET NULL rather than CASCADE, matching both siblings: the council session is
  the person's own artefact and outlives the card that prompted it.
- uq_council_cases_insight: partial unique index, at most one council per
  insight. App-level dedup does not exist on this path yet, so here the index is
  purely the DB-level race guard against a double tap. NULL rows are unaffected,
  which is what makes it safe on a table where most rows will never have one.

NO RLS STATEMENT, deliberately (C-05). This adds a column to an existing table;
it does not create one. council_cases already has RLS enabled — 052 enabled it
across all public tables, and nothing here changes that.

NO BACKFILL, and it could not be honest. The 55 existing cases (2026-09-15) have
no recoverable link: the insight id was never sent to the server, so there is
nothing in the database to reconstruct it from. Matching on prefill text would be
a guess written into a foreign key. Old rows stay NULL, correctly meaning "we did
not record this", which is different from "there was no insight".
"""
from alembic import op

revision = '065_council_insight_id'
down_revision = '064_self_comparison_ring_true'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE council_cases ADD COLUMN insight_id UUID "
        "REFERENCES insights(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_council_cases_insight ON council_cases (insight_id) "
        "WHERE insight_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_council_cases_insight")
    op.execute("ALTER TABLE council_cases DROP COLUMN IF EXISTS insight_id")
