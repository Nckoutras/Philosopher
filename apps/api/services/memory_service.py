import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import MemoryEntry, Insight
from schemas import THEME_VALUES
from services.llm_client import llm_client
from services.embedding_client import embedding_client
from config import config

logger = logging.getLogger(__name__)

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

MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for a philosophical companion app.

Given a conversation exchange (user message + assistant response), extract memorable observations about the user.
Focus on: beliefs, values, ongoing struggles, recurring patterns, personal milestones, stated goals.

Return a JSON array only. No explanation. No markdown.
Each item: {"type": "belief|value|struggle|pattern|milestone|dilemma", "content": "...", "confidence": 0.0-1.0, "theme": "<one theme slug or omit>"}

Rules:
- Only extract what is genuinely stated or clearly implied. Do not infer beyond the text.
- Content should be 1-2 concise sentences about the USER, not the conversation.
- Confidence > 0.8 = stated explicitly. 0.6-0.8 = clearly implied. Below 0.6 = skip it.
- Return [] if nothing meaningful is extractable.
- Max 3 entries per exchange.
- "dilemma": a live decision the user is ACTIVELY weighing between two courses of action, stated in THIS exchange. Not general uncertainty, not a decision already made in the past, not the assistant's framing. Content = one sentence naming the two sides in the user's own voice, first person (it is placed in the user's own input field verbatim).
- "belief": write content as the belief ITSELF — a single declarative sentence in the user's own voice, not "You believe that…". e.g. "If I don't handle everything myself, it won't be done right." This text is used verbatim as a Counterview anchor.
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
            # Dilemma items are insight-only signals (see below) — never memory rows.
            if entry.get("type") == "dilemma":
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

        # ── Dilemma/belief → Insight (Slice 2) ────────────────────────────────
        # Explicitly-stated, chip-worthy signals promoted to an Insight — ONLY when
        # the exchange was safety-clean (safety_ok, level 'none' both ways) and the
        # SAME throttle/dedup gate detect_recurrence uses allows it. At most one write
        # per call; a dilemma is preferred over a belief when both qualify. content is
        # used verbatim downstream (Council prefill for a dilemma, Counterview anchor
        # for a belief); source_count=None (not a cross-conversation recurrence).
        # Self-contained — a failure here must never break memory persistence.
        if safety_ok:
            try:
                signal = None
                for want in ("dilemma", "belief"):
                    signal = next(
                        (
                            e for e in entries_data
                            if e.get("type") == want
                            and e.get("confidence", 0) >= 0.8
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
        top_k: int = 6,
    ) -> list[MemoryEntry]:
        """Retrieve semantically relevant memories for a query."""
        query_vec = await embedding_client.embed(query)

        # pgvector cosine similarity search
        result = await db.execute(
            text("""
                SELECT id, entry_type, content, confidence, created_at,
                       1 - (embedding <=> CAST(:query_vec AS vector)) AS score
                FROM memory_entries
                WHERE user_id = :user_id
                  AND is_active = TRUE
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :top_k
            """),
            {
                "query_vec": str(query_vec),
                "user_id": user_id,
                "top_k": top_k,
            }
        )
        rows = result.fetchall()
        # Filter by score threshold
        return [r for r in rows if r.score > 0.70]

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

    async def get_user_memories(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        result = await db.execute(
            select(MemoryEntry)
            .where(MemoryEntry.user_id == user_id, MemoryEntry.is_active == True)
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def deactivate(self, db: AsyncSession, memory_id: str, user_id: str) -> bool:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.id == memory_id,
                MemoryEntry.user_id == user_id,
            )
        )
        memory = result.scalar_one_or_none()
        if not memory:
            return False
        memory.is_active = False
        return True


memory_service = MemoryService()
