"""MEM2-C-3a — did the reply USE the callback it was offered? Fills memory_callbacks.used.

LOG-ONLY, OFF THE REPLY PATH. stream_response enqueues detect_callback_use_task after
Phase C2 has committed the reply and its ledger row; the worker runs this. Nothing
here gates a reply, an offer or a cooldown. One thing reads `used`: the messages
endpoint shows the "That's not right" control only under a reply that used its
callback (C-3a decision 1 = B), so a rejection can never retire a memory the
person was not shown.

DETERMINISTIC, NO LLM CALL (C-3a decision 2). A reply used its callback when any of
three signals fires, on text normalised by `normalize`:

  quote       a quoted span ("…", “…”, «…», „…“) of >= MIN_QUOTED_WORDS words that
              appears in the person's original message. «…» is owed to C-3 by the
              C-2 STEP 0 ruling: Greek replies quote with guillemets.
  when        the offer's {when} phrase within WHEN_WINDOW characters of a
              said/wrote verb ("You said a few weeks ago that…", "Είπες πριν από
              μερικές εβδομάδες ότι…"). The directive asks for exactly this framing.
  shared_run  a run of SHARED_RUN_WORDS words the reply shares with the original
              that is NOT in this turn's user message — an unframed paraphrase,
              minus what the person just said again themselves.

Measured against the C-1 judge's call-1 "called back item A" verdict on the stored
runs (tests/services/test_callback_use.py pins these counts): English Pro 36/37 used
replies caught, 0/18 unused flagged; Greek Pro under the Greek directive 20/21 caught,
2/34 flagged — at least one of those two is a callback the judge missed.

Normalisation: casefold, strip combining marks (Greek tonos), punctuation to space.
casefold() folds Greek final ς to σ, so the verb stems are normalised the same way
rather than written pre-folded; the first prototype missed every Greek verb for
exactly that reason.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.callback_service import when_bucket

logger = logging.getLogger(__name__)

MIN_QUOTED_WORDS = 3
WHEN_WINDOW = 60
SHARED_RUN_WORDS = 4

# Opening and closing marks. „…“ is the German/Greek low-high pair.
QUOTE_PAIRS = (('"', '"'), ("“", "”"), ("«", "»"), ("„", "“"))

# Stems, so every tense and person matches: είπ- (είπες), έγραψ- (έγραψες),
# έγραφ- (έγραφες), έλεγ- (έλεγες), ανέφερ- (ανέφερες), περιέγραψ- (περιέγραψες).
VERB_STEMS = (
    "said", "say", "wrote", "write", "written", "told", "mentioned", "described", "put it",
    "είπ", "έγραψ", "έγραφ", "έλεγ", "ανέφερ", "περιέγραψ",
)


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s.casefold())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


_VERBS = re.compile("(" + "|".join(re.escape(normalize(v)) for v in VERB_STEMS) + ")")


def quoted_spans(reply: str) -> list[str]:
    spans: list[str] = []
    for o, c in QUOTE_PAIRS:
        marks = re.escape(o + c)
        spans += re.findall(re.escape(o) + "([^" + marks + "]{3,400})" + re.escape(c), reply)
    return spans


def _runs(normalized: str, n: int = SHARED_RUN_WORDS) -> set[str]:
    w = normalized.split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


@dataclass(frozen=True)
class UseSignals:
    quote: bool
    when: bool
    shared_run: bool

    @property
    def used(self) -> bool:
        return self.quote or self.when or self.shared_run


def detect(reply: str, original: str, user_text: str, when_phrases: Iterable[str]) -> UseSignals:
    """Pure. `when_phrases` are the {when} texts the offer could have carried."""
    nr, no = normalize(reply), normalize(original)
    quote = False
    for span in quoted_spans(reply):
        ns = normalize(span)
        if len(ns.split()) >= MIN_QUOTED_WORDS and ns in no:
            quote = True
            break
    when = False
    for phrase in when_phrases:
        np = normalize(phrase)
        for m in re.finditer(re.escape(np), nr):
            if _VERBS.search(nr[max(0, m.start() - WHEN_WINDOW): m.end() + WHEN_WINDOW]):
                when = True
                break
        if when:
            break
    shared_run = bool((_runs(nr) & _runs(no)) - _runs(normalize(user_text or "")))
    return UseSignals(quote=quote, when=when, shared_run=shared_run)


def when_phrases_for(row_created_at: datetime, offered_at: datetime) -> list[str]:
    """Both languages' bucket for the row's age at offer: the reply's language is
    the conversation's, and a phrase in the other language is harmless to look for."""
    days = max(0, int((offered_at - row_created_at).total_seconds() // 86400))
    return [when_bucket(days, "en"), when_bucket(days, "el")]


# The offer on this assistant message, its reply, the person's ORIGINAL words (the
# same join as the gate's pool, Ruling 2), and the user message the reply answered.
OFFER_SQL = """
    SELECT cb.id::text AS id, cb.used, cb.offered_at,
           m.created_at AS row_created_at,
           a.content AS reply,
           orig.content AS original,
           (SELECT u.content FROM messages u
            WHERE u.conversation_id = a.conversation_id
              AND u.role = 'user'
              AND u.created_at < a.created_at
            ORDER BY u.created_at DESC
            LIMIT 1) AS user_text
    FROM memory_callbacks cb
    JOIN messages a ON a.id = cb.message_id
    JOIN memory_entries m ON m.id = cb.memory_id
    LEFT JOIN messages orig
           ON orig.id = m.source_message_ids[1]
          AND orig.role = 'user'
          AND orig.user_id = cb.user_id
    WHERE cb.message_id = CAST(:message_id AS uuid)
"""

MARK_SQL = "UPDATE memory_callbacks SET used = :used WHERE id = CAST(:id AS uuid) AND used IS NULL"


def _log(outcome: str, **fields) -> None:
    """One line per run. Ids and booleans only — never content."""
    extra = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("callback_use outcome=%s %s", outcome, extra)


async def mark_use(db: AsyncSession, message_id: str) -> UseSignals | None:
    """Fill `used` for the offer on `message_id`. Does not commit. Idempotent: a row
    already marked is left alone. None when there is nothing to mark."""
    row = (await db.execute(text(OFFER_SQL), {"message_id": str(message_id)})).one_or_none()
    if row is None:
        _log("no_offer", message_id=message_id)
        return None
    if row.used is not None:
        _log("already_marked", callback_id=row.id)
        return None
    if not row.original:
        # The gate never offers a row without its original (rule k), so this is a
        # deleted source message. `used` stays NULL: unknown, not "unused".
        _log("no_original", callback_id=row.id)
        return None
    signals = detect(row.reply, row.original, row.user_text or "",
                     when_phrases_for(row.row_created_at, row.offered_at))
    await db.execute(text(MARK_SQL), {"used": signals.used, "id": row.id})
    _log("used" if signals.used else "unused", callback_id=row.id,
         quote=signals.quote, when=signals.when, shared_run=signals.shared_run)
    return signals
