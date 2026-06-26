"""Tests for the Counterview rebuttal exchange (POST /counterview/{id}/respond).

This path is safety-gated on BOTH ends (check_input on the user rebuttal,
check_output on the persona reply) and cap-enforced (MAX_REBUTTALS generated
turns). These tests lock that behaviour. The LLM and safety_service are mocked —
no live calls. The DB session is mocked in the house style (sequenced execute()),
so each test documents the exact execute() order it expects.

Covered:
- Cap: at the generated-rebuttal cap → respond raises cap_reached; the router maps
  it to 409; the serializer reports rebuttals_remaining == 0.
- Suppressed input: check_input suppress → turn persisted status='suppressed', NO
  LLM call, NO output check; cap not consumed (status != 'generated').
- Suppressed output: check_output suppress → reply dropped, status='suppressed';
  cap not consumed.
- Suppressed/empty turns don't block: with only 2 GENERATED turns counted, a 3rd
  rebuttal proceeds (suppressed/empty never consume the budget).
- Sequence race: IntegrityError on commit → rollback, returns the counterview, no
  crash.
- go-deeper untouched: a counterview with a round-1 deeper line + rebuttal turns
  serializes BOTH without collision.

Run: cd apps/api && pytest tests/services/test_counterview_rebuttal.py -v
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

import services.counterview_service as cs
from services.counterview_service import MAX_REBUTTALS, respond_to_rebuttal
import routers.counterview as rc
from routers.counterview import _serialize_counterview, respond_counterview
from schemas import CounterviewRespondRequest

USER_ID = "11111111-1111-1111-1111-111111111111"
CV_ID = "22222222-2222-2222-2222-222222222222"
PERSONA = "miyamoto_musashi"  # a real slug in COUNTERVIEW_PERSONAS


# ── helpers ──────────────────────────────────────────────────────────────────

_SENTINEL = object()


def _result(*, scalar=_SENTINEL, scalar_one=_SENTINEL, all_=_SENTINEL, first=_SENTINEL):
    """A canned execute() result configured only for the accessor a step uses."""
    r = MagicMock()
    if scalar is not _SENTINEL:
        r.scalar_one_or_none.return_value = scalar
    if scalar_one is not _SENTINEL:
        r.scalar_one.return_value = scalar_one
    if all_ is not _SENTINEL:
        r.scalars.return_value.all.return_value = all_
    if first is not _SENTINEL:
        r.first.return_value = first
    return r


def _db(results, *, commit_exc=None):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock(side_effect=commit_exc) if commit_exc else AsyncMock()
    return db


def _cv(status="generated"):
    cv = MagicMock()
    cv.id = CV_ID
    cv.user_id = USER_ID
    cv.status = status
    cv.anchor_text = "I should wait before leaving my job."
    cv.source = "direct"
    return cv


def _safety(suppress: bool):
    return MagicMock(should_suppress_persona=suppress)


@pytest.fixture
def patch_safety_llm(monkeypatch):
    """Default-safe gates + an LLM that returns one valid generated reply. Tests
    override individual pieces as needed."""
    monkeypatch.setattr(cs.safety_service, "check_input", AsyncMock(return_value=_safety(False)))
    monkeypatch.setattr(cs.safety_service, "check_output", AsyncMock(return_value=_safety(False)))
    monkeypatch.setattr(
        cs.llm_client, "complete",
        AsyncMock(return_value='{"status":"generated","verdict":"Waiting is fear in a calmer coat."}'),
    )
    # Decouple the bounded-context build (2 execute calls) from the orchestration
    # order under test — its own correctness is not what these tests cover.
    monkeypatch.setattr(cs, "_rebuttal_context", AsyncMock(return_value="Your case so far:\n- x"))
    return monkeypatch


# ── Cap enforcement ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cap_reached_raises(monkeypatch, patch_safety_llm):
    """At MAX_REBUTTALS generated turns, a further rebuttal raises cap_reached —
    no LLM call, no turn written."""
    monkeypatch.setattr(cs, "count_generated_rebuttals", AsyncMock(return_value=MAX_REBUTTALS))
    db = _db([_result(scalar=_cv())])  # only the cv load happens before the cap check

    with pytest.raises(ValueError, match="cap_reached"):
        await respond_to_rebuttal(db, USER_ID, CV_ID, PERSONA, "but I have a family")

    cs.llm_client.complete.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_router_maps_cap_to_409(monkeypatch):
    """The endpoint maps the cap_reached ValueError to HTTP 409."""
    from fastapi import HTTPException

    monkeypatch.setattr(rc, "respond_to_rebuttal", AsyncMock(side_effect=ValueError("cap_reached")))
    body = CounterviewRespondRequest(persona_slug=PERSONA, text="a rebuttal")
    user = MagicMock(id=USER_ID)

    with pytest.raises(HTTPException) as ei:
        await respond_counterview(CV_ID, body, db=AsyncMock(), user=user)
    assert ei.value.status_code == 409
    assert ei.value.detail == "rebuttal_cap_reached"


@pytest.mark.asyncio
async def test_serializer_rebuttals_remaining_zero_at_cap():
    """With MAX_REBUTTALS generated turns, the serializer reports 0 remaining."""
    cv = _cv()
    responses = [
        MagicMock(persona_slug=PERSONA, position=0, round=0, verdict="v0a"),
        MagicMock(persona_slug="niccolo_machiavelli", position=1, round=0, verdict="v0b"),
    ]
    turns = [
        MagicMock(sequence=i, persona_slug=PERSONA, user_text=f"u{i}", persona_response=f"r{i}", status="generated")
        for i in range(1, MAX_REBUTTALS + 1)
    ]
    personas = [
        SimpleNamespace(slug=PERSONA, name="Miyamoto Musashi", portrait_url="/p/musashi.webp"),
        SimpleNamespace(slug="niccolo_machiavelli", name="Niccolo Machiavelli", portrait_url="/p/mach.webp"),
    ]
    db = _db([
        _result(all_=responses),   # responses
        _result(all_=turns),       # turns
        _result(all_=personas),    # personas
        _result(first=None),       # is_saved
    ])

    out = await _serialize_counterview(db, cv, USER_ID)
    assert out.rebuttals_remaining == 0
    assert len(out.turns) == MAX_REBUTTALS


# ── Suppressed input ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suppressed_input_no_llm_no_consume(monkeypatch, patch_safety_llm):
    """check_input suppress → turn persisted status='suppressed', persona_response
    None, NO LLM call, NO output check, cap NOT consumed (non-generated status)."""
    monkeypatch.setattr(cs, "count_generated_rebuttals", AsyncMock(return_value=0))
    monkeypatch.setattr(cs.safety_service, "check_input", AsyncMock(return_value=_safety(True)))
    # execute order after the cap check: cv load, then _write_turn's max(seq) + cv reload
    db = _db([_result(scalar=_cv()), _result(scalar_one=0), _result(scalar_one=_cv())])

    await respond_to_rebuttal(db, USER_ID, CV_ID, PERSONA, "self-harming text")

    cs.llm_client.complete.assert_not_called()
    cs.safety_service.check_output.assert_not_called()
    turn = db.add.call_args[0][0]
    assert turn.status == "suppressed"
    assert turn.persona_response is None
    assert turn.status != "generated"  # → never counted toward the cap


# ── Suppressed output ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suppressed_output_drops_reply(monkeypatch, patch_safety_llm):
    """check_output suppress → reply dropped, turn status='suppressed', cap not
    consumed. The LLM IS called once (input passed)."""
    monkeypatch.setattr(cs, "count_generated_rebuttals", AsyncMock(return_value=0))
    monkeypatch.setattr(cs.safety_service, "check_output", AsyncMock(return_value=_safety(True)))
    db = _db([_result(scalar=_cv()), _result(scalar_one=0), _result(scalar_one=_cv())])

    await respond_to_rebuttal(db, USER_ID, CV_ID, PERSONA, "a sharp rebuttal")

    cs.llm_client.complete.assert_called_once()
    turn = db.add.call_args[0][0]
    assert turn.status == "suppressed"
    assert turn.persona_response is None


# ── Suppressed/empty don't block (cap counts generated only) ──────────────────

@pytest.mark.asyncio
async def test_third_rebuttal_proceeds_when_only_two_generated(monkeypatch, patch_safety_llm):
    """count_generated_rebuttals returns 2 (suppressed/empty turns don't count) →
    a further rebuttal is allowed and writes a GENERATED turn."""
    monkeypatch.setattr(cs, "count_generated_rebuttals", AsyncMock(return_value=2))
    db = _db([_result(scalar=_cv()), _result(scalar_one=0), _result(scalar_one=_cv())])

    await respond_to_rebuttal(db, USER_ID, CV_ID, PERSONA, "the market is bad")

    turn = db.add.call_args[0][0]
    assert turn.status == "generated"
    assert turn.persona_response  # a real reply was stored
    assert turn.sequence == 1     # max(seq)=0 → next ordinal


# ── Sequence race ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sequence_race_rolls_back(monkeypatch, patch_safety_llm):
    """A concurrent insert wins uq_counterview_turn_seq → IntegrityError on commit
    → rollback, return the counterview, no crash."""
    monkeypatch.setattr(cs, "count_generated_rebuttals", AsyncMock(return_value=0))
    cv = _cv()
    db = _db(
        [_result(scalar=cv), _result(scalar_one=0), _result(scalar_one=cv)],
        commit_exc=IntegrityError("stmt", {}, Exception("dup")),
    )

    result = await respond_to_rebuttal(db, USER_ID, CV_ID, PERSONA, "a rebuttal")

    db.rollback.assert_awaited_once()
    assert result is cv  # returned unchanged, no exception propagated


# ── go-deeper untouched: round-1 + turns serialize without collision ──────────

@pytest.mark.asyncio
async def test_serializes_deeper_and_turns_without_collision():
    """A counterview carrying a round-0 verdict, a round-1 go-deeper line, AND
    rebuttal turns serializes all of them — the two axes never collide."""
    cv = _cv()
    responses = [
        MagicMock(persona_slug=PERSONA, position=0, round=0, verdict="first cut"),
        MagicMock(persona_slug="niccolo_machiavelli", position=1, round=0, verdict="other cut"),
        MagicMock(persona_slug=PERSONA, position=0, round=1, verdict="deeper cut"),  # go-deeper
    ]
    turns = [
        MagicMock(sequence=1, persona_slug=PERSONA, user_text="u1", persona_response="r1", status="generated"),
        MagicMock(sequence=2, persona_slug="niccolo_machiavelli", user_text="u2", persona_response="r2", status="generated"),
    ]
    personas = [
        SimpleNamespace(slug=PERSONA, name="Miyamoto Musashi", portrait_url="/p/musashi.webp"),
        SimpleNamespace(slug="niccolo_machiavelli", name="Niccolo Machiavelli", portrait_url="/p/mach.webp"),
    ]
    db = _db([
        _result(all_=responses),
        _result(all_=turns),
        _result(all_=personas),
        _result(first=None),
    ])

    out = await _serialize_counterview(db, cv, USER_ID)

    # Both round-0 and the round-1 deeper line are present.
    rounds = sorted(r.round for r in out.responses)
    assert rounds == [0, 0, 1]
    # Both rebuttal turns are present and independent of the verdict rounds.
    assert [t.sequence for t in out.turns] == [1, 2]
    # 2 generated turns → 1 remaining (MAX_REBUTTALS - 2).
    assert out.rebuttals_remaining == MAX_REBUTTALS - 2
