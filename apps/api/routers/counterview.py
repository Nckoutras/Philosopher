from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from db.session import get_db
from models import Counterview, CounterviewResponse, Persona, User
from schemas import CounterviewCreate, CounterviewOut, CounterviewResponseOut
from services.counterview_service import generate_counterview

router = APIRouter(prefix="/counterview", tags=["counterview"])

BELIEF_MAX_CHARS = 1000


async def _serialize_counterview(db: AsyncSession, cv: Counterview) -> CounterviewOut:
    """Serialize a counterview + its responses, resolving each persona's display
    name and portrait from the DB (the same source as the mirror reader). A
    'suppressed'/'empty' counterview simply has no responses — never expose that
    safety detection happened."""
    responses = (
        await db.execute(
            select(CounterviewResponse)
            .where(CounterviewResponse.counterview_id == cv.id)
            .order_by(CounterviewResponse.position.asc())
        )
    ).scalars().all()

    personas: dict[str, Persona] = {}
    slugs = {r.persona_slug for r in responses}
    if slugs:
        rows = (
            await db.execute(select(Persona).where(Persona.slug.in_(slugs)))
        ).scalars().all()
        personas = {p.slug: p for p in rows}

    out_responses = [
        CounterviewResponseOut(
            persona_slug=r.persona_slug,
            persona_name=personas[r.persona_slug].name if r.persona_slug in personas else r.persona_slug,
            persona_portrait_url=(personas[r.persona_slug].portrait_url or None) if r.persona_slug in personas else None,
            position=r.position,
            round=r.round,
            verdict=r.verdict,
        )
        for r in responses
    ]

    return CounterviewOut(
        id=cv.id,
        source=cv.source,
        anchor_text=cv.anchor_text,
        status=cv.status,
        responses=out_responses,
    )


@router.post("", response_model=CounterviewOut)
async def create_counterview(
    body: CounterviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a counterview for a position the user types directly. Status
    'empty'/'suppressed' returns a clean 200 with responses=[] for the frontend
    to handle, not an error."""
    belief = (body.belief or "").strip()
    if not belief:
        raise HTTPException(status_code=400, detail="empty_belief")
    if len(belief) > BELIEF_MAX_CHARS:
        raise HTTPException(status_code=400, detail="belief_too_long")

    cv = await generate_counterview(
        db, user.id, belief=belief, insight_id=None, source="direct"
    )
    return await _serialize_counterview(db, cv)


@router.get("/{counterview_id}", response_model=CounterviewOut)
async def get_counterview(
    counterview_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cv = (
        await db.execute(
            select(Counterview).where(
                Counterview.id == counterview_id,
                Counterview.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if cv is None:
        raise HTTPException(status_code=404)
    return await _serialize_counterview(db, cv)
