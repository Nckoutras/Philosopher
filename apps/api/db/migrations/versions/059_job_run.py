"""Create job_run (scheduled-run audit) + weekly_letters.email_suppressed_reason

Revision ID: 059_job_run
Revises: 058_letter_failed_status
Create Date: 2026-09-07

Schema only. NOTHING WRITES TO job_run YET — the dispatch rewrite that opens a
row per run lands in PR-B (letters -> ARQ cron_jobs), and the guard that fills
email_suppressed_reason lands there too. This migration exists on its own so the
DDL is reviewable apart from the behaviour change that will depend on it (P-02).

WHY job_run EXISTS. A scheduled letter run currently leaves no trace of itself.
If Sunday's dispatch never fires, or fires and dies partway, the only evidence is
the absence of letters — which is indistinguishable from a week where nobody
qualified for one. status='failed' (058) records a letter that was attempted and
lost; it cannot record a RUN that never happened. That is the gap here.

THE COLUMNS.

run_key — the PERIOD the run is for, never when it executed (R7). Weekly is the
ISO week '2026-W36', monthly is 'YYYY-MM'. Derived from period_start, so a
catch-up executed on Tuesday for last Sunday's week carries last Sunday's key and
collides with the run that already covered it. An execution-time key would make
every re-run look like a new run, which is the one thing this table must not do.
VARCHAR(32) is far wider than either format needs; the width is not the
constraint, the UNIQUE index is.

finished_at NULL — the crash signal, and the reason it is nullable rather than
defaulted. A row is opened with status='running' and finished_at NULL; a process
that dies mid-run never comes back to close it. So "finished_at IS NULL AND
status='running'" is the query that finds a run nobody noticed dying. A default
would erase exactly that.

candidate_count / selected_count / enqueued_count (R3) — nullable, because a run
that crashes before it counts anything must not claim zero. NULL means "never got
that far"; 0 means "counted, and there were none". The distinction is the whole
point: "no letters went out because nobody qualified" and "no letters went out
because dispatch died" look identical without it.

NO detail JSONB (R6). Counts only for v1. A free-form blob is where a schema goes
to stop being one, and nothing has yet named a field it would need.

THE UNIQUE INDEX (job_name, run_key) is the idempotency key, in the shape
055_billing_lifecycle uses for stripe_events: a second dispatch for a period
already covered becomes a constraint violation rather than a judgement call at
the call site. PR-C's catch-up is invoked with an explicit run_key (R8) and this
index is what makes that safe to run twice.

weekly_letters.email_suppressed_reason — nullable VARCHAR(32), additive, no
backfill. NULL means the email was sent, or predates this column. The guard in
PR-B writes one of: localhost | no_email | opt_out | already_sent | send_failed
(R2). Today the letter is generated and the email silently does not go out, and
the row records nothing about which of those happened.

NO CHECK CONSTRAINT ON IT, DELIBERATELY — and this is the one place this file
departs from how weekly_letters.status is handled. Those five values are an
APPLICATION vocabulary, not a data-integrity rule: a sixth reason is a code
change, and it must not also be a production migration. The values are pinned in
PR-B's test instead, which is where the guard that writes them lives (R2a). The
contrast with 058 is deliberate rather than an oversight: status is read back by
the dedup query and by the list endpoint, so a wrong value there changes
behaviour; a suppression reason is written once and only ever read by an operator.

C-05, BOTH HALVES.
  - job_run is a NEW public table, so it gets ENABLE ROW LEVEL SECURITY here, in
    the same migration, in the posture 052_enable_rls established and verified
    against production: ENABLED, ZERO POLICIES, NO FORCE. The API connects as the
    table owner and owners bypass RLS, so this never gates the API; what it
    closes is the PostgREST anon/authenticated surface, where an unauthenticated
    caller would otherwise read every row of a new table. Adding policies is a
    separate decision requiring its own review, exactly as 052 says.
  - weekly_letters gets a COLUMN, not a table, so C-05 does not apply to it. 052
    already enabled RLS on weekly_letters and nothing about that posture changes
    here. Said explicitly rather than left for a reader to work out, following
    053, 054 and 058.

STYLE follows 055_billing_lifecycle, the nearest precedent: it is the most recent
migration that both creates public tables and adds nullable columns to an
existing one. op.create_table / sa.Column / op.create_index rather than raw SQL,
and the UUID primary key carries server_default gen_random_uuid() AS WELL AS the
model's Python default — following 002_otp_codes via 055: the model default only
fires through the ORM, and a row inserted by raw SQL would otherwise have no id.

DOWNGRADE is the exact mirror: the column, RLS off, indexes, table. job_run holds
only operational history, so dropping it loses no user data.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = '059_job_run'
down_revision = '058_letter_failed_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── job_run ──────────────────────────────────────────────────────────────
    op.create_table(
        'job_run',
        # server_default as well as the model default, per 055 (following 002):
        # the Python default only fires through the ORM, and a row inserted by
        # raw SQL would otherwise have no id.
        sa.Column(
            'id', UUID(as_uuid=False), primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('job_name', sa.String(length=64), nullable=False),
        # The PERIOD, not the execution time (R7): '2026-W36' or '2026-09'.
        sa.Column('run_key', sa.String(length=32), nullable=False),
        sa.Column(
            'started_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        # NULL = still running, or crashed and never closed. No default: that
        # NULL is the only evidence a run died mid-flight.
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        # Nullable, not 0-defaulted: NULL is "never counted", 0 is "counted none".
        sa.Column('candidate_count', sa.Integer(), nullable=True),
        sa.Column('selected_count', sa.Integer(), nullable=True),
        sa.Column('enqueued_count', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name='ck_job_run_status',
        ),
    )
    # The idempotency key: one run per (job, period). A re-dispatch for a period
    # already covered violates this rather than quietly producing a second run.
    op.create_index(
        'uq_job_run_name_key', 'job_run', ['job_name', 'run_key'], unique=True,
    )
    # "What has the scheduler done lately" without a sequential scan.
    op.create_index('ix_job_run_started_at', 'job_run', ['started_at'])

    # ── RLS (C-05) — same shape as 052: enabled, zero policies, no FORCE ─────
    op.execute('ALTER TABLE public.job_run ENABLE ROW LEVEL SECURITY;')

    # ── weekly_letters: one additive nullable column, no backfill ────────────
    # No CHECK — the five reasons are an app vocabulary pinned in PR-B's test,
    # so adding a sixth stays a code change and never becomes a migration.
    op.add_column(
        'weekly_letters',
        sa.Column('email_suppressed_reason', sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('weekly_letters', 'email_suppressed_reason')
    op.execute('ALTER TABLE public.job_run DISABLE ROW LEVEL SECURITY;')
    op.drop_index('ix_job_run_started_at', table_name='job_run')
    op.drop_index('uq_job_run_name_key', table_name='job_run')
    op.drop_table('job_run')
