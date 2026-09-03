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
UPDATEs the 88 seeded quotes and raises when an update matches no row, but those
rows are inserted by db/seed_quotes.py — a SCRIPT, whose own docstring says "run
once after migration 045". So the chain is: upgrade to 048, run the seed, then
upgrade to head. That is what _build_schema does.

The larger fact this surfaced, recorded for the docs rotation: **production's
database is not reproducible from migrations alone.** That is a
disaster-recovery property, not a test inconvenience, and nothing had exercised
it because nothing had ever rebuilt from scratch.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

API_DIR = Path(__file__).resolve().parent.parent.parent

# The revision the quotes seed must run at: 049 is the first migration that reads
# those rows back. Named, not computed — if the chain changes shape, this should
# fail loudly rather than silently stage at the wrong point.
SEED_AT_REVISION = "048_saved_quotes"

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


@pytest.fixture(scope="session")
def live_db_url() -> str:
    url = _test_url()
    if not url:
        pytest.skip(_SKIP_REASON, allow_module_level=True)
    return url


@pytest.fixture(scope="session")
def schema(live_db_url: str) -> str:
    """Build the real schema once per session, via the staged migration path.

    Synchronous on purpose: these are subprocess calls, so keeping the fixture
    sync sidesteps pytest-asyncio's session-vs-function event-loop scoping
    entirely (asyncio_default_fixture_loop_scope is unset in this repo).
    """
    _run([sys.executable, "-m", "alembic", "upgrade", SEED_AT_REVISION], live_db_url)
    _run([sys.executable, "db/seed_quotes.py"], live_db_url)
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
