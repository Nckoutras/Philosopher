from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
from models import WeeklyLetter, Persona
from schemas import WeeklyLetterOut

router = APIRouter(prefix="/weekly-letters", tags=["weekly-letters"])


def _to_out(letter: WeeklyLetter, persona: Persona | None) -> WeeklyLetterOut:
    return WeeklyLetterOut(
        id=letter.id,
        period_start=letter.period_start,
        period_end=letter.period_end,
        status=letter.status,
        payload=letter.payload,
        read_at=letter.read_at,
        voice_persona_slug=persona.slug if persona else None,
        voice_persona_name=persona.name if persona else None,
    )


@router.get("", response_model=list[WeeklyLetterOut])
async def list_weekly_letters(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    result = await db.execute(
        select(WeeklyLetter)
        .where(WeeklyLetter.user_id == user.id)
        .order_by(WeeklyLetter.created_at.desc())
    )
    letters = result.scalars().all()

    # Load associated personas in one query
    persona_ids = [l.voice_persona_id for l in letters if l.voice_persona_id]
    personas: dict[str, Persona] = {}
    if persona_ids:
        p_result = await db.execute(select(Persona).where(Persona.id.in_(persona_ids)))
        for p in p_result.scalars().all():
            personas[p.id] = p

    return [_to_out(l, personas.get(l.voice_persona_id)) for l in letters]


@router.get("/{letter_id}", response_model=WeeklyLetterOut)
async def get_weekly_letter(
    letter_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    result = await db.execute(
        select(WeeklyLetter).where(
            WeeklyLetter.id == letter_id,
            WeeklyLetter.user_id == user.id,
        )
    )
    letter = result.scalar_one_or_none()
    if letter is None:
        return JSONResponse(status_code=404, content={"error_code": "not_found"})

    # Mark read on first fetch
    if letter.read_at is None:
        letter.read_at = datetime.now(timezone.utc)
        await db.commit()

    persona = None
    if letter.voice_persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == letter.voice_persona_id))
        persona = p_result.scalar_one_or_none()

    return _to_out(letter, persona)
