"""Create shares — a share becomes an object with a lifetime

Revision ID: 067_shares
Revises: 066_disclaimer_wise_room
Create Date: 2026-09-20

WHAT THIS CHANGES ABOUT SHARING. Until now six endpoints rendered a PNG, handed
back the bytes and persisted NOTHING (routers/share.py said so in a comment).
A share had no identity, so there was nothing to link to, nothing to attribute a
signup to, and nothing to switch off. This table is what makes all three
expressible; PR-1 uses the first and the third.

THE SNAPSHOT IS THE POINT, AND IT IS WHY artifact_id CARRIES NO FOREIGN KEY.
The public page at /s/{public_id} reads `snapshot` and NEVER reads the source
artifact. That is a founder ruling, and the schema has to hold it up:

  - ON DELETE CASCADE would delete the share when the artifact goes, so deleting
    a reflection would silently break every link already in circulation.
  - ON DELETE RESTRICT would refuse to delete the artifact, so a share would
    quietly take away a user's ability to delete their own reflection.

Both contradict the ruling, so artifact_id is a bare UUID kept for provenance
and debugging. The cost is named rather than hidden: DELETING AN ARTIFACT DOES
NOT UNPUBLISH A SHARE OF IT. A user who deletes a reflection and expects the
public page to go with it has to turn the link off as a separate act. Account
deletion is unaffected — user_id CASCADEs, and account deletion is a single
DELETE FROM users (056 closed the last of those FKs), so erasure still takes
every share with it.

PUBLIC_ID IS NOT THE PRIMARY KEY, DELIBERATELY. `id` stays a UUID for joins and
any future FK; `public_id` is the 22-character token that appears in the URL and
on the card. Keeping them separate means the token could be rotated without
rewriting references, and means the PK is never guessable from a link.

  secrets.token_urlsafe(16) -> 22 chars, 128 bits, alphabet [A-Za-z0-9_-].

Why not the UUID itself: 36 characters instead of 22, and it welds the public
identifier to the primary key. Why not base32 (which QR's alphanumeric mode
covers): the payload is https://<host>/s/<token> and the lowercase scheme and
host force byte mode regardless, so base32 would cost 4 characters and buy
nothing. At 22 the whole URL is ~48 characters — a low-density QR that survives
being photographed off someone else's phone screen.

NO view_count, AND THAT IS A RULING TOO. v1 shows the sharer no view statistics,
so the column does not exist rather than existing unread. A column that nothing
writes is an invitation to assume it means zero.

REVOCATION IS revoked_at, NOT A DELETE. A revoked share must still resolve, so
the page can say it was withdrawn rather than 404 — a 404 reads as a broken app
to someone who just scanned a friend's card. The row therefore outlives the
revocation, and the landing route stops returning `snapshot` once it is set.

RLS (C-05): enabled here, zero policies, no FORCE — the shape 052, 059 and 061
use. The API connects as the table owner and owners bypass RLS, so the public
landing route still reads normally. What it closes is the PostgREST anon
surface, which matters more on this table than on most: it is the one table in
the schema that is reached from an unauthenticated page, and every row in it is
a pointer to something a person wrote.

STYLE follows 061_trajectory_snapshots: op.create_table / sa.Column /
op.create_index rather than raw SQL, and the UUID primary key carries
server_default gen_random_uuid() AS WELL AS the model's Python default.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '067_shares'
down_revision = '066_disclaimer_wise_room'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'shares',
        sa.Column(
            'id', postgresql.UUID(as_uuid=False), primary_key=True,
            server_default=sa.text('gen_random_uuid()'), nullable=False,
        ),
        # The URL token. 22 chars is exactly len(secrets.token_urlsafe(16)); the
        # column is sized to it rather than to a round number so a scheme change
        # has to come past a migration.
        sa.Column('public_id', sa.String(22), nullable=False),
        sa.Column(
            'user_id', postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('artifact_type', sa.String(20), nullable=False),
        # No FK — see the module docstring. This is provenance, not a reference.
        sa.Column('artifact_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('snapshot', postgresql.JSONB, nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_type IN ('line', 'quote', 'council', 'mirror', 'letter', 'counterview')",
            name='ck_shares_artifact_type',
        ),
    )

    # The lookup every public request makes. UNIQUE because a collision would
    # hand one person's link to another's artifact — 128 bits makes that
    # vanishingly unlikely and the constraint makes it impossible.
    op.create_index('uq_shares_public_id', 'shares', ['public_id'], unique=True)

    # For a future "your shares" list, and for answering "what did this account
    # share, and when" without a sequential scan.
    op.create_index(
        'ix_shares_user_created', 'shares',
        ['user_id', sa.text('created_at DESC')],
    )

    # NO INDEX ON artifact_id, deliberately. Nothing queries by it in v1 — the
    # landing page reads the snapshot and the source artifact is never consulted.
    # A "deleting an artifact revokes its shares" feature would need one, and
    # that feature can bring its own.

    # ── RLS (C-05) — enabled, zero policies, no FORCE ─────────────────────────
    op.execute('ALTER TABLE public.shares ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    op.execute('ALTER TABLE public.shares DISABLE ROW LEVEL SECURITY;')
    op.drop_index('ix_shares_user_created', table_name='shares')
    op.drop_index('uq_shares_public_id', table_name='shares')
    op.drop_table('shares')
