import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Conversation, Insight, Message, Mirror, Persona
from services.llm_client import llm_client

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

    # ── Source conversation + host persona ────────────────────────────────────
    conversation = None
    if insight.conversation_id is not None:
        conversation = (
            await db.execute(
                select(Conversation).where(Conversation.id == insight.conversation_id)
            )
        ).scalar_one_or_none()

    host_persona_id = insight.persona_id or (conversation.persona_id if conversation else None)

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
    system = INSIGHT_MIRROR_PROMPT.format(
        persona_name=persona.name if persona else "A thoughtful observer",
        persona_tradition_clause=persona_tradition_clause,
    )

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
    except Exception as e:
        # Degrade gracefully to 'empty' rather than surfacing a 500 to the user.
        logger.warning("Insight mirror generation failed insight=%s: %s", insight_id, e)
        payload = None

    if payload is None:
        return await _write_mirror(
            db, user_id, insight_id, host_persona_id, now, status="empty"
        )

    return await _write_mirror(
        db, user_id, insight_id, host_persona_id, now,
        status="generated", payload=payload,
    )


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
