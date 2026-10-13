"""UAT-TOPIC-001 PR-B — migration 075 retires topic-derived memory and marks topic turns.

What needs a real Postgres here, and why:

1. THE MATCHING RULE. It is a SQL join over messages, daily_questions and
   memory_entries: btrim, a concatenated tail with U+2014, a uuid[] subscript, and a
   correlated "next user message" bound. Reading it verifies none of that; a driver
   executing it does (CLAUDE.md, 2026-09-15). The tests run the migration's OWN
   statements (COUNT_SQL, RETIRE_SQL, MARK_SQL), not copies (071 precedent).
2. WHAT IT MUST NOT TOUCH. Words the person typed that merely contain a topic, a
   look-alike tail, a topic quoted by the assistant, rows after the next user turn,
   rows linked to a different message, and rows already retired for another reason.
3. THE REAL upgrade() AND downgrade(), through alembic, over committed rows: the
   count guard executes, the downgrade reactivates exactly what 075 retired, and
   the constraint narrows and widens again.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_not_user_words_075.py -v
"""
import asyncio
import importlib.util
import os
import random
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

API_DIR = Path(__file__).resolve().parent.parent.parent
TAIL = " Let's think through this together — where would you start?"


def _load_075():
    path = API_DIR / "db" / "migrations" / "versions" / "075_not_user_words.py"
    spec = importlib.util.spec_from_file_location("migration_075", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixture rows, shaped like production's ───────────────────────────────────

async def _exec(s, sql, **params):
    return await s.execute(text(sql), params)


async def _user(s) -> str:
    uid = str(uuid.uuid4())
    await _exec(s, "INSERT INTO users (id, email) VALUES (:id, :e)", id=uid, e=f"{uid}@example.test")
    return uid


async def _conv(s, uid) -> str:
    cid = str(uuid.uuid4())
    pid = (await _exec(s, "SELECT id FROM personas LIMIT 1")).scalar_one()
    await _exec(s, "INSERT INTO conversations (id, user_id, persona_id) VALUES (:id, :u, :p)",
                id=cid, u=uid, p=pid)
    return cid


async def _msg(s, uid, cid, role, content, at_s) -> str:
    """at_s: seconds after now(), so the order is explicit and nothing binds a
    timestamptz from Python (TD-76)."""
    mid = str(uuid.uuid4())
    await _exec(
        s,
        "INSERT INTO messages (id, conversation_id, user_id, role, content, safety_level, created_at)"
        " VALUES (:id, :c, :u, :r, :t, 'none', now() + make_interval(secs => :at))",
        id=mid, c=cid, u=uid, r=role, t=content, at=float(at_s),
    )
    return mid


async def _mem(s, uid, cid, at_s, *, ids=None, active=True, reason=None) -> str:
    """ids=None is a pre-070 row (timing rule); a list is a linked row."""
    mid = str(uuid.uuid4())
    await _exec(
        s,
        "INSERT INTO memory_entries (id, user_id, conversation_id, entry_type, content,"
        " is_active, inactive_reason, source_message_ids, created_at)"
        " VALUES (:id, :u, :c, 'belief', 'a claim', :act, :rsn, CAST(:ids AS uuid[]),"
        " now() + make_interval(secs => :at))",
        id=mid, u=uid, c=cid, act=active, rsn=reason,
        ids=[uuid.UUID(i) for i in ids] if ids else None, at=float(at_s),
    )
    return mid


async def _seed(s) -> dict:
    """One question, two accounts, every case the rule must and must not catch."""
    q = f"A topic nobody typed {uuid.uuid4()} — what would you keep?"
    qid = str(uuid.uuid4())
    # INACTIVE: production's 80 rows include retired ones, and the rule ignores `active`.
    await _exec(s, "INSERT INTO daily_questions (id, question_text, display_order, active)"
                   " VALUES (:id, :q, :o, false)",
                id=qid, q=q, o=random.randint(10_000_000, 99_999_999))
    u, v = await _user(s), await _user(s)
    k = {"qid": qid, "users": [u, v]}

    # 1. Exact topic (space-padded: btrim strips spaces only, and production has no padded
    #    topic turns at all, 2026-10-13), legacy rows bounded by the next user turn.
    c = await _conv(s, u)
    k["topic_exact"] = await _msg(s, u, c, "user", f"  {q}  ", 0)
    await _msg(s, u, c, "assistant", "a reply", 1)
    k["legacy_in_window"] = await _mem(s, u, c, 2)
    k["legacy_superseded"] = await _mem(s, u, c, 3, active=False, reason="superseded")
    k["next_user"] = await _msg(s, u, c, "user", "my own words", 10)
    k["legacy_after_next"] = await _mem(s, u, c, 11)

    # 2. Tailed topic, linked rows: the link decides, never the timing.
    c = await _conv(s, u)
    k["topic_tailed"] = await _msg(s, u, c, "user", q + TAIL, 0)
    a = await _msg(s, u, c, "assistant", "a reply", 1)
    reply = await _msg(s, u, c, "user", "here is what I think", 5)
    k["linked_to_topic"] = await _mem(s, u, c, 6, ids=[k["topic_tailed"], a])      # late, but linked
    k["linked_to_reply"] = await _mem(s, u, c, 3, ids=[reply, a])                  # in window, but not linked

    # 3. Look-alikes that are the person's words, or not the person's at all.
    c = await _conv(s, u)
    k["typed_containing"] = await _msg(s, u, c, "user", q + " and I think it is courage", 0)
    k["legacy_after_typed"] = await _mem(s, u, c, 2)
    c = await _conv(s, u)
    k["hyphen_tail"] = await _msg(s, u, c, "user", q + TAIL.replace("—", "-"), 0)
    k["legacy_after_hyphen"] = await _mem(s, u, c, 2)
    c = await _conv(s, u)
    k["assistant_quote"] = await _msg(s, u, c, "assistant", q, 0)
    k["legacy_after_quote"] = await _mem(s, u, c, 2)

    # 4. Another account: the ruling is every account.
    c = await _conv(s, v)
    k["other_topic"] = await _msg(s, v, c, "user", q, 0)
    k["other_legacy"] = await _mem(s, v, c, 2)
    return k


async def _state(s, k) -> dict:
    mem = {r.id: (r.is_active, r.inactive_reason) for r in await _exec(
        s, "SELECT id::text AS id, is_active, inactive_reason FROM memory_entries"
           " WHERE user_id = ANY(CAST(:u AS uuid[]))", u=[uuid.UUID(x) for x in k["users"]])}
    msg = {r.id: r.message_kind for r in await _exec(
        s, "SELECT id::text AS id, message_kind FROM messages"
           " WHERE user_id = ANY(CAST(:u AS uuid[]))", u=[uuid.UUID(x) for x in k["users"]])}
    return {"mem": mem, "msg": msg}


RETIRED = ("legacy_in_window", "linked_to_topic", "other_legacy")
UNTOUCHED_ACTIVE = ("legacy_after_next", "linked_to_reply", "legacy_after_typed",
                    "legacy_after_hyphen", "legacy_after_quote")
MARKED = ("topic_exact", "topic_tailed", "other_topic")
STANDARD = ("next_user", "typed_containing", "hyphen_tail", "assistant_quote")


def _assert_cleaned(state, k):
    for key in RETIRED:
        assert state["mem"][k[key]] == (False, "not_user_words"), key
    for key in UNTOUCHED_ACTIVE:
        assert state["mem"][k[key]] == (True, None), key
    assert state["mem"][k["legacy_superseded"]] == (False, "superseded"), \
        "an already-inactive row keeps its reason (ruling 2026-10-12)"
    for key in MARKED:
        assert state["msg"][k[key]] == "daily_topic", key
    for key in STANDARD:
        assert state["msg"][k[key]] == "standard", key


# ── 1–2. The statements, on a rolled-back transaction ────────────────────────

@pytest.mark.asyncio
async def test_the_rule_counts_retires_and_marks_exactly_the_topic_cases(db):
    mod = _load_075()
    k = await _seed(db)

    before = (await db.execute(text(mod.COUNT_SQL))).one()
    retired = (await db.execute(text(mod.RETIRE_SQL))).rowcount
    marked = (await db.execute(text(mod.MARK_SQL))).rowcount
    after = (await db.execute(text(mod.COUNT_SQL))).one()

    # The guard's arithmetic, on this database: whatever else it holds, the counts
    # reconcile, and they include at least the cases seeded here.
    assert retired == before.rows_active >= len(RETIRED)
    assert marked == before.topics_standard >= len(MARKED)
    assert (after.rows_active, after.topics_standard) == (0, 0)
    assert after.topics == before.topics, "marking a turn must not change whether it matches"

    _assert_cleaned(await _state(db, k), k)


@pytest.mark.asyncio
async def test_a_second_run_changes_nothing(db):
    mod = _load_075()
    k = await _seed(db)
    await db.execute(text(mod.RETIRE_SQL))
    await db.execute(text(mod.MARK_SQL))
    first = await _state(db, k)

    assert (await db.execute(text(mod.RETIRE_SQL))).rowcount == 0
    assert (await db.execute(text(mod.MARK_SQL))).rowcount == 0
    assert await _state(db, k) == first


@pytest.mark.asyncio
async def test_not_user_words_is_accepted_and_an_off_vocabulary_value_still_refused(db):
    k = await _seed(db)
    await _exec(db, "UPDATE memory_entries SET is_active = false, inactive_reason = 'not_user_words'"
                    " WHERE id = :id", id=k["legacy_in_window"])
    with pytest.raises(Exception) as excinfo:
        await _exec(db, "UPDATE memory_entries SET inactive_reason = 'not_mine' WHERE id = :id",
                    id=k["legacy_after_next"])
    assert "ck_memory_entries_inactive_reason" in str(excinfo.value)


# ── 3. The real upgrade() and downgrade(), through alembic ───────────────────

def _alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATABASE_URL": url,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "sk-test-dummy"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "test-dummy"),
    }
    proc = subprocess.run([sys.executable, "-m", "alembic", *args],
                          cwd=API_DIR, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, f"alembic {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc


def _committed(url, fn):
    async def run():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                return await fn(conn)
        finally:
            await engine.dispose()
    return asyncio.run(run())


async def _constraint_literals(conn) -> set[str]:
    sql = (await conn.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
        " WHERE conname = 'ck_memory_entries_inactive_reason'"))).scalar_one()
    return set(re.findall(r"'([^']*)'", sql))


def test_075_upgrade_guards_and_cleans_and_downgrade_reverses_it(schema):
    """Synchronous for the same reason as the 070 round trip. The schema is ALWAYS
    returned to head, and the seeded rows are always deleted."""
    k = _committed(schema, _seed)
    try:
        _alembic(schema, "downgrade", "074_memory_callbacks")
        assert _committed(schema, _constraint_literals) == {"superseded", "user_removed", "user_rejected"}

        proc = _alembic(schema, "upgrade", "075_not_user_words")
        assert "075: before" in proc.stdout + proc.stderr, "the counts must reach the deploy log"
        assert "not_user_words" in _committed(schema, _constraint_literals)
        _assert_cleaned(_committed(schema, lambda c: _state(c, k)), k)

        _alembic(schema, "downgrade", "074_memory_callbacks")
        state = _committed(schema, lambda c: _state(c, k))
        for key in RETIRED + UNTOUCHED_ACTIVE:
            assert state["mem"][k[key]] == (True, None), f"{key}: downgrade reactivates exactly 075's rows"
        assert state["mem"][k["legacy_superseded"]] == (False, "superseded")
        for key in MARKED:
            assert state["msg"][k[key]] == "daily_topic", f"{key}: message marks are not reset"
    finally:
        _alembic(schema, "upgrade", "head")

        async def cleanup(conn):
            for uid in k["users"]:
                await conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
            await conn.execute(text("DELETE FROM daily_questions WHERE id = :q"), {"q": k["qid"]})
        _committed(schema, cleanup)
