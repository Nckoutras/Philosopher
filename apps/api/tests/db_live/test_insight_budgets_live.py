"""MEM2-B1 against Postgres: a signal card no longer closes the recurrence window.

The unit tests pin the SQL the gate issues; this pins what Postgres answers. The
September-shaped case is the first test: a belief card written a minute ago, then
the recurrence check asks — before B1 it got "throttle", now it gets None.

Rows are inserted with the ORM so the CHECK on insight_type (if any arrives later)
and the defaults are the real ones. Everything rolls back with the `db` fixture.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_memory_recall_and_cascades import _make_conversation, _make_user  # noqa: E402

from models import Insight  # noqa: E402
from services.memory_service import memory_service  # noqa: E402

pytestmark = pytest.mark.asyncio


async def _insight(db, user_id, conversation_id, insight_type, *, age_minutes=1, dismissed=False):
    row = Insight(
        id=str(uuid.uuid4()),
        user_id=user_id,
        conversation_id=conversation_id,
        content=f"a {insight_type} card",
        insight_type=insight_type,
        is_dismissed=dismissed,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=age_minutes),
    )
    db.add(row)
    await db.flush()
    return row


async def test_a_fresh_signal_card_does_not_block_a_recurrence_card(db):
    uid = await _make_user(db)
    conv_a = await _make_conversation(db, uid)
    conv_b = await _make_conversation(db, uid)
    await _insight(db, uid, conv_a, "belief")

    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="recurrence") is None
    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="signal") == "throttle"


async def test_a_fresh_recurrence_card_does_not_block_a_signal_card(db):
    uid = await _make_user(db)
    conv_a = await _make_conversation(db, uid)
    conv_b = await _make_conversation(db, uid)
    await _insight(db, uid, conv_a, "pattern")

    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="signal") is None
    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="recurrence") == "throttle"


async def test_one_per_conversation_is_per_class(db):
    uid = await _make_user(db)
    conv = await _make_conversation(db, uid)
    # Old enough to be outside the 6h window, so only the conversation rule speaks.
    await _insight(db, uid, conv, "dilemma", age_minutes=10 * 60)

    assert await memory_service._insight_gate_blocked(db, uid, conv, kind="signal") == "per_conversation"
    assert await memory_service._insight_gate_blocked(db, uid, conv, kind="recurrence") is None


async def test_a_dismissed_card_still_widens_its_own_window_only(db):
    uid = await _make_user(db)
    conv_a = await _make_conversation(db, uid)
    conv_b = await _make_conversation(db, uid)
    await _insight(db, uid, conv_a, "belief", dismissed=True)
    await _insight(db, uid, conv_a, "pattern")

    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="signal") is None
    assert await memory_service._insight_gate_blocked(db, uid, conv_b, kind="recurrence") == "throttle"


async def test_legacy_types_spend_neither_budget(db):
    uid = await _make_user(db)
    conv = await _make_conversation(db, uid)
    await _insight(db, uid, conv, "question")

    assert await memory_service._insight_gate_blocked(db, uid, conv, kind="signal") is None
    assert await memory_service._insight_gate_blocked(db, uid, conv, kind="recurrence") is None
    # And the row is really there, so the two Nones above are the filter's doing.
    n = (await db.execute(text("SELECT count(*) FROM insights WHERE user_id = :u"), {"u": uid})).scalar_one()
    assert n == 1
