import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, get_current_user_plan
from db.session import get_db
from models import User
from schemas import (
    PreferenceUpsertRequest,
    PreferenceOut,
    MatchOut,
    ProfileIn,
    ProfileReflectionOut,
    SelfPortraitAnswerIn,
    SelfPortraitOut,
    SelfPortraitPortraitOut,
    BestFitOut,
)
from services.preferences_service import (
    get_user_preferences,
    upsert_preferences,
    set_profile,
)
from services.matching_service import compute_matches
from services.profile_text import profile_to_statements
from services.self_comparison_service import self_comparison_service
from services import self_portrait_summary
from services.self_portrait import (
    answered_category_count,
    answers_to_statements,
    get_question,
    is_free_question,
    portrait_state,
    portrait_theme_scores,
    PORTRAIT_REGEN_DELTA,
    total_category_count,
    total_question_count,
    visible_questions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.post("", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
async def upsert_user_preferences(
    body: PreferenceUpsertRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save (insert or replace) the current user's onboarding preferences."""
    record = await upsert_preferences(
        user_id=user.id,
        themes=body.themes,
        other_text=body.other_text,
        need_most=body.need_most,
        db=db,
    )
    return record


@router.get("", response_model=PreferenceOut)
async def read_user_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's preferences, or 404 if not yet set."""
    record = await get_user_preferences(user_id=user.id, db=db)
    if record is None:
        raise HTTPException(status_code=404, detail="Preferences not set")
    return record


@router.patch("/profile", response_model=PreferenceOut)
async def update_profile(
    body: ProfileIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instant-save the onboarding profile pills onto the user's preferences row,
    then enqueue the (async, embedded) memory seeding. Used by both the onboarding
    profile step and the standalone /app/profile editor."""
    record = await set_profile(user_id=user.id, profile=body.model_dump(), db=db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete the questionnaire first.",
        )

    # Seed embedded memory_entries off the request path (fire-and-forget).
    q = getattr(request.app.state, "arq_queue", None)
    if q is not None:
        try:
            await q.enqueue_job("seed_profile_memory_task", str(user.id))
        except Exception as e:
            logger.warning(f"Failed to enqueue profile memory seed: {e}")

    return record


@router.post("/profile/reflection", response_model=ProfileReflectionOut)
async def profile_reflection(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instant reflection at the end of onboarding. Reuses forming_reflection() over
    the SAME self-statements that seed memory (one shared helper). One cheap LLM call;
    returns [] on failure so the frontend can skip the beat silently."""
    prefs = await get_user_preferences(user_id=user.id, db=db)
    statements = profile_to_statements(prefs.profile if prefs else None)
    bullets = await self_comparison_service.forming_reflection(statements)
    return ProfileReflectionOut(bullets=bullets)


@router.get("/self-portrait", response_model=SelfPortraitOut)
async def read_self_portrait(
    auth: tuple = Depends(get_current_user_plan),
    db: AsyncSession = Depends(get_db),
):
    """Return the Self-Portrait questions this tier may see, the user's stored answers
    (filtered to the visible set), the tier flag, and the Pro-locked count.

    A fresh user with no preferences row still sees the questions (answers {}) — we do
    NOT 404 here; the quiz is reachable before the onboarding questionnaire is done."""
    user, plan = auth
    is_pro = plan in ("pro", "premium")
    qs = visible_questions(is_pro)

    prefs = await get_user_preferences(user_id=user.id, db=db)
    stored = ((prefs.profile if prefs else None) or {}).get("answers") or {}
    visible_ids = {q["id"] for q in qs}
    answers = {k: v for k, v in stored.items() if k in visible_ids}
    locked_count = 0 if is_pro else (total_question_count() - len(qs))

    return SelfPortraitOut(
        questions=qs,
        answers=answers,
        is_pro=is_pro,
        locked_count=locked_count,
        # From `stored`, NOT `answers`: the coverage number must describe what the user
        # actually answered, including categories whose questions this tier can no longer
        # see. Passing the filtered dict here would reintroduce the undercount on the
        # server side, which is the whole defect this closes.
        answered_category_count=answered_category_count(stored),
        total_category_count=total_category_count(),
    )


def _portrait_from_cache(
    state: str, cache: dict, theme_scores: list[dict]
) -> SelfPortraitPortraitOut:
    """Build the ready payload from a valid cache entry. No preview — a served
    summary never also carries forming lines. `theme_scores` (the curated radar axes)
    is computed on read and identical across every branch."""
    best_fit = [
        BestFitOut(
            slug=b["slug"],
            name=b["name"],
            portrait_url=b.get("portrait_url"),
            bio=b.get("bio"),
            why=b.get("why"),
        )
        for b in (cache.get("best_fit") or [])
        if isinstance(b, dict) and b.get("slug") and b.get("name")
    ]
    return SelfPortraitPortraitOut(
        state=state, preview=[], summary=cache.get("text"),
        best_fit=best_fit, theme_scores=theme_scores,
    )


@router.get("/self-portrait/portrait", response_model=SelfPortraitPortraitOut)
async def read_self_portrait_portrait(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The present-tense Self-Portrait payoff. Breadth-aware gate: 'forming' until
    the user's answers span enough life areas, then 'ready'. The payload NEVER
    carries a count/%/fraction — only `state` plus the surfaced content.

    Ready path (5b): serve the cached Sonnet summary + persona best-fit; regenerate
    synchronously only when the cache is missing or >= PORTRAIT_REGEN_DELTA new
    answers stale, then write `portrait_cache`. A valid/fresh cache is served WITHOUT
    calling forming_reflection — a ready open never pays for both LLM paths. Summary
    generation is best-effort: any failure falls back to a prior cache or the forming
    preview and still returns 200 (a summary failure never 500s the portrait).

    Forming path: `state` + observation lines from the user's OWN answers via the
    cheap forming_reflection — describes HOW they answered, never a diagnosis.
    """
    prefs = await get_user_preferences(user_id=user.id, db=db)
    answers = ((prefs.profile if prefs else None) or {}).get("answers") or {}
    state = portrait_state(answers)
    cache = (prefs.portrait_cache if prefs else None) or None

    # B1: curated radar axes — computed on read from answers (no migration, no count
    # on the wire), identical in every branch below.
    scores = portrait_theme_scores(answers)

    if state == "ready":
        watermark = (cache or {}).get("answer_count_watermark")
        fresh = (
            cache is not None
            and isinstance(watermark, int)
            and (len(answers) - watermark) < PORTRAIT_REGEN_DELTA
            and isinstance(cache.get("text"), str)
            and cache["text"].strip()
        )
        if fresh:
            return _portrait_from_cache(state, cache, scores)

        # Missing or stale → regenerate (synchronous, best-effort) — UNLESS a recent
        # failure is still within the retry cooldown, in which case skip the call so
        # an LLM outage doesn't re-fire the ~2-4s generation on every open.
        if not self_portrait_summary.in_failure_cooldown(cache):
            generated = await self_portrait_summary.generate_portrait(
                db=db,
                user_id=user.id,
                answers=answers,
                need_most=(prefs.need_most if prefs else "") or "",
            )
            if generated is not None:
                prefs.portrait_cache = generated
                await db.commit()
                return _portrait_from_cache(state, generated, scores)

            # Failure: stamp a `last_failed_at` marker (negative cache) so the next
            # opens serve forming/stale without re-attempting until the cooldown
            # elapses. Merged in, so any prior good summary survives; a later success
            # replaces the dict and drops the marker (self-heal).
            prefs.portrait_cache = self_portrait_summary.mark_failed(cache)
            await db.commit()

        # In cooldown OR just-failed: serve a prior valid summary if we have one,
        # else fall through to the forming preview below.
        if cache and isinstance(cache.get("text"), str) and cache["text"].strip():
            return _portrait_from_cache(state, cache, scores)

    # Forming, OR ready with no usable summary cache. The forming preview is cached in
    # the SAME portrait_cache under an INDEPENDENT `forming` sub-key, mirroring the
    # ready path exactly: serve verbatim when fresh, else regenerate (unless a recent
    # failure is still in the shared cooldown), write, serve; on failure mark_failed +
    # serve any stale preview. This keeps forming lines STABLE on reopen — they change
    # only after >= PORTRAIT_REGEN_DELTA new answers, never on wording-resample. The
    # `forming` and ready sub-keys are independent; neither stomps the other.
    forming = (cache or {}).get("forming") if isinstance(cache, dict) else None
    f_watermark = (forming or {}).get("answer_count_watermark")
    f_preview = (forming or {}).get("preview")
    f_fresh = (
        isinstance(forming, dict)
        and isinstance(f_watermark, int)
        and (len(answers) - f_watermark) < PORTRAIT_REGEN_DELTA
        and isinstance(f_preview, list)
        and len(f_preview) > 0
    )
    if f_fresh:
        return SelfPortraitPortraitOut(
            state=state, preview=f_preview[:2], summary=None, best_fit=[],
            theme_scores=scores,
        )

    # Missing or stale → regenerate, UNLESS a recent generation failure (ready OR
    # forming — the cooldown marker is shared) is still within the retry window, so an
    # LLM outage doesn't re-fire forming_reflection on every open. Only attempt when we
    # actually have statements AND a row to write the cache onto.
    statements = answers_to_statements(answers, limit=8)
    if prefs is not None and statements and not self_portrait_summary.in_failure_cooldown(cache):
        preview = (await self_comparison_service.forming_reflection(statements))[:2]
        if preview:
            merged = dict(cache) if isinstance(cache, dict) else {}
            merged["forming"] = {
                "preview": preview,
                "answer_count_watermark": len(answers),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            prefs.portrait_cache = merged
            await db.commit()
            return SelfPortraitPortraitOut(
                state=state, preview=preview, summary=None, best_fit=[],
                theme_scores=scores,
            )

        # Empty despite having statements → treat as a generation failure: stamp the
        # shared `last_failed_at` marker (merged, so a prior ready summary AND any stale
        # forming preview survive), so the next opens serve stale without re-attempting
        # until the cooldown elapses. A later success replaces the dict (self-heal).
        prefs.portrait_cache = self_portrait_summary.mark_failed(cache)
        await db.commit()

    # In cooldown, just-failed, or nothing to generate from: serve a stale forming
    # preview if we have one, else empty (the frontend renders the calm "still
    # forming" message).
    if isinstance(f_preview, list) and f_preview:
        return SelfPortraitPortraitOut(
            state=state, preview=f_preview[:2], summary=None, best_fit=[],
            theme_scores=scores,
        )
    return SelfPortraitPortraitOut(
        state=state, preview=[], summary=None, best_fit=[], theme_scores=scores
    )


@router.patch("/self-portrait", response_model=PreferenceOut)
async def update_self_portrait(
    body: SelfPortraitAnswerIn,
    request: Request,
    auth: tuple = Depends(get_current_user_plan),
    db: AsyncSession = Depends(get_db),
):
    """Persist one Self-Portrait quiz answer and (async) seed it into memory.

    Validates the answer against the question bank, MERGES it into profile.answers
    (preserving the onboarding pills and every other already-answered question), then
    enqueues an incremental, embedded memory seed for just this question. The answer
    reaches chat via memory recall and the Sunday/season letters — never the turn-1
    <what_we_know> block."""
    user, plan = auth
    question = get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=400, detail="Unknown question_id.")
    pills = question.get("pills") or []
    if not (0 <= body.pill_index < len(pills)):
        raise HTTPException(status_code=400, detail="pill_index out of range for this question.")

    if plan not in ("pro", "premium") and not is_free_question(body.question_id):
        raise HTTPException(status_code=403, detail="This question is part of Pro.")

    prefs = await get_user_preferences(user_id=user.id, db=db)
    if prefs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete the questionnaire first.",
        )

    # Merge this one answer into the existing answers sub-dict, then let set_profile
    # shallow-merge {answers: ...} into the profile (preserving values / disagreement).
    # Capture the prior answer FIRST so the seed task can detect a re-answer (edit-as-change).
    existing_answers = (prefs.profile or {}).get("answers") or {}
    old_index = existing_answers.get(body.question_id)
    answers = {**existing_answers, body.question_id: body.pill_index}
    record = await set_profile(user_id=user.id, profile={"answers": answers}, db=db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete the questionnaire first.",
        )

    # Incremental seed off the request path (fire-and-forget); one embed per tap.
    q = getattr(request.app.state, "arq_queue", None)
    if q is not None:
        try:
            await q.enqueue_job("seed_self_portrait_memory_task", str(user.id), body.question_id, old_index)
        except Exception as e:
            logger.warning(f"Failed to enqueue self-portrait memory seed: {e}")

    return record


@router.get(
    "/matches",
    response_model=list[MatchOut],
    summary="Get top 3 persona matches based on saved preferences",
)
async def get_matches(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MatchOut]:
    """Compute persona matches based on the user's saved preferences.

    Returns 404 if the user hasn't completed the questionnaire yet.
    """
    prefs = await get_user_preferences(user_id=user.id, db=db)
    if prefs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete the questionnaire first to see your matches.",
        )

    matches = compute_matches(
        user_themes=prefs.themes,
        user_need_most=prefs.need_most,
        top_n=9,
    )

    return [
        MatchOut(slug=m.slug, score=m.score, reason=m.reason)
        for m in matches
    ]
