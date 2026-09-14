"""The period-filtered recurrence caller, and the proof it narrowed nothing.

WHAT THIS IS FOR. The trajectory snapshot asks a different question than the
insight card does: "which entries written in week W echo entries written BEFORE
W". Same cosine mechanics, different bounds — so the mechanics were extracted
into find_recurrences and the lifetime detector became one of its two callers.

THE ASSERTION THAT MATTERS MOST is test_the_lifetime_sql_is_byte_identical. The
ruling on this work is that the lifetime detector is NOT narrowed: "you raised
this in March and again today" is the product, and a window would destroy exactly
that. A frozen literal of the SQL as it stood before the extraction is the only
thing that can prove the refactor changed no behaviour, because every other test
here drives a mocked session that returns fixture rows whatever the query says.

WHICH IS ALSO THE LIMIT OF THIS FILE. A mock cannot enforce a WHERE clause. Every
assertion below about the period filter is an assertion about a STRING; that the
filter actually excludes rows is proven against a live schema in
tests/db_live/test_period_recurrence_filter.py, CI-only per TD-57.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services import memory_service as ms
from services.memory_service import RECURRENCE_LIMIT, find_recurrences

USER_ID = "11111111-1111-1111-1111-111111111111"
CONV_ID = "22222222-2222-2222-2222-222222222222"

PERIOD_START = datetime(2026, 9, 7, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 9, 13, 18, 0, 1, tzinfo=timezone.utc)

# The SQL as it stood at #642, before the mechanics were extracted. FROZEN —
# copied from the pre-extraction source, not generated from the current code,
# because a literal regenerated from what it is meant to police proves nothing.
LIFETIME_SQL = """
                        SELECT id, content, conversation_id,
                               1 - (embedding <=> CAST(:query_vec AS vector)) AS score
                        FROM memory_entries
                        WHERE user_id = :user_id
                          AND is_active = TRUE
                          AND embedding IS NOT NULL
                          AND conversation_id != :conversation_id
                        ORDER BY embedding <=> CAST(:query_vec AS vector)
                        LIMIT 20
                    """


def _entry(eid="e1", conv=CONV_ID):
    return SimpleNamespace(
        id=eid, content="the row that triggered it", embedding=[0.1] * 8,
        conversation_id=conv,
    )


def _match(mid, conv, score=0.91, text="an earlier row"):
    return SimpleNamespace(id=mid, content=text, conversation_id=conv, score=score)


def _db(matches):
    db = AsyncMock()
    rows = MagicMock()
    rows.fetchall.return_value = matches
    db.execute = AsyncMock(return_value=rows)
    return db


def _emitted(db):
    """(sql, params) as the function actually handed them to the session."""
    clause, params = db.execute.await_args.args
    return str(clause), params


# ── THE NO-NARROWING PROOF ────────────────────────────────────────────────────

async def test_the_lifetime_sql_is_byte_identical_to_before_the_extraction():
    """THE ONE THAT MATTERS. With no corpus bounds the emitted SQL must equal, to
    the byte, what this query was before find_recurrences existed.

    The clauses are appended to the exclusion filter rather than occupying a slot
    of their own, precisely so that an absent bound leaves no trace — an empty
    slot would leave an indented blank line, which is a different string and would
    fail here.
    """
    db = _db([_match("m1", "conv-a")])
    await find_recurrences(db, USER_ID, _entry(), exclude_conversation=CONV_ID)

    sql, _ = _emitted(db)
    assert sql == LIFETIME_SQL


async def test_the_lifetime_path_binds_no_period_parameters():
    db = _db([_match("m1", "conv-a")])
    await find_recurrences(db, USER_ID, _entry(), exclude_conversation=CONV_ID)

    _, params = _emitted(db)
    assert "corpus_since" not in params
    assert "corpus_until" not in params
    assert set(params) == {"query_vec", "user_id", "conversation_id"}


async def test_the_lifetime_evidence_window_is_still_null():
    """The second half of the no-narrowing proof, and what #642 already asserts
    from the other direction."""
    db = _db([_match("m1", "conv-a")])
    _, evidence = await find_recurrences(db, USER_ID, _entry(), exclude_conversation=CONV_ID)

    assert evidence["detector"]["window"] is None


# ── The bounded caller ────────────────────────────────────────────────────────

async def test_corpus_until_reaches_the_sql_and_binds_its_parameter():
    db = _db([_match("m1", "conv-a")])
    await find_recurrences(
        db, USER_ID, _entry(), exclude_conversation=CONV_ID,
        corpus_until=PERIOD_START,
    )

    sql, params = _emitted(db)
    assert "AND created_at < :corpus_until" in sql
    assert params["corpus_until"] == PERIOD_START


async def test_corpus_since_is_available_and_unused_by_todays_callers():
    """Reserved for a bounded look-back ("only the last six months"). Asserted so
    the parameter is known to work before something depends on it."""
    db = _db([_match("m1", "conv-a")])
    await find_recurrences(
        db, USER_ID, _entry(), exclude_conversation=CONV_ID,
        corpus_since=PERIOD_START, corpus_until=PERIOD_END,
    )

    sql, params = _emitted(db)
    assert "AND created_at >= :corpus_since" in sql
    assert "AND created_at < :corpus_until" in sql
    assert params["corpus_since"] == PERIOD_START
    assert params["corpus_until"] == PERIOD_END


async def test_the_bounded_evidence_records_the_window_it_used():
    db = _db([_match("m1", "conv-a")])
    _, evidence = await find_recurrences(
        db, USER_ID, _entry(), exclude_conversation=CONV_ID,
        corpus_until=PERIOD_START,
    )

    assert evidence["detector"]["window"] == {
        "since": None,
        "until": "2026-09-07T00:00:00Z",
    }


# ── The echo must predate the window ─────────────────────────────────────────

async def test_an_echo_inside_the_period_is_not_a_recurrence():
    """The whole meaning of the bound. A snapshot for week W asks which entries
    written in W echo entries written BEFORE W — two entries from the same week
    are one preoccupation, not a returning one.

    The filter itself is SQL and a mock cannot enforce it, so what is asserted
    here is that the bound is asked for. That it is obeyed is a db_live test.
    """
    db = _db([])  # the live query would have excluded the in-period row
    result = await find_recurrences(
        db, USER_ID, _entry(), exclude_conversation=CONV_ID,
        corpus_until=PERIOD_START,
    )

    assert result is None, "no pre-period echo means no recurrence"
    sql, params = _emitted(db)
    assert "AND created_at < :corpus_until" in sql
    assert params["corpus_until"] == PERIOD_START


# ── The seam has no side effects ─────────────────────────────────────────────

def test_the_extracted_function_writes_nothing_and_calls_no_model():
    """THE VALUE OF THE SEAM. The snapshot needs match sets, not cards. If this
    function ever grows a classifier call, an Insight write or a throttle read,
    the two callers stop being separable and PR C inherits an insight-writer it
    never asked for."""
    src = inspect.getsource(ms.find_recurrences)

    assert "llm_client" not in src, "find_recurrences must make no model call"
    assert "Insight(" not in src, "find_recurrences must write no insight"
    assert "_insight_gate_blocked" not in src, "the throttle belongs to the caller"
    assert "db.commit" not in src, "find_recurrences must not commit"


def test_the_lifetime_caller_still_owns_its_loop_and_stops_at_the_first_hit():
    """detect_recurrence writes ONE card, so it breaks. The snapshot wants every
    hit. A loop inside the extracted function would force one caller to discard
    work the other needs — which is why query_entry is singular."""
    src = inspect.getsource(ms.MemoryService.detect_recurrence)

    assert "for entry in new_entries:" in src
    assert "break" in src
    assert "await find_recurrences(" in src


def test_the_limit_is_named_rather_than_a_literal():
    """RECURRENCE_LIMIT is recorded in every evidence dict, so it has to be one
    value rather than a number typed in two places."""
    src = inspect.getsource(ms.find_recurrences)

    assert "LIMIT {RECURRENCE_LIMIT}" in src
    assert RECURRENCE_LIMIT == 20


# ── The recorded limits ──────────────────────────────────────────────────────

def test_the_supersession_limit_is_recorded_not_silently_inherited():
    """is_active = TRUE bounds BOTH callers, so this corpus cannot see a belief
    being replaced. That is the deferred version-chain question, and the docstring
    has to say so — a divergence between two callers of the same mechanics is the
    class of thing that becomes a stale claim."""
    doc = inspect.getdoc(ms.find_recurrences) or ""

    assert "CANNOT SEE SUPERSESSION" in doc
    assert "include_superseded" in doc


def test_the_filtered_ann_risk_is_recorded_with_both_levers():
    """Accepted, not tuned. The failure is quiet under-recall on a heavy week, so
    the mechanism and the two levers have to be written down where the next reader
    meets them rather than in a backlog entry alone."""
    doc = inspect.getdoc(ms.find_recurrences) or ""

    assert "ef_search" in doc
    assert "UNDER-RECALL" in doc
    assert "TD-75" in doc
