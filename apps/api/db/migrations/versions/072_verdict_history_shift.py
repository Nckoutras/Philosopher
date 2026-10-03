"""Verdict history on insights; the insight a memory row was written about

Revision ID: 072_verdict_history_shift
Revises: 071_memory_provenance_backfill
Create Date: 2026-10-03

MEM2-B2. Two columns, both additive and NULLable (founder ruling, 2026-10-03).

  insights.verdict_history         JSONB, append-only list of {verdict, at}. The
                                   ring-true handler appends on EVERY verdict
                                   write from this deploy on. ring_true and
                                   ring_true_at keep holding the CURRENT verdict
                                   only. NO BACKFILL: history starts at deploy,
                                   and NULL reads as an empty list. A legacy
                                   insight with no 'no' in its history falls back
                                   to the ring_true_at loaded in-request (ruling).
  memory_entries.source_insight_id FK -> insights(id) ON DELETE SET NULL. The
                                   insight a system-composed row is ABOUT. Today
                                   only insight_verdict_shift rows set it. SET
                                   NULL rather than CASCADE: a memory row outlives
                                   what it came from (the 057 / Ruling #7c
                                   direction), and an insight is deleted only by
                                   the users-row cascade, which takes the memory
                                   row with it anyway.

ONE INDEX, partial, on source_insight_id. Unlike supersedes_memory_id (070, R1:
no reader, no index), this column has readers from day one: a 'no' retires the
insight's active shift row by it, and the shift task supersedes by it. A partial
index (WHERE NOT NULL) also keeps the FK's ON DELETE SET NULL from scanning all
of memory_entries for each insight a users-row cascade deletes. It holds one
row per shift entry, so it costs almost nothing to maintain.

NO ROW LEVEL SECURITY statement: this adds columns to two existing tables, both
already RLS-enabled (052_enable_rls). C-05 applies to migrations that CREATE a
public table.

Self-contained per C-01: no application import.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '072_verdict_history_shift'
down_revision = '071_memory_provenance_backfill'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('insights', sa.Column('verdict_history', JSONB, nullable=True))
    op.add_column(
        'memory_entries',
        sa.Column('source_insight_id', UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        'fk_memory_entries_source_insight',
        'memory_entries', 'insights',
        ['source_insight_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_memory_entries_source_insight_id',
        'memory_entries',
        ['source_insight_id'],
        postgresql_where=sa.text('source_insight_id IS NOT NULL'),
    )


def downgrade():
    op.drop_index('ix_memory_entries_source_insight_id', table_name='memory_entries')
    op.drop_constraint('fk_memory_entries_source_insight', 'memory_entries', type_='foreignkey')
    op.drop_column('memory_entries', 'source_insight_id')
    op.drop_column('insights', 'verdict_history')
