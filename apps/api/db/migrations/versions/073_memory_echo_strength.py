"""Recurrence strength on memory_entries: echo_count, last_echo_at

Revision ID: 073_memory_echo_strength
Revises: 072_verdict_history_shift
Create Date: 2026-10-03

MEM2-B4 (founder ruling 2026-10-03). Two columns, both additive and NULLable.

  echo_count    INT. How many extraction calls have produced a new row that
                matched this one at or above the recurrence threshold (0.75).
                The search's own exclusion decides what counts: a chat row is
                compared only with OTHER conversations; a row with no
                conversation (a counterview belief) with every row but itself.
                +1 per anchor per call, however many new rows in that call
                matched it.
  last_echo_at  timestamptz. When that last happened.

Counted in detect_recurrence's search, which since B4 runs for every new row
BEFORE the insight gate, so strength accrues whether or not a card is written.
NULL means "never echoed since this deployed": NO BACKFILL, counting starts at
deploy.

NO INDEX: nothing filters or orders by either column yet; the data export reads
them per row. An index for a reader that does not exist is a write cost with no
query behind it (070's rule for supersedes_memory_id).

B3 (signal evidence, R4) needs no schema: insights.evidence is JSONB and only
its shape changes. This migration is the two B4 columns only (ruling).

NO ROW LEVEL SECURITY statement: this adds columns to an existing table, which
already has RLS enabled (052_enable_rls). C-05 applies to migrations that CREATE
a public table.

Self-contained per C-01: no application import.
"""
import sqlalchemy as sa
from alembic import op

revision = '073_memory_echo_strength'
down_revision = '072_verdict_history_shift'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('memory_entries', sa.Column('echo_count', sa.Integer, nullable=True))
    op.add_column(
        'memory_entries',
        sa.Column('last_echo_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('memory_entries', 'last_echo_at')
    op.drop_column('memory_entries', 'echo_count')
