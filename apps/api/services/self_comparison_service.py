import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import SelfComparison, Message, Conversation
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.safety_service import safety_service
from services.self_model_service import self_model_service
from services.self_comparison_prompts import SELF_SYSTEM_PROMPT, CLOSING_PROMPT, FORMING_REFLECTION_PROMPT

logger = logging.getLogger(__name__)

MODEL_PRO = "claude-sonnet-4-6"   # same model Council uses
WEEKLY_LIMIT_BY_TIER = {"pro": 5, "premium": 30}   # asks/week; premium capped (cost safety)
DEFAULT_WEEKLY_LIMIT = 5
CANDIDATES_PER_WINDOW = 8
QUOTE_TRUNC = 200
FORMING_REFLECTION_MAX_TOKENS = 220


def weekly_limit(plan: str) -> int:
    return WEEKLY_LIMIT_BY_TIER.get(plan, DEFAULT_WEEKLY_LIMIT)


def _week_start() -> datetime:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.isoweekday() - 1)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _format_signals(by_type: dict) -> str:
    lines: list[str] = []
    for entry_type, items in by_type.items():
        lines.append(f"{entry_type}:")
        for it in items:
            lines.append(f"- {it}")
    return "\n".join(lines)


class SelfComparisonService:

    async def forming_reflection(self, signals: list[str]) -> list[str]:
        """Synthesize the raw recent memory signals into a short, warm, second-person
        reflection for the "what's beginning to take shape" block.

        Block-scoped: does NOT touch memory extraction or RAG — it only rewrites how
        these already-stored signals are surfaced in this one preview. Returns up to 3
        short bullet observations (or [] on failure), in which case the block hides
        rather than show raw, third-person ("user") text. Uses the default memory-tier model (fast/cheap)
        since this fires on each forming-state status load.
        """
        cleaned = [s.strip() for s in signals if s and s.strip()]
        if not cleaned:
            return []
        user_block = "Observations:\n" + "\n".join(f"- {s}" for s in cleaned)
        try:
            raw = await llm_client.complete(
                system=FORMING_REFLECTION_PROMPT,
                user=user_block,
                max_tokens=FORMING_REFLECTION_MAX_TOKENS,
            )
        except Exception as exc:
            logger.warning(f"Forming reflection synthesis failed: {exc}")
            return []
        text = raw.strip()
        bullets = [
            ln.strip().lstrip("-•*").strip().strip('"').strip()
            for ln in text.splitlines()
        ]
        bullets = [b for b in bullets if b][:3]
        return bullets

    async def weekly_remaining(self, db: AsyncSession, user_id: str, plan: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(SelfComparison).where(
                SelfComparison.user_id == user_id,
                SelfComparison.created_at >= _week_start(),
            )
        )
        return max(0, weekly_limit(plan) - result.scalar_one())

    async def _candidates(self, db: AsyncSession, user_id: str, start, end) -> list[dict]:
        result = await db.execute(
            select(Message.id, Message.content, Message.created_at)
            .where(
                Message.user_id == user_id,
                Message.role == "user",
                Message.created_at >= start,
                Message.created_at <= end,
            )
            .order_by(Message.created_at.asc())
            .limit(CANDIDATES_PER_WINDOW)
        )
        return [{"id": r.id, "text": r.content, "date": r.created_at} for r in result.all()]

    async def _window_has_crisis(self, db, user_id, start, end) -> bool:
        result = await db.execute(
            select(func.count()).select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.user_id == user_id,
                Message.created_at >= start,
                Message.created_at <= end,
                Message.safety_level.in_(("high", "critical")),
            )
        )
        return result.scalar_one() > 0

    async def stream(self, db: AsyncSession, user_id: str, prompt: str, *, bypass_gate: bool = False) -> AsyncGenerator[str, None]:
        # 1. Safety gate on the prompt
        safety_in = await safety_service.check_input(prompt, user_id)
        if safety_in.should_suppress_persona:
            yield f"data: {json.dumps({'type': 'safety', 'level': safety_in.level})}\n\n"
            safe = prompt_builder.build_safety_response(level=safety_in.level)
            yield f"data: {json.dumps({'type': 'chunk', 'which': 'safety', 'data': safe})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # 2. Require unlocked self-model
        model = await self_model_service.build(db, user_id, bypass_gate=bypass_gate)
        if not model["unlocked"]:
            yield f"data: {json.dumps({'type': 'error', 'error_code': 'not_unlocked'})}\n\n"
            return

        then_w, now_w = model["then"], model["now"]

        # 3. Window crisis-content safety gate (weekly-mirror inheritance)
        if await self._window_has_crisis(db, user_id, then_w["start"], now_w["end"]):
            yield f"data: {json.dumps({'type': 'safety', 'level': 'suppressed'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # 4. Create pending row
        row = SelfComparison(
            user_id=user_id, prompt=prompt,
            then_start=then_w["start"], then_end=then_w["end"],
            now_start=now_w["start"], now_end=now_w["end"],
            status="pending",
        )
        db.add(row)
        await db.flush()

        # 5. Stream the two selves
        answers: dict[str, str] = {}
        for which, label, win in (("then", "earlier", then_w), ("now", "more recent", now_w)):
            system = SELF_SYSTEM_PROMPT.format(which_label=label, signals=_format_signals(win["by_type"]))
            yield f"data: {json.dumps({'type': 'self', 'which': which, 'start': win['start'].isoformat(), 'end': win['end'].isoformat()})}\n\n"
            buf: list[str] = []
            chunks_yielded = False
            success = False
            for attempt in range(3):
                buf = []
                chunks_yielded = False
                try:
                    async for chunk in llm_client.stream(
                        system=system, messages=[{"role": "user", "content": prompt}], model=MODEL_PRO
                    ):
                        buf.append(chunk)
                        chunks_yielded = True
                        yield f"data: {json.dumps({'type': 'chunk', 'which': which, 'data': chunk})}\n\n"
                    success = True
                    break
                except anthropic.RateLimitError:
                    if chunks_yielded: break
                    await asyncio.sleep(2 ** attempt)
                except anthropic.APIStatusError as exc:
                    if chunks_yielded or exc.status_code < 500: break
                    await asyncio.sleep(2 ** attempt)
                except (anthropic.APIConnectionError, anthropic.APITimeoutError):
                    if chunks_yielded: break
                    await asyncio.sleep(2 ** attempt)
            if not success and not chunks_yielded:
                yield f"data: {json.dumps({'type': 'error', 'error_code': 'self_unavailable', 'which': which})}\n\n"
            answers[which] = "".join(buf)

        # ── 6. App-voice closing + evidence ──────────────────────────────
        candidates = {
            "then": await self._candidates(db, user_id, then_w["start"], then_w["end"]),
            "now":  await self._candidates(db, user_id, now_w["start"], now_w["end"]),
        }
        by_id = {c["id"]: c for side in candidates.values() for c in side}

        def _fmt(side: str) -> str:
            return "\n".join(f"[{c['id']}] ({c['date']:%b %d}) {c['text'][:240]}" for c in candidates[side])

        closing_user = (
            f"Question:\n{prompt}\n\n"
            f"Earlier self answered:\n{answers.get('then','')}\n\n"
            f"More recent self answered:\n{answers.get('now','')}\n\n"
            f"Earlier-period messages:\n{_fmt('then')}\n\n"
            f"Recent-period messages:\n{_fmt('now')}"
        )

        closing = {"observation": "", "question": "", "then_quote": None, "now_quote": None}
        try:
            raw = await llm_client.complete(system=CLOSING_PROMPT, user=closing_user, model=MODEL_PRO, max_tokens=512)
            ctext = raw.strip()
            if ctext.startswith("```"):
                ctext = ctext.split("\n", 1)[1] if "\n" in ctext else ""
            if ctext.endswith("```"):
                ctext = ctext[:-3].rstrip()
            data = json.loads(ctext)
            closing["observation"] = data.get("observation", "")
            closing["question"] = data.get("question", "")
            for side, key in (("then", "then_quote_id"), ("now", "now_quote_id")):
                qid = data.get(key)
                cand = by_id.get(qid) if qid else None
                if cand:
                    closing[f"{side}_quote"] = {"text": cand["text"][:QUOTE_TRUNC], "date": cand["date"].isoformat()}
        except Exception as exc:
            logger.error(f"Self-comparison closing failed for user={user_id}: {exc}")

        yield f"data: {json.dumps({'type': 'closing', **closing})}\n\n"

        # 6. Persist
        row.payload = {
            "then": {"answer": answers.get("then", ""), "start": then_w["start"].isoformat(), "end": then_w["end"].isoformat()},
            "now":  {"answer": answers.get("now", ""),  "start": now_w["start"].isoformat(),  "end": now_w["end"].isoformat()},
            "closing": closing,
        }
        row.status = "ready"
        await db.commit()

        # 7. Done
        yield f"data: {json.dumps({'type': 'done', 'comparison_id': row.id})}\n\n"


self_comparison_service = SelfComparisonService()
