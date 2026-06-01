import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from models import CouncilCase, CouncilSession, CouncilResponse
from personas import get_persona
from services.council_prompts import COUNCIL_VERDICT_INSTRUCTION, COUNCIL_SYNTHESIS_PROMPT
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.safety_service import safety_service

logger = logging.getLogger(__name__)

MODEL_PRO = "claude-sonnet-4-6"

COUNCIL_MEMBERS = [
    "niccolo_machiavelli",
    "epictetus",
    "sigmund_freud",
    "simone_de_beauvoir",
]
WEEKLY_LIMIT_PER_SOURCE = 1


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

    async def stream_council(
        self,
        db: AsyncSession,
        user_id: str,
        matter: str,
        source: str = "direct",
        mirror_id: str | None = None,
    ) -> AsyncGenerator[str, None]:

        # ── 1. PRE-RITUAL SAFETY GATE ────────────────────────────────────
        safety_in = await safety_service.check_input(matter, user_id)
        if safety_in.should_suppress_persona:
            yield f"data: {json.dumps({'type': 'safety', 'level': safety_in.level})}\n\n"
            safe = prompt_builder.build_safety_response(level=safety_in.level)
            for chunk in _chunk_text(safe):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

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
        )
        db.add(session)
        await db.flush()

        yield f"data: {json.dumps({'type': 'convening'})}\n\n"

        # ── 3. FOUR MEMBER VERDICTS ───────────────────────────────────────
        verdicts: list[tuple[str, str]] = []  # (persona_name, verdict_text)

        for i, slug in enumerate(COUNCIL_MEMBERS):
            persona = get_persona(slug)
            if persona is None:
                logger.error(f"Council member persona not found: {slug}")
                yield f"data: {json.dumps({'type': 'error', 'error_code': 'member_unavailable', 'slug': slug})}\n\n"
                continue

            system = (
                prompt_builder.build_system(
                    persona=persona,
                    memories=[],
                    passages=[],
                    phenomenology_bridge=None,
                )
                + "\n\n"
                + COUNCIL_VERDICT_INSTRUCTION.format(persona_name=persona.name)
            )
            messages = [{"role": "user", "content": matter}]

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
                        system=system, messages=messages, model=MODEL_PRO
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

        # ── 4. SYNTHESIS (app voice) ──────────────────────────────────────
        yield f"data: {json.dumps({'type': 'synthesis_start'})}\n\n"

        verdicts_block = "\n\n".join(f"[{name}]: {text}" for name, text in verdicts)
        synthesis_user_content = f"The matter:\n{matter}\n\nThe four verdicts:\n{verdicts_block}"

        synthesis_buf: list[str] = []
        try:
            async for chunk in llm_client.stream(
                system=COUNCIL_SYNTHESIS_PROMPT,
                messages=[{"role": "user", "content": synthesis_user_content}],
                model=MODEL_PRO,
            ):
                synthesis_buf.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            session.synthesis = "".join(synthesis_buf)
        except Exception as exc:
            logger.error(f"Council synthesis failed for user={user_id}: {exc}")
            session.synthesis = None
            yield f"data: {json.dumps({'type': 'synthesis_error'})}\n\n"

        session.status = "complete"

        # ── 5. COMMIT + DONE ──────────────────────────────────────────────
        await db.commit()
        yield f"data: {json.dumps({'type': 'done', 'case_id': case.id, 'session_id': session.id})}\n\n"


council_service = CouncilService()
