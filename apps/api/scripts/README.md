# apps/api/scripts

One-off operational tools for corpus ingestion and manual testing.

---

## ingest_corpus.py

Fetches public-domain philosopher texts from Project Gutenberg, chunks them via a
fixed-token + overlap strategy, generates embeddings with OpenAI
`text-embedding-3-small`, and writes the results to the `source_chunks` table.

**Run from `apps/api/`:**

```bash
# Full corpus — all configured personas
python -m scripts.ingest_corpus

# Dry run — fetch and chunk only; no OpenAI calls, no DB writes
python -m scripts.ingest_corpus --dry-run

# Single persona — useful for incremental testing
python -m scripts.ingest_corpus --persona socrates
python -m scripts.ingest_corpus --persona marcus_aurelius --dry-run
```

**Required environment variables:**

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg format) |
| `OPENAI_API_KEY` | OpenAI API key for text-embedding-3-small |

**Cost estimate:** `text-embedding-3-small` costs $0.02 per 1M tokens.
The full corpus is <500K tokens; expected cost **<$0.01** per full run.

**Idempotency:** Re-running on unchanged content is safe. The script uses
`ON CONFLICT (persona_id, source_title, chunk_index) DO UPDATE` — rows are
updated in place, not duplicated.

**When to run:**
- Initial setup after `alembic upgrade head` and `python db/seed.py`
- After adding new sources to `corpus_sources.py`
- After a persona is added to the DB (run with `--persona <slug>`)

---

## curated_chunks.py

A pure data module of hand-selected passages with precise citation references.
Loaded alongside auto-chunked URL sources by `ingest_corpus.py`.

**When to use curated vs auto-chunked:**

| | Curated | Auto-chunked |
|---|---|---|
| Selection | Hand-picked, high signal | All text, variable quality |
| Citations | Exact book/section refs | None |
| Coverage | Key passages only | Full corpus |
| Use case | Quality retrieval | Broad coverage |

For production RAG quality, curated and auto-chunked chunks complement each
other — curated chunks surface canonical passages for common queries while
auto-chunked chunks handle obscure references.

**Disambiguation:** Curated chunks use `source_title = "<Title> (curated)"`
(e.g., `"Meditations (curated)"`). Auto-chunked chunks use the plain title
(e.g., `"Meditations"`). Both carry integer `chunk_index` values so both
participate in the DB-level upsert dedup index. No conflicts are possible.

**Adding curated chunks for a new persona:**

1. Add an entry to `CURATED_CHUNKS` in `curated_chunks.py`:

```python
CURATED_CHUNKS = {
    "marcus_aurelius": [...],   # existing
    "socrates": [
        {
            "source_title": "Apology (curated)",
            "source_type": "primary_text",
            "page_ref": "17a",
            "content": "...",
        },
    ],
}
```

2. All content must be public domain.
3. Re-run `ingest_corpus.py` (or `--persona socrates`) to ingest.

Currently populated: Marcus Aurelius — 19 passages from Meditations (Long 1862,
recovered from pre-C3a `ingest_sources.py` per CLAUDE.md Rule 5 reconciliation).

---

## corpus_sources.py

Static allowlist of Project Gutenberg sources per persona. Each entry has:

```python
{
    "title": str,
    "translator": str | None,   # translator name and year
    "year": int,                # translation year (must be < 1928 for US PD)
    "gutenberg_url": str,       # direct .txt cache URL
    "source_type": str,         # "primary_text" | "commentary"
    "license": str,             # always "public_domain"
}
```

**Excluded personas** (copyright-blocked per Decision #7):
`carl_jung`, `simone_de_beauvoir`

URLs marked `# VERIFY IN C3b` have not been live-fetched during development.
The dry-run mode in `ingest_corpus.py` will surface any 404s without incurring
embedding cost.

---

## chunking.py

Pure functions for token-based text chunking. Uses `tiktoken` (cl100k_base,
the encoding used by `text-embedding-3-small`).

```python
from scripts.chunking import chunk_text

chunks = chunk_text(
    text,
    chunk_size_tokens=512,   # default
    overlap_tokens=50,       # default
)
```

No I/O, no side effects. Safe to import and test without any credentials.

---

## Other scripts

| Script | Purpose |
|---|---|
| `voice_test_socrates.py` | Manual voice/tone test for Socrates persona |
| `test_preferences_endpoint.py` | Manual smoke test for preferences API |
| `test_matches_endpoint.py` | Manual smoke test for matches API |
