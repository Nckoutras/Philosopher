"""Add auth_provider and oauth_provider_id to users

Revision ID: 014_user_oauth_cols
Revises: 013_conv_fk_ondelete
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '014_user_oauth_cols'
down_revision = '013_conv_fk_ondelete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('auth_provider', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('oauth_provider_id', sa.Text(), nullable=True))
    op.create_index('ix_users_oauth_provider_id', 'users', ['oauth_provider_id'])


def downgrade() -> None:
    op.drop_index('ix_users_oauth_provider_id', table_name='users')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'auth_provider')
