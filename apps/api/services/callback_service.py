"""MEM2-C-2 — the callback gate, the ledger, Ruling 9's lookup, and the rejection.

WHAT A CALLBACK IS. On a Pro turn that a deterministic gate clears, the persona is
shown ONE thing the person wrote in an earlier conversation, with the approved
directive that lets it say so once ("You said a few weeks ago that…"). Ruling #6
("never announce that you remember") stays the default and stays in the prompt;
the block sits directly after it as the one named exception. Rulings: Phase C
record and C-1 rulings, IMPLEMENTATION_BACKLOG_v29.md § MEM2-C.

BEHIND CALLBACKS_ENABLED, DEFAULT OFF. Off, stream_response never calls into this
module and its prompt is byte-identical to before C-2 (a test pins it). Two things
here are deliberately NOT gated by the flag: the rejection endpoint, so an offer
made before the flag went off stays rejectable; and the worker's Ruling 9 lookup,
so the reply to an offer made just before the flag went off is still marked.

THE GATE IS ITS OWN QUERY (D1). Recall's Lane B floor is 0.75; production recall
would have kept the candidate in 0 of 66 C-1 R/R2/T samples (best related row
0.538). So the gate selects from the user's eligible rows with its own 0.35 sanity
floor (STEP 0(a)), and an offered row recall did not return is APPENDED to the
memory block — the shape C-1 measured (C1-f: the candidate stays in the block).

RULE ORDER mirrors evals/callback_gate.py one-for-one (a–g), then the C-2 rules
(h–l). `why_ineligible` is pure and names the first rule a row fails, so the gate
log can say what excluded what. tests/services/test_callback_service.py runs every
C-1 sample through both gates and requires the same candidate.

ZERO LLM CALLS on the reply path (Ruling 6). Cost when the flag is on: on a Pro
NORMAL/none non-deep turn, one indexed ledger query, then one pool query over the
user's active chat rows that carry message ids. Nothing at all on any other turn.
"""
from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import MemoryCallback, MemoryEntry
from services.memory_service import DUPLICATE_SIM_THRESHOLD
from text_utils import dominant_language

logger = logging.getLogger(__name__)


# ── Rulings, as constants ────────────────────────────────────────────────────

SCORE_FLOOR = 0.35                      # STEP 0(a): candidate_row_cosine, flat across languages
MIN_ROW_AGE = timedelta(days=2)         # C1-c
USER_COOLDOWN = timedelta(days=7)       # C1-b: at most one offer per user per 7 days
CHAIN_COOLDOWN = timedelta(days=30)     # C1-b: same row-or-chain never within 30 days
# Ruling 5: active rows at >= this cosine to a rejected row become ineligible.
# The recall block's own duplicate threshold, not a new number.
NEAR_DUPLICATE_THRESHOLD = DUPLICATE_SIM_THRESHOLD
ELIGIBLE_PLANS = ("pro", "premium")     # C1-e: Sonnet only; the model choice at stream_response
ELIGIBLE_OUTCOME = "NORMAL"             # Ruling 6
ELIGIBLE_LEVEL = "none"                 # Ruling 6
# The pool is the user's nearest eligible-shaped rows. A row outside it could only
# win if more than this many nearer rows all failed a rule.
POOL_LIMIT = 50
CHAIN_DEPTH_CAP = 100                   # bounds a cycle, which no writer creates (CHAIN_DEPTH_SQL)


def enabled() -> bool:
    """Read at call time, as dedup_judge.enabled(), so a test can patch config."""
    return bool(config.CALLBACKS_ENABLED)


# ── The approved copy (prompts/, parity-pinned against evals/) ───────────────
#
# Plain text, filled with str.replace exactly as evals/callback_directive.py does.
# Never rendered as Jinja: the person's own words go into {original}, and they may
# carry braces. tests/services/test_callback_service.py pins both files
# byte-for-byte against the evals copy C-1 and STEP 0(b) measured.

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def _load(name: str) -> str:
    # Text mode, so a CRLF checkout (core.autocrlf) reads as LF. One trailing
    # newline is the file's, not the copy's.
    body = (_PROMPTS / name).read_text(encoding="utf-8")
    return body[:-1] if body.endswith("\n") else body


DIRECTIVE = _load("callback_directive.txt")
DIRECTIVE_EL = _load("callback_directive_el.txt")

# (inclusive upper bound in whole days, text). Approved 2026-10-05; the Greek set
# with the founder's register edit at 56–120. Parity-pinned against evals.
WHEN_BUCKETS: tuple[tuple[int | None, str], ...] = (
    (6, "a few days ago"),
    (13, "last week"),
    (55, "a few weeks ago"),
    (120, "a couple of months ago"),
    (None, "some months ago"),
)
WHEN_BUCKETS_EL: tuple[tuple[int | None, str], ...] = (
    (6, "πριν από λίγες μέρες"),
    (13, "την προηγούμενη εβδομάδα"),
    (55, "πριν από μερικές εβδομάδες"),
    (120, "πριν από ένα-δυο μήνες"),
    (None, "πριν από αρκετούς μήνες"),
)

# The line system_base.jinja2 opens HARD RULES with — the same anchor as
# evals/harness.py, so production puts the block where C-1 measured it.
HARD_RULES_ANCHOR = (
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "HARD RULES (non-negotiable)"
)


def _variant(lang: str):
    if lang == "en":
        return DIRECTIVE, WHEN_BUCKETS
    if lang == "el":
        return DIRECTIVE_EL, WHEN_BUCKETS_EL
    raise ValueError(f"no callback directive for language {lang!r}")


def conversation_language(user_text: str) -> str:
    """'el' for a Greek message, else 'en'. The current message only: nothing on
    the send path computes a conversation language, and a tie reads as English."""
    return "el" if dominant_language([user_text]) == "Greek" else "en"


def when_bucket(days: int, lang: str = "en") -> str:
    if days < 0:
        raise ValueError(f"a memory cannot be from the future: days={days}")
    for upper, phrase in _variant(lang)[1]:
        if upper is None or days <= upper:
            return phrase
    raise AssertionError("unreachable: the last bucket is open-ended")


def render_block(original: str, days: int, lang: str = "en") -> str:
    """`original` is the person's ORIGINAL message (Ruling 2), never the stored row."""
    directive, _ = _variant(lang)
    when = when_bucket(days, lang)
    return (
        directive
        .replace("{When}", when[0].upper() + when[1:])
        .replace("{when}", when)
        .replace("{original}", original.strip())
    )


def insert_block(system: str, block: str) -> str:
    """Directly before HARD RULES, i.e. after the memory block. Refuses rather than
    guesses if the anchor is missing or ambiguous (evals/harness._insert_callback)."""
    if system.count(HARD_RULES_ANCHOR) != 1:
        raise ValueError("HARD RULES anchor must appear exactly once in the system prompt")
    i = system.index(HARD_RULES_ANCHOR)
    return system[:i] + block + "\n\n\n" + system[i:]


# ── The gate (pure) ──────────────────────────────────────────────────────────

@dataclass
class CandidateRow:
    """One pool row, with everything the rules read. Built from CANDIDATE_POOL_SQL."""
    id: str
    entry_type: str
    content: str
    created_at: datetime
    conversation_id: str | None
    persona_id: str | None
    source_message_ids: list | None
    is_active: bool
    elicited_by_callback: bool
    callback_blocked_at: datetime | None
    flagged_conversation: bool
    offered_in_conversation: bool
    chain_offered_recently: bool
    original: str | None
    score: float


@dataclass
class CallbackOffer:
    """What the send path carries from Phase A to Phase C2. `entry_type` and
    `content` let it stand in the memory block like a recall row (D1)."""
    id: str
    entry_type: str
    content: str
    score: float
    days: int
    language: str
    block: str


def turn_ineligible(*, user_plan: str, gate_outcome: str, safety_level: str,
                    deep_mode: bool) -> str | None:
    """The first TURN rule that fails, or None. No query runs if one does."""
    if user_plan not in ELIGIBLE_PLANS:
        return "plan"                                   # C1-e
    if gate_outcome != ELIGIBLE_OUTCOME or safety_level != ELIGIBLE_LEVEL:
        return "turn_not_normal"                        # Ruling 6
    if deep_mode:
        return "deep_mode"                              # D5: unmeasured
    return None


def _days(created_at: datetime, now: datetime) -> int:
    return int((now - created_at).total_seconds() // 86400)


def why_ineligible(row: CandidateRow, *, responder_persona_id: str,
                   current_conversation_id: str, now: datetime,
                   floor: float = SCORE_FLOOR) -> str | None:
    """The FIRST rule a row fails, or None. a–g are evals/callback_gate.py's rules
    in its order; h–l are C-2's."""
    if not row.source_message_ids:
        return "no_source_message_ids"                  # a  Ruling 2
    if not row.is_active:
        return "inactive"                               # b  Ruling 2
    if row.conversation_id is None or str(row.conversation_id) == str(current_conversation_id):
        return "same_or_no_conversation"                # c  Ruling 2
    if str(row.persona_id) != str(responder_persona_id):
        return "other_persona"                          # d  Rulings 2, 3
    if row.flagged_conversation:
        return "flagged_conversation"                   # e  Ruling 6 (D2: any non-'none')
    if row.elicited_by_callback:
        return "elicited_by_callback"                   # f  Ruling 9
    if row.offered_in_conversation:
        return "already_offered_this_conversation"      # g  Ruling 4
    if now - row.created_at < MIN_ROW_AGE:
        return "too_new"                                # h  C1-c
    if row.chain_offered_recently:
        return "chain_cooldown"                         # i  C1-b
    if row.callback_blocked_at is not None:
        return "callback_blocked"                       # j  Ruling 5
    if not row.original:
        return "no_original"                            # k  Ruling 2: fidelity needs it
    if row.score < floor:
        return "below_floor"                            # l  STEP 0(a)
    return None


def choose(rows: Iterable[CandidateRow], *, responder_persona_id: str,
           current_conversation_id: str, now: datetime,
           floor: float = SCORE_FLOOR) -> tuple[CandidateRow | None, Counter]:
    """The single candidate, or None, and how many rows each rule excluded.

    Order: highest score, then newest, then id — the eval gate's tie-break, which
    is memory_service._ordered's — so identical inputs offer an identical row."""
    excluded: Counter = Counter()
    eligible = []
    for r in rows:
        reason = why_ineligible(r, responder_persona_id=responder_persona_id,
                                current_conversation_id=current_conversation_id,
                                now=now, floor=floor)
        if reason is None:
            eligible.append(r)
        else:
            excluded[reason] += 1
    if not eligible:
        return None, excluded
    xs = sorted(eligible, key=lambda r: str(r.id))
    xs.sort(key=lambda r: r.created_at, reverse=True)
    xs.sort(key=lambda r: r.score, reverse=True)
    return xs[0], excluded


# ── The gate (queries) ───────────────────────────────────────────────────────

USER_COOLDOWN_SQL = """
    SELECT EXISTS (
        SELECT 1 FROM memory_callbacks
        WHERE user_id = :user_id AND offered_at >= :since
    ) AS recent
"""

# The pool, with every field the rules read. Two rules are applied in SQL as well
# as in why_ineligible (is_active, source_message_ids present): they are the shape
# of a candidate, and narrowing on them keeps the pool to chat rows. The chain CTE
# walks each pool row BACK through supersedes_memory_id: candidates are active,
# and an active row is its chain's head, so its ancestors are the whole chain.
CANDIDATE_POOL_SQL = f"""
    WITH RECURSIVE pool AS (
        SELECT m.id, m.entry_type, m.content, m.created_at, m.conversation_id,
               m.persona_id, m.source_message_ids, m.is_active,
               m.elicited_by_callback, m.callback_blocked_at,
               1 - (m.embedding <=> CAST(:query_vec AS vector)) AS score
        FROM memory_entries m
        WHERE m.user_id = :user_id
          AND m.is_active = TRUE
          AND m.embedding IS NOT NULL
          AND m.source_message_ids IS NOT NULL
        ORDER BY m.embedding <=> CAST(:query_vec AS vector)
        LIMIT {POOL_LIMIT}
    ),
    chain(root, id, depth) AS (
        SELECT p.id, p.id, 0 FROM pool p
      UNION ALL
        SELECT c.root, e.supersedes_memory_id, c.depth + 1
        FROM chain c JOIN memory_entries e ON e.id = c.id
        WHERE e.supersedes_memory_id IS NOT NULL AND c.depth < {CHAIN_DEPTH_CAP}
    )
    SELECT p.id::text AS id, p.entry_type, p.content, p.created_at,
           p.conversation_id::text AS conversation_id,
           p.persona_id::text AS persona_id,
           p.source_message_ids::text[] AS source_message_ids,
           p.is_active, p.elicited_by_callback, p.callback_blocked_at, p.score,
           orig.content AS original,
           EXISTS (
               SELECT 1 FROM messages f
               WHERE f.conversation_id = p.conversation_id AND f.safety_level <> 'none'
           ) AS flagged_conversation,
           EXISTS (
               SELECT 1 FROM memory_callbacks o
               WHERE o.memory_id = p.id
                 AND o.conversation_id = CAST(:conversation_id AS uuid)
           ) AS offered_in_conversation,
           EXISTS (
               SELECT 1 FROM chain ch JOIN memory_callbacks cb ON cb.memory_id = ch.id
               WHERE ch.root = p.id AND cb.offered_at >= :chain_since
           ) AS chain_offered_recently
    FROM pool p
    LEFT JOIN messages orig
           ON orig.id = p.source_message_ids[1]
          AND orig.role = 'user'
          AND orig.user_id = :user_id
    ORDER BY p.score DESC
"""


def _log_gate(outcome: str, **fields) -> None:
    """One line per gate run. Ids and counts only — never content."""
    extra = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("callback_gate outcome=%s %s", outcome, extra)


async def select_callback(
    db: AsyncSession, *, user_id: str, conversation_id: str,
    responder_persona_id: str, user_plan: str, gate_outcome: str,
    safety_level: str, deep_mode: bool, user_text: str,
    query_vec: list[float] | None, now: datetime | None = None,
) -> CallbackOffer | None:
    """The one callback this turn may offer, or None. Raises on a query failure,
    after rolling back its own savepoint — the caller fails open.

    The queries run inside a SAVEPOINT so a failure cannot leave the turn's
    transaction aborted (the user message is saved on it afterwards), and so the
    rollback does not expire the conversation the caller still reads."""
    now = now or datetime.now(timezone.utc)
    reason = turn_ineligible(user_plan=user_plan, gate_outcome=gate_outcome,
                             safety_level=safety_level, deep_mode=deep_mode)
    if reason is not None:
        _log_gate("skipped", reason=reason)
        return None
    if query_vec is None:
        _log_gate("skipped", reason="no_query_vector")
        return None

    savepoint = await db.begin_nested()
    try:
        recent = (await db.execute(
            text(USER_COOLDOWN_SQL), {"user_id": user_id, "since": now - USER_COOLDOWN},
        )).scalar()
        if recent is True:
            await savepoint.commit()
            _log_gate("skipped", reason="user_cooldown")
            return None
        result = await db.execute(text(CANDIDATE_POOL_SQL), {
            "query_vec": str(query_vec),
            "user_id": user_id,
            "conversation_id": str(conversation_id),
            "chain_since": now - CHAIN_COOLDOWN,
        })
        rows = [CandidateRow(**dict(r._mapping)) for r in result.fetchall()]
        await savepoint.commit()
    except Exception:
        await savepoint.rollback()
        raise

    chosen, excluded = choose(rows, responder_persona_id=responder_persona_id,
                              current_conversation_id=conversation_id, now=now)
    counts = ",".join(f"{k}:{v}" for k, v in sorted(excluded.items())) or "-"
    if chosen is None:
        _log_gate("none", pool=len(rows), excluded=counts)
        return None

    lang = conversation_language(user_text)
    days = _days(chosen.created_at, now)
    _log_gate("offered", pool=len(rows), excluded=counts, memory_id=chosen.id,
              score=f"{chosen.score:.3f}", days=days, lang=lang)
    return CallbackOffer(
        id=chosen.id, entry_type=chosen.entry_type, content=chosen.content,
        score=float(chosen.score), days=days, language=lang,
        block=render_block(chosen.original, days, lang),
    )


def record_offer(db: AsyncSession, *, user_id: str, offer: CallbackOffer,
                 persona_id: str, conversation_id: str, message_id: str) -> None:
    """The ledger row, ON OFFER (Ruling 4). Added to the caller's session: Phase C2
    commits it with the assistant message that carried the offer, so a reply that
    was never saved leaves no row — the person saw nothing."""
    db.add(MemoryCallback(
        user_id=user_id, memory_id=offer.id, persona_id=persona_id,
        conversation_id=conversation_id, message_id=message_id, score=offer.score,
    ))


# ── Ruling 9: which turn of a callback is this pair? ─────────────────────────

# offer_turn  this pair's assistant reply carried an offer. Only the ASSISTANT text
#             is contaminated: the user message predates the callback (D7).
# reply_turn  the assistant message just before this pair's user message carried
#             an offer, so this user message is a reply to a callback.
TURN_ROLE_SQL = """
    SELECT
        EXISTS (
            SELECT 1 FROM memory_callbacks
            WHERE message_id = CAST(:assistant_id AS uuid)
        ) AS offer_turn,
        EXISTS (
            SELECT 1 FROM memory_callbacks cb
            WHERE cb.message_id = (
                SELECT p.id
                FROM messages u
                JOIN messages p ON p.conversation_id = u.conversation_id
                WHERE u.id = CAST(:user_message_id AS uuid)
                  AND p.role = 'assistant'
                  AND p.created_at < u.created_at
                ORDER BY p.created_at DESC
                LIMIT 1
            )
        ) AS reply_turn
"""


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


async def callback_turn_role(db: AsyncSession, source_message_ids) -> tuple[bool, bool]:
    """(offer_turn, reply_turn) for an extraction pair [user id, assistant id].

    NOT flag-gated: with no offers the ledger is empty and both are False. A job
    with no ids (queued before 070) cannot be placed and is neither.

    On a query failure the pair is treated as a REPLY turn — its rows lose their
    evidence credit rather than risk laundering one (ruling G: conservative)."""
    ids = list(source_message_ids or [])
    if len(ids) < 2 or not all(_is_uuid(x) for x in ids[:2]):
        return False, False
    savepoint = await db.begin_nested()
    try:
        row = (await db.execute(text(TURN_ROLE_SQL), {
            "user_message_id": str(ids[0]), "assistant_id": str(ids[1]),
        })).one()
        await savepoint.commit()
    except Exception as e:  # noqa: BLE001 — fail conservative, never raise into the task
        await savepoint.rollback()
        logger.error("callback_turn_role failed ids=%s: %s", ids[:2], e, exc_info=True)
        return False, True
    # `is True`, not truthiness: the driver returns a real bool, and a stand-in
    # session in a test must never mark a pair by accident (C-06).
    return row.offer_turn is True, row.reply_turn is True


# ── Ruling 5: "that's not right" ─────────────────────────────────────────────

# The CONNECTED supersession chain of one row: back through supersedes_memory_id
# and forward to every row that superseded it. Scoped to the user.
CHAIN_MEMBERS_SQL = f"""
    WITH RECURSIVE back(id, depth) AS (
        SELECT CAST(:memory_id AS uuid), 0
      UNION ALL
        SELECT e.supersedes_memory_id, b.depth + 1
        FROM back b JOIN memory_entries e ON e.id = b.id
        WHERE e.supersedes_memory_id IS NOT NULL AND b.depth < {CHAIN_DEPTH_CAP}
    ),
    fwd(id, depth) AS (
        SELECT CAST(:memory_id AS uuid), 0
      UNION ALL
        SELECT e.id, f.depth + 1
        FROM fwd f JOIN memory_entries e ON e.supersedes_memory_id = f.id
        WHERE f.depth < {CHAIN_DEPTH_CAP}
    )
    SELECT m.id::text AS id
    FROM memory_entries m
    WHERE m.user_id = :user_id
      AND m.id IN (SELECT id FROM back UNION SELECT id FROM fwd)
"""

# Active rows near the rejected one: blocked as callbacks, NOT retired (Ruling 5).
NEAR_DUPLICATE_BLOCK_SQL = """
    UPDATE memory_entries n
    SET callback_blocked_at = :now
    FROM memory_entries o
    WHERE o.id = CAST(:memory_id AS uuid)
      AND o.embedding IS NOT NULL
      AND n.user_id = :user_id
      AND n.is_active = TRUE
      AND n.embedding IS NOT NULL
      AND n.callback_blocked_at IS NULL
      AND n.id <> ALL(CAST(:chain_ids AS uuid[]))
      AND 1 - (n.embedding <=> o.embedding) >= :threshold
"""


@dataclass
class Rejection:
    callback_id: str
    memory_id: str
    already_rejected: bool
    retired: int
    blocked: int
    blocked_near_duplicates: int


async def reject_callback(db: AsyncSession, *, user_id: str, callback_id: str,
                          now: datetime | None = None) -> Rejection | None:
    """Ruling 5. None when the callback is not this user's (the router's 404).

    Runs in the CALLER's transaction and does not commit. Idempotent: a second
    call changes nothing and says so.

      1. the row and its connected chain: ACTIVE members retired as
         'user_rejected' — the reject_cited_memories predicate, so a row already
         retired for another reason keeps it;
      2. every chain member: callback_blocked_at, permanently. An insight 'yes'
         may later reactivate a user_rejected row (B2, D4); it never makes it a
         callback again;
      3. active rows at >= NEAR_DUPLICATE_THRESHOLD to the offered row: blocked
         as callbacks, left ACTIVE;
      4. the ledger row: reaction 'rejected'.
    """
    now = now or datetime.now(timezone.utc)
    cb = (await db.execute(
        select(MemoryCallback).where(MemoryCallback.id == callback_id,
                                     MemoryCallback.user_id == user_id)
    )).scalar_one_or_none()
    if cb is None:
        return None
    if cb.reaction == "rejected":
        return Rejection(callback_id=str(cb.id), memory_id=str(cb.memory_id),
                         already_rejected=True, retired=0, blocked=0,
                         blocked_near_duplicates=0)

    chain_ids = [r.id for r in (await db.execute(
        text(CHAIN_MEMBERS_SQL), {"memory_id": str(cb.memory_id), "user_id": user_id},
    )).fetchall()]
    retired = blocked = 0
    if chain_ids:
        retired = (await db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id.in_(chain_ids), MemoryEntry.user_id == user_id,
                   MemoryEntry.is_active == True)  # noqa: E712 — SQL
            .values(is_active=False, inactive_reason="user_rejected")
            .execution_options(synchronize_session=False)
        )).rowcount or 0
        blocked = (await db.execute(
            update(MemoryEntry)
            .where(MemoryEntry.id.in_(chain_ids), MemoryEntry.user_id == user_id,
                   MemoryEntry.callback_blocked_at.is_(None))
            .values(callback_blocked_at=now)
            .execution_options(synchronize_session=False)
        )).rowcount or 0
    near = (await db.execute(text(NEAR_DUPLICATE_BLOCK_SQL), {
        "now": now, "memory_id": str(cb.memory_id), "user_id": user_id,
        # uuid.UUID, as dedup_new_entries binds its uuid[] (own_ids).
        "chain_ids": [uuid.UUID(i) for i in chain_ids],
        "threshold": NEAR_DUPLICATE_THRESHOLD,
    })).rowcount or 0

    cb.reaction = "rejected"
    cb.reacted_at = now
    await db.flush()
    logger.info("callback_rejected callback=%s memory=%s retired=%d blocked=%d near=%d",
                cb.id, cb.memory_id, retired, blocked, near)
    return Rejection(callback_id=str(cb.id), memory_id=str(cb.memory_id),
                     already_rejected=False, retired=retired, blocked=blocked,
                     blocked_near_duplicates=near)
