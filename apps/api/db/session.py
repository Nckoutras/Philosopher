import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import config

# POOL LIVENESS. Added 2026-09-16 after the Supavisor incident.
#
# WHAT BROKE. The connection in front of us is Supavisor in SESSION mode, and it
# reaps its own idle backend on a cleanup timer. The hourly `preview_mirror` job
# (workers/cron.py) leaves its pooled connection idle for ~an hour, so by the
# next tick Supavisor had torn the backend down. The log ordering is the proof —
# "DbHandler: Cleanup timeout, shutting down" at :28:43.788, then the failed
# reconnect and ECHECKOUTFAILED 57ms later. SQLAlchemy had no way to notice: it
# handed out a dead connection and the job failed into its own except block.
#
# pool_pre_ping issues a cheap liveness check before a connection leaves the
# pool and transparently replaces it if the check fails — the direct answer to a
# connection reaped while we held it. pool_recycle retires connections older
# than 5 minutes so the pool is never holding one long enough to be reaped in
# the first place; pre_ping recovers, recycle avoids. They are deliberately both
# here: pre_ping alone would still hand out a reaped connection once per idle
# hour and eat the round trip discovering it.
#
# pool_timeout and max_overflow are LEFT AT THEIR DEFAULTS ON PURPOSE. Nothing
# in the incident evidence pointed at pool exhaustion — Postgres logged no
# connection pressure and checkpoints stayed at 2-113 buffers throughout — so
# tuning them would be a guess dressed as a fix, and raising concurrency against
# a pooler is the wrong direction for a connection-scarcity failure anyway.
engine = create_async_engine(
    config.DATABASE_URL,
    pool_size=config.DATABASE_POOL_SIZE,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=config.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def release_on_exit(body, db: AsyncSession):
    """Wrap an SSE generator that keeps using a request session after get_db closed it.

    THE LEAK THIS CLOSES (OBS-002). On FastAPI 0.115 the get_db teardown — commit,
    then close — runs BEFORE a StreamingResponse body starts (SAFETY-004, measured).
    Four streams (another_mind, go_deeper, council, self-comparison) take that
    session anyway, and their first query silently checks a fresh connection out of
    the pool on the closed session. The generator holds that connection across the
    whole LLM call and returns it only at its own commit at the end.

    When the reader navigates away mid-stream, Starlette cancels the stream task
    through an anyio cancel scope (StreamingResponse.__call__). CancelledError lands
    inside the generator at the LLM await; no commit runs, the generator dies, and
    the session object — held only by that dead frame, kept alive a while longer by
    the traceback cycle — is reclaimed by the CYCLIC garbage collector at some later
    allocation-heavy moment. SQLAlchemy then logs "The garbage collector is trying to
    clean up non-checked-in connection", in whatever request happens to be running:
    on this product that is GET /api/v1/insights, which fires on every app page.
    The Sentry transaction tag named the bystander, not the owner.

    WHY shield(). Under a cancelled anyio scope EVERY await in the task is cancelled
    again, so a plain `await db.close()` in a finally would itself be cut off before
    asyncpg returned the connection — the leak would move one line and stay. shield()
    runs the close in its own task, which the cancel scope does not reach, and that
    task finishes on the loop after this frame is gone. The same `finally` also runs
    when the body completes, raises, or is dropped at a yield and closed by the
    async-generator finalizer; close() on a session with no connection is a no-op.

    The main chat stream does NOT need this: send_message authenticates with
    get_user_plan_streaming and opens its own sessions per phase (auth.py, the "§5
    pool-leak fix"), so it never borrows the request session at all. That is the
    pattern these four should eventually adopt; this wrapper is the narrow fix.
    """
    try:
        if hasattr(body, "__aiter__"):
            async for item in body:
                yield item
        else:
            # StreamingResponse also accepts a plain iterable, and the router tests
            # patch the service streams with one. Production bodies are async.
            for item in body:
                yield item
    finally:
        await asyncio.shield(db.close())
