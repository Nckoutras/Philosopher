"""Allow 'conclusion' as a saved_lines.source_type

Revision ID: 024_saved_line_conclusion_source
Revises: 023_add_message_kind
Create Date: 2026-06-09

Gravity-gated conclusions (message_kind='conclusion') become a savable unit.
When such a message is saved, SavedLinesService tags the SavedLine with
source_type='conclusion'. Extend the existing CHECK constraint to permit it.

Note: no migration is needed for messages.message_kind='conclusion' — that
column (added in 023) is a plain VARCHAR(20) with no CHECK constraint.

Downgrade caveat: if any saved_lines.source_type='conclusion' rows exist, the
downgrade's narrower CHECK will fail to validate. That is intentional — a
downgrade past this revision must first reconcile those rows.
"""
from alembic import op


revision = '024_saved_line_conclusion_source'
down_revision = '023_add_message_kind'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE saved_lines DROP CONSTRAINT ck_saved_lines_source_type")
    op.execute("""
        ALTER TABLE saved_lines
          ADD CONSTRAINT ck_saved_lines_source_type
          CHECK (source_type IN ('manual_save', 'kept_insight', 'conclusion'))
    """)


def downgrade():
    op.execute("ALTER TABLE saved_lines DROP CONSTRAINT ck_saved_lines_source_type")
    op.execute("""
        ALTER TABLE saved_lines
          ADD CONSTRAINT ck_saved_lines_source_type
          CHECK (source_type IN ('manual_save', 'kept_insight'))
    """)
