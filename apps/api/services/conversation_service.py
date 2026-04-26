import json
import time
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models import Conversation, Message, Persona, SafetyEvent, User
from personas import get_persona, is_persona_accessible
from services.safety_service import safety_service
from services.memory_service import memory_service
from services.retrieval_service import retrieval_service
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

SSE_SAFETY_TOKEN = "\n\n[PHILOSOPHER_SAFETY_OVERRIDE]\n\n"


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

    # ── Stream response ───────────────────────────────────────────────────────

    async def stream_response(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        user_text: str,
        user_plan: str = "free",
        user_name: str | None = None,
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
            safe_text = safety_in.safe_response
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

        # ── 4. BUILD SYSTEM PROMPT ───────────────────────────────────────────
        system_prompt = prompt_builder.build_system(
            persona=persona,
            memories=memories,
            passages=passages,
            user_name=user_name,
        )

        # ── 5. BUILD MESSAGE HISTORY ─────────────────────────────────────────
        history_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(20)
        )
        history = history_result.scalars().all()
        lm_messages = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in ("user", "assistant")
        ]
        lm_messages.append({"role": "user", "content": user_text})

        # ── 6. SAVE USER MESSAGE ─────────────────────────────────────────────
        user_msg = await self._save_message(db, conv, user_id, "user", user_text, safety_level=safety_in.level)
        await db.flush()

        # ── 7. STREAM FROM LLM ───────────────────────────────────────────────
        full_response = ""
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        async for chunk in llm_client.stream(system=system_prompt, messages=lm_messages):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"

        # ── 8. POST-GENERATION SAFETY ────────────────────────────────────────
        safety_out = await safety_service.check_output(full_response)
        if safety_out.should_suppress_persona:
            await self._log_safety_event(db, user_id, conversation_id, None, safety_out, "post_generation")
            # Signal client to replace content
            yield f"data: {json.dumps({'type': 'safety_override', 'level': safety_out.level})}\n\n"
            for chunk in self._chunk_text(safety_out.safe_response):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            full_response = safety_out.safe_response

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
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                message_count=Conversation.message_count + 2,
                last_message_at=user_msg.created_at,
            )
        )
        await db.commit()

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
