from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models import User, MemoryEntry, Insight
from schemas import (
    MemoryEntryOut, MemoryEntryUpdate, InsightOut, InsightRingTrueRequest,
    MirrorOut, CounterviewOut,
)
from auth import get_current_user
from services.safety_service import safety_service
from services.analytics_service import analytics_service
from services.insight_mirror_service import generate_insight_mirror
from services.memory_service import (
    reactivate_cited_memories,
    reject_cited_memories,
    reject_verdict_shift,
    shift_anchor,
    verdict_entry,
    verdict_shift_days,
)
from services.enqueue import safe_enqueue
from services.counterview_service import (
    generate_counterview,
    find_counterview_for_insight,
    resolve_insight_anchor,
)
from services.rate_limit_service import check_fair_use_limit
from services.tier_service import get_user_tier
# Reuse the mirrors router's serializer + persona loader so the insight-mirror
# response stays a 1:1 match with /mirrors (one source of truth, no drift).
from routers.mirrors import _mirror_out, _load_persona
# Reuse the counterview router's serializer so the insight-counterview response
# stays a 1:1 match with /counterview (one source of truth, no drift).
from routers.counterview import _serialize_counterview

memory_router = APIRouter(prefix="/memory", tags=["memory"])
insights_router = APIRouter(prefix="/insights", tags=["insights"])


# ── Memory ────────────────────────────────────────────────────────────────────

@memory_router.get("", response_model=list[MemoryEntryOut])
async def get_memory(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user.id, MemoryEntry.is_active == True)
        .order_by(MemoryEntry.created_at.desc())
        .limit(100)
    )
    return [MemoryEntryOut.model_validate(m) for m in result.scalars().all()]


@memory_router.patch("/{memory_id}", response_model=MemoryEntryOut)
async def update_memory(
    memory_id: str,
    body: MemoryEntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == memory_id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404)
    if body.content is not None:
        entry.content = body.content
    if body.is_active is not None:
        entry.is_active = body.is_active
        # inactive_reason follows is_active (070) so the two cannot disagree: a
        # row switched off here is the person's removal, and a row switched back
        # on carries no reason for being off.
        entry.inactive_reason = None if body.is_active else "user_removed"
    await db.flush()
    return MemoryEntryOut.model_validate(entry)


@memory_router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MemoryEntry).where(MemoryEntry.id == memory_id, MemoryEntry.user_id == user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404)
    entry.is_active = False
    entry.inactive_reason = "user_removed"


# ── Insights ──────────────────────────────────────────────────────────────────

@insights_router.get("", response_model=list[InsightOut])
async def get_insights(
    conversation_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Insight)
        .where(Insight.user_id == user.id, Insight.is_dismissed == False)
    )
    if conversation_id is not None:
        query = query.where(Insight.conversation_id == conversation_id)
    query = query.order_by(Insight.created_at.desc()).limit(20)
    result = await db.execute(query)
    return [InsightOut.model_validate(i) for i in result.scalars().all()]


@insights_router.patch("/{insight_id}/dismiss", status_code=204)
async def dismiss_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404)
    insight.is_dismissed = True


def _utcnow() -> datetime:
    """The verdict's clock. A seam so the 72h guard's boundary can be tested exactly."""
    return datetime.now(timezone.utc)


@insights_router.patch("/{insight_id}/ring-true", response_model=InsightOut)
async def set_insight_ring_true(
    insight_id: str,
    body: InsightRingTrueRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The reader's verdict on what the room noticed.

    NOT PRO-GATED, deliberately and unlike every other insight door here
    (/reflect and /counterview both are). Saying "that is not true of me" is the
    one thing a person must be able to do about a claim the product has made
    about them, and putting it behind a subscription would make correction a paid
    feature. get_current_user, not get_current_user_plan, for that reason.

    DOES NOT TOUCH is_dismissed. A 'no' records disagreement and leaves the card
    where it is; Discard remains the only dismissal. The reason is mechanical as
    well as editorial: the 6h insight throttle counts non-dismissed insights
    (services/memory_service.py), so a verdict that dismissed would quietly widen
    how often the room may notice anything, as a side effect of someone
    disagreeing with it.

    OVERWRITE IS ALLOWED — a person may change their mind, and the timestamp
    moves with the answer. ring_true/ring_true_at hold the CURRENT verdict, which
    is what every reader of them wants; verdict_history (072, MEM2-B2) keeps every
    verdict written since 072 deployed, appended here on each write.
    """
    result = await db.execute(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404)

    # The previous verdict, read BEFORE it is overwritten: the 72h guard needs the
    # 'no' this 'yes' answers, and the legacy fallback needs ring_true_at.
    prior_history = list(insight.verdict_history or [])
    previous_verdict, previous_at = insight.ring_true, insight.ring_true_at

    now = _utcnow()
    insight.ring_true = body.ring_true
    insight.ring_true_at = now
    # A NEW list, not an in-place append: a JSONB column is not mutation-tracked,
    # and an appended list would be the same object and never be written.
    insight.verdict_history = prior_history + [verdict_entry(body.ring_true, now)]

    # MEM2 R3: a 'no' retires the memory rows the insight was derived from, so a
    # claim the person rejected stops being recalled into what the room says to
    # them. It also retires this insight's active shift entry (B2): "they came to
    # accept it" is no longer true. A no-op when evidence is NULL — signal insights
    # carry none yet (R4, Phase B).
    #
    # MEM2-B2: a 'yes' REACTIVATES the cited rows retired as 'user_rejected' —
    # on every 'yes', not only one that follows a 'no', because another insight
    # may have retired them (Q5). When this 'yes' answers a 'no' on the same
    # insight at least 72h earlier, a shift entry is owed too, written by its own
    # task after the commit below. A DISMISSED insight does neither: a dismissed
    # card is silent everywhere (founder ruling 2026-10-03). Its verdict and
    # history are still recorded.
    #
    # All of these run BEFORE the commit, in the verdict's transaction. 'partly'
    # does nothing (R6).
    shift_days = None
    if body.ring_true == "no":
        await reject_cited_memories(db, user.id, insight.evidence)
        await reject_verdict_shift(db, user.id, insight.id)
    elif body.ring_true == "yes" and not insight.is_dismissed:
        await reactivate_cited_memories(db, user.id, insight.evidence)
        shift_days = verdict_shift_days(
            shift_anchor(prior_history, previous_verdict, previous_at), now,
        )

    # EXPLICIT commit, so the event below genuinely fires after one. get_db
    # commits in its teardown (db/session.py), AFTER the handler returns — so a
    # track() call placed here without this line would report a write that had
    # not happened yet, and would still report it if the teardown commit failed.
    # The Γ-1 rule (letter_open_to_app) is "after the commit, never before", and
    # on this router that takes a line rather than an ordering.
    await db.commit()

    # insight_type may be None on rows written before the type existed; sent as
    # None rather than a stand-in string, the letter_delivered precedent. verdict
    # is safe by construction — a Literal at the edge, so no other value reaches
    # here, and the request body never becomes a property in any other form.
    #
    # Γ-5: `surface` is sent EXPLICITLY here rather than assumed in the dashboard.
    # Ring-true is "one speech act, one contract, three surfaces" (models.Insight),
    # and until Γ-5 only this one of the three fired an event — two thirds of the
    # verdicts the product collects were stored and never counted. Now that mirrors
    # and self_comparisons fire too, a breakdown by surface is only honest if every
    # event carries the property: an absent value on the oldest call site would
    # read as a fourth category made of the rows that predate the others.
    analytics_service.track("memory_feedback", user.id, {
        "insight_type": insight.insight_type,
        "verdict": insight.ring_true,
        "surface": "insight",
    })

    # After the commit, so the task never reads a 'yes' that is not there yet. The
    # task re-checks the verdict when it runs, because the person may have
    # answered 'no' again in between.
    if shift_days is not None:
        await safe_enqueue(
            getattr(request.app.state, "arq_queue", None),
            "record_verdict_shift_task",
            str(user.id),
            str(insight.id),
            shift_days,
            context=f"user={user.id} insight={insight.id}",
        )

    return InsightOut.model_validate(insight)


@insights_router.post("/{insight_id}/reflect", response_model=MirrorOut)
async def reflect_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate (or return the existing) insight-seeded mirror for this insight.
    Synchronous — the caller waits for generation. Status 'empty'/'suppressed'
    is returned as a clean 200 (with null payload) for the frontend to handle,
    not an error."""
    try:
        mirror = await generate_insight_mirror(db, user.id, insight_id)
    except ValueError:
        raise HTTPException(status_code=404)

    persona = await _load_persona(db, mirror.host_persona_id)
    return _mirror_out(mirror, persona)


@insights_router.post("/{insight_id}/counterview", response_model=CounterviewOut)
async def counterview_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate (or return the existing) counterview seeded from this insight.
    Synchronous — the caller waits for generation. Status 'empty'/'suppressed'
    is returned as a clean 200 (responses=[]) for the frontend to handle, not
    an error.

    TD-70: this door spends the same five persona generations the direct path
    does, and check_fair_use_limit counts its rows either way — so leaving it
    uncapped left the cap with an open door beside it. The cap below is the SAME
    check the direct path runs, in the SAME order, and the ordering is the whole
    design: dedup first, then safety, then quota.
    """
    # ── 1) The anchor, and the 404 ────────────────────────────────────────────
    # Ownership is established before anything else is read or refused. The
    # service resolves this again on the way through; the lookup is shared so the
    # two cannot disagree about what "not found" means.
    try:
        insight = await resolve_insight_anchor(db, user.id, insight_id)
    except ValueError:
        raise HTTPException(status_code=404)

    # ── 2) DEDUP BEFORE QUOTA ─────────────────────────────────────────────────
    # A second tap on the same insight returns the row that already exists. It
    # generates nothing, so it must cost nothing: the cap is skipped entirely
    # rather than checked-and-passed. Re-reading a counterview you already own
    # can never be refused, and never moves the counter.
    existing = await find_counterview_for_insight(db, insight_id)

    if existing is None:
        # ── 3) CRISIS BEFORE QUOTA ────────────────────────────────────────────
        # The #591 ordering, and the same product rule the direct path states: a
        # crisis position is never answered with a quota. The same person can
        # arrive at the same state through either door, so the rule cannot live
        # on one of them.
        #
        # This sees insight.content ONLY — one layer short of the service, which
        # additionally suppresses on a flagged source conversation behind this
        # check. That is deliberate: it is exactly the guarantee the direct path
        # gives for its own anchor text, and the deeper check still runs.
        safety_in = await safety_service.check_input(insight.content, user.id)
        if not safety_in.should_suppress_persona and not user.is_admin:
            tier = await get_user_tier(db, user.id)
            fair_use = await check_fair_use_limit(db, user.id, user_tier=tier)
            if not fair_use.allowed:
                # 'insight_counterview', not 'counterview': the two doors carry
                # different cap semantics (the free daily cap governs only the
                # direct one) and different intent, and merging them would make
                # this series unable to answer which door hit the ceiling — the
                # question that found TD-70 in the first place.
                analytics_service.track("usage_cap_hit", user.id, {
                    "tier": tier,
                    "cap_kind": (
                        "pro_fair_use_monthly" if fair_use.period == "month" else "pro_fair_use"
                    ),
                    "path": "insight_counterview",
                })
                return JSONResponse(
                    status_code=429,
                    content={"error_code": "fair_use_limit", "period": fair_use.period},
                    headers={
                        "X-RateLimit-Limit": str(fair_use.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": fair_use.reset_at.isoformat(),
                    },
                )

    # The free daily cap (check_counterview_limit) is NOT applied here, by
    # design: it counts source='direct' rows only and its docstring says this
    # path never consumes that allowance. A free user stays bounded transitively
    # — one counterview per insight, and insights come from chat, which is capped.
    try:
        cv = await generate_counterview(db, user.id, insight_id=insight_id, source="insight")
    except ValueError:
        raise HTTPException(status_code=404)
    return await _serialize_counterview(db, cv, user.id)
