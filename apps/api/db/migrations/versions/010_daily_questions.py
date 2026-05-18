"""Daily questions — rotating daily reflection prompt (A0/D1)

Revision ID: 010_daily_questions
Revises: 009_saved_lines
Create Date: 2026-05-18
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision = '010_daily_questions'
down_revision = '009_saved_lines'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'daily_questions',
        sa.Column('id', UUID(as_uuid=False), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('display_order', sa.Integer, nullable=False, unique=True),
        sa.Column('active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_daily_questions_active_order', 'daily_questions', ['active', 'display_order'])

    questions = [
        (1,  "What are you pretending not to know?"),
        (2,  "Whose approval are you still waiting for?"),
        (3,  "What story about yourself has become too useful?"),
        (4,  "Where are you mistaking habit for character?"),
        (5,  "What do you know, but refuse to admit?"),
        (6,  "What are you protecting by staying busy?"),
        (7,  "Where has your time stopped telling the truth?"),
        (8,  "What are you postponing until life feels safer?"),
        (9,  "What choice keeps returning in different clothes?"),
        (10, "What have you abandoned without saying so?"),
        (11, "What do you expect from others but rarely give?"),
        (12, "Whom do you resent for seeing you clearly?"),
        (13, "What kindness are you withholding out of pride?"),
        (14, "What truth would change your next decision?"),
        (15, "What lie has become convenient enough to keep?"),
        (16, "What fear has learned to sound reasonable?"),
        (17, "What would you attempt without witnesses?"),
        (18, "Where are you obeying an old fear?"),
        (19, "What do you want without wanting to confess it?"),
        (20, "What desire have you disguised as discipline?"),
        (21, "What are you chasing that never satisfies you?"),
        (22, "Who are you becoming when no one interrupts?"),
        (23, "What part of you has outlived its usefulness?"),
        (24, "Which version of you are you still defending?"),
        (25, "What work deserves more of your seriousness?"),
        (26, "What are you building that can outlast attention?"),
        (27, "Where has ambition become a hiding place?"),
        (28, "What ending have you delayed by naming it hope?"),
        (29, "What would you mourn if it never returned?"),
        (30, "What remains when your excuses are taken away?"),
    ]

    conn = op.get_bind()
    for order, text in questions:
        conn.execute(
            sa.text(
                "INSERT INTO daily_questions (question_text, display_order, active) "
                "VALUES (:text, :order, true)"
            ),
            {"text": text, "order": order},
        )


def downgrade() -> None:
    op.drop_index('ix_daily_questions_active_order', table_name='daily_questions')
    op.drop_table('daily_questions')
