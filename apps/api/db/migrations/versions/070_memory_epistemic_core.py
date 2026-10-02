"""Epistemic core on memory_entries: provenance, surface, sources, supersession, reason

Revision ID: 070_memory_epistemic_core
Revises: 069_another_mind_count
Create Date: 2026-10-02

MEM2-A. Five columns, all additive and NULLable. Nothing existing changes shape,
and no reader of memory_entries has to change: is_active stays the single recall
gate (RECALL_SQL, standing_memories, find_recurrences, the self-model, the
portrait summary, You-vs-You, the trajectory snapshot and GET /memory all read
it, and none of them read anything added here).

  provenance           who authored the STORED WORDING (founder ruling
                       2026-10-02): 'user_stated' | 'user_selected' |
                       'system_inferred'. A separate axis from the recall lanes.
  source_surface       the surface that wrote the row. Free text, no CHECK: the
                       distill task's source_label vocabulary is open-ended.
  source_message_ids   uuid[], chat rows written after this migration only. NO
                       FOREIGN KEY, and that is required rather than lazy:
                       messages.conversation_id is ON DELETE CASCADE while
                       memory_entries.conversation_id is SET NULL (057, Ruling
                       #7c), so a thread delete removes the messages and keeps
                       the memory. A FK would either block that delete or take
                       the memory with it. Postgres cannot put a FK on an array
                       element in any case.
  supersedes_memory_id self-FK, ON DELETE SET NULL. One-for-one supersession
                       only (a re-answered portrait question). Onboarding
                       re-seeds replace a SET with a set and stay NULL.
  inactive_reason      why is_active went false: 'superseded' | 'user_removed'
                       | 'user_rejected'. Records the reason; does not gate.

NO BACKFILL HERE. 071 fills the existing rows, as its own data migration, so that
this schema change and that data change can each be read and reverted alone.

NO ROW LEVEL SECURITY statement: this adds columns to an existing table, which
already has RLS enabled (052_enable_rls). C-05 applies to migrations that CREATE
a public table.

NO INDEX on supersedes_memory_id. The chain is walked by nothing yet
(evolving_beliefs stays deferred, MEM2 ruling R1); an index for a reader that
does not exist is a write cost with no query behind it.

Self-contained per C-01: no application import.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = '070_memory_epistemic_core'
down_revision = '069_another_mind_count'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('memory_entries', sa.Column('provenance', sa.String(20), nullable=True))
    op.add_column('memory_entries', sa.Column('source_surface', sa.String(40), nullable=True))
    op.add_column(
        'memory_entries',
        sa.Column('source_message_ids', ARRAY(UUID(as_uuid=False)), nullable=True),
    )
    op.add_column(
        'memory_entries',
        sa.Column('supersedes_memory_id', UUID(as_uuid=False), nullable=True),
    )
    op.add_column('memory_entries', sa.Column('inactive_reason', sa.String(20), nullable=True))

    op.create_foreign_key(
        'fk_memory_entries_supersedes',
        'memory_entries', 'memory_entries',
        ['supersedes_memory_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_check_constraint(
        'ck_memory_entries_provenance',
        'memory_entries',
        "provenance IN ('user_stated', 'user_selected', 'system_inferred')",
    )
    op.create_check_constraint(
        'ck_memory_entries_inactive_reason',
        'memory_entries',
        "inactive_reason IN ('superseded', 'user_removed', 'user_rejected')",
    )


def downgrade():
    op.drop_constraint('ck_memory_entries_inactive_reason', 'memory_entries', type_='check')
    op.drop_constraint('ck_memory_entries_provenance', 'memory_entries', type_='check')
    op.drop_constraint('fk_memory_entries_supersedes', 'memory_entries', type_='foreignkey')
    op.drop_column('memory_entries', 'inactive_reason')
    op.drop_column('memory_entries', 'supersedes_memory_id')
    op.drop_column('memory_entries', 'source_message_ids')
    op.drop_column('memory_entries', 'source_surface')
    op.drop_column('memory_entries', 'provenance')
