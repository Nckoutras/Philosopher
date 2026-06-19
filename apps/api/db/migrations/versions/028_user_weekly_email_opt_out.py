"""Add weekly_email_opt_out to users table

Revision ID: 028_user_weekly_email_opt_out
Revises: 027_add_orwell_musashi
Create Date: 2026-06-19

Schema-only. Adds a single boolean opt-out flag for the weekly-letter email.
NOT NULL DEFAULT false so every existing row is opted IN by default; the
public /unsubscribe/weekly endpoint flips it to true.
"""
from alembic import op

revision = '028_user_weekly_email_opt_out'
down_revision = '027_add_orwell_musashi'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN weekly_email_opt_out BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS weekly_email_opt_out")
