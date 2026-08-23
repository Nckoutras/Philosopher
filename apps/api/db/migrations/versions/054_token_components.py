"""Add messages token-component columns (input / cache_creation / cache_read)

Revision ID: 054_token_components
Revises: 053_token_version
Create Date: 2026-08-23

messages.tokens_used (#556) stores the SUM of the four Anthropic usage fields.
The four are disjoint, so the sum is the true prompt+output volume — but they
price very differently: input 1.0x, cache_creation 1.25x, cache_read 0.1x. Two
messages with identical tokens_used can therefore differ by ~10x in actual
spend. A consumption ceiling built on the sum would protect VOLUME, not COST.

These three columns store the raw components. Raw stays re-interpretable when
pricing changes; a cost-weighted scalar computed at write time would freeze
today's rates into historical rows and could never be recovered. Every future
computation — ceiling thresholds, unit economics — happens in SQL over these.

NO output_tokens COLUMN, DELIBERATELY. It is derivable:

    output = tokens_used - (input_tokens + cache_creation_tokens + cache_read_tokens)

That identity holds even when a single message accumulates several API calls
(stream_response's post-processing correction regenerates the reply and adds to
the same sink), because every component accumulates in lockstep with the total.
A fourth column would be a second source of truth for a value already implied by
the other four, and the first drift between them would be unresolvable.

Additive and nullable, NO BACKFILL. NULL means "written before component logging
existed", which is every row up to this deploy. It does NOT mean zero: zero is a
legitimate stored value — cache_read_tokens = 0 is exactly what an uncached
request records — and the two must stay distinguishable.

tokens_used is UNCHANGED in meaning and in value. These columns are additive
information beside it, not a redefinition of it.

C-05 (RLS on new tables) does not apply here: this migration creates NO table. It
adds columns to `messages`, which already has ROW LEVEL SECURITY enabled by
052_enable_rls. Nothing about the RLS posture changes.
"""
import sqlalchemy as sa
from alembic import op

revision = '054_token_components'
down_revision = '053_token_version'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('messages', sa.Column('input_tokens', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('cache_creation_tokens', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('cache_read_tokens', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('messages', 'cache_read_tokens')
    op.drop_column('messages', 'cache_creation_tokens')
    op.drop_column('messages', 'input_tokens')
