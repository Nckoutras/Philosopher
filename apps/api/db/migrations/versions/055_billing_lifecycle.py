"""Webhook idempotency, event ordering, billing interval, lifecycle history

Revision ID: 055_billing_lifecycle
Revises: 054_token_components
Create Date: 2026-09-01

The Stripe webhook processed every delivery as if it were the first and only
one. Stripe retries on any non-2xx and can deliver out of order, so a retried
customer.subscription.deleted could overwrite a newer .updated, and a duplicate
checkout.session.completed fired subscription_activated twice. With live keys
that is money: a paying user flips to free, or a cancelled one stays Pro.

WHAT EACH PIECE IS FOR.

stripe_events — the idempotency key, and its primary key IS Stripe's event id.
A duplicate delivery becomes a constraint violation rather than a judgement
call. `created` is Stripe's own clock and is what ordering is judged on;
received_at is ours and is only for forensics. processed_at NULL means in
flight or crashed; `skipped` true means recorded and deliberately not applied
because it was older than what the row had already seen — the two must stay
distinguishable, which is why skipped is a column and not an absence.

subscriptions.last_stripe_event_at — the ordering baseline. NULL means no event
has been applied yet and the event should be APPLIED, not skipped: the 6-hourly
reconcile cron (workers/cron.py) writes `status` without going through the
webhook, so a row it has touched would otherwise sit behind a baseline nothing
ever sets.

subscriptions.interval — so the database can answer "how often is this billed"
without a Stripe API call. PR #5's grace window and #11's fair-use both need it.

subscriptions.pro_since — when the row FIRST became paying Pro, NULL again after
a cancel so a re-subscribe starts a fresh tenure. This exists because
subscription_canceled.tenure_days was computed from created_at, which is stamped
at SIGNUP when every row is created on the free plan — so it measured account
age, not how long somebody paid, which is the entire distinction the event was
added to make.

subscription_events — one row per state-changing webhook. The subscriptions
table records only the current state, so a user reporting "I was charged and
then lost access" leaves nothing to read back. Nobody reads this yet; PR #5
builds the cancel reason and the 14-day feature summary on it.

NO BACKFILL, on any of the three columns. NULL means "before this deploy", and
the rows that predate it are comp grants and archived test accounts. Inventing a
pro_since for them would put fabricated tenures into the first cohort analysis
that reads the column.

RLS (C-05). Both new tables get ENABLE ROW LEVEL SECURITY in this migration, in
the shape 052_enable_rls established and verified against production: enabled,
ZERO policies, no FORCE. With no policies and no FORCE the owner still sees
everything and every non-owner role sees nothing. The API connects as the table
owner and owners bypass RLS, so this never gates the API; what it closes is the
PostgREST anon/authenticated surface, where an unauthenticated caller would
otherwise read every row of a new table. Adding policies is a separate decision
requiring its own review, exactly as 052 says.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = '055_billing_lifecycle'
down_revision = '054_token_components'
branch_labels = None
depends_on = None


def upgrade():
    # ── subscriptions: three additive nullable columns, no backfill ──────────
    op.add_column('subscriptions', sa.Column('interval', sa.String(length=10), nullable=True))
    op.add_column('subscriptions', sa.Column('pro_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'subscriptions',
        sa.Column('last_stripe_event_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── stripe_events ────────────────────────────────────────────────────────
    op.create_table(
        'stripe_events',
        # Stripe's event id (evt_…). Text rather than a bounded String: Stripe
        # does not document a maximum length, and a truncating column on the
        # idempotency key would silently collide two different events.
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('type', sa.String(length=100), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'received_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'skipped', sa.Boolean(),
            server_default=sa.text('false'), nullable=False,
        ),
    )
    # Answers "what has this endpoint been sent lately, and did any of it stall"
    # without a sequential scan once the table is large.
    op.create_index('ix_stripe_events_created', 'stripe_events', ['created'])
    op.create_index('ix_stripe_events_processed_at', 'stripe_events', ['processed_at'])

    # ── subscription_events ──────────────────────────────────────────────────
    op.create_table(
        'subscription_events',
        # gen_random_uuid() server-side as well as the model's Python default,
        # following 002_otp_codes: the model default only fires through the ORM,
        # and a row inserted by raw SQL would otherwise have no id.
        sa.Column(
            'id', UUID(as_uuid=False), primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'user_id', UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'subscription_id', UUID(as_uuid=False),
            sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False,
        ),
        # SET NULL, not CASCADE: the stripe_events row is DELETED when
        # processing crashes, and a history row must not be taken with it. The
        # transition stays on record with its provenance lost, which is strictly
        # better than losing the transition.
        sa.Column(
            'stripe_event_id', sa.Text(),
            sa.ForeignKey('stripe_events.id', ondelete='SET NULL'), nullable=True,
        ),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=True),
        sa.Column('from_plan', sa.String(length=50), nullable=True),
        sa.Column('to_plan', sa.String(length=50), nullable=True),
        sa.Column('interval', sa.String(length=10), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
    )
    # The read PR #5 will make: this user's history, newest first.
    op.create_index(
        'ix_subscription_events_user_created',
        'subscription_events', ['user_id', 'created_at'],
    )

    # ── RLS (C-05) — same shape as 052: enabled, zero policies, no FORCE ─────
    op.execute('ALTER TABLE public.stripe_events ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE public.subscription_events ENABLE ROW LEVEL SECURITY;')


def downgrade():
    op.execute('ALTER TABLE public.subscription_events DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE public.stripe_events DISABLE ROW LEVEL SECURITY;')
    op.drop_index('ix_subscription_events_user_created', table_name='subscription_events')
    op.drop_table('subscription_events')
    op.drop_index('ix_stripe_events_processed_at', table_name='stripe_events')
    op.drop_index('ix_stripe_events_created', table_name='stripe_events')
    op.drop_table('stripe_events')
    op.drop_column('subscriptions', 'last_stripe_event_at')
    op.drop_column('subscriptions', 'pro_since')
    op.drop_column('subscriptions', 'interval')
