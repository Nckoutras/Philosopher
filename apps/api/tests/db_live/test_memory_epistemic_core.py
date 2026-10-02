"""MEM2-A — the epistemic core on memory_entries (migrations 070 + 071).

What needs a real Postgres here, and why each piece is in this file rather than
behind a mock:

1. THE TWO CHECK CONSTRAINTS. Enforced by the server and nothing else; the model
   declaration is DDL metadata the ORM never evaluates (ck_insights_ring_true
   precedent). Both sides are compared as sets of literals.
2. THE 071 BACKFILL, run as its own statements (BACKFILL_STATEMENTS) against
   rows shaped like production's — and run TWICE, because "idempotent" is a
   claim about the second run and can only be checked by making one.
3. EVERY WRITER'S METADATA, through the real task / service / route with real
   commits, read back with a fresh session. A row that was only flushed is not
   there.
4. THE REJECTION LOOP. The 'no' verdict and the rows it retires must land in one
   commit, scoped to the person, without touching rows retired for another
   reason. A mocked session would accept any UPDATE and prove none of that.
5. MIGRATION DOWN AND UP. 070's downgrade must actually remove what it added, and
   upgrading again must succeed on a database that already has data.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_memory_epistemic_core.py -v
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Same arrangement as test_period_recurrence_filter.py: pytest does not put this
# directory on the path, and conftest.py is not importable by name, so the
# factories come from a sibling module and the alembic step is spelled out below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_memory_recall_and_cascades import _make_conversation, _make_user  # noqa: E402

API_DIR = Path(__file__).resolve().parent.parent.parent

PROVENANCE = {"user_stated", "user_selected", "system_inferred"}
INACTIVE_REASONS = {"superseded", "user_removed", "user_rejected"}
NEW_COLUMNS = {
    "provenance", "source_surface", "source_message_ids",
    "supersedes_memory_id", "inactive_reason",
}
FAKE_EMBEDDING = [0.01] * 1536


def _literals(sql_text: str) -> set[str]:
    return set(re.findall(r"'([^']*)'", sql_text))


def _load_071():
    """The migration module, loaded by path: its filename starts with a digit and
    is not importable by name."""
    path = API_DIR / "db" / "migrations" / "versions" / "071_memory_provenance_backfill.py"
    spec = importlib.util.spec_from_file_location("migration_071", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Real commits on the test database ─────────────────────────────────────────

@pytest_asyncio.fixture
async def live(schema, monkeypatch):
    """Tasks open their OWN session via db.session.AsyncSessionLocal and commit it,
    so they get a real sessionmaker here (test_safety_events_committed precedent),
    and everything is cleaned up by deleting the user — memory_entries, insights and
    user_preferences all cascade on users.id."""
    import db.session as db_session

    engine = create_async_engine(schema)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "AsyncSessionLocal", Session)

    created: list[str] = []

    async def make_user() -> str:
        uid = str(uuid.uuid4())
        async with Session() as s:
            await s.execute(
                text("INSERT INTO users (id, email) VALUES (:id, :e)"),
                {"id": uid, "e": f"{uid}@example.test"},
            )
            await s.commit()
        created.append(uid)
        return uid

    try:
        yield SimpleNamespace(Session=Session, make_user=make_user)
    finally:
        async with Session() as s:
            for uid in created:
                await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
            await s.commit()
        await engine.dispose()


async def _rows(Session, user_id: str) -> list:
    async with Session() as s:
        return list(await s.execute(
            text(
                "SELECT id::text AS id, entry_type, is_active, provenance, source_surface,"
                " source_message_ids, supersedes_memory_id::text AS supersedes,"
                " inactive_reason, created_at"
                " FROM memory_entries WHERE user_id = :u ORDER BY created_at, id"
            ),
            {"u": user_id},
        ))


async def _insert_row(s, user_id, entry_type, *, is_active=True, source_turn=None,
                      conversation_id=None, created_offset_s=0, **cols) -> str:
    mid = str(uuid.uuid4())
    names = ["id", "user_id", "entry_type", "content", "is_active", "source_turn",
             "conversation_id", "created_at", *cols.keys()]
    values = {
        "id": mid, "user_id": user_id, "entry_type": entry_type,
        "content": f"{entry_type} row", "is_active": is_active,
        "source_turn": source_turn, "conversation_id": conversation_id,
        "off": float(created_offset_s), **cols,
    }
    placeholders = [
        ":id", ":user_id", ":entry_type", ":content", ":is_active", ":source_turn",
        ":conversation_id", "now() + make_interval(secs => :off)",
        *[f":{k}" for k in cols],
    ]
    await s.execute(
        text(f"INSERT INTO memory_entries ({', '.join(names)}) VALUES ({', '.join(placeholders)})"),
        values,
    )
    return mid


# ── 1. Schema and constraints ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_070_adds_five_nullable_columns(db):
    cols = {
        r.column_name: r.is_nullable
        for r in await db.execute(text(
            "SELECT column_name, is_nullable FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = 'memory_entries'"
        ))
    }
    assert NEW_COLUMNS <= set(cols), NEW_COLUMNS - set(cols)
    assert all(cols[c] == "YES" for c in NEW_COLUMNS), "070 is additive: every new column is NULLable"


@pytest.mark.asyncio
@pytest.mark.parametrize("name,expected", [
    ("ck_memory_entries_provenance", PROVENANCE),
    ("ck_memory_entries_inactive_reason", INACTIVE_REASONS),
])
async def test_the_live_constraints_match_the_model(db, name, expected):
    from models import MemoryEntry

    live = (await db.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    )).scalar_one_or_none()
    assert live is not None, f"{name} is missing from the live schema"
    assert _literals(live) == expected

    declared = next(c for c in MemoryEntry.__table__.constraints if c.name == name)
    assert _literals(str(declared.sqltext)) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("column", ["provenance", "inactive_reason"])
async def test_an_off_vocabulary_value_is_refused_by_postgres(db, column):
    uid = await _make_user(db)
    with pytest.raises(Exception) as excinfo:
        await _insert_row(db, uid, "belief", **{column: "maybe"})
        await db.flush()
    assert f"ck_memory_entries_{column}" in str(excinfo.value)


@pytest.mark.asyncio
async def test_deleting_a_superseded_row_unlinks_rather_than_blocks(db):
    """ON DELETE SET NULL on the self-FK: removing the older row (account-level
    cleanup, C-07) must not be refused because a newer row points at it."""
    uid = await _make_user(db)
    old = await _insert_row(db, uid, "self_portrait", is_active=False, source_turn=7)
    new = await _insert_row(db, uid, "self_portrait", source_turn=7, supersedes_memory_id=old)
    await db.execute(text("DELETE FROM memory_entries WHERE id = :id"), {"id": old})
    link = (await db.execute(
        text("SELECT supersedes_memory_id FROM memory_entries WHERE id = :id"), {"id": new},
    )).scalar_one()
    assert link is None


# ── 2. The 071 backfill, run twice ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_071_backfills_production_shaped_rows_and_is_idempotent(db):
    mod = _load_071()
    uid = await _make_user(db)

    # Legacy rows: every new column NULL, as production has them before 071.
    ids = {
        "stated": await _insert_row(db, uid, "stated"),
        "counterview_belief": await _insert_row(db, uid, "counterview_belief"),
        "onboarding_old": await _insert_row(db, uid, "onboarding_profile", is_active=False, source_turn=0),
        "onboarding_new": await _insert_row(db, uid, "onboarding_profile", source_turn=0, created_offset_s=1),
        "portrait_1": await _insert_row(db, uid, "self_portrait", is_active=False, source_turn=42),
        "portrait_2": await _insert_row(db, uid, "self_portrait", is_active=False, source_turn=42, created_offset_s=1),
        "portrait_3": await _insert_row(db, uid, "self_portrait", source_turn=42, created_offset_s=2),
        "portrait_other_q": await _insert_row(db, uid, "self_portrait", source_turn=99),
        "shift_old": await _insert_row(db, uid, "self_portrait_shift", is_active=False, source_turn=42),
        "shift_new": await _insert_row(db, uid, "self_portrait_shift", source_turn=42, created_offset_s=1),
        "struggle": await _insert_row(db, uid, "struggle", conversation_id=None),
        "grief": await _insert_row(db, uid, "grief"),   # an unrequested type: the catch-all
    }

    async def snapshot():
        return {
            r.id: r for r in await db.execute(text(
                "SELECT id::text AS id, provenance, source_surface, source_message_ids,"
                " inactive_reason, supersedes_memory_id::text AS supersedes"
                " FROM memory_entries WHERE user_id = :u"
            ), {"u": uid})
        }

    for statement in mod.BACKFILL_STATEMENTS:
        await db.execute(text(statement))
    first = await snapshot()

    def row(key):
        return first[ids[key]]

    assert row("stated").provenance == "user_stated"
    assert row("stated").source_surface is None, "stated rows' surface was never stored"
    assert row("counterview_belief").provenance == "user_stated"
    assert row("counterview_belief").source_surface == "counterview_belief"
    assert row("onboarding_new").provenance == "user_selected"
    assert row("onboarding_new").source_surface == "onboarding"
    assert row("portrait_3").provenance == "user_selected"
    assert row("portrait_3").source_surface == "self_portrait"
    assert row("shift_new").provenance == "system_inferred", "founder ruling 2026-10-02"
    assert row("shift_new").source_surface == "self_portrait"
    assert row("struggle").provenance == "system_inferred"
    assert row("struggle").source_surface == "chat"
    assert row("grief").provenance == "system_inferred"
    assert row("grief").source_surface == "chat"

    # Every legacy row: no message ids (R9).
    assert all(r.source_message_ids is None for r in first.values())

    # Inactive -> superseded; active rows carry no reason.
    for key in ("onboarding_old", "portrait_1", "portrait_2", "shift_old"):
        assert row(key).inactive_reason == "superseded", key
    for key in ("onboarding_new", "portrait_3", "struggle", "stated"):
        assert row(key).inactive_reason is None, key

    # Chains: 3 -> 2 -> 1 per question; the first answer and other questions unlinked.
    assert row("portrait_3").supersedes == ids["portrait_2"]
    assert row("portrait_2").supersedes == ids["portrait_1"]
    assert row("portrait_1").supersedes is None
    assert row("portrait_other_q").supersedes is None
    assert row("shift_new").supersedes == ids["shift_old"]
    # Onboarding: set replaces set, never linked.
    assert row("onboarding_new").supersedes is None

    for statement in mod.BACKFILL_STATEMENTS:
        await db.execute(text(statement))
    second = await snapshot()
    assert second == first, "a second run of 071 must change nothing"


@pytest.mark.asyncio
async def test_071_never_overwrites_a_value_a_writer_already_stamped(db):
    mod = _load_071()
    uid = await _make_user(db)
    rejected = await _insert_row(
        db, uid, "struggle", is_active=False,
        provenance="system_inferred", source_surface="chat", inactive_reason="user_rejected",
    )
    for statement in mod.BACKFILL_STATEMENTS:
        await db.execute(text(statement))
    reason = (await db.execute(
        text("SELECT inactive_reason FROM memory_entries WHERE id = :id"), {"id": rejected},
    )).scalar_one()
    assert reason == "user_rejected"


# ── 3. Every writer stamps its metadata ───────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_extraction_stamps_inferred_chat_and_both_message_ids(live):
    from services.memory_service import memory_service

    uid = await live.make_user()
    async with live.Session() as s:
        conv = await _make_conversation(s, uid)
        await s.commit()

    msg_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    extracted = json.dumps([
        {"type": "struggle", "content": "User is weighing a hard decision about work.", "confidence": 0.9},
    ])
    with patch("services.memory_service.llm_client.complete", AsyncMock(return_value=extracted)), \
         patch("services.memory_service.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)):
        async with live.Session() as s:
            await memory_service.extract_and_store(
                db=s, user_id=uid, conversation_id=conv, persona_id=None,
                user_text="I keep weighing whether to leave my work behind.",
                assistant_text="That weighing is itself telling.",
                source_turn=0, safety_ok=False, source_message_ids=msg_ids,
            )
            await s.commit()

    (r,) = await _rows(live.Session, uid)
    assert r.provenance == "system_inferred"
    assert r.source_surface == "chat"
    assert [str(x) for x in r.source_message_ids] == msg_ids, "user id first, then assistant"


@pytest.mark.asyncio
async def test_a_job_queued_before_070_stores_null_message_ids(live):
    """The trailing argument's default: a stale-queued job runs and guesses nothing."""
    from services.memory_service import memory_service

    uid = await live.make_user()
    extracted = json.dumps([{"type": "value", "content": "User values candour.", "confidence": 0.9}])
    with patch("services.memory_service.llm_client.complete", AsyncMock(return_value=extracted)), \
         patch("services.memory_service.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)):
        async with live.Session() as s:
            await memory_service.extract_and_store(
                db=s, user_id=uid, conversation_id=None, persona_id=None,
                user_text="Candour matters more to me than comfort does.",
                assistant_text="Then say so.",
            )
            await s.commit()

    (r,) = await _rows(live.Session, uid)
    assert r.source_message_ids is None
    assert r.provenance == "system_inferred"


@pytest.mark.asyncio
async def test_distill_stores_its_source_label_as_the_surface(live):
    from workers.arq_worker import distill_user_text_to_memory_task

    uid = await live.make_user()
    safe = SimpleNamespace(should_suppress_persona=False)
    with patch("services.safety_service.safety_service.check_input", AsyncMock(return_value=safe)), \
         patch("services.memory_service.distill_to_memory", AsyncMock(return_value="User wants to write more.")), \
         patch("services.embedding_client.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)):
        await distill_user_text_to_memory_task({}, uid, None, "I want to write more than I do.", "letter_write_back")

    (r,) = await _rows(live.Session, uid)
    assert r.entry_type == "stated"
    assert r.provenance == "user_stated"
    assert r.source_surface == "letter_write_back"


@pytest.mark.asyncio
async def test_counterview_belief_is_user_stated(live):
    from workers.arq_worker import counterview_belief_task

    uid = await live.make_user()
    with patch("services.embedding_client.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)), \
         patch("services.memory_service.memory_service.detect_recurrence", AsyncMock()):
        await counterview_belief_task({}, uid, "If I do not do it myself it will not be done right.")

    (r,) = await _rows(live.Session, uid)
    assert r.provenance == "user_stated"
    assert r.source_surface == "counterview_belief"


@pytest.mark.asyncio
async def test_onboarding_reseed_supersedes_the_old_set_without_links(live):
    from workers.arq_worker import seed_profile_memory_task

    uid = await live.make_user()

    async def set_profile(values):
        async with live.Session() as s:
            await s.execute(
                text(
                    "INSERT INTO user_preferences (user_id, need_most, profile)"
                    " VALUES (:u, 'comfort', CAST(:p AS jsonb))"
                    " ON CONFLICT (user_id) DO UPDATE SET profile = EXCLUDED.profile"
                ),
                {"u": uid, "p": json.dumps({"values": values})},
            )
            await s.commit()

    with patch("services.embedding_client.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)):
        await set_profile(["honesty"])
        await seed_profile_memory_task({}, uid)
        await set_profile(["freedom"])
        await seed_profile_memory_task({}, uid)

    old, new = await _rows(live.Session, uid)
    assert (old.is_active, old.inactive_reason) == (False, "superseded")
    assert (new.is_active, new.inactive_reason) == (True, None)
    for r in (old, new):
        assert r.provenance == "user_selected"
        assert r.source_surface == "onboarding"
        assert r.supersedes is None, "set replaces set: no one-for-one link"


@pytest.mark.asyncio
async def test_portrait_reanswer_links_the_new_row_to_the_one_it_replaced(live):
    from services.self_portrait import free_question_ids, get_question
    from workers.arq_worker import seed_self_portrait_memory_task

    uid = await live.make_user()
    qid = sorted(free_question_ids())[0]
    assert len(get_question(qid)["pills"]) >= 2

    async def answer(index):
        async with live.Session() as s:
            await s.execute(
                text(
                    "INSERT INTO user_preferences (user_id, need_most, profile)"
                    " VALUES (:u, 'comfort', CAST(:p AS jsonb))"
                    " ON CONFLICT (user_id) DO UPDATE SET profile = EXCLUDED.profile"
                ),
                {"u": uid, "p": json.dumps({"answers": {qid: index}})},
            )
            await s.commit()

    with patch("services.embedding_client.embedding_client.embed", AsyncMock(return_value=FAKE_EMBEDDING)):
        await answer(0)
        await seed_self_portrait_memory_task({}, uid, qid, None)
        await answer(1)
        await seed_self_portrait_memory_task({}, uid, qid, 0)

    rows = await _rows(live.Session, uid)
    portraits = [r for r in rows if r.entry_type == "self_portrait"]
    shifts = [r for r in rows if r.entry_type == "self_portrait_shift"]
    first, second = portraits

    assert (first.is_active, first.inactive_reason) == (False, "superseded")
    assert (second.is_active, second.inactive_reason) == (True, None)
    assert second.supersedes == first.id
    assert first.supersedes is None
    for r in portraits:
        assert (r.provenance, r.source_surface) == ("user_selected", "self_portrait")

    (shift,) = shifts
    assert shift.provenance == "system_inferred", "founder ruling 2026-10-02"
    assert shift.source_surface == "self_portrait"
    assert shift.supersedes is None, "the first shift for this question replaces nothing"


@pytest.mark.asyncio
async def test_delete_memory_records_user_removed(live):
    from routers.memory import delete_memory

    uid = await live.make_user()
    async with live.Session() as s:
        mid = await _insert_row(s, uid, "belief", provenance="system_inferred")
        await s.commit()
    async with live.Session() as s:
        await delete_memory(mid, db=s, user=SimpleNamespace(id=uid))
        await s.commit()   # get_db's teardown commit, made explicit

    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (False, "user_removed")


# ── 4. The rejection loop (R3) ────────────────────────────────────────────────

async def _insight(s, user_id, evidence) -> str:
    iid = str(uuid.uuid4())
    await s.execute(
        text(
            "INSERT INTO insights (id, user_id, content, insight_type, evidence)"
            " VALUES (:id, :u, 'This theme keeps returning.', 'pattern', CAST(:ev AS jsonb))"
        ),
        {"id": iid, "u": user_id, "ev": json.dumps(evidence) if evidence is not None else None},
    )
    return iid


def _evidence(recurring_id, *prior_ids):
    return {
        "recurring_entry": {"memory_entry_id": recurring_id, "text": "now", "conversation_id": None},
        "prior_matches": [
            {"memory_entry_id": p, "text": "before", "conversation_id": None, "score": 0.8}
            for p in prior_ids
        ],
        "shown_to_classifier": len(prior_ids),
        "detector": {"threshold": 0.75, "limit": 20, "window": None},
    }


async def _verdict(live, uid, iid, verdict):
    from routers.memory import set_insight_ring_true
    from schemas import InsightRingTrueRequest

    with patch("routers.memory.analytics_service"):
        async with live.Session() as s:
            return await set_insight_ring_true(
                iid, InsightRingTrueRequest(ring_true=verdict), db=s, user=SimpleNamespace(id=uid),
            )


@pytest.mark.asyncio
async def test_a_no_retires_exactly_the_cited_active_rows_of_this_person(live):
    uid = await live.make_user()
    other = await live.make_user()
    async with live.Session() as s:
        recurring = await _insert_row(s, uid, "struggle")
        prior = await _insert_row(s, uid, "pattern")
        already_superseded = await _insert_row(s, uid, "self_portrait", is_active=False,
                                               inactive_reason="superseded")
        uncited = await _insert_row(s, uid, "value")
        someone_elses = await _insert_row(s, other, "struggle")
        iid = await _insight(s, uid, _evidence(
            recurring, prior, already_superseded, someone_elses, "not-a-uuid",
        ))
        await s.commit()

    out = await _verdict(live, uid, iid, "no")
    assert out.ring_true == "no"

    mine = {r.id: r for r in await _rows(live.Session, uid)}
    assert (mine[recurring].is_active, mine[recurring].inactive_reason) == (False, "user_rejected")
    assert (mine[prior].is_active, mine[prior].inactive_reason) == (False, "user_rejected")
    assert mine[already_superseded].inactive_reason == "superseded", "an earlier reason is kept"
    assert (mine[uncited].is_active, mine[uncited].inactive_reason) == (True, None)
    (theirs,) = await _rows(live.Session, other)
    assert (theirs.is_active, theirs.inactive_reason) == (True, None), "never another person's row"

    async with live.Session() as s:
        stored = (await s.execute(
            text("SELECT ring_true FROM insights WHERE id = :id"), {"id": iid},
        )).scalar_one()
    assert stored == "no"


@pytest.mark.asyncio
async def test_the_verdict_and_the_retirement_commit_together(live):
    """One transaction: if the commit fails, NEITHER the verdict NOR the retired
    rows survive. The commit is made to fail after both writes are staged."""
    uid = await live.make_user()
    async with live.Session() as s:
        recurring = await _insert_row(s, uid, "struggle")
        iid = await _insight(s, uid, _evidence(recurring))
        await s.commit()

    from routers.memory import set_insight_ring_true
    from schemas import InsightRingTrueRequest

    with patch("routers.memory.analytics_service"):
        async with live.Session() as s:
            s.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
            with pytest.raises(RuntimeError):
                await set_insight_ring_true(
                    iid, InsightRingTrueRequest(ring_true="no"), db=s, user=SimpleNamespace(id=uid),
                )
            await s.rollback()

    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (True, None)
    async with live.Session() as s:
        stored = (await s.execute(
            text("SELECT ring_true FROM insights WHERE id = :id"), {"id": iid},
        )).scalar_one()
    assert stored is None


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence", [None, {}, {"prior_matches": []}])
async def test_a_no_without_evidence_is_a_no_op(live, evidence):
    """Signal insights carry no evidence (R4, Phase B), and nothing is guessed."""
    uid = await live.make_user()
    async with live.Session() as s:
        row = await _insert_row(s, uid, "belief")
        iid = await _insight(s, uid, evidence)
        await s.commit()

    out = await _verdict(live, uid, iid, "no")
    assert out.ring_true == "no"
    (r,) = await _rows(live.Session, uid)
    assert (r.id, r.is_active, r.inactive_reason) == (row, True, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", ["yes", "partly"])
async def test_yes_and_partly_write_no_memory(live, verdict):
    uid = await live.make_user()
    async with live.Session() as s:
        recurring = await _insert_row(s, uid, "struggle")
        iid = await _insight(s, uid, _evidence(recurring))
        await s.commit()

    await _verdict(live, uid, iid, verdict)
    (r,) = await _rows(live.Session, uid)
    assert (r.is_active, r.inactive_reason) == (True, None)


# ── 5. Down and up ────────────────────────────────────────────────────────────

def _columns(url: str) -> set[str]:
    import asyncio

    async def fetch():
        conn = await asyncpg.connect(url.replace("+asyncpg", ""))
        try:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_schema = 'public' AND table_name = 'memory_entries'"
            )
            return {r["column_name"] for r in rows}
        finally:
            await conn.close()

    return asyncio.run(fetch())


def _alembic(url: str, *args: str) -> None:
    """One alembic step against the TEST database, in a subprocess — the same
    reason conftest gives: alembic reads the URL through an already-built config."""
    env = {
        **os.environ,
        "DATABASE_URL": url,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "sk-test-dummy"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "test-dummy"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_DIR, env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"alembic {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}"
    )


def test_070_and_071_downgrade_cleanly_and_upgrade_again(schema):
    """Synchronous: alembic runs in a subprocess and the column read drives its own
    loop. The schema is ALWAYS returned to head, so a failure here cannot leave the
    rest of the session running against 069."""
    try:
        _alembic(schema, "downgrade", "069_another_mind_count")
        cols = _columns(schema)
        assert not (NEW_COLUMNS & cols), f"070 downgrade left {NEW_COLUMNS & cols}"
    finally:
        _alembic(schema, "upgrade", "head")
    assert NEW_COLUMNS <= _columns(schema)
