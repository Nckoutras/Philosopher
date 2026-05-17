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
