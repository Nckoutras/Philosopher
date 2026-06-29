import logging

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
)
from services.preferences_service import (
    get_user_preferences,
    upsert_preferences,
    set_profile,
)
from services.matching_service import compute_matches
from services.profile_text import profile_to_statements
from services.self_comparison_service import self_comparison_service
from services.self_portrait import (
    answers_to_statements,
    get_question,
    is_free_question,
    portrait_state,
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
    )


@router.get("/self-portrait/portrait", response_model=SelfPortraitPortraitOut)
async def read_self_portrait_portrait(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The present-tense Self-Portrait payoff. Breadth-aware gate: 'forming' until
    the user's answers span enough life areas, then 'ready'. The payload NEVER
    carries a count/%/fraction — only `state` plus the surfaced content.

    5a slice: returns `state` + (always-usable) forming-preview lines derived from
    the user's OWN self-portrait answers via the existing forming_reflection path —
    so the endpoint is never empty. The cached Sonnet summary and persona best-fit
    arrive in 5b; until then `summary` is null and `best_fit` is empty, and the
    preview carries the surface (regardless of state). No LLM summary, no cache
    write, no best-fit here — `portrait_cache` (migration 039) is reserved storage.
    """
    prefs = await get_user_preferences(user_id=user.id, db=db)
    answers = ((prefs.profile if prefs else None) or {}).get("answers") or {}

    state = portrait_state(answers)

    # Observation lines from the user's own answers — describes HOW they answered,
    # never a diagnosis. Best-effort: forming_reflection returns [] on no answers or
    # failure, and the block simply renders nothing.
    statements = answers_to_statements(answers, limit=8)
    preview = (await self_comparison_service.forming_reflection(statements))[:2]

    return SelfPortraitPortraitOut(state=state, preview=preview, summary=None, best_fit=[])


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
