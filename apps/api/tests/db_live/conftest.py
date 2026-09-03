"""Live-Postgres fixture for the memory domain (TD-57 down payment, Ruling #10).

WHY THIS EXISTS. No test in this repository has ever opened a database
connection. That was tolerable when the schema was simple; it is not now.
`memory_service.recall` orders by a pgvector cosine distance and cuts at 0.70;
`memory_entries.conversation_id` carries ON DELETE CASCADE; account deletion is a
single `DELETE FROM users` that only the schema enforces. A mocked AsyncSession
returns whatever the test author invented, so none of those can be asserted
against a mock — the query result IS the behaviour
(MEMORY_V2_INVESTIGATION_2026-09-03 §3).

SKIPS, NEVER ERRORS. Everything here is gated on DATABASE_URL_TEST. When it is
unset — every local run today, and the existing bare-`pytest -q` CI job — these
tests skip. `ci_baseline_failures.txt` is empty by design, so a collection error
here would turn the whole backend job red everywhere; a skip is invisible to it.

RUNNING THESE. CI does it automatically (see the `db-tests` job in
backend-ci.yml). Locally, once you have Docker:

    docker run --rm -d -p 5433:5432 \
      -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=philosopher_test \
      pgvector/pgvector:pg16

    cd apps/api
    DATABASE_URL_TEST=postgresql+asyncpg://postgres:postgres@localhost:5433/philosopher_test \
      python -m pytest tests/db_live -v

The image must be pgvector/pgvector (or another build carrying pgvector >= 0.5.0):
migration 001 runs CREATE EXTENSION vector, and 008 builds HNSW indexes, which
plain postgres:16 cannot do.

THE SCHEMA IS BUILT BY MIGRATIONS, NEVER create_all. create_all builds what the
models declare; migrations build what production actually has. The ON DELETE
clauses these tests exist to verify live only in the migrations
(013 set memory_entries.conversation_id to CASCADE; 056 closed the last four
account-deletion FKs), so a create_all schema would pass tests that production
would fail.

...WITH ONE STAGE IN THE MIDDLE, and it is a finding rather than a convenience.
`alembic upgrade head` does NOT run on an empty database. 049_quotes_expand
UPDATEs 88 quote rows and raises when an update matches no row — but no migration
inserts those rows. They come from db/seed_quotes.py, a SCRIPT, whose own
docstring says "run once after migration 045". So the schema has to be built in
stages: upgrade to 048, put the pre-049 corpus in place, then upgrade to head.

AND THE SEED SCRIPT CANNOT BE THAT MIDDLE STAGE — the first CI run proved it.
data/quotes_seed.json has moved on: it now holds the CURRENT corpus of 198 rows
(11 personas x 18), which is the 88 that predate 049 plus the very 110 that 049
inserts. Running it at 048-state therefore inserts 049's rows before 049 does,
and 049's bulk_insert dies on uq_quotes_persona_locator_text. The failing key in
that run was (socrates, "Plato, Apology 28b-d", "Count neither death nor anything
else before disgrace.") — row 0 of 049's own inserts list.

So the middle stage reconstructs the 045-era corpus instead: the seed file MINUS
the rows 049 adds. That subtraction is exact and checked at fixture time
(_pre_049_quotes) rather than assumed, and it touches no production file.

The larger fact all of this surfaced, recorded for the docs rotation:
**production's database is not reproducible from migrations alone**, and the seed
script is no longer a faithful replay of the 045-era corpus either. That is a
disaster-recovery property, not a test inconvenience, and nothing had exercised
it because nothing had ever rebuilt from scratch.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

API_DIR = Path(__file__).resolve().parent.parent.parent

# The revision the quotes seed must run at: 049 is the first migration that reads
# those rows back. Named, not computed — if the chain changes shape, this should
# fail loudly rather than silently stage at the wrong point.
SEED_AT_REVISION = "048_saved_quotes"

QUOTES_SEED = API_DIR / "data" / "quotes_seed.json"
MIGRATION_049_DATA = API_DIR / "db" / "migrations" / "data" / "quotes_049_data.json"

_SKIP_REASON = (
    "DATABASE_URL_TEST is not set — live-Postgres tests skipped. "
    "See this module's docstring for the docker one-liner."
)


def _test_url() -> str | None:
    return os.environ.get("DATABASE_URL_TEST") or None


def _run(argv: list[str], url: str) -> None:
    """Run one build step in a subprocess against the TEST database.

    A subprocess, not an in-process call, because both alembic's env.py and
    db/seed_quotes.py read the URL through `config` — a pydantic-settings object
    already instantiated at import with the real DATABASE_URL. Mutating that
    in-process is a fight with import order; handing a child process its own
    environment is not.
    """
    env = {
        **os.environ,
        "DATABASE_URL": url,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "sk-test-dummy"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "test-dummy"),
    }
    proc = subprocess.run(
        argv, cwd=API_DIR, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"schema build step failed: {' '.join(argv)}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )


def _pre_049_quotes() -> list[dict]:
    """The quotes corpus as it stood before 049 — the seed file MINUS 049's inserts.

    049 UPDATEs 88 rows by (persona_slug, text_en) and raises unless each update
    matches exactly one. Those 88 are what has to be in place; the 110 that 049
    inserts must NOT be, or its bulk_insert collides on
    uq_quotes_persona_locator_text (045). Since today's seed file contains both
    sets, the pre-049 corpus is the difference.

    DERIVED, NOT HARDCODED, and then CHECKED. If the corpus grows again through a
    later migration, the subtraction silently stops matching what 049 needs — so
    the invariant is asserted here and fails with an explanation rather than as a
    UniqueViolation 200 lines deeper.
    """
    seed = json.loads(QUOTES_SEED.read_text(encoding="utf-8"))
    data = json.loads(MIGRATION_049_DATA.read_text(encoding="utf-8"))

    def natural_key(row):
        return (row["persona_slug"], row["source_locator"], row["text_en"])

    added_by_049 = {natural_key(r) for r in data["inserts"]}
    remainder = [r for r in seed if natural_key(r) not in added_by_049]

    wanted = {(r["persona_slug"], r["text_en"]) for r in data["updates"]}
    have = {(r["persona_slug"], r["text_en"]) for r in remainder}
    if have != wanted or len(have) != len(remainder):
        raise RuntimeError(
            "the pre-049 quotes corpus can no longer be derived from "
            f"{QUOTES_SEED.name} minus 049's inserts: expected the {len(wanted)} rows "
            f"049 updates, got {len(remainder)} rows covering {len(have)} distinct keys. "
            "A later migration probably added quotes too; extend the subtraction to "
            "cover it, or the staged schema build cannot reproduce 048-state."
        )
    return remainder


async def _insert_quotes(dsn: str, rows: list[dict]) -> None:
    """Insert the pre-049 corpus with raw asyncpg.

    Raw asyncpg rather than db/seed_quotes.py: that script inserts today's whole
    corpus (see the module docstring), and editing it would be a production
    change to fix a test. Raw rather than SQLAlchemy because this runs inside a
    synchronous fixture and needs no models, no config and no session.
    """
    conn = await asyncpg.connect(dsn)
    try:
        await conn.executemany(
            "INSERT INTO quotes (persona_slug, text_en, text_original, source_locator,"
            " translation_note, confidence, context, themes)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            [
                (
                    r["persona_slug"], r["text_en"], r.get("text_original"),
                    r["source_locator"], r.get("translation_note"), r["confidence"],
                    r["context"], list(r.get("themes") or []),
                )
                for r in rows
            ],
        )
    finally:
        await conn.close()


def _seed_pre_049_corpus(url: str) -> None:
    """asyncpg speaks libpq, not SQLAlchemy — drop the driver from the URL.

    asyncio.run is safe here: this is a synchronous fixture running at session
    setup, before pytest-asyncio has a loop of its own open.
    """
    asyncio.run(_insert_quotes(url.replace("+asyncpg", ""), _pre_049_quotes()))


@pytest.fixture(scope="session")
def live_db_url() -> str:
    url = _test_url()
    if not url:
        pytest.skip(_SKIP_REASON, allow_module_level=True)
    return url


@pytest.fixture(scope="session")
def schema(live_db_url: str) -> str:
    """Build the real schema once per session, via the staged migration path.

    Synchronous on purpose: the alembic steps are subprocess calls and the seed
    step drives its own loop, so keeping the fixture sync sidesteps
    pytest-asyncio's session-vs-function event-loop scoping entirely
    (asyncio_default_fixture_loop_scope is unset in this repo).
    """
    _run([sys.executable, "-m", "alembic", "upgrade", SEED_AT_REVISION], live_db_url)
    _seed_pre_049_corpus(live_db_url)
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], live_db_url)
    return live_db_url


@pytest_asyncio.fixture
async def db(schema: str):
    """An AsyncSession inside a transaction that is ALWAYS rolled back.

    Isolation by rollback rather than by truncation: every test sees the seeded
    schema exactly as the migrations left it, and nothing a test writes outlives
    it — including the cascade tests, whose whole business is deleting rows.

    Engine per test rather than per session, for the same event-loop reason as
    above. These are a handful of tests; correctness beats the milliseconds.
    """
    engine = create_async_engine(schema, poolclass=None)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
