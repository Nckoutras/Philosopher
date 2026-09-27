# -*- coding: utf-8 -*-
"""You-vs-You's crisis gate: recency refuses, older flags exclude (ruling 2026-09-25).

The gate used to refuse EVERY question when any high/critical message fell anywhere
between the earlier window's start and the recent window's end. For a long-standing
person that span is months, so one flagged message closed the ritual for months —
the founder hit it on 2026-09-25 with "how have I changed in terms of accepting
death as inevitable", which the input check passes.

Now:
  * a high/critical message in the LAST 14 DAYS refuses, before anything is
    generated, with the approved line "Let's leave this comparison for another day."
    (event: safety, level 'recent');
  * an OLDER flag does not refuse. Its conversation's memory rows are dropped from
    the then/now windows and its messages from the citable candidates, so crisis
    content is never replayed — while the unlock gate still counts every row, so an
    old flag cannot lock anyone out either.

The two queries are tested against real Postgres in
tests/db_live/test_yvy_window_gate.py; these tests cover the wiring and the
windowing, which are plain Python.

Run: cd apps/api && pytest tests/test_yvy_window_gate.py -v
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.self_comparison_service as scs
from services.self_model_service import self_model_service

USER_ID = "11111111-1111-1111-1111-111111111111"
T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)
FLAGGED = "aaaaaaaa-0000-0000-0000-00000000000f"   # real UUID strings, as the ORM loads them
OK = "aaaaaaaa-0000-0000-0000-0000000000a0"


def _entry(i, conversation_id, content=None):
    """Every field build() and _window() read, set explicitly (C-06)."""
    return SimpleNamespace(
        entry_type="struggle", content=content or f"signal {i}",
        conversation_id=conversation_id, created_at=T0 + timedelta(days=i),
    )


def _db_returning(entries):
    r = MagicMock()
    r.scalars.return_value.all.return_value = entries
    db = MagicMock()
    db.execute = AsyncMock(return_value=r)
    return db


# ── The windowing: exclusion drops rows from the windows, never from the gate ──


@pytest.mark.asyncio
async def test_excluded_conversations_leave_the_windows():
    entries = [_entry(i, FLAGGED if i in (0, 1, 30) else OK) for i in range(31)]
    entries[0].content = "crisis-adjacent then"
    entries[30].content = "crisis-adjacent now"
    model = await self_model_service.build(
        _db_returning(entries), USER_ID, exclude_conversation_ids={FLAGGED},
    )
    assert model["unlocked"] is True
    shown = [s for w in ("then", "now") for s in model[w]["by_type"]["struggle"]]
    assert "crisis-adjacent then" not in shown and "crisis-adjacent now" not in shown


@pytest.mark.asyncio
async def test_the_unlock_gate_still_counts_excluded_rows():
    """20 rows over 14+ days unlocks. 15 of them sit in a flagged conversation:
    the person is still unlocked — an old flag must not lock anyone out."""
    entries = [_entry(i, FLAGGED if i < 15 else OK) for i in range(20)]
    model = await self_model_service.build(
        _db_returning(entries), USER_ID, exclude_conversation_ids={FLAGGED},
    )
    assert model["unlocked"] is True
    assert model["total_signals"] == 20


@pytest.mark.asyncio
async def test_a_uuid_object_in_the_exclusion_set_still_drops_the_entry():
    """THE TYPE PIN. The ORM loads conversation_id as str (UUID(as_uuid=False)).
    A caller holding uuid.UUID objects must still exclude — without one shared
    representation, `str not in {UUID}` is always True and excludes nothing."""
    import uuid
    flagged = uuid.uuid4()
    entries = [_entry(i, str(flagged) if i in (0, 29) else "11111111-1111-1111-1111-111111111111")
               for i in range(30)]
    entries[0].content, entries[29].content = "flagged then", "flagged now"
    model = await self_model_service.build(
        _db_returning(entries), USER_ID, exclude_conversation_ids={flagged},
    )
    shown = [s for w in ("then", "now") for s in model[w]["by_type"]["struggle"]]
    assert "flagged then" not in shown and "flagged now" not in shown


@pytest.mark.asyncio
async def test_a_uuid_object_on_the_entry_side_is_dropped_too():
    import uuid
    flagged = uuid.uuid4()
    entries = [_entry(i, flagged if i == 0 else None) for i in range(24)]
    entries[0].content = "flagged then"
    model = await self_model_service.build(
        _db_returning(entries), USER_ID, exclude_conversation_ids={str(flagged).upper()},
    )
    shown = [s for w in ("then", "now") for s in model[w]["by_type"]["struggle"]]
    assert "flagged then" not in shown


@pytest.mark.asyncio
async def test_all_history_flagged_reads_as_forming():
    """KNOWN PROPERTY: when every signal sits in a flagged conversation nothing is
    left to compare, so the person reads as still forming (the stream answers
    not_unlocked). _forming must take the empty list without failing."""
    entries = [_entry(i, "22222222-2222-2222-2222-222222222222") for i in range(25)]
    model = await self_model_service.build(
        _db_returning(entries), USER_ID,
        exclude_conversation_ids={"22222222-2222-2222-2222-222222222222"},
    )
    assert model == {
        "unlocked": False, "total_signals": 25, "reason": "forming",
        "forming_preview": [], "then": None, "now": None,
    }


@pytest.mark.asyncio
async def test_rows_with_no_conversation_are_kept():
    entries = [_entry(i, None if i % 2 else OK) for i in range(24)]
    model = await self_model_service.build(
        _db_returning(entries), USER_ID, exclude_conversation_ids={FLAGGED},
    )
    shown = sum(len(v) for w in ("then", "now") for v in model[w]["by_type"].values())
    assert shown == 24


# ── The stream: recent refuses, older excludes ────────────────────────────────


def _window():
    return {"start": T0, "end": T0 + timedelta(days=60),
            "by_type": {"struggle": ["keeps postponing one decision"]}}


async def _run(monkeypatch, *, recent, flagged):
    streamed = []

    async def fake_stream(system=None, messages=None, model=None, **kw):
        streamed.append(system)
        yield "An answer."

    closing = json.dumps({"observation": "Then… lately…", "question": "Fair?",
                          "then_quote_id": None, "now_quote_id": None,
                          "hidden_continuity": None, "sentence_owed": None})
    build = AsyncMock(return_value={
        "unlocked": True, "total_signals": 30, "reason": None, "forming_preview": [],
        "then": _window(), "now": _window(),
    })
    candidates = AsyncMock(return_value=[])
    monkeypatch.setattr(scs.llm_client, "stream", fake_stream)
    monkeypatch.setattr(scs.llm_client, "complete", AsyncMock(return_value=closing))
    monkeypatch.setattr(scs.self_model_service, "build", build)
    monkeypatch.setattr(scs.self_comparison_service, "_recent_crisis", AsyncMock(return_value=recent))
    monkeypatch.setattr(scs.self_comparison_service, "_flagged_conversation_ids",
                        AsyncMock(return_value=flagged))
    monkeypatch.setattr(scs.self_comparison_service, "_candidates", candidates)

    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    r.scalar_one.return_value = 0
    r.all.return_value = []
    r.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=r)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()

    events = [json.loads(ev[len("data: "):]) async for ev in
              scs.self_comparison_service.stream(db, USER_ID, "How have I changed about work?")]
    return events, streamed, build, candidates


@pytest.mark.asyncio
async def test_a_recent_flag_refuses_before_anything_is_generated(monkeypatch):
    events, streamed, _, _ = await _run(monkeypatch, recent=True, flagged=set())
    assert events[0] == {"type": "safety", "level": "recent"}
    assert events[-1]["type"] == "done"
    assert streamed == [], "nothing may be generated"


@pytest.mark.asyncio
async def test_an_older_flag_does_not_refuse_it_excludes(monkeypatch):
    events, streamed, build, candidates = await _run(
        monkeypatch, recent=False, flagged={"c-flagged"},
    )
    assert "safety" not in [e["type"] for e in events]
    assert len(streamed) == 2, "both selves are generated"
    assert build.await_args.kwargs["exclude_conversation_ids"] == {"c-flagged"}
    for call in candidates.await_args_list:
        assert call.kwargs["exclude_conversation_ids"] == {"c-flagged"}


@pytest.mark.asyncio
async def test_no_flags_changes_nothing(monkeypatch):
    events, streamed, _, _ = await _run(monkeypatch, recent=False, flagged=set())
    assert "safety" not in [e["type"] for e in events]
    assert len(streamed) == 2


def test_the_recent_window_is_fourteen_days():
    assert scs.RECENT_CRISIS_DAYS == 14
