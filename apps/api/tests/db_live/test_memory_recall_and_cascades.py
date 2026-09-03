"""The three memory behaviours a mock cannot assert (first cut, Ruling #10).

Each of these was on the investigation's "untestable without a database" list
(MEMORY_V2_INVESTIGATION_2026-09-03 §3). What they have in common is that the
behaviour IS the query result — a mocked session returns whatever the test author
configured, so a mock can only assert that a statement was issued, never that it
returned the right rows.

  1. recall's 0.70 cut and distance ordering — pgvector arithmetic.
  2. Deleting a conversation DESTROYS its memories — an ON DELETE clause.
  3. Deleting a user reaches memory_entries — the account-deletion cascade.

Tests 2, 5, 6 and 7 from that list (recurrence exclusion, the insight gate,
self_portrait source_turn dedup, seed-task atomicity) are a deliberate follow-up
once this lands green.

NO EMBEDDING API CALLS. Vectors are constructed arithmetically and inserted as
literals, and recall is handed its query vector directly via query_embedding.
Nothing here reaches OpenAI.
"""
import uuid

import pytest
from sqlalchemy import text

from services.memory_service import memory_service

DIM = 1536  # Vector(1536) on memory_entries — text-embedding-3-small


# ── Deterministic unit vectors ───────────────────────────────────────────────
#
# pgvector's `<=>` is COSINE DISTANCE, and recall computes `1 - (embedding <=> q)`
# — i.e. cosine similarity — then keeps `score > 0.70`. Building every vector in
# the plane spanned by e0 and e1 makes each similarity exact and known in advance:
# a unit vector at angle θ from e0 has similarity cos θ with e0, so the expected
# score IS the e0 coefficient. That turns the threshold into arithmetic rather
# than a guess, and lets the boundary be tested from both sides.

def _unit(a: float, b: float) -> list[float]:
    """The unit vector a*e0 + b*e1. Caller supplies a**2 + b**2 == 1."""
    v = [0.0] * DIM
    v[0] = a
    v[1] = b
    return v


QUERY = _unit(1.0, 0.0)          # e0
IDENTICAL = _unit(1.0, 0.0)      # similarity 1.00  → kept, ranked first
NEAR = _unit(0.8, 0.6)           # similarity 0.80  → kept, ranked second
BELOW_CUT = _unit(0.6, 0.8)      # similarity 0.60  → dropped by the 0.70 cut
ORTHOGONAL = _unit(0.0, 1.0)     # similarity 0.00  → dropped


def _vec(v: list[float]) -> str:
    """pgvector literal. Full precision — a rounded literal would move the
    similarity off the exact value the assertions depend on."""
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _a_persona_id(db) -> str:
    """Personas are inserted by the migration chain itself (006, 027), so there is
    a real row to point at without this test inventing one."""
    row = (await db.execute(text("SELECT id FROM personas LIMIT 1"))).first()
    assert row is not None, "the migration chain should have seeded personas"
    return str(row[0])


async def _make_conversation(db, user_id: str) -> str:
    cid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO conversations (id, user_id, persona_id) "
            "VALUES (:id, :uid, :pid)"
        ),
        {"id": cid, "uid": user_id, "pid": await _a_persona_id(db)},
    )
    return cid


async def _make_memory(db, user_id: str, content: str, vector: list[float],
                       conversation_id: str | None = None) -> str:
    mid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO memory_entries "
            "  (id, user_id, conversation_id, entry_type, content, embedding, confidence) "
            f"VALUES (:id, :uid, :cid, 'struggle', :content, '{_vec(vector)}'::vector, 0.9)"
        ),
        {"id": mid, "uid": user_id, "cid": conversation_id, "content": content},
    )
    return mid


async def _memory_exists(db, memory_id: str) -> bool:
    row = (await db.execute(
        text("SELECT 1 FROM memory_entries WHERE id = :id"), {"id": memory_id},
    )).first()
    return row is not None


# ── 1. recall: the 0.70 cut and distance ordering ───────────────────────────

@pytest.mark.asyncio
async def test_recall_keeps_only_matches_above_the_threshold_in_distance_order(db):
    """THE ASSERTION NO MOCK CAN MAKE. Four rows at similarities 1.00 / 0.80 /
    0.60 / 0.00 to the query; recall must return exactly the first two, in that
    order, because it orders by `embedding <=> query` and cuts at score > 0.70."""
    user_id = await _make_user(db)
    await _make_memory(db, user_id, "identical", IDENTICAL)
    await _make_memory(db, user_id, "near", NEAR)
    await _make_memory(db, user_id, "below the cut", BELOW_CUT)
    await _make_memory(db, user_id, "orthogonal", ORTHOGONAL)
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused — the vector is supplied", query_embedding=QUERY,
    )

    assert [r.content for r in rows] == ["identical", "near"]
    assert rows[0].score == pytest.approx(1.0, abs=1e-5)
    assert rows[1].score == pytest.approx(0.8, abs=1e-5)


@pytest.mark.asyncio
async def test_the_threshold_is_pinned_from_both_sides(db):
    """0.69 out, 0.71 in — the cut is where the code says it is.

    DELIBERATELY NOT TESTED AT EXACTLY 0.70. pgvector's `vector` is float4, so
    0.7 is not representable: it stores as 0.6999999880..., and whether the
    resulting similarity lands above or below the `> 0.70` comparison is a
    property of single-precision rounding rather than of the product. A test on
    that knife-edge would be a coin flip dressed as an assertion. A +/-0.01
    margin pins the threshold just as tightly and cannot flake."""
    user_id = await _make_user(db)
    below = _unit(0.69, (1 - 0.69 ** 2) ** 0.5)
    above = _unit(0.71, (1 - 0.71 ** 2) ** 0.5)
    await _make_memory(db, user_id, "below the cut", below)
    await _make_memory(db, user_id, "above the cut", above)
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused", query_embedding=QUERY,
    )

    assert [r.content for r in rows] == ["above the cut"]


@pytest.mark.asyncio
async def test_recall_never_crosses_users(db):
    """The WHERE clause is the only thing separating two people's memories."""
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _make_memory(db, mine, "mine", IDENTICAL)
    await _make_memory(db, theirs, "theirs", IDENTICAL)
    await db.flush()

    rows = await memory_service.recall(db, mine, query="unused", query_embedding=QUERY)

    assert [r.content for r in rows] == ["mine"]


@pytest.mark.asyncio
async def test_recall_skips_inactive_rows_and_rows_without_an_embedding(db):
    """Both guards are in the SQL, and both are invisible to a mock."""
    user_id = await _make_user(db)
    kept = await _make_memory(db, user_id, "kept", IDENTICAL)
    inactive = await _make_memory(db, user_id, "deactivated", IDENTICAL)
    await db.execute(
        text("UPDATE memory_entries SET is_active = FALSE WHERE id = :id"),
        {"id": inactive},
    )
    await db.execute(
        text(
            "INSERT INTO memory_entries (id, user_id, entry_type, content, confidence) "
            "VALUES (:id, :uid, 'struggle', 'no embedding', 0.9)"
        ),
        {"id": str(uuid.uuid4()), "uid": user_id},
    )
    await db.flush()

    rows = await memory_service.recall(db, user_id, query="unused", query_embedding=QUERY)

    assert [r.content for r in rows] == ["kept"]
    assert await _memory_exists(db, kept)


@pytest.mark.asyncio
async def test_recall_respects_top_k(db):
    """top_k is a LIMIT, applied before the Python-side threshold filter."""
    user_id = await _make_user(db)
    for i in range(5):
        await _make_memory(db, user_id, f"m{i}", IDENTICAL)
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused", query_embedding=QUERY, top_k=2,
    )

    assert len(rows) == 2


# ── 3. Conversation delete CASCADEs into memory_entries ─────────────────────

@pytest.mark.asyncio
async def test_deleting_a_conversation_destroys_the_memories_extracted_from_it(db):
    """PINS TODAY'S BEHAVIOUR, WHICH IS A KNOWN PROBLEM, NOT A GOOD ONE.

    memory_entries.conversation_id is ON DELETE CASCADE (migration 013, reasoned
    then as "derived data, safe to lose with parent"), and DELETE /conversations
    is a hard delete. So tidying an old thread silently destroys what the room
    learned in it — while the product copy promises the opposite
    (MEMORY_V2_INVESTIGATION §2d).

    THE v2 MIGRATION WILL FLIP THIS TEST, DELIBERATELY. When conversation_id
    becomes SET NULL, this assertion inverts to "the row survives with a NULL
    conversation_id". That is the point of pinning it now: the change becomes a
    visible, intentional edit to this file rather than a silent behaviour swap.
    """
    user_id = await _make_user(db)
    conversation_id = await _make_conversation(db, user_id)
    from_conversation = await _make_memory(
        db, user_id, "learned in the thread", IDENTICAL, conversation_id=conversation_id,
    )
    standalone = await _make_memory(db, user_id, "not tied to a thread", NEAR)
    await db.flush()

    await db.execute(
        text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id},
    )
    await db.flush()

    assert await _memory_exists(db, from_conversation) is False  # ← flips under v2
    # Rows with a NULL conversation_id were never at risk, and must not be.
    assert await _memory_exists(db, standalone) is True


# ── 4. User hard-delete reaches memory_entries ──────────────────────────────

@pytest.mark.asyncio
async def test_deleting_a_user_cascades_all_the_way_to_their_memories(db):
    """Account deletion is a single `DELETE FROM users` (#588), and ONLY the
    schema makes that reach memory_entries. The mocked deletion test can prove
    the statement was issued; only this can prove the rows disappear."""
    user_id = await _make_user(db)
    conversation_id = await _make_conversation(db, user_id)
    with_conversation = await _make_memory(
        db, user_id, "tied to a thread", IDENTICAL, conversation_id=conversation_id,
    )
    without_conversation = await _make_memory(db, user_id, "standalone", NEAR)
    await db.flush()

    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await db.flush()

    assert await _memory_exists(db, with_conversation) is False
    assert await _memory_exists(db, without_conversation) is False
    survivors = (await db.execute(
        text("SELECT count(*) FROM memory_entries WHERE user_id = :id"), {"id": user_id},
    )).scalar_one()
    assert survivors == 0


@pytest.mark.asyncio
async def test_deleting_one_user_leaves_another_users_memories_alone(db):
    """The cascade must be bounded by the FK, not by anything wider."""
    doomed = await _make_user(db)
    bystander = await _make_user(db)
    await _make_memory(db, doomed, "goes", IDENTICAL)
    survivor = await _make_memory(db, bystander, "stays", IDENTICAL)
    await db.flush()

    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": doomed})
    await db.flush()

    assert await _memory_exists(db, survivor) is True
