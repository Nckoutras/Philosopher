import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Insight, Message, Mirror, Persona, User
from services.llm_client import llm_client
from text_utils import dominant_language, language_directive, language_matches

logger = logging.getLogger(__name__)

# Minimum user messages in the source conversation for an insight mirror to be
# worth generating. Lower than the weekly mirror's 5: this reflection is anchored
# on a known recurring thread and a single conversation, so it needs less to work.
INSIGHT_MIRROR_MIN_MESSAGES = 2

# Insight-seeded variant of the weekly MIRROR_PROMPT. Same said/meant/thread JSON
# shape (so MirrorOut rendering / MirrorVerdictCard are unchanged), but oriented
# to ONE conversation and anchored on a thread already noticed across the person's
# reflections. It carries over the weekly mirror's wellbeing guardrails verbatim
# in spirit: charged-kernel "said", genuine interpretation "meant", a lens-not-a-
# verdict "thread", at least one moment honoring what the person was reaching for,
# and see-clearly-not-cruelly framing.
INSIGHT_MIRROR_PROMPT = """You are {persona_name}{persona_tradition_clause}. You are holding up a mirror to a person — not to summarize a conversation, but to show them the deeper meaning beneath their own words, seen through your distinct way of understanding.

A recurring thread has already been noticed in this person's reflections. You will receive that thread, and the person's messages from the one conversation where it surfaced.

1. Anchored on the noticed thread, select the 2-3 moments from this conversation that carry the most emotional weight — where the person revealed something real (a fear, a longing, a contradiction, a vulnerability) that speaks to the thread. Choose through YOUR lens — what YOU would find significant. Prefer 2 unless a third is genuinely distinct.
2. For each, capture what they SAID and interpret what they MEANT. "said" = the single charged phrase in their own words — the kernel that carries the weight, NOT the whole passage. Trim hard to one short line. "meant" = one or two sentences of genuine interpretation in your voice, going beneath the phrase to what they were really reaching for.
3. Name the single thread that runs through these moments — one sentence, your closing reflection. Address the person directly in the second person ("you"), as if speaking to them — never describe them in the third person ("a person", "they", "themselves"). Offer it as a lens, never as a verdict about who they are.

Return JSON only, no preamble, in exactly this shape:
{{"status": "generated", "moments": [{{"said": "...", "meant": "..."}}], "thread": "..."}}

If the conversation holds nothing significant enough to reflect on, return exactly: {{"status": "empty"}}

Rules:
- "moments": 2-3 items, prefer 2. "said" = the person's actual words, the charged kernel only — one short line, trim aggressively. "meant" = genuine interpretation in your voice.
- At least one moment — even when you choose only two — must honor what the person was reaching for: a longing, a courage, a real attempt. Do not let every moment be a confrontation. See clearly, not cruelly. A mirror reveals a person to themselves; it does not indict them.
- "thread": one sentence, offered as a lens, never a verdict.
- Frame every reading as a lens you are offering, never a verdict you are delivering. Prefer "you may be...", "perhaps...", "what if..." over flat pronouncements about who they are. Sharpness is welcome; certainty about their character is not. Even a hard truth is offered as something to consider, not a sentence passed.
- Be grounded and brief. No clinical or therapy language. You are a reflective companion, not a therapist — never diagnose."""


async def generate_insight_mirror(
    db: AsyncSession,
    user_id: str,
    insight_id: str,
) -> Mirror:
    """Synchronously generate (or return the existing) insight-seeded mirror for
    one insight + its source conversation, in the source persona's voice.

    Reuses the whole Mirror artifact system (kind="insight"). The weekly task is
    untouched. Raises ValueError if the insight does not exist for this user.
    """
    # ── Load the insight (must belong to the user) ────────────────────────────
    insight = (
        await db.execute(
            select(Insight).where(
                Insight.id == insight_id,
                Insight.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if insight is None:
        raise ValueError("insight not found")

    # ── App-level dedup: one mirror per insight, no second LLM call ───────────
    existing = (
        await db.execute(
            select(Mirror).where(Mirror.insight_id == insight_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # ── Host persona ──────────────────────────────────────────────────────────
    # Host the insight mirror through the user's chosen weekly mirror host (the
    # persona behind their weekly reflection), NOT the source conversation's
    # persona — so insight reflections stay consistent with the weekly mirror.
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    host_slug = (user.mirror_host_slug if user else None) or "carl_jung"
    host_persona = (
        await db.execute(select(Persona).where(Persona.slug == host_slug))
    ).scalar_one_or_none()
    host_persona_id = host_persona.id if host_persona else None

    # User messages of the source conversation, oldest-first.
    messages = []
    if insight.conversation_id is not None:
        messages = (
            await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == insight.conversation_id,
                    Message.role == "user",
                )
                .order_by(Message.created_at.asc())
            )
        ).scalars().all()

    now = datetime.now(timezone.utc)

    # ── Safety gate (mirrors the weekly task): high/critical → suppressed ─────
    if any(m.safety_level in ("high", "critical") for m in messages):
        return await _write_mirror(
            db, user_id, insight_id, host_persona_id, now, status="suppressed"
        )

    # ── Empty gate: too little to reflect on ──────────────────────────────────
    if len(messages) < INSIGHT_MIRROR_MIN_MESSAGES:
        return await _write_mirror(
            db, user_id, insight_id, host_persona_id, now, status="empty"
        )

    # ── Generate ──────────────────────────────────────────────────────────────
    persona = None
    if host_persona_id is not None:
        persona = (
            await db.execute(select(Persona).where(Persona.id == host_persona_id))
        ).scalar_one_or_none()
    persona_tradition_clause = (
        (", " + persona.tradition) if persona and persona.tradition else ""
    )
    # THE MESSAGES, NOT insight.content. The thread is model-written and #628
    # enforces language on dilemma-typed insights only, so a belief- or
    # aspiration-seeded thread can already be in the wrong language; anchoring on
    # it would copy that into the mirror. `messages` is role == "user" throughout —
    # the person's own words with no persona text mixed in, which is exactly what
    # #627 found missing when a language was read off a whole transcript. The
    # INSIGHT_MIRROR_MIN_MESSAGES floor above guarantees at least two of them here,
    # so unlike counterview this path needs no fallback.
    language = dominant_language([m.content for m in messages])

    # APPENDED AFTER .format(), never inside it. This prompt is the one of the seven
    # that really is formatted: it carries 3 DOUBLED brace pairs for its JSON shape
    # alongside the two real fields, so the directive must not be routed through
    # the same call — it has no braces to escape and no business being scanned.
    system = INSIGHT_MIRROR_PROMPT.format(
        persona_name=persona.name if persona else "A thoughtful observer",
        persona_tradition_clause=persona_tradition_clause,
    ) + language_directive(language)

    convo_text = "\n".join(f"[{m.created_at:%b %d}] {m.content}" for m in messages)
    user_prompt = (
        f"<thread_noticed>{insight.content}</thread_noticed>\n"
        f"<conversation>\n{convo_text}\n</conversation>"
    )

    payload = None
    try:
        raw = await llm_client.complete(
            system=system,
            user=user_prompt,
            model=config.ANTHROPIC_MODEL,
            max_tokens=768,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].rstrip()
        data = json.loads(text)
        if data.get("status") == "generated":
            payload = {"thread": data.get("thread"), "moments": data.get("moments")}
            if payload is not None and not payload_language_matches(payload, language):
                logger.warning(
                    "insight_mirror_language_mismatch",
                    extra={"expected_language": language,
                           "insight_id": insight_id,
                           "user_id": user_id},
                )
                payload = None
    except Exception as e:
        # Degrade gracefully to 'empty' rather than surfacing a 500 to the user.
        logger.warning("Insight mirror generation failed insight=%s: %s", insight_id, e)
        payload = None

    # 'empty' is a first-class path: routers/memory.reflect_insight returns it as a
    # clean 200 with a null payload. It is also PERMANENT for this insight — the
    # dedup at the top returns any existing mirror regardless of status, so this is
    # never regenerated. Accepted for the same reason as the counterview: a
    # 'generated' wrong-language mirror would be stored and re-served by that same
    # dedup forever, which is worse than the empty state the frontend already draws.
    if payload is None:
        return await _write_mirror(
            db, user_id, insight_id, host_persona_id, now, status="empty"
        )

    return await _write_mirror(
        db, user_id, insight_id, host_persona_id, now,
        status="generated", payload=payload,
    )


def payload_language_matches(payload: dict, language: str) -> bool:
    """Is the model's OWN prose in the expected language?

    PUBLIC, and shared by BOTH mirrors. The weekly/preview mirror in
    workers/arq_worker.py produces a byte-identical payload shape from a
    byte-identical prompt, so it imports this rather than growing a second copy
    that can drift. If the shape ever diverges, this function splits — not the
    rule it encodes.

    Checks `thread` and every `meant` — the sentences the mirror writes. It does
    NOT check `said`, and that is deliberate twice over: `said` is the person's own
    charged phrase quoted back, so it is in their language by construction and a
    mismatch there would mean the quote was fabricated, not mistranslated; and it
    is trimmed to "one short line", which is usually under EN_MIN_TOKENS and so
    carries no ratio signal anyway.

    Missing or malformed fields are not a language failure — they are left to the
    existing parse handling, which nulls the whole payload on its own terms.
    """
    texts = [payload.get("thread")]
    for m in payload.get("moments") or []:
        if isinstance(m, dict):
            texts.append(m.get("meant"))
    checkable = [t for t in texts if isinstance(t, str) and t.strip()]
    return all(language_matches(t, language) for t in checkable)


async def _write_mirror(
    db: AsyncSession,
    user_id: str,
    insight_id: str,
    host_persona_id: str | None,
    now: datetime,
    *,
    status: str,
    payload: dict | None = None,
) -> Mirror:
    """Insert the insight mirror, race-safe against the partial unique index on
    insight_id: on IntegrityError (a concurrent double-tap won the insert) we
    roll back and return the row that already landed."""
    mirror = Mirror(
        user_id=user_id,
        host_persona_id=host_persona_id,
        insight_id=insight_id,
        period_start=now,
        period_end=now,
        kind="insight",
        status=status,
        payload=payload,
    )
    db.add(mirror)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = (
            await db.execute(
                select(Mirror).where(Mirror.insight_id == insight_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        raise
    await db.refresh(mirror)
    return mirror
