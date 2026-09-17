"""Disclaimer 1.1 — the product name, and nothing else

Revision ID: 066_disclaimer_wise_room
Revises: 065_council_insight_id
Create Date: 2026-09-17

BUG-005. The consent gate every new user passes through still read "I understand
Great Minds is for reflection…" — the pre-rebrand product name. The string is NOT
in the frontend, the build output, or any code path: it is one row in
`disclaimer_versions`, seeded by 003_disclaimer_acceptances.py:42-49 (the string
itself at :47) and served to apps/web/app/auth/disclaimer/page.tsx.

WHY A NEW ROW AND NOT AN UPDATE. Migration 003 stays byte-identical (C-01): a
shipped migration's prose is a record of what ran, not a place to edit. And an
in-place UPDATE of row 1 would silently rewrite the text that 19 existing users
have already consented to, while their `disclaimer_acceptances` rows went on
pointing at it. A consent is to a SPECIFIC text; the record has to keep showing
what was agreed. So this is additive: row 1 is untouched, its acceptances stay
valid evidence of the 1.0 wording, and 1.1 is a new thing to be consented to.

WHAT CHANGES IN THE COPY: "Great Minds" → "The Wise Room". Nothing else.
Verified before this file was written, against PRODUCTION rather than against
the 003 literal:

    md5(live positioning_copy)                              = 8e7dc868…8c87
    md5(live copy with 'Great Minds'→'The Wise Room')       = 109ac920…c087
    md5(the literal below)                                  = 109ac920…c087

215 chars → 217, a delta of exactly len('The Wise Room') - len('Great Minds').
Both sentences intact, punctuation untouched. The founder's first draft of this
copy shortened the consent — dropping "diagnosis, crisis support, or medical
treatment" and the whole crisis-routing sentence, which is the only safety
instruction in the gate — and was withdrawn once the live row was read. No
shortening is intended here, now or as a follow-up; a shorter consent would be a
legal decision with its own review, not a rider on a rebrand.

EVERY EXISTING USER IS RE-PROMPTED, deliberately. `get_current_version` orders by
`effective_at DESC` (services/disclaimer_service.py:26-36), so 1.1 becomes
current the moment this runs. `user_needs_acceptance` (:39-56) looks for an
acceptance against the CURRENT version's id, finds none for 1.1, and
`needs_disclaimer` comes back true from routers/auth.py:52,83,101,305 and
auth_oauth.py:234 — the frontend then routes to /auth/disclaimer. At the time of
writing that is 19 users with a 1.0 acceptance each, out of 22.

NO SCHEMA CHANGE, so C-05 does not apply: this migration creates no table and
enables no RLS. It inserts one row into a table 052 already covered.

`effective_at` is left to its server default (`now()`), which is the moment of
the deploy that runs this. Not a chosen timestamp: the selection query has no
`WHERE effective_at <= now()`, so a future-dated row would be served immediately
rather than scheduled — see TD-80.
"""
from alembic import op

revision = '066_disclaimer_wise_room'
down_revision = '065_council_insight_id'
branch_labels = None
depends_on = None

def upgrade():
    # Frozen inline literal (C-01), in ONE place. Written out in full rather than
    # derived from row 1 with a SQL replace(): what this migration inserts is
    # readable here and cannot change if row 1 is ever touched by anything else.
    # age_copy carries no product name and is repeated verbatim from 1.0.
    #
    # Deliberately NOT also assigned to a module constant. The consent text
    # appearing twice in one file is a drift hazard, and the copy that matters is
    # the one Postgres receives.
    op.execute(
        """
        INSERT INTO disclaimer_versions (version_string, age_copy, positioning_copy)
        VALUES (
            '1.1',
            'I am 18 years or older.',
            'I understand The Wise Room is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional.'
        )
        """
    )


def downgrade():
    # Deletes the VERSION only, never an acceptance. If anyone has consented to
    # 1.1 by the time this runs, the FK from disclaimer_acceptances.version_id
    # (003:30) raises and the whole downgrade rolls back — loudly, and with the
    # consent record intact.
    #
    # That refusal is the intended behaviour, not an oversight. The alternative
    # is deleting the acceptance rows first, which would destroy evidence of a
    # consent a real person actually gave in order to undo a text change. A
    # downgrade that stops and makes someone look is the correct failure here.
    op.execute("DELETE FROM disclaimer_versions WHERE version_string = '1.1'")
