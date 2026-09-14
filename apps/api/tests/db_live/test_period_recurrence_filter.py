"""The corpus bound, proven against a real schema instead of a string.

WHY THIS FILE HAS TO EXIST. Every other test of the period filter drives a mocked
session, and a mock returns its fixture rows whatever the SQL says — so those
tests assert that the bound is ASKED FOR, never that it is obeyed. #642 found
this the hard way: removing `id` from the SELECT left every mocked test green.

A WHERE clause is only enforced by a database. So the one thing that cannot be
faked is asserted here: an entry written inside the period is not returned as a
prior echo when corpus_until is the period start.

Skips without DATABASE_URL_TEST, like everything in this directory. CI runs it;
locally it is invisible. That is TD-57's recorded decision, not an accident.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from services.memory_service import find_recurrences

# REUSED, NOT RE-WRITTEN. The first version of this file seeded conversations with
# (id, user_id) only and CI rejected all three cases on
# NotNullViolationError: persona_id. `conversations` has exactly two required
# columns without defaults — user_id and persona_id — and a seeder that knows that
# already exists next door, together with the lookup that makes it work:
# personas are inserted by the migration chain (006, 027), so a test points at a
# real row rather than inventing one. Importing beats copying: a second seeder is
# a second thing to be wrong about the schema.
#
# The sys.path line is required and was verified, not assumed: pytest does NOT put
# this directory on the path for us here (the first attempt failed collection with
# ModuleNotFoundError). No conftest import — pytest discovers
# tests/db_live/conftest.py on its own, as every other file in this directory
# relies on.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_memory_recall_and_cascades import (  # noqa: E402
    _make_conversation,
    _make_user,
)

# Two identical unit vectors: cosine similarity 1.0, so the threshold is never
# what decides these tests. The DATE is the only variable.
IDENTICAL = [1.0] + [0.0] * 1535

# DATETIME OBJECTS, NOT ISO STRINGS, and timezone-aware. asyncpg binds a
# timestamptz parameter from a date/datetime only; a string raises DataError at
# BIND time, before the statement ever reaches Postgres — so it fails identically
# whether the column, the value or the query is at fault, and the message names
# the argument position rather than the column. This applies to every parameter
# compared against a timestamptz, which means the corpus bound below as much as
# the inserted rows: passing the window as a string would fail the same way one
# step later.
PERIOD_START = datetime(2026, 9, 7, tzinfo=timezone.utc)
BEFORE_PERIOD = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
INSIDE_PERIOD = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
QUERY_WRITTEN = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)


def _vec(v) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


async def _memory(db, user_id: str, conversation_id: str, content: str,
                  created_at: datetime) -> str:
    """created_at is set EXPLICITLY — the column defaults to now(), and a test
    about a date filter that let the database choose its own dates would be
    testing nothing.

    This one is NOT the neighbouring _make_memory: that helper cannot set
    created_at, and created_at is the only variable these tests vary. The user,
    persona and conversation seeders are imported rather than repeated.
    """
    mid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO memory_entries "
            "  (id, user_id, conversation_id, entry_type, content, embedding, "
            "   confidence, created_at) "
            f"VALUES (:id, :uid, :cid, 'struggle', :content, '{_vec(IDENTICAL)}'::vector, "
            "        0.9, :created_at)"
        ),
        {"id": mid, "uid": user_id, "cid": conversation_id,
         "content": content, "created_at": created_at},
    )
    return mid


class _Entry:
    """The query side. A plain object, not a MagicMock: find_recurrences reads
    three attributes and an omission must raise rather than arrive as a Mock
    (C-06)."""

    def __init__(self, entry_id, conversation_id):
        self.id = entry_id
        self.content = "the row that triggered it"
        self.embedding = IDENTICAL
        self.conversation_id = conversation_id


@pytest.mark.asyncio
async def test_an_in_period_row_is_excluded_from_the_corpus(db):
    """THE ASSERTION A MOCK CANNOT MAKE.

    Three memories, all with identical vectors so similarity never decides:
      - one written BEFORE the period, in another conversation → a real echo
      - one written INSIDE the period, in another conversation → not an echo
      - the query entry itself, in its own conversation → excluded by the
        conversation clause, as it always was

    With corpus_until = period start, only the pre-period row may come back.
    """
    user_id = await _make_user(db)
    own = await _make_conversation(db, user_id)
    other = await _make_conversation(db, user_id)

    before_id = await _memory(db, user_id, other, "raised in August", BEFORE_PERIOD)
    await _memory(db, user_id, other, "raised again this week", INSIDE_PERIOD)
    query_id = await _memory(db, user_id, own, "raised today", QUERY_WRITTEN)
    await db.flush()

    found = await find_recurrences(
        db, user_id, _Entry(query_id, own),
        exclude_conversation=own,
        corpus_until=PERIOD_START,
    )

    assert found is not None, "the August row is a genuine pre-period echo"
    matches, evidence = found
    returned = {str(m.id) for m in matches}
    assert returned == {before_id}, (
        "only the pre-period row may be cited; an in-period row is the same "
        "preoccupation, not a returning one"
    )
    assert evidence["detector"]["window"]["until"].startswith("2026-09-07")


@pytest.mark.asyncio
async def test_with_no_bound_the_same_data_returns_both(db):
    """The other half, and the reason the first test proves something: WITHOUT the
    bound this corpus returns both rows. If it did not, the first test would pass
    for a reason unrelated to the filter."""
    user_id = await _make_user(db)
    own = await _make_conversation(db, user_id)
    other = await _make_conversation(db, user_id)

    before_id = await _memory(db, user_id, other, "raised in August", BEFORE_PERIOD)
    inside_id = await _memory(db, user_id, other, "raised again this week", INSIDE_PERIOD)
    query_id = await _memory(db, user_id, own, "raised today", QUERY_WRITTEN)
    await db.flush()

    found = await find_recurrences(
        db, user_id, _Entry(query_id, own), exclude_conversation=own,
    )

    assert found is not None
    matches, evidence = found
    assert {str(m.id) for m in matches} == {before_id, inside_id}
    assert evidence["detector"]["window"] is None, "the unbounded caller is lifetime"


@pytest.mark.asyncio
async def test_a_period_with_no_prior_echo_finds_nothing(db):
    """A person's first week. Everything they have written is inside the window,
    so there is nothing for it to echo — and that must read as "no recurrence",
    not as an error."""
    user_id = await _make_user(db)
    own = await _make_conversation(db, user_id)
    other = await _make_conversation(db, user_id)

    await _memory(db, user_id, other, "raised this week", INSIDE_PERIOD)
    query_id = await _memory(db, user_id, own, "raised today", QUERY_WRITTEN)
    await db.flush()

    found = await find_recurrences(
        db, user_id, _Entry(query_id, own),
        exclude_conversation=own,
        corpus_until=PERIOD_START,
    )

    assert found is None
