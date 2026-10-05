"""MEM2-C-1 — multi-session callback samples. 11 personas x 2 languages x 6 = 132.

THE PROBLEM THIS SOLVES. Every §8.2 sample is a first message with memories=[]
(harness.py docstring). A callback needs three things none of them has: memory
rows in the prompt, an earlier conversation for the row to come from, and the
person's ORIGINAL words from it, because Ruling 2 judges fidelity against those
and never against the stored row.

THE SIX SCENARIOS, per (persona, language). Each thread is authored once, in
callback_threads.json; a persona takes thread i % 6 and age bucket i % 5, so the
threads and the five {when} buckets are both spread across personas.

    R    related message, new conversation. The candidate is offered.
    R2   a SECOND related message in a LATER conversation, same candidate offered
         again. R and R2 are the repetition pair: used in both = repeated in
         consecutive sessions.
    T    tangential message, same candidate offered. What the model does with a
         weakly relevant offer is what the floor is for.
    B    R's message, plus bait in the memory block: the same theme said to ANOTHER
         persona (Ruling 3), said in a FLAGGED conversation (Ruling 6), and the
         person's onboarding and self-portrait taps (no source_message_ids, so
         Ruling 2). All relevant, all ineligible. The gate still offers only the
         candidate. Misuse = the reply calls back any of the bait.
    L1   ANTI-LAUNDERING, inside session 1: R's conversation continues with a
         FIXED callback turn and the person agreeing. The candidate is NOT offered
         again (the within-conversation ledger). Does the reply now state the
         memory as more certain or more general than the original words?
    L2   ANTI-LAUNDERING, session 2: R2's message, R2's offer, and one extra row in
         the block — what extraction would plausibly write from session 1's
         agreement, deliberately generalised ("User confirmed that … is simply who
         they are"). Ruling 9: that row is not independent evidence, so the gate
         never offers it. L2 vs R2 is the certainty-escalation comparison: the
         only difference between them is that row.

L1 IS IDENTICAL ACROSS ARMS, BY CONSTRUCTION. No candidate is offered in L1, so
the callback block is absent in both arms and the prompts match byte-for-byte. It
is generated in both anyway — the arms share one sample list, as the brief
requires — and the pair is reported as a replicate, not as an arm difference.

PRESENCE IS FORCED, AND RECORDED. Every row is placed in the memory block whether
or not production's recall would have surfaced it (Lane B's 0.75 floor). That is
arm F's forced-injection stance: it measures what the persona does WITH the
material. The run computes the real cosine of each row against the current
message and records which rows `compose_recall` would actually have kept, so the
report can say how often production would ever have reached this state.

THE ROWS ARE DUCK-TYPED for system_base.jinja2, which reads only `entry_type`
and `content`, and for evals.callback_gate, which reads the eligibility fields.
`onboarding_profile` and `self_portrait` content comes from the production
functions that write those rows (profile_to_statements, answer_statement), so
the bait is byte-identical to what a real user's block carries — English, by
design, even for a Greek speaker (the bank is English, 2026-09-11).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from personas import PERSONA_REGISTRY
from services.profile_text import profile_to_statements
from services.self_portrait import answer_statement

from . import callback_gate
from .callback_directive import when_bucket

THREADS_PATH = Path(__file__).resolve().parent / "callback_threads.json"

LANGUAGES = ("en", "el")
LANGUAGE_NAME = {"en": "English", "el": "Greek"}   # text_utils.dominant_language's names
SCENARIOS = ("R", "R2", "T", "B", "L1", "L2")

# One per persona, cycled, so each bucket is exercised on 2-3 personas per
# language. Each value sits inside a bucket rather than on a boundary; the
# boundaries are pinned by tests/test_callback_directive.py.
AGE_CYCLE = (3, 10, 30, 90, 200)
REFERENCE_NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

# Row kinds, for reporting. "candidate" is the only one the gate may offer.
KIND_CANDIDATE = "candidate"
KIND_OTHER_PERSONA = "other_persona"
KIND_FLAGGED = "flagged"
KIND_ONBOARDING = "onboarding_profile"
KIND_SELF_PORTRAIT = "self_portrait"
KIND_BACKGROUND = "background"
KIND_ELICITED = "elicited"
INELIGIBLE_KINDS = (KIND_OTHER_PERSONA, KIND_FLAGGED, KIND_ONBOARDING,
                    KIND_SELF_PORTRAIT, KIND_BACKGROUND, KIND_ELICITED)


@dataclass
class MemoryRow:
    id: str
    kind: str
    entry_type: str
    content: str
    provenance: str
    persona_slug: str | None
    conversation_id: str | None
    source_message_ids: tuple[str, ...] | None
    original: str | None            # the person's own words, when the row has any
    days_ago: int
    is_active: bool = True
    flagged_conversation: bool = False
    elicited_by_callback: bool = False
    score: float = 0.0              # cosine to the current message; filled by the run

    @property
    def created_at(self) -> datetime:
        """Fixed, not now(): memory_service._ordered and compose_recall read it, and
        a block that reordered with the wall clock would not be reproducible."""
        return REFERENCE_NOW - timedelta(days=self.days_ago)


@dataclass
class CallbackSample:
    scenario: str
    persona_slug: str
    language: str
    thread_id: str
    user_message: str
    conversation_id: str
    rows: list[MemoryRow]
    history: list[dict] = field(default_factory=list)
    offered_in_conversation: tuple[str, ...] = ()
    candidate_days: int = 0

    # ── the harness reads these, as it reads prompt_set.Sample ──
    @property
    def sample_id(self) -> str:
        return f"{self.scenario}::{self.persona_slug}::{self.language}"

    @property
    def problem_id(self) -> str:
        return f"{self.thread_id}::{self.scenario}"

    @property
    def mode(self) -> str:
        return "standard"

    @property
    def deep(self) -> bool:
        return False

    # ── convenience ──
    def candidate(self):
        """What the gate offers on this sample — computed, never stored."""
        return callback_gate.offer(
            self.rows, responder_slug=self.persona_slug,
            current_conversation_id=self.conversation_id,
            offered_in_conversation=self.offered_in_conversation,
        )

    def candidate_row(self) -> MemoryRow:
        """The thread's candidate row, offered or not (L1 does not offer it)."""
        return next(r for r in self.rows if r.kind == KIND_CANDIDATE)


def load_threads() -> dict:
    return json.loads(THREADS_PATH.read_text(encoding="utf-8"))


def _rid(*parts: str) -> str:
    return "mem:" + ":".join(parts)


def _cid(*parts: str) -> str:
    return "conv:" + ":".join(parts)


def _standing_rows(data: dict, slug: str, days: int) -> list[MemoryRow]:
    out = []
    for qid, idx in data["standing_self_portrait"]:
        out.append(MemoryRow(
            id=_rid(slug, "sp", qid), kind=KIND_SELF_PORTRAIT,
            entry_type="self_portrait", content=answer_statement(qid, idx),
            provenance="user_selected", persona_slug=None, conversation_id=None,
            source_message_ids=None, original=None, days_ago=days + 40,
        ))
    return out


def _background_rows(data: dict, slug: str, other: str, lang: str) -> list[MemoryRow]:
    return [
        MemoryRow(
            id=_rid(slug, lang, "bg", str(i)), kind=KIND_BACKGROUND,
            entry_type=r["entry_type"], content=r["content"],
            provenance="system_inferred", persona_slug=other,
            conversation_id=_cid(slug, lang, "bg", str(i)),
            source_message_ids=(f"msg:{slug}:{lang}:bg{i}:u", f"msg:{slug}:{lang}:bg{i}:a"),
            original=None, days_ago=60 + 10 * i,
        )
        for i, r in enumerate(data["background_rows"][lang])
    ]


def _bait_rows(thread: dict, slug: str, other: str, lang: str, days: int) -> list[MemoryRow]:
    t = thread[lang]
    rows = [
        MemoryRow(
            id=_rid(slug, lang, "other"), kind=KIND_OTHER_PERSONA,
            entry_type=thread["other_type"], content=t["other_row"],
            provenance="system_inferred", persona_slug=other,
            conversation_id=_cid(slug, lang, "other"),
            source_message_ids=(f"msg:{slug}:{lang}:other:u", f"msg:{slug}:{lang}:other:a"),
            original=t["other_original"], days_ago=days + 5,
        ),
        MemoryRow(
            id=_rid(slug, lang, "flagged"), kind=KIND_FLAGGED,
            entry_type="struggle", content=t["flagged_row"],
            provenance="system_inferred", persona_slug=slug,
            conversation_id=_cid(slug, lang, "flagged"),
            source_message_ids=(f"msg:{slug}:{lang}:flagged:u", f"msg:{slug}:{lang}:flagged:a"),
            original=t["flagged_original"], days_ago=days + 2,
            flagged_conversation=True,
        ),
    ]
    qid, idx = thread["bait_self_portrait"]
    rows.append(MemoryRow(
        id=_rid(slug, "sp-bait", qid), kind=KIND_SELF_PORTRAIT,
        entry_type="self_portrait", content=answer_statement(qid, idx),
        provenance="user_selected", persona_slug=None, conversation_id=None,
        source_message_ids=None, original=None, days_ago=days + 30,
    ))
    for j, stmt in enumerate(profile_to_statements(thread["bait_profile"])):
        rows.append(MemoryRow(
            id=_rid(slug, "onb", str(j)), kind=KIND_ONBOARDING,
            entry_type="onboarding_profile", content=stmt,
            provenance="user_selected", persona_slug=None, conversation_id=None,
            source_message_ids=None, original=None, days_ago=days + 60,
        ))
    return rows


def build_samples() -> list[CallbackSample]:
    """The 132, in a stable order: persona (registry order), language, scenario."""
    data = load_threads()
    threads = data["threads"]
    slugs = list(PERSONA_REGISTRY)
    out: list[CallbackSample] = []
    for i, slug in enumerate(slugs):
        thread = threads[i % len(threads)]
        other = slugs[(i + 1) % len(slugs)]
        days = AGE_CYCLE[i % len(AGE_CYCLE)]
        for lang in LANGUAGES:
            t = thread[lang]
            prior_conv = _cid(slug, lang, "prior")
            cand = MemoryRow(
                id=_rid(slug, lang, "cand"), kind=KIND_CANDIDATE,
                entry_type=thread["candidate_type"], content=t["row"],
                provenance="system_inferred", persona_slug=slug,
                conversation_id=prior_conv,
                source_message_ids=(f"msg:{slug}:{lang}:prior:u", f"msg:{slug}:{lang}:prior:a"),
                original=t["original"], days_ago=days,
            )
            base = _standing_rows(data, slug, days) + [cand] + _background_rows(
                data, slug, other, lang)

            conv_r = _cid(slug, lang, "R")
            when = when_bucket(days)
            when_text = when if lang == "en" else data["when_el"][when]
            callback_turn = t["callback_turn"].replace("{when}", when_text)
            elicited = MemoryRow(
                id=_rid(slug, lang, "elicited"), kind=KIND_ELICITED,
                entry_type=thread["candidate_type"], content=t["elicited_row"],
                provenance="system_inferred", persona_slug=slug,
                conversation_id=conv_r,
                source_message_ids=(f"msg:{slug}:{lang}:R:aff", f"msg:{slug}:{lang}:R:a2"),
                original=t["affirmation"], days_ago=max(0, days - 1),
                elicited_by_callback=True,
            )

            def mk(scenario, message, conv, rows, history=(), offered=()):
                return CallbackSample(
                    scenario=scenario, persona_slug=slug, language=lang,
                    thread_id=thread["id"], user_message=message,
                    conversation_id=conv, rows=[_copy(r) for r in rows],
                    history=list(history), offered_in_conversation=tuple(offered),
                    candidate_days=days,
                )

            out += [
                mk("R", t["current_r"], conv_r, base),
                mk("R2", t["current_r2"], _cid(slug, lang, "R2"), base),
                mk("T", t["current_t"], _cid(slug, lang, "T"), base),
                mk("B", t["current_r"], _cid(slug, lang, "B"),
                   base + _bait_rows(thread, slug, other, lang, days)),
                mk("L1", t["affirmation"], conv_r, base,
                   history=[{"role": "user", "content": t["current_r"]},
                            {"role": "assistant", "content": callback_turn}],
                   offered=(cand.id,)),
                mk("L2", t["current_r2"], _cid(slug, lang, "L2"), base + [elicited]),
            ]
    order = {s: k for k, s in enumerate(SCENARIOS)}
    return sorted(out, key=lambda s: (slugs.index(s.persona_slug),
                                      LANGUAGES.index(s.language), order[s.scenario]))


def _copy(r: MemoryRow) -> MemoryRow:
    """Each sample owns its rows: the run writes `score` per sample."""
    return MemoryRow(**r.__dict__)


def sample_set_hash() -> str:
    """Digest of every input a run consumed: messages, history, rows, offers.
    Recorded in the manifest; two runs over different sample sets are not
    comparable, and sample_ids alone would line up either way."""
    h = hashlib.sha256()
    for s in build_samples():
        cand = s.candidate()
        h.update(json.dumps({
            "id": s.sample_id, "msg": s.user_message, "hist": s.history,
            "conv": s.conversation_id, "offered": list(s.offered_in_conversation),
            "cand": cand.id if cand else None,
            "rows": [[r.id, r.kind, r.entry_type, r.content, r.provenance,
                      r.persona_slug, r.conversation_id,
                      list(r.source_message_ids or ()), r.original, r.days_ago,
                      r.flagged_conversation, r.elicited_by_callback] for r in s.rows],
        }, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]
