import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import MemoryEntry
from services.llm_client import llm_client
from services.embedding_client import embedding_client
from config import config

logger = logging.getLogger(__name__)

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
            entries_data = json.loads(raw.strip())
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
                       1 - (embedding <=> :query_vec::vector) AS score
                FROM memory_entries
                WHERE user_id = :user_id
                  AND is_active = TRUE
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :query_vec::vector
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
