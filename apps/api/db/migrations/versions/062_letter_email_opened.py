"""Add weekly_letters.email_opened_at (Γ-1 — letter attribution)

Revision ID: 062_letter_email_opened
Revises: 061_trajectory_snapshots
Create Date: 2026-09-14

WHAT THIS CLOSES. `email_sent_at` and `read_at` already sit on this row, so
"a letter was opened within 72h of delivery" has always been computable. What
was NOT computable is whether the EMAIL caused the open: `read_at` is written by
the first authenticated fetch of the letter from any door — the Home card and
the letters list write it exactly as an email click does. The 72h number was
therefore an over-count of the Blueprint §16 gate, which asks specifically that
a delivered letter CAUSE an authenticated return.

This column records only the email-attributed open. The letter email's read link
now carries `?src=email` (workers/arq_worker.py), the frontend forwards it, and
GET /weekly-letters/{id} stamps this column the FIRST time it sees it.

IDEMPOTENT BY THE NULL CHECK, not by a constraint: the router writes only when
the column IS NULL, so a second visit from the same email — or a forwarded link
opened a week later — never moves the timestamp. The first email-attributed open
is the event the gate is about.

KNOWN UNDER-COUNT, deliberately not fixed here. A signed-out click lands on
/auth?mode=signin and post-verify goes to /app/today; there is no returnTo
mechanism in the app, so both the deep link and `?src=email` are lost and that
person is never counted. The column therefore reports a FLOOR on email-caused
returns, never a ceiling — which is the safe direction for a gate you must clear.

C-05 (RLS on new tables) does not apply here: this migration creates NO table.
It adds a nullable column to `weekly_letters`, which already has ROW LEVEL
SECURITY enabled by 052_enable_rls. Nothing about the RLS posture changes.

Nullable with no server default — NULL means "never opened from the email", which
is the correct reading for every row that predates this migration. A DEFAULT here
would be a lie about history.
"""
import sqlalchemy as sa
from alembic import op

revision = '062_letter_email_opened'
down_revision = '061_trajectory_snapshots'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'weekly_letters',
        sa.Column('email_opened_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('weekly_letters', 'email_opened_at')
