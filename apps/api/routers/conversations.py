from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.session import get_db, AsyncSessionLocal
from models import User, Conversation, Message, Persona, SavedLine
from schemas import (
    ConversationCreate, ConversationOut, CrossPersonaRequest,
    MessageCreate, MessageOut, PersonaOut, LLMErrorResponse,
    AnotherMindCreate, ActiveMindSet, ReadingRevisitCreate,
)
from auth import get_current_user, get_current_user_plan, get_user_plan_streaming
from services.conversation_service import conversation_service
from services.tier_service import get_user_tier
from services.persona_voice import get_error_voice
import services.rate_limit_service as rate_limit_service
from personas import get_persona, is_persona_accessible

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _build_source_contents(db: AsyncSession, convs: list[Conversation]) -> dict[str, str]:
    """For cross-persona conversations, fetch the original saved-line message content."""
    source_ids = [c.source_saved_line_id for c in convs if c.source_saved_line_id]
    if not source_ids:
        return {}
    rows = await db.execute(
        select(SavedLine.id, Message.content)
        .join(Message, Message.id == SavedLine.message_id)
        .where(SavedLine.id.in_(source_ids))
    )
    return {str(row[0]): row[1] for row in rows.all()}


async def _build_last_snippets(db: AsyncSession, convs: list[Conversation], max_len: int = 70) -> dict[str, str]:
    """Latest assistant-message preview per conversation (one DISTINCT ON query)."""
    conv_ids = [c.id for c in convs]
    if not conv_ids:
        return {}
    rows = await db.execute(
        select(Message.conversation_id, Message.content)
        .where(Message.conversation_id.in_(conv_ids))
        .where(Message.role == "assistant")
        # CONCLUSION EXCLUSION: list preview should be the real last spoken line,
        # not a distilled conclusion bubble.
        .where(Message.message_kind != 'conclusion')
        .order_by(Message.conversation_id, Message.created_at.desc())
        .distinct(Message.conversation_id)
    )
    out: dict[str, str] = {}
    for conv_id, content in rows.all():
        text = " ".join((content or "").split())
        if len(text) > max_len:
            text = text[:max_len].rstrip() + "…"
        out[str(conv_id)] = text
    return out


def _conv_out(conv: Conversation, source_contents: dict[str, str], snippets: dict[str, str] | None = None) -> ConversationOut:
    # Universal read rule: `persona` is the coalesced ACTIVE mind (sticky guest when
    # set, else home) — so header, history thumbnails and resume all show who the
    # conversation is *currently* with. `origin_persona_*` always points to the
    # immutable home persona, for the "Return to [origin]" affordance.
    active = conv.active_persona or conv.persona
    pc = get_persona(active.slug)
    return ConversationOut(
        id=conv.id,
        persona=PersonaOut(
            id=active.id,
            slug=active.slug,
            name=active.name,
            era=active.era,
            tradition=active.tradition,
            tier=active.tier,
            tagline=pc.tagline if pc else None,
            avatar_emoji=pc.avatar_emoji if pc else None,
            # Needed so the client can render the active mind's portrait
            # immediately on a sticky switch (no refetch).
            portrait_url=active.portrait_url,
        ),
        title=conv.title,
        message_count=conv.message_count,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        source_persona_slug=conv.source_persona_slug,
        source_context_content=(
            source_contents.get(conv.source_saved_line_id)
            if conv.source_saved_line_id else None
        ),
        last_message_snippet=(snippets or {}).get(str(conv.id)),
        origin_persona_slug=conv.persona.slug,
        origin_persona_name=conv.persona.name,
        deep_mode=conv.deep_mode,
    )


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
            skip_opening=body.skip_opening,
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


@router.post("/cross-persona", response_model=ConversationOut, status_code=201)
async def create_cross_persona_conversation(
    body: CrossPersonaRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, _plan = auth
    try:
        conv = await conversation_service.create_cross_persona(
            db=db,
            user_id=user.id,
            saved_line_id=body.saved_line_id,
            target_persona_slug=body.target_persona_slug,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    await db.refresh(conv, ["persona"])

    source_contents = await _build_source_contents(db, [conv])
    return _conv_out(conv, source_contents)


@router.post("/reading-revisit", response_model=ConversationOut, status_code=201)
async def create_reading_revisit_conversation(
    body: ReadingRevisitCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """Create a conversation whose first message is the persona's candid read on
    the user, generated from a weekly letter. Pro + persona-access gated."""
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    try:
        conv = await conversation_service.create_reading_revisit(
            db=db,
            user_id=user.id,
            weekly_letter_id=body.weekly_letter_id,
            target_persona_slug=body.target_persona_slug,
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
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.persona), selectinload(Conversation.active_persona))
        .where(Conversation.user_id == user.id)
    )
    if q:
        stmt = stmt.where(Conversation.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Conversation.last_message_at.desc().nullslast()).limit(50)

    result = await db.execute(stmt)
    convs = result.scalars().all()

    source_contents = await _build_source_contents(db, convs)
    snippets = await _build_last_snippets(db, convs)
    return [_conv_out(c, source_contents, snippets) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversationOut:
    """Get a single conversation by ID. Verifies ownership."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.persona), selectinload(Conversation.active_persona))
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    source_contents = await _build_source_contents(db, [conv])
    return _conv_out(conv, source_contents)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .options(selectinload(Message.persona))
    )
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            safety_level=m.safety_level,
            persona_override=m.persona_override,
            persona_slug=m.persona.slug if m.persona else None,
            message_kind=m.message_kind,
            created_at=m.created_at,
        )
        for m in msgs.scalars().all()
    ]


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: Request,
    body: MessageCreate,
    auth: tuple = Depends(get_user_plan_streaming),
):
    """SSE streaming endpoint. Returns text/event-stream.

    §5 pool-leak fix: auth + preflight run in short-lived sessions that close
    BEFORE the stream starts, and the generator manages its own sessions via
    the factory. No pooled DB session is held across the multi-second token
    stream. (get_db is intentionally NOT a dependency here.)
    """
    user, plan = auth

    # Preflight (conv lookup + rate-limit) in a short-lived session opened and
    # CLOSED here — never held across the token stream.
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Sticky guest: the responder (and thus whose quota this send consumes) is
        # the active mind when set, else the home persona.
        responder_persona_id = conv.active_persona_id or conv.persona_id
        persona_result = await db.execute(select(Persona).where(Persona.id == responder_persona_id))
        persona = persona_result.scalar_one()

        rate_limit_result = None
        if not user.is_admin and conv.ritual_id is None:
            user_tier = await get_user_tier(db, user.id)
            rate_limit_result = await rate_limit_service.check_rate_limit(
                db, UUID(user.id), UUID(responder_persona_id), user_tier=user_tier
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

    arq_queue = getattr(request.app.state, "arq_queue", None)

    return StreamingResponse(
        conversation_service.stream_response(
            session_factory=AsyncSessionLocal,
            conversation_id=conversation_id,
            user_id=user.id,
            user_text=body.content,
            user_plan=plan,
            user_name=user.full_name,
            is_admin=user.is_admin,
            arq_queue=arq_queue,
            seeded_opening=body.seeded_opening,
        ),
        media_type="text/event-stream",
        headers=response_headers,
    )


@router.post("/{conversation_id}/another-mind")
async def another_mind(
    conversation_id: str,
    request: Request,
    body: AnotherMindCreate,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """SSE streaming endpoint. Generates a second persona's reply inside an existing conversation."""
    user, plan = auth

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    home_persona_result = await db.execute(select(Persona).where(Persona.id == conv.persona_id))
    home_persona = home_persona_result.scalar_one()

    target_config = get_persona(body.target_persona_slug)
    if not target_config:
        raise HTTPException(status_code=404, detail="Persona not found")

    if body.target_persona_slug == home_persona.slug:
        return JSONResponse(status_code=400, content={"error_code": "same_persona"})

    if not is_persona_accessible(target_config, plan):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    target_persona_result = await db.execute(select(Persona).where(Persona.slug == body.target_persona_slug))
    target_persona = target_persona_result.scalar_one_or_none()
    if not target_persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    rate_limit_result = None
    if not user.is_admin and conv.ritual_id is None:
        user_tier = await get_user_tier(db, user.id)
        rate_limit_result = await rate_limit_service.check_rate_limit(
            db, UUID(user.id), UUID(target_persona.id), user_tier=user_tier
        )
        if not rate_limit_result.allowed:
            return JSONResponse(
                status_code=429,
                content=LLMErrorResponse(
                    error_code="rate_limited",
                    persona_voice=get_error_voice(target_config, "rate_limited"),
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

    arq_queue = getattr(request.app.state, "arq_queue", None)

    return StreamingResponse(
        conversation_service.stream_another_mind(
            db=db,
            conversation_id=conversation_id,
            user_id=user.id,
            target_persona_slug=body.target_persona_slug,
            user_plan=plan,
            user_name=user.full_name,
            is_admin=user.is_admin,
            arq_queue=arq_queue,
        ),
        media_type="text/event-stream",
        headers=response_headers,
    )


@router.post("/{conversation_id}/active-mind", response_model=ConversationOut)
async def set_active_mind(
    conversation_id: str,
    body: ActiveMindSet,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> ConversationOut:
    """Make the chosen guest the sticky active mind (continue with [guest]).

    Persists `active_persona_id`; the immutable home `persona_id` is never touched.
    Reuses the exact tier gate another-mind uses. Setting the active mind to the
    home persona is normalised to NULL (return to origin).
    """
    user, plan = auth
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.persona), selectinload(Conversation.active_persona))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    target_config = get_persona(body.target_persona_slug)
    if not target_config:
        raise HTTPException(status_code=404, detail="Persona not found")
    if not is_persona_accessible(target_config, plan):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    target_result = await db.execute(select(Persona).where(Persona.slug == body.target_persona_slug))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Persona not found")

    conv.active_persona_id = None if target.id == conv.persona_id else target.id
    await db.commit()
    await db.refresh(conv, attribute_names=["active_persona"])

    source_contents = await _build_source_contents(db, [conv])
    return _conv_out(conv, source_contents)


@router.delete("/{conversation_id}/active-mind", response_model=ConversationOut)
async def clear_active_mind(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversationOut:
    """Return to origin: clear the sticky active mind back to the home persona."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.persona), selectinload(Conversation.active_persona))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.active_persona_id = None
    await db.commit()
    await db.refresh(conv, attribute_names=["active_persona"])

    source_contents = await _build_source_contents(db, [conv])
    return _conv_out(conv, source_contents)


async def _set_deep_mode(conversation_id: str, on: bool, db: AsyncSession, user: User) -> ConversationOut:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.persona), selectinload(Conversation.active_persona))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.deep_mode = on
    await db.commit()

    source_contents = await _build_source_contents(db, [conv])
    return _conv_out(conv, source_contents)


@router.post("/{conversation_id}/deep-mode", response_model=ConversationOut)
async def set_deep_mode(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> ConversationOut:
    """Turn sticky deep mode ON. Pro/premium only — free users never get sticky
    depth (per-tap go-deeper only). The read site in stream_response is ALSO
    Pro-gated, so the flag is inert if an account later downgrades."""
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})
    return await _set_deep_mode(conversation_id, True, db, user)


@router.delete("/{conversation_id}/deep-mode", response_model=ConversationOut)
async def clear_deep_mode(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConversationOut:
    """Turn sticky deep mode OFF (back to normal replies)."""
    return await _set_deep_mode(conversation_id, False, db, user)


@router.post("/{conversation_id}/go-deeper")
async def go_deeper(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """SSE streaming endpoint. Same persona presses the user one level deeper."""
    user, plan = auth

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Go deeper is spoken by the current responder (sticky active guest when set,
    # else home), so it checks/consumes that mind's quota — Gap 2.
    responder_persona_id = conv.active_persona_id or conv.persona_id
    home_persona_result = await db.execute(select(Persona).where(Persona.id == responder_persona_id))
    home_persona = home_persona_result.scalar_one()
    home_config = get_persona(home_persona.slug)

    rate_limit_result = None
    if not user.is_admin and conv.ritual_id is None:
        user_tier = await get_user_tier(db, user.id)
        rate_limit_result = await rate_limit_service.check_rate_limit(
            db, UUID(user.id), UUID(responder_persona_id), user_tier=user_tier
        )
        if not rate_limit_result.allowed:
            return JSONResponse(
                status_code=429,
                content=LLMErrorResponse(
                    error_code="rate_limited",
                    persona_voice=get_error_voice(home_config, "rate_limited"),
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

    arq_queue = getattr(request.app.state, "arq_queue", None)

    return StreamingResponse(
        conversation_service.stream_go_deeper(
            db=db,
            conversation_id=conversation_id,
            user_id=user.id,
            user_plan=plan,
            user_name=user.full_name,
            is_admin=user.is_admin,
            arq_queue=arq_queue,
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
