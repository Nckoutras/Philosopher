"""Create counterview_turns table (bounded user rebuttal exchange)

Revision ID: 038_counterview_turns
Revises: 037_user_preferences_profile
Create Date: 2026-06-26

Additive, new table. Lets a generated Counterview hold a SHORT, bounded sequence
of user rebuttals, each answered by the CURRENT speaker (one persona). Kept on its
own table so the verdict/go-deeper model (`counterview_responses.round`, capped at
1, written by generate_deeper) is left completely untouched — the two axes never
share a key:

- counterview_responses.round  = a persona's elaboration depth (0 verdict, 1 deeper)
- counterview_turns.sequence    = the rebuttal exchange order (new, independent)

One row per rebuttal turn:
- `persona_slug` is the persona the rebuttal targets (= the current speaker = who
  answers), so the response attributes correctly even if the user switches voices.
- `user_text` is the user's rebuttal (it passed safety check_input before insert).
- `persona_response` is the persona's <=18-word reply; NULL when status != generated.
- `status` mirrors the verdict vocabulary ('generated' | 'empty' | 'suppressed').
- UNIQUE (counterview_id, sequence) orders the thread AND guards the insert race
  (mirrors uq_counterview_response). The free 3-rebuttal cap counts status='generated'
  turns only, enforced in the service (not at the DB).
"""
from alembic import op

revision = '038_counterview_turns'
down_revision = '037_user_preferences_profile'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE counterview_turns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            counterview_id UUID NOT NULL REFERENCES counterviews(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            persona_slug VARCHAR(100) NOT NULL,
            user_text TEXT NOT NULL,
            persona_response TEXT,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_counterview_turns_status CHECK (status IN ('generated', 'empty', 'suppressed')),
            CONSTRAINT uq_counterview_turn_seq UNIQUE (counterview_id, sequence)
        )
    """)
    op.execute("CREATE INDEX ix_counterview_turns_cv ON counterview_turns (counterview_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS counterview_turns")
