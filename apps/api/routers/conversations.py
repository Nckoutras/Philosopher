from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, Conversation, Message
from schemas import ConversationCreate, ConversationOut, MessageCreate, MessageOut, PersonaOut
from auth import get_current_user, get_current_user_plan
from services.conversation_service import conversation_service
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
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.last_message_at.desc().nullslast())
        .limit(50)
    )
    convs = result.scalars().all()
    out = []
    for conv in convs:
        await db.refresh(conv, ["persona"])
        persona_config = get_persona(conv.persona.slug)
        out.append(ConversationOut(
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

    # Verify ownership
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StreamingResponse(
        conversation_service.stream_response(
            db=db,
            conversation_id=conversation_id,
            user_id=user.id,
            user_text=body.content,
            user_plan=plan,
            user_name=user.full_name,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
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
