import asyncio
import json
from time import perf_counter
from services.analytics_service import analytics_service
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from models import CouncilCase, CouncilSession, CouncilResponse, Message
from personas import get_persona
from services.council_prompts import (
    COUNCIL_VERDICT_INSTRUCTION,
    COUNCIL_ROLE_DIRECTIVE,
    COUNCIL_SYNTHESIS_PROMPT,
    COUNCIL_DISTILL_PROMPT,
    COUNCIL_DISPLAY_BRIEF_PROMPT,
)
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.safety_service import safety_service
from text_utils import dominant_language
from services.safety_event_log import log_safety_event, STAGE_COUNCIL_INPUT

logger = logging.getLogger(__name__)

MODEL_PRO = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"

COUNCIL_MEMBERS = [
    "niccolo_machiavelli",
    "epictetus",
    "sigmund_freud",
    "simone_de_beauvoir",
]
WEEKLY_LIMIT_PER_SOURCE = 1


def _latency_bucket(seconds: float) -> str:
    """Coarse buckets, deliberately not milliseconds. Analytics answers "is this
    too slow to sit through", which a bucket answers and a raw number does not."""
    if seconds < 10:
        return "under_10s"
    if seconds < 30:
        return "10_30s"
    if seconds < 60:
        return "30_60s"
    return "over_60s"


def _iso_week_start() -> datetime:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.isoweekday() - 1)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _chunk_text(text: str, size: int = 20):
    for i in range(0, len(text), size):
        yield text[i:i + size]


class CouncilService:

    async def weekly_remaining(self, db: AsyncSession, user_id: str, source: str) -> int:
        week_start = _iso_week_start()
        result = await db.execute(
            select(func.count()).select_from(CouncilCase).where(
                CouncilCase.user_id == user_id,
                CouncilCase.source == source,
                CouncilCase.created_at >= week_start,
            )
        )
        count = result.scalar_one()
        return max(0, WEEKLY_LIMIT_PER_SOURCE - count)

    async def _distill_brief(
        self, db: AsyncSession, user_id: str, conversation_id: str
    ) -> str | None:
        """Distil a chat conversation into a 1–2 sentence essence brief for the
        council members. Internal-only — never stored, never sent to the client.
        Returns None on any failure or too-thin a conversation, so the caller
        falls back to the raw matter and the council never breaks."""
        try:
            # Last ~12 messages of THIS user's conversation. Scoped by user_id AND
            # conversation_id so a foreign conversation yields nothing. Mirrors the
            # canonical history query's conclusion exclusion.
            result = await db.execute(
                select(Message)
                .where(
                    Message.user_id == user_id,
                    Message.conversation_id == conversation_id,
                    Message.message_kind != 'conclusion',
                )
                .order_by(Message.created_at.desc())
                .limit(12)
            )
            recent = list(reversed(result.scalars().all()))

            # Too thin to distil: a single turn is already captured by the raw
            # matter (the last user message), so distilling adds nothing.
            user_turns = sum(1 for m in recent if m.role == "user")
            if user_turns < 2:
                return None

            transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)
            brief = await llm_client.complete(
                system=COUNCIL_DISTILL_PROMPT,
                user=transcript,
                model=MODEL_HAIKU,
                max_tokens=150,
            )
            brief = (brief or "").strip()
            return brief or None
        except Exception as exc:
            logger.warning(f"Council distill failed for user={user_id}: {exc}")
            return None

    async def display_brief(
        self, db: AsyncSession, user_id: str, conversation_id: str
    ) -> str | None:
        """User-facing summary of a chat conversation, for DISPLAY-ONLY prefill of
        the Council matter textarea. Written first-person in the user's own voice and
        language (COUNCIL_DISPLAY_BRIEF_PROMPT) — distinct from _distill_brief, which
        produces the neutral third-person INTERNAL brief the members deliberate. This
        text is never sent to the council members and never changes what they receive.

        Mirrors _distill_brief's query shape (last 12 messages, exclude conclusion,
        <2 user turns → None) but is a separate method — _distill_brief is untouched.
        Returns None on any failure or too-thin a conversation so the caller keeps the
        raw prefill."""
        try:
            result = await db.execute(
                select(Message)
                .where(
                    Message.user_id == user_id,
                    Message.conversation_id == conversation_id,
                    Message.message_kind != 'conclusion',
                )
                .order_by(Message.created_at.desc())
                .limit(12)
            )
            recent = list(reversed(result.scalars().all()))

            user_turns = sum(1 for m in recent if m.role == "user")
            if user_turns < 2:
                return None

            transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)
            brief = await llm_client.complete(
                system=COUNCIL_DISPLAY_BRIEF_PROMPT,
                user=transcript,
                model=MODEL_HAIKU,
                max_tokens=150,
            )
            brief = (brief or "").strip()
            return brief or None
        except Exception as exc:
            logger.warning(f"Council display brief failed for user={user_id}: {exc}")
            return None

    async def stream_council(
        self,
        db: AsyncSession,
        user_id: str,
        matter: str,
        source: str = "direct",
        mirror_id: str | None = None,
        conversation_id: str | None = None,
        matter_edited: bool = False,
        arq_queue=None,
    ) -> AsyncGenerator[str, None]:

        # ── 1. PRE-RITUAL SAFETY GATE ────────────────────────────────────
        safety_in = await safety_service.check_input(matter, user_id)
        if safety_in.should_log:
            await log_safety_event(db, user_id, safety_in, STAGE_COUNCIL_INPUT)
        if safety_in.should_suppress_persona:
            yield f"data: {json.dumps({'type': 'safety', 'level': safety_in.level})}\n\n"
            safe = prompt_builder.build_safety_response(
                level=safety_in.level, language=dominant_language([matter]),
            )
            for chunk in _chunk_text(safe):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # ── 1b. ESSENCE BRIEF (chat only) ────────────────────────────────
        # For chat-sourced councils with a conversation, distil the recent
        # exchange into a neutral brief so the members deliberate the GIST,
        # not just the last-message fragment. Internal-only: input_text below
        # keeps the RAW matter, and the brief is never sent to the client.
        # On any failure _distill_brief returns None → fall back to raw matter.
        # When the user edited the auto-filled matter (matter_edited), skip the
        # re-distillation entirely so the members deliberate the EDITED text —
        # gating the CALL only; _distill_brief itself is unchanged.
        brief = None
        if source == "chat" and conversation_id and not matter_edited:
            brief = await self._distill_brief(db, user_id, conversation_id)
        effective_matter = brief or matter

        # ── 2. CREATE CASE + SESSION ──────────────────────────────────────
        case = CouncilCase(
            user_id=user_id,
            source=source,
            mirror_id=mirror_id,
            status="open",
            session_count=1,
        )
        db.add(case)
        await db.flush()

        session = CouncilSession(
            case_id=case.id,
            session_number=1,
            input_text=matter,
            status="generating",
            matter_edited=matter_edited,
        )
        db.add(session)
        await db.flush()

        _t0 = perf_counter()
        yield f"data: {json.dumps({'type': 'convening'})}\n\n"

        # ── 3. FOUR MEMBER VERDICTS ───────────────────────────────────────
        verdicts: list[tuple[str, str]] = []  # (persona_name, verdict_text)

        for i, slug in enumerate(COUNCIL_MEMBERS):
            persona = get_persona(slug)
            if persona is None:
                logger.error(f"Council member persona not found: {slug}")
                yield f"data: {json.dumps({'type': 'error', 'error_code': 'member_unavailable', 'slug': slug})}\n\n"
                continue

            # Internal role directive holds each voice to a distinct function so the
            # four don't overlap. Appended AFTER the shared verdict instruction; never
            # surfaced to the client.
            role_directive = COUNCIL_ROLE_DIRECTIVE.get(slug, "")
            system = (
                prompt_builder.build_system(
                    persona=persona,
                    memories=[],
                    passages=[],
                    phenomenology_bridge=None,
                )
                + "\n\n"
                + COUNCIL_VERDICT_INSTRUCTION.format(persona_name=persona.name)
                + (f"\n\n{role_directive}" if role_directive else "")
            )
            # The matter is FRAMED, not handed over bare. A bare user turn carrying a
            # quotation reads as "comment on this text", so members opened by disowning
            # and attributing it instead of counselling the person (UAT A5). The closing
            # line does the most work: what the model carries into its first sentence is
            # what it read last, and the first sentence is where the disowning happened.
            # Applies on the shared path — direct- and mirror-sourced matters too.
            # NOTE: effective_matter itself is deliberately NOT reassigned; the synthesis
            # step below builds its own string from it and must keep the unwrapped text.
            framed_matter = (
                "The person brings this before the council:\n\n"
                f"{effective_matter}\n\n"
                "This is what they ask you to weigh."
            )
            messages = [{"role": "user", "content": framed_matter}]

            yield f"data: {json.dumps({'type': 'member', 'slug': slug, 'name': persona.name, 'position': i})}\n\n"

            _llm_success = False
            _last_err: Exception | None = None
            _buf: list[str] = []
            _chunks_yielded = False

            for attempt in range(3):
                _buf = []
                _chunks_yielded = False
                try:
                    async for chunk in llm_client.stream(
                        system=prompt_builder.cache_whole_system(system),
                        messages=messages,
                        model=MODEL_PRO,
                    ):
                        _buf.append(chunk)
                        _chunks_yielded = True
                        yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                    _llm_success = True
                    break
                except anthropic.RateLimitError as exc:
                    _last_err = exc
                    if _chunks_yielded:
                        break
                    await asyncio.sleep(2 ** attempt)
                except anthropic.APIStatusError as exc:
                    _last_err = exc
                    if _chunks_yielded or exc.status_code < 500:
                        break
                    await asyncio.sleep(2 ** attempt)
                except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                    _last_err = exc
                    if _chunks_yielded:
                        break
                    await asyncio.sleep(2 ** attempt)

            if not _llm_success:
                logger.error(f"Council LLM failed for member={slug}: {_last_err}")
                yield f"data: {json.dumps({'type': 'error', 'error_code': 'member_unavailable', 'slug': slug})}\n\n"
                continue

            verdict_text = "".join(_buf)
            verdicts.append((persona.name, verdict_text))
            db.add(CouncilResponse(
                session_id=session.id,
                persona_slug=slug,
                position=i,
                verdict=verdict_text,
            ))

        # ── 4. SYNTHESIS (structured decision instrument) ─────────────────
        # One structured JSON call (no longer streamed prose): real_question /
        # tension / verdict / next_move. The verdict beat is ALSO written to the
        # flat `synthesis` column so the feed + share card read it unchanged. A
        # total failure (or a verdict-less parse) falls back to synthesis_error /
        # flat-None exactly as the old streamed synthesis did.
        yield f"data: {json.dumps({'type': 'synthesis_start'})}\n\n"

        verdicts_block = "\n\n".join(f"[{name}]: {text}" for name, text in verdicts)
        synthesis_user_content = f"The matter:\n{effective_matter}\n\nThe four verdicts:\n{verdicts_block}"

        structured = None
        try:
            raw = await llm_client.complete(
                system=COUNCIL_SYNTHESIS_PROMPT,
                user=synthesis_user_content,
                model=MODEL_PRO,
                max_tokens=600,
            )
            structured = _parse_synthesis(raw)
        except Exception as exc:
            logger.error(f"Council synthesis failed for user={user_id}: {exc}")
            structured = None

        verdict_text = (structured.get("verdict") or "").strip() if structured else ""
        if verdict_text:
            # real_question + next_move + theme: grounded-or-null, cap-guarded
            # (>= 1.5x) + the same output-safety gate (null the field, keep the
            # rest). tension + verdict ride the prompt caps as-is.
            #
            # theme is the share card's context line — the NEUTRAL subject, which is
            # why it is a separate beat and not real_question: real_question is the
            # private reading and has no business on a surface built to be shared.
            # Null-safe by construction, and absent entirely from every session
            # generated before this shipped; the card skips the line either way.
            payload = {
                "real_question": await _clean_field(structured.get("real_question"), cap_words=20),
                "tension": (structured.get("tension") or "").strip() or None,
                "verdict": verdict_text,
                "next_move": await _clean_field(structured.get("next_move"), cap_words=18),
                "theme": await _clean_field(structured.get("theme"), cap_words=8),
            }
            session.synthesis = verdict_text            # flat — MUST stay populated
            session.synthesis_structured = payload
            yield f"data: {json.dumps({'type': 'synthesis', **payload})}\n\n"
        else:
            session.synthesis = None
            session.synthesis_structured = None
            yield f"data: {json.dumps({'type': 'synthesis_error'})}\n\n"

        session.status = "complete"

        # ── 5. COMMIT + DONE ──────────────────────────────────────────────
        await db.commit()

        # ── 6. EDITED-MATTER → CONFIDENCE-1 MEMORY (chat-edit only) ────────
        # When a chat-sourced council ran on matter the user REWROTE in their own
        # words (matter_edited), distil that edited text into one clean stated
        # memory. Async + cheap: the task pre-filters trivial edits before any LLM
        # call. `matter` is the edited text here (re-distillation was skipped in 1b
        # for matter_edited). Only in this exact case — never for non-edited or
        # direct councils. Fire-and-forget; enqueue failure never breaks the stream.
        if arq_queue is not None and source == "chat" and matter_edited:
            try:
                await arq_queue.enqueue_job(
                    "distill_user_text_to_memory_task",
                    str(user_id),
                    str(conversation_id) if conversation_id else None,
                    matter,
                    "council_edit",
                )
            except Exception as exc:
                logger.error(f"Council edit-to-memory enqueue failed for user={user_id}: {exc}")

        # Fired where the stream actually completes, not where it starts: a
        # council that dies mid-synthesis produces council_started with no
        # council_completed, which is exactly the gap worth seeing.
        #
        # member_count is how many of the four members returned a verdict --
        # member_unavailable is yielded per slug, so this is a real measurement
        # rather than a constant 4. latency_bucket is a bucket, not milliseconds:
        # the decision it informs is "is the council too slow to sit through",
        # which a bucket answers and a raw number obscures. No used_memory --
        # this service passes memories=[] unconditionally.
        analytics_service.track("council_completed", user_id, {
            "member_count": len(verdicts),
            "latency_bucket": _latency_bucket(perf_counter() - _t0),
        })

        yield f"data: {json.dumps({'type': 'done', 'case_id': case.id, 'session_id': session.id})}\n\n"


def _parse_synthesis(raw: str) -> dict | None:
    """Parse the structured synthesis JSON (tolerating a ```-fenced payload).
    Returns the dict, or None if unparseable / not an object."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text[:-3].rstrip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


async def _clean_field(value, *, cap_words: int) -> str | None:
    """Normalize a grounded synthesis beat (real_question / next_move): None unless
    a non-empty string within the gross word cap (>= 1.5x nulls; marginal ships)
    that passes the SAME output-safety gate. A flagged field is nulled only — the
    rest of the synthesis (verdict, tension) is unaffected."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() == "null":
        return None
    if len(text.split()) >= cap_words * 1.5:
        return None
    if (await safety_service.check_output(text)).should_suppress_persona:
        return None
    return text


council_service = CouncilService()
