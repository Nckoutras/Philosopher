import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import MemoryEntry, Insight
from schemas import THEME_VALUES
from services.llm_client import llm_client
from services.embedding_client import embedding_client
from config import config

logger = logging.getLogger(__name__)

# ── Hybrid recall (Memory-v2 Ruling #5, design §2) ────────────────────────────
# Memory rows differ in one way that matters more than any other: SOME ARE THE
# PERSON'S OWN WORDS, THE REST ARE A MODEL'S INFERENCE ABOUT THEM. `stated` is
# text they typed, distilled; `self_portrait` is a pill they tapped. Neither can
# be wrong ABOUT them the way `belief`/`pattern`/`struggle` can — those are an
# LLM's reading, written at confidence >= 0.65, and a confident wrong one is the
# "λάθος μνήμη" Ruling #5 forbids. So the two kinds get two lanes, and the whole
# precision budget is spent on the lane where wrongness lives.
#
# Lane A (standing): exempt from the relevance floor — self-authored material
# does not have to earn its place by cosine score — but bounded, so it cannot
# flood the block.
#
# Lane A IS A CLOSED TWO-TYPE SET (Ruling #5; O-2 declined to widen it for
# `onboarding_profile`). Everything else is inferred BY CONSTRUCTION — the lane
# test is `entry_type NOT IN standing`, never an allow-list. That matters
# because `entry_type` is not validated on write: extraction stores the LLM's
# `type` field verbatim (`entry.get("type", "pattern")` below is a fallback for
# a MISSING key, not a whitelist), so an unrecognised or future type can exist
# in the table. With a catch-all it lands in Lane B, floor-gated and quota'd.
# With an allow-list it would be silently dropped from recall. `self_portrait_shift`
# is the live example and is Lane B by this rule (design §2b, ruled 2026-09-03).
STANDING_TYPES = ("stated", "self_portrait")

RECALL_TOTAL_BUDGET = 8      # rows in the prompt block, both lanes together
STANDING_CAP = 3             # Lane A, all standing types together
STANDING_PER_TYPE = 2        # Lane A, any one type
INFERRED_CAP = 5             # Lane B before Lane A's unfilled slots spill in
INFERRED_PER_TYPE = 2        # Lane B, any one type — stops one prolific type

# Lane B's relevance floor, replacing the 0.70 literal that had stood unmeasured
# since the initial commit. Ruling #5 buys precision with recall in as many words
# ("never a wrong memory in, even if one goes missing"), so the floor rises.
# 0.75 is a SHIP-AND-TUNE value (O-1): no measurement of either number against
# real embeddings exists, and a synthetic-vector test can pin that the floor is
# ENFORCED but not where it belongs. Named so it moves without touching the query.
INFERRED_SCORE_FLOOR = 0.75

# Candidates, not the answer. ROW_NUMBER ranks WITHIN each entry_type so one
# prolific type cannot crowd the others out before Python ever sees the rows,
# and the floor is applied to the inferred branch only. `compose_recall` then
# applies the caps and the spillover.
#
# The lane test is `entry_type = ANY(:standing_types)` / `<> ALL(...)` — the
# catch-all form, for the reason given on STANDING_TYPES.
#
# Module-level so tests can EXPLAIN the REAL query rather than a copy that can
# drift from it (T-9).
RECALL_SQL = """
    WITH scored AS (
        SELECT id, entry_type, content, confidence, created_at,
               1 - (embedding <=> CAST(:query_vec AS vector)) AS score,
               ROW_NUMBER() OVER (
                   PARTITION BY entry_type
                   ORDER BY embedding <=> CAST(:query_vec AS vector),
                            created_at DESC, id
               ) AS rank_in_type
        FROM memory_entries
        WHERE user_id = :user_id
          AND is_active = TRUE
          AND embedding IS NOT NULL
    )
    SELECT id, entry_type, content, confidence, created_at, score
    FROM scored
    WHERE (entry_type = ANY(CAST(:standing_types AS text[]))
           AND rank_in_type <= :standing_per_type)
       OR (entry_type <> ALL(CAST(:standing_types AS text[]))
           AND rank_in_type <= :inferred_per_type
           AND score > :floor)
"""


def _ordered(rows: list) -> list:
    """Score DESC, then created_at DESC, then id ASC.

    Three stable sorts rather than one composite key, because the key would have
    to negate a datetime to sort it descending alongside an ascending id. Python's
    sort is stable, so sorting by the LEAST significant field first and the most
    significant last produces the lexicographic order without that trick.

    The tie-break is not decoration: identical inputs must render an identical
    block. A prompt that reorders between two identical turns is untestable, and
    it moves text that sits after the cache breakpoint for no reason.
    """
    xs = sorted(rows, key=lambda r: str(r.id))
    xs.sort(key=lambda r: r.created_at, reverse=True)
    xs.sort(key=lambda r: r.score, reverse=True)
    return xs


def _take_per_type(rows: list, per_type: int) -> list:
    """First `per_type` of each entry_type, preserving the given order."""
    seen: Counter = Counter()
    kept = []
    for r in rows:
        if seen[r.entry_type] >= per_type:
            continue
        seen[r.entry_type] += 1
        kept.append(r)
    return kept


def compose_recall(
    rows: list,
    *,
    standing_types: tuple = STANDING_TYPES,
    standing_cap: int = STANDING_CAP,
    standing_per_type: int = STANDING_PER_TYPE,
    inferred_cap: int = INFERRED_CAP,
    inferred_per_type: int = INFERRED_PER_TYPE,
    floor: float = INFERRED_SCORE_FLOOR,
    total_budget: int = RECALL_TOTAL_BUDGET,
) -> list:
    """Candidate rows in → the block's rows out. PURE: no session, no query.

    This is where Ruling #5 actually lives, and it is a plain function on purpose
    — the SQL is what needs a live Postgres to verify, while the caps, the quota,
    the spillover and the ordering are arithmetic and belong in unit tests.

    Lane A (standing) is taken first: per-type capped, then capped in total, with
    NO floor. Lane B (everything else) must clear `floor`, is per-type capped, and
    receives Lane A's unfilled slots — one way only. A floor-less lane has to stay
    bounded, so nothing ever spills from B back into A.

    Rows are re-filtered and re-ranked here rather than trusted from the query:
    the SQL's window is an optimisation that fetches fewer rows, not the authority
    on the answer. That keeps this function meaningful against any input a test
    hands it.
    """
    standing_set = set(standing_types)

    standing_rows = [r for r in rows if r.entry_type in standing_set]
    inferred_rows = [
        r for r in rows
        if r.entry_type not in standing_set and r.score > floor
    ]

    # Lane A is clamped by the BUDGET as well as by its own cap. Without the
    # min, a caller asking for fewer rows than the person has standing rows would
    # get more than it asked for: Lane B's room would clamp to 0 while Lane A had
    # already overshot. total_budget is the total, including Lane A.
    standing = _take_per_type(_ordered(standing_rows), standing_per_type)[
        : min(standing_cap, total_budget)
    ]

    # Spillover, expressed both ways and clamped by the smaller. The two agree
    # whenever STANDING_CAP + INFERRED_CAP == RECALL_TOTAL_BUDGET; the min is what
    # keeps the total honest if one constant is later tuned without the others.
    inferred_room = min(
        inferred_cap + (standing_cap - len(standing)),
        total_budget - len(standing),
    )
    inferred = _take_per_type(_ordered(inferred_rows), inferred_per_type)[:max(inferred_room, 0)]

    # Standing first: it is the stable frame the persona reads the topical matches
    # against. The reverse buries that frame under whatever this turn matched.
    return standing + inferred


# ── Recurrence detection (Insight Slice 1) ─────────────────────────────────────
# A factual recurrence detector: when a memory the user just raised has surfaced
# before in OTHER conversations, write a durable Insight naming the recurring
# thread. Constants are named here so they are trivial to tune.
RECURRENCE_SIM_THRESHOLD = 0.75   # cosine score a prior entry must clear to count
RECURRENCE_MIN_PRIOR = 1          # how many prior-conversation matches → recurrence
RECURRENCE_THROTTLE_HOURS = 6     # min spacing between 'pattern' insights per user

RECURRENCE_PROMPT = """You name a recurring thread in someone's reflections — factually, not therapeutically.

You are given something the person raised just now, and one or more things they said earlier in OTHER conversations that closely echo it.

Write a single observation that names WHAT keeps returning. Rules:
- At most 2 sentences. Plain, grounded, observational.
- Name the recurring theme concretely. Do not interpret motive or character.
- No therapy-speak. No diagnosis. Never say "you always" or "you never".
- Address the person as "you". No preamble, no quotation marks.
- Never quote the person and never paraphrase their sentences one-to-one.
- Distill the essence. You may reuse the person's own key concept-words as anchors, but reframe — name the pattern one level above the instance.
- If find-and-replace on their words could produce your line, rewrite it.
- Make no claim the material does not support.

Example: "The question of whether to leave your job has come up again — it surfaced weeks ago in a different conversation, and here it is once more." """

# ── Shift detection (Insight Slice 2) ──────────────────────────────────────────
# One classify+phrase call: given a just-raised memory and the prior memories that
# echo it, decide whether the person's STANCE has changed ('shift') or merely
# recurred ('pattern'), and phrase the observation in one shot. STRONGLY biased to
# 'pattern' — LLMs over-detect narrative change; 'shift' is reserved for genuine
# directional movement of the position. Shifts are hedged to a certainty ladder.
SHIFT_CLASSIFY_PROMPT = """You compare something a person raised just now against closely-related things they said earlier, in OTHER conversations, and decide whether their STANCE on the theme has actually changed.

Return JSON only — no markdown, no preamble — exactly: {"insight_type": "pattern" | "shift", "content": "..."}

Classification (default to "pattern"):
- "pattern" is the DEFAULT. Choose it whenever the theme simply recurs and the person's position is essentially unchanged. Different wording, new examples, fresh emphasis, or a more detailed retelling of the SAME stance is still "pattern".
- "shift" ONLY when there is genuine DIRECTIONAL change in the stance itself — the position moved or reversed (e.g. from wanting to leave → wanting to stay; from certainty → doubt; from resisting → accepting). Rephrasing or paraphrase variation is NOT a shift. When in doubt, it is a pattern.

Write "content" as a single observation, at most 2 sentences, addressed to the person as "you". Plain, grounded, observational. No therapy-speak, no diagnosis, never "you always"/"you never", no preamble, no quotation marks.

For "pattern": name the recurring theme concretely — a familiar thread returning.

For "shift": HEDGE the claim to how clearly the change shows in the material. Match the language to your confidence, and never state a tentative shift as a certain fact:
- low confidence    → "Something may be beginning to shift — ..."
- medium confidence → "It seems as though ..."
- high confidence   → "It's quite likely that ..." or "What you once called X, you now seem to name Y."

No-verbatim rule (both types): never quote the person and never paraphrase their sentences one-to-one. Reuse their key concept-words as anchors, but reframe — name it one level above the instance. If find-and-replace on their words could produce your line, rewrite it. Make no claim the material does not support.

Example pattern: {"insight_type": "pattern", "content": "The question of whether to leave your job has come up again — it surfaced weeks ago in a different conversation, and here it is once more."}
Example shift: {"insight_type": "shift", "content": "It seems as though the certainty you once had about leaving has loosened; where you spoke of escape, you now weigh what staying might be worth."}"""

# ── Single-text → memory distillation (reusable) ───────────────────────────────
# Turn a person's OWN words into one clean, third-person memory statement. Generic
# by design (no council/ritual wording) so later #4 surfaces (Counterview, Future
# Self, Mirror) reuse it unchanged. Cheap: a word-count pre-filter skips trivial
# text BEFORE any LLM call, and the one LLM call rides the default memory model
# (Haiku via config.ANTHROPIC_MEMORY_MODEL). Returns None on trivial/empty/NONE.
MIN_DISTILL_WORDS = 6

DISTILL_TO_MEMORY_PROMPT = """You convert a person's own words into ONE clean memory statement about them.

You are given text the person wrote themselves — their own framing of a matter they wanted considered. Rewrite it as a single, third-person memory statement in the shape "User ..." — factual, grounded, one sentence, no interpretation beyond what they stated. Write it in the SAME language as the input.

Return ONLY the statement, no preamble, no quotation marks. If the text holds nothing meaningful to remember, return exactly: NONE"""


async def distill_to_memory(text: str) -> str | None:
    """Distil a person's own text into ONE third-person memory statement ("User …").

    Pre-filter: text with fewer than MIN_DISTILL_WORDS words returns None WITHOUT any
    LLM call (trivial edits cost nothing past this check). Otherwise one Haiku
    completion (default memory model) produces the statement; an empty reply or the
    sentinel NONE → None. Generic (no council-specific wording) so #4b/c/d reuse it.
    """
    text = (text or "").strip()
    if len(text.split()) < MIN_DISTILL_WORDS:
        return None
    raw = await llm_client.complete(
        system=DISTILL_TO_MEMORY_PROMPT,
        user=text,
        max_tokens=160,
    )
    statement = (raw or "").strip()
    # Strip wrapping quotes if the model added them despite instructions.
    if len(statement) >= 2 and statement[0] in "\"'" and statement[-1] in "\"'":
        statement = statement[1:-1].strip()
    if not statement or statement.upper() == "NONE":
        return None
    return statement


MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for a philosophical companion app.

Given a conversation exchange (user message + assistant response), extract memorable observations about the user.
Focus on: beliefs, values, ongoing struggles, recurring patterns, personal milestones, stated goals.

Return a JSON array only. No explanation. No markdown.
Each item: {"type": "belief|value|struggle|pattern|milestone|dilemma|aspiration", "content": "...", "confidence": 0.0-1.0, "theme": "<one theme slug or omit>"}

Rules:
- Only extract what is genuinely stated or clearly implied. Do not infer beyond the text.
- Content should be 1-2 concise sentences about the USER, not the conversation.
- Confidence > 0.8 = stated explicitly. 0.6-0.8 = clearly implied. Below 0.6 = skip it.
- Return [] if nothing meaningful is extractable.
- Max 3 entries per exchange.
- "dilemma": a live decision the user is ACTIVELY weighing between two courses of action, stated in THIS exchange. Not general uncertainty, not a decision already made in the past, not the assistant's framing. Content = one sentence naming the two sides in the user's own voice, first person (it is placed in the user's own input field verbatim).
- "belief": write content as the belief ITSELF — a single declarative sentence in the user's own voice, not "You believe that…". e.g. "If I don't handle everything myself, it won't be done right." This text is used verbatim as a Counterview anchor.
- "aspiration": a genuine reach toward who the user wants to BECOME, or a direction/change they are resolving to make — stated with real weight in THIS exchange. NOT a passing wish, a casual preference, or an offhand goal. Only when they articulate the person they want to be or a change they mean to commit to. Content = one sentence in the user's own voice, first person, naming the direction.
- "theme" (OPTIONAL): the single best-fitting life-theme for this item, one of: separation, anxiety, fear, grief, acceptance, work, relationships, purpose, dilemma, controversy, doubt, freedom. Omit the field entirely if none clearly fits. Only meaningful for "dilemma" and "belief"; may be omitted for other types.

Example output:
[
  {"type": "struggle", "content": "User is experiencing conflict between career ambitions and desire for stability.", "confidence": 0.85},
  {"type": "value", "content": "User places high importance on honesty in relationships.", "confidence": 0.75},
  {"type": "dilemma", "content": "I'm weighing whether to leave a secure job for one that feels meaningful but far less certain.", "confidence": 0.9, "theme": "work"},
  {"type": "belief", "content": "If I don't handle everything myself, it won't be done right.", "confidence": 0.85, "theme": "work"}
]"""


class MemoryService:

    async def extract_and_store(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        persona_id: str,
        user_text: str,
        assistant_text: str,
        source_turn: int = 0,
        safety_ok: bool = False,
    ) -> list[MemoryEntry]:
        """Extract memory signals from a message pair and persist them.

        `safety_ok` (input+output both level 'none') gates ONLY the dilemma/belief
        signal-insight write below; memory-row persistence is unchanged by it.
        """
        try:
            raw = await llm_client.complete(
                system=MEMORY_EXTRACTION_PROMPT,
                user=f"USER: {user_text}\n\nASSISTANT: {assistant_text}",
                max_tokens=512,
            )
            # Strip markdown code fences if LLM wrapped the JSON
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text[:-3].rstrip()
            entries_data = json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []

        saved = []
        for entry in entries_data:
            # Dilemma/aspiration items are insight-only signals (see below) — never memory rows.
            if entry.get("type") in ("dilemma", "aspiration"):
                continue
            if entry.get("confidence", 0) < 0.65:
                continue

            content = entry.get("content", "").strip()
            if not content:
                continue

            embedding = await embedding_client.embed(content)

            memory = MemoryEntry(
                user_id=user_id,
                persona_id=persona_id,
                conversation_id=conversation_id,
                entry_type=entry.get("type", "pattern"),
                content=content,
                embedding=embedding,
                confidence=entry.get("confidence", 0.7),
                source_turn=source_turn,
            )
            db.add(memory)
            saved.append(memory)

        await db.flush()

        # ── Dilemma/belief/aspiration → Insight (Slice 2) ─────────────────────
        # Explicitly-stated, chip-worthy signals promoted to an Insight — ONLY when
        # the exchange was safety-clean (safety_ok, level 'none' both ways) and the
        # SAME throttle/dedup gate detect_recurrence uses allows it. At most one write
        # per call; priority order dilemma > belief > aspiration when several qualify.
        # Per-type confidence bar (_SIGNAL_MIN_CONF): dilemma/belief 0.8, aspiration
        # 0.7. content is used verbatim downstream (Council prefill for a dilemma,
        # Counterview anchor for a belief, Future Self door for an aspiration);
        # source_count=None (not a cross-conversation recurrence).
        # Self-contained — a failure here must never break memory persistence.
        if safety_ok:
            try:
                _SIGNAL_MIN_CONF = {"dilemma": 0.8, "belief": 0.8, "aspiration": 0.7}
                signal = None
                for want in ("dilemma", "belief", "aspiration"):
                    thr = _SIGNAL_MIN_CONF[want]
                    signal = next(
                        (
                            e for e in entries_data
                            if e.get("type") == want
                            and e.get("confidence", 0) >= thr
                            and (e.get("content") or "").strip()
                        ),
                        None,
                    )
                    if signal is not None:
                        break
                if signal is not None:
                    blocked = await self._insight_gate_blocked(db, user_id, conversation_id)
                    if blocked is None:
                        raw_theme = (signal.get("theme") or "").strip().lower()
                        theme = raw_theme if raw_theme in THEME_VALUES else None
                        db.add(Insight(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            persona_id=persona_id,
                            content=(signal.get("content") or "").strip(),
                            insight_type=signal.get("type"),
                            source_count=None,
                            theme=theme,
                        ))
                        await db.flush()
                        logger.info(
                            "Signal insight written type=%s user=%s conv=%s",
                            signal.get("type"), user_id, conversation_id,
                        )
                    else:
                        logger.info("Signal insight skipped (%s) conv=%s", blocked, conversation_id)
            except Exception as e:
                logger.error("Signal insight write failed conv=%s: %s", conversation_id, e, exc_info=True)

        logger.info(f"Stored {len(saved)} memory entries for user={user_id}")
        return saved

    async def recall(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = RECALL_TOTAL_BUDGET,
        query_embedding: list[float] | None = None,
    ) -> list[MemoryEntry]:
        """Retrieve semantically relevant memories for a query — HYBRID (Ruling #5).

        Two lanes, described on STANDING_TYPES above: standing rows enter without
        clearing the floor, inferred rows must clear INFERRED_SCORE_FLOOR and are
        quota'd per type. The SQL fetches CANDIDATES; `compose_recall` decides
        which of them survive, so caps, spillover and ordering are a pure function
        over rows and unit-testable without a database.

        top_k is the TOTAL budget across both lanes, defaulting to
        RECALL_TOTAL_BUDGET. The four callers no longer pass it.

        query_embedding: an optional precomputed embedding of ``query``. When the
        caller already embedded the same text (e.g. the chat turn reuses one vector
        for both recall and retrieval), pass it here to skip a redundant embed. When
        None, embed internally exactly as before.
        """
        query_vec = query_embedding if query_embedding is not None else await embedding_client.embed(query)

        result = await db.execute(
            text(RECALL_SQL),
            {
                "query_vec": str(query_vec),
                "user_id": user_id,
                "standing_types": list(STANDING_TYPES),
                "standing_per_type": STANDING_PER_TYPE,
                "inferred_per_type": INFERRED_PER_TYPE,
                "floor": INFERRED_SCORE_FLOOR,
            }
        )
        return compose_recall(result.fetchall(), total_budget=top_k)

    async def standing_memories(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        limit: int,
    ) -> list[MemoryEntry]:
        """The standing lane WITHOUT a query — most recent `stated` rows first.

        WHY THIS EXISTS SEPARATELY FROM recall(). A chat turn has a query: the
        user's message. A LETTER DOES NOT. It covers a week or a month, and there
        is no single text to embed. Lane A is the half of hybrid recall that never
        needed one — its members are chosen by TYPE and bounded by COUNT, and
        cosine only orders them. Drop the ordering and the lane still stands, which
        is what makes it the right thing to give a query-free surface.

        `stated` ONLY, deliberately. The other standing type, `self_portrait`, is
        already rendered into both letters as the <self_portrait> block, built from
        profile.answers via answers_to_statements — including it here would put the
        same quiz answers in one prompt twice, in two different sentence shapes.
        `stated` is the person's own words from Council, mirrors, counterview and
        future-self notes, and it is the material a letter has no other route to.

        A NARROWING OF DESIGN §3a, RECORDED AS SUCH. The design specified one
        dual-mode accessor — `standing_memories(..., query_embedding=None)` falling
        back to recency, cosine-ranked when given a vector. PR-2 shipped only the
        query-driven half (inside recall's windowed SQL), and PR-3 may not reopen
        recall, so the query-driven mode has no implementation to delegate to and
        no caller that wants it. Building a second cosine path here to satisfy a
        signature would be machinery for nobody. Ruled 2026-09-03; goes to the next
        docs rotation as a correction to §3a rather than an edit to the design doc.

        Ordinary ORM query: no embedding, no vector maths, no LLM, no cost.
        """
        result = await db.execute(
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.entry_type == "stated",
                MemoryEntry.is_active == True,  # noqa: E712 — SQL, not Python truth
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _insight_gate_blocked(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str | None,
    ) -> str | None:
        """Shared throttle/dedup gate for ALL insight writes (recurrence AND the
        dilemma/belief signal write) so the guards can never diverge. Returns a block
        reason ("throttle" | "per_conversation") when a write must be skipped, or None
        when it may proceed.

        - "throttle": any non-dismissed insight for this user within the last
          RECURRENCE_THROTTLE_HOURS → skip. Spacing + idempotency vs ARQ's
          at-least-once delivery; max one insight of any type per window.
        - "per_conversation": for a real source conversation, any existing insight in
          it → skip (max one per conversation). A NULL-conversation source (e.g. a
          voluntary counterview belief) is a no-op here (== NULL never matches), so it
          skips this check and leans on the throttle.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=RECURRENCE_THROTTLE_HOURS)
        recent = await db.execute(
            select(Insight.id).where(
                Insight.user_id == user_id,
                Insight.is_dismissed == False,
                Insight.created_at >= cutoff,
            ).limit(1)
        )
        if recent.scalar_one_or_none() is not None:
            return "throttle"

        if conversation_id is not None:
            per_conv = await db.execute(
                select(Insight.id).where(
                    Insight.user_id == user_id,
                    Insight.conversation_id == conversation_id,
                ).limit(1)
            )
            if per_conv.scalar_one_or_none() is not None:
                return "per_conversation"

        return None

    async def detect_recurrence(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        persona_id: str,
        new_entries: list[MemoryEntry],
    ) -> None:
        """Factual recurrence detector. If a memory the user just raised echoes
        memories from OTHER conversations, write a durable 'pattern' Insight
        naming the recurring thread.

        Safe by construction: wrapped in try/except, NEVER raises into the caller
        (the memory task). Reuses the entries' already-computed embeddings — the
        session uses expire_on_commit=False, so they remain readable post-commit.
        """
        try:
            if not new_entries:
                return

            # ── DEDUP / THROTTLE (shared gate) ────────────────────────────────
            # The SAME gate the dilemma/belief signal write uses (see
            # _insight_gate_blocked), so a pattern, a shift, and a signal insight can
            # never diverge on spacing or the one-per-conversation rule.
            blocked = await self._insight_gate_blocked(db, user_id, conversation_id)
            if blocked == "throttle":
                logger.info("Recurrence skipped (throttle) user=%s", user_id)
                return
            if blocked == "per_conversation":
                logger.info("Recurrence skipped (one per conversation) conv=%s", conversation_id)
                return

            # ── DETECTION ─────────────────────────────────────────────────────
            # For each freshly-stored entry, cosine-search prior memories from
            # OTHER conversations (mirrors recall(): same str(vector) + CAST AS
            # vector serialization so the param format cannot silently mismatch).
            recurring_entry = None
            prior_matches: list = []
            for entry in new_entries:
                if entry.embedding is None:
                    continue
                # Build the pgvector literal explicitly. NOT str(embedding): if the
                # value is ever a numpy array, str() truncates with "..." and uses
                # space separators → an invalid literal that would be swallowed by
                # the try/except and silently yield zero matches forever.
                vec_literal = "[" + ",".join(repr(float(x)) for x in entry.embedding) + "]"
                # Exclude the source's own context so an entry can never match itself.
                # Chat path: exclude the whole source conversation. NULL-conversation
                # source (voluntary belief): exclude only this entry by its own id —
                # `conversation_id != NULL` would exclude every row (SQL 3-valued logic).
                if conversation_id is not None:
                    exclude_clause = "AND conversation_id != :conversation_id"
                    exclude_param = {"conversation_id": conversation_id}
                else:
                    exclude_clause = "AND id != :self_id"
                    exclude_param = {"self_id": entry.id}
                result = await db.execute(
                    text(f"""
                        SELECT content, conversation_id,
                               1 - (embedding <=> CAST(:query_vec AS vector)) AS score
                        FROM memory_entries
                        WHERE user_id = :user_id
                          AND is_active = TRUE
                          AND embedding IS NOT NULL
                          {exclude_clause}
                        ORDER BY embedding <=> CAST(:query_vec AS vector)
                        LIMIT 20
                    """),
                    {
                        "query_vec": vec_literal,
                        "user_id": user_id,
                        **exclude_param,
                    },
                )
                rows = result.fetchall()
                matches = [r for r in rows if r.score >= RECURRENCE_SIM_THRESHOLD]
                if len(matches) >= RECURRENCE_MIN_PRIOR:
                    recurring_entry = entry
                    prior_matches = matches
                    break

            if recurring_entry is None:
                logger.info("Recurrence: none above threshold for conv=%s", conversation_id)
                return

            # Distinct conversations the theme was noticed across: the distinct
            # prior conversations that cleared the similarity bar, plus this one.
            source_count = len({m.conversation_id for m in prior_matches}) + 1

            # ── CLASSIFY + PHRASE ─────────────────────────────────────────────
            # One call decides pattern vs shift and produces the phrasing. On any
            # ambiguity / empty / parse failure we fall back to the slice-1 plain
            # recurrence phrasing as a 'pattern' — never lose the insight, never
            # surface an unvalidated 'shift'.
            prior_text = "\n".join(f"- {m.content}" for m in prior_matches[:5])
            user_prompt = (
                f"Raised now:\n- {recurring_entry.content}\n\n"
                f"Echoed earlier (other conversations):\n{prior_text}"
            )

            raw = await llm_client.complete(
                system=SHIFT_CLASSIFY_PROMPT,
                user=user_prompt,
                max_tokens=160,
            )

            insight_type = "pattern"
            content = None
            try:
                parsed = (raw or "").strip()
                if parsed.startswith("```"):
                    parsed = parsed.split("\n", 1)[1] if "\n" in parsed else ""
                if parsed.endswith("```"):
                    parsed = parsed[:-3].rstrip()
                data = json.loads(parsed)
                candidate_type = data.get("insight_type")
                candidate_content = (data.get("content") or "").strip()
                if candidate_type in ("pattern", "shift") and candidate_content:
                    insight_type = candidate_type
                    content = candidate_content
            except Exception:
                content = None  # fall through to plain-phrasing fallback

            if content is None:
                # Safe fallback: slice-1 plain recurrence phrasing, always 'pattern'.
                fallback = await llm_client.complete(
                    system=RECURRENCE_PROMPT,
                    user=user_prompt,
                    max_tokens=80,
                )
                insight_type = "pattern"
                content = (fallback or "").strip()

            if len(content) >= 2 and content[0] in "\"'" and content[-1] in "\"'":
                content = content[1:-1].strip()
            if not content:
                logger.info("Recurrence: empty phrasing for conv=%s", conversation_id)
                return

            db.add(Insight(
                user_id=user_id,
                conversation_id=conversation_id,
                persona_id=persona_id,
                content=content,
                insight_type=insight_type,
                source_count=source_count,
            ))
            await db.commit()
            logger.info(
                "Insight written type=%s user=%s conv=%s (%s prior matches)",
                insight_type, user_id, conversation_id, len(prior_matches),
            )
        except Exception as e:
            logger.error("detect_recurrence failed for conv=%s: %s", conversation_id, e, exc_info=True)

memory_service = MemoryService()
