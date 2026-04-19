from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import Persona
from schemas import PersonaOut
from auth import get_current_user_plan
from personas import PERSONA_REGISTRY, is_persona_accessible

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaOut])
async def list_personas(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    _, plan = auth
    result = await db.execute(
        select(Persona).where(Persona.is_active == True).order_by(Persona.tier.asc(), Persona.name.asc())
    )
    personas = result.scalars().all()
    out = []
    for p in personas:
        config = PERSONA_REGISTRY.get(p.slug)
        out.append(PersonaOut(
            id=p.id,
            slug=p.slug,
            name=p.name,
            era=p.era,
            tradition=p.tradition,
            tier=p.tier,
            tagline=config.tagline if config else None,
            avatar_emoji=config.avatar_emoji if config else None,
            opening_invocation=config.opening_invocation if config else None,
            is_accessible=is_persona_accessible(config, plan) if config else False,
        ))
    return out


@router.get("/{slug}", response_model=PersonaOut)
async def get_persona_detail(
    slug: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    _, plan = auth
    result = await db.execute(select(Persona).where(Persona.slug == slug, Persona.is_active == True))
    p = result.scalar_one_or_none()
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Persona not found")
    config = PERSONA_REGISTRY.get(p.slug)
    return PersonaOut(
        id=p.id, slug=p.slug, name=p.name, era=p.era, tradition=p.tradition, tier=p.tier,
        tagline=config.tagline if config else None,
        avatar_emoji=config.avatar_emoji if config else None,
        opening_invocation=config.opening_invocation if config else None,
        is_accessible=is_persona_accessible(config, plan) if config else False,
    )
