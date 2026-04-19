"""Initial schema

Revision ID: 001_initial
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # users
    op.create_table(
        'users',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('email',           sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.Text),
        sa.Column('full_name',       sa.String(255)),
        sa.Column('avatar_url',      sa.Text),
        sa.Column('onboarded_at',    sa.DateTime(timezone=True)),
        sa.Column('is_admin',        sa.Boolean, server_default='false'),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id',                     UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',                UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stripe_customer_id',     sa.String(255), unique=True, nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True),
        sa.Column('plan',                   sa.String(50),  server_default='free'),
        sa.Column('status',                 sa.String(50),  server_default='active'),
        sa.Column('current_period_end',     sa.DateTime(timezone=True)),
        sa.Column('cancel_at_period_end',   sa.Boolean, server_default='false'),
        sa.Column('created_at',             sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at',             sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # personas
    op.create_table(
        'personas',
        sa.Column('id',         UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('slug',       sa.String(100), unique=True, nullable=False),
        sa.Column('name',       sa.String(255), nullable=False),
        sa.Column('era',        sa.String(100)),
        sa.Column('tradition',  sa.String(100)),
        sa.Column('tier',       sa.String(50),  server_default='free'),
        sa.Column('is_active',  sa.Boolean,     server_default='true'),
        sa.Column('config',     JSONB,          nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # conversations
    op.create_table(
        'conversations',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',         UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_id',      UUID(as_uuid=False), sa.ForeignKey('personas.id'), nullable=False),
        sa.Column('title',           sa.String(500)),
        sa.Column('ritual_id',       UUID(as_uuid=False)),
        sa.Column('message_count',   sa.Integer, server_default='0'),
        sa.Column('last_message_at', sa.DateTime(timezone=True)),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_conv_user', 'conversations', ['user_id', 'last_message_at'])

    # messages
    op.create_table(
        'messages',
        sa.Column('id',               UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('conversation_id',  UUID(as_uuid=False), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id',          UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role',             sa.String(20), nullable=False),
        sa.Column('content',          sa.Text, nullable=False),
        sa.Column('tokens_used',      sa.Integer),
        sa.Column('retrieval_ids',    JSONB),
        sa.Column('safety_level',     sa.String(20), server_default='none'),
        sa.Column('persona_override', sa.Boolean, server_default='false'),
        sa.Column('latency_ms',       sa.Integer),
        sa.Column('created_at',       sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id', 'created_at'])

    # memory_entries
    op.create_table(
        'memory_entries',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',         UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_id',      UUID(as_uuid=False), sa.ForeignKey('personas.id')),
        sa.Column('conversation_id', UUID(as_uuid=False), sa.ForeignKey('conversations.id')),
        sa.Column('entry_type',      sa.String(50), nullable=False),
        sa.Column('content',         sa.Text, nullable=False),
        sa.Column('embedding',       Vector(1536)),
        sa.Column('confidence',      sa.Float, server_default='1.0'),
        sa.Column('source_turn',     sa.Integer),
        sa.Column('is_active',       sa.Boolean, server_default='true'),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_memory_user', 'memory_entries', ['user_id', 'is_active'])
    op.execute("""
        CREATE INDEX idx_memory_embedding
        ON memory_entries USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # insights
    op.create_table(
        'insights',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',         UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=False), sa.ForeignKey('conversations.id')),
        sa.Column('persona_id',      UUID(as_uuid=False), sa.ForeignKey('personas.id')),
        sa.Column('content',         sa.Text, nullable=False),
        sa.Column('insight_type',    sa.String(50)),
        sa.Column('is_dismissed',    sa.Boolean, server_default='false'),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # rituals
    op.create_table(
        'rituals',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('slug',            sa.String(100), unique=True, nullable=False),
        sa.Column('name',            sa.String(255), nullable=False),
        sa.Column('description',     sa.Text),
        sa.Column('persona_id',      UUID(as_uuid=False), sa.ForeignKey('personas.id')),
        sa.Column('tier',            sa.String(50), server_default='free'),
        sa.Column('prompt_template', sa.Text, nullable=False),
        sa.Column('frequency',       sa.String(50), server_default='daily'),
        sa.Column('is_active',       sa.Boolean, server_default='true'),
    )

    # user_ritual_completions
    op.create_table(
        'user_ritual_completions',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',         UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('ritual_id',       UUID(as_uuid=False), sa.ForeignKey('rituals.id'), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=False), sa.ForeignKey('conversations.id')),
        sa.Column('completed_at',    sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    # source_chunks
    op.create_table(
        'source_chunks',
        sa.Column('id',           UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('persona_id',   UUID(as_uuid=False), sa.ForeignKey('personas.id')),
        sa.Column('source_title', sa.String(500), nullable=False),
        sa.Column('source_type',  sa.String(100), nullable=False),
        sa.Column('content',      sa.Text, nullable=False),
        sa.Column('embedding',    Vector(1536)),
        sa.Column('page_ref',     sa.String(100)),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_chunks_persona', 'source_chunks', ['persona_id'])
    op.execute("""
        CREATE INDEX idx_chunks_embedding
        ON source_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # safety_events
    op.create_table(
        'safety_events',
        sa.Column('id',              UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id',         UUID(as_uuid=False), sa.ForeignKey('users.id')),
        sa.Column('conversation_id', UUID(as_uuid=False), sa.ForeignKey('conversations.id')),
        sa.Column('message_id',      UUID(as_uuid=False), sa.ForeignKey('messages.id')),
        sa.Column('trigger_stage',   sa.String(50), nullable=False),
        sa.Column('risk_level',      sa.String(50), nullable=False),
        sa.Column('category',        sa.String(100)),
        sa.Column('action_taken',    sa.String(100), nullable=False),
        sa.Column('raw_flags',       JSONB),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade():
    for table in [
        'safety_events', 'source_chunks', 'user_ritual_completions',
        'rituals', 'insights', 'memory_entries', 'messages',
        'conversations', 'personas', 'subscriptions', 'users',
    ]:
        op.drop_table(table)
