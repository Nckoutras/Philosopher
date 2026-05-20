"""Scheduled emails — send-to-future-self feature

Revision ID: 012_scheduled_emails
Revises: 011_cross_persona_conversations
Create Date: 2026-05-20
"""
import sqlalchemy as sa
from alembic import op

revision = '012_scheduled_emails'
down_revision = '011_cross_persona_conversations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE scheduled_emails (
          id               UUID                     PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id          UUID                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          saved_line_id    UUID                     REFERENCES saved_lines(id) ON DELETE SET NULL,
          persona_id       UUID                     NOT NULL REFERENCES personas(id) ON DELETE RESTRICT,
          note             TEXT,
          recipient_email  VARCHAR(320)             NOT NULL,
          scheduled_for    TIMESTAMP WITH TIME ZONE NOT NULL,
          status           VARCHAR(16)              NOT NULL DEFAULT 'pending'
                             CONSTRAINT ck_scheduled_emails_status
                             CHECK (status IN ('pending','sent','failed','cancelled')),
          sent_at          TIMESTAMP WITH TIME ZONE,
          failure_reason   TEXT,
          created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
          updated_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX ix_scheduled_emails_pending
          ON scheduled_emails (scheduled_for)
          WHERE status = 'pending'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scheduled_emails_pending")
    op.execute("DROP TABLE IF EXISTS scheduled_emails")
