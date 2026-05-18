from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from db.session import get_db
from models import User, Conversation, Message, Persona, SavedLine, DailyQuestion
from schemas import DailyQuestionOut, LastConversationOut, RecentSavedLineOut
from auth import get_current_user
from personas import PERSONA_REGISTRY

router = APIRouter(tags=["home"])


@router.get("/today/question", response_model=DailyQuestionOut)
async def get_today_question(db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("""
            SELECT id, question_text
            FROM daily_questions
            WHERE active = true
            ORDER BY display_order
            OFFSET (
                (EXTRACT(DOY FROM now()::date)::int - 1)
                % (SELECT COUNT(*) FROM daily_questions WHERE active = true)
            )
            LIMIT 1
        """)
    )
    q = row.mappings().one()
    return DailyQuestionOut(id=str(q["id"]), question_text=q["question_text"])


@router.get("/me/last-conversation")
async def get_last_conversation(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.deleted_at.is_(None))
        .order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.created_at.desc(),
        )
        .limit(1)
    )
    conv = conv_result.scalar_one_or_none()
    if conv is None:
        response.status_code = 204
        return None

    persona_result = await db.execute(
        select(Persona).where(Persona.id == conv.persona_id)
    )
    persona = persona_result.scalar_one_or_none()

    last_msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_msg = last_msg_result.scalar_one_or_none()
    snippet: str | None = None
    if last_msg:
        snippet = last_msg.content[:80] + "…" if len(last_msg.content) > 80 else last_msg.content

    config = PERSONA_REGISTRY.get(persona.slug) if persona else None
    tagline = (config.tagline if config else None) or (persona.config or {}).get('tagline') if persona else None

    return LastConversationOut(
        conversation_id=conv.id,
        persona_id=conv.persona_id,
        persona_slug=persona.slug if persona else "",
        persona_name=persona.name if persona else "",
        persona_tagline=tagline,
        persona_portrait_url=persona.portrait_url if persona else "",
        last_message_snippet=snippet,
        updated_at=conv.last_message_at or conv.created_at,
    )


@router.get("/me/recent-saved-line")
async def get_recent_saved_line(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sl_result = await db.execute(
        select(SavedLine)
        .where(SavedLine.user_id == user.id, SavedLine.deleted_at.is_(None))
        .order_by(SavedLine.saved_at.desc())
        .limit(1)
    )
    sl = sl_result.scalar_one_or_none()
    if sl is None:
        response.status_code = 204
        return None

    msg_result = await db.execute(select(Message).where(Message.id == sl.message_id))
    msg = msg_result.scalar_one_or_none()

    persona_result = await db.execute(select(Persona).where(Persona.id == sl.persona_id))
    persona = persona_result.scalar_one_or_none()

    return RecentSavedLineOut(
        saved_line_id=sl.id,
        content=msg.content if msg else "",
        persona_id=sl.persona_id,
        persona_slug=persona.slug if persona else "",
        persona_name=persona.name if persona else "",
        saved_at=sl.saved_at,
    )
