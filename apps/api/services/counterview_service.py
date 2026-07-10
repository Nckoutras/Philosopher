import json
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Counterview, CounterviewResponse, CounterviewTurn, Insight, Message
from services.llm_client import llm_client
from services.safety_service import safety_service

logger = logging.getLogger(__name__)

# Musashi on the left (position 0), Machiavelli on the right (position 1).
COUNTERVIEW_PERSONAS = [("miyamoto_musashi", 0), ("niccolo_machiavelli", 1)]

# Per-line ceiling. Verdicts over this trigger ONE tightening retry (we never cut
# a line mid-sentence — a marginally-long retry is kept).
MAX_WORDS = 10

# "What still stands" closing line cap. Prompt-enforced at 14; the server only
# nulls on GROSS overage (>= 1.5x = 21 words) — a marginal line ships, never cut
# mid-sentence. Mirrors the R1a _closing_line pattern.
STILL_STANDS_MAX_WORDS = 14

# Terrain title cap. Prompt-enforced at 2-4 words; the server hard-nulls anything
# longer (a title is a heading, not a sentence — no marginal tolerance).
TITLE_MAX_WORDS = 4

COUNTERVIEW_PROMPT = """You are giving the CASE AGAINST a position a person holds. Two distinct minds answer, each in one sharp line.

You receive the person's stated position, in their own words. Do not agree, soften, or reassure. Show — briefly and without cruelty — where it is weak: a contradiction, a blind spot, a cost they are not counting, an angle they have not considered.

Two voices, each ONE line, 10 words MAXIMUM:
- Miyamoto Musashi — the discipline of action. He sees drift dressed as patience, fear dressed as care, the price of not moving.
- Niccolo Machiavelli — the reading of motive and power. He sees the convenient story, the hidden self-interest, the resolve that is missing.

The two lines must come from DIFFERENT angles — never say the same thing twice.

Hard rules:
- Anchor STRICTLY to what the person actually wrote. Never invent a fact, a history, or a detail they did not state. If you are adding information, stop — that is hallucination.
- Attack the position, the contradiction, the blind spot — NEVER the person. No insults, no contempt, nothing below the belt.
- If the position genuinely holds, do not fake an objection — name its cost, or the thing it quietly ignores.
- Plain, modern language. No archaic phrasing, no quotes, never name yourself. One clean cut.
- 10 words max per line. Shorter is stronger.
- ONE idea, ONE blade. No em-dash or semicolon stitching two thoughts together — a single clean cut, not a compound sentence.

After the two cuts, add ONE quiet closing line — "what still stands": the part of their position that SURVIVES the challenge, the grain worth keeping once the weak parts fall away. ONE sentence, 14 words MAXIMUM, neutral and plain.
- This is NOT praise and NOT a third attack — it names, honestly, what of the belief remains true or worth holding.
- Anchor it STRICTLY to what they wrote, same as the cuts. Invent nothing.
- If nothing of the position honestly survives, use null — never manufacture one.

Finally, name the TERRAIN of the belief in a TITLE of 2-4 words: the abstract domain the position lives on, in the register of a quiet chapter heading (e.g. "Bravery and decisions", "Ambition and rest", "Loyalty and its limits").
- It names the theme, NEVER the confession. Do not summarise what they said, do not quote their words, do not judge, do not sell — no clickbait, no verdict, no "why you are wrong".
- Abstract and dignified: the ground the belief stands on, not the person standing on it.
- The "X and Y" shape is one option, not a template — "The shape of ambition", "When to walk away" are equally valid. Vary the form.
- If the position is too vague to name a clear terrain, choose the nearest honest theme rather than inventing drama.
- Same language as the person's position — if they wrote in Greek, the title is in Greek.

Return JSON only, no preamble, exactly:
{"status":"generated","verdicts":[{"persona":"miyamoto_musashi","verdict":"..."},{"persona":"niccolo_machiavelli","verdict":"..."}],"still_stands":"<one sentence, or null>","title":"<2-4 words naming the terrain>"}

If there is genuinely nothing to push against, return exactly: {"status":"empty"}"""

# Appended to the system prompt for the single tightening retry.
TIGHTEN_DIRECTIVE = "\n\nYour previous attempt exceeded 10 words on at least one line. Rewrite BOTH lines to 10 words maximum each. Cut every non-essential word — keep the same meaning, the same two distinct angles, the same JSON shape."


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
    # still_stands rides the same JSON as the verdicts; the tighten retry, when it
    # fires, adopts the retry response wholesale (both verdicts and its closing line).
    verdicts = None
    still_stands = None
    title = None
    try:
        verdicts, still_stands, title = await _call_llm(anchor_text)
        if verdicts is not None and any(_word_count(v[2]) > MAX_WORDS for v in verdicts):
            retry_verdicts, retry_still, retry_title = await _call_llm(anchor_text, tighten=True)
            if retry_verdicts is not None:
                verdicts = retry_verdicts
                still_stands = retry_still
                title = retry_title
    except Exception as e:
        # Degrade gracefully to 'empty' rather than surfacing a 500.
        logger.warning("Counterview generation failed user=%s: %s", user_id, e)
        verdicts = None
        still_stands = None
        title = None

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

    # The closing line: cap-guarded + the SAME output-safety gate, nulled (not
    # suppressing) on failure — the verdicts already passed.
    still_stands = await _clean_still_stands(still_stands)

    # The terrain title: field-level (C-01) — a fail/empty/over-length/flagged title
    # is nulled only, never blocks the counterview whose verdicts already passed.
    title = await _clean_title(title)

    # ── 7) Persist generated counterview + its two responses ──────────────────
    return await _write_counterview(
        db, user_id, source, insight_id, anchor_text,
        status="generated", verdicts=verdicts, still_stands=still_stands, title=title,
    )


async def _call_llm(anchor_text: str, *, tighten: bool = False):
    """One LLM call → (verdicts, still_stands, title): verdicts is a list of
    [slug, position, verdict] in COUNTERVIEW_PERSONAS order (or None if the model
    returned non-'generated' / unparseable / an incomplete persona set), still_stands
    is the raw closing line (or None), and title is the raw terrain heading (or None).
    still_stands and title are only meaningful when verdicts is not None."""
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
        return None, None, None
    if not isinstance(data, dict) or data.get("status") != "generated":
        return None, None, None

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
            return None, None, None  # incomplete set → treat as empty
        result.append([slug, position, verdict])

    # The closing line and the title both ride the same JSON; raw here, each
    # cleaned + safety-checked later (independently, field-level).
    still_raw = data.get("still_stands")
    still_stands = still_raw.strip() if isinstance(still_raw, str) else None
    title_raw = data.get("title")
    title = title_raw.strip() if isinstance(title_raw, str) else None
    return result, (still_stands or None), (title or None)


async def _clean_still_stands(value: str | None) -> str | None:
    """Normalize the "what still stands" closing line: None unless a non-empty
    string within the gross word cap (>= 1.5x nulls; marginal ships) that passes
    the SAME output-safety gate as the verdicts. A flagged line is nulled only —
    the verdicts already passed, so the counterview is never suppressed for it."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if _word_count(text) >= STILL_STANDS_MAX_WORDS * 1.5:
        return None
    if (await safety_service.check_output(text)).should_suppress_persona:
        return None
    return text


async def _clean_title(value: str | None) -> str | None:
    """Normalize the terrain TITLE: None unless a non-empty string of at most
    TITLE_MAX_WORDS words that passes the SAME output-safety gate as the verdicts.
    Surrounding quotes and trailing sentence punctuation are stripped (a title is a
    heading, not a sentence). A flagged / over-length / empty title is nulled only —
    the counterview is never suppressed for it (field-level C-01)."""
    if not isinstance(value, str):
        return None
    text = value.strip().strip("\"'“”‘’").strip()
    text = text.rstrip(".,;:!?—–-").strip()
    if not text:
        return None
    if _word_count(text) > TITLE_MAX_WORDS:
        return None
    if (await safety_service.check_output(text)).should_suppress_persona:
        return None
    return text


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
    still_stands: str | None = None,
    title: str | None = None,
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
        still_stands=still_stands,
        title=title,
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


# ── Go deeper ──────────────────────────────────────────────────────────────────

# Each persona's voice, reused in the deeper prompt (carried over verbatim from
# COUNTERVIEW_PROMPT so the deeper line stays in the same register as the first).
PERSONA_VOICE = {
    "miyamoto_musashi": "Miyamoto Musashi — the discipline of action; you see drift dressed as patience, fear dressed as care, the price of not moving.",
    "niccolo_machiavelli": "Niccolo Machiavelli — the reading of motive and power; you see the convenient story, the hidden self-interest, the resolve that is missing.",
}

# A deeper line gets a little more room than the first cut.
DEEPER_MAX_WORDS = 18

# {voice} is filled per-persona via .replace() (NOT .format() — the JSON example
# below contains literal braces that would break str.format).
DEEPER_PROMPT = """You are {voice}

A person holds a position. You already made one cut against it. Press ONE layer deeper: a second, sharper line that exposes what your first cut implied — the contradiction underneath, the cost they still aren't counting. 18 words MAXIMUM.

Hard rules:
- Anchor STRICTLY to what the person wrote. Invent nothing, no new facts.
- Attack the position, never the person. No insults, nothing below the belt.
- Do not repeat your first line — go further.
- Plain modern language. No quotes, never name yourself.

Return JSON only: {"status":"generated","verdict":"..."}  or  {"status":"empty"} if there is nothing more honest to add."""

# Appended to the system prompt for the single tightening retry.
DEEPER_TIGHTEN = "\n\nYour previous attempt exceeded 18 words. Rewrite to 18 words maximum. Cut every non-essential word — keep the deeper angle and the same JSON shape."


async def generate_deeper(
    db: AsyncSession,
    user_id: str,
    counterview_id: str,
    persona_slug: str,
) -> Counterview:
    """Press one layer deeper for a single persona: add a second, sharper response
    (round = prior max + 1) to an existing generated counterview.

    Raises ValueError("counterview not found") if the counterview is not the
    user's, ValueError("invalid persona") for an unknown slug. Every other failure
    (nothing to deepen, LLM/parse error, safety trip, cap reached) returns the
    counterview unchanged — never a 500.
    """
    cv = (
        await db.execute(
            select(Counterview).where(
                Counterview.id == counterview_id,
                Counterview.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if cv is None:
        raise ValueError("counterview not found")
    if cv.status != "generated":
        return cv  # nothing to deepen (empty/suppressed)

    if persona_slug not in {slug for slug, _ in COUNTERVIEW_PERSONAS}:
        raise ValueError("invalid persona")

    rows = (
        await db.execute(
            select(CounterviewResponse)
            .where(
                CounterviewResponse.counterview_id == cv.id,
                CounterviewResponse.persona_slug == persona_slug,
            )
            .order_by(CounterviewResponse.round.asc())
        )
    ).scalars().all()
    if not rows:
        return cv
    max_round = max(r.round for r in rows)
    if max_round >= 1:
        return cv  # cap: one deepening per persona

    base = next((r for r in rows if r.round == 0), rows[0])
    prior_verdict = base.verdict
    position = base.position

    # ── Generate the deeper line (+ one tightening retry on over-length) ──────
    line = None
    try:
        line = await _call_deeper_llm(cv.anchor_text, persona_slug, prior_verdict)
        if line is not None and _word_count(line) > DEEPER_MAX_WORDS:
            retry = await _call_deeper_llm(
                cv.anchor_text, persona_slug, prior_verdict, tighten=True
            )
            if retry is not None:
                line = retry
    except Exception as e:
        logger.warning(
            "Counterview deeper failed cv=%s persona=%s: %s",
            counterview_id, persona_slug, e,
        )
        line = None

    if line is None:
        return cv  # nothing more honest to add / generation failed

    # ── Post-generation safety: a flagged deeper line is simply not added ──────
    out = await safety_service.check_output(line)
    if out.should_suppress_persona:
        return cv

    db.add(CounterviewResponse(
        counterview_id=cv.id,
        persona_slug=persona_slug,
        round=max_round + 1,
        position=position,
        verdict=line,
    ))
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent deeper for this (counterview, persona, round) won the race
        # (uq_counterview_response). Roll back and return the counterview as-is.
        await db.rollback()
        return cv
    await db.refresh(cv)
    return cv


async def _call_deeper_llm(
    anchor_text: str | None,
    persona_slug: str,
    prior_verdict: str,
    *,
    tighten: bool = False,
):
    """One LLM call for a single persona's deeper line → the verdict string, or
    None if the model returned non-'generated' / unparseable / empty."""
    voice = PERSONA_VOICE[persona_slug]
    system = DEEPER_PROMPT.replace("{voice}", voice) + (DEEPER_TIGHTEN if tighten else "")
    user = f'<position>\n{anchor_text}\n</position>\nYour first cut: "{prior_verdict}"'
    raw = await llm_client.complete(
        system=system,
        user=user,
        model=config.ANTHROPIC_MODEL,
        max_tokens=200,
    )
    return _extract_deeper(raw)


def _extract_deeper(raw: str):
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
    verdict = (data.get("verdict") or "").strip()
    return verdict or None


# ── Rebuttal exchange ───────────────────────────────────────────────────────────

# The bounded cap: at most this many GENERATED user rebuttals per counterview.
# Counts status='generated' turns only — a safety-suppressed or failed turn does
# not consume the budget. Enforced here (not at the DB).
MAX_REBUTTALS = 3

# Per-line ceiling for a rebuttal response — same tightness as a go-deeper line.
RESPOND_MAX_WORDS = DEEPER_MAX_WORDS

# {voice} is filled per-persona via .replace() (NOT .format() — the JSON example
# below contains literal braces that would break str.format).
RESPOND_PROMPT = """You are {voice}

A person holds a position. You already made the case against it. Now they push back. Answer their pushback in ONE sharp line — hold your ground or sharpen it, never concede merely to be agreeable. 18 words MAXIMUM.

Hard rules:
- Anchor STRICTLY to what the person wrote — their position and their pushback. Invent no new facts.
- Answer the pushback directly. Do not change the subject, and do not repeat an earlier line verbatim.
- Attack the position, never the person. No insults, nothing below the belt.
- Plain modern language. No quotes, never name yourself. One clean cut.

Return JSON only: {"status":"generated","verdict":"..."}  or  {"status":"empty"} if there is nothing honest left to say."""

# Appended to the system prompt for the single tightening retry.
RESPOND_TIGHTEN = "\n\nYour previous attempt exceeded 18 words. Rewrite to 18 words maximum. Cut every non-essential word — keep the same answer and the same JSON shape."


async def count_generated_rebuttals(db: AsyncSession, counterview_id: str) -> int:
    """How many GENERATED rebuttal turns a counterview already has (drives the cap
    + the rebuttals_remaining the serializer exposes)."""
    return (
        await db.execute(
            select(func.count())
            .select_from(CounterviewTurn)
            .where(
                CounterviewTurn.counterview_id == counterview_id,
                CounterviewTurn.status == "generated",
            )
        )
    ).scalar_one()


async def respond_to_rebuttal(
    db: AsyncSession,
    user_id: str,
    counterview_id: str,
    persona_slug: str,
    user_text: str,
) -> Counterview:
    """Record one user rebuttal and the CURRENT speaker's reply to it.

    Only `persona_slug` answers (the persona the rebuttal targets) — one LLM call,
    one safety check on the input, one on the output. The reply is <=18 words with
    the same tighten-retry as go-deeper. Bounded: at most MAX_REBUTTALS *generated*
    turns per counterview.

    Raises ValueError("counterview not found") if the counterview is not the user's,
    ValueError("invalid persona") for an unknown slug, ValueError("cap_reached") when
    the generated-rebuttal cap is already met. A suppressed input, an empty/failed
    generation, or a suppressed output each persists a turn with the matching status
    (no reply) and returns the counterview — never a 500.
    """
    cv = (
        await db.execute(
            select(Counterview).where(
                Counterview.id == counterview_id,
                Counterview.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if cv is None:
        raise ValueError("counterview not found")
    if cv.status != "generated":
        return cv  # nothing to rebut (empty/suppressed)

    if persona_slug not in {slug for slug, _ in COUNTERVIEW_PERSONAS}:
        raise ValueError("invalid persona")

    # ── Cap: count GENERATED turns only ───────────────────────────────────────
    if await count_generated_rebuttals(db, counterview_id) >= MAX_REBUTTALS:
        raise ValueError("cap_reached")

    # ── Pre-generation safety gate on the user's rebuttal ─────────────────────
    res = await safety_service.check_input(user_text, user_id)
    if res.should_suppress_persona:
        return await _write_turn(
            db, counterview_id, persona_slug, user_text,
            response=None, status="suppressed",
        )

    # ── Build the bounded context for this persona (verdict + deeper + prior
    #    generated turns with this persona) and generate (+ one tighten retry) ──
    history = await _rebuttal_context(db, cv, persona_slug)
    line = None
    try:
        line = await _call_respond_llm(cv.anchor_text, persona_slug, history, user_text)
        if line is not None and _word_count(line) > RESPOND_MAX_WORDS:
            retry = await _call_respond_llm(
                cv.anchor_text, persona_slug, history, user_text, tighten=True
            )
            if retry is not None:
                line = retry
    except Exception as e:
        logger.warning(
            "Counterview rebuttal failed cv=%s persona=%s: %s",
            counterview_id, persona_slug, e,
        )
        line = None

    if line is None:
        return await _write_turn(
            db, counterview_id, persona_slug, user_text, response=None, status="empty"
        )

    # ── Post-generation safety: a flagged reply is dropped (turn kept, no reply)
    out = await safety_service.check_output(line)
    if out.should_suppress_persona:
        return await _write_turn(
            db, counterview_id, persona_slug, user_text, response=None, status="suppressed"
        )

    return await _write_turn(
        db, counterview_id, persona_slug, user_text, response=line, status="generated"
    )


async def _rebuttal_context(db: AsyncSession, cv: Counterview, persona_slug: str) -> str:
    """A compact, bounded transcript for one persona: its verdict (round 0), its
    deeper line (round 1) if any, and the prior GENERATED rebuttal turns with this
    persona — so the reply stays coherent and does not repeat itself. Capped in
    size by MAX_REBUTTALS, so it never balloons."""
    rows = (
        await db.execute(
            select(CounterviewResponse)
            .where(
                CounterviewResponse.counterview_id == cv.id,
                CounterviewResponse.persona_slug == persona_slug,
            )
            .order_by(CounterviewResponse.round.asc())
        )
    ).scalars().all()
    lines: list[str] = ["Your case so far:"]
    for r in rows:
        lines.append(f"- {r.verdict}")

    turns = (
        await db.execute(
            select(CounterviewTurn)
            .where(
                CounterviewTurn.counterview_id == cv.id,
                CounterviewTurn.persona_slug == persona_slug,
                CounterviewTurn.status == "generated",
            )
            .order_by(CounterviewTurn.sequence.asc())
        )
    ).scalars().all()
    if turns:
        lines.append("Earlier pushback and your replies:")
        for t in turns:
            lines.append(f'- They said: "{t.user_text}" — You answered: "{t.persona_response}"')
    return "\n".join(lines)


async def _call_respond_llm(
    anchor_text: str | None,
    persona_slug: str,
    history: str,
    user_text: str,
    *,
    tighten: bool = False,
):
    """One LLM call for the current speaker's reply to a rebuttal → the verdict
    string, or None if the model returned non-'generated' / unparseable / empty."""
    voice = PERSONA_VOICE[persona_slug]
    system = RESPOND_PROMPT.replace("{voice}", voice) + (RESPOND_TIGHTEN if tighten else "")
    user = (
        f"<position>\n{anchor_text}\n</position>\n"
        f"{history}\n"
        f'They now push back: "{user_text}"'
    )
    raw = await llm_client.complete(
        system=system,
        user=user,
        model=config.ANTHROPIC_MODEL,
        max_tokens=200,
    )
    return _extract_deeper(raw)  # same {status, verdict} shape as a deeper line


async def _write_turn(
    db: AsyncSession,
    counterview_id: str,
    persona_slug: str,
    user_text: str,
    *,
    response: str | None,
    status: str,
) -> Counterview:
    """Insert one rebuttal turn at the next sequence ordinal. Race-safe against
    uq_counterview_turn_seq (a concurrent rebuttal won the slot) — on IntegrityError
    roll back and return the counterview unchanged. Returns the parent counterview."""
    next_seq = (
        await db.execute(
            select(func.coalesce(func.max(CounterviewTurn.sequence), 0)).where(
                CounterviewTurn.counterview_id == counterview_id
            )
        )
    ).scalar_one() + 1

    db.add(CounterviewTurn(
        counterview_id=counterview_id,
        sequence=next_seq,
        persona_slug=persona_slug,
        user_text=user_text,
        persona_response=response,
        status=status,
    ))
    cv = (
        await db.execute(
            select(Counterview).where(Counterview.id == counterview_id)
        )
    ).scalar_one()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return cv
    await db.refresh(cv)
    return cv
