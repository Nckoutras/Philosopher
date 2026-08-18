"""Tests for the shared SafetyEvent writer (A18b).

Until A18b, SafetyEvent had exactly one writer — ConversationService._log_safety_event —
so the table recorded chat and nothing else. Every ritual surface ran safety checks and
acted on them but left no operator record: a user in distress who works only in rituals
was protected and invisible at the same time.

Pattern: AsyncMock for db, real SafetyResult objects. No database, no network.

NOT covered here: that each of the six call sites is wired, and that each logs BEFORE its
suppression branch. Those need a session and a live service per surface — reviewable in
the diff, where every site reads check -> `if …should_log:` -> log -> suppression.

Run: cd apps/api && pytest tests/services/test_safety_event_log.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import AsyncMock, MagicMock

from services.safety_event_log import (
    log_safety_event,
    STAGE_COUNCIL_INPUT,
    STAGE_COUNTERVIEW_INPUT,
    STAGE_COUNTERVIEW_REBUTTAL_INPUT,
    STAGE_SELF_COMPARISON_INPUT,
    STAGE_SCHEDULED_EMAIL_INPUT,
)
from services.safety_service import SafetyResult

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
CONV_ID = "bbbbbbbb-0000-0000-0000-000000000002"


def _db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


def _added(db):
    """The single SafetyEvent handed to db.add."""
    assert db.add.call_count == 1, f"expected one row, got {db.add.call_count}"
    return db.add.call_args[0][0]


# ── The ritual case: the gap A18b exists to close ─────────────────────────────

async def test_a_ritual_event_writes_with_null_conversation_and_message():
    """The whole point. A council matter has no conversation and no message, and both
    columns are nullable precisely so a ritual row needs to invent neither."""
    db = _db()
    res = SafetyResult(level="high", category="self_harm", trigger="phrase", raw_flags=["f"])

    await log_safety_event(db, USER_ID, res, STAGE_COUNCIL_INPUT)

    ev = _added(db)
    assert ev.user_id == USER_ID
    assert ev.conversation_id is None
    assert ev.message_id is None
    assert ev.trigger_stage == "council_input"
    assert ev.risk_level == "high"
    db.flush.assert_awaited_once()


async def test_every_ritual_stage_is_written_verbatim():
    """The vocabulary is the operator's index — a typo or a silent rename makes a whole
    surface unfindable in the record. String(50), no CHECK, so nothing else guards it."""
    for stage, expected in [
        (STAGE_COUNCIL_INPUT, "council_input"),
        (STAGE_COUNTERVIEW_INPUT, "counterview_input"),
        (STAGE_COUNTERVIEW_REBUTTAL_INPUT, "counterview_rebuttal_input"),
        (STAGE_SELF_COMPARISON_INPUT, "self_comparison_input"),
        (STAGE_SCHEDULED_EMAIL_INPUT, "scheduled_email_input"),
    ]:
        db = _db()
        await log_safety_event(db, USER_ID, SafetyResult(level="medium"), stage)
        assert _added(db).trigger_stage == expected
        assert len(expected) <= 50, "trigger_stage is String(50)"


# ── action_taken mirrors the decision, never makes it ─────────────────────────

async def test_action_taken_says_suppressed_when_the_caller_will_suppress():
    """This module RECORDS; it never decides. action_taken must read back exactly what
    the caller's own gate did, so 'suppressed' tracks should_suppress_persona."""
    db = _db()
    await log_safety_event(db, USER_ID, SafetyResult(level="medium"), STAGE_COUNCIL_INPUT)
    assert _added(db).action_taken == "suppressed"


def test_the_threshold_and_the_decision_are_different_lines():
    """A 'low' result is logged but NOT suppressed — which is why callers gate on
    should_log, not on should_suppress_persona. Pins the asymmetry the wiring relies on."""
    low = SafetyResult(level="low")
    assert low.should_log is True
    assert low.should_suppress_persona is False

    none = SafetyResult(level="none")
    assert none.should_log is False


async def test_a_low_result_is_still_recorded_as_logged_not_suppressed():
    db = _db()
    await log_safety_event(db, USER_ID, SafetyResult(level="low"), STAGE_SELF_COMPARISON_INPUT)
    assert _added(db).action_taken == "logged"


# ── Chat must be byte-identical through the delegating wrapper ────────────────

async def test_the_chat_wrapper_delegates_with_identical_semantics():
    """_log_safety_event kept its exact signature so the three chat call sites need no
    edit. A row written through it must be indistinguishable from what chat wrote before
    A18b — same stage, same ids, same flush."""
    from services.conversation_service import conversation_service

    db = _db()
    res = SafetyResult(level="critical", category="crisis", trigger="t", raw_flags=["a", "b"])

    await conversation_service._log_safety_event(
        db, USER_ID, CONV_ID, None, res, "pre_generation"
    )

    ev = _added(db)
    assert ev.user_id == USER_ID
    assert ev.conversation_id == CONV_ID
    assert ev.message_id is None
    assert ev.trigger_stage == "pre_generation"
    assert ev.risk_level == "critical"
    assert ev.category == "crisis"
    assert ev.action_taken == "suppressed"
    assert ev.raw_flags == {"flags": ["a", "b"], "trigger": "t"}
    db.flush.assert_awaited_once()


async def test_the_writer_never_commits():
    """The caller owns the transaction: get_db commits on successful teardown, worker
    tasks commit explicitly. A commit here would end someone else's transaction early."""
    db = _db()
    await log_safety_event(db, USER_ID, SafetyResult(level="high"), STAGE_COUNTERVIEW_INPUT)
    db.commit.assert_not_awaited()
