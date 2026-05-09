"""Disclaimer versions and acceptances tables

Revision ID: 003_disclaimer_acceptances
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET

revision = '003_disclaimer_acceptances'
down_revision = '002_otp_codes'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'disclaimer_versions',
        sa.Column('id',               sa.Integer,              primary_key=True, autoincrement=True),
        sa.Column('version_string',   sa.String(20),           nullable=False, unique=True),
        sa.Column('age_copy',         sa.Text,                 nullable=False),
        sa.Column('positioning_copy', sa.Text,                 nullable=False),
        sa.Column('effective_at',     sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'disclaimer_acceptances',
        sa.Column('id',                    UUID(as_uuid=False),    primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',               UUID(as_uuid=False),    sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_id',            sa.Integer,             sa.ForeignKey('disclaimer_versions.id'), nullable=False),
        sa.Column('accepted_at',           sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('locale',                sa.String(10),          nullable=False, server_default='en'),
        sa.Column('confirmed_age_18',      sa.Boolean,             nullable=False),
        sa.Column('confirmed_non_therapy', sa.Boolean,             nullable=False),
        sa.Column('ip_address',            INET,                   nullable=True),
        sa.Column('user_agent',            sa.Text,                nullable=True),
        sa.UniqueConstraint('user_id', 'version_id', name='uq_disclaimer_acceptances_user_version'),
    )

    op.create_index('ix_disclaimer_acceptances_user', 'disclaimer_acceptances', ['user_id'])

    op.execute("""
        INSERT INTO disclaimer_versions (version_string, age_copy, positioning_copy)
        VALUES (
            '1.0',
            'I am 18 years or older.',
            'I understand Great Minds is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional.'
        )
    """)


def downgrade():
    op.drop_index('ix_disclaimer_acceptances_user', table_name='disclaimer_acceptances')
    op.drop_table('disclaimer_acceptances')
    op.drop_table('disclaimer_versions')
