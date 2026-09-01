import logging
from services.analytics_service import analytics_service
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user, get_current_user_plan
from db.session import get_db
import services.rate_limit_service as rate_limit_service
from models import Mirror, MirrorSave, Persona, User
from schemas import MirrorOut, RingTrueRequest, MirrorHostOut, MirrorHostsResponse, SetMirrorHostRequest
from services.image_service import generate_mirror_share_image
from services.safety_service import safety_service
from services.safety_event_log import log_safety_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mirrors", tags=["mirrors"])

# App-voice crisis response for the ring-true note (A18c). NOT persona voice:
# it is not attributed to any thinker and must not read as one — the persona is
# dropped entirely when this fires.
RING_TRUE_SAFETY_MESSAGE = (
    "What you've shared matters. Before we continue, I want to make "
    "sure you're okay. If you're going through something difficult "
    "right now, please reach out to someone you trust or contact a "
    "crisis line in your country."
)

# Free-tier share cap — the SAME 90-day rolling Redis counter the line and
# council share endpoints use (key: share_screenshot:{user_id}).
FREE_SHARE_LIMIT  = 3
SHARE_WINDOW_SECS = 90 * 24 * 60 * 60


def _mirror_out(mirror: Mirror, persona: Persona | None) -> MirrorOut:
    return MirrorOut(
        id=mirror.id,
        kind=mirror.kind,
        status=mirror.status,
        period_start=mirror.period_start,
        period_end=mirror.period_end,
        host_persona_slug=persona.slug if persona else None,
        host_persona_name=persona.name if persona else None,
        payload=mirror.payload,
        ring_true=mirror.ring_true,
        ring_true_note=mirror.ring_true_note,
        created_at=mirror.created_at,
    )


async def _load_persona(db: AsyncSession, persona_id: str | None) -> Persona | None:
    if not persona_id:
        return None
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    return result.scalar_one_or_none()


@router.get("/latest", response_model=MirrorOut | None)
async def get_latest_mirror(
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
):
    user, plan = auth
    stmt = (
        select(Mirror)
        # Insight-seeded mirrors are reached only via the ?insightId= reflect flow
        # — never as the weekly reader's "latest". (Free is already preview-only
        # below; this clause covers paid, which has no kind filter.)
        .where(
            Mirror.user_id == user.id,
            Mirror.status == "generated",
            Mirror.kind != "insight",
        )
        .order_by(Mirror.created_at.desc())
        .limit(1)
    )
    if plan == "free":
        stmt = stmt.where(Mirror.kind == "preview")
    result = await db.execute(stmt)
    mirror = result.scalar_one_or_none()
    if mirror is None:
        return None
    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)


@router.post("/{mirror_id}/ring-true", response_model=MirrorOut)
async def set_ring_true(
    mirror_id: str,
    body: RingTrueRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Mirror).where(Mirror.id == mirror_id, Mirror.user_id == user.id)
    )
    mirror = result.scalar_one_or_none()
    if mirror is None:
        raise HTTPException(status_code=404)

    # ── Pre-persistence safety gate on the ring-true note ─────────────────────
    # The note is free text about the user's own emotional reaction. The ARQ
    # enqueue below has a safety gate inside the task, but that runs after the
    # commit — a crisis signal would already be stored and nothing would answer
    # it. This gate is synchronous and runs BEFORE any attribute is assigned, so
    # on suppression the note is never written: `mirror` stays unmodified and
    # there is nothing dirty for the session to flush.
    note = (body.note or "").strip()
    if note:
        safety_result = await safety_service.check_input(note, str(user.id))
        if safety_result.should_log:
            await log_safety_event(
                db, str(user.id), safety_result, "ring_true_input",
                conversation_id=None,
                message_id=None,
            )
        if safety_result.should_suppress_persona:
            # Return a well-formed MirrorOut built from the UNCHANGED mirror, so
            # the client still gets every field it reads. Because the early return
            # is above the assignments, the mirror carries pre-note state and
            # ring_true/ring_true_note are whatever they already were — the two
            # safety fields are what tell the client this note did not land.
            persona = await _load_persona(db, mirror.host_persona_id)
            out = _mirror_out(mirror, persona)
            out.safety_triggered = True
            out.safety_message = RING_TRUE_SAFETY_MESSAGE
            return out

    mirror.ring_true = body.ring_true
    mirror.ring_true_note = body.note
    mirror.ring_true_at = datetime.now(timezone.utc)
    # Explicit commit (not a bare flush): the enqueue below fires only once the note
    # is durably persisted, so a rollback at teardown can never orphan a stored memory.
    await db.commit()

    # The ring-true note is the user's OWN reaction to the mirror — distil it into a
    # confidence-1.0 memory (safety-gated + word-filtered inside the task). Async;
    # only when a non-empty note was written. Fire-and-forget; never break the response.
    # `note` was computed by the safety gate above; reaching here means it passed.
    if note:
        arq_queue = getattr(request.app.state, "arq_queue", None)
        if arq_queue is not None:
            try:
                await arq_queue.enqueue_job(
                    "distill_user_text_to_memory_task",
                    str(user.id),
                    None,
                    note,
                    "mirror_ring_true",
                )
            except Exception as exc:
                logger.error("Mirror ring-true note enqueue failed user=%s: %s", user.id, exc)

    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)


@router.get("/hosts", response_model=MirrorHostsResponse)
async def get_mirror_hosts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Persona).where(Persona.is_active == True))
    personas = result.scalars().all()
    eligible = [p for p in personas if p.config.get("mirror_capable")]
    jung_first = [p for p in eligible if p.slug == "carl_jung"]
    others = sorted([p for p in eligible if p.slug != "carl_jung"], key=lambda p: p.name)
    ordered = jung_first + others
    hosts = [MirrorHostOut(slug=p.slug, name=p.name, portrait_url=p.portrait_url or None) for p in ordered]
    return MirrorHostsResponse(hosts=hosts, selected=user.mirror_host_slug, default="carl_jung")


@router.post("/host", response_model=dict)
async def set_mirror_host(
    body: SetMirrorHostRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Persona).where(Persona.is_active == True))
    personas = result.scalars().all()
    eligible_slugs = {p.slug for p in personas if p.config.get("mirror_capable")}
    if body.host_slug not in eligible_slugs:
        raise HTTPException(status_code=400, detail="Not an eligible mirror host")
    user.mirror_host_slug = body.host_slug
    await db.flush()
    return {"host_slug": body.host_slug}


@router.post("/{mirror_id}/save")
async def save_mirror(
    mirror_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify the mirror belongs to this user
    result = await db.execute(
        select(Mirror).where(Mirror.id == mirror_id, Mirror.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404)

    # Upsert: re-save if soft-deleted, insert if absent, no-op if active
    existing = await db.execute(
        select(MirrorSave).where(
            MirrorSave.user_id == user.id,
            MirrorSave.mirror_id == mirror_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row is None:
        db.add(MirrorSave(user_id=user.id, mirror_id=mirror_id))
    elif row.deleted_at is not None:
        row.deleted_at = None

    await db.commit()
    return {"saved": True}


@router.delete("/{mirror_id}/save")
async def unsave_mirror(
    mirror_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MirrorSave).where(
            MirrorSave.user_id == user.id,
            MirrorSave.mirror_id == mirror_id,
            MirrorSave.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    return {"saved": False}


@router.post("/{mirror_id}/share")
async def share_mirror(
    mirror_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple = Depends(get_current_user_plan),
) -> Response:
    """
    Generate a share image for a mirror's closing reflection.
    Returns raw image/png bytes.
    Free tier: max 3 per 90-day rolling window (shared counter with line and
    council shares). Pro/premium: unlimited.
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
        png_bytes = await generate_mirror_share_image(
            db=db,
            mirror_id=mirror_id,
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # One event for every artifact a person chose to share. artifact_type is
    # the only property: there is no share_id yet (all six endpoints return raw
    # PNG bytes and persist nothing) and no channel (the OS share sheet never
    # tells us where it went). Both arrive with the P3 public share page, which
    # is also what makes share_landing_view and share_signup possible.
    analytics_service.track("share_created", user.id, {"artifact_type": "mirror"})

    return Response(content=png_bytes, media_type="image/png")
