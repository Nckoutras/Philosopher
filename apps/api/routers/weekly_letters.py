from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
import services.rate_limit_service as rate_limit_service
from models import WeeklyLetter, Persona
from schemas import WeeklyLetterOut, WriteBackIn
from services.image_service import generate_letter_share_image

# Free-tier share cap — the SAME 90-day rolling Redis counter the mirror, line,
# and council share endpoints use (key: share_screenshot:{user_id}).
FREE_SHARE_LIMIT  = 3
SHARE_WINDOW_SECS = 90 * 24 * 60 * 60

router = APIRouter(prefix="/weekly-letters", tags=["weekly-letters"])


def _to_out(letter: WeeklyLetter, persona: Persona | None) -> WeeklyLetterOut:
    return WeeklyLetterOut(
        id=letter.id,
        period_start=letter.period_start,
        period_end=letter.period_end,
        status=letter.status,
        kind=letter.kind,
        payload=letter.payload,
        read_at=letter.read_at,
        write_back_text=letter.write_back_text,
        write_back_at=letter.write_back_at,
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


@router.patch("/{letter_id}/write-back", response_model=WeeklyLetterOut)
async def write_back_to_letter(
    letter_id: str,
    body: WriteBackIn,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    """
    Capture the reader's short response to a Sunday/season letter. Pro-gated like
    its sibling endpoints. One write-back per letter — re-submitting overwrites
    the prior one. No live LLM reply in v1; the text is fed forward into the next
    letter via the generators' existing prior-letters fetch.
    """
    user, plan = auth
    if plan not in ("pro", "premium"):
        return JSONResponse(status_code=403, content={"error_code": "upgrade_required"})

    text = body.text.strip()
    if not text:
        return JSONResponse(status_code=422, content={"error_code": "empty_write_back"})

    result = await db.execute(
        select(WeeklyLetter).where(
            WeeklyLetter.id == letter_id,
            WeeklyLetter.user_id == user.id,
        )
    )
    letter = result.scalar_one_or_none()
    if letter is None:
        return JSONResponse(status_code=404, content={"error_code": "not_found"})

    letter.write_back_text = text
    letter.write_back_at = datetime.now(timezone.utc)
    await db.commit()

    persona = None
    if letter.voice_persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == letter.voice_persona_id))
        persona = p_result.scalar_one_or_none()

    return _to_out(letter, persona)


@router.delete("/{letter_id}", status_code=204)
async def delete_weekly_letter(
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

    await db.delete(letter)
    await db.commit()
    return Response(status_code=204)


@router.post("/{letter_id}/share")
async def share_weekly_letter(
    letter_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """
    Generate a share image (wax-seal card) for a Sunday Letter's pull_quote.
    Returns raw image/png bytes.
    Free tier: max 3 per 90-day rolling window (shared counter with mirror, line,
    and council shares). Pro/premium: unlimited.
    """
    user, plan = auth

    if plan not in ("pro", "premium"):
        allowed = await rate_limit_service.check_and_increment(
            key=f"share_screenshot:{user.id}",
            max_count=FREE_SHARE_LIMIT,
            window_seconds=SHARE_WINDOW_SECS,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error_code": "share_limit_reached"},
            )

    try:
        png_bytes = await generate_letter_share_image(
            db=db,
            weekly_letter_id=letter_id,
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(content=png_bytes, media_type="image/png")
