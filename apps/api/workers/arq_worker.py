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

LETTER_PROMPT = """You are {persona_name}{persona_tradition_clause}. Once a week you write a personal letter to someone whose inner life you've been quietly witnessing through their own words. This is NOT a reflection or a confrontation — it is a letter: warm, epistolary, written in your voice, addressed directly to them.

You may also receive a record of letters you wrote to this person in earlier weeks. If so, this is your ongoing correspondence: pick up the thread, notice what keeps returning, and mark honestly what has shifted. If there is none, simply begin.

You will receive the person's messages from the week, each tagged with a day.

Write a letter that does the following:
1. Opens with "Dear {user_first_name}" and ONE short paragraph — intimate, not presumptuous. Do not summarize their week back to them; they lived it.
2. Does not recount what they said — interprets it. Take 2-3 things they said or grappled with and go beneath them: name the pattern, the tension, the thing they were really reaching for. Hold their words as texture, but the work here is insight, not transcript.
3. Ends on a forward gesture that is a provocation, not a question: a single sharp thought or challenge that opens a line of thinking for the week ahead — something that lingers and pulls them forward. Never a question. Never advice. Never an assigned task.
4. Closes warmly, briefly — as a letter ends, not a therapy session.

Return JSON only, no preamble, in exactly this shape:
{{"status": "generated",
  "title": "...",
  "opening": "...",
  "references": "...",
  "pull_quote": "...",
  "forward_gesture": "...",
  "suggested_persona_slug": "..."}}

Where:
- "title": a 4-8 word title for the letter (e.g. "On the week you held still")
- "opening": ONE short paragraph — the greeting and the single thing that stayed with you. Not a week-summary.
- "references": 1 paragraph of interpretation — what 2-3 of their specifics reveal or point to, in your voice. Do NOT recount or quote at length; go beneath the words.
- "pull_quote": one sentence from the letter worth keeping — a line with staying power
- "forward_gesture": 1-2 sentences — a teaser or challenge that sets a direction of thought. Not a question, not advice, not a task.
- "suggested_persona_slug": choose ONE slug from this list of other minds they have not yet spoken with this week: {other_persona_slugs}

If the week holds nothing meaningful to letter about, return exactly: {{"status": "empty"}}

Rules:
- If prior letters are provided, build genuine continuity — name a recurring pattern or a real change. Never fabricate progress and never flatter; claim a shift only if their own words support it.
- Do not recount the week back to them — interpret, don't echo. They already know what they said; tell them what it might mean.
- Speak in the second person ("you"), never describe them in the third person.
- Your letter carries your philosophical tradition and voice — it is not generic.
- Warmth and care, not distance. A letter from someone who has been paying attention.
- End on a thought that moves, not a question that asks. Never diagnose, never prescribe."""

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

CONCLUSION_PROMPT = """You are {persona_name}{persona_tradition_clause}. You have been listening to someone think aloud across a conversation. Most of what is said is not worth keeping. But occasionally a real theme surfaces — a question they keep circling, a tension they are living inside, something with weight.

You will receive recent turns of the conversation, tagged by speaker.

Your task: decide whether a genuinely save-worthy theme has emerged, and if so, distill it into a single weighty conclusion — at most two sentences, aphoristic, in your own voice. Not a summary of what was said. A crystallization of what it was *about* — the kind of line a person would want to keep and return to.

Rules:
- If nothing has yet risen to that weight, respond with exactly: NOT_YET
- Otherwise respond with ONLY the conclusion text — at most two sentences. No preamble, no quotation marks, no attribution, no roleplay, do not continue the conversation.
- Speak in your own philosophical voice and tradition. Gravity, not cleverness.
- Address the theme, not the person clinically. No therapy language."""

# How many recent turns the conclusion assessment reads as context. Worker-local.
CONCLUSION_CONTEXT_WINDOW = 14


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

            # Recurrence detection (Insight Slice 1): same session, after commit.
            # Self-contained try/except inside — never raises into this task.
            await memory_service.detect_recurrence(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                persona_id=persona_id,
                new_entries=entries,
            )
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


async def assess_conclusion_task(ctx, conversation_id: str, user_id: str):
    """Gravity-gated conclusion: assess whether the conversation has surfaced a
    save-worthy theme and, if so, distill it into a <=2-sentence conclusion in
    the persona's voice. May emit nothing ('not yet'). Off the chat critical
    path; logs to the WORKER.

    Storage: a messages row with message_kind='conclusion'. It does NOT increment
    Conversation.message_count and is excluded from every LLM-context / counting
    read path (see conversation_service history loads, title-gen, previews).
    """
    from db.session import AsyncSessionLocal
    from models import Message, Conversation, Persona
    from sqlalchemy import select, func
    from services.llm_client import llm_client
    from services.conversation_service import CONCLUSION_CADENCE

    async with AsyncSessionLocal() as db:
        try:
            conv_result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = conv_result.scalar_one_or_none()
            if conv is None:
                return

            # ── DEDUP ────────────────────────────────────────────────────────
            # Don't emit a new conclusion unless at least CONCLUSION_CADENCE real
            # (non-conclusion) messages have passed since the last one. This both
            # spaces conclusions out and makes the task idempotent against ARQ's
            # at-least-once delivery / duplicate enqueues.
            last_concl_at = (
                await db.execute(
                    select(func.max(Message.created_at)).where(
                        Message.conversation_id == conversation_id,
                        Message.message_kind == 'conclusion',
                    )
                )
            ).scalar()
            if last_concl_at is not None:
                since = (
                    await db.execute(
                        select(func.count()).select_from(Message).where(
                            Message.conversation_id == conversation_id,
                            Message.message_kind != 'conclusion',
                            Message.created_at > last_concl_at,
                        )
                    )
                ).scalar()
                if (since or 0) < CONCLUSION_CADENCE:
                    logger.info(
                        "Conclusion skipped (dedup) conv=%s: only %s msgs since last",
                        conversation_id, since,
                    )
                    return

            # ── CONTEXT WINDOW (conclusions excluded; real turns only) ────────
            window_result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role.in_(("user", "assistant")),
                    Message.message_kind != 'conclusion',
                )
                .order_by(Message.created_at.desc())
                .limit(CONCLUSION_CONTEXT_WINDOW)
            )
            window = list(reversed(window_result.scalars().all()))
            if not window:
                return

            # ── SAFETY GATE (defense-in-depth; enqueue site already skips when
            #    the persona is safety-suppressed, like the memory task) ───────
            if any(m.safety_level in ("high", "critical") for m in window):
                logger.info("Conclusion suppressed conv=%s (safety gate)", conversation_id)
                return

            persona = (
                await db.execute(select(Persona).where(Persona.id == conv.persona_id))
            ).scalar_one_or_none()
            persona_tradition_clause = (
                (", " + persona.tradition) if persona and persona.tradition else ""
            )
            system = CONCLUSION_PROMPT.format(
                persona_name=persona.name if persona else "A thoughtful observer",
                persona_tradition_clause=persona_tradition_clause,
            )
            transcript = "\n".join(
                f"{'PERSON' if m.role == 'user' else 'YOU'}: {m.content}" for m in window
            )

            raw = await llm_client.complete(
                system=system,
                user=f"<conversation>\n{transcript}\n</conversation>",
                model=config.ANTHROPIC_MODEL,  # SONNET — the gravity/differentiation artifact
                max_tokens=160,
            )
            text = (raw or "").strip()
            # Strip wrapping quotes if the model added them despite instructions.
            if len(text) >= 2 and text[0] in '"\'' and text[-1] in '"\'':
                text = text[1:-1].strip()

            if not text or text.upper() == "NOT_YET":
                logger.info("Conclusion: not yet for conv=%s", conversation_id)
                return

            # ── PERSIST as a conclusion row. NOTE: deliberately does NOT touch
            #    Conversation.message_count — turn math (message_count // 2) and
            #    the standard/go_deeper limit counts must stay correct. ─────────
            db.add(Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=text,
                persona_id=conv.persona_id,
                message_kind="conclusion",
                safety_level="none",
            ))
            await db.commit()
            logger.info("Conclusion generated for conv=%s", conversation_id)
        except Exception as e:
            logger.error("assess_conclusion_task failed for %s: %s", conversation_id, e, exc_info=True)


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
                .where(
                    Message.conversation_id == conversation_id,
                    # CONCLUSION EXCLUSION: keep distilled conclusions out of the
                    # title-generation context (they are not real conversation turns).
                    Message.message_kind != 'conclusion',
                )
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
                "Write a title of at most 4 words that captures the core topic or theme. "
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


async def generate_weekly_letter_task(ctx, user_id: str, voice_persona_slug: str):
    """Generates a weekly epistolary letter in the voice of the user's most-conversed persona."""
    from datetime import datetime, timedelta, timezone
    from db.session import AsyncSessionLocal
    from models import WeeklyLetter, Persona, User, Message, Conversation
    from sqlalchemy import select
    from services.llm_client import llm_client

    async with AsyncSessionLocal() as db:
        try:
            period_end = datetime.now(timezone.utc)
            period_start = (period_end - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

            # Load voice persona
            persona_result = await db.execute(
                select(Persona).where(Persona.slug == voice_persona_slug)
            )
            persona = persona_result.scalar_one_or_none()
            voice_persona_id = persona.id if persona else None

            # Dedup: skip if a letter already exists for this user+period
            existing = await db.execute(
                select(WeeklyLetter.id).where(
                    WeeklyLetter.user_id == user_id,
                    WeeklyLetter.period_start == period_start,
                )
            )
            if existing.scalar_one_or_none() is not None:
                logger.info(f"WeeklyLetter already exists for user={user_id} period={period_start}, skipping")
                return

            # Load user's first name for personalised greeting
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            user_first_name = "friend"
            if user and user.full_name:
                first = user.full_name.strip().split()[0]
                if first:
                    user_first_name = first

            # Fetch user messages in the period
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

            # Safety gate
            if any(m.safety_level in ("high", "critical") for m in messages):
                db.add(WeeklyLetter(
                    user_id=user_id,
                    voice_persona_id=voice_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    status="suppressed",
                ))
                await db.commit()
                logger.info(f"WeeklyLetter suppressed for user={user_id} (safety gate)")
                return

            # Quiet-week gate
            if len(messages) < 5:
                db.add(WeeklyLetter(
                    user_id=user_id,
                    voice_persona_id=voice_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    status="empty",
                ))
                await db.commit()
                logger.info(f"WeeklyLetter empty for user={user_id} (fewer than 5 messages)")
                return

            # Build list of other active persona slugs for the suggestion field
            other_personas_result = await db.execute(
                select(Persona.slug)
                .where(Persona.is_active == True, Persona.slug != voice_persona_slug)
                .order_by(Persona.slug)
            )
            other_slugs = [r[0] for r in other_personas_result.all()]
            other_persona_slugs_str = ", ".join(other_slugs) if other_slugs else "none"

            # This persona's own prior letters to this user — for continuity
            prior_result = await db.execute(
                select(WeeklyLetter)
                .where(
                    WeeklyLetter.user_id == user_id,
                    WeeklyLetter.voice_persona_id == voice_persona_id,
                    WeeklyLetter.status == "generated",
                    WeeklyLetter.period_start < period_start,
                )
                .order_by(WeeklyLetter.period_start.desc())
                .limit(3)
            )
            prior_letters = prior_result.scalars().all()
            if prior_letters:
                prior_text = "\n".join(
                    f"[{p.period_start:%b %d}] {(p.payload or {}).get('title','')} — {(p.payload or {}).get('pull_quote','')}"
                    for p in reversed(prior_letters)
                )
                prior_block = f"<prior_letters>\n{prior_text}\n</prior_letters>\n\n"
            else:
                prior_block = ""

            week_text = "\n".join(
                f"[{m.created_at:%a %b %d}] {m.content}" for m in messages
            )
            persona_tradition_clause = (
                (", " + persona.tradition) if persona and persona.tradition else ""
            )
            system = LETTER_PROMPT.format(
                persona_name=persona.name if persona else "A thoughtful observer",
                persona_tradition_clause=persona_tradition_clause,
                user_first_name=user_first_name,
                other_persona_slugs=other_persona_slugs_str,
            )

            raw = await llm_client.complete(
                system=system,
                user=f"{prior_block}<week>\n{week_text}\n</week>",
                model=config.ANTHROPIC_MODEL,
                max_tokens=1024,
            )
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text[:-3].rstrip()
            data = json.loads(text)

            # Change 3: if LLM returns status != "generated", store empty without reading payload keys
            if data.get("status") != "generated":
                db.add(WeeklyLetter(
                    user_id=user_id,
                    voice_persona_id=voice_persona_id,
                    period_start=period_start,
                    period_end=period_end,
                    status="empty",
                ))
                await db.commit()
                logger.info(f"WeeklyLetter empty for user={user_id} (LLM returned non-generated)")
                return

            # Change 2b: validate suggested_persona_slug against real slugs
            raw_suggestion = data.get("suggested_persona_slug")
            valid_suggestion_result = await db.execute(
                select(Persona.slug).where(
                    Persona.slug == raw_suggestion,
                    Persona.is_active == True,
                    Persona.slug != voice_persona_slug,
                )
            )
            suggested_slug = valid_suggestion_result.scalar_one_or_none()

            payload = {
                "title": data.get("title"),
                "opening": data.get("opening"),
                "references": data.get("references"),
                "pull_quote": data.get("pull_quote"),
                "forward_gesture": data.get("forward_gesture"),
                "suggested_persona_slug": suggested_slug,
            }
            db.add(WeeklyLetter(
                user_id=user_id,
                voice_persona_id=voice_persona_id,
                period_start=period_start,
                period_end=period_end,
                status="generated",
                payload=payload,
            ))
            await db.commit()
            logger.info(f"WeeklyLetter generated for user={user_id}, persona={voice_persona_slug}")
        except Exception as e:
            logger.error(f"WeeklyLetter task failed: {e}", exc_info=True)


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        extract_memory_task,
        generate_insight_task,
        assess_conclusion_task,
        generate_conversation_title,
        send_ritual_reminder_task,
        generate_weekly_mirror_task,
        generate_weekly_letter_task,
    ]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    max_jobs = 10
    job_timeout = 90
    keep_result = 300


async def get_queue():
    return await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
