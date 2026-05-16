from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.session import get_db
from models import User, Conversation, Message, Persona
from schemas import ConversationCreate, ConversationOut, MessageCreate, MessageOut, PersonaOut, LLMErrorResponse
from auth import get_current_user, get_current_user_plan
from services.conversation_service import conversation_service
from services.tier_service import get_user_tier
from services.persona_voice import get_error_voice
import services.rate_limit_service as rate_limit_service
from personas import get_persona

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    try:
        conv = await conversation_service.create(
            db=db,
            user_id=user.id,
            persona_slug=body.persona_slug,
            ritual_id=body.ritual_id,
            user_plan=plan,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    await db.refresh(conv, ["persona"])
    persona_config = get_persona(conv.persona.slug)

    return ConversationOut(
        id=conv.id,
        persona=PersonaOut(
            id=conv.persona.id,
            slug=conv.persona.slug,
            name=conv.persona.name,
            era=conv.persona.era,
            tradition=conv.persona.tradition,
            tier=conv.persona.tier,
            tagline=persona_config.tagline if persona_config else None,
            avatar_emoji=persona_config.avatar_emoji if persona_config else None,
            opening_invocation=persona_config.opening_invocation if persona_config else None,
        ),
        title=conv.title,
        message_count=conv.message_count,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
    )


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.persona))
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.last_message_at.desc().nullslast())
        .limit(50)
    )
    convs = result.scalars().all()
    out = []
    for conv in convs:
        pc = get_persona(conv.persona.slug)
        out.append(ConversationOut(
            id=conv.id,
            persona=PersonaOut(
                id=conv.persona.id,
                slug=conv.persona.slug,
                name=conv.persona.name,
                era=conv.persona.era,
                tradition=conv.persona.tradition,
                tier=conv.persona.tier,
                tagline=pc.tagline if pc else None,
                avatar_emoji=pc.avatar_emoji if pc else None,
            ),
            title=conv.title,
            message_count=conv.message_count,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
        ))
    return out


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return [MessageOut.model_validate(m) for m in msgs.scalars().all()]


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """SSE streaming endpoint. Returns text/event-stream."""
    user, plan = auth

    # Verify ownership and load conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load persona (needed for error voice on rate limit)
    persona_result = await db.execute(select(Persona).where(Persona.id == conv.persona_id))
    persona = persona_result.scalar_one()

    # Rate limit check — skip for admins and ritual conversations
    rate_limit_result = None
    if not user.is_admin and conv.ritual_id is None:
        user_tier = await get_user_tier(db, user.id)
        rate_limit_result = await rate_limit_service.check_rate_limit(
            db, UUID(user.id), UUID(conv.persona_id), user_tier=user_tier
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

    response_headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    if rate_limit_result is not None:
        response_headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
        response_headers["X-RateLimit-Remaining"] = str(
            max(0, rate_limit_result.remaining - 1)
        )
        response_headers["X-RateLimit-Reset"] = rate_limit_result.reset_at.isoformat()

    return StreamingResponse(
        conversation_service.stream_response(
            db=db,
            conversation_id=conversation_id,
            user_id=user.id,
            user_text=body.content,
            user_plan=plan,
            user_name=user.full_name,
            is_admin=user.is_admin,
        ),
        media_type="text/event-stream",
        headers=response_headers,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)
    await db.delete(conv)
