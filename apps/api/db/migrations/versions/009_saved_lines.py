"""Saved lines — user saves of persona replies (C3 / F1)

Revision ID: 009_saved_lines
Revises: 008_hnsw_vector_indexes
Create Date: 2026-05-17

PR notes (documented here, no code change required):
- ON DELETE CASCADE on message_id FK is dormant. Messages are not currently
  hard-deleted in this codebase — only conversations.deleted_at soft-delete
  exists. If message hard-delete is ever introduced, revisit whether
  saved_lines should survive or cascade with the message.
- No (user_id, persona_id, saved_at DESC) index in v1. Free users are capped
  at 3 saves; Pro cohort is small in early stage. Deliberate non-optimization;
  revisit when any Pro user crosses ~100 saves.
- Race condition between count + insert accepted as known minor: worst case a
  free user lands 4 saves instead of 3 via concurrent POSTs across browser
  tabs. Self-correcting on next attempt (count check blocks the 5th). No
  SELECT FOR UPDATE in v1.
"""
import sqlalchemy as sa
from alembic import op


revision = '009_saved_lines'
down_revision = '008_hnsw_vector_indexes'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE saved_lines (
          id           UUID                     PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id      UUID                     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          message_id   UUID                     NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
          persona_id   UUID                     NOT NULL REFERENCES personas(id),
          source_type  VARCHAR(32)              NOT NULL DEFAULT 'manual_save'
                         CONSTRAINT ck_saved_lines_source_type CHECK (source_type IN ('manual_save', 'kept_insight')),
          saved_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
          deleted_at   TIMESTAMP WITH TIME ZONE NULL
        )
    """)

    op.execute("""
        CREATE INDEX ix_saved_lines_user_saved_at
          ON saved_lines (user_id, saved_at DESC)
          WHERE deleted_at IS NULL
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_saved_lines_user_message_active
          ON saved_lines (user_id, message_id)
          WHERE deleted_at IS NULL
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_saved_lines_user_message_active")
    op.execute("DROP INDEX IF EXISTS ix_saved_lines_user_saved_at")
    op.execute("DROP TABLE IF EXISTS saved_lines")
