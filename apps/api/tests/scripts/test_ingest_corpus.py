"""Unit tests for scripts/ingest_corpus.py.

All external calls (httpx, OpenAI, SQLAlchemy) are mocked.
No real DB writes, no real API calls.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helper: minimal Gutenberg-formatted text ──────────────────────────────────

_SAMPLE_BODY = "The unexamined life is not worth living. " * 50

SAMPLE_GUTENBERG_TEXT = f"""
The Project Gutenberg EBook of Apology

Some preamble text here.

*** START OF THE PROJECT GUTENBERG EBOOK APOLOGY ***

{_SAMPLE_BODY}

*** END OF THE PROJECT GUTENBERG EBOOK APOLOGY ***

End of the Project Gutenberg EBook
"""


# ── Boilerplate stripping ──────────────────────────────────────────────────────

def test_strip_boilerplate_removes_header_and_footer():
    from scripts.ingest_corpus import _strip_boilerplate

    result = _strip_boilerplate(SAMPLE_GUTENBERG_TEXT)
    assert "*** START OF" not in result
    assert "*** END OF" not in result
    assert "The unexamined life" in result


def test_strip_boilerplate_no_markers_returns_full_text():
    from scripts.ingest_corpus import _strip_boilerplate

    text = "Pure philosophy without markers."
    result = _strip_boilerplate(text)
    assert result == text


# ── Fetch text ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_text_returns_none_on_http_error():
    from scripts.ingest_corpus import _fetch_text
    import httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )

    with patch("scripts.ingest_corpus.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await _fetch_text("https://example.com/fake.txt")

    assert result is None


# ── _ingest_source ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_source_dry_run_does_not_write():
    """In dry-run mode: chunks are computed but no embeddings called, no DB writes."""
    from scripts.ingest_corpus import _ingest_source

    db = AsyncMock()
    source = {
        "title": "Apology",
        "gutenberg_url": "https://www.gutenberg.org/cache/epub/1656/pg1656.txt",
        "source_type": "primary_text",
    }

    with patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=SAMPLE_GUTENBERG_TEXT)):
        ins, upd, skipped = await _ingest_source(db, "persona-uuid", source, dry_run=True)

    assert ins == 0
    assert upd == 0
    assert skipped > 0
    db.execute.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_source_calls_embed_and_upsert():
    """Live run: embeddings are requested and DB upsert is called once per chunk."""
    from scripts.ingest_corpus import _ingest_source

    mock_scalar = MagicMock(return_value=True)   # was_inserted = True
    mock_result = MagicMock()
    mock_result.scalar = mock_scalar

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    mock_embedding = [0.1] * 1536

    source = {
        "title": "Apology",
        "gutenberg_url": "https://www.gutenberg.org/cache/epub/1656/pg1656.txt",
        "source_type": "primary_text",
    }

    with (
        patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=SAMPLE_GUTENBERG_TEXT)),
        patch(
            "scripts.ingest_corpus.chunk_text",
            return_value=["chunk one", "chunk two"],
        ),
        patch("scripts.ingest_corpus.AsyncSessionLocal"),
        patch(
            "services.embedding_client.embedding_client.embed_batch",
            new=AsyncMock(return_value=[mock_embedding, mock_embedding]),
        ),
    ):
        ins, upd, skipped = await _ingest_source(db, "persona-uuid", source, dry_run=False)

    assert ins == 2
    assert upd == 0
    assert db.execute.call_count == 2  # once per chunk
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_source_failed_fetch_returns_zeros():
    """A 404 or network error on a source yields (0, 0, 0) and does not raise."""
    from scripts.ingest_corpus import _ingest_source

    db = AsyncMock()
    source = {
        "title": "Missing Book",
        "gutenberg_url": "https://www.gutenberg.org/cache/epub/99999/pg99999.txt",
        "source_type": "primary_text",
    }

    with patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=None)):
        ins, upd, skipped = await _ingest_source(db, "persona-uuid", source, dry_run=False)

    assert ins == 0
    assert upd == 0
    assert skipped == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_main_skips_missing_persona_and_continues():
    """A persona not found in DB causes an error count but the loop continues."""
    from scripts.ingest_corpus import main

    # Persona lookup returns nothing (persona not seeded)
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None   # persona not found
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {"ghost_persona": [
            {
                "title": "Ghost Work",
                "gutenberg_url": "https://example.com/ghost.txt",
                "source_type": "primary_text",
            }
        ]}),
    ):
        # Should complete without raising even though persona is missing
        await main(dry_run=False, persona_filter=None)


@pytest.mark.asyncio
async def test_main_single_source_error_does_not_halt_loop():
    """An exception in one source's ingestion does not abort remaining sources."""
    from scripts.ingest_corpus import main

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    persona_result = MagicMock()
    persona_result.fetchone.return_value = MagicMock(id="persona-uuid-1")
    db.execute = AsyncMock(return_value=persona_result)

    two_sources = [
        {"title": "Book A", "gutenberg_url": "https://example.com/a.txt", "source_type": "primary_text"},
        {"title": "Book B", "gutenberg_url": "https://example.com/b.txt", "source_type": "primary_text"},
    ]

    call_count = 0

    async def failing_then_ok(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated network failure")
        return (1, 0, 0)

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {"test_persona": two_sources}),
        patch("scripts.ingest_corpus._ingest_source", side_effect=failing_then_ok),
    ):
        await main(dry_run=False, persona_filter=None)

    # Both sources were attempted despite first failure
    assert call_count == 2


# ── Curated chunks ────────────────────────────────────────────────────────────

_MOCK_CURATED = [
    {
        "source_title": "Meditations (curated)",
        "source_type": "primary_text",
        "page_ref": "Book II.4",
        "content": "Consider how much more pain is brought on us by the anger.",
    },
    {
        "source_title": "Meditations (curated)",
        "source_type": "primary_text",
        "page_ref": "Book V.8",
        "content": "In the morning when thou risest unwillingly.",
    },
]


def test_curated_chunks_module_loads():
    """All 19 Marcus Aurelius curated chunks load from curated_chunks.py."""
    from scripts.curated_chunks import CURATED_CHUNKS

    assert "marcus_aurelius" in CURATED_CHUNKS
    chunks = CURATED_CHUNKS["marcus_aurelius"]
    assert len(chunks) == 19
    # All must be primary_text and use the curated source_title
    for chunk in chunks:
        assert chunk["source_title"] == "Meditations (curated)"
        assert chunk["source_type"] == "primary_text"
        assert chunk["page_ref"] is not None
        assert chunk["content"]
    # No Stanford Encyclopedia or Beauvoir content
    for chunk in chunks:
        assert "Stanford" not in chunk["source_title"]
        assert "Beauvoir" not in chunk["source_title"]


@pytest.mark.asyncio
async def test_ingest_curated_dry_run_skips_embed_and_db():
    """dry_run=True returns (0, 0, N) without calling embed or DB."""
    from scripts.ingest_corpus import _ingest_curated

    db = AsyncMock()

    with patch(
        "services.embedding_client.embedding_client.embed_batch",
        new=AsyncMock(),
    ) as mock_embed:
        ins, upd, skipped = await _ingest_curated(db, "persona-uuid", _MOCK_CURATED, dry_run=True)

    assert ins == 0
    assert upd == 0
    assert skipped == len(_MOCK_CURATED)
    mock_embed.assert_not_called()
    db.execute.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_curated_live_embeds_and_upserts():
    """Live run embeds all chunks in one batch and calls DB once per chunk."""
    from scripts.ingest_corpus import _ingest_curated

    mock_embedding = [0.1] * 1536
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=True)  # was_inserted = True

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "services.embedding_client.embedding_client.embed_batch",
        new=AsyncMock(return_value=[mock_embedding, mock_embedding]),
    ):
        ins, upd, skipped = await _ingest_curated(db, "persona-uuid", _MOCK_CURATED, dry_run=False)

    assert ins == 2
    assert upd == 0
    assert skipped == 0
    assert db.execute.call_count == 2
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_main_persona_filter_excludes_curated_other_persona():
    """--persona socrates does NOT process marcus_aurelius curated chunks."""
    from scripts.ingest_corpus import main

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    persona_result = MagicMock()
    persona_result.fetchone.return_value = MagicMock(id="persona-uuid-socrates")
    db.execute = AsyncMock(return_value=persona_result)

    mock_ingest_curated = AsyncMock(return_value=(0, 0, 0))

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {"socrates": []}),
        patch(
            "scripts.ingest_corpus.CURATED_CHUNKS",
            {"marcus_aurelius": _MOCK_CURATED},
        ),
        patch("scripts.ingest_corpus._ingest_curated", mock_ingest_curated),
    ):
        await main(dry_run=False, persona_filter="socrates")

    # _ingest_curated must NOT have been called for marcus_aurelius
    mock_ingest_curated.assert_not_called()


@pytest.mark.asyncio
async def test_main_curated_respects_dry_run():
    """--dry-run propagates to _ingest_curated (no DB writes)."""
    from scripts.ingest_corpus import main

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    persona_result = MagicMock()
    persona_result.fetchone.return_value = MagicMock(id="persona-uuid")
    db.execute = AsyncMock(return_value=persona_result)

    mock_ingest_curated = AsyncMock(return_value=(0, 0, len(_MOCK_CURATED)))

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {}),
        patch(
            "scripts.ingest_corpus.CURATED_CHUNKS",
            {"marcus_aurelius": _MOCK_CURATED},
        ),
        patch("scripts.ingest_corpus._ingest_curated", mock_ingest_curated),
    ):
        await main(dry_run=True, persona_filter=None)

    # Confirm _ingest_curated was called with dry_run=True
    mock_ingest_curated.assert_called_once()
    call_args = mock_ingest_curated.call_args
    assert call_args.args[3] is True  # dry_run positional arg
    # DB commit must NOT be called in dry-run
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_curated_source_title_distinct_from_auto_chunked():
    """Curated source_title 'Meditations (curated)' never equals auto-chunked 'Meditations'."""
    from scripts.curated_chunks import CURATED_CHUNKS
    from scripts.corpus_sources import CORPUS_SOURCES

    curated_titles = {c["source_title"] for c in CURATED_CHUNKS.get("marcus_aurelius", [])}
    auto_titles = {s["title"] for s in CORPUS_SOURCES.get("marcus_aurelius", [])}

    assert curated_titles.isdisjoint(auto_titles), (
        f"Collision between curated and auto-chunked titles: {curated_titles & auto_titles}"
    )
