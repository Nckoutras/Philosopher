"""
Ingest the corpus defined in corpus_sources.py into the source_chunks table.

Usage (from apps/api/):
    python -m scripts.ingest_corpus [--dry-run] [--persona SLUG]

Flags:
    --dry-run     Fetch and chunk without calling OpenAI or writing to DB.
                  Useful for verifying Gutenberg URLs before incurring cost.
    --persona     Only ingest sources for one persona slug (e.g. --persona socrates).

Idempotency:
    Uses ON CONFLICT (persona_id, source_title, chunk_index) WHERE chunk_index IS NOT NULL
    DO UPDATE to upsert. Re-running on unchanged content is a no-op except for the
    embedding recalculation on updated chunks.

Cost estimate:
    text-embedding-3-small costs $0.02 per 1M tokens.
    Full corpus is <500K tokens; expected cost <$0.01 per full run.
"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import text

from db.session import AsyncSessionLocal
from scripts.chunking import chunk_text
from scripts.corpus_sources import CORPUS_SOURCES

logger = logging.getLogger(__name__)

_GUTENBERG_START = "*** START OF THE PROJECT GUTENBERG"
_GUTENBERG_END = "*** END OF THE PROJECT GUTENBERG"


# ── Text acquisition ──────────────────────────────────────────────────────────

def _strip_boilerplate(raw: str) -> str:
    start_idx = raw.find(_GUTENBERG_START)
    if start_idx != -1:
        newline = raw.find("\n", start_idx)
        if newline != -1:
            raw = raw[newline + 1:]

    end_idx = raw.find(_GUTENBERG_END)
    if end_idx != -1:
        raw = raw[:end_idx]

    return raw.strip()


async def _fetch_text(url: str, timeout: int = 30) -> str | None:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(3):
            try:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content
                if content.startswith(b"\xef\xbb\xbf"):   # UTF-8 BOM
                    content = content[3:]
                return content.decode("utf-8", errors="replace")
            except httpx.HTTPStatusError as exc:
                logger.error("HTTP %s for %s", exc.response.status_code, url)
                return None
            except Exception as exc:
                if attempt == 2:
                    logger.error("Failed to fetch %s after 3 attempts: %s", url, exc)
                    return None
                await asyncio.sleep(2 ** attempt)
    return None


# ── Per-source ingestion ──────────────────────────────────────────────────────

async def _ingest_source(
    db,
    persona_id: str,
    source: dict,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Returns (inserted, updated, dry_run_skipped)."""
    from services.embedding_client import embedding_client

    url = source["gutenberg_url"]
    title = source["title"]
    source_type = source.get("source_type", "primary_text")

    logger.info("  Fetching: %s", title)
    raw = await _fetch_text(url)
    if raw is None:
        return 0, 0, 0

    clean = _strip_boilerplate(raw)
    chunks = chunk_text(clean)

    if not chunks:
        logger.warning("  No chunks produced for %s", title)
        return 0, 0, 0

    logger.info("  %d chunks from %s", len(chunks), title)

    if dry_run:
        logger.info("  [dry-run] would embed and upsert %d chunks", len(chunks))
        return 0, 0, len(chunks)

    # Embed in batches to respect rate limits
    batch_size = 100
    embeddings: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch_embeddings = await embedding_client.embed_batch(chunks[i : i + batch_size])
        embeddings.extend(batch_embeddings)

    inserted = updated = 0
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        row = await db.execute(
            text("""
                INSERT INTO source_chunks
                    (id, persona_id, source_title, source_type, content,
                     embedding, chunk_index, created_at)
                VALUES
                    (gen_random_uuid(), :persona_id, :source_title, :source_type, :content,
                     CAST(:embedding AS vector), :chunk_index, now())
                ON CONFLICT (persona_id, source_title, chunk_index)
                WHERE chunk_index IS NOT NULL
                DO UPDATE SET
                    content   = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
                RETURNING (xmax = 0) AS was_inserted
            """),
            {
                "persona_id": persona_id,
                "source_title": title,
                "source_type": source_type,
                "content": chunk,
                "embedding": str(embedding),
                "chunk_index": idx,
            },
        )
        was_inserted = row.scalar()
        if was_inserted:
            inserted += 1
        else:
            updated += 1

    await db.flush()
    return inserted, updated, 0


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(dry_run: bool = False, persona_filter: str | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sources_to_run = {
        slug: sources
        for slug, sources in CORPUS_SOURCES.items()
        if persona_filter is None or slug == persona_filter
    }

    if not sources_to_run:
        logger.error("No sources found for persona filter: %s", persona_filter)
        sys.exit(1)

    mode_label = "[DRY RUN] " if dry_run else ""
    logger.info("%sIngesting corpus for %d persona(s)...", mode_label, len(sources_to_run))

    total_inserted = total_updated = total_skipped = total_errors = 0

    async with AsyncSessionLocal() as db:
        for slug, sources in sources_to_run.items():
            if not sources:
                logger.info("\n%s: no sources configured — skipping", slug)
                continue

            result = await db.execute(
                text("SELECT id FROM personas WHERE slug = :slug"),
                {"slug": slug},
            )
            persona_row = result.fetchone()
            if not persona_row:
                logger.error("\n%s: persona not found in DB (run seed.py first)", slug)
                total_errors += 1
                continue

            persona_id = persona_row.id
            logger.info("\n%s (%d source(s)):", slug, len(sources))

            for source in sources:
                try:
                    ins, upd, skipped = await _ingest_source(db, persona_id, source, dry_run)
                    total_inserted += ins
                    total_updated += upd
                    total_skipped += skipped
                    if not dry_run:
                        logger.info("  ✓ %s: %d new, %d updated", source["title"], ins, upd)
                except Exception as exc:
                    logger.error("  ✗ %s: %s", source.get("title", "?"), exc)
                    total_errors += 1

        if not dry_run:
            await db.commit()

    logger.info(
        "\nDone — inserted: %d, updated: %d, skipped (dry-run): %d, errors: %d",
        total_inserted,
        total_updated,
        total_skipped,
        total_errors,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest philosopher corpus into source_chunks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and chunk without calling OpenAI or writing to DB",
    )
    parser.add_argument(
        "--persona",
        metavar="SLUG",
        help="Only ingest sources for this persona slug",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, persona_filter=args.persona))
