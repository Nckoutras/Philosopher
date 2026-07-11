import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.session import engine, Base
from config import config

# Import all models so Alembic sees them
import models  # noqa: F401

from routers.auth import router as auth_router
from routers.auth_oauth import router as auth_oauth_router
from routers.conversations import router as conversations_router
from routers.personas import router as personas_router
from routers.memory import memory_router, insights_router
from routers.billing import router as billing_router
from routers.admin import router as admin_router
from routers.rituals import router as rituals_router
from routers.disclaimer import router as disclaimer_router
from routers.preferences import router as preferences_router
from routers.saved_lines import router as saved_lines_router
from routers.reflections import router as reflections_router
from routers.home import router as home_router
from routers.share import router as share_router
from routers.scheduled_emails import router as scheduled_emails_router
from routers.mirrors import router as mirrors_router
from routers.council import router as council_router
from routers.counterview import router as counterview_router
from routers.self_comparison import router as self_comparison_router
from routers.weekly_letters import router as weekly_letters_router
from routers.unsubscribe import router as unsubscribe_router
from routers.quotes import router as quotes_router

logging.basicConfig(level=logging.INFO if not config.DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Philosopher API [{config.ENV}]")
    if config.BETA_GRANT_PRO_TO_ALL:
        logger.warning("⚠️ BETA_GRANT_PRO_TO_ALL is ENABLED — all users granted Pro tier. Disable before production launch.")

    # In dev: create tables. In prod: use Alembic migrations.
    if config.ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Start ARQ queue + cron scheduler
    arq_queue = None
    try:
        from workers.arq_worker import get_queue
        from workers.cron import setup_cron
        arq_queue = await get_queue()
        app.state.arq_queue = arq_queue
        setup_cron(arq_queue)
        logger.info("ARQ queue and cron scheduler ready")
    except Exception as e:
        logger.warning(f"ARQ/cron startup failed (non-fatal in dev without Redis): {e}")

    yield

    # Shutdown
    from workers.cron import shutdown_cron
    shutdown_cron()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Philosopher API",
    version="0.1.0",
    docs_url="/docs" if config.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],

)

PREFIX = "/api/v1"
app.include_router(auth_router,          prefix=PREFIX)
app.include_router(auth_oauth_router,    prefix=PREFIX)
app.include_router(personas_router,      prefix=PREFIX)
app.include_router(conversations_router, prefix=PREFIX)
app.include_router(memory_router,        prefix=PREFIX)
app.include_router(insights_router,      prefix=PREFIX)
app.include_router(billing_router,       prefix=PREFIX)
app.include_router(rituals_router,       prefix=PREFIX)
app.include_router(admin_router,         prefix=PREFIX)
app.include_router(disclaimer_router,    prefix=PREFIX)
app.include_router(preferences_router,   prefix=PREFIX)
app.include_router(saved_lines_router,   prefix=PREFIX)
app.include_router(reflections_router,   prefix=PREFIX)
app.include_router(home_router,          prefix=PREFIX)
app.include_router(share_router,              prefix=PREFIX)
app.include_router(scheduled_emails_router,   prefix=PREFIX)
app.include_router(mirrors_router,            prefix=PREFIX)
app.include_router(council_router,            prefix=PREFIX)
app.include_router(counterview_router,        prefix=PREFIX)
app.include_router(self_comparison_router,    prefix=PREFIX)
app.include_router(weekly_letters_router,     prefix=PREFIX)
app.include_router(unsubscribe_router,         prefix=PREFIX)
app.include_router(quotes_router,              prefix=PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "env": config.ENV}
