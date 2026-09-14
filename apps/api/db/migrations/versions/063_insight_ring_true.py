"""Add insights.ring_true + ring_true_at (Γ-2 — the recognition loop's record)

Revision ID: 063_insight_ring_true
Revises: 062_letter_email_opened
Create Date: 2026-09-14

WHAT THIS CLOSES. The room notices things about a person and shows them a card.
Until now the only durable response was `is_dismissed`, which conflates "wrong
about me" with "seen, done with it" — so a reader who thought *yes, exactly* left
no trace distinguishable from one who never opened the card. Every signal the
product could record was negative or neutral.

REUSES THE SHIPPED VOCABULARY, does not invent one. 'yes' | 'partly' | 'no' is
what mirrors.ring_true has meant since 017 and what self_comparisons has meant
since 021, with the same CHECK spelling as 017:31 so the three read identically
in psql. A fourth vocabulary for the same speech act would be a fourth thing to
keep in step.

NO ring_true_note HERE, deliberately. Mirrors and self-comparisons both carry a
free-text note; the weekly letter reads the mirrors one. A third note with no
reader would be a free-text column to safety-check, export, erase and migrate,
earning nothing until something consumes it. The verdict alone is the record v1
needs; the note is recorded as deferred rather than dropped.

INDEPENDENT OF is_dismissed, and this is load-bearing rather than stylistic. The
6h insight throttle (services/memory_service.py) counts NON-DISMISSED insights,
so dismissal already widens how often the room may notice anything. A 'no' that
implied dismissal would silently loosen that guard as a side effect of a person
disagreeing — the opposite of what disagreement should cost. Discard stays the
only dismissal.

C-05 (RLS on new tables) does not apply here: this migration creates NO table. It
adds two nullable columns to `insights`, which already has ROW LEVEL SECURITY
enabled by 052_enable_rls. Nothing about the RLS posture changes.

Both columns nullable with no server default — NULL means "not answered", which
is the correct and only honest reading for every row that predates this. A
default would invent an opinion on the reader's behalf.

NOT IN THIS MIGRATION: the missing CHECK on self_comparisons.ring_true (which
accepts any VARCHAR(10) today, since 021 created it without one). Adding it
requires first counting the off-vocabulary rows already in production, and that
count could not be run from this session. See the PR description.
"""
import sqlalchemy as sa
from alembic import op

revision = '063_insight_ring_true'
down_revision = '062_letter_email_opened'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('insights', sa.Column('ring_true', sa.String(10), nullable=True))
    op.add_column(
        'insights',
        sa.Column('ring_true_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Same spelling as ck_mirrors_ring_true (017:31) on purpose — three surfaces,
    # one contract, and a constraint that greps identically across all of them.
    op.create_check_constraint(
        'ck_insights_ring_true',
        'insights',
        "ring_true IN ('yes', 'partly', 'no')",
    )


def downgrade():
    op.drop_constraint('ck_insights_ring_true', 'insights', type_='check')
    op.drop_column('insights', 'ring_true_at')
    op.drop_column('insights', 'ring_true')
