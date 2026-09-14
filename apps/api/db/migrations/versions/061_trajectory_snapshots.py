"""Create trajectory_snapshots — the weekly record of what kept returning

Revision ID: 061_trajectory_snapshots
Revises: 060_insight_evidence
Create Date: 2026-09-14

Schema and its writer land together, but NOTHING READS THIS YET. The Sunday
letter (step D) is the reader; step C only fills the table so that D has a
history to read when it ships. A snapshot is an INTERNAL derived record: no LLM
call produces it, no persona voices it, and no endpoint returns it.

WHY A NEW TABLE AND NOT A `kind` ON `mirrors`. This table is, column for column,
the shape of `mirrors`: user_id, period_start, period_end, kind, status, payload,
and the same UNIQUE (user_id, period_start, kind). That duplication is deliberate
and was ruled on rather than overlooked, so the next person finds the decision
here instead of rediscovering the overlap:

  - `mirrors` is a LIVE user-facing table with shipped readers. Widening
    ck_mirrors_kind and ck_mirrors_status to admit an internal record that
    carries no host_persona_id, no insight_id and no ring_true triplet would
    make every existing `mirrors` query a candidate for an unqualified sweep —
    a production risk taken to avoid a migration.
  - 'failed' IS NOT A MIRROR STATE. A mirror that fails is simply not shown; a
    snapshot that fails must still be recorded, because D has to tell "nothing
    happened that week" from "we did not run that week". That is the same
    distinction 059 draws with job_run's NULL-vs-0 counts, one level down.

Duplicated SHAPE is acceptable. Duplicated LIFECYCLE is not.

THE COLUMNS.

period_start / period_end — the ISO week the snapshot covers, aligned exactly as
letter_dispatch.week_period aligns it, so weekly_run_key(period_start) is the
job_run key of the run that wrote the row (R7). period_start is therefore the
Monday 00:00Z of the week that is ending, and it is ALSO the corpus boundary the
snapshot was built against: a recurrence is an entry written in the period that
echoes entries written strictly before it.

kind — 'weekly' for v1. A String(20) with no CHECK, matching how `mirrors`
carries kind, so a later 'monthly' is a code change rather than a migration.
The UNIQUE index includes it for the same reason `mirrors` does: two cadences
can legitimately share a period_start.

status — CHECK ('generated', 'empty', 'failed'). Three states, each a different
fact and none inferable from the others:
  generated — the run completed and found at least one recurrence.
  empty     — the run completed and found none. The person was active; nothing
              they wrote that week echoed anything earlier.
  failed    — the run raised. We do not know what the week held.
A user with ZERO acts in the period gets NO ROW AT ALL, which is a fourth fact
and deliberately not a status: 'empty' means we looked, and the absence of a row
means there was nothing to look at.

payload — JSONB, the snapshot itself. v1 carries recurring_questions and
changes_since_prior and nothing else. evolving_beliefs is deferred behind the
version-chain question (memory_service.find_recurrences documents why its corpus
cannot see supersession), and unresolved_threads is out because no signal for it
exists.

NO FOREIGN KEYS FROM THE PAYLOAD CONTENTS, for the reason 060_insight_evidence
gives at greater length: the payload cites memory_entries by id AND carries a
denormalised text snippet beside each one. A memory row can be deactivated, and
057 lets a conversation be deleted out from under it. This is a HISTORICAL
RECORD — a citation that stopped rendering when its source vanished would defeat
the point of keeping it. user_id is ON DELETE CASCADE, so an erasure still takes
the whole row and the snippets add no surface that survives it.

C-05. trajectory_snapshots is a NEW public table, so it gets ENABLE ROW LEVEL
SECURITY here, in the same migration, in the posture 052_enable_rls established
and verified against production: ENABLED, ZERO POLICIES, NO FORCE. The API
connects as the table owner and owners bypass RLS, so this never gates the API;
what it closes is the PostgREST anon/authenticated surface, where an
unauthenticated caller would otherwise read every row of a new table. Adding
policies is a separate decision requiring its own review, exactly as 052 says.

C-04. The revision id is 24 characters and the filename equals it.

STYLE follows 059_job_run, the nearest precedent: op.create_table / sa.Column /
op.create_index rather than raw SQL, and the UUID primary key carries
server_default gen_random_uuid() AS WELL AS the model's Python default — the
model default only fires through the ORM, and a row inserted by raw SQL would
otherwise have no id.

DOWNGRADE is the exact mirror. The table holds only derived records, so dropping
it loses no user data — though it does lose history that cannot be rebuilt for
any week whose source rows have since been deactivated.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '061_trajectory_snapshots'
down_revision = '060_insight_evidence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'trajectory_snapshots',
        # server_default as well as the model default, per 059 (following 055,
        # following 002): the Python default only fires through the ORM, and a
        # row inserted by raw SQL would otherwise have no id.
        sa.Column(
            'id', UUID(as_uuid=False), primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'user_id', UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        # The ISO week covered. period_start is also the corpus boundary the
        # snapshot was built against — see the module docstring.
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        # No CHECK, as `mirrors` does it: a later cadence is a code change.
        sa.Column(
            'kind', sa.String(length=20), nullable=False,
            server_default=sa.text("'weekly'"),
        ),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('payload', JSONB, nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('generated', 'empty', 'failed')",
            name='ck_trajectory_snapshots_status',
        ),
    )
    # The idempotency key, in the shape uq_mirrors_user_period_kind uses: one
    # snapshot per (user, period, cadence). A re-run for a period already
    # covered violates this rather than quietly producing a second row.
    op.create_index(
        'uq_trajectory_snapshots_user_period_kind', 'trajectory_snapshots',
        ['user_id', 'period_start', 'kind'], unique=True,
    )
    # "This user's snapshots, newest first" — the query step D will run.
    op.create_index(
        'ix_trajectory_snapshots_user_period', 'trajectory_snapshots',
        ['user_id', sa.text('period_start DESC')],
    )

    # ── RLS (C-05) — same shape as 052 and 059: enabled, zero policies, no FORCE
    op.execute('ALTER TABLE public.trajectory_snapshots ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    op.execute('ALTER TABLE public.trajectory_snapshots DISABLE ROW LEVEL SECURITY;')
    op.drop_index('ix_trajectory_snapshots_user_period', table_name='trajectory_snapshots')
    op.drop_index('uq_trajectory_snapshots_user_period_kind', table_name='trajectory_snapshots')
    op.drop_table('trajectory_snapshots')
