# -*- coding: utf-8 -*-
"""Post-generation safety on the eleven generators that had none (founder ruling 2026-09-24).

Chat, another-mind and go-deeper run check_output on every reply (TD-101). These did
not, so a harmful line from any of them reached the person with no second gate:

   #  path                          on a positive
   1  Council member verdict        safety_override; the council ends, nothing persists
   2  You-vs-You then/now answer    safety_override; the run ends, the row is removed
   3  weekly letter                 status='suppressed' (never emailed)
   4  monthly letter                status='suppressed' (never emailed)
   5  weekly / preview mirror       status='suppressed'
   6  insight mirror                status='suppressed'
   7  portrait summary              None -> the previous summary is kept
   8  conversation conclusion       no row
   9  conversation title            left NULL -> the library's default
  10  insight text (both writers)   no row
  11  forming reflection            [] -> the block hides

Every positive also writes one safety_events row whose trigger_stage names the
surface. None of these replaces the text with a crisis message: a title replaced by
a crisis message is worse than a default title.

THESE TESTS USE THE REAL safety_service. The LLM is stubbed to return a real
OUTPUT_RISK phrase, and nothing about the check itself is mocked, so removing a
call site fails the test. That is the gap the 2026-09-24 mutation run found in the
persona-lexicon wiring (M13), not repeated here.

Run: cd apps/api && pytest tests/test_output_safety_generators.py -v
"""
import ast
import inspect
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.memory_service as ms
import services.self_comparison_service as scs
import workers.arq_worker as aw
from models import Insight, Message, Mirror, SafetyEvent, WeeklyLetter
from services import safety_event_log as sel
from services.output_gate import output_is_unsafe
from services.safety_lexicons import OUTPUT_RISK_PHRASES

USER_ID = "11111111-1111-1111-1111-111111111111"
CONV_ID = "22222222-2222-2222-2222-222222222222"
INSIGHT_ID = "33333333-3333-3333-3333-333333333333"

RISK = "lethal dose"
assert RISK in OUTPUT_RISK_PHRASES, "the fixture must be a phrase the real check flags"

RISKY_EN = f"If it ever comes to that, a {RISK} is closer than you think."
CLEAN_EN = "What you call patience may be the fear of being the one who ends it."


class _Recorder:
    """A plain recorder, not a MagicMock (C-06): the tests assert on the TYPE of
    what was added, and a MagicMock would make 'was a row persisted?' unanswerable."""

    def __init__(self, results=()):
        self.added = []
        self.deleted = []
        self.executed = []
        self._results = list(results)
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.refresh = AsyncMock()

    def add(self, row):
        self.added.append(row)

    async def delete(self, row):
        self.deleted.append(row)

    async def execute(self, stmt, *a, **k):
        self.executed.append(stmt)
        if self._results:
            return self._results.pop(0)
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        r.scalar_one.return_value = 0
        r.scalar.return_value = None
        r.all.return_value = []
        r.scalars.return_value.all.return_value = []
        return r

    def of(self, cls):
        return [r for r in self.added if isinstance(r, cls)]


def _events(db, stage):
    return [e for e in db.of(SafetyEvent) if e.trigger_stage == stage]


def _r(*, scalar=None, all_=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    r.scalar.return_value = scalar
    r.scalars.return_value.all.return_value = all_ if all_ is not None else []
    return r


def _msg(content, role="user", safety_level="none"):
    """Every field these generators read, set explicitly (C-06)."""
    return SimpleNamespace(
        role=role, content=content, safety_level=safety_level, user_id=USER_ID,
        message_kind="standard",
        created_at=datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc),
    )


class _Session:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *a):
        return False


# ═══════════════════════════════════════════════════════════════════════════
# The helper
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_the_gate_flags_a_risky_payload_and_records_the_surface():
    db = _Recorder()
    result = await output_is_unsafe(
        db, {"title": "Sunday", "moments": [{"meant": RISKY_EN}]},
        user_id=USER_ID, stage=sel.STAGE_MIRROR_OUTPUT,
    )
    assert result and result.level == "high"
    (event,) = _events(db, "mirror_output")
    assert event.user_id == USER_ID and event.action_taken == "suppressed"


@pytest.mark.asyncio
async def test_the_gate_passes_clean_text_and_writes_nothing():
    db = _Recorder()
    assert await output_is_unsafe(db, CLEAN_EN, user_id=USER_ID, stage="x") is None
    assert db.added == []


@pytest.mark.asyncio
async def test_the_gate_without_a_session_still_says_no():
    assert await output_is_unsafe(None, RISKY_EN, user_id=USER_ID, stage="x")


# ═══════════════════════════════════════════════════════════════════════════
# 1 · Council member verdict (streamed)
# ═══════════════════════════════════════════════════════════════════════════


async def _council(member_text):
    import services.council_service as cvs

    async def fake_stream(*a, **kw):
        yield member_text

    persona = SimpleNamespace(name="Epictetus", slug="epictetus")
    db = _Recorder()
    with (
        patch.object(cvs.llm_client, "stream", fake_stream),
        patch.object(cvs.llm_client, "complete", AsyncMock(return_value="")),
        patch.object(cvs, "get_persona", return_value=persona),
        patch.object(cvs.prompt_builder, "build_system", return_value="system"),
        patch.object(cvs.memory_service, "recall", AsyncMock(return_value=[])),
    ):
        events = []
        async for ev in cvs.council_service.stream_council(
            db=db, user_id=USER_ID, matter="Should I leave my job this year?",
        ):
            events.append(json.loads(ev[len("data: "):]))
    return events, db


@pytest.mark.asyncio
async def test_a_harmful_council_verdict_is_overridden_and_the_council_ends():
    events, db = await _council(RISKY_EN)
    types = [e["type"] for e in events]
    assert "safety_override" in types
    assert "synthesis" not in types and "synthesis_start" not in types
    assert types[-1] == "done"
    assert len(_events(db, "council_member_output")) == 1


@pytest.mark.asyncio
async def test_an_overridden_council_does_not_spend_the_weekly_allowance():
    """The TD-101 rule: no allowance consumed. The allowance is a count of
    council_cases rows, so the case is deleted, as the input-safety exit never
    creates one."""
    _, db = await _council(RISKY_EN)
    deletes = [s for s in db.executed if type(s).__name__ == "Delete"]
    assert deletes and deletes[0].table.name == "council_cases"


@pytest.mark.asyncio
async def test_a_clean_council_verdict_is_not_touched():
    events, db = await _council(CLEAN_EN)
    assert "safety_override" not in [e["type"] for e in events]
    assert _events(db, "council_member_output") == []


# ═══════════════════════════════════════════════════════════════════════════
# 2 · You vs You then/now answers (streamed)
# ═══════════════════════════════════════════════════════════════════════════


def _window():
    return {
        "start": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "end": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "by_type": {"struggle": ["keeps postponing one decision"]},
    }


async def _yvy(monkeypatch, self_answer):
    async def fake_stream(system=None, messages=None, model=None, **kw):
        yield self_answer

    closing = json.dumps({"observation": CLEAN_EN, "question": "Does that feel fair?",
                          "then_quote_id": None, "now_quote_id": None,
                          "hidden_continuity": None, "sentence_owed": None})
    monkeypatch.setattr(scs.llm_client, "stream", fake_stream)
    monkeypatch.setattr(scs.llm_client, "complete", AsyncMock(return_value=closing))
    monkeypatch.setattr(scs.self_model_service, "build", AsyncMock(return_value={
        "unlocked": True, "total_signals": 9, "reason": None,
        "forming_preview": [], "then": _window(), "now": _window(),
    }))
    db = _Recorder()
    events = []
    async for ev in scs.self_comparison_service.stream(
        db, USER_ID, "What am I actually afraid of when I put off this decision?"
    ):
        events.append(json.loads(ev[len("data: "):]))
    return events, db


@pytest.mark.asyncio
async def test_a_harmful_self_answer_is_overridden_and_the_run_removed(monkeypatch):
    events, db = await _yvy(monkeypatch, RISKY_EN)
    types = [e["type"] for e in events]
    assert "safety_override" in types
    assert "closing" not in types, "no closing is generated over a withheld answer"
    assert types[-1] == "done"
    assert len(_events(db, "self_comparison_output")) == 1
    # The pending row counts toward the weekly allowance, so it goes.
    assert len(db.deleted) == 1 and type(db.deleted[0]).__name__ == "SelfComparison"


@pytest.mark.asyncio
async def test_a_clean_self_answer_is_not_touched(monkeypatch):
    events, db = await _yvy(monkeypatch, CLEAN_EN)
    assert "safety_override" not in [e["type"] for e in events]
    assert db.deleted == []


# ═══════════════════════════════════════════════════════════════════════════
# 3 + 4 · Weekly and monthly letters
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_harmful_letter_is_stored_suppressed_and_recorded():
    db = _Recorder()
    now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    withheld = await aw._letter_output_withheld(
        db, user_id=USER_ID, data={"status": "generated", "opening": RISKY_EN},
        stage=sel.STAGE_WEEKLY_LETTER_OUTPUT, voice_persona_id="p1",
        period_start=now, period_end=now, kind="weekly",
    )
    assert withheld
    (letter,) = db.of(WeeklyLetter)
    assert letter.status == "suppressed" and letter.payload is None
    assert letter.kind == "weekly"
    assert len(_events(db, "weekly_letter_output")) == 1
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_a_clean_letter_is_left_to_the_task():
    db = _Recorder()
    now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    withheld = await aw._letter_output_withheld(
        db, user_id=USER_ID, data={"status": "generated", "opening": CLEAN_EN},
        stage=sel.STAGE_MONTHLY_LETTER_OUTPUT, voice_persona_id="p1",
        period_start=now, period_end=now, kind="monthly",
    )
    assert not withheld and db.added == []


@pytest.mark.parametrize("task,stage", [
    ("generate_weekly_letter_task", "STAGE_WEEKLY_LETTER_OUTPUT"),
    ("generate_monthly_letter_task", "STAGE_MONTHLY_LETTER_OUTPUT"),
])
def test_both_letter_tasks_withhold_before_writing_a_generated_letter(task, stage):
    """STRUCTURAL, declared as such. The letter tasks run eleven queries before the
    LLM call and have no behavioural harness anywhere in this suite; the helper is
    tested behaviourally above, and this pins the wiring: an `if await
    _letter_output_withheld(...): return` naming this stage, placed before the
    status='generated' WeeklyLetter is built. Removing the call fails this test."""
    fn = next(n for n in ast.walk(ast.parse(inspect.getsource(aw)))
              if isinstance(n, ast.AsyncFunctionDef) and n.name == task)
    gate = [n for n in ast.walk(fn) if isinstance(n, ast.If)
            and "_letter_output_withheld" in ast.unparse(n.test)
            and stage in ast.unparse(n.test)
            and any(isinstance(b, ast.Return) for b in n.body)]
    assert len(gate) == 1
    generated = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and ast.unparse(n.func) == "WeeklyLetter"
                 and "status='generated'" in ast.unparse(n)]
    assert generated and gate[0].lineno < min(g.lineno for g in generated)


# ═══════════════════════════════════════════════════════════════════════════
# 5 · Weekly / preview mirror
# ═══════════════════════════════════════════════════════════════════════════


async def _mirror(reply, kind="weekly"):
    persona = SimpleNamespace(id="p1", name="Carl Jung", tradition="analytical psychology")
    week = [_msg("I keep thinking about whether I should leave my job this year.")] * 5
    db = _Recorder([_r(scalar=persona), _r(scalar=None), _r(all_=week)])
    with (
        patch("db.session.AsyncSessionLocal", lambda: _Session(db)),
        patch("services.llm_client.llm_client.complete", new=AsyncMock(return_value=reply)),
    ):
        await aw.generate_weekly_mirror_task({}, USER_ID, "carl_jung", kind, 7)
    return db


MIRROR_RISKY = json.dumps({"status": "generated", "thread": RISKY_EN,
                           "moments": [{"said": "I keep thinking", "meant": CLEAN_EN}]})
MIRROR_CLEAN = json.dumps({"status": "generated", "thread": CLEAN_EN,
                           "moments": [{"said": "I keep thinking", "meant": CLEAN_EN}]})


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["weekly", "preview"])
async def test_a_harmful_mirror_is_stored_suppressed(kind):
    db = await _mirror(MIRROR_RISKY, kind)
    (mirror,) = db.of(Mirror)
    assert mirror.status == "suppressed" and mirror.payload is None
    assert len(_events(db, "mirror_output")) == 1


@pytest.mark.asyncio
async def test_a_clean_mirror_is_generated():
    db = await _mirror(MIRROR_CLEAN)
    (mirror,) = db.of(Mirror)
    assert mirror.status == "generated"


# ═══════════════════════════════════════════════════════════════════════════
# 6 · Insight mirror
# ═══════════════════════════════════════════════════════════════════════════


async def _insight_mirror(reply):
    import services.insight_mirror_service as ims

    persona = SimpleNamespace(id="p1", slug="carl_jung", name="Carl Jung",
                              tradition="analytical psychology")
    insight = SimpleNamespace(id=INSIGHT_ID, user_id=USER_ID, content=CLEAN_EN,
                              conversation_id=CONV_ID)
    convo = [_msg("I keep waiting for the right moment to say something about it."),
             _msg("I do not want to be the one who ends this, so I wait instead.")]
    db = _Recorder([
        _r(scalar=insight), _r(scalar=None),
        _r(scalar=SimpleNamespace(mirror_host_slug="carl_jung")),
        _r(scalar=persona), _r(all_=convo), _r(scalar=persona),
    ])
    with patch.object(ims.llm_client, "complete", AsyncMock(return_value=reply)):
        await ims.generate_insight_mirror(db, USER_ID, INSIGHT_ID)
    return db


@pytest.mark.asyncio
async def test_a_harmful_insight_mirror_is_stored_suppressed():
    db = await _insight_mirror(MIRROR_RISKY)
    (mirror,) = db.of(Mirror)
    assert mirror.status == "suppressed" and mirror.payload is None
    assert len(_events(db, "insight_mirror_output")) == 1


@pytest.mark.asyncio
async def test_a_clean_insight_mirror_is_generated():
    db = await _insight_mirror(MIRROR_CLEAN)
    (mirror,) = db.of(Mirror)
    assert mirror.status == "generated"


# ═══════════════════════════════════════════════════════════════════════════
# 7 · Portrait summary
# ═══════════════════════════════════════════════════════════════════════════


async def _portrait(summary, why="because"):
    import services.self_portrait_summary as sps

    async def fake_complete(system, user, model=None, max_tokens=512):
        return json.dumps({"summary": summary, "best_fit": [{"slug": "socrates", "why": why}]})

    persona = SimpleNamespace(slug="socrates", name="Socrates",
                              portrait_url="/personas/socrates.webp", bio="bio")
    db = _Recorder([_r(all_=[persona])])
    with patch.object(sps, "llm_client") as llm, \
         patch.object(sps, "answers_to_statements", return_value=["Asked X, they answered: Y."]), \
         patch.object(sps, "themes_from_answers", return_value=["work"]), \
         patch.object(sps, "compute_matches", return_value=[SimpleNamespace(slug="socrates")]), \
         patch.object(sps, "_recent_signals", new=AsyncMock(return_value=[])):
        llm.complete = fake_complete
        out = await sps.generate_portrait(db, USER_ID, {"q1": 0}, "clarity")
    return out, db


@pytest.mark.asyncio
async def test_a_harmful_portrait_summary_keeps_the_previous_one():
    """None is the caller's existing keep-the-previous-summary path."""
    out, db = await _portrait(RISKY_EN)
    assert out is None
    assert len(_events(db, "portrait_summary_output")) == 1


@pytest.mark.asyncio
async def test_a_harmful_best_fit_reason_is_caught_too():
    out, _ = await _portrait(CLEAN_EN, why=RISKY_EN)
    assert out is None


@pytest.mark.asyncio
async def test_a_clean_portrait_summary_is_returned():
    out, _ = await _portrait(CLEAN_EN)
    assert out and out["text"] == CLEAN_EN


# ═══════════════════════════════════════════════════════════════════════════
# 8 · Conversation conclusion
# ═══════════════════════════════════════════════════════════════════════════


async def _conclusion(reply):
    conv = SimpleNamespace(id=CONV_ID, user_id=USER_ID, persona_id="p1")
    persona = SimpleNamespace(id="p1", name="Carl Jung", tradition="analytical psychology")
    window = [_msg("I keep thinking about whether I should leave my job this year."),
              _msg(CLEAN_EN, role="assistant")]
    db = _Recorder([_r(scalar=conv), _r(scalar=None), _r(all_=window), _r(scalar=persona)])
    with (
        patch("db.session.AsyncSessionLocal", lambda: _Session(db)),
        patch("services.llm_client.llm_client.complete", new=AsyncMock(return_value=reply)),
    ):
        await aw.assess_conclusion_task({}, CONV_ID, USER_ID)
    return db


@pytest.mark.asyncio
async def test_a_harmful_conclusion_writes_no_row():
    db = await _conclusion(RISKY_EN)
    assert db.of(Message) == []
    (event,) = _events(db, "conclusion_output")
    assert event.conversation_id == CONV_ID


@pytest.mark.asyncio
async def test_a_clean_conclusion_is_written():
    db = await _conclusion(CLEAN_EN)
    assert len(db.of(Message)) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 9 · Conversation title
# ═══════════════════════════════════════════════════════════════════════════


async def _title(reply):
    conv = SimpleNamespace(id=CONV_ID, user_id=USER_ID, title=None)
    msgs = [_msg("I keep thinking about whether I should leave my job."),
            _msg(CLEAN_EN, role="assistant")]
    db = _Recorder([_r(all_=msgs), _r(scalar=conv)])
    with (
        patch("db.session.AsyncSessionLocal", lambda: _Session(db)),
        patch("services.llm_client.llm_client.complete", new=AsyncMock(return_value=reply)),
    ):
        await aw.generate_conversation_title({}, CONV_ID)
    return conv, db


@pytest.mark.asyncio
async def test_a_harmful_title_is_left_null():
    conv, db = await _title(f"The {RISK}")
    assert conv.title is None, "NULL is the library's default: it shows the last snippet"
    (event,) = _events(db, "title_output")
    assert event.user_id == USER_ID and event.conversation_id == CONV_ID


@pytest.mark.asyncio
async def test_a_clean_title_is_set():
    conv, _ = await _title("Leaving the job")
    assert conv.title == "Leaving the job"


# ═══════════════════════════════════════════════════════════════════════════
# 10 · Insight text — both writers
# ═══════════════════════════════════════════════════════════════════════════


async def _signal_insight(content):
    async def fake_complete(system, user, model=None, max_tokens=512):
        return json.dumps([{"type": "dilemma", "content": content, "confidence": 0.95}])

    db = _Recorder()
    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(return_value=[0.0] * 1536)), \
         patch.object(ms.memory_service, "_insight_gate_blocked",
                      new=AsyncMock(return_value=None)):
        await ms.memory_service.extract_and_store(
            db, USER_ID, CONV_ID, "p1", "I keep thinking about leaving my job.",
            "assistant reply", source_turn=1, safety_ok=True,
        )
    return db


@pytest.mark.asyncio
async def test_a_harmful_signal_insight_is_not_written():
    db = await _signal_insight(f"Whether to leave the job, or whether a {RISK} is easier.")
    assert db.of(Insight) == []
    assert len(_events(db, "insight_output")) == 1


@pytest.mark.asyncio
async def test_a_clean_signal_insight_is_written():
    db = await _signal_insight("Whether to leave a secure job for work that means something.")
    assert len(db.of(Insight)) == 1


async def _recurrence(content):
    async def complete(**kw):
        return json.dumps({"insight_type": "pattern", "content": content})

    entry = SimpleNamespace(id="e1", content="a memory row", embedding=[0.1] * 8,
                            conversation_id=CONV_ID)
    rows = MagicMock()
    rows.fetchall.return_value = [SimpleNamespace(id="m1", score=0.99, content="an older row",
                                                  conversation_id="other")]
    db = _Recorder([rows])
    with patch.object(ms.memory_service, "_insight_gate_blocked", AsyncMock(return_value=None)), \
         patch("services.llm_client.llm_client.complete", new=complete):
        await ms.memory_service.detect_recurrence(
            db=db, user_id=USER_ID, conversation_id=CONV_ID, persona_id="p1",
            new_entries=[entry], language="English",
        )
    return db


@pytest.mark.asyncio
async def test_a_harmful_recurrence_insight_is_not_written():
    db = await _recurrence(f"The same question has come back, and so has the {RISK}.")
    assert db.of(Insight) == []
    assert len(_events(db, "insight_output")) == 1


@pytest.mark.asyncio
async def test_a_clean_recurrence_insight_is_written():
    db = await _recurrence("The question of whether to leave your job has come up again.")
    assert len(db.of(Insight)) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 11 · Forming reflection
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_harmful_forming_reflection_hides(monkeypatch):
    monkeypatch.setattr(scs.llm_client, "complete",
                        AsyncMock(return_value=f"- Returning to one decision\n- {RISKY_EN}"))
    db = _Recorder()
    out = await scs.self_comparison_service.forming_reflection(
        ["keeps postponing one decision"], language="English", db=db, user_id=USER_ID,
    )
    assert out == []
    assert len(_events(db, "forming_reflection_output")) == 1


@pytest.mark.asyncio
async def test_a_clean_forming_reflection_is_returned(monkeypatch):
    monkeypatch.setattr(scs.llm_client, "complete",
                        AsyncMock(return_value="- Returning often to the same decision"))
    out = await scs.self_comparison_service.forming_reflection(
        ["keeps postponing one decision"], language="English", db=_Recorder(), user_id=USER_ID,
    )
    assert out == ["Returning often to the same decision"]


def test_every_forming_reflection_caller_hands_over_its_session():
    """So a positive is recorded, not only withheld. Three callers, per the
    function's own docstring."""
    import routers.preferences as prefs
    import routers.self_comparison as rsc
    calls = [
        n for mod in (prefs, rsc) for n in ast.walk(ast.parse(inspect.getsource(mod)))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "forming_reflection"
    ]
    assert len(calls) == 3
    for call in calls:
        kwargs = {k.arg: ast.unparse(k.value) for k in call.keywords}
        assert kwargs.get("db") == "db" and "user_id" in kwargs
