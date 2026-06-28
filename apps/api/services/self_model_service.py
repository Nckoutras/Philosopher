"""Self-model read service for the You vs You ritual.

Reads existing memory_entries (no new extraction) and splits them into a "then"
and "now" window to characterize the user's earlier and recent self.
Pure read + aggregation. No LLM, no writes.
"""
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import MemoryEntry

# ── Tunable thresholds ────────────────────────────────────────────────────────
WINDOW_SIZE = 12          # signals per window (earliest K = "then", latest K = "now")
MIN_TOTAL_ENTRIES = 20    # minimum active signals before the comparison unlocks
MIN_SPAN_DAYS = 14        # minimum days between earliest and latest signal
FORMING_PREVIEW_SIZE = 4  # recent signals surfaced while still "forming"


class SelfModelService:

    async def build(self, db: AsyncSession, user_id: str, *, bypass_gate: bool = False) -> dict:
        result = await db.execute(
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.is_active == True,
                # Voluntary counterview beliefs are their own surface (recurrence +
                # letter spine); keep them out of the You-vs-You then/now windows.
                MemoryEntry.entry_type != "counterview_belief",
                # self_portrait is atemporal self-knowledge (perpetual quiz answers);
                # excluded from the temporal then/now windows AND the
                # MIN_TOTAL_ENTRIES unlock gate, so answering questions can neither
                # pollute the contrast nor falsely unlock You-vs-You. It is reinjected
                # as a stable self-knowledge block in PR-1b.
                MemoryEntry.entry_type != "self_portrait",
                # self_portrait_shift rows are surfaced in the YvY closing + chat recall,
                # never as windowed signals — keep them out of the then/now windows AND the
                # unlock gate, same reasoning as self_portrait above.
                MemoryEntry.entry_type != "self_portrait_shift",
            )
            .order_by(MemoryEntry.created_at.asc())
        )
        entries = result.scalars().all()
        total = len(entries)

        # An empty self-model can never be windowed (no signals to split), so it
        # always stays "forming" — even for admins bypassing the gate.
        if total == 0:
            return self._forming(entries, total)

        if not bypass_gate:
            if total < MIN_TOTAL_ENTRIES:
                return self._forming(entries, total)

            span = entries[-1].created_at - entries[0].created_at
            if span < timedelta(days=MIN_SPAN_DAYS):
                return self._forming(entries, total)

        then_entries = entries[:WINDOW_SIZE]
        now_entries = entries[-WINDOW_SIZE:]
        return {
            "unlocked": True,
            "total_signals": total,
            "reason": None,
            "forming_preview": [],
            "then": self._window(then_entries),
            "now": self._window(now_entries),
        }

    def _forming(self, entries: list, total: int) -> dict:
        return {
            "unlocked": False,
            "total_signals": total,
            "reason": "forming",
            "forming_preview": [e.content for e in entries[-FORMING_PREVIEW_SIZE:]],
            "then": None,
            "now": None,
        }

    def _window(self, entries: list) -> dict:
        by_type: dict[str, list[str]] = {}
        for e in entries:
            by_type.setdefault(e.entry_type, []).append(e.content)
        return {"start": entries[0].created_at, "end": entries[-1].created_at, "by_type": by_type}


self_model_service = SelfModelService()
