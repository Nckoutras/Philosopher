"""Create weekly_letters table

Revision ID: 022_create_weekly_letters
Revises: 021_create_self_comparisons
Create Date: 2026-06-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = '022_create_weekly_letters'
down_revision = '021_create_self_comparisons'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE weekly_letters (
          id               UUID                     PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id          UUID                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          voice_persona_id UUID                     NULL      REFERENCES personas(id),
          period_start     TIMESTAMP WITH TIME ZONE NOT NULL,
          period_end       TIMESTAMP WITH TIME ZONE NOT NULL,
          status           VARCHAR(20)              NOT NULL
                             CONSTRAINT ck_weekly_letters_status
                             CHECK (status IN ('generated', 'empty', 'suppressed')),
          payload          JSONB                    NULL,
          read_at          TIMESTAMP WITH TIME ZONE NULL,
          email_sent_at    TIMESTAMP WITH TIME ZONE NULL,
          created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_weekly_letters_user_period
          ON weekly_letters (user_id, period_start)
    """)

    op.execute("""
        CREATE INDEX ix_weekly_letters_user_id
          ON weekly_letters (user_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_weekly_letters_user_period")
    op.execute("DROP INDEX IF EXISTS ix_weekly_letters_user_id")
    op.execute("DROP TABLE IF EXISTS weekly_letters")
