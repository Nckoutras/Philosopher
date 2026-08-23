"""Tests for conversation_service dedup behavior (Prompt 1.5 fix).

Verifies that POST /conversations reuses an existing empty conversation
rather than creating duplicate rows.

Run: cd apps/api && pytest tests/test_conversations.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.conversation_service import ConversationService


@pytest.fixture
def service():
    return ConversationService()


def _mock_persona_db(slug="marcus_aurelius", persona_id="persona-uuid-1"):
    p = MagicMock()
    p.id = persona_id
    p.slug = slug
    return p


def _mock_conv(conv_id="conv-uuid-existing", message_count=0):
    c = MagicMock()
    c.id = conv_id
    c.message_count = message_count
    return c


def _stmt_table(stmt) -> str:
    """Which table a statement selects from. Never a call index.

    create()'s queries are distinguishable by table alone — rituals, personas,
    conversations, messages — so this needs none of the filter-level
    discrimination the stream_response harness requires.
    """
    try:
        sql = " ".join(str(stmt.compile(compile_kwargs={"literal_binds": True})).split()).upper()
    except Exception:
        return "other"
    for table in ("RITUALS", "PERSONAS", "CONVERSATIONS", "MESSAGES"):
        if f"FROM {table}" in sql:
            return table.lower()
    return "other"


def _make_db(*, persona_db, dedup_conv, ritual=None, existing_opening=None):
    """Mock AsyncSession dispatching by statement SHAPE, not call order.

    This harness previously handed execute() an ORDERED side_effect list of two
    or three results. create() now issues a FOURTH query — the `has_opening`
    lookup at conversation_service.py:396, inserted inside the dedup branch
    after this was written — so the list ran dry and both tests died on
    StopAsyncIteration before reaching an assertion. Neither was a product
    defect; they broke when a query was added.

    Dispatching by table means an inserted query returns a benign empty result
    instead of shifting or exhausting anything. `existing_opening` controls the
    has_opening lookup: None (default) means the conversation has no assistant
    message yet, so create() seeds the opening invocation.
    """
    db = AsyncMock()

    def _result(value):
        r = MagicMock()
        r.scalar_one_or_none.return_value = value
        return r

    results = {
        "rituals": _result(ritual),
        "personas": _result(persona_db),
        "conversations": _result(dedup_conv),
        "messages": _result(existing_opening),
    }

    async def execute(stmt, *args, **kwargs):
        return results.get(_stmt_table(stmt)) or _result(None)

    db.execute = AsyncMock(side_effect=execute)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


# ── a) Dedup returns existing empty conversation ──────────────────────────────

@pytest.mark.asyncio
async def test_create_returns_existing_empty_conversation(service):
    """Calling create() when an empty conversation already exists returns it."""
    persona_db = _mock_persona_db("marcus_aurelius")
    existing = _mock_conv("conv-uuid-existing", message_count=0)
    db = _make_db(persona_db=persona_db, dedup_conv=existing)

    result = await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    assert result.id == "conv-uuid-existing"


# ── b) New conversation created when existing has messages ────────────────────

@pytest.mark.asyncio
async def test_create_returns_new_after_messages_sent(service):
    """When no empty conversation exists (dedup miss), a new row is created."""
    persona_db = _mock_persona_db("marcus_aurelius")
    # Dedup returns None — the existing conv has messages so it wasn't returned
    db = _make_db(persona_db=persona_db, dedup_conv=None)

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    assert db.add.called


# ── c) No second opening invocation on dedup hit ─────────────────────────────

@pytest.mark.asyncio
async def test_create_does_not_duplicate_opening_invocation(service):
    """A dedup'd conv that ALREADY has an opening gets no second one.

    The fixture must say whether the existing conversation already has an
    assistant message. Before #244 it did not have to: create() never looked, so
    a dedup hit could never add anything. #244 ("ensure dedup'd empty conv always
    has opening message") made it look, which is what `existing_opening` now
    models. The invariant this test is named for — never TWO openings — is
    unchanged; only the setup had to become explicit about the precondition.
    """
    persona_db = _mock_persona_db("marcus_aurelius")
    existing = _mock_conv("conv-uuid-existing", message_count=0)
    db = _make_db(
        persona_db=persona_db,
        dedup_conv=existing,
        existing_opening="msg-uuid-opening",  # the conv already has one
    )

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_seeds_opening_when_dedup_hit_has_none(service):
    """The other half of #244: a dedup'd conv MISSING its opening gets one.

    Previously uncovered — the pre-#244 harness could not express this state, so
    the behaviour that PR shipped had no test at all.
    """
    persona_db = _mock_persona_db("marcus_aurelius")
    existing = _mock_conv("conv-uuid-existing", message_count=0)
    db = _make_db(
        persona_db=persona_db,
        dedup_conv=existing,
        existing_opening=None,  # no assistant message yet
    )

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
    )

    added = [c.args[0] for c in db.add.call_args_list]
    assert len(added) == 1, "expected exactly one seeded opening"
    assert added[0].role == "assistant"
    assert added[0].conversation_id == "conv-uuid-existing"


# ── d) ritual_id scopes the dedup — different ritual = new conversation ───────

@pytest.mark.asyncio
async def test_create_dedup_respects_ritual_id(service):
    """A plain conv (ritual_id=None) is not reused for a call with ritual_id set."""
    persona_db = _mock_persona_db("marcus_aurelius")
    # ritual_id validation now runs first — supply a valid free ritual so the call
    # proceeds; the dedup (ritual-scoped) then misses (None) and a new conv is made.
    db = _make_db(persona_db=persona_db, dedup_conv=None, ritual=MagicMock(tier="free"))

    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="marcus_aurelius",
        ritual_id="ritual-uuid-99",
    )

    assert db.add.called


# ── e) Persona scopes the dedup — different persona = new conversation ────────

@pytest.mark.asyncio
async def test_create_dedup_respects_persona_slug(service):
    """A conversation for persona A is never returned as a dedup hit for persona B."""
    persona_db = _mock_persona_db("epictetus", persona_id="persona-uuid-2")
    # No empty conv found for epictetus
    db = _make_db(persona_db=persona_db, dedup_conv=None)

    # user_plan="pro" so the plan-access check passes for epictetus (pro-tier persona)
    await service.create(
        db=db,
        user_id="user-1",
        persona_slug="epictetus",
        user_plan="pro",
    )

    assert db.add.called
