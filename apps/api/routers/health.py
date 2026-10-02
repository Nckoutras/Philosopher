"""GET /health/deep — does the system actually work, asked from inside the API.

WHY A SECOND PATH. /health (main.py) is a constant and must stay one: Render's
health check, if it points there, restarts the service when it fails, and a
database blip must not turn into an API restart. This endpoint is the opposite
kind of thing — it is allowed to say "no" — so it lives on its own path and is
read by the GitHub Actions liveness workflow, whose failure email is the alert
channel this product has (OBS-001, ruling 1).

WHAT IT CHECKS, and why each one is here:

  db                 SELECT 1 through the app's own pool. The API cannot serve
                     a single authenticated request without it.
  migrations         alembic_version equals the head of db/migrations. A deploy
                     that crashed at the version write (C-04) leaves the code
                     ahead of the schema; nothing else notices until a query
                     hits a missing column.
  worker             the newest succeeded worker_heartbeat row is younger than
                     HEARTBEAT_STALE_AFTER_MINUTES. One row proves the worker,
                     its Redis and its DATABASE_URL together, which is why no
                     separate queue-depth inspection is needed.
  queue              app.state.arq_queue exists and Redis answers PING. The
                     September class of failure in the OTHER direction: the API
                     boots healthy with no queue (main.py lifespan) and every
                     request-path enqueue skips silently.
  scheduler          the in-process APScheduler is running. Same lifespan, same
                     silent-boot failure.

PUBLIC, BY RULING (OBS-001 ruling 2), so the workflow needs no secret and a
rotated token cannot make the monitor itself go dark. The price is that the
payload must carry nothing worth reading: booleans, ages, and the two alembic
revision ids. No hostnames, no versions, no identifiers, no error text —
tests/routers/test_health_deep.py pins the exact key set. Failures are logged
at WARNING with the exception type only: the component that failed logs its
own ERROR elsewhere, and an unauthenticated route must not be a way to write
events into Sentry at will.

EVERY CHECK IS TIME-BOXED. A hung pool or an unreachable Redis must produce a
503 in seconds, not a request that hangs until the runner's curl gives up and
reports nothing useful.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from workers.heartbeat import HEARTBEAT_STALE_AFTER_MINUTES, JOB_HEARTBEAT

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Per-check ceiling. Four checks in parallel, so the whole endpoint answers in
# about this long at worst.
CHECK_TIMEOUT_S = 5.0

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _code_head() -> str | None:
    """The single head of db/migrations, read from the files on disk.

    Computed on every call rather than cached at import: it is a directory
    listing, and a cached value would survive a hot reload in development.

    The script location is given ABSOLUTELY, not via alembic.ini: that file's
    `script_location = db/migrations` is resolved against the process's cwd,
    which is apps/api under the Procfile and under pytest and nothing else.
    Caught by calling this from the repo root, not by the tests that ran from
    the directory it happened to work in.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(_API_DIR, "db", "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head()


async def _db_revision() -> str | None:
    """alembic_version.version_num, or None when the table is empty."""
    from sqlalchemy import text

    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()


async def _db_select_one() -> bool:
    from sqlalchemy import text

    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT 1"))).scalar_one() == 1


async def _heartbeat_age_minutes() -> int | None:
    """Minutes since the newest succeeded heartbeat, computed by Postgres.

    now() is the server's clock on both sides of the subtraction, so the answer
    cannot be skewed by this process's clock — the same reason the workflow
    computes it in SQL.
    """
    from sqlalchemy import text

    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        seconds = (await db.execute(
            text(
                "SELECT extract(epoch FROM (now() - max(started_at))) "
                "FROM job_run WHERE job_name = :job AND status = 'succeeded'"
            ),
            {"job": JOB_HEARTBEAT},
        )).scalar_one_or_none()
    return None if seconds is None else int(seconds // 60)


async def _queue_ping(queue) -> bool:
    if queue is None:
        return False
    return bool(await queue.ping())


def _scheduler_running() -> bool:
    from workers.cron import scheduler

    return bool(scheduler.running)


async def _guarded(name: str, coro):
    """Run one check under the ceiling; any failure is False, never a 500."""
    try:
        return await asyncio.wait_for(coro, timeout=CHECK_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 — the whole point is to answer, not raise
        logger.warning("health/deep: %s check failed type=%s", name, type(e).__name__)
        return None


async def deep_health(app_state) -> tuple[int, dict]:
    """(status_code, payload). 200 only when every check is true."""
    queue = getattr(app_state, "arq_queue", None)

    db_ok, revision, heartbeat_age, queue_ok = await asyncio.gather(
        _guarded("db", _db_select_one()),
        _guarded("migrations", _db_revision()),
        _guarded("worker", _heartbeat_age_minutes()),
        _guarded("queue", _queue_ping(queue)),
    )

    try:
        code_head = _code_head()
    except Exception as e:  # noqa: BLE001
        logger.warning("health/deep: code head unreadable type=%s", type(e).__name__)
        code_head = None

    try:
        scheduler_ok = _scheduler_running()
    except Exception as e:  # noqa: BLE001
        logger.warning("health/deep: scheduler check failed type=%s", type(e).__name__)
        scheduler_ok = False

    checks = {
        "db": db_ok is True,
        "migrations_at_head": code_head is not None and revision == code_head,
        "worker_alive": heartbeat_age is not None and heartbeat_age <= HEARTBEAT_STALE_AFTER_MINUTES,
        "queue_reachable": queue_ok is True,
        "scheduler_running": scheduler_ok is True,
    }
    ok = all(checks.values())
    payload = {
        "status": "ok" if ok else "degraded",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **checks,
        "heartbeat_age_minutes": heartbeat_age,
        "heartbeat_stale_after_minutes": HEARTBEAT_STALE_AFTER_MINUTES,
        "db_revision": revision,
        "code_head": code_head,
    }
    return (200 if ok else 503), payload


@router.get("/health/deep")
async def health_deep(request: Request):
    status, payload = await deep_health(request.app.state)
    return JSONResponse(status_code=status, content=payload)
