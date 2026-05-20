import asyncio
import json
import time
import logging
import os
from datetime import date
from typing import AsyncGenerator

import anthropic

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models import Conversation, DailyUsage, Message, Persona, SafetyEvent, SavedLine, User
from personas import get_persona, is_persona_accessible
from services.safety_service import safety_service
from services.memory_service import memory_service
from services.retrieval_service import retrieval_service
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.analytics_service import analytics_service
from services.persona_voice import get_error_voice
from services.postprocessing_service import (
    regenerate_or_trim,
    POSTPROCESSING_ENABLED,
)
from services.phenomenology_bridge_service import phenomenology_bridge_service

MODEL_FREE = "claude-haiku-4-5-20251001"
MODEL_PRO = "claude-sonnet-4-6"
MEMORY_WINDOW_FREE = 5
MEMORY_WINDOW_PRO = 20

logger = logging.getLogger(__name__)

SSE_SAFETY_TOKEN = "\n\n[PHILOSOPHER_SAFETY_OVERRIDE]\n\n"

# Phase 4 — Modern Phenomenology Bridge feature flag.
# Default off. Enabled in production via Render env var after smoke test.
PHENOMENOLOGY_BRIDGE_ENABLED = (
    os.getenv("PHENOMENOLOGY_BRIDGE_ENABLED", "false").lower() == "true"
)


class ConversationService:

    # ── Create conversation ───────────────────────────────────────────────────
    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        persona_slug: str,
        ritual_id: str | None = None,
        user_plan: str = "free",
    ) -> Conversation:
        persona_config = get_persona(persona_slug)
        if not persona_config:
            raise ValueError(f"Unknown persona: {persona_slug}")
        if not is_persona_accessible(persona_config, user_plan):
            raise PermissionError(f"Persona {persona_slug} requires plan upgrade")

        # Fetch persona DB record (for FK)
        result = await db.execute(select(Persona).where(Persona.slug == persona_slug))
        persona = result.scalar_one_or_none()
        if not persona:
            raise ValueError(f"Persona {persona_slug} not in database")

        # Return existing empty conversation for this (user, persona, ritual) tuple
        # rather than creating a duplicate row. message_count == 0 means the user
        # has never sent a message (opening invocation does not increment this counter).
        ritual_filter = (
            Conversation.ritual_id.is_(None) if ritual_id is None
            else Conversation.ritual_id == ritual_id
        )
        dedup_result = await db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.persona_id == persona.id,
                Conversation.message_count == 0,
                ritual_filter,
            )
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        existing = dedup_result.scalar_one_or_none()
        if existing:
            return existing

        conv = Conversation(
            user_id=user_id,
            persona_id=persona.id,
            ritual_id=ritual_id,
        )
        db.add(conv)
        await db.flush()

        # Send opening invocation as first assistant message
        if persona_config.opening_invocation:
            opening = Message(
                conversation_id=conv.id,
                user_id=user_id,
                role="assistant",
                content=persona_config.opening_invocation,
            )
            db.add(opening)
        await db.flush()
        return conv

    # ── Create cross-persona conversation ────────────────────────────────────
    async def create_cross_persona(
        self,
        db: AsyncSession,
        user_id: str,
        saved_line_id: str,
        target_persona_slug: str,
    ) -> Conversation:
        """Create a new empty conversation seeded from a saved line.

        Sets source_saved_line_id and source_persona_slug for analytics and
        frontend pre-fill. No bootstrap message is created; the user sends
        the first message after the draft is pre-filled from localStorage.
        """
        # Load saved line + verify ownership
        sl_result = await db.execute(
            select(SavedLine).where(
                SavedLine.id == saved_line_id,
                SavedLine.user_id == user_id,
                SavedLine.deleted_at.is_(None),
            )
        )
        saved_line = sl_result.scalar_one_or_none()
        if not saved_line:
            raise ValueError("Saved line not found")

        # Load source persona (for source_persona_slug)
        src_persona_result = await db.execute(
            select(Persona).where(Persona.id == saved_line.persona_id)
        )
        source_persona = src_persona_result.scalar_one()

        # Load and validate target persona
        tgt_persona_result = await db.execute(
            select(Persona).where(Persona.slug == target_persona_slug)
        )
        target_persona = tgt_persona_result.scalar_one_or_none()
        if not target_persona:
            raise ValueError(f"Persona not found: {target_persona_slug}")
        if target_persona.slug == source_persona.slug:
            raise ValueError("Target persona must differ from source persona")

        # Create the conversation record
        conv = Conversation(
            user_id=user_id,
            persona_id=target_persona.id,
            source_saved_line_id=saved_line_id,
            source_persona_slug=source_persona.slug,
        )
        db.add(conv)
        await db.flush()
        return conv

    # ── Stream response ───────────────────────────────────────────────────────
    async def stream_response(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        user_text: str,
        user_plan: str = "free",
        user_name: str | None = None,
        is_admin: bool = False,
        arq_queue=None,
    ) -> AsyncGenerator[str, None]:
        start = time.monotonic()

        # Load conversation + persona
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise ValueError("Conversation not found")
        persona_result = await db.execute(select(Persona).where(Persona.id == conv.persona_id))
        persona_db = persona_result.scalar_one()
        persona = get_persona(persona_db.slug)

        # ── 1. PRE-GENERATION SAFETY ─────────────────────────────────────────
        safety_in = await safety_service.check_input(user_text, user_id)
        if safety_in.should_log:
            await self._log_safety_event(db, user_id, conversation_id, None, safety_in, "pre_generation")
        if safety_in.should_suppress_persona:
            # Save user message first
            user_msg = await self._save_message(db, conv, user_id, "user", user_text, safety_level=safety_in.level)
            safe_text = prompt_builder.build_safety_response(level=safety_in.level)
            await self._save_message(db, conv, user_id, "assistant", safe_text, safety_level=safety_in.level, persona_override=True)
            await db.commit()
            analytics_service.track("safety_event_pre", user_id, {"risk_level": safety_in.level, "category": safety_in.category})
            yield f"data: {json.dumps({'type': 'safety', 'level': safety_in.level})}\n\n"
            for chunk in self._chunk_text(safe_text):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # ── 2. RECALL MEMORY ─────────────────────────────────────────────────
        memories = []
        try:
            memories = await memory_service.recall(db, user_id, user_text, top_k=6)
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
            await db.rollback()

        # ── 3. RETRIEVE PASSAGES ─────────────────────────────────────────────
        passages = []
        try:
            passages = await retrieval_service.retrieve(db, user_text, persona)
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")
            await db.rollback()

        # ── 3.5. PHENOMENOLOGY BRIDGE LOOKUP (Phase 4) ───────────────────────
        # If a modern term in the user's message maps to a phenomenological
        # essence, the persona will see the timeless translation in its
        # system prompt and engage with that — without naming the modern
        # term back. Feature-flagged; fail-open on any error.
        phenomenology_bridge = None
        if PHENOMENOLOGY_BRIDGE_ENABLED:
            try:
                phenomenology_bridge = phenomenology_bridge_service.lookup(
                    user_message=user_text,
                    persona_slug=persona.slug,
                )
            except Exception as e:
                logger.warning(
                    f"Phenomenology bridge lookup failed for "
                    f"persona={persona.slug}: {e}. Proceeding without bridge."
                )
                # phenomenology_bridge stays None

        # ── 4. BUILD SYSTEM PROMPT ───────────────────────────────────────────
        system_prompt = prompt_builder.build_system(
            persona=persona,
            memories=memories,
            passages=passages,
            phenomenology_bridge=phenomenology_bridge,
        )

        # ── 5. BUILD MESSAGE HISTORY ─────────────────────────────────────────
        history_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(MEMORY_WINDOW_PRO if user_plan in ("pro", "premium") else MEMORY_WINDOW_FREE)
        )
        history = history_result.scalars().all()
        lm_messages = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in ("user", "assistant")
        ]
        # W3 fix: Anthropic API requires messages to start with a user turn.
        # opening_invocation and cross-persona bootstrap both save an initial
        # assistant message with no preceding user message in the DB. Strip any
        # leading assistant turns so the API call is always user-first.
        while lm_messages and lm_messages[0]["role"] == "assistant":
            lm_messages.pop(0)
        lm_messages.append({"role": "user", "content": user_text})

        # ── 6. SAVE USER MESSAGE ─────────────────────────────────────────────
        user_msg = await self._save_message(db, conv, user_id, "user", user_text, safety_level=safety_in.level)
        await db.flush()

        # ── 7. STREAM FROM LLM ───────────────────────────────────────────────
        # Both modes buffer internally so the LLM call can be retried on
        # transient failure. Legacy mode no longer streams in real-time
        # during the LLM call; chunks are yielded after the call succeeds.
        model = MODEL_PRO if user_plan in ("pro", "premium") else MODEL_FREE
        full_response = ""
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        _llm_success = False
        _last_llm_error: Exception | None = None
        for attempt in range(3):
            try:
                _buf: list[str] = []
                async for chunk in llm_client.stream(
                    system=system_prompt, messages=lm_messages, model=model
                ):
                    _buf.append(chunk)
                full_response = "".join(_buf)
                _llm_success = True
                break
            except anthropic.RateLimitError as exc:
                _last_llm_error = exc
                await asyncio.sleep(2**attempt)
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500:
                    _last_llm_error = exc
                    await asyncio.sleep(2**attempt)
                else:
                    _last_llm_error = exc
                    break
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                _last_llm_error = exc
                await asyncio.sleep(2**attempt)

        if not _llm_success:
            persona_voice_text = get_error_voice(persona, "llm_unavailable")
            error_event = {
                "type": "error",
                "error_code": "llm_unavailable",
                "persona_voice": persona_voice_text,
            }
            logger.error(
                f"LLM stream failed for persona={persona.slug}: {_last_llm_error}"
            )
            yield f"data: {json.dumps(error_event)}\n\n"
            await db.commit()
            return

        # ── 8. POST-GENERATION SAFETY ────────────────────────────────────────
        # SAFETY OVERRIDE BYPASS — non-negotiable invariant (Decision D).
        # When safety suppresses the persona, the safety response is sent
        # AS-IS. Postprocessing MUST NOT touch safety override content.
        # Reasons: safety copy must be deterministic; brevity / forbidden
        # rules must never alter safety wording; safety > style, always.
        safety_out = await safety_service.check_output(full_response)
        if safety_out.should_suppress_persona:
            await self._log_safety_event(db, user_id, conversation_id, None, safety_out, "post_generation")
            yield f"data: {json.dumps({'type': 'safety_override', 'level': safety_out.level})}\n\n"
            safe_text = prompt_builder.build_safety_response(level=safety_out.level)
            for chunk in self._chunk_text(safe_text):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            full_response = safe_text
            # NOTE: postprocessing intentionally NOT called in this branch.
            # Safety override is final and immutable.
        elif POSTPROCESSING_ENABLED:
            # ── 8b. POSTPROCESSING (Phase 2, persona reply only) ──────────────
            try:
                conv_position = "first_message" if len(history) <= 1 else "mid_session"
                full_response, _check_history = await regenerate_or_trim(
                    reply=full_response,
                    persona=persona,
                    system_prompt=system_prompt,
                    user_text=user_text,
                    conversation_position=conv_position,
                )
            except Exception as e:
                logger.warning(
                    f"Postprocessing failed for persona={persona.slug}: {e}. "
                    f"Sending original reply (failed-open)."
                )
                # Fall through with unmodified full_response
            # Yield buffered (and possibly postprocessed) content as chunks
            for chunk in self._chunk_text(full_response):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
        else:
            # Legacy mode: LLM response buffered during retry window; yield now.
            for chunk in self._chunk_text(full_response):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"

        latency_ms = int((time.monotonic() - start) * 1000)

        # ── 9. SAVE ASSISTANT MESSAGE ────────────────────────────────────────
        assistant_msg = await self._save_message(
            db, conv, user_id, "assistant", full_response,
            retrieval_ids=[str(p.id) for p in passages],
            safety_level=max(safety_in.level, safety_out.level, key=lambda l: ["none","low","medium","high","critical"].index(l)),
            persona_override=safety_out.should_suppress_persona,
            latency_ms=latency_ms,
        )

        # ── 10. UPDATE CONVERSATION METADATA ────────────────────────────────
        new_message_count = (conv.message_count or 0) + 2
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                message_count=Conversation.message_count + 2,
                last_message_at=user_msg.created_at,
            )
        )

        # ── 10b. INCREMENT DAILY USAGE ───────────────────────────────────────
        # Skip for admins, ritual conversations, and safety-suppressed responses.
        if not is_admin and conv.ritual_id is None and not safety_out.should_suppress_persona:
            today = date.today()
            usage_result = await db.execute(
                select(DailyUsage).where(
                    DailyUsage.user_id == user_id,
                    DailyUsage.persona_id == conv.persona_id,
                    DailyUsage.usage_date == today,
                )
            )
            usage = usage_result.scalar_one_or_none()
            if usage:
                usage.message_count += 1
            else:
                db.add(DailyUsage(
                    user_id=user_id,
                    persona_id=conv.persona_id,
                    usage_date=today,
                    message_count=1,
                ))

        await db.commit()

        if (
            arq_queue is not None
            and new_message_count >= 6
            and conv.title is None
        ):
            await arq_queue.enqueue_job(
                "generate_conversation_title", str(conv.id)
            )

        if arq_queue is not None and not safety_out.should_suppress_persona:
            await arq_queue.enqueue_job(
                "extract_memory_task",
                str(user_id),
                str(conv.id),
                str(conv.persona_id),
                user_text,
                full_response,
                (conv.message_count or 0) // 2,
            )

        # ── 11. ANALYTICS ────────────────────────────────────────────────────
        analytics_service.track("message_sent", user_id, {
            "persona_slug": persona.slug,
            "conversation_id": conversation_id,
            "safety_level": safety_in.level,
            "retrieval_hit": len(passages) > 0,
            "memory_hit": len(memories) > 0,
            "latency_ms": latency_ms,
        })

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id})}\n\n"

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _save_message(
        self, db, conv, user_id, role, content,
        retrieval_ids=None, safety_level="none",
        persona_override=False, latency_ms=None,
    ) -> Message:
        msg = Message(
            conversation_id=conv.id,
            user_id=user_id,
            role=role,
            content=content,
            retrieval_ids=retrieval_ids,
            safety_level=safety_level,
            persona_override=persona_override,
            latency_ms=latency_ms,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def _log_safety_event(self, db, user_id, conversation_id, message_id, safety_result, stage):
        event = SafetyEvent(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            trigger_stage=stage,
            risk_level=safety_result.level,
            category=safety_result.category,
            action_taken="suppressed" if safety_result.should_suppress_persona else "logged",
            raw_flags={"flags": safety_result.raw_flags, "trigger": safety_result.trigger},
        )
        db.add(event)
        await db.flush()

    def _chunk_text(self, text: str, size: int = 20):
        """Split text into small chunks for SSE simulation."""
        for i in range(0, len(text), size):
            yield text[i:i+size]


conversation_service = ConversationService()
