"""The three memory behaviours a mock cannot assert (first cut, Ruling #10).

Each of these was on the investigation's "untestable without a database" list
(MEMORY_V2_INVESTIGATION_2026-09-03 §3). What they have in common is that the
behaviour IS the query result — a mocked session returns whatever the test author
configured, so a mock can only assert that a statement was issued, never that it
returned the right rows.

  1. recall's Lane B floor, its per-type quota and its distance ordering —
     pgvector arithmetic plus a ROW_NUMBER window. (Was "the 0.70 cut" before
     PR-2 made recall hybrid: Ruling #5, INFERRED_SCORE_FLOOR = 0.75.)
  1b. The plan SHAPE of that query — one scan, one window, no timing (T-9).
  2. Deleting a conversation KEEPS its memories and its insights, orphaning both
     — an ON DELETE clause (SET NULL since migration 057; this said DESTROYS
     before it, and the flip is Memory-v2 Ruling #7c).
  3. Deleting a user reaches memory_entries AND insights — the account-deletion
     cascade, which 057 deliberately did not touch.
  4. An orphaned memory drops out of detect_recurrence's candidate set, because
     `conversation_id != :cid` is NULL for it — three-valued logic, which is
     precisely what a mocked session cannot enforce (T-5).

Recurrence exclusion was on that list and is now covered, in the one respect
057 makes live: an orphaned row's NULL conversation_id drops it from the
candidate set (T-5). The insight gate, self_portrait source_turn dedup and
seed-task atomicity remain a deliberate follow-up.

NO EMBEDDING API CALLS. Vectors are constructed arithmetically and inserted as
literals, and recall is handed its query vector directly via query_embedding.
Nothing here reaches OpenAI.
"""
import uuid

import pytest
from sqlalchemy import text

from services.memory_service import (
    INFERRED_PER_TYPE,
    INFERRED_SCORE_FLOOR,
    RECALL_SQL,
    RECALL_TOTAL_BUDGET,
    STANDING_CAP,
    STANDING_PER_TYPE,
    STANDING_TYPES,
    memory_service,
)

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
                       conversation_id: str | None = None,
                       entry_type: str = "struggle") -> str:
    """entry_type is a parameter since PR-2: recall is lane-aware, so a test that
    wants the FLOOR to be the binding constraint has to spread its rows across
    types — otherwise the per-type quota caps them first and the test passes for
    a reason it never meant to check. 'struggle' stays the default (Lane B), so
    every cascade test above reads exactly as it did."""
    mid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO memory_entries "
            "  (id, user_id, conversation_id, entry_type, content, embedding, confidence) "
            f"VALUES (:id, :uid, :cid, :etype, :content, '{_vec(vector)}'::vector, 0.9)"
        ),
        {"id": mid, "uid": user_id, "cid": conversation_id,
         "content": content, "etype": entry_type},
    )
    return mid


async def _memory_exists(db, memory_id: str) -> bool:
    row = (await db.execute(
        text("SELECT 1 FROM memory_entries WHERE id = :id"), {"id": memory_id},
    )).first()
    return row is not None


async def _memory_conversation_id(db, memory_id: str):
    """The FK itself, so a test can tell "survived, orphaned" from "survived,
    still attached" — under CASCADE the row is gone and under SET NULL it is
    here with a NULL, and only reading the column distinguishes them."""
    return (await db.execute(
        text("SELECT conversation_id FROM memory_entries WHERE id = :id"),
        {"id": memory_id},
    )).scalar_one()


async def _make_insight(db, user_id: str, content: str,
                        conversation_id: str | None = None,
                        insight_type: str = "pattern") -> str:
    """The insights half of the cascade. Nothing in apps/api/tests touched this
    table before 057 — the design's §4c enumeration found zero tests referencing
    the Insight model in either direction, which is why the cascade could change
    under it unnoticed."""
    iid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO insights (id, user_id, conversation_id, content, insight_type) "
            "VALUES (:id, :uid, :cid, :content, :itype)"
        ),
        {"id": iid, "uid": user_id, "cid": conversation_id,
         "content": content, "itype": insight_type},
    )
    return iid


async def _insight_exists(db, insight_id: str) -> bool:
    row = (await db.execute(
        text("SELECT 1 FROM insights WHERE id = :id"), {"id": insight_id},
    )).first()
    return row is not None


async def _insight_conversation_id(db, insight_id: str):
    return (await db.execute(
        text("SELECT conversation_id FROM insights WHERE id = :id"),
        {"id": insight_id},
    )).scalar_one()


# ── 1. recall: the Lane B floor and distance ordering ───────────────────────

@pytest.mark.asyncio
async def test_recall_keeps_only_matches_above_the_threshold_in_distance_order(db):
    """THE ASSERTION NO MOCK CAN MAKE. Four rows at similarities 1.00 / 0.80 /
    0.60 / 0.00 to the query; recall must return exactly the first two, in that
    order, because it orders by `embedding <=> query` and cuts at
    INFERRED_SCORE_FLOOR.

    Rewritten for PR-2 in two ways. The cut moved from a 0.70 literal to the named
    Lane B floor (0.75, Ruling #5 / O-1) — 0.80 still clears it and 0.60 still does
    not, so the expected output is unchanged. And the four rows now carry FOUR
    DISTINCT inferred types: left all on 'struggle' they would hit the per-type
    quota of 2 first, and this test would pass while measuring the quota instead of
    the floor it is named for."""
    user_id = await _make_user(db)
    await _make_memory(db, user_id, "identical", IDENTICAL, entry_type="belief")
    await _make_memory(db, user_id, "near", NEAR, entry_type="value")
    await _make_memory(db, user_id, "below the cut", BELOW_CUT, entry_type="struggle")
    await _make_memory(db, user_id, "orthogonal", ORTHOGONAL, entry_type="pattern")
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused — the vector is supplied", query_embedding=QUERY,
    )

    assert [r.content for r in rows] == ["identical", "near"]
    assert rows[0].score == pytest.approx(1.0, abs=1e-5)
    assert rows[1].score == pytest.approx(0.8, abs=1e-5)


@pytest.mark.asyncio
async def test_the_threshold_is_pinned_from_both_sides(db):
    """T-1. 0.74 out, 0.76 in — the Lane B floor is where the constant says it is.

    DELIBERATELY NOT TESTED AT EXACTLY THE FLOOR. pgvector's `vector` is float4,
    so a component written as 0.75 is stored at single precision and the resulting
    similarity lands a hair either side of the `> :floor` comparison by rounding
    rather than by product behaviour. (0.75 is exactly representable in binary
    where 0.70 was not, but the OTHER component of these unit vectors is an
    irrational square root, so the dot product is not exact regardless — the
    hazard is unchanged.) A test on that knife-edge would be a coin flip dressed
    as an assertion. A +/-0.01 margin pins the threshold just as tightly and
    cannot flake.

    Two distinct types, so the per-type quota cannot be what excludes the loser."""
    user_id = await _make_user(db)
    below = _unit(0.74, (1 - 0.74 ** 2) ** 0.5)
    above = _unit(0.76, (1 - 0.76 ** 2) ** 0.5)
    await _make_memory(db, user_id, "below the cut", below, entry_type="belief")
    await _make_memory(db, user_id, "above the cut", above, entry_type="value")
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused", query_embedding=QUERY,
    )

    assert [r.content for r in rows] == ["above the cut"]


@pytest.mark.asyncio
async def test_a_standing_row_below_the_floor_is_still_recalled(db):
    """T-3. Lane A has NO floor, and only a live query proves the SQL agrees with
    compose_recall about that: the standing branch of the WHERE has no `score >`
    clause at all.

    The `stated` row here is at similarity 0.20 — far below anything Lane B could
    survive — and the identically-scored `belief` row beside it is dropped. That
    pairing is the test: same score, opposite outcome, decided only by lane."""
    user_id = await _make_user(db)
    faint = _unit(0.20, (1 - 0.20 ** 2) ** 0.5)
    await _make_memory(db, user_id, "their own words", faint, entry_type="stated")
    await _make_memory(db, user_id, "an inference", faint, entry_type="belief")
    await db.flush()

    rows = await memory_service.recall(db, user_id, query="unused", query_embedding=QUERY)

    assert [r.content for r in rows] == ["their own words"]


@pytest.mark.asyncio
async def test_one_prolific_type_cannot_crowd_out_the_others(db):
    """T-2. A lopsided corpus: six 'pattern' rows, every one of them a closer match
    than the single 'milestone'. Under the old flat top-k the block would have been
    six patterns and nothing else — the failure mode Ruling #5's per-type quota
    exists for.

    This needs the database because the quota is a ROW_NUMBER() window: a mock
    returns whatever the author invented, so 'the query ranked within type' is
    exactly what it cannot assert."""
    user_id = await _make_user(db)
    for i in range(6):
        a = 0.99 - i * 0.01
        await _make_memory(db, user_id, f"pattern {i}", _unit(a, (1 - a ** 2) ** 0.5),
                           entry_type="pattern")
    await _make_memory(db, user_id, "the milestone", _unit(0.80, (1 - 0.80 ** 2) ** 0.5),
                       entry_type="milestone")
    await db.flush()

    rows = await memory_service.recall(db, user_id, query="unused", query_embedding=QUERY)
    types = [r.entry_type for r in rows]

    assert types.count("pattern") == INFERRED_PER_TYPE
    assert "the milestone" in [r.content for r in rows]


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
    """top_k is the TOTAL budget across both lanes since PR-2 — no longer a SQL
    LIMIT, since the caps and quotas decide the block and the query only fetches
    candidates. Five distinct types, so the per-type quota is not what holds the
    result to two."""
    user_id = await _make_user(db)
    for i, etype in enumerate(("belief", "value", "struggle", "pattern", "milestone")):
        a = 0.99 - i * 0.01
        await _make_memory(db, user_id, f"m{i}", _unit(a, (1 - a ** 2) ** 0.5),
                           entry_type=etype)
    await db.flush()

    rows = await memory_service.recall(
        db, user_id, query="unused", query_embedding=QUERY, top_k=2,
    )

    assert len(rows) == 2


@pytest.mark.asyncio
async def test_the_default_budget_fills_both_lanes(db):
    """The default is RECALL_TOTAL_BUDGET (8), not the 6 the four callers used to
    pass. Two standing types and six inferred types, all well above the floor: the
    block should be 3 standing + 5 inferred, standing first.

    This is the assertion that would have caught shipping the design's lanes with
    the old budget still in force at the call sites."""
    user_id = await _make_user(db)
    for i, etype in enumerate(("stated", "stated", "self_portrait", "self_portrait")):
        a = 0.99 - i * 0.001
        await _make_memory(db, user_id, f"standing {i}", _unit(a, (1 - a ** 2) ** 0.5),
                           entry_type=etype)
    for i, etype in enumerate(("belief", "value", "struggle", "pattern",
                               "milestone", "counterview_belief")):
        a = 0.95 - i * 0.01
        await _make_memory(db, user_id, f"inferred {i}", _unit(a, (1 - a ** 2) ** 0.5),
                           entry_type=etype)
    await db.flush()

    rows = await memory_service.recall(db, user_id, query="unused", query_embedding=QUERY)
    types = [r.entry_type for r in rows]

    assert len(rows) == RECALL_TOTAL_BUDGET
    assert sum(t in STANDING_TYPES for t in types) == STANDING_CAP
    # Standing leads, and it is contiguous — not interleaved by score.
    assert all(t in STANDING_TYPES for t in types[:STANDING_CAP])
    assert not any(t in STANDING_TYPES for t in types[STANDING_CAP:])


# ── 1c. standing_memories: the query-free lane (PR-3) ───────────────────────

@pytest.mark.asyncio
async def test_standing_memories_returns_only_stated_rows_newest_first(db):
    """F-13, PROVEN WHERE IT LIVES. The letters' <what_you_know> block can never
    carry a self_portrait row, and the reason is a WHERE clause — which is exactly
    what a mocked session cannot assert, because it returns whatever the test
    author invented.

    It matters because the letters ALREADY render those quiz answers, as
    <self_portrait> built from profile.answers. A `stated`-only filter is the one
    thing keeping one set of answers from appearing twice in a single prompt.

    Ordering is recency, not relevance: a letter covers a whole week or month and
    has no single text to embed, so there is no query to be relevant to.

    Note every row here carries the SAME vector — it is never read on this path.
    No embedding is computed and no distance is taken."""
    user_id = await _make_user(db)
    await _make_memory(db, user_id, "portrait answer", IDENTICAL, entry_type="self_portrait")
    await _make_memory(db, user_id, "a shift", IDENTICAL, entry_type="self_portrait_shift")
    await _make_memory(db, user_id, "an inference", IDENTICAL, entry_type="belief")
    await _make_memory(db, user_id, "older words", IDENTICAL, entry_type="stated")
    await _make_memory(db, user_id, "newer words", IDENTICAL, entry_type="stated")
    await db.flush()

    # created_at is a server default, so both `stated` rows share a timestamp on a
    # fast insert. Age one explicitly rather than trusting insert order to be the
    # ordering — the assertion is about ORDER BY, so the input has to make the
    # order real.
    await db.execute(
        text("UPDATE memory_entries SET created_at = now() - interval '1 day' "
             "WHERE user_id = :uid AND content = 'older words'"),
        {"uid": user_id},
    )
    await db.flush()

    rows = await memory_service.standing_memories(db, user_id, limit=4)

    assert [r.content for r in rows] == ["newer words", "older words"]
    assert all(r.entry_type == "stated" for r in rows)


@pytest.mark.asyncio
async def test_standing_memories_honours_its_limit_and_skips_inactive_rows(db):
    """The cap is what keeps the block from crowding out the period's own words,
    and `is_active` is the soft-delete the /memory endpoints write."""
    user_id = await _make_user(db)
    for i in range(6):
        await _make_memory(db, user_id, f"said {i}", IDENTICAL, entry_type="stated")
    gone = await _make_memory(db, user_id, "retracted", IDENTICAL, entry_type="stated")
    await db.execute(
        text("UPDATE memory_entries SET is_active = FALSE WHERE id = :id"), {"id": gone},
    )
    await db.flush()

    rows = await memory_service.standing_memories(db, user_id, limit=4)

    assert len(rows) == 4
    assert "retracted" not in [r.content for r in rows]


@pytest.mark.asyncio
async def test_standing_memories_never_crosses_users(db):
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _make_memory(db, mine, "mine", IDENTICAL, entry_type="stated")
    await _make_memory(db, theirs, "theirs", IDENTICAL, entry_type="stated")
    await db.flush()

    rows = await memory_service.standing_memories(db, mine, limit=4)

    assert [r.content for r in rows] == ["mine"]


# ── 2. The query plan (T-9) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_recall_query_plans_as_one_scan_with_one_window(db):
    """T-9. PLAN SHAPE, NEVER TIMING.

    Two structural claims, both stable at any table size:

      1. A WindowAgg node exists — the per-type ranking happens IN THE DATABASE,
         once, rather than by fetching everything and ranking in Python.
      2. `memory_entries` is scanned exactly once — the CTE did not become a
         self-join.

    WHAT THIS DELIBERATELY DOES NOT ASSERT: index usage. The design flagged
    (§2e) that HNSW is an ANN index over the whole table while recall is
    user-scoped, and that the window rewrite forecloses any ANN top-k shortcut.
    On a test table of a handful of rows Postgres will correctly choose a
    sequential scan, so asserting `Index Scan` would pin the planner's
    size-dependent choice rather than anything about the product. Nor does it
    assert a duration: a timing assertion on a CI runner is a flake generator.

    EXPLAIN runs the REAL query text (memory_service.RECALL_SQL), not a copy —
    a copy could drift from the query it claims to describe."""
    import json as _json

    user_id = await _make_user(db)
    await _make_memory(db, user_id, "one", IDENTICAL, entry_type="belief")
    await db.flush()

    plan_rows = await db.execute(
        text("EXPLAIN (FORMAT JSON) " + RECALL_SQL),
        {
            "query_vec": _vec(QUERY),
            "user_id": user_id,
            "standing_types": list(STANDING_TYPES),
            "standing_per_type": STANDING_PER_TYPE,
            "inferred_per_type": INFERRED_PER_TYPE,
            "floor": INFERRED_SCORE_FLOOR,
        },
    )
    raw = plan_rows.scalar_one()
    plan = _json.loads(raw) if isinstance(raw, str) else raw

    node_types = []
    relations = []

    def _walk(node):
        node_types.append(node.get("Node Type"))
        if node.get("Relation Name"):
            relations.append(node["Relation Name"])
        for child in node.get("Plans", []) or []:
            _walk(child)

    _walk(plan[0]["Plan"])

    assert "WindowAgg" in node_types, node_types
    assert relations.count("memory_entries") == 1, relations


# ── 3. Conversation delete SETs NULL on memory_entries and insights ─────────

@pytest.mark.asyncio
async def test_deleting_a_conversation_keeps_the_memories_extracted_from_it(db):
    """THE FLIP THIS TEST WAS WRITTEN TO RECEIVE. Migration 057, Memory-v2
    Ruling #7c (MEMORY_V2_DESIGN_2026-09-03 §4a).

    Its previous form pinned the opposite — `_memory_exists(...) is False`,
    carrying a docstring that said in as many words: "THE v2 MIGRATION WILL FLIP
    THIS TEST, DELIBERATELY. When conversation_id becomes SET NULL, this
    assertion inverts to 'the row survives with a NULL conversation_id'. That is
    the point of pinning it now: the change becomes a visible, intentional edit
    to this file rather than a silent behaviour swap."

    This is that edit. 013 set memory_entries.conversation_id to CASCADE as
    "derived data, safe to lose with parent"; 057 moves it into the category 013
    gave safety_events, "preserve the row, null out the conversation ref",
    because memory is no longer derived data that dies with one thread — it is
    the spine of chat recall, the letters, You-vs-You and the recurrence
    detector, and the explore copy promises the room carries it forward
    (MEMORY_V2_INVESTIGATION §2d).

    SURVIVING IS NOT ENOUGH TO ASSERT — the FK is read too. A row that survived
    still attached would mean the DELETE never happened; only conversation_id
    IS NULL proves SET NULL fired rather than nothing at all.
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

    assert await _memory_exists(db, from_conversation) is True       # ← flipped by 057
    assert await _memory_conversation_id(db, from_conversation) is None
    # Rows with a NULL conversation_id were never at risk, and must not be.
    assert await _memory_exists(db, standalone) is True


@pytest.mark.asyncio
async def test_deleting_a_conversation_keeps_the_insights_raised_in_it(db):
    """T-4, the insights half — and the half that had NO test at all before 057
    (design §4c: a repo-wide grep for the Insight model across apps/api/tests
    returned zero files). The memory half above could at least flip visibly; this
    one could have changed under everybody in silence.

    Same 013 category move, same reason, and a sharper one: insights are the
    "what the room noticed" block in every weekly and monthly letter, selected by
    user_id + is_dismissed + a created_at window and never by conversation_id, so
    a deleted thread used to silently thin future letters.
    """
    user_id = await _make_user(db)
    conversation_id = await _make_conversation(db, user_id)
    from_conversation = await _make_insight(
        db, user_id, "keeps circling the same decision", conversation_id=conversation_id,
    )
    standalone = await _make_insight(db, user_id, "raised outside any thread")
    await db.flush()

    await db.execute(
        text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id},
    )
    await db.flush()

    assert await _insight_exists(db, from_conversation) is True
    assert await _insight_conversation_id(db, from_conversation) is None
    assert await _insight_exists(db, standalone) is True


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


@pytest.mark.asyncio
async def test_deleting_a_user_still_destroys_their_insights(db):
    """The F-10 analogue for insights. 057 loosened the CONVERSATION FK on this
    table and must not have touched the USER one: erasure (GDPR Art. 17) runs
    through insights.user_id, which stays CASCADE.

    The orphaned insight is the case that matters. It has no conversation left to
    be deleted through, so if user_id did not reach it, it would outlive the
    account with the person's content in it — a row 057 newly makes possible and
    the exact thing that must not survive."""
    user_id = await _make_user(db)
    conversation_id = await _make_conversation(db, user_id)
    attached = await _make_insight(
        db, user_id, "raised in a thread", conversation_id=conversation_id,
    )
    standalone = await _make_insight(db, user_id, "raised outside any thread")
    await db.flush()

    # Orphan one FIRST, so the account delete has to reach a row whose only
    # remaining link to the user is user_id itself.
    await db.execute(
        text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id},
    )
    await db.flush()
    assert await _insight_exists(db, attached) is True  # orphaned, not gone

    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await db.flush()

    assert await _insight_exists(db, attached) is False
    assert await _insight_exists(db, standalone) is False
    survivors = (await db.execute(
        text("SELECT count(*) FROM insights WHERE user_id = :id"), {"id": user_id},
    )).scalar_one()
    assert survivors == 0


# ── 5. Orphans and detect_recurrence (T-5) ──────────────────────────────────

@pytest.mark.asyncio
async def test_an_orphaned_memory_is_not_counted_as_a_prior_conversation(db):
    """T-5. detect_recurrence looks for the same theme in the user's OTHER
    conversations, excluding the current one with `AND conversation_id != :cid`.
    For an orphan that predicate is NULL, not TRUE, so SQL's three-valued logic
    drops the row — orphans are invisible as recurrence evidence.

    That is the SAFE direction and it is why source_count stays honest: the
    count is "distinct prior conversations + 1", so a row with no conversation
    has no conversation to contribute. Before 057 these rows did not exist at
    all, so this is an opportunity not taken rather than a regression — but it
    is now a property of live data, and it is asserted here rather than reasoned
    about.

    The query is reproduced rather than driven through detect_recurrence: that
    method makes LLM calls and commits, and what T-5 is about is the WHERE
    clause's NULL semantics, which is exactly the part a mock cannot enforce.
    """
    user_id = await _make_user(db)
    current = await _make_conversation(db, user_id)
    other = await _make_conversation(db, user_id)
    doomed = await _make_conversation(db, user_id)

    await _make_memory(db, user_id, "in the current thread", IDENTICAL, conversation_id=current)
    await _make_memory(db, user_id, "in another thread", IDENTICAL, conversation_id=other)
    await _make_memory(db, user_id, "in a thread about to go", IDENTICAL, conversation_id=doomed)
    await db.flush()

    async def _prior_conversations() -> set:
        rows = (await db.execute(
            text(
                "SELECT conversation_id FROM memory_entries "
                "WHERE user_id = :uid AND is_active = TRUE AND embedding IS NOT NULL "
                "  AND conversation_id != :cid"
            ),
            {"uid": user_id, "cid": current},
        )).scalars().all()
        # asyncpg decodes uuid columns to uuid.UUID; the helpers above hand back
        # str, so normalize here or the set comparison fails on type, not content.
        return {str(r) for r in rows}

    assert await _prior_conversations() == {other, doomed}

    await db.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": doomed})
    await db.flush()

    # The row survived 057's SET NULL — and dropped out of the candidate set,
    # because NULL != :cid is NULL, not TRUE.
    assert (await db.execute(
        text("SELECT count(*) FROM memory_entries WHERE user_id = :uid"), {"uid": user_id},
    )).scalar_one() == 3
    assert await _prior_conversations() == {other}
    # source_count is distinct prior conversations + 1: 2 before, 1 after. The
    # orphan cannot inflate it, and cannot be double-counted against NULL.
    assert len(await _prior_conversations()) + 1 == 2
