"""Add users.token_version (A16 — token revocation)

Revision ID: 053_token_version
Revises: 052_enable_rls
Create Date: 2026-08-13

Sign-out is client-side only: the frontend clears the cookie, localStorage and
store, but the JWT itself stays valid until natural expiry. A leaked or stolen
token could not be revoked at all. This column is the revocation counter — tokens
carry the version they were minted with ("ver"), both validators compare it
against this column, and incrementing it kills every token on every device.

Additive, NOT NULL DEFAULT 0. Existing rows backfill to 0 via the server default
— pure no-op for current data.

NO MASS LOGOUT ON DEPLOY. Every token minted before A16 has no "ver" claim, and
the validators read a missing claim as 0 — which is exactly this column's default.
So every currently-valid token stays valid and ages out naturally. The first
increment for a given user is what kills their old tokens, which is the intended
behaviour: a revocation must not spare pre-A16 tokens.

C-05 (RLS on new tables) does not apply here: this migration creates NO table. It
adds a column to `users`, which already has ROW LEVEL SECURITY enabled by
052_enable_rls. Nothing extra is needed, and nothing about the RLS posture changes.
"""
import sqlalchemy as sa
from alembic import op

revision = '053_token_version'
down_revision = '052_enable_rls'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('users', 'token_version')
