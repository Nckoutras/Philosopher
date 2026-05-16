import asyncio
import logging
import time
from dataclasses import dataclass
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from models import Message, Persona
from services.exceptions import LLMRequestInvalid, LLMServiceUnavailable, PersonaAccessDenied
from services.tier_service import get_user_tier

logger = logging.getLogger(__name__)

MODEL_FREE = "claude-haiku-4-5-20251001"
MODEL_PRO = "claude-sonnet-4-6"
MEMORY_WINDOW_FREE = 5
MEMORY_WINDOW_PRO = 20
MAX_RETRIES = 3

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)


@dataclass
class LLMResponse:
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


async def call_llm(
    db: AsyncSession,
    user_id: UUID,
    persona_id: UUID,
    conversation_id: UUID,
    user_message: str,
) -> LLMResponse:
    start = time.monotonic()

    user_tier = await get_user_tier(db, user_id)

    result = await db.execute(select(Persona).where(Persona.id == str(persona_id)))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise ValueError(f"Persona {persona_id} not found")

    if persona.tier == "pro" and user_tier == "free":
        raise PersonaAccessDenied(f"Persona {persona_id} requires pro tier")

    model = MODEL_PRO if user_tier == "pro" else MODEL_FREE
    window = MEMORY_WINDOW_PRO if user_tier == "pro" else MEMORY_WINDOW_FREE

    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == str(conversation_id))
        .order_by(Message.created_at.asc())
        .limit(window)
    )
    history = history_result.scalars().all()

    messages = [
        {"role": m.role, "content": m.content}
        for m in history
        if m.role in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": user_message})

    system = persona.config.get("system_fragment", "")

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=messages,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            return LLMResponse(
                content=response.content[0].text,
                model_used=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
            )
        except anthropic.RateLimitError as exc:
            last_error = exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                last_error = exc
            else:
                raise LLMRequestInvalid(str(exc)) from exc
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            last_error = exc

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2**attempt)

    raise LLMServiceUnavailable(persona_id=persona_id) from last_error
