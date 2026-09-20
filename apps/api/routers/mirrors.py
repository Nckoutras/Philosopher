import logging
from services.analytics_service import analytics_service
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user, get_current_user_plan
from db.session import get_db
from models import Mirror, MirrorSave, Persona, User
from schemas import MirrorOut, RingTrueRequest, MirrorHostOut, MirrorHostsResponse, SetMirrorHostRequest
from services.image_service import generate_mirror_share_image
from routers.share import create_and_render
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

    # Γ-5 — the recognition loop's second surface, and until now an unrecorded one.
    # Ring-true is "one speech act, one contract, three surfaces" (models.Insight);
    # the insight surface has fired memory_feedback since Γ-2 and this one has fired
    # nothing, so a mirror verdict was stored and never counted. Same event name,
    # not a second one: it is the same question ("how often is the room right"),
    # and `surface` keeps the surfaces separable without doubling the taxonomy.
    #
    # AFTER THE COMMIT, NEVER BEFORE — the Γ-1 rule. The commit above already
    # exists for the enqueue, so this needs no new line, only the right position.
    # Fired here rather than from the web for the reason memory_feedback was:
    # a recognition metric that counts only readers who accepted the analytics
    # cookie measures consent, not recognition.
    #
    # NO insight_type: a mirror has no such column, and the registry permits a
    # site to omit a property it cannot know. The note is never a property in any
    # form — verdict is a Literal at the edge, and that is the whole payload.
    analytics_service.track("memory_feedback", user.id, {
        "verdict": mirror.ring_true,
        "surface": "mirror",
    })

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
    Mint a share for a mirror's closing reflection and return its card.
    Returns raw image/png bytes; the share's link is on the card as a QR.
    20/day + 5/min for every tier (PR-1).
    """
    user, _plan = auth
    # One creation path for all six kinds (PR-1) — see routers/share.py. The
    # per-router rate limit that used to sit here applied to three of the six
    # kinds and only to free users; it is now 20/day + 5/min for everyone,
    # enforced inside share_service.
    return await create_and_render(
        db=db, user_id=user.id,
        artifact_type="mirror", artifact_id=mirror_id,
        generator=generate_mirror_share_image,
        mirror_id=mirror_id,
    )
