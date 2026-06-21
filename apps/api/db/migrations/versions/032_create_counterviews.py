"""Create counterviews + counterview_responses tables

Revision ID: 032_create_counterviews
Revises: 031_mirrors_insight_id
Create Date: 2026-06-21

The Counterview ritual: anchored on a position the person holds (typed directly,
or seeded from an insight), two distinct minds each deliver one sharp line making
the case against it. Modelled on the Council pattern (one parent + N persona rows).

- counterviews: one row per generated counterview. `source` distinguishes a typed
  belief ('direct') from an insight-seeded one ('insight'). `insight_id` is set
  only for the insight path; the partial unique index enforces at most one
  counterview per insight (app-level dedup + DB-level race guard, like
  uq_mirrors_insight). `status` mirrors the mirror/letter vocabulary.
- counterview_responses: the persona verdicts (round=0 in this slice; go-deeper
  rounds are a later slice). Unique on (counterview_id, persona_slug, round).
"""
from alembic import op

revision = '032_create_counterviews'
down_revision = '031_mirrors_insight_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE counterviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source VARCHAR(20) NOT NULL DEFAULT 'direct',
            insight_id UUID REFERENCES insights(id) ON DELETE SET NULL,
            anchor_text TEXT,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_counterviews_source CHECK (source IN ('direct', 'insight')),
            CONSTRAINT ck_counterviews_status CHECK (status IN ('generated', 'empty', 'suppressed'))
        )
    """)
    op.execute("CREATE INDEX ix_counterviews_user_created ON counterviews (user_id, created_at DESC)")
    op.execute(
        "CREATE UNIQUE INDEX uq_counterviews_insight ON counterviews (insight_id) "
        "WHERE insight_id IS NOT NULL"
    )

    op.execute("""
        CREATE TABLE counterview_responses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            counterview_id UUID NOT NULL REFERENCES counterviews(id) ON DELETE CASCADE,
            persona_slug VARCHAR(100) NOT NULL,
            round INTEGER NOT NULL DEFAULT 0,
            position INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_counterview_response UNIQUE (counterview_id, persona_slug, round)
        )
    """)
    op.execute("CREATE INDEX ix_counterview_responses_cv ON counterview_responses (counterview_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS counterview_responses")
    op.execute("DROP TABLE IF EXISTS counterviews")
