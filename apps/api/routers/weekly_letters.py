import logging
from services.analytics_service import analytics_service
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user_plan
from db.session import get_db
import services.rate_limit_service as rate_limit_service
from models import WeeklyLetter, Persona
from schemas import WeeklyLetterOut, WriteBackIn
from services.image_service import generate_letter_share_image

logger = logging.getLogger(__name__)

# Free-tier share cap — the SAME 90-day rolling Redis counter the mirror, line,
# and council share endpoints use (key: share_screenshot:{user_id}).
FREE_SHARE_LIMIT  = 3
SHARE_WINDOW_SECS = 90 * 24 * 60 * 60

router = APIRouter(prefix="/weekly-letters", tags=["weekly-letters"])

# Write-back length buckets for letter_write_back (Γ-5). Coarse on purpose, and
# the coarseness is a privacy property rather than a rounding convenience: the
# decision these inform is "is the correspondence one-liners or real replies",
# which four buckets answer, and an exact character count is a weak fingerprint
# of a text this event may never carry.
#
# The ceiling is WriteBackIn's 2,000-character cap (schemas.py), so `over_1200`
# is a real top bucket rather than an open tail — a write-back cannot exceed it.
_WRITE_BACK_LENGTH_BUCKETS = ((100, "under_100"), (400, "100_400"), (1200, "400_1200"))


def write_back_length_bucket(text: str) -> str:
    """The bucket for a write-back's length. A closed set of four, pinned by test.

    Takes the STRIPPED text the endpoint is about to store, so the number matches
    what a later `length(write_back_text)` in SQL would report — the two
    instruments must agree, because the runbook treats SQL as authoritative.

    There is no 'unknown' arm, unlike gap_bucket's: the endpoint 422s on empty
    input before this is reached, so every value here is a real non-empty string.
    """
    n = len(text)
    for limit, name in _WRITE_BACK_LENGTH_BUCKETS:
        if n < limit:
            return name
    return "over_1200"


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

    # 'failed' (A17) is an operator-visibility fact — a letter the LLM produced and
    # we lost to malformed JSON — never a user-facing state. Excluded here so the
    # client's status union stays true and the reader is never told "a quiet week"
    # about a week that was not quiet.
    result = await db.execute(
        select(WeeklyLetter)
        .where(
            WeeklyLetter.user_id == user.id,
            WeeklyLetter.status != "failed",
        )
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
    # Attribution marker from the weekly-letter email's read link (062). Typed
    # `str | None` and NOT a Literal/pattern on purpose: only the exact string
    # "email" has any effect, and every other value is ignored in silence. The
    # reason is the CheckoutRequest.source rationale in schemas/__init__.py --
    # a value this endpoint does not recognise is a reporting gap, never a reason
    # to refuse. A Literal here would answer 422 to a link an email client had
    # rewritten, and the person would lose their letter to an analytics
    # annotation. Analytics is an observer and may not change what the product
    # does. No free text can reach PostHog through this: `src` is never sent as a
    # property -- the event carries `week` and `host`, both read off the row.
    src: str | None = None,
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

    now = datetime.now(timezone.utc)

    # Mark read on first fetch. Unchanged: ANY door writes this, which is exactly
    # why it cannot answer the §16 gate on its own.
    touched = False
    if letter.read_at is None:
        letter.read_at = now
        touched = True

    # First email-attributed open. The NULL check is the idempotence: a second
    # visit from the same email -- or a forwarded link opened weeks later -- finds
    # a non-NULL column and changes nothing, so the timestamp keeps meaning "the
    # first time this letter's email brought someone back".
    email_open = src == "email" and letter.email_opened_at is None
    if email_open:
        letter.email_opened_at = now
        touched = True

    if touched:
        await db.commit()

    persona = None
    if letter.voice_persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == letter.voice_persona_id))
        persona = p_result.scalar_one_or_none()

    # After the commit, never before: this event means a return was recorded, not
    # that one was attempted. Fired SERVER-side deliberately -- its web twin would
    # need the analytics cookie, and consent is exactly the variable a delivery
    # gate must not depend on. `week` is the ISO week of period_start (the same
    # bucket letter_delivered sends, so the two join in the dashboard) and `host`
    # is the voice persona's slug. No letter text, no subject, no recipient.
    if email_open:
        analytics_service.track("letter_open_to_app", user.id, {
            "week": letter.period_start.strftime("%G-W%V") if letter.period_start else None,
            "host": persona.slug if persona is not None else None,
        })

    return _to_out(letter, persona)


@router.patch("/{letter_id}/write-back", response_model=WeeklyLetterOut)
async def write_back_to_letter(
    letter_id: str,
    body: WriteBackIn,
    request: Request,
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

    # Γ-5: read BEFORE the assignment below overwrites it. A re-submit overwrites
    # the prior write-back (this endpoint's documented behaviour), so after the
    # next line there is no way left to tell a first answer from a revision.
    is_first_write_back = letter.write_back_at is None

    letter.write_back_text = text
    letter.write_back_at = datetime.now(timezone.utc)
    # Explicit commit (not a bare flush): the enqueue below fires only once the
    # write-back is durably persisted, so a rollback at teardown can never orphan
    # a stored memory.
    await db.commit()

    # Γ-5 — the correspondence loop's closure, and the last of the three letter
    # events. letter_delivered says an email left the building; letter_open_to_app
    # says one brought a person back; this says they answered it. `week` and `host`
    # are spelled EXACTLY as those two spell them, which is what lets the three
    # join into one funnel rather than three unrelated counts.
    #
    # FIRST WRITE-BACK ONLY, the letter_open_to_app precedent: there, a NULL
    # email_opened_at IS the idempotence, and a second visit changes nothing. Here
    # a NULL write_back_at plays the same part. A revision is a person changing
    # their words, not the loop closing a second time, and counting it would make
    # the funnel's denominator mean two different things at once.
    #
    # The persona load moved ABOVE this from the bottom of the handler so `host`
    # costs no extra query; _to_out still uses the same object.
    #
    # length_bucket is one of four fixed strings over the stripped text. The text
    # ITSELF is never a property — not truncated, not hashed. What this event
    # answers is "does the correspondence get answered, and at what length", and a
    # bucket answers that completely.
    persona = None
    if letter.voice_persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == letter.voice_persona_id))
        persona = p_result.scalar_one_or_none()

    if is_first_write_back:
        analytics_service.track("letter_write_back", user.id, {
            "week": letter.period_start.strftime("%G-W%V") if letter.period_start else None,
            "host": persona.slug if persona is not None else None,
            "length_bucket": write_back_length_bucket(text),
        })

    # The write-back is the user's OWN words back to the letter — distil it into a
    # confidence-1.0 memory (safety-gated + word-filtered inside the task). Async;
    # conversation_id is None because a letter is not a conversation. Fire-and-forget;
    # never break the response. `text` is guaranteed non-empty (422 above).
    arq_queue = getattr(request.app.state, "arq_queue", None)
    if arq_queue is not None:
        try:
            await arq_queue.enqueue_job(
                "distill_user_text_to_memory_task",
                str(user.id),
                None,
                text,
                "letter_write_back",
            )
        except Exception as exc:
            logger.error(
                "Letter write-back enqueue failed user=%s letter=%s: %s",
                user.id, letter_id, exc,
            )

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

    # One event for every artifact a person chose to share. artifact_type is
    # the only property: there is no share_id yet (all six endpoints return raw
    # PNG bytes and persist nothing) and no channel (the OS share sheet never
    # tells us where it went). Both arrive with the P3 public share page, which
    # is also what makes share_landing_view and share_signup possible.
    analytics_service.track("share_created", user.id, {"artifact_type": "letter"})

    return Response(content=png_bytes, media_type="image/png")
