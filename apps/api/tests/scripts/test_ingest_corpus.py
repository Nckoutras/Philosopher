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

Title: Apology
Author: Plato
Translator: Benjamin Jowett
Release date: March 1, 1999 [eBook #1656]
Language: English

*** START OF THE PROJECT GUTENBERG EBOOK APOLOGY ***

{_SAMPLE_BODY}

*** END OF THE PROJECT GUTENBERG EBOOK APOLOGY ***

End of the Project Gutenberg EBook
"""


def _source(title="Apology", gutenberg_title=None, **overrides):
    """A CORPUS_SOURCES-shaped dict. gutenberg_title defaults to title."""
    source = {
        "title": title,
        "gutenberg_title": title if gutenberg_title is None else gutenberg_title,
        "gutenberg_url": "https://www.gutenberg.org/cache/epub/1656/pg1656.txt",
        "source_type": "primary_text",
    }
    source.update(overrides)
    return source


def _gutenberg_text(title: str, body: str = _SAMPLE_BODY) -> str:
    """A Gutenberg-shaped file whose `Title:` header is `title`."""
    return (
        f"The Project Gutenberg EBook of {title}\n\n"
        f"Title: {title}\n"
        "Author: Someone\n"
        "Language: English\n\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
        f"{body}\n\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK ***\n"
    )


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
async def test_ingest_source_dry_run_counts_but_does_not_write():
    """Dry run: chunks computed, existing rows COUNTED, no embeddings, no writes.

    The dry run reads production (a SELECT) because its whole purpose is to
    preview the row-level change before the real run. What it must never do is
    embed or write.
    """
    from scripts.ingest_corpus import _ingest_source

    count_result = MagicMock()
    count_result.scalar.return_value = 247

    db = AsyncMock()
    db.execute = AsyncMock(return_value=count_result)

    embed = AsyncMock()

    with (
        patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=SAMPLE_GUTENBERG_TEXT)),
        patch("services.embedding_client.embedding_client.embed_batch", new=embed),
    ):
        deleted, inserted = await _ingest_source(db, "persona-uuid", _source(), dry_run=True)

    assert deleted == 247
    assert inserted > 0
    embed.assert_not_called()
    db.flush.assert_not_called()

    # Every statement issued was a SELECT — nothing was mutated.
    for call in db.execute.call_args_list:
        assert "SELECT" in str(call.args[0]).upper()
        assert "DELETE" not in str(call.args[0]).upper()


@pytest.mark.asyncio
async def test_ingest_source_deletes_before_inserting():
    """Live run: the source is cleared first, then one INSERT per chunk."""
    from scripts.ingest_corpus import _ingest_source

    delete_result = MagicMock()
    delete_result.rowcount = 247

    db = AsyncMock()
    db.execute = AsyncMock(return_value=delete_result)

    mock_embedding = [0.1] * 1536

    with (
        patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=SAMPLE_GUTENBERG_TEXT)),
        patch("scripts.ingest_corpus.chunk_text", return_value=["chunk one", "chunk two"]),
        patch(
            "services.embedding_client.embedding_client.embed_batch",
            new=AsyncMock(return_value=[mock_embedding, mock_embedding]),
        ),
    ):
        deleted, inserted = await _ingest_source(db, "persona-uuid", _source(), dry_run=False)

    assert deleted == 247
    assert inserted == 2

    statements = [str(call.args[0]).upper() for call in db.execute.call_args_list]
    assert len(statements) == 3, "expected one DELETE then two INSERTs"
    assert "DELETE" in statements[0]
    assert all("INSERT" in s for s in statements[1:])

    # The DELETE must come first: an insert-then-delete order would wipe the
    # rows it had just written.
    assert statements.index([s for s in statements if "DELETE" in s][0]) == 0
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_source_clears_superseded_titles_too():
    """A retitled source clears its OLD title as well, or those rows are stranded.

    This is the Epictetus case: 38 rows written as "Discourses of Epictetus" when
    the source is now titled "Discourses of Epictetus (selections)". Keyed only on
    the new title, the delete would miss them entirely.
    """
    from scripts.ingest_corpus import _ingest_source

    delete_result = MagicMock()
    delete_result.rowcount = 19

    db = AsyncMock()
    db.execute = AsyncMock(return_value=delete_result)

    source = _source(
        title="Discourses of Epictetus (selections)",
        gutenberg_title="Discourses of Epictetus (selections)",
        supersedes=["Discourses of Epictetus"],
    )

    with (
        patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(
            return_value=_gutenberg_text("Discourses of Epictetus (selections)")
        )),
        patch("scripts.ingest_corpus.chunk_text", return_value=["only chunk"]),
        patch(
            "services.embedding_client.embedding_client.embed_batch",
            new=AsyncMock(return_value=[[0.1] * 1536]),
        ),
    ):
        deleted, inserted = await _ingest_source(db, "persona-uuid", source, dry_run=False)

    # Two deletes, one per title, both counted.
    assert deleted == 38
    assert inserted == 1

    cleared = [
        call.args[1]["source_title"]
        for call in db.execute.call_args_list
        if "DELETE" in str(call.args[0]).upper()
    ]
    assert cleared == ["Discourses of Epictetus (selections)", "Discourses of Epictetus"]


@pytest.mark.asyncio
async def test_ingest_source_failed_fetch_refuses():
    """A 404 or network error ABORTS. It used to return (0, 0, 0) and continue.

    That tolerance is what let a partial corpus commit and report success.
    """
    from scripts.ingest_corpus import _ingest_source, IngestRefused

    db = AsyncMock()

    with patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(return_value=None)):
        with pytest.raises(IngestRefused, match="FETCH FAILED"):
            await _ingest_source(db, "persona-uuid", _source(title="Missing Book"), dry_run=False)

    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_main_missing_persona_aborts_without_committing():
    """A persona absent from the DB aborts the run. It used to be counted and skipped."""
    from scripts.ingest_corpus import main

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None   # persona not seeded
    db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {"ghost_persona": [_source(title="Ghost Work")]}),
        patch("scripts.ingest_corpus.CURATED_CHUNKS", {}),
    ):
        with pytest.raises(SystemExit) as exc:
            await main(dry_run=False, persona_filter=None)

    assert exc.value.code == 1
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_main_single_source_failure_aborts_the_whole_run():
    """One failing source stops the run; later sources are NOT attempted.

    This test previously asserted the opposite — that the loop continued — and
    named it a feature. It is the silent-success mode that produced the 2026-05-17
    corpus damage: catch, count, commit everything else, exit 0.
    """
    from scripts.ingest_corpus import main, IngestRefused

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    persona_result = MagicMock()
    persona_result.fetchone.return_value = MagicMock(id="persona-uuid-1")
    db.execute = AsyncMock(return_value=persona_result)

    two_sources = [_source(title="Book A"), _source(title="Book B")]

    call_count = 0

    async def failing_then_ok(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IngestRefused("simulated title mismatch")
        return (0, 1)

    with (
        patch("scripts.ingest_corpus.AsyncSessionLocal", return_value=db),
        patch("scripts.ingest_corpus.CORPUS_SOURCES", {"test_persona": two_sources}),
        patch("scripts.ingest_corpus.CURATED_CHUNKS", {}),
        patch("scripts.ingest_corpus._ingest_source", side_effect=failing_then_ok),
    ):
        with pytest.raises(SystemExit) as exc:
            await main(dry_run=False, persona_filter=None)

    assert exc.value.code == 1
    assert call_count == 1, "the second source must not be attempted"
    db.commit.assert_not_called()


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


# ── The title guard ───────────────────────────────────────────────────────────
#
# The runtime half of Step 6. These never reach the network: each feeds the guard
# a Gutenberg-shaped string and checks what it does. Together they pin the one
# property that matters — the comparison is EXACT, and no near-miss passes.

def test_title_guard_accepts_the_exact_header():
    from scripts.ingest_corpus import _assert_title_matches

    _assert_title_matches(_source(), SAMPLE_GUTENBERG_TEXT)   # must not raise


def test_title_guard_refuses_a_different_book():
    """The Crito case: pg1700 returned 200 and served Charlotte Bronte."""
    from scripts.ingest_corpus import _assert_title_matches, IngestRefused

    served = _gutenberg_text("The Life of Charlotte Bronte - Volume 2")

    with pytest.raises(IngestRefused, match="TITLE MISMATCH") as exc:
        _assert_title_matches(_source(title="Crito"), served)

    # The message must name both sides — a refusal nobody can act on gets ignored.
    assert "Crito" in str(exc.value)
    assert "Charlotte Bronte" in str(exc.value)


def test_title_guard_refuses_when_expected_is_a_substring_of_served():
    """THE regression test for this whole change.

    "The Enchiridion" is a substring of "A Selection from the Discourses of
    Epictetus with the Encheiridion". A substring or `in` comparison would call
    this a match and ingest the wrong book — which is precisely how 178 rows of a
    boys' sports novel reached production under the Enchiridion's name.
    """
    from scripts.ingest_corpus import _assert_title_matches, IngestRefused

    served = _gutenberg_text(
        "A Selection from the Discourses of Epictetus with the Encheiridion"
    )

    with pytest.raises(IngestRefused, match="TITLE MISMATCH"):
        _assert_title_matches(_source(title="The Enchiridion"), served)


def test_title_guard_refuses_when_served_is_a_substring_of_expected():
    """The same trap in the other direction."""
    from scripts.ingest_corpus import _assert_title_matches, IngestRefused

    served = _gutenberg_text("The Enchiridion")
    source = _source(
        title="Discourses of Epictetus (selections)",
        gutenberg_title="A Selection from the Discourses of Epictetus with the Encheiridion",
    )

    with pytest.raises(IngestRefused, match="TITLE MISMATCH"):
        _assert_title_matches(source, served)


def test_title_guard_tolerates_crlf_and_repeated_whitespace():
    """Normalisation is the ONLY latitude: line endings and whitespace runs."""
    from scripts.ingest_corpus import _assert_title_matches

    served = (
        "Title:   The    Republic  \r\n"
        "Author: Plato\r\n\r\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK ***\r\n\r\n"
        "body text\r\n"
    )

    _assert_title_matches(_source(title="The Republic"), served)   # must not raise


def test_title_guard_reads_a_title_wrapped_onto_a_second_line():
    """Gutenberg wraps long titles onto indented continuation lines."""
    from scripts.ingest_corpus import _parse_gutenberg_title

    served = (
        "Title: The Importance of Being Earnest: A Trivial Comedy for\n"
        "       Serious People\n"
        "Author: Oscar Wilde\n\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\nbody\n"
    )

    assert _parse_gutenberg_title(served) == (
        "The Importance of Being Earnest: A Trivial Comedy for Serious People"
    )


def test_parse_title_does_not_absorb_the_next_field():
    from scripts.ingest_corpus import _parse_gutenberg_title

    served = "Title: Crito\nAuthor: Plato\nTranslator: Benjamin Jowett\n"
    assert _parse_gutenberg_title(served) == "Crito"


def test_title_guard_refuses_a_file_with_no_title_header():
    from scripts.ingest_corpus import _assert_title_matches, IngestRefused

    with pytest.raises(IngestRefused, match="NO Title: HEADER"):
        _assert_title_matches(_source(), "just some text with no header at all")


def test_parse_title_reads_the_header_not_the_body():
    """The header sits ABOVE the START marker, which _strip_boilerplate discards.

    A `Title:` line occurring inside the body must not be mistaken for it.
    """
    from scripts.ingest_corpus import _parse_gutenberg_title

    served = (
        "Title: Phaedo\n"
        "Author: Plato\n\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
        "Title: Not The Real Header\n"
    )

    assert _parse_gutenberg_title(served) == "Phaedo"


@pytest.mark.asyncio
async def test_a_mismatch_costs_no_embedding_call():
    """The guard runs before embedding, so a bad id costs one GET and nothing else."""
    from scripts.ingest_corpus import _ingest_source, IngestRefused

    db = AsyncMock()
    embed = AsyncMock()

    with (
        patch("scripts.ingest_corpus._fetch_text", new=AsyncMock(
            return_value=_gutenberg_text("On Your Mark!")
        )),
        patch("services.embedding_client.embedding_client.embed_batch", new=embed),
    ):
        with pytest.raises(IngestRefused, match="TITLE MISMATCH"):
            await _ingest_source(db, "persona-uuid", _source(title="The Enchiridion"), dry_run=False)

    embed.assert_not_called()
    db.execute.assert_not_called()
