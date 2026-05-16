import logging
import uuid as _uuid
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user
from db.session import get_db
from models import Conversation, DailyUsage, Message, Persona
from schemas import (
    ConversationSummary,
    LLMErrorResponse,
    MessageCreateRequest,
    MessageEnvelope,
    MessageResponse,
)
from services.exceptions import LLMRequestInvalid, LLMServiceUnavailable, PersonaAccessDenied
from services.persona_voice import get_error_voice
from services.tier_service import get_user_tier
import services.llm_service as llm_service_module
import services.rate_limit_service as rate_limit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageEnvelope)
async def send_message(
    request: Request,
    response: Response,
    body: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # Load persona
    persona_result = await db.execute(
        select(Persona).where(Persona.id == body.persona_id)
    )
    persona = persona_result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Load or create conversation
    if body.conversation_id is not None:
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.user_id == user.id,
                Conversation.deleted_at.is_(None),
            )
        )
        conv = conv_result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.persona_id != body.persona_id:
            raise HTTPException(
                status_code=400,
                detail="Persona ID does not match conversation",
            )
    else:
        conv = Conversation(
            id=str(_uuid.uuid4()),
            user_id=user.id,
            persona_id=body.persona_id,
        )
        db.add(conv)
        await db.flush()

    # Validate persona access before saving user message
    user_tier = await get_user_tier(db, user.id)
    if persona.tier == "pro" and user_tier == "free":
        raise HTTPException(
            status_code=403,
            detail=LLMErrorResponse(
                error_code="persona_locked",
                persona_voice=get_error_voice(persona, "persona_locked"),
            ).model_dump(),
        )

    # Enforce daily message limit for free tier
    rate_limit_result = await rate_limit_service.check_rate_limit(
        db, UUID(user.id), UUID(body.persona_id), user_tier=user_tier
    )
    if not rate_limit_result.allowed:
        return JSONResponse(
            status_code=429,
            content=LLMErrorResponse(
                error_code="rate_limited",
                persona_voice=get_error_voice(persona, "rate_limited"),
            ).model_dump(),
            headers={
                "X-RateLimit-Limit": str(rate_limit_result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": rate_limit_result.reset_at.isoformat(),
            },
        )

    # Insert user message
    user_msg = Message(
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # Call LLM service — commit user message on any failure so user can retry
    try:
        llm_response = await llm_service_module.call_llm(
            db=db,
            user_id=UUID(user.id),
            persona_id=UUID(body.persona_id),
            conversation_id=UUID(conv.id),
            user_message=body.content,
        )
    except PersonaAccessDenied:
        await db.commit()
        raise HTTPException(
            status_code=403,
            detail=LLMErrorResponse(
                error_code="persona_locked",
                persona_voice=get_error_voice(persona, "persona_locked"),
            ).model_dump(),
        )
    except LLMServiceUnavailable:
        await db.commit()
        raise HTTPException(
            status_code=503,
            detail=LLMErrorResponse(
                error_code="llm_unavailable",
                persona_voice=get_error_voice(persona, "llm_unavailable"),
            ).model_dump(),
        )
    except LLMRequestInvalid:
        await db.commit()
        raise HTTPException(status_code=500, detail="Internal error processing request")

    # Insert assistant message
    assistant_msg = Message(
        id=str(_uuid.uuid4()),
        conversation_id=conv.id,
        user_id=user.id,
        role="assistant",
        content=llm_response.content,
        model_used=llm_response.model_used,
        tokens_used=llm_response.input_tokens + llm_response.output_tokens,
        latency_ms=llm_response.latency_ms,
    )
    db.add(assistant_msg)
    await db.flush()

    # Update conversation counters
    conv.message_count = (conv.message_count or 0) + 2
    conv.last_message_at = datetime.now(timezone.utc)
    await db.flush()

    # Increment daily_usage — counts only user messages (rate limit unit)
    today = date.today()
    usage_result = await db.execute(
        select(DailyUsage).where(
            DailyUsage.user_id == user.id,
            DailyUsage.persona_id == body.persona_id,
            DailyUsage.usage_date == today,
        )
    )
    usage = usage_result.scalar_one_or_none()
    if usage:
        usage.message_count += 1
    else:
        db.add(DailyUsage(
            user_id=user.id,
            persona_id=body.persona_id,
            usage_date=today,
            message_count=1,
        ))

    await db.commit()
    await db.refresh(assistant_msg)
    await db.refresh(conv)

    # Attach rate limit headers to the success response
    remaining_after = (
        rate_limit_result.remaining - 1
        if rate_limit_result.remaining != -1
        else -1
    )
    response.headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining_after)
    response.headers["X-RateLimit-Reset"] = rate_limit_result.reset_at.isoformat()

    # Enqueue title generation after the 3rd total message (e.g. opening + first exchange)
    if conv.message_count == 3 and conv.title is None:
        try:
            arq_queue = getattr(request.app.state, "arq_queue", None)
            if arq_queue:
                await arq_queue.enqueue_job(
                    "generate_conversation_title", str(conv.id)
                )
        except Exception as exc:
            logger.warning("Failed to enqueue title generation for %s: %s", conv.id, exc)

    return MessageEnvelope(
        conversation=ConversationSummary(
            id=conv.id,
            persona_id=conv.persona_id,
            title=conv.title,
            created_at=conv.created_at or datetime.now(timezone.utc),
        ),
        message=MessageResponse(
            id=assistant_msg.id,
            conversation_id=conv.id,
            role="assistant",
            content=assistant_msg.content,
            model_used=assistant_msg.model_used,
            tokens_used=assistant_msg.tokens_used,
            latency_ms=assistant_msg.latency_ms,
            created_at=assistant_msg.created_at or datetime.now(timezone.utc),
        ),
    )
