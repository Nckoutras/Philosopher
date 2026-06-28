"""Self-Portrait question-bank loader + statement helpers.

The "Self-Portrait" is a perpetual self-knowledge quiz. A canonical question bank
(apps/api/data/question_bank.json) is the SOURCE OF TRUTH; this module is content-
AGNOSTIC — it is built against the bank SCHEMA, never against specific questions:

    { "questions": [ { "id", "category", "question", "pills": [...],
                       "theme_tags": [...], "feeds": [...] }, ... ] }

(A bare top-level list of question objects is also accepted, so the real bank file
can drop in with or without the wrapper.)

Responsibilities:
  - Load + validate the bank at import (FAIL FAST on a bad theme_tag).
  - Resolve a (question_id, pill_index) answer into a short memory statement.
  - Provide the per-question dedup key used to seed/refresh a self_portrait
    memory_entry incrementally (see `question_key`).

This module does NOT touch the onboarding pills path (profile_text.py /
profile_to_statements / <what_we_know>). Quiz answers flow into the persona ONLY via
memory recall and the Sunday/season letters — never into the turn-1 prompt.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

# Fixed theme vocabulary. Every theme_tag on every question MUST be in this set;
# the loader fails fast at import otherwise, so a typo never reaches production.
THEME_VOCABULARY: frozenset[str] = frozenset({
    "grief", "fear", "envy", "meaning", "duty", "desire", "guilt", "parents",
    "power", "loneliness", "death", "aging", "friendship", "resentment",
    "identity", "discipline", "freedom", "doubt", "control", "dilemma",
})

_BANK_PATH = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"

# Cap on self_portrait statements injected into a single letter's material, so the
# week's/month's own messages stay dominant. Deterministic selection (sorted by
# question_id) keeps the chosen subset stable across runs for the same answer set.
MAX_LETTER_STATEMENTS = 12


def _load_bank(path: Path) -> dict[str, dict]:
    """Load + validate the question bank into an {id: question} map. Raises at import
    on a malformed bank or an out-of-vocabulary theme_tag (fail fast)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions = raw["questions"] if isinstance(raw, dict) else raw
    if not isinstance(questions, list):
        raise ValueError("question_bank: expected a list of questions (or {'questions': [...]})")

    bank: dict[str, dict] = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            raise ValueError(f"question_bank: a question is missing 'id': {q!r}")
        if qid in bank:
            raise ValueError(f"question_bank: duplicate question id {qid!r}")
        if not isinstance(q.get("pills"), list) or not q["pills"]:
            raise ValueError(f"question_bank: question {qid!r} has no pills")
        for tag in (q.get("theme_tags") or []):
            if tag not in THEME_VOCABULARY:
                raise ValueError(
                    f"question_bank: question {qid!r} has out-of-vocabulary theme_tag {tag!r}. "
                    f"Allowed: {sorted(THEME_VOCABULARY)}"
                )
        bank[qid] = q
    return bank


# Loaded once at import — bad bank ⇒ the app/worker fails to boot (intended).
_BANK: dict[str, dict] = _load_bank(_BANK_PATH)


def get_question(question_id: str) -> dict | None:
    """Return the question dict for an id, or None if it is not in the bank."""
    return _BANK.get(question_id)


def total_question_count() -> int:
    """Total number of questions in the bank (used to compute the Pro-locked count
    for the free tier without reaching into the private _BANK from outside)."""
    return len(_BANK)


# ── Free-tier gating ──────────────────────────────────────────────────────────
#
# The free tier sees a fixed, DETERMINISTIC slice of the bank; Pro sees everything.
# The slice is computed once at import (the bank is immutable at runtime) so every
# request and worker agrees on exactly which ids are free — the PATCH gate and the
# GET visibility filter must never disagree.

FREE_QUESTION_LIMIT = 15


def _compute_free_question_ids() -> frozenset[str]:
    """Deterministic interleave: group the bank by category (categories sorted;
    questions sorted by id within each), then round-robin across categories taking
    one each until FREE_QUESTION_LIMIT ids are collected. Round-robin (rather than
    first-N-by-id) keeps the free slice spread across life areas instead of front-
    loading whichever category sorts first. Stable for a given bank → frozen once."""
    by_category: dict[str, list[str]] = {}
    for qid, q in _BANK.items():
        by_category.setdefault(q.get("category", ""), []).append(qid)
    for ids in by_category.values():
        ids.sort()

    ordered_categories = sorted(by_category)
    chosen: list[str] = []
    round_idx = 0
    # Stop once we've collected the limit OR no category has anything left to give.
    while len(chosen) < FREE_QUESTION_LIMIT:
        progressed = False
        for cat in ordered_categories:
            ids = by_category[cat]
            if round_idx < len(ids):
                chosen.append(ids[round_idx])
                progressed = True
                if len(chosen) >= FREE_QUESTION_LIMIT:
                    break
        if not progressed:
            break
        round_idx += 1
    return frozenset(chosen)


_FREE_QUESTION_IDS: frozenset[str] = _compute_free_question_ids()


def free_question_ids() -> frozenset[str]:
    """The fixed set of question ids visible to the free tier (cached at import)."""
    return _FREE_QUESTION_IDS


def is_free_question(question_id: str) -> bool:
    """True iff this question is part of the free tier's visible slice."""
    return question_id in _FREE_QUESTION_IDS


def _public_question(q: dict) -> dict:
    """Project a bank question to its PUBLIC shape — {id, category, question, pills}.
    Strips the internal `theme_tags` and `feeds` (matching/seeding routing detail
    that must never leave the API)."""
    return {
        "id": q["id"],
        "category": q["category"],
        "question": q["question"],
        "pills": list(q.get("pills") or []),
    }


def visible_questions(is_pro: bool) -> list[dict]:
    """Questions the given tier may see, in a stable order (category sorted, then id):
    Pro → all questions; free → only the free slice. Returns the PUBLIC shape only."""
    out = [
        _public_question(q)
        for q in _BANK.values()
        if is_pro or is_free_question(q["id"])
    ]
    out.sort(key=lambda q: (q["category"], q["id"]))
    return out


def question_key(question_id: str) -> int:
    """Deterministic per-question key for self_portrait memory dedup.

    SEMANTIC OVERLOAD WARNING: this value is stored in MemoryEntry.source_turn,
    which everywhere else means "the chat message-turn index a memory was
    extracted from". For entry_type='self_portrait' rows ONLY, source_turn instead
    holds this stable hash of the question_id, so that re-answering question X can
    deactivate exactly that question's prior row and insert one fresh embedded row
    (incremental — one embed per tap, not a full re-seed). No read path interprets
    source_turn for self_portrait rows (self_model excludes them; recall/insight
    read only content), so the overload is safe. crc32 is masked to 31 bits to fit
    Postgres int4; collisions across a user's few-dozen answers are negligible.
    """
    return zlib.crc32(question_id.encode("utf-8")) & 0x7FFFFFFF


def answer_statement(question_id: str, pill_index: int) -> str | None:
    """Resolve one answer into a short, content-agnostic self-statement (third
    person, matching the onboarding-statement voice). Returns None if the question
    is unknown or the pill_index is out of range — so callers seed nothing rather
    than a malformed row. Templated from the question + chosen pill label only; NO
    per-pill authored fragments (keeps the module bank-agnostic)."""
    q = get_question(question_id)
    if q is None:
        return None
    pills = q.get("pills") or []
    if not (0 <= pill_index < len(pills)):
        return None
    return f"Asked “{q['question']}”, they answered: {pills[pill_index]}."


def answers_to_statements(answers: dict, *, limit: int = MAX_LETTER_STATEMENTS) -> list[str]:
    """Map a profile.answers dict ({question_id: pill_index}) to self-statements.

    Deterministic: questions are taken in sorted question_id order and capped to
    `limit` (default MAX_LETTER_STATEMENTS) so a growing bank can never let quiz
    answers crowd out a letter's actual week/month material. Unknown ids or
    out-of-range pills are silently skipped (the bank may change under stored
    answers). Used by the Sunday/season letter injection."""
    out: list[str] = []
    for qid in sorted(answers):
        if len(out) >= limit:
            break
        stmt = answer_statement(qid, answers[qid])
        if stmt:
            out.append(stmt)
    return out
