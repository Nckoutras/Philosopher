"""Add the missing CHECK on self_comparisons.ring_true (Γ-2 follow-up)

Revision ID: 064_self_comparison_ring_true
Revises: 063_insight_ring_true
Create Date: 2026-09-14

THE LAST OF THE THREE. `ring_true` means the same thing on mirrors (017),
insights (063) and self_comparisons — one speech act, one vocabulary — but only
two of the three have ever enforced it. 021 created this column as a bare
VARCHAR(10) with no constraint, and until Γ-2 the input schema was
`str(max_length=10)`, so any ten characters could be written and stored.

Nothing exploited that: the founder counted the off-vocabulary rows in production
on 2026-09-14 and the answer was ZERO, which is why this migration is a plain
ADD CONSTRAINT with no normalisation step and no NOT VALID escape hatch. It is
also why the count had to come first — a validating constraint against a table
holding even one bad row fails the deploy, and the failure would arrive as a
Render crash rather than as a review comment.

Same spelling as ck_mirrors_ring_true (017:31) and ck_insights_ring_true (063),
so the three read identically in psql and a future reader can grep one string and
find all of them.

Separate from 063 rather than merged into it: 063 shipped before the production
count existed, and rewriting a migration that has already been reviewed to add a
clause that needed different evidence would hide which fact justified which line.

C-05 (RLS on new tables) does not apply here: this migration creates NO table. It
adds a constraint to `self_comparisons`, which already has ROW LEVEL SECURITY
enabled by 052_enable_rls. Nothing about the RLS posture changes.
"""
from alembic import op

revision = '064_self_comparison_ring_true'
down_revision = '063_insight_ring_true'
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        'ck_self_comparisons_ring_true',
        'self_comparisons',
        "ring_true IN ('yes', 'partly', 'no')",
    )


def downgrade():
    op.drop_constraint(
        'ck_self_comparisons_ring_true', 'self_comparisons', type_='check'
    )
