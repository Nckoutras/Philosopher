"""Create council_cases, council_sessions, council_responses tables

Revision ID: 019_create_council
Revises: 018_user_mirror_host
Create Date: 2026-06-01
"""
from alembic import op

revision = '019_create_council'
down_revision = '018_user_mirror_host'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE council_cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source VARCHAR(20) NOT NULL DEFAULT 'direct',
            mirror_id UUID REFERENCES mirrors(id) ON DELETE SET NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            session_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            closed_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_council_cases_user_id ON council_cases (user_id)")
    op.execute("CREATE INDEX ix_council_cases_user_created ON council_cases (user_id, created_at)")

    op.execute("""
        CREATE TABLE council_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id UUID NOT NULL REFERENCES council_cases(id) ON DELETE CASCADE,
            session_number INTEGER NOT NULL,
            input_text TEXT NOT NULL,
            synthesis TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'generating',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_council_sessions_case_number UNIQUE (case_id, session_number)
        )
    """)
    op.execute("CREATE INDEX ix_council_sessions_case_id ON council_sessions (case_id)")

    op.execute("""
        CREATE TABLE council_responses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES council_sessions(id) ON DELETE CASCADE,
            persona_slug VARCHAR(100) NOT NULL,
            position INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            quote TEXT,
            quote_source VARCHAR(200),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_council_responses_session_id ON council_responses (session_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS council_responses")
    op.execute("DROP TABLE IF EXISTS council_sessions")
    op.execute("DROP TABLE IF EXISTS council_cases")
