"""OTP codes table

Revision ID: 002_otp_codes
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '002_otp_codes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'otp_codes',
        sa.Column('id',         UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('email',      sa.String(255), nullable=False),
        sa.Column('code_hash',  sa.String(128), nullable=False),
        sa.Column('salt',       sa.String(32),  nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts',   sa.Integer, nullable=False, server_default='0'),
        sa.Column('used_at',    sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_otp_codes_email_created', 'otp_codes', ['email', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('ix_otp_codes_email_created', table_name='otp_codes')
    op.drop_table('otp_codes')
