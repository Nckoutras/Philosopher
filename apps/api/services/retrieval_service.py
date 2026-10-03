import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from personas._base import PersonaConfig
from models import SourceChunk
from services.embedding_client import embedding_client

logger = logging.getLogger(__name__)


# No runtime caller since RET-001 (ruling 1β, 2026-10-03). Production retrieval
# returned zero passages in 858 turns against the 0.72 threshold, so the reply
# path no longer calls retrieve(); the corpus, its embeddings and this module
# stay as an OFFLINE resource (scripts/ingest_corpus.py, evals/retrieval_arm).
# Do not wire retrieve() back into a request path without a new ruling.

# Was PersonaConfig.retrieval_top_k, removed with the runtime call: ten personas
# carried 4, Socrates 3, and nothing but the deleted call read it.
DEFAULT_TOP_K = 4


class RetrievalService:

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        persona: PersonaConfig,
        top_k: int | None = None,
        score_threshold: float = 0.72,
        query_embedding: list[float] | None = None,
    ) -> list[SourceChunk]:
        # query_embedding: an optional precomputed embedding of ``query``, so an
        # offline caller that already embedded the text can skip a second embed.
        # When None, embed internally.
        top_k = top_k or DEFAULT_TOP_K
        query_vec = query_embedding if query_embedding is not None else await embedding_client.embed(query)

        result = await db.execute(
            text("""
                SELECT sc.id, sc.source_title, sc.source_type, sc.content,
                       sc.page_ref, sc.persona_id,
                       1 - (sc.embedding <=> CAST(:query_vec AS vector)) AS score
                FROM source_chunks sc
                JOIN personas p ON p.id = sc.persona_id
                WHERE p.slug = :persona_slug
                  AND sc.embedding IS NOT NULL
                ORDER BY sc.embedding <=> CAST(:query_vec AS vector)
                LIMIT :fetch_k
            """),
            {
                "query_vec": str(query_vec),
                "persona_slug": persona.slug,
                "fetch_k": top_k * 3,
            }
        )
        rows = result.fetchall()
        filtered = [r for r in rows if r.score >= score_threshold]
        return filtered[:top_k]

    async def ingest_chunk(
        self,
        db: AsyncSession,
        persona_id: str,
        source_title: str,
        source_type: str,
        content: str,
        page_ref: str | None = None,
    ) -> SourceChunk:
        """Used by admin ingestion scripts to add new source material."""
        embedding = await embedding_client.embed(content)
        chunk = SourceChunk(
            persona_id=persona_id,
            source_title=source_title,
            source_type=source_type,
            content=content,
            embedding=embedding,
            page_ref=page_ref,
        )
        db.add(chunk)
        await db.flush()
        return chunk


retrieval_service = RetrievalService()
