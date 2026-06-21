"""Assembles the unified Reflections feed: saved lines + saved Mirror/Council
verdicts, merged into one saved_at-descending list of typed items.

Read-only. Saves are written elsewhere (saved_lines, mirror_saves, council_saves).
Soft-deleted rows are excluded. No tier filtering: a saved verdict stays visible
even if the user later lapses to free, because access was gated at creation time.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    CouncilResponse,
    CouncilSave,
    CouncilSession,
    Counterview,
    CounterviewResponse,
    CounterviewSave,
    Mirror,
    MirrorSave,
    Persona,
)
from services.saved_lines_service import saved_lines_service


class ReflectionsFeedService:

    async def _lines(self, db: AsyncSession, user_id: str) -> list[dict]:
        rows = await saved_lines_service.list_for_user(db, user_id)
        return [{"kind": "line", **row} for row in rows]

    async def _mirror_verdicts(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(
                MirrorSave.id.label("save_id"),
                MirrorSave.mirror_id,
                MirrorSave.saved_at,
                Mirror.payload,
                Mirror.kind.label("mirror_kind"),
                Persona.slug.label("host_persona_slug"),
                Persona.name.label("host_persona_name"),
            )
            .join(Mirror, MirrorSave.mirror_id == Mirror.id)
            .outerjoin(Persona, Mirror.host_persona_id == Persona.id)
            .where(
                MirrorSave.user_id == user_id,
                MirrorSave.deleted_at.is_(None),
            )
        )
        items: list[dict] = []
        for row in result.all():
            thread = (row.payload or {}).get("thread")
            # Defensive: skip saves pointing at a mirror with no verdict text
            # (e.g. a non-generated mirror). Nothing to render.
            if not thread:
                continue
            items.append({
                "kind": "mirror_verdict",
                "save_id": row.save_id,
                "mirror_id": row.mirror_id,
                "thread": thread,
                "host_persona_slug": row.host_persona_slug,
                "host_persona_name": row.host_persona_name,
                "mirror_kind": row.mirror_kind,
                "saved_at": row.saved_at,
            })
        return items

    async def _council_verdicts(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(
                CouncilSave.id.label("save_id"),
                CouncilSave.session_id,
                CouncilSave.saved_at,
                CouncilSession.synthesis,
                CouncilSession.created_at,
            )
            .join(CouncilSession, CouncilSave.session_id == CouncilSession.id)
            .where(
                CouncilSave.user_id == user_id,
                CouncilSave.deleted_at.is_(None),
            )
        )
        rows = [r for r in result.all() if r.synthesis]  # skip failed syntheses
        if not rows:
            return []

        session_ids = [r.session_id for r in rows]
        slugs_result = await db.execute(
            select(CouncilResponse.session_id, CouncilResponse.persona_slug)
            .where(CouncilResponse.session_id.in_(session_ids))
            .order_by(CouncilResponse.position.asc())
        )
        slugs_by_session: dict[str, list[str]] = {}
        for session_id, slug in slugs_result.all():
            slugs_by_session.setdefault(session_id, []).append(slug)

        return [{
            "kind": "council_verdict",
            "save_id": r.save_id,
            "session_id": r.session_id,
            "synthesis": r.synthesis,
            "persona_slugs": slugs_by_session.get(r.session_id, []),
            "created_at": r.created_at,
            "saved_at": r.saved_at,
        } for r in rows]

    async def _counterview_verdicts(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(
                CounterviewSave.id.label("save_id"),
                CounterviewSave.counterview_id,
                CounterviewSave.saved_at,
                Counterview.source,
                Counterview.anchor_text,
            )
            .join(Counterview, CounterviewSave.counterview_id == Counterview.id)
            .where(
                CounterviewSave.user_id == user_id,
                CounterviewSave.deleted_at.is_(None),
                Counterview.status == "generated",
            )
        )
        rows = result.all()
        if not rows:
            return []

        # The round-0 verdicts for those counterviews, with each persona's display
        # name, ordered by position (left → right).
        cv_ids = [r.counterview_id for r in rows]
        verdicts_result = await db.execute(
            select(
                CounterviewResponse.counterview_id,
                CounterviewResponse.persona_slug,
                CounterviewResponse.verdict,
                CounterviewResponse.position,
                Persona.name.label("persona_name"),
            )
            .join(Persona, Persona.slug == CounterviewResponse.persona_slug)
            .where(
                CounterviewResponse.counterview_id.in_(cv_ids),
                CounterviewResponse.round == 0,
            )
            .order_by(CounterviewResponse.position.asc())
        )
        verdicts_by_cv: dict[str, list[dict]] = {}
        for v in verdicts_result.all():
            verdicts_by_cv.setdefault(v.counterview_id, []).append({
                "persona_slug": v.persona_slug,
                "persona_name": v.persona_name,
                "verdict": v.verdict,
                "position": v.position,
            })

        return [{
            "kind": "counterview_verdict",
            "save_id": r.save_id,
            "counterview_id": r.counterview_id,
            "source": r.source,
            "anchor_text": r.anchor_text,
            "verdicts": verdicts_by_cv.get(r.counterview_id, []),
            "saved_at": r.saved_at,
        } for r in rows]

    async def get_feed(self, db: AsyncSession, user_id: str) -> list[dict]:
        lines = await self._lines(db, user_id)
        mirrors = await self._mirror_verdicts(db, user_id)
        councils = await self._council_verdicts(db, user_id)
        counterviews = await self._counterview_verdicts(db, user_id)
        merged = lines + mirrors + councils + counterviews
        merged.sort(key=lambda item: item["saved_at"], reverse=True)
        return merged


reflections_feed_service = ReflectionsFeedService()
