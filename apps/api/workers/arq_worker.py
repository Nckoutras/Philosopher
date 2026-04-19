import json
import logging
from arq import create_pool
from arq.connections import RedisSettings
from config import config

logger = logging.getLogger(__name__)

# ── Prompts ───────────────────────────────────────────────────────────────────

INSIGHT_PROMPT = """You are an insight generation system for a philosophical companion app.

Given a list of memory entries about a user, identify one meaningful pattern, contradiction, or shift
worth surfacing to the user.

Return JSON only: {"content": "...", "insight_type": "pattern|shift|question|challenge"}
- content: 1-3 sentences. Thoughtful, non-clinical, grounded. No therapy-speak.
- insight_type: choose the most accurate.

Return null if there is no meaningful insight to surface.
Example: {"content": "You often describe ambition as a burden rather than a desire. That tension may be worth examining.", "insight_type": "pattern"}"""


# ── Tasks ─────────────────────────────────────────────────────────────────────

async def extract_memory_task(
    ctx,
    user_id: str,
    conversation_id: str,
    persona_id: str,
    user_text: str,
    assistant_text: str,
    turn: int = 0,
):
    """Extracts and stores memory entries after each message pair."""
    from db.session import AsyncSessionLocal
    from services.memory_service import memory_service

    async with AsyncSessionLocal() as db:
        try:
            entries = await memory_service.extract_and_store(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                persona_id=persona_id,
                user_text=user_text,
                assistant_text=assistant_text,
                source_turn=turn,
            )
            await db.commit()
            logger.info(f"Memory task: stored {len(entries)} entries for user={user_id}")
        except Exception as e:
            logger.error(f"Memory task failed: {e}", exc_info=True)


async def generate_insight_task(ctx, user_id: str, conversation_id: str):
    """Generates an insight from recent memory entries."""
    from db.session import AsyncSessionLocal
    from models import MemoryEntry, Insight
    from sqlalchemy import select
    from services.llm_client import llm_client

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(MemoryEntry)
                .where(MemoryEntry.user_id == user_id, MemoryEntry.is_active == True)
                .order_by(MemoryEntry.created_at.desc())
                .limit(15)
            )
            memories = result.scalars().all()
            if len(memories) < 4:
                return  # Not enough signal yet

            memory_text = "\n".join(
                f"[{m.entry_type}] {m.content}" for m in memories
            )
            raw = await llm_client.complete(
                system=INSIGHT_PROMPT,
                user=memory_text,
                max_tokens=256,
            )
            if raw.strip().lower() == "null":
                return

            data = json.loads(raw.strip())
            insight = Insight(
                user_id=user_id,
                conversation_id=conversation_id,
                content=data["content"],
                insight_type=data.get("insight_type"),
            )
            db.add(insight)
            await db.commit()
            logger.info(f"Insight generated for user={user_id}")
        except Exception as e:
            logger.error(f"Insight task failed: {e}", exc_info=True)


async def send_ritual_reminder_task(ctx, user_id: str, ritual_id: str):
    """Sends ritual reminder email via Resend."""
    from db.session import AsyncSessionLocal
    from models import User, Ritual
    from sqlalchemy import select
    import resend

    resend.api_key = config.RESEND_API_KEY

    async with AsyncSessionLocal() as db:
        try:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            ritual_result = await db.execute(select(Ritual).where(Ritual.id == ritual_id))
            ritual = ritual_result.scalar_one_or_none()
            if not user or not ritual:
                return

            resend.Emails.send({
                "from": config.FROM_EMAIL,
                "to": user.email,
                "subject": f"Your daily ritual: {ritual.name}",
                "html": f"""
                    <p>Good morning{f", {user.full_name.split()[0]}" if user.full_name else ""}.</p>
                    <p>Your ritual <strong>{ritual.name}</strong> is waiting for you.</p>
                    <p><a href="{config.BASE_URL}/rituals">Begin your practice</a></p>
                """,
            })
        except Exception as e:
            logger.error(f"Ritual reminder task failed: {e}", exc_info=True)


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        extract_memory_task,
        generate_insight_task,
        send_ritual_reminder_task,
    ]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    max_jobs = 10
    job_timeout = 90
    keep_result = 300


async def get_queue():
    return await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
