"""User preferences table

Revision ID: 004_user_preferences
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = '004_user_preferences'
down_revision = '003_disclaimer_acceptances'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_preferences',
        sa.Column('user_id',    UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('themes',     ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column('other_text', sa.Text()),
        sa.Column('need_most',  sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint(
            'cardinality(themes) >= 1 OR other_text IS NOT NULL',
            name='ck_user_preferences_some_input',
        ),
    )


def downgrade():
    op.drop_table('user_preferences')
