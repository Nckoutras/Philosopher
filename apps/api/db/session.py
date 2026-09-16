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
