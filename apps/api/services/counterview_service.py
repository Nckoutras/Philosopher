import json
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Counterview, CounterviewResponse, Insight, Message
from services.llm_client import llm_client
from services.safety_service import safety_service

logger = logging.getLogger(__name__)

# Musashi on the left (position 0), Machiavelli on the right (position 1).
COUNTERVIEW_PERSONAS = [("miyamoto_musashi", 0), ("niccolo_machiavelli", 1)]

# Per-line ceiling. Verdicts over this trigger ONE tightening retry (we never cut
# a line mid-sentence — a marginally-long retry is kept).
MAX_WORDS = 15

COUNTERVIEW_PROMPT = """You are giving the CASE AGAINST a position a person holds. Two distinct minds answer, each in one sharp line.

You receive the person's stated position, in their own words. Do not agree, soften, or reassure. Show — briefly and without cruelty — where it is weak: a contradiction, a blind spot, a cost they are not counting, an angle they have not considered.

Two voices, each ONE line, 15 words MAXIMUM:
- Miyamoto Musashi — the discipline of action. He sees drift dressed as patience, fear dressed as care, the price of not moving.
- Niccolo Machiavelli — the reading of motive and power. He sees the convenient story, the hidden self-interest, the resolve that is missing.

The two lines must come from DIFFERENT angles — never say the same thing twice.

Hard rules:
- Anchor STRICTLY to what the person actually wrote. Never invent a fact, a history, or a detail they did not state. If you are adding information, stop — that is hallucination.
- Attack the position, the contradiction, the blind spot — NEVER the person. No insults, no contempt, nothing below the belt.
- If the position genuinely holds, do not fake an objection — name its cost, or the thing it quietly ignores.
- Plain, modern language. No archaic phrasing, no quotes, never name yourself. One clean cut.
- 15 words max per line. Shorter is stronger.

Return JSON only, no preamble, exactly:
{"status":"generated","verdicts":[{"persona":"miyamoto_musashi","verdict":"..."},{"persona":"niccolo_machiavelli","verdict":"..."}]}

If there is genuinely nothing to push against, return exactly: {"status":"empty"}"""

# Appended to the system prompt for the single tightening retry.
TIGHTEN_DIRECTIVE = "\n\nYour previous attempt exceeded 15 words on at least one line. Rewrite BOTH lines to 15 words maximum each. Cut every non-essential word — keep the same meaning, the same two distinct angles, the same JSON shape."


async def generate_counterview(
    db: AsyncSession,
    user_id: str,
    *,
    belief: str | None = None,
    insight_id: str | None = None,
    source: str,
) -> Counterview:
    """Synchronously generate (or, for the insight path, return the existing)
    counterview for one anchor position.

    Raises ValueError("counterview anchor not found") only when an insight path
    references an insight that does not belong to the user. Every other failure
    (LLM error, parse failure, safety trip) degrades to a clean persisted status
    ('empty' / 'suppressed') — never a 500 to the caller.
    """
    # ── 1) Resolve the anchor (may raise ValueError) ──────────────────────────
    insight: Insight | None = None
    if source == "insight":
        if not insight_id:
            raise ValueError("counterview anchor not found")
        insight = (
            await db.execute(
                select(Insight).where(
                    Insight.id == insight_id,
                    Insight.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if insight is None:
            raise ValueError("counterview anchor not found")
        anchor_text = insight.content

        # ── 2) App-level dedup (insight only): one counterview per insight, no LLM
        existing = (
            await db.execute(
                select(Counterview).where(Counterview.insight_id == insight_id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    else:
        anchor_text = (belief or "").strip()

    # ── 3) Pre-generation safety gate ─────────────────────────────────────────
    res = await safety_service.check_input(anchor_text, user_id)
    if res.should_suppress_persona:
        return await _write_counterview(
            db, user_id, source, insight_id, anchor_text, status="suppressed"
        )

    # Insight path: the source conversation may carry a high/critical user message
    # even if the distilled insight text reads clean — suppress on that too.
    if source == "insight" and insight is not None and insight.conversation_id is not None:
        messages = (
            await db.execute(
                select(Message).where(
                    Message.conversation_id == insight.conversation_id,
                    Message.role == "user",
                )
            )
        ).scalars().all()
        if any(m.safety_level in ("medium", "high", "critical") for m in messages):
            return await _write_counterview(
                db, user_id, source, insight_id, anchor_text, status="suppressed"
            )

    # ── 4-5) Generate (+ one tightening retry on over-length) ─────────────────
    verdicts = None
    try:
        verdicts = await _call_llm(anchor_text)
        if verdicts is not None and any(_word_count(v[2]) > MAX_WORDS for v in verdicts):
            retry = await _call_llm(anchor_text, tighten=True)
            if retry is not None:
                verdicts = retry
    except Exception as e:
        # Degrade gracefully to 'empty' rather than surfacing a 500.
        logger.warning("Counterview generation failed user=%s: %s", user_id, e)
        verdicts = None

    if not verdicts:
        return await _write_counterview(
            db, user_id, source, insight_id, anchor_text, status="empty"
        )

    # ── 6) Post-generation safety: any flagged verdict suppresses the whole set
    for _slug, _pos, vtext in verdicts:
        out = await safety_service.check_output(vtext)
        if out.should_suppress_persona:
            return await _write_counterview(
                db, user_id, source, insight_id, anchor_text, status="suppressed"
            )

    # ── 7) Persist generated counterview + its two responses ──────────────────
    return await _write_counterview(
        db, user_id, source, insight_id, anchor_text,
        status="generated", verdicts=verdicts,
    )


async def _call_llm(anchor_text: str, *, tighten: bool = False):
    """One LLM call → list of [slug, position, verdict] in COUNTERVIEW_PERSONAS
    order, or None if the model returned non-'generated' / unparseable / an
    incomplete persona set."""
    system = COUNTERVIEW_PROMPT + (TIGHTEN_DIRECTIVE if tighten else "")
    raw = await llm_client.complete(
        system=system,
        user=f"<position>\n{anchor_text}\n</position>",
        model=config.ANTHROPIC_MODEL,
        max_tokens=300,
    )
    return _extract_verdicts(raw)


def _extract_verdicts(raw: str):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text[:-3].rstrip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("status") != "generated":
        return None

    by_persona = {}
    for item in data.get("verdicts") or []:
        if isinstance(item, dict):
            verdict = (item.get("verdict") or "").strip()
            if verdict:
                by_persona[item.get("persona")] = verdict

    result = []
    for slug, position in COUNTERVIEW_PERSONAS:
        verdict = by_persona.get(slug)
        if not verdict:
            return None  # incomplete set → treat as empty
        result.append([slug, position, verdict])
    return result


def _word_count(text: str) -> int:
    return len(text.split())


async def _write_counterview(
    db: AsyncSession,
    user_id: str,
    source: str,
    insight_id: str | None,
    anchor_text: str | None,
    *,
    status: str,
    verdicts: list | None = None,
) -> Counterview:
    """Insert the counterview (+ responses when generated), race-safe against the
    partial unique index on insight_id: on IntegrityError (a concurrent insight
    double-tap won the insert) roll back and return the row that already landed."""
    eff_insight_id = insight_id if source == "insight" else None
    counterview = Counterview(
        user_id=user_id,
        source=source,
        insight_id=eff_insight_id,
        anchor_text=anchor_text,
        status=status,
    )
    db.add(counterview)
    try:
        await db.flush()
        if status == "generated" and verdicts:
            for slug, position, vtext in verdicts:
                db.add(CounterviewResponse(
                    counterview_id=counterview.id,
                    persona_slug=slug,
                    round=0,
                    position=position,
                    verdict=vtext,
                ))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if eff_insight_id is not None:
            existing = (
                await db.execute(
                    select(Counterview).where(Counterview.insight_id == eff_insight_id)
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
        raise
    await db.refresh(counterview)
    return counterview
