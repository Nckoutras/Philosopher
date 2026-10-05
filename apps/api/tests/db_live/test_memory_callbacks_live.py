"""MEM2-C-2 against real Postgres: migration 074, the gate's SQL, Ruling 9's
lookup, and the rejection — executed, not read (the 2026-09-15 rule: a query is
not verified until a driver has executed it).

WHAT A MOCK CANNOT SHOW, and this file does:
  - the recursive chain CTEs walk the right way (back for the cooldown, both ways
    for the rejection) and terminate;
  - the flagged-conversation derivation, the original-message JOIN and the
    already-offered / cooldown EXISTS clauses select what why_ineligible assumes;
  - timestamptz and uuid[] parameters bind (TD-76, Γ-5);
  - the FKs do what 074 says on a user delete and a thread delete;
  - RLS is on with zero policies and no FORCE (C-05).

Vectors: every row is `_spread(a, axis)` — similarity exactly `a` to QUERY, on its
own axis so rows are not accidentally near-duplicates of EACH OTHER (the D3 note
in test_memory_recall_and_cascades.py).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from services import callback_service as cs
from services.memory_service import find_recurrences

DIM = 1536
QUERY = [1.0] + [0.0] * (DIM - 1)


def _spread(a: float, axis: int) -> list[float]:
    v = [0.0] * DIM
    v[0] = a
    v[axis] = (1 - a * a) ** 0.5
    return v


def _vec(v) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def _ago(days: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def _user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(text("INSERT INTO users (id, email) VALUES (:id, :e)"),
                     {"id": uid, "e": f"{uid}@example.test"})
    return uid


async def _personas(db) -> tuple[str, str]:
    rows = (await db.execute(text("SELECT id::text FROM personas ORDER BY slug LIMIT 2"))).all()
    assert len(rows) == 2, "the migration chain seeds personas"
    return rows[0][0], rows[1][0]


async def _conversation(db, uid, pid) -> str:
    cid = str(uuid.uuid4())
    await db.execute(text("INSERT INTO conversations (id, user_id, persona_id) VALUES (:c, :u, :p)"),
                     {"c": cid, "u": uid, "p": pid})
    return cid


async def _message(db, uid, cid, role, content, at, level="none") -> str:
    mid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO messages (id, conversation_id, user_id, role, content, safety_level, created_at) "
             "VALUES (:id, :c, :u, :r, :t, :l, :at)"),
        {"id": mid, "c": cid, "u": uid, "r": role, "t": content, "l": level, "at": at},
    )
    return mid


async def _memory(db, uid, pid, cid, vector, *, days=10.0, ids=None, elicited=False,
                  blocked=None, active=True, supersedes=None, reason=None,
                  content="User struggles with something.") -> str:
    mid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO memory_entries (id, user_id, persona_id, conversation_id, entry_type, "
             " content, embedding, confidence, provenance, source_surface, source_message_ids, "
             " created_at, elicited_by_callback, callback_blocked_at, is_active, "
             " supersedes_memory_id, inactive_reason) "
             f"VALUES (:id, :u, :p, :c, 'struggle', :content, '{_vec(vector)}'::vector, 0.9, "
             " 'system_inferred', 'chat', CAST(:ids AS uuid[]), :at, :el, :bl, :act, :sup, :rsn)"),
        {"id": mid, "u": uid, "p": pid, "c": cid, "content": content,
         "ids": [uuid.UUID(i) for i in ids] if ids else None, "at": _ago(days),
         "el": elicited, "bl": blocked, "act": active, "sup": supersedes, "rsn": reason},
    )
    return mid


async def _chat_row(db, uid, pid, vector, *, days=10.0, level="none", original=True, **kw):
    """A memory row the way chat extraction writes one: its own conversation, a
    user message and a reply, and source_message_ids pointing at both."""
    cid = await _conversation(db, uid, pid)
    u = await _message(db, uid, cid, "user", "my own words", _ago(days + 0.01), level=level)
    a = await _message(db, uid, cid, "assistant", "a reply", _ago(days))
    ids = [u, a] if original else [str(uuid.uuid4()), a]
    return await _memory(db, uid, pid, cid, vector, days=days, ids=ids, **kw), cid


async def _ledger(db, uid, memory_id, *, days, conversation_id=None, message_id=None) -> str:
    lid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO memory_callbacks (id, user_id, memory_id, conversation_id, message_id, "
             "score, offered_at) VALUES (:id, :u, :m, :c, :msg, 0.5, :at)"),
        {"id": lid, "u": uid, "m": memory_id, "c": conversation_id, "msg": message_id,
         "at": _ago(days)},
    )
    return lid


async def _select(db, uid, pid, cid, text_="I keep thinking about it."):
    return await cs.select_callback(
        db, user_id=uid, conversation_id=cid, responder_persona_id=pid,
        user_plan="pro", gate_outcome="NORMAL", safety_level="none", deep_mode=False,
        user_text=text_, query_vec=QUERY,
    )


# ── 1. Schema (074) ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rls_is_enabled_with_zero_policies_and_no_force(db):
    row = (await db.execute(text(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'memory_callbacks'"
    ))).one()
    assert (row[0], row[1]) == (True, False)
    policies = (await db.execute(text(
        "SELECT count(*) FROM pg_policies WHERE tablename = 'memory_callbacks'"))).scalar_one()
    assert policies == 0


@pytest.mark.asyncio
async def test_new_memory_columns_default_to_unmarked_and_unblocked(db):
    uid = await _user(db)
    mid = str(uuid.uuid4())
    await db.execute(text("INSERT INTO memory_entries (id, user_id, entry_type, content) "
                          "VALUES (:id, :u, 'value', 'x')"), {"id": mid, "u": uid})
    row = (await db.execute(text("SELECT elicited_by_callback, callback_blocked_at "
                                 "FROM memory_entries WHERE id = :id"), {"id": mid})).one()
    assert (row[0], row[1]) == (False, None)


@pytest.mark.asyncio
async def test_reaction_is_constrained(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    mid, _ = await _chat_row(db, uid, p, _spread(0.5, 2))
    lid = await _ledger(db, uid, mid, days=1)
    await db.execute(text("SAVEPOINT s"))
    with pytest.raises(Exception, match="ck_memory_callbacks_reaction"):
        await db.execute(text("UPDATE memory_callbacks SET reaction = 'liked' WHERE id = :id"),
                         {"id": lid})
    await db.execute(text("ROLLBACK TO SAVEPOINT s"))


@pytest.mark.asyncio
async def test_a_thread_delete_keeps_the_ledger_row_and_a_user_delete_takes_it(db):
    """SET NULL on conversation and message, so a thread delete does not reset
    the cooldowns; CASCADE on the user, so account deletion leaves nothing."""
    uid = await _user(db)
    p, _ = await _personas(db)
    mid, _ = await _chat_row(db, uid, p, _spread(0.5, 2))
    cid = await _conversation(db, uid, p)
    msg = await _message(db, uid, cid, "assistant", "the reply", _ago(1))
    lid = await _ledger(db, uid, mid, days=1, conversation_id=cid, message_id=msg)

    await db.execute(text("DELETE FROM conversations WHERE id = :c"), {"c": cid})
    row = (await db.execute(text("SELECT conversation_id, message_id FROM memory_callbacks "
                                 "WHERE id = :id"), {"id": lid})).one()
    assert (row[0], row[1]) == (None, None)

    await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
    left = (await db.execute(text("SELECT count(*) FROM memory_callbacks WHERE id = :id"),
                             {"id": lid})).scalar_one()
    assert left == 0


@pytest.mark.asyncio
async def test_record_offer_writes_through_the_orm(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    mid, _ = await _chat_row(db, uid, p, _spread(0.5, 2))
    cid = await _conversation(db, uid, p)
    msg = await _message(db, uid, cid, "assistant", "the reply", _ago(0))
    offer = cs.CallbackOffer(id=mid, entry_type="struggle", content="c", score=0.5,
                             days=10, language="en", block="B")
    cs.record_offer(db, user_id=uid, offer=offer, persona_id=p, conversation_id=cid,
                    message_id=msg)
    await db.flush()
    row = (await db.execute(text("SELECT memory_id::text, score, used, reaction, offered_at "
                                 "FROM memory_callbacks WHERE message_id = :m"), {"m": msg})).one()
    assert (row[0], row[1], row[2], row[3]) == (mid, 0.5, None, None)
    assert row[4] is not None


# ── 2. The gate, end to end ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_gate_offers_the_best_row_every_rule_leaves(db):
    """One decoy per rule, each scoring ABOVE the row that must win."""
    uid = await _user(db)
    p, other = await _personas(db)
    current = await _conversation(db, uid, p)

    await _chat_row(db, uid, other, _spread(0.84, 2))                    # d other persona
    await _chat_row(db, uid, p, _spread(0.83, 3), level="low")           # e flagged (D2: any non-'none')
    await _chat_row(db, uid, p, _spread(0.82, 4), days=1.5)              # h too new
    await _chat_row(db, uid, p, _spread(0.81, 5), elicited=True)         # f elicited
    await _chat_row(db, uid, p, _spread(0.80, 6), blocked=_ago(3))       # j blocked
    await _chat_row(db, uid, p, _spread(0.79, 7), original=False)        # k original gone
    await _memory(db, uid, p, current, _spread(0.78, 8),                 # c same conversation
                  ids=[str(uuid.uuid4()), str(uuid.uuid4())])
    await _memory(db, uid, p, None, _spread(0.77, 9),                    # a no message ids
                  ids=None)
    await _chat_row(db, uid, p, _spread(0.30, 10))                       # l below floor
    winner, _ = await _chat_row(db, uid, p, _spread(0.60, 11), days=9)
    await _chat_row(db, uid, p, _spread(0.50, 12))

    offer = await _select(db, uid, p, current)
    assert offer is not None and offer.id == winner
    assert offer.days == 9
    assert abs(offer.score - 0.60) < 1e-4
    assert '"my own words"' in offer.block          # the ORIGINAL message, not the row


@pytest.mark.asyncio
async def test_one_offer_per_user_per_seven_days(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    current = await _conversation(db, uid, p)
    row, _ = await _chat_row(db, uid, p, _spread(0.6, 2))
    old, _ = await _chat_row(db, uid, p, _spread(0.2, 3))

    lid = await _ledger(db, uid, old, days=6.9)
    assert await _select(db, uid, p, current) is None
    await db.execute(text("UPDATE memory_callbacks SET offered_at = :t WHERE id = :id"),
                     {"t": _ago(7.1), "id": lid})
    assert (await _select(db, uid, p, current)).id == row


@pytest.mark.asyncio
async def test_a_row_already_offered_in_this_conversation_is_not_offered_again(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    current = await _conversation(db, uid, p)
    first, _ = await _chat_row(db, uid, p, _spread(0.6, 2))
    second, _ = await _chat_row(db, uid, p, _spread(0.5, 3))
    # 40 days: outside both cooldowns, so only rule g can exclude it.
    await _ledger(db, uid, first, days=40, conversation_id=current)
    assert (await _select(db, uid, p, current)).id == second


@pytest.mark.asyncio
async def test_the_thirty_day_cooldown_follows_the_supersession_chain(db):
    """The head of a chain inherits the offer made on its ancestor."""
    uid = await _user(db)
    p, _ = await _personas(db)
    current = await _conversation(db, uid, p)
    ancestor, _ = await _chat_row(db, uid, p, _spread(0.2, 2), active=False, reason="superseded")
    head, _ = await _chat_row(db, uid, p, _spread(0.6, 3), supersedes=ancestor)
    other, _ = await _chat_row(db, uid, p, _spread(0.5, 4))

    lid = await _ledger(db, uid, ancestor, days=20)
    assert (await _select(db, uid, p, current)).id == other
    await db.execute(text("UPDATE memory_callbacks SET offered_at = :t WHERE id = :id"),
                     {"t": _ago(31), "id": lid})
    assert (await _select(db, uid, p, current)).id == head


@pytest.mark.asyncio
async def test_a_greek_message_gets_the_greek_block(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    current = await _conversation(db, uid, p)
    await _chat_row(db, uid, p, _spread(0.6, 2), days=70)
    offer = await _select(db, uid, p, current, text_="Σκέφτομαι συνέχεια τη δουλειά μου.")
    assert offer.language == "el"
    assert "Είπες πριν από ένα-δυο μήνες ότι" in offer.block


# ── 3. Ruling 9: which pair is which ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_offer_pair_and_the_reply_pair_are_told_apart(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    cid = await _conversation(db, uid, p)
    mem, _ = await _chat_row(db, uid, p, _spread(0.6, 2))
    u1 = await _message(db, uid, cid, "user", "u1", _ago(0.06))
    a1 = await _message(db, uid, cid, "assistant", "a1 carries the callback", _ago(0.05))
    u2 = await _message(db, uid, cid, "user", "u2 answers it", _ago(0.04))
    a2 = await _message(db, uid, cid, "assistant", "a2", _ago(0.03))
    u3 = await _message(db, uid, cid, "user", "u3", _ago(0.02))
    a3 = await _message(db, uid, cid, "assistant", "a3", _ago(0.01))
    await _ledger(db, uid, mem, days=0.05, conversation_id=cid, message_id=a1)

    assert await cs.callback_turn_role(db, [u1, a1]) == (True, False)
    assert await cs.callback_turn_role(db, [u2, a2]) == (False, True)
    assert await cs.callback_turn_role(db, [u3, a3]) == (False, False)


@pytest.mark.asyncio
async def test_an_elicited_row_is_never_a_recurrence_anchor(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    here = await _conversation(db, uid, p)
    v = _spread(0.6, 2)
    elicited, _ = await _chat_row(db, uid, p, v, elicited=True)
    entry = type("E", (), {"id": str(uuid.uuid4()), "content": "new", "embedding": v,
                           "conversation_id": here})()
    assert await find_recurrences(db, uid, entry, exclude_conversation=here) is None

    await db.execute(text("UPDATE memory_entries SET elicited_by_callback = FALSE WHERE id = :id"),
                     {"id": elicited})
    matches, _ = await find_recurrences(db, uid, entry, exclude_conversation=here)
    assert [str(m.id) for m in matches] == [elicited]


# ── 4. "That's not right" ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_rejection_retires_the_chain_and_blocks_near_duplicates(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    offered_vec = _spread(0.6, 2)
    # The offered row was later superseded: the FORWARD walk must reach the head.
    offered, _ = await _chat_row(db, uid, p, offered_vec, active=False, reason="superseded")
    head, _ = await _chat_row(db, uid, p, _spread(0.6, 3), supersedes=offered)
    near, _ = await _chat_row(db, uid, p, offered_vec)                 # cosine 1.0 to offered
    far, _ = await _chat_row(db, uid, p, _spread(0.5, 4))              # cosine 0.30 to offered
    lid = await _ledger(db, uid, offered, days=1)

    out = await cs.reject_callback(db, user_id=uid, callback_id=lid)
    assert (out.already_rejected, out.retired, out.blocked, out.blocked_near_duplicates) == (
        False, 1, 2, 1)

    async def state(mid):
        r = (await db.execute(text("SELECT is_active, inactive_reason, callback_blocked_at "
                                   "FROM memory_entries WHERE id = :id"), {"id": mid})).one()
        return r[0], r[1], r[2] is not None

    assert await state(offered) == (False, "superseded", True)   # keeps its own reason
    assert await state(head) == (False, "user_rejected", True)
    assert await state(near) == (True, None, True)               # blocked, NOT retired
    assert await state(far) == (True, None, False)
    reaction = (await db.execute(text("SELECT reaction, reacted_at FROM memory_callbacks "
                                      "WHERE id = :id"), {"id": lid})).one()
    assert reaction[0] == "rejected" and reaction[1] is not None

    again = await cs.reject_callback(db, user_id=uid, callback_id=lid)
    assert again.already_rejected is True


@pytest.mark.asyncio
async def test_another_users_callback_cannot_be_rejected(db):
    uid = await _user(db)
    intruder = await _user(db)
    p, _ = await _personas(db)
    mid, _ = await _chat_row(db, uid, p, _spread(0.6, 2))
    lid = await _ledger(db, uid, mid, days=1)
    assert await cs.reject_callback(db, user_id=intruder, callback_id=lid) is None
    active = (await db.execute(text("SELECT is_active FROM memory_entries WHERE id = :id"),
                               {"id": mid})).scalar_one()
    assert active is True


# ── 5. MEM2-C-3a: the use detector's query and the "That's not right" lookup ─

from services import callback_use as cu  # noqa: E402


async def _offered_turn(db, uid, p, reply, *, original="I count the minutes until I can leave.",
                        user_text="Today was the same again."):
    """An earlier conversation whose user message is the row's original, and a
    later one where the reply to `user_text` carried the offer."""
    old = await _conversation(db, uid, p)
    o_user = await _message(db, uid, old, "user", original, _ago(20.01))
    o_reply = await _message(db, uid, old, "assistant", "an old reply", _ago(20))
    mid = await _memory(db, uid, p, old, _spread(0.5, 2), days=20, ids=[o_user, o_reply])
    cid = await _conversation(db, uid, p)
    await _message(db, uid, cid, "user", user_text, _ago(0.002))
    msg = await _message(db, uid, cid, "assistant", reply, _ago(0.001))
    lid = await _ledger(db, uid, mid, days=0, conversation_id=cid, message_id=msg)
    return cid, msg, lid


async def _used(db, lid):
    return (await db.execute(text("SELECT used FROM memory_callbacks WHERE id = :id"),
                             {"id": lid})).scalar_one()


@pytest.mark.asyncio
async def test_mark_use_reads_the_original_and_marks_a_used_reply_once(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    _, msg, lid = await _offered_turn(
        db, uid, p, 'A few weeks ago you wrote «count the minutes until I can leave».')
    signals = await cu.mark_use(db, msg)
    assert signals.used and signals.quote and signals.when
    assert await _used(db, lid) is True
    assert await cu.mark_use(db, msg) is None          # idempotent: already marked
    assert await _used(db, lid) is True


@pytest.mark.asyncio
async def test_mark_use_does_not_credit_words_the_person_just_repeated(db):
    """The shared run is excluded when it is in THIS turn's user message — the
    subquery must find the user message the reply answered."""
    uid = await _user(db)
    p, _ = await _personas(db)
    repeated = "I count the minutes until I can leave."
    _, msg, lid = await _offered_turn(
        db, uid, p, "You count the minutes until I can leave, you say. Why?",
        user_text=repeated)
    assert (await cu.mark_use(db, msg)).used is False
    assert await _used(db, lid) is False


@pytest.mark.asyncio
async def test_mark_use_on_a_reply_without_an_offer_writes_nothing(db):
    uid = await _user(db)
    p, _ = await _personas(db)
    cid = await _conversation(db, uid, p)
    msg = await _message(db, uid, cid, "assistant", "a reply", _ago(0))
    assert await cu.mark_use(db, msg) is None


@pytest.mark.asyncio
async def test_the_messages_endpoint_carries_only_a_used_unrejected_callback(db):
    from types import SimpleNamespace
    from routers.conversations import get_messages

    uid = await _user(db)
    p, _ = await _personas(db)
    cid, msg, lid = await _offered_turn(db, uid, p, "Tell me more about today.")
    user = SimpleNamespace(id=uid)

    async def callback_ids():
        out = await get_messages(cid, db=db, user=user)
        return {m.id: m.callback_id for m in out}

    assert (await callback_ids())[msg] is None                    # used IS NULL
    await db.execute(text("UPDATE memory_callbacks SET used = FALSE WHERE id = :id"), {"id": lid})
    assert (await callback_ids())[msg] is None                    # unused: never shown
    await db.execute(text("UPDATE memory_callbacks SET used = TRUE WHERE id = :id"), {"id": lid})
    ids = await callback_ids()
    assert ids[msg] == lid
    assert [v for k, v in ids.items() if k != msg] == [None]      # the user message
    await cs.reject_callback(db, user_id=uid, callback_id=lid)
    assert (await callback_ids())[msg] is None                    # rejected: gone
