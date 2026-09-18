"""
Ingest the corpus defined in corpus_sources.py into the source_chunks table.

Usage (from apps/api/):
    python -m scripts.ingest_corpus [--dry-run] [--persona SLUG]

Flags:
    --dry-run     Fetch and chunk without calling OpenAI or writing to DB.
                  Useful for verifying Gutenberg URLs before incurring cost.
    --persona     Only ingest sources for one persona slug (e.g. --persona socrates).

Verification (added 2026-09-18, P0 corpus re-ingest):
    Every source is checked against the `Title:` header the fetched file actually
    serves, compared EXACTLY to its `gutenberg_title`. A mismatch REFUSES the run:
    nothing is committed and the process exits non-zero. HTTP 200 is not evidence
    that a URL serves the book it is configured to serve — four of these URLs
    served entirely different books for four months precisely because status was
    the only thing checked. See scripts/corpus_sources.py for that history.

Failure policy:
    ANY per-source failure aborts the whole run. A fetch failure, an empty chunk
    list, a missing persona row or a title mismatch all raise IngestRefused, the
    transaction rolls back and nothing is written. The previous behaviour — catch,
    count into `total_errors`, commit everything else, exit 0 — is what allowed a
    partial corpus to look like a successful ingest. A partial corpus is not a
    successful ingest.

Idempotency:
    Delete-then-insert per source, inside the run's single transaction. Rows for
    the source's own title AND for any title listed in its `supersedes` are
    deleted before the new chunks are inserted, so a source that shrinks (or is
    retitled) cannot strand an orphan tail of rows from the previous ingest at
    higher chunk_index values. Re-running produces the same final state.

Atomicity and rollback:
    The whole run is ONE transaction with a single commit at the end. Interrupting
    it, or any refusal, leaves production exactly as it was. There is no partial
    state to clean up and no resume to implement: a re-run starts over, and the
    full corpus costs roughly $0.02 and a few minutes.

Cost estimate:
    text-embedding-3-small costs $0.02 per 1M tokens. The full corpus is ~2.5k
    chunks of 512 tokens with 50 overlap, so ~1.1M tokens: about $0.02 per full
    run, in ~29 batched embedding calls.
"""

import argparse
import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import text

from db.session import AsyncSessionLocal
from scripts.chunking import chunk_text
from scripts.corpus_sources import CORPUS_SOURCES
from scripts.curated_chunks import CURATED_CHUNKS

logger = logging.getLogger(__name__)

_GUTENBERG_START = "*** START OF THE PROJECT GUTENBERG"
_GUTENBERG_END = "*** END OF THE PROJECT GUTENBERG"

# A Gutenberg header field is "Key: value", optionally wrapped onto following
# lines which are indented. Anything at column 0 ending in ":" starts a new field.
_TITLE_LINE = re.compile(r"^Title:[ \t]*(.*)$", re.MULTILINE)
_NEW_FIELD = re.compile(r"^[A-Za-z][A-Za-z ]*:")


class IngestRefused(Exception):
    """A source failed verification. Aborts the entire run; nothing is committed."""


# ── Source verification ───────────────────────────────────────────────────────

def _normalise_title(value: str) -> str:
    """Collapse CRLF and runs of whitespace to single spaces, and strip.

    This is the ONLY latitude the comparison gets. It is deliberately not a
    casefold, not a punctuation strip and not a substring test: "The Enchiridion"
    is a substring of "A Selection from the Discourses of Epictetus with the
    Encheiridion", so a substring guard would have passed the 2026-05-17 damage
    rather than caught it.
    """
    return " ".join(value.replace("\r\n", "\n").split())


def _parse_gutenberg_title(raw: str) -> str | None:
    """Return the `Title:` header of a Gutenberg plaintext file, or None.

    Read from the RAW text: the header sits above the "*** START OF ..." marker
    and so is discarded by _strip_boilerplate. A wrapped title continues on
    indented lines, which are joined back together here.
    """
    header = raw.split(_GUTENBERG_START, 1)[0]
    match = _TITLE_LINE.search(header)
    if match is None:
        return None

    parts = [match.group(1)]
    for line in header[match.end():].split("\n")[1:]:
        if not line.strip():
            break
        if not line[:1].isspace() or _NEW_FIELD.match(line.strip()):
            break
        parts.append(line.strip())

    title = _normalise_title(" ".join(parts))
    return title or None


def _assert_title_matches(source: dict, raw: str) -> None:
    """Refuse the run unless the fetched file is the book the config claims.

    This is the guard that would have caught all four wrong books in May. It runs
    before any embedding call, so a misconfigured source costs nothing but a GET.
    """
    expected = source["gutenberg_title"]
    found = _parse_gutenberg_title(raw)

    if found is None:
        raise IngestRefused(
            f"NO Title: HEADER in the file served for {source['title']!r}\n"
            f"    url:      {source['gutenberg_url']}\n"
            f"    expected: {expected!r}\n"
            "  A Gutenberg plaintext file always carries one. Refusing to ingest "
            "a file this script cannot identify."
        )

    if _normalise_title(found) != _normalise_title(expected):
        raise IngestRefused(
            f"TITLE MISMATCH for {source['title']!r}\n"
            f"    url:      {source['gutenberg_url']}\n"
            f"    expected: {expected!r}\n"
            f"    served:   {found!r}\n"
            "  The URL does not serve the book this source claims. Either the id "
            "is wrong, or Gutenberg retitled the file — check which, then fix the "
            "url or update gutenberg_title. Refusing to ingest."
        )


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
) -> tuple[int, int]:
    """Verify, clear and re-insert one source. Returns (deleted, inserted).

    Under --dry-run both numbers are what WOULD happen: the clear is counted with
    a SELECT instead of a DELETE and the insert count is the chunk count, with no
    embedding call and no write. That makes a dry run a genuine preview of the
    row-level change, which is what it is read for before a production run.
    """
    from services.embedding_client import embedding_client

    url = source["gutenberg_url"]
    title = source["title"]
    source_type = source.get("source_type", "primary_text")

    logger.info("  Fetching: %s", title)
    raw = await _fetch_text(url)
    if raw is None:
        raise IngestRefused(
            f"FETCH FAILED for {title!r}\n"
            f"    url: {url}\n"
            "  Refusing to continue: a corpus missing one of its sources is not a "
            "successful ingest."
        )

    # Before any embedding call, so a misconfigured source costs one GET.
    _assert_title_matches(source, raw)

    clean = _strip_boilerplate(raw)
    chunks = chunk_text(clean)

    if not chunks:
        raise IngestRefused(
            f"NO CHUNKS produced for {title!r}\n"
            f"    url: {url}\n"
            "  The fetch succeeded and the title matched, so the file is empty or "
            "the boilerplate markers consumed it. Refusing to ingest."
        )

    # Rows this source owns: its own title, plus every title it was previously
    # written under. Without the second, a RETITLE strands the old rows entirely;
    # without the clear at all, a source that produces FEWER chunks than last time
    # leaves a tail at the higher chunk_index values — invisible, still embedded,
    # still retrievable. That tail is how 227 of the 247 rows of Charlotte Brontë
    # would have survived a naive re-ingest of the real Crito, which is 20 chunks.
    titles_to_clear = [title, *source.get("supersedes", [])]

    deleted = 0
    for stale_title in titles_to_clear:
        if dry_run:
            result = await db.execute(
                text(
                    "SELECT count(*) FROM source_chunks "
                    "WHERE persona_id = :persona_id AND source_title = :source_title"
                ),
                {"persona_id": persona_id, "source_title": stale_title},
            )
            count = result.scalar() or 0
        else:
            result = await db.execute(
                text(
                    "DELETE FROM source_chunks "
                    "WHERE persona_id = :persona_id AND source_title = :source_title"
                ),
                {"persona_id": persona_id, "source_title": stale_title},
            )
            count = result.rowcount or 0
        if count:
            logger.info(
                "    %s %d existing row(s) titled %r",
                "would clear" if dry_run else "cleared",
                count,
                stale_title,
            )
        deleted += count

    logger.info("  %d chunks from %s", len(chunks), title)

    if dry_run:
        logger.info("  [dry-run] would embed and insert %d chunks", len(chunks))
        return deleted, len(chunks)

    # Embed in batches to respect rate limits
    batch_size = 100
    embeddings: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch_embeddings = await embedding_client.embed_batch(chunks[i : i + batch_size])
        embeddings.extend(batch_embeddings)

    # A plain INSERT, not an upsert. The clear above emptied this (persona, title),
    # so a unique violation here would mean the clear was wrong — and that must
    # raise rather than quietly resolve itself into an UPDATE.
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        await db.execute(
            text("""
                INSERT INTO source_chunks
                    (id, persona_id, source_title, source_type, content,
                     embedding, chunk_index, created_at)
                VALUES
                    (gen_random_uuid(), :persona_id, :source_title, :source_type, :content,
                     CAST(:embedding AS vector), :chunk_index, now())
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

    await db.flush()
    return deleted, len(chunks)


# ── Curated chunk ingestion ───────────────────────────────────────────────────

async def _ingest_curated(
    db,
    persona_id: str,
    curated_list: list[dict],
    dry_run: bool,
) -> tuple[int, int, int]:
    """Embed and upsert hand-curated chunks. Returns (inserted, updated, dry_run_skipped)."""
    from services.embedding_client import embedding_client

    if not curated_list:
        return 0, 0, 0

    logger.info("  %d curated chunks to process", len(curated_list))

    if dry_run:
        logger.info("  [dry-run] would embed and upsert %d curated chunks", len(curated_list))
        return 0, 0, len(curated_list)

    contents = [c["content"] for c in curated_list]
    embeddings = await embedding_client.embed_batch(contents)

    inserted = updated = 0
    for idx, (chunk_data, embedding) in enumerate(zip(curated_list, embeddings)):
        row = await db.execute(
            text("""
                INSERT INTO source_chunks
                    (id, persona_id, source_title, source_type, content,
                     embedding, chunk_index, page_ref, created_at)
                VALUES
                    (gen_random_uuid(), :persona_id, :source_title, :source_type, :content,
                     CAST(:embedding AS vector), :chunk_index, :page_ref, now())
                ON CONFLICT (persona_id, source_title, chunk_index)
                WHERE chunk_index IS NOT NULL
                DO UPDATE SET
                    content   = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    page_ref  = EXCLUDED.page_ref
                RETURNING (xmax = 0) AS was_inserted
            """),
            {
                "persona_id": persona_id,
                "source_title": chunk_data["source_title"],
                "source_type": chunk_data["source_type"],
                "content": chunk_data["content"],
                "embedding": str(embedding),
                "chunk_index": idx,
                "page_ref": chunk_data.get("page_ref"),
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

async def _persona_id(db, slug: str) -> str:
    result = await db.execute(
        text("SELECT id FROM personas WHERE slug = :slug"),
        {"slug": slug},
    )
    row = result.fetchone()
    if not row:
        raise IngestRefused(
            f"PERSONA NOT IN DB: {slug!r} (run seed.py first).\n"
            "  Refusing to ingest a corpus with a missing persona."
        )
    return row.id


async def main(dry_run: bool = False, persona_filter: str | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sources_to_run = {
        slug: sources
        for slug, sources in CORPUS_SOURCES.items()
        if persona_filter is None or slug == persona_filter
    }

    curated_to_run = {
        slug: chunks
        for slug, chunks in CURATED_CHUNKS.items()
        if persona_filter is None or slug == persona_filter
    }

    if not sources_to_run and not curated_to_run:
        logger.error("No sources found for persona filter: %s", persona_filter)
        sys.exit(1)

    mode_label = "[DRY RUN] " if dry_run else ""
    persona_count = len(set(sources_to_run) | set(curated_to_run))
    logger.info("%sIngesting corpus for %d persona(s)...", mode_label, persona_count)

    # (slug, title, deleted, inserted) per source, for the closing table.
    per_source: list[tuple[str, str, int, int]] = []
    total_deleted = total_inserted = 0
    total_curated_inserted = total_curated_updated = total_curated_skipped = 0

    # ONE transaction for the whole run, committed once at the end. Any refusal
    # propagates out of this block, the session closes without committing, and
    # production is untouched. There is deliberately no per-source recovery:
    # a partial corpus is not a successful ingest.
    try:
        async with AsyncSessionLocal() as db:
            for slug, sources in sources_to_run.items():
                if not sources:
                    logger.info("\n%s: no sources configured — skipping", slug)
                    continue

                persona_id = await _persona_id(db, slug)
                logger.info("\n%s (%d source(s)):", slug, len(sources))

                for source in sources:
                    deleted, inserted = await _ingest_source(db, persona_id, source, dry_run)
                    per_source.append((slug, source["title"], deleted, inserted))
                    total_deleted += deleted
                    total_inserted += inserted
                    logger.info(
                        "  %s %s: %d cleared, %d %s",
                        "→" if dry_run else "✓",
                        source["title"],
                        deleted,
                        inserted,
                        "to insert" if dry_run else "inserted",
                    )

            for slug, curated_list in curated_to_run.items():
                if not curated_list:
                    continue

                persona_id = await _persona_id(db, slug)
                logger.info("\n%s curated (%d chunk(s)):", slug, len(curated_list))

                ins, upd, skipped = await _ingest_curated(db, persona_id, curated_list, dry_run)
                total_curated_inserted += ins
                total_curated_updated += upd
                total_curated_skipped += skipped
                if not dry_run:
                    logger.info("  ✓ curated: %d new, %d updated", ins, upd)

            if not dry_run:
                await db.commit()

    except IngestRefused as exc:
        logger.error("\n%sREFUSED — %s", mode_label, exc)
        logger.error(
            "\nNothing was committed. The transaction rolled back; production is "
            "exactly as it was before this run."
        )
        raise SystemExit(1)

    logger.info("\n%s", "─" * 74)
    logger.info("%-20s %-38s %7s %8s", "persona", "source", "cleared", "inserted")
    logger.info("%s", "─" * 74)
    for slug, title, deleted, inserted in per_source:
        logger.info("%-20s %-38s %7d %8d", slug, title[:38], deleted, inserted)
    logger.info("%s", "─" * 74)
    logger.info("%-59s %7d %8d", "TOTAL", total_deleted, total_inserted)

    if total_curated_inserted or total_curated_updated or total_curated_skipped:
        logger.info(
            "curated: %d new, %d updated, %d skipped (dry-run)",
            total_curated_inserted,
            total_curated_updated,
            total_curated_skipped,
        )

    if dry_run:
        logger.info("\n[DRY RUN] nothing was written.")


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
