"""Add council_sessions.synthesis_structured (decision-instrument synthesis)

Revision ID: 042_council_synthesis_json
Revises: 041_counterview_still_stands
Create Date: 2026-07-09

Additive, nullable: the structured close of a council — real_question / tension /
verdict / next_move — stored as JSONB. The flat `synthesis` Text column stays
populated (with the verdict beat) so the Reflections feed and share card keep
reading it unchanged. Old sessions have synthesis_structured NULL and the live
screen falls back to the flat synthesis.
"""
from alembic import op

revision = '042_council_synthesis_json'
down_revision = '041_counterview_still_stands'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE council_sessions ADD COLUMN synthesis_structured JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE council_sessions DROP COLUMN IF EXISTS synthesis_structured")
