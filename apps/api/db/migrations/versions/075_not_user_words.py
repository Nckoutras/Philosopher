"""Retire memory rows taken from auto-sent daily topics; mark those topic turns

Revision ID: 075_not_user_words
Revises: 074_memory_callbacks
Create Date: 2026-10-13

UAT-TOPIC-001 PR-B (founder rulings 2026-10-12, IMPLEMENTATION_BACKLOG_v29.md
§ UAT-TOPIC-001). PR-A (#790) stops NEW topic turns reaching extraction and marks
them message_kind='daily_topic'. This cleans up what happened before it.

THE DEFECT. Quick start with an empty textarea seeds the day's topic itself and
auto-sends it as the first user turn. It was stored as an ordinary user message, and
extract_memory_task attributed the topic's claim to the person.

ONE TRANSACTION (env.py runs the upgrade in one), three steps:
  1. widen ck_memory_entries_inactive_reason with 'not_user_words';
  2. retire every ACTIVE memory row derived from a topic turn, on every account,
     to is_active=false, inactive_reason='not_user_words'. Rows that are already
     inactive (in production: 6, all 'superseded') keep their reason (ruling);
  3. re-mark every topic turn still 'standard' as message_kind='daily_topic', so
     the historical turns read the same as the ones PR-A marks.

THE MATCHING RULE (Step 0 of the UAT-D1 investigation, executed against Oregon
read-only on 2026-10-12 and again on 2026-10-13 with identical counts):
  topic turn  a role='user' message whose btrim'd content equals a btrim'd
              daily_questions row (active or not), or that row followed by the
              since-retired tail " Let's think through this together — where
              would you start?" (U+2014, ASCII apostrophe; 6 June messages).
  derived row a memory row linked by source_message_ids[1] = the topic turn; or,
              for rows with no source_message_ids (pre-070), a row in the same
              conversation created after the topic turn and before the next user
              message in it (or at any time after, if there is none). A linked row
              is judged by its link alone, never by timing.

  Measured on Oregon, 2026-10-13: 47 topic turns (41 exact + 6 tailed, every one a
  thread's first user turn, all 'standard'); 91 derived rows, 85 active, 6 inactive
  (all 'superseded'), 17 linked. The rule is not given those numbers: it runs on CI's
  database and on any rebuilt one too, so it counts and checks itself instead.

THE GUARD. The rows retired must equal the active derived rows counted beforehand,
and the turns marked must equal the 'standard' topic turns counted beforehand;
afterwards both counts must be zero. Anything else raises, and the whole upgrade
rolls back to 074 (049 precedent). Both counts are printed to the deploy log.

The statements are module-level so tests/db_live/test_not_user_words_075.py runs
THESE strings, not copies of them (071 precedent).

DOWNGRADE reactivates the 'not_user_words' rows (is_active=true, reason NULL) and
narrows the constraint back. That is an exact reversal: no other writer sets the
reason, and every such row was active before this ran. It does NOT reset the
re-marked messages: after PR-A a 'daily_topic' turn is written at send time too, the
two cannot be told apart, and message_kind has no constraint that would reject them.

Self-contained per C-01: no application import. C-04: the id is 18 characters and
the filename equals it. C-05: no table is created.
"""
import sqlalchemy as sa
from alembic import op

revision = '075_not_user_words'
down_revision = '074_memory_callbacks'
branch_labels = None
depends_on = None


TOPIC_CTE = """
    WITH topic AS (
        SELECT DISTINCT m.id, m.conversation_id, m.created_at, m.message_kind
        FROM messages m
        JOIN daily_questions q
          ON btrim(m.content) = btrim(q.question_text)
          OR btrim(m.content) = btrim(q.question_text)
             || ' Let''s think through this together ' || chr(8212) || ' where would you start?'
        WHERE m.role = 'user'
    ),
    bounded AS (
        SELECT t.*,
               (SELECT min(n.created_at) FROM messages n
                WHERE n.conversation_id = t.conversation_id
                  AND n.role = 'user'
                  AND n.created_at > t.created_at) AS next_user_at
        FROM topic t
    ),
    derived AS (
        SELECT DISTINCT e.id, e.is_active
        FROM memory_entries e
        JOIN bounded b
          ON (e.source_message_ids IS NOT NULL AND e.source_message_ids[1] = b.id)
          OR (e.source_message_ids IS NULL
              AND e.conversation_id = b.conversation_id
              AND e.created_at > b.created_at
              AND (b.next_user_at IS NULL OR e.created_at < b.next_user_at))
    )
"""

COUNT_SQL = TOPIC_CTE + """
    SELECT (SELECT count(*) FROM topic) AS topics,
           (SELECT count(*) FROM topic WHERE message_kind = 'standard') AS topics_standard,
           (SELECT count(*) FROM derived) AS rows_derived,
           (SELECT count(*) FROM derived WHERE is_active) AS rows_active
"""

RETIRE_SQL = TOPIC_CTE + """
    UPDATE memory_entries
    SET is_active = FALSE, inactive_reason = 'not_user_words'
    WHERE is_active
      AND id IN (SELECT id FROM derived)
"""

MARK_SQL = TOPIC_CTE + """
    UPDATE messages
    SET message_kind = 'daily_topic'
    WHERE message_kind = 'standard'
      AND id IN (SELECT id FROM topic)
"""

REACTIVATE_SQL = """
    UPDATE memory_entries
    SET is_active = TRUE, inactive_reason = NULL
    WHERE inactive_reason = 'not_user_words'
"""

WIDE = "inactive_reason IN ('superseded', 'user_removed', 'user_rejected', 'not_user_words')"
NARROW = "inactive_reason IN ('superseded', 'user_removed', 'user_rejected')"


def upgrade():
    op.drop_constraint('ck_memory_entries_inactive_reason', 'memory_entries', type_='check')
    op.create_check_constraint('ck_memory_entries_inactive_reason', 'memory_entries', WIDE)

    bind = op.get_bind()
    before = bind.execute(sa.text(COUNT_SQL)).one()
    retired = bind.execute(sa.text(RETIRE_SQL)).rowcount
    marked = bind.execute(sa.text(MARK_SQL)).rowcount
    after = bind.execute(sa.text(COUNT_SQL)).one()

    print(
        f"075: before topics={before.topics} standard={before.topics_standard} "
        f"derived={before.rows_derived} active={before.rows_active}; "
        f"retired={retired} marked={marked}; "
        f"after standard={after.topics_standard} active={after.rows_active}"
    )
    if (retired != before.rows_active or marked != before.topics_standard
            or after.rows_active != 0 or after.topics_standard != 0):
        raise RuntimeError(
            f"075: counts do not reconcile (before={tuple(before)}, retired={retired}, "
            f"marked={marked}, after={tuple(after)}); rolling back"
        )


def downgrade():
    op.execute(REACTIVATE_SQL)
    op.drop_constraint('ck_memory_entries_inactive_reason', 'memory_entries', type_='check')
    op.create_check_constraint('ck_memory_entries_inactive_reason', 'memory_entries', NARROW)
