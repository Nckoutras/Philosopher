from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.session import get_db
from models import User, Ritual, UserRitualCompletion, Conversation, Persona
from schemas import RitualOut, ConversationOut, PersonaOut
from auth import get_current_user, get_current_user_plan
from services.conversation_service import conversation_service
from personas import get_persona
from constants import TIER_ORDER

router = APIRouter(prefix="/rituals", tags=["rituals"])


@router.get("", response_model=list[RitualOut])
async def list_rituals(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    _, plan = auth
    result = await db.execute(
        select(Ritual).where(Ritual.is_active == True).order_by(Ritual.tier.asc(), Ritual.name.asc())
    )
    rituals = result.scalars().all()
    user_tier = TIER_ORDER.get(plan, 0)

    return [
        RitualOut(
            id=r.id,
            slug=r.slug,
            name=r.name,
            description=r.description,
            tier=r.tier,
            frequency=r.frequency,
            is_accessible=TIER_ORDER.get(r.tier, 0) <= user_tier,
        )
        for r in rituals
    ]


@router.post("/{ritual_id}/start", response_model=ConversationOut, status_code=201)
async def start_ritual(
    ritual_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    user_tier = TIER_ORDER.get(plan, 0)

    result = await db.execute(select(Ritual).where(Ritual.id == ritual_id, Ritual.is_active == True))
    ritual = result.scalar_one_or_none()
    if not ritual:
        raise HTTPException(status_code=404, detail="Ritual not found")
    if TIER_ORDER.get(ritual.tier, 0) > user_tier:
        raise HTTPException(status_code=403, detail="Upgrade required")

    # Determine which persona to use
    if ritual.persona_id:
        persona_result = await db.execute(select(Persona).where(Persona.id == ritual.persona_id))
        persona_db = persona_result.scalar_one()
        persona_slug = persona_db.slug
    else:
        # Default to Marcus for persona-agnostic rituals
        persona_slug = "marcus_aurelius"

    # Create conversation for this ritual
    conv = await conversation_service.create(
        db=db,
        user_id=user.id,
        persona_slug=persona_slug,
        ritual_id=ritual_id,
        user_plan=plan,
    )

    # Override the opening message with the ritual prompt
    from jinja2 import Environment
    from datetime import date
    env = Environment()
    tpl = env.from_string(ritual.prompt_template)
    ritual_opener = tpl.render(
        user_name=user.full_name,
        current_date=date.today().strftime("%B %d, %Y"),
    )

    from models import Message
    from sqlalchemy import update
    # Replace default opening invocation with ritual prompt
    first_msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.role == "assistant")
        .order_by(Message.created_at.asc())
        .limit(1)
    )
    first_msg = first_msg_result.scalar_one_or_none()
    if first_msg:
        first_msg.content = ritual_opener
    else:
        msg = Message(
            conversation_id=conv.id,
            user_id=user.id,
            role="assistant",
            content=ritual_opener,
        )
        db.add(msg)

    # Record completion
    completion = UserRitualCompletion(
        user_id=user.id,
        ritual_id=ritual_id,
        conversation_id=conv.id,
    )
    db.add(completion)
    await db.commit()

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
        ),
        title=ritual.name,
        message_count=1,
        last_message_at=None,
        created_at=conv.created_at,
    )


@router.get("/completions")
async def get_completions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserRitualCompletion)
        .where(UserRitualCompletion.user_id == user.id)
        .order_by(UserRitualCompletion.completed_at.desc())
        .limit(200)
    )
    completions = result.scalars().all()
    return [
        {
            "id": c.id,
            "ritual_id": c.ritual_id,
            "conversation_id": c.conversation_id,
            "completed_at": c.completed_at,
        }
        for c in completions
    ]
