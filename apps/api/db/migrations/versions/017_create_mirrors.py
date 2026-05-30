"""Create mirrors table for weekly and preview reflection summaries

Revision ID: 017_create_mirrors
Revises: 016_message_persona_id
Create Date: 2026-05-30
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = '017_create_mirrors'
down_revision = '016_message_persona_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mirrors (
          id              UUID                     PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id         UUID                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          host_persona_id UUID                     NULL      REFERENCES personas(id),
          period_start    TIMESTAMP WITH TIME ZONE NOT NULL,
          period_end      TIMESTAMP WITH TIME ZONE NOT NULL,
          kind            VARCHAR(20)              NOT NULL DEFAULT 'weekly'
                            CONSTRAINT ck_mirrors_kind CHECK (kind IN ('weekly', 'preview')),
          status          VARCHAR(20)              NOT NULL
                            CONSTRAINT ck_mirrors_status CHECK (status IN ('generated', 'empty', 'suppressed')),
          payload         JSONB                    NULL,
          ring_true       VARCHAR(10)              NULL
                            CONSTRAINT ck_mirrors_ring_true CHECK (ring_true IN ('yes', 'partly', 'no')),
          ring_true_note  TEXT                     NULL,
          ring_true_at    TIMESTAMP WITH TIME ZONE NULL,
          created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX ix_mirrors_user_created
          ON mirrors (user_id, created_at DESC)
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_mirrors_user_period_kind
          ON mirrors (user_id, period_start, kind)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_mirrors_user_period_kind")
    op.execute("DROP INDEX IF EXISTS ix_mirrors_user_created")
    op.execute("DROP TABLE IF EXISTS mirrors")
