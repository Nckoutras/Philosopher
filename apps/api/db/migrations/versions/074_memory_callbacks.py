"""Callback ledger (memory_callbacks) + two memory_entries columns

Revision ID: 074_memory_callbacks
Revises: 073_memory_echo_strength
Create Date: 2026-10-05

MEM2-C-2 (rulings 2026-10-05, IMPLEMENTATION_BACKLOG_v29.md § MEM2-C: Ruling 4,
Ruling 5, Ruling 9, C1-b). Behind CALLBACKS_ENABLED, default OFF: with the flag
off nothing writes to the new table and both new columns keep their defaults.

memory_callbacks — ONE ROW PER OFFER. Written deterministically when the gate
offered a candidate and the reply carrying it was saved (Phase C2 of
stream_response, same transaction as the assistant message). Zero LLM cost.

  memory_id        the offered row. CASCADE: memory rows are only hard-deleted
                   with the account, and the ledger goes with them.
  persona_id       the responder. No ondelete, as memory_entries.persona_id.
  conversation_id  SET NULL, and message_id SET NULL: deleting a thread must NOT
                   reset the cooldowns, so the ledger row outlives the thread.
                   It is a system record (the safety_events kind), not content
                   the user wrote; C-07 governs cleanup, account deletion cascades.
  message_id       the assistant reply that carried the offer. Ruling 9 looks it
                   up to mark the rows extracted from that pair and the next.
  score            cosine at offer — the canary's tuning data (C1-b).
  used, reaction   NULL until C-3 (the use detector) and the rejection endpoint.

Indexes serve the two cooldown queries (C1-b: one offer per user per 7 days;
the same row-or-chain never within 30 days) and the Ruling 9 lookup by message.

memory_entries:
  elicited_by_callback  NOT NULL DEFAULT false. Rows extracted from the user's
                        reply to a callback (Ruling 9): never independent
                        recurrence, echo, dedup or signal evidence, never a
                        callback candidate. A constant default is a metadata-only
                        change on Postgres 11+: no table rewrite.
  callback_blocked_at   NULL, or when the row became permanently ineligible as a
                        callback (rejected, in a rejected chain, or a near-
                        duplicate of a rejected row). NOT a recall gate: a
                        blocked row may stay active (Ruling 5).

RLS (C-05): enabled on memory_callbacks in this migration, the 052/061 posture —
enabled, zero policies, no FORCE. The memory_entries columns need no RLS
statement: they are columns on an existing table.

C-04: the revision id is 20 characters and the filename equals it.

NO BACKFILL. DOWNGRADE is the exact mirror; the ledger is derived state and the
two columns hold nothing a pre-C-2 reader uses.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = '074_memory_callbacks'
down_revision = '073_memory_echo_strength'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'memory_callbacks',
        # server_default as well as the model default (059/061): a row inserted
        # by raw SQL would otherwise have no id.
        sa.Column(
            'id', UUID(as_uuid=False), primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'user_id', UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'memory_id', UUID(as_uuid=False),
            sa.ForeignKey('memory_entries.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'persona_id', UUID(as_uuid=False),
            sa.ForeignKey('personas.id'), nullable=True,
        ),
        sa.Column(
            'conversation_id', UUID(as_uuid=False),
            sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True,
        ),
        sa.Column(
            'message_id', UUID(as_uuid=False),
            sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True,
        ),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column(
            'offered_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('reaction', sa.String(length=20), nullable=True),
        sa.Column('reacted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "reaction IN ('rejected')",
            name='ck_memory_callbacks_reaction',
        ),
    )
    # C1-b: "at most one offer per user per 7 days".
    op.create_index(
        'ix_memory_callbacks_user_offered', 'memory_callbacks',
        ['user_id', sa.text('offered_at DESC')],
    )
    # C1-b: "the same row-or-chain never re-offered within 30 days".
    op.create_index(
        'ix_memory_callbacks_memory_offered', 'memory_callbacks',
        ['memory_id', sa.text('offered_at DESC')],
    )
    # Ruling 9: the worker asks "did this assistant message carry an offer".
    op.create_index(
        'ix_memory_callbacks_message', 'memory_callbacks', ['message_id'],
        postgresql_where=sa.text('message_id IS NOT NULL'),
    )

    op.add_column(
        'memory_entries',
        sa.Column(
            'elicited_by_callback', sa.Boolean(), nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'memory_entries',
        sa.Column('callback_blocked_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── RLS (C-05) — same shape as 052, 059, 061: enabled, zero policies, no FORCE
    op.execute('ALTER TABLE public.memory_callbacks ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    op.execute('ALTER TABLE public.memory_callbacks DISABLE ROW LEVEL SECURITY;')
    op.drop_column('memory_entries', 'callback_blocked_at')
    op.drop_column('memory_entries', 'elicited_by_callback')
    op.drop_index('ix_memory_callbacks_message', table_name='memory_callbacks')
    op.drop_index('ix_memory_callbacks_memory_offered', table_name='memory_callbacks')
    op.drop_index('ix_memory_callbacks_user_offered', table_name='memory_callbacks')
    op.drop_table('memory_callbacks')
