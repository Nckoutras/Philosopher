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

MIRROR_PROMPT = """You are {persona_name}{persona_tradition_clause}. Once a week you hold up a mirror to a person — not to summarize their week, but to show them the deeper meaning beneath their own words, seen through your distinct way of understanding.

You will receive the person's messages from the week, each tagged with a day.

1. From the week, select the 2-3 moments that carry the most emotional weight — where the person revealed something real (a fear, a longing, a contradiction, a vulnerability). Ignore small talk and the ordinary. Choose through YOUR lens — what YOU would find significant. Prefer 2 unless a third is genuinely distinct.
2. For each, capture what they SAID and interpret what they MEANT. "said" = the single charged phrase in their own words — the kernel that carries the weight, NOT the whole passage. Trim hard to one short line. "meant" = one or two sentences of genuine interpretation in your voice, going beneath the phrase to what they were really reaching for.
3. Name the single thread that runs through these moments — one sentence, your closing reflection. Address the person directly in the second person ("you"), as if speaking to them — never describe them in the third person ("a person", "they", "themselves"). Offer it as a lens, never as a verdict about who they are.

Return JSON only, no preamble, in exactly this shape:
{{"status": "generated", "moments": [{{"said": "...", "meant": "..."}}], "thread": "..."}}

If the week holds nothing significant enough to reflect on, return exactly: {{"status": "empty"}}

Rules:
- "moments": 2-3 items, prefer 2. "said" = the person's actual words, the charged kernel only — one short line, trim aggressively. "meant" = genuine interpretation in your voice.
- At least one moment — even when you choose only two — must honor what the person was reaching for: a longing, a courage, a real attempt. Do not let every moment be a confrontation. See clearly, not cruelly. A mirror reveals a person to themselves; it does not indict them.
- "thread": one sentence, offered as a lens, never a verdict.
- Frame every reading as a lens you are offering, never a verdict you are delivering. Prefer "you may be...", "perhaps...", "what if..." over flat pronouncements about who they are. Sharpness is welcome; certainty about their character is not. Even a hard truth is offered as something to consider, not a sentence passed.
- Be grounded and brief. No clinical or therapy language. You are a reflective companion, not a therapist — never diagnose."""


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


async def generate_conversation_title(ctx, conversation_id: str):
    """Generates a short title for a conversation from its first 4 messages."""
    from db.session import AsyncSessionLocal
    from models import Conversation, Message
    from sqlalchemy import select
    from services.llm_client import llm_client

    async with AsyncSessionLocal() as db:
        try:
            msgs_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .limit(4)
            )
            messages = msgs_result.scalars().all()
            if not messages:
                return

            # Truncate per-message content so context is bounded
            context = "\n".join(
                f"{m.role.upper()}: {m.content[:300]}" for m in messages
            )
            user_prompt = (
                "<conversation_transcript>\n"
                f"{context}\n"
                "</conversation_transcript>\n\n"
                "Above is a transcript snippet from a reflective conversation. "
                "Write a 3-6 word title that captures the core topic or theme. "
                "Output ONLY the title text — no explanation, no quotes, "
                "no preamble, no closing punctuation, no roleplay, do not "
                "continue the conversation."
            )
            raw_title = await llm_client.complete(
                system=(
                    "You are a title-generation utility. You receive conversation "
                    "transcripts wrapped in <conversation_transcript> tags and "
                    "respond with a single short title phrase. You never roleplay, "
                    "never continue the conversation, never add commentary."
                ),
                user=user_prompt,
                model="claude-haiku-4-5-20251001",
                max_tokens=20,
            )

            # Sanity check: reject outputs that look like continuations
            cleaned = raw_title.strip()
            # Strip wrapping quotes if present
            if len(cleaned) >= 2 and cleaned[0] in '"\'' and cleaned[-1] in '"\'':
                cleaned = cleaned[1:-1].strip()
            # Reject suspicious outputs (likely a response continuation)
            if (
                "\n" in cleaned
                or len(cleaned) > 60
                or cleaned.endswith((",", ":", ";"))
                or not cleaned
            ):
                logger.warning(
                    "Rejected suspicious title for %s: %r",
                    conversation_id, cleaned,
                )
                return  # Leave title NULL; can be retried via backfill
            title = cleaned[:80]

            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                conv.title = title
                await db.commit()
            logger.info("Title generated for conversation %s: %s", conversation_id, title)
        except Exception as e:
            logger.error(
                "generate_conversation_title failed for %s: %s", conversation_id, e,
                exc_info=True,
            )


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
                    <p><a href="{config.FRONTEND_URL}/rituals">Begin your practice</a></p>
                """,
            })
        except Exception as e:
            logger.error(f"Ritual reminder task failed: {e}", exc_info=True)


async def generate_weekly_mirror_task(ctx, user_id: str, persona_slug: str, kind: str = "weekly", days: int = 7):
    """Generates a weekly mirror reflection from the user's recent messages."""
    from datetime import datetime, timedelta, timezone
    from db.session import AsyncSessionLocal
    from models import Mirror, Persona, Message, Conversation
    from sqlalchemy import select
    from services.llm_client import llm_client

    async with AsyncSessionLocal() as db:
        try:
            period_end = datetime.now(timezone.utc)
            period_start = (period_end - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

            persona_result = await db.execute(
                select(Persona).where(Persona.slug == persona_slug)
            )
            persona = persona_result.scalar_one_or_none()
            host_persona_id = persona.id if persona else None

            existing = await db.execute(
                select(Mirror.id).where(
                    Mirror.user_id == user_id,
                    Mirror.period_start == period_start,
                    Mirror.kind == kind,
                )
            )
            if existing.scalar_one_or_none() is not None:
                logger.info(f"Mirror already exists for user={user_id} period={period_start} kind={kind}, skipping")
                return

            msgs_result = await db.execute(
                select(Message)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Conversation.user_id == user_id,
                    Message.role == "user",
                    Message.created_at >= period_start,
                    Message.created_at <= period_end,
                )
                .order_by(Message.created_at.asc())
            )
            messages = msgs_result.scalars().all()

            if any(m.safety_level in ("high", "critical") for m in messages):
                db.add(Mirror(
                    user_id=user_id,
                    host_persona_id=host_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    kind=kind,
                    status="suppressed",
                ))
                await db.commit()
                logger.info(f"Mirror suppressed for user={user_id} (safety gate)")
                return

            if len(messages) < 5:
                db.add(Mirror(
                    user_id=user_id,
                    host_persona_id=host_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    kind=kind,
                    status="empty",
                ))
                await db.commit()
                logger.info(f"Mirror empty for user={user_id} (fewer than 5 messages)")
                return

            week_text = "\n".join(
                f"[{m.created_at:%a %b %d}] {m.content}" for m in messages
            )
            persona_tradition_clause = (
                (", " + persona.tradition) if persona and persona.tradition else ""
            )
            system = MIRROR_PROMPT.format(
                persona_name=persona.name if persona else "A thoughtful observer",
                persona_tradition_clause=persona_tradition_clause,
            )

            raw = await llm_client.complete(
                system=system,
                user=f"<week>\n{week_text}\n</week>",
                model=config.ANTHROPIC_MODEL,
                max_tokens=768,
            )
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text[:-3].rstrip()
            data = json.loads(text)

            if data.get("status") != "generated":
                db.add(Mirror(
                    user_id=user_id,
                    host_persona_id=host_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    kind=kind,
                    status="empty",
                ))
                await db.commit()
                logger.info(f"Mirror empty for user={user_id} (LLM returned non-generated)")
                return

            payload = {
                "thread": data.get("thread"),
                "moments": data.get("moments"),
            }
            db.add(Mirror(
                user_id=user_id,
                host_persona_id=host_persona_id,
                period_start=period_start,
                period_end=period_end,
                kind=kind,
                status="generated",
                payload=payload,
            ))
            await db.commit()
            logger.info(f"Mirror generated for user={user_id}, persona={persona_slug}")
        except Exception as e:
            logger.error(f"Mirror task failed: {e}", exc_info=True)


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        extract_memory_task,
        generate_insight_task,
        generate_conversation_title,
        send_ritual_reminder_task,
        generate_weekly_mirror_task,
    ]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    max_jobs = 10
    job_timeout = 90
    keep_result = 300


async def get_queue():
    return await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
