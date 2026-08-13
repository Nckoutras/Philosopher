"""Enable ROW LEVEL SECURITY on every application table (codifies the live state)

Revision ID: 052_enable_rls
Revises: 051_council_matter_edited
Create Date: 2026-08-13

Records in the chain what production already does. RLS was enabled on the live
database by hand (CORR-05) but no migration ever contained ROW LEVEL SECURITY in
any form (OPS-005), so a database rebuilt from migrations came up with RLS
DISABLED on every table — silently, with nothing to notice it. This migration
closes that gap: a rebuilt database now matches production.

NO-OP ON THE LIVE DATABASE. ENABLE ROW LEVEL SECURITY on an already-enabled table
succeeds and changes nothing, so applying this in production is inert by
construction. It is a bookkeeping migration, not a change.

WHAT RLS DOES HERE. The API connects as the table owner, and owners bypass RLS,
so this never gates the API. What it closes is the PostgREST anon/authenticated
surface, where an unauthenticated caller would otherwise read every row.

ZERO POLICIES, NO FORCE — deliberately. That is the verified production posture
(CORR-05: RLS enabled, 0 policies, FORCE not set, owner postgres), and this file
reproduces it exactly rather than an improved version of it. With no policies and
no FORCE: the owner still sees everything, and every non-owner role sees nothing.
Adding policies is a separate decision requiring its own review.

THE TABLE COUNT — 34 here, 35 live. This is an explanation, not a discrepancy.
The live database reports 35 public tables with RLS enabled; 34 of them are the
application tables listed below, which are exactly the tables in models/__init__.py
(the model list and the migration chain were cross-checked and agree exactly, with
no orphan on either side). The 35th is `alembic_version` — Alembic's own
bookkeeping table, which also lives in the public schema. It is deliberately
EXCLUDED here: its security posture is the migration tool's business, not the
application's, and a migration that reaches into its own version table is a
migration reaching into its own plumbing. Expect 34 from a rebuilt database and 35
from production; both are correct.

THE LIST IS LITERAL, not reflected. A runtime information_schema loop would enable
RLS on whatever tables happen to exist when it runs, which is a different and
weaker guarantee than naming them. A migration must be deterministic and
reviewable in the diff.

GOING FORWARD (C-05): every future migration that creates a public table must
enable RLS on it in the SAME migration. This file is a one-time catch-up for
001-051; it is not a pattern to re-run. Nothing here retrofits or edits any
existing migration — 001-051 stay byte-identical.
"""
from alembic import op

revision = '052_enable_rls'
down_revision = '051_council_matter_edited'
branch_labels = None
depends_on = None


# The 34 application tables, in models/__init__.py declaration order.
TABLES = [
    'users',
    'subscriptions',
    'personas',
    'quotes',
    'conversations',
    'messages',
    'memory_entries',
    'insights',
    'mirrors',
    'weekly_letters',
    'self_comparisons',
    'rituals',
    'user_ritual_completions',
    'source_chunks',
    'safety_events',
    'user_preferences',
    'otp_codes',
    'disclaimer_versions',
    'disclaimer_acceptances',
    'saved_lines',
    'scheduled_emails',
    'daily_questions',
    'daily_usage',
    'council_cases',
    'council_sessions',
    'council_responses',
    'council_saves',
    'counterviews',
    'counterview_responses',
    'counterview_saves',
    'saved_quotes',
    'self_comparison_saves',
    'counterview_turns',
    'mirror_saves',
]


def upgrade():
    for table in TABLES:
        op.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;')


def downgrade():
    for table in TABLES:
        op.execute(f'ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;')
