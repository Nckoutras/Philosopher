from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from db.session import get_db
from models import Counterview, CounterviewResponse, CounterviewSave, CounterviewTurn, Persona, User
from schemas import (
    CounterviewCreate,
    CounterviewDeeperRequest,
    CounterviewListItem,
    CounterviewOut,
    CounterviewResponseOut,
    CounterviewRespondRequest,
    CounterviewTurnOut,
)
from services.counterview_service import (
    MAX_REBUTTALS,
    generate_counterview,
    generate_deeper,
    respond_to_rebuttal,
)

router = APIRouter(prefix="/counterview", tags=["counterview"])

BELIEF_MAX_CHARS = 1000
REBUTTAL_MAX_CHARS = 1000


async def _serialize_counterview(db: AsyncSession, cv: Counterview, user_id: str) -> CounterviewOut:
    """Serialize a counterview + its responses, resolving each persona's display
    name and portrait from the DB (the same source as the mirror reader). A
    'suppressed'/'empty' counterview simply has no responses — never expose that
    safety detection happened. `is_saved` reflects an active (not soft-deleted)
    save by this user — the Save button's initial state on reload."""
    responses = (
        await db.execute(
            select(CounterviewResponse)
            .where(CounterviewResponse.counterview_id == cv.id)
            .order_by(CounterviewResponse.position.asc(), CounterviewResponse.round.asc())
        )
    ).scalars().all()

    # The rebuttal exchange, in sequence order (independent of the verdict rounds).
    turns = (
        await db.execute(
            select(CounterviewTurn)
            .where(CounterviewTurn.counterview_id == cv.id)
            .order_by(CounterviewTurn.sequence.asc())
        )
    ).scalars().all()

    personas: dict[str, Persona] = {}
    slugs = {r.persona_slug for r in responses} | {t.persona_slug for t in turns}
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

    out_turns = [
        CounterviewTurnOut(
            sequence=t.sequence,
            persona_slug=t.persona_slug,
            persona_name=personas[t.persona_slug].name if t.persona_slug in personas else t.persona_slug,
            persona_portrait_url=(personas[t.persona_slug].portrait_url or None) if t.persona_slug in personas else None,
            user_text=t.user_text,
            persona_response=t.persona_response,
            status=t.status,
        )
        for t in turns
    ]

    # Cap budget: status='generated' turns only (suppressed/empty don't consume it).
    generated_turns = sum(1 for t in turns if t.status == "generated")
    rebuttals_remaining = max(0, MAX_REBUTTALS - generated_turns)

    is_saved = (
        await db.execute(
            select(CounterviewSave.id).where(
                CounterviewSave.user_id == user_id,
                CounterviewSave.counterview_id == cv.id,
                CounterviewSave.deleted_at.is_(None),
            )
        )
    ).first() is not None

    return CounterviewOut(
        id=cv.id,
        source=cv.source,
        anchor_text=cv.anchor_text,
        status=cv.status,
        still_stands=cv.still_stands,
        title=cv.title,
        responses=out_responses,
        turns=out_turns,
        rebuttals_remaining=rebuttals_remaining,
        is_saved=is_saved,
    )


@router.post("", response_model=CounterviewOut)
async def create_counterview(
    body: CounterviewCreate,
    request: Request,
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

    # Feed the voluntary belief into the self-model + recurrence detector (Slice 1).
    # Direct path only, and only when a real counterview was generated (the belief was
    # non-suppressed, substantive content). We enqueue the user's OWN belief text — the
    # anchor, never a verdict. Fire-and-forget; the insight path never reaches here, so
    # source='insight' is never re-detected (avoids looping off an existing insight).
    if cv.status == "generated":
        q = getattr(request.app.state, "arq_queue", None)
        if q is not None:
            await q.enqueue_job("counterview_belief_task", str(user.id), belief)

    return await _serialize_counterview(db, cv, user.id)


@router.get("", response_model=list[CounterviewListItem])
async def list_counterviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Slim, most-recent-first list of this user's generated counterviews for the
    revisit list. Skips empty/suppressed; reopening pulls the full set via GET /{id}.
    Distinct from POST "" (different method) and GET /{id} (different path)."""
    rows = (
        await db.execute(
            select(Counterview.id, Counterview.anchor_text, Counterview.created_at)
            .where(
                Counterview.user_id == user.id,
                Counterview.status == "generated",
            )
            .order_by(Counterview.created_at.desc())
            .limit(10)
        )
    ).all()
    return [
        CounterviewListItem(id=str(r.id), anchor_text=r.anchor_text, created_at=r.created_at)
        for r in rows
    ]


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
    return await _serialize_counterview(db, cv, user.id)


@router.post("/{counterview_id}/deeper", response_model=CounterviewOut)
async def deeper_counterview(
    counterview_id: str,
    body: CounterviewDeeperRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Press one layer deeper for a single persona. Returns the full counterview
    (now carrying the persona's round-1 response). A no-op (cap reached, nothing
    to add, safety trip) returns the counterview unchanged with a clean 200."""
    try:
        cv = await generate_deeper(db, user.id, counterview_id, body.persona_slug)
    except ValueError as e:
        if "invalid persona" in str(e):
            raise HTTPException(status_code=400)
        raise HTTPException(status_code=404)
    return await _serialize_counterview(db, cv, user.id)


@router.post("/{counterview_id}/respond", response_model=CounterviewOut)
async def respond_counterview(
    counterview_id: str,
    body: CounterviewRespondRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """User rebuttal directed at the current speaker (persona_slug); that persona
    replies in one tight (<=18-word) line. Bounded: at most MAX_REBUTTALS generated
    rebuttals per counterview (409 once met). A suppressed input / empty generation /
    suppressed output persists a turn with that status (no reply) and returns 200.
    The returned counterview carries `turns[]` and the updated `rebuttals_remaining`."""
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty_rebuttal")
    if len(text) > REBUTTAL_MAX_CHARS:
        raise HTTPException(status_code=400, detail="rebuttal_too_long")

    try:
        cv = await respond_to_rebuttal(db, user.id, counterview_id, body.persona_slug, text)
    except ValueError as e:
        msg = str(e)
        if "invalid persona" in msg:
            raise HTTPException(status_code=400, detail="invalid_persona")
        if "cap_reached" in msg:
            raise HTTPException(status_code=409, detail="rebuttal_cap_reached")
        raise HTTPException(status_code=404)
    return await _serialize_counterview(db, cv, user.id)


@router.post("/{counterview_id}/save")
async def save_counterview(
    counterview_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify the counterview belongs to this user
    result = await db.execute(
        select(Counterview).where(
            Counterview.id == counterview_id,
            Counterview.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404)

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active
    existing = await db.execute(
        select(CounterviewSave).where(
            CounterviewSave.user_id == user.id,
            CounterviewSave.counterview_id == counterview_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(CounterviewSave(user_id=user.id, counterview_id=counterview_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    return {"saved": True}


@router.delete("/{counterview_id}/save")
async def unsave_counterview(
    counterview_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CounterviewSave).where(
            CounterviewSave.user_id == user.id,
            CounterviewSave.counterview_id == counterview_id,
            CounterviewSave.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}
