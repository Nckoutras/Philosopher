"""Record which share a signup came from — users.signup_share_id

Revision ID: 068_signup_share
Revises: 067_shares
Create Date: 2026-09-20

067 gave a share an identity. This is the other end of the loop: when an
account is created after someone opened a share link, the share that brought
them is recorded here.

IT STORES shares.id — THE OPAQUE PRIMARY KEY — AND NOT shares.public_id, AND
THAT IS THE LOAD-BEARING DETAIL OF THIS COLUMN. Both are unique identifiers for
the same row, so the choice looks arbitrary until you notice what public_id IS:

  **public_id is a CREDENTIAL.** It is the 22-character token in the share URL,
  and anyone holding it can read that share at /s/{public_id}. It is the only
  thing standing between a stranger and someone else's reflection.

  **shares.id is an opaque reference.** It grants nothing and reveals nothing.

This column sits on the row of the person who was RECRUITED — a third party to
the share. Storing public_id here would put a working access token for A's
share onto B's user row, and into B's data export, where it would survive A
later revoking the link: the exported file would still carry a token, and the
person reading it is not the person who withdrew it. That is the same class of
leak as putting snapshot text into og:description — content outliving its own
revocation somewhere we do not control. The UUID cannot leak that way because it
opens nothing.

WHAT THIS COLUMN IS *NOT*, AND WHY. Not `referred_by_user_id`. A self-referential
user FK writes "this person recruited that person" directly onto the recruited
person's row, where it outlives the share that caused it and is one join away
from nothing. Pointing at the SHARE instead means:

  - the link to a PERSON is indirect. Answering "who recruited whom" requires a
    deliberate join through `shares`; it is not a property of the user row.
  - it breaks by itself. Delete the share and the reference dangles into
    nothing, which is the correct lifetime for a record whose only reason to
    exist was that share. A user FK would have outlived it.

Both of those hold identically for shares.id and shares.public_id — the
indirection and the dangling are properties of pointing at the share, not of
which of its two ids you use. The bearer-token argument above is what decides
between them.

NO FOREIGN KEY, for the same reason 067's artifact_id has none: a CASCADE would
erase the origin of a signup when a sharer tidied up their links, and a RESTRICT
would stop them deleting their own share because a stranger once used it.
Neither is right. This is provenance, not a reference.

IT ALSO MAKES THE ANALYTICS JOIN DIRECT. share_created, share_landing_view and
share_signup all carry `share_id` = shares.id, so this column holds the same
value the events do. Storing public_id would have left every DB-to-PostHog
query needing an undocumented hop through `shares` to translate — the kind of
step that is discovered late, by someone writing their first attribution query.

IDEMPOTENCY IS THE OTHER HALF OF ITS JOB. Attribution is triggered by a call the
CLIENT makes after signup, so a refresh, a retry or a double-mounted effect can
fire it twice. `attribute_signup` writes only when the column is NULL, which
makes "at most one share_signup per account" a property of the database rather
than a property of the client behaving.

NO RLS CHANGE. C-05 governs migrations that CREATE a public table; this adds a
column to `users`, which has had RLS enabled since 052. Said explicitly rather
than left for a reader to wonder about, exactly as 053 and 054 do.

Nullable with no default and no backfill: every account that existed before this
shipped arrived from somewhere we did not record, and writing anything into
those rows would be inventing data. NULL means "we do not know", which is true.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '068_signup_share'
down_revision = '067_shares'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        # UUID(as_uuid=False) to match shares.id exactly — the model maps it to
        # `str`, which is what the analytics payloads and every comparison in
        # this codebase already expect.
        sa.Column('signup_share_id', postgresql.UUID(as_uuid=False), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'signup_share_id')
