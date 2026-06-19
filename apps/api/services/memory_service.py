import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import MemoryEntry, Insight
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

MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for a philosophical companion app.

Given a conversation exchange (user message + assistant response), extract memorable observations about the user.
Focus on: beliefs, values, ongoing struggles, recurring patterns, personal milestones, stated goals.

Return a JSON array only. No explanation. No markdown.
Each item: {"type": "belief|value|struggle|pattern|milestone", "content": "...", "confidence": 0.0-1.0}

Rules:
- Only extract what is genuinely stated or clearly implied. Do not infer beyond the text.
- Content should be 1-2 concise sentences about the USER, not the conversation.
- Confidence > 0.8 = stated explicitly. 0.6-0.8 = clearly implied. Below 0.6 = skip it.
- Return [] if nothing meaningful is extractable.
- Max 3 entries per exchange.

Example output:
[
  {"type": "struggle", "content": "User is experiencing conflict between career ambitions and desire for stability.", "confidence": 0.85},
  {"type": "value", "content": "User places high importance on honesty in relationships.", "confidence": 0.75}
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
    ) -> list[MemoryEntry]:
        """Extract memory signals from a message pair and persist them."""
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

            # ── DEDUP / THROTTLE ──────────────────────────────────────────────
            # Skip if a non-dismissed 'pattern' insight was minted for this user
            # within the throttle window (spacing + idempotency vs at-least-once
            # delivery), and never mint more than one 'pattern' insight per
            # conversation.
            cutoff = datetime.now(timezone.utc) - timedelta(hours=RECURRENCE_THROTTLE_HOURS)
            recent = await db.execute(
                select(Insight.id).where(
                    Insight.user_id == user_id,
                    Insight.insight_type == "pattern",
                    Insight.is_dismissed == False,
                    Insight.created_at >= cutoff,
                ).limit(1)
            )
            if recent.scalar_one_or_none() is not None:
                logger.info("Recurrence skipped (throttle) user=%s", user_id)
                return

            per_conv = await db.execute(
                select(Insight.id).where(
                    Insight.user_id == user_id,
                    Insight.conversation_id == conversation_id,
                    Insight.insight_type == "pattern",
                ).limit(1)
            )
            if per_conv.scalar_one_or_none() is not None:
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
                result = await db.execute(
                    text("""
                        SELECT content,
                               1 - (embedding <=> CAST(:query_vec AS vector)) AS score
                        FROM memory_entries
                        WHERE user_id = :user_id
                          AND is_active = TRUE
                          AND embedding IS NOT NULL
                          AND conversation_id != :conversation_id
                        ORDER BY embedding <=> CAST(:query_vec AS vector)
                        LIMIT 20
                    """),
                    {
                        "query_vec": vec_literal,
                        "user_id": user_id,
                        "conversation_id": conversation_id,
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

            # ── PHRASING ──────────────────────────────────────────────────────
            prior_text = "\n".join(f"- {m.content}" for m in prior_matches[:5])
            raw = await llm_client.complete(
                system=RECURRENCE_PROMPT,
                user=(
                    f"Raised now:\n- {recurring_entry.content}\n\n"
                    f"Echoed earlier (other conversations):\n{prior_text}"
                ),
                max_tokens=80,
            )
            content = (raw or "").strip()
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
                insight_type="pattern",
            ))
            await db.commit()
            logger.info(
                "Recurrence insight written user=%s conv=%s (%s prior matches)",
                user_id, conversation_id, len(prior_matches),
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
