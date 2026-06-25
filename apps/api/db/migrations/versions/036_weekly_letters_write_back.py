"""Add write_back_text / write_back_at to weekly_letters (reader write-back)

Revision ID: 036_weekly_letters_write_back
Revises: 035_deep_mode_and_go_deeper_count
Create Date: 2026-06-25

Additive, schema-only. Lets a reader write a short response to a Sunday/season
letter. Both columns are NULLABLE: NULL means "no write-back" and the letter
behaves exactly as today. One write-back per letter (the row is overwritten on
re-submit) — no history table. The text is fed forward into the NEXT letter via
the existing prior-letters fetch, so no new query is added to the generators.
All existing rows default to NULL, so this migration is a pure no-op for current
behaviour. Mirrors the proven `mirrors.ring_true_note` / `ring_true_at` pattern.
"""
import sqlalchemy as sa
from alembic import op

revision = '036_weekly_letters_write_back'
down_revision = '035_deep_mode_and_go_deeper_count'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('weekly_letters', sa.Column('write_back_text', sa.Text(), nullable=True))
    op.add_column('weekly_letters', sa.Column(
        'write_back_at', sa.DateTime(timezone=True), nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('weekly_letters', 'write_back_at')
    op.drop_column('weekly_letters', 'write_back_text')
