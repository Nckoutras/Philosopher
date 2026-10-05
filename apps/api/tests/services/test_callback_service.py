"""MEM2-C-2 — the callback gate, its copy, and its mocked query paths.

THREE THINGS ARE PINNED, and they fail independently:

  1. THE COPY IS THE MEASURED COPY. prompts/callback_directive*.txt equal, byte for
     byte, the evals strings C-1 and STEP 0(b) ran; so do the {when} buckets and the
     rendered block for every age. A reworded production file fails here.

  2. THE GATE IS THE EVAL GATE. Every C-1 sample, with C-1's own stored scores, is
     run through both gates; production must offer the same row (the floor and
     C-2's added rules set to pass — they have their own tests below).

  3. EACH RULE IS NAMED. One test per turn rule and per row rule, asserting the
     reason the gate log will print, in the documented order.

What a mock cannot prove — that the SQL selects what the rules assume — is in
tests/db_live/test_memory_callbacks_live.py, which executes it.
"""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals import callback_directive as ev
from evals import callback_gate as ev_gate
from evals import callback_run as ev_run
from evals import harness as ev_harness
from evals.callback_samples import build_samples
from services import callback_service as cs

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
CONV = "c-current"
PERSONA = "p-responder"


# ── 1. The copy ──────────────────────────────────────────────────────────────

def test_production_copy_is_the_measured_evals_copy():
    assert cs.DIRECTIVE == ev.DIRECTIVE
    assert cs.DIRECTIVE_EL == ev.DIRECTIVE_EL
    assert cs.WHEN_BUCKETS == ev.WHEN_BUCKETS
    assert cs.WHEN_BUCKETS_EL == ev.WHEN_BUCKETS_EL


def test_the_copy_files_carry_one_trailing_newline_and_nothing_else():
    root = Path(cs.__file__).resolve().parent.parent / "prompts"
    for name, copy in (("callback_directive.txt", ev.DIRECTIVE),
                       ("callback_directive_el.txt", ev.DIRECTIVE_EL)):
        body = (root / name).read_text(encoding="utf-8")
        assert body == copy + "\n", name


@pytest.mark.parametrize("lang", ["en", "el"])
def test_every_rendered_block_matches_evals(lang):
    original = "I keep {braces} and «quotes» as typed.  "
    for days in range(0, 400):
        assert cs.render_block(original, days, lang) == ev.render_block(original, days, lang)


def test_insertion_is_the_harness_insertion():
    system = "A\n\nWHAT YOU KNOW\nrow\n\n\n" + cs.HARD_RULES_ANCHOR + "\n1. rule"
    assert cs.HARD_RULES_ANCHOR == ev_harness.HARD_RULES_ANCHOR
    assert cs.insert_block(system, "BLOCK") == ev_harness._insert_callback(system, "BLOCK")


def test_insertion_refuses_a_missing_or_doubled_anchor():
    with pytest.raises(ValueError):
        cs.insert_block("no anchor", "B")
    with pytest.raises(ValueError):
        cs.insert_block(cs.HARD_RULES_ANCHOR + cs.HARD_RULES_ANCHOR, "B")


@pytest.mark.parametrize("text,lang", [
    ("I keep thinking about my job.", "en"),
    ("Σκέφτομαι συνέχεια τη δουλειά μου.", "el"),
    ("", "en"),
])
def test_conversation_language(text, lang):
    assert cs.conversation_language(text) == lang


# ── 2. Parity with the eval gate, over every C-1 sample ──────────────────────

def _scored_samples():
    samples = build_samples()
    stored = json.loads((Path(ev_run.RESULTS_DIR) / "2026-10-05_mem2c1" / "scores.json")
                        .read_text(encoding="utf-8"))
    ev_run.apply_scores(samples, stored)
    return samples


def _as_candidate(row, sample) -> cs.CandidateRow:
    """The eval row in production's shape. persona slug stands in for persona_id on
    both sides; every eval row that has message ids also has an original message in
    the world C-1 models, so `original` is present whenever ids are."""
    return cs.CandidateRow(
        id=row.id, entry_type=row.entry_type, content=row.content,
        created_at=NOW - timedelta(days=row.days_ago),
        conversation_id=row.conversation_id, persona_id=row.persona_slug,
        source_message_ids=list(row.source_message_ids) if row.source_message_ids else None,
        is_active=row.is_active, elicited_by_callback=row.elicited_by_callback,
        callback_blocked_at=None, flagged_conversation=row.flagged_conversation,
        offered_in_conversation=row.id in sample.offered_in_conversation,
        chain_offered_recently=False,
        original=(row.original or "the person's words") if row.source_message_ids else None,
        score=row.score,
    )


def test_production_offers_what_the_eval_gate_offers_on_every_c1_sample():
    samples = _scored_samples()
    assert len(samples) == 132
    offered = 0
    for s in samples:
        want = ev_gate.offer(s.rows, responder_slug=s.persona_slug,
                             current_conversation_id=s.conversation_id,
                             offered_in_conversation=s.offered_in_conversation)
        got, _ = cs.choose([_as_candidate(r, s) for r in s.rows],
                           responder_persona_id=s.persona_slug,
                           current_conversation_id=s.conversation_id,
                           now=NOW, floor=-1.0)
        assert (got.id if got else None) == (want.id if want else None), s.sample_id
        offered += got is not None
    assert offered == 110, "C-1 offered on every scenario but L1 (22 samples)"


def test_with_the_floor_on_no_tangential_sample_is_offered():
    """STEP 0(a)'s ruling, re-derived: at 0.35 on candidate_row_cosine, zero T."""
    for s in _scored_samples():
        if s.scenario != "T":
            continue
        got, _ = cs.choose([_as_candidate(r, s) for r in s.rows],
                           responder_persona_id=s.persona_slug,
                           current_conversation_id=s.conversation_id, now=NOW)
        assert got is None, s.sample_id


# ── 3. The rules, one by one ─────────────────────────────────────────────────

@pytest.mark.parametrize("kw,reason", [
    (dict(user_plan="free"), "plan"),
    (dict(gate_outcome="DISTRESS"), "turn_not_normal"),
    (dict(gate_outcome="DISCUSSING"), "turn_not_normal"),
    (dict(safety_level="low"), "turn_not_normal"),
    (dict(deep_mode=True), "deep_mode"),
    (dict(), None),
    (dict(user_plan="premium"), None),
])
def test_turn_rules(kw, reason):
    base = dict(user_plan="pro", gate_outcome="NORMAL", safety_level="none", deep_mode=False)
    assert cs.turn_ineligible(**{**base, **kw}) == reason


def _row(**kw) -> cs.CandidateRow:
    base = dict(
        id="r1", entry_type="struggle", content="User struggles with X.",
        created_at=NOW - timedelta(days=10), conversation_id="c-old",
        persona_id=PERSONA, source_message_ids=["u1", "a1"], is_active=True,
        elicited_by_callback=False, callback_blocked_at=None,
        flagged_conversation=False, offered_in_conversation=False,
        chain_offered_recently=False, original="I struggle with X.", score=0.5,
    )
    return cs.CandidateRow(**{**base, **kw})


def _why(row):
    return cs.why_ineligible(row, responder_persona_id=PERSONA,
                             current_conversation_id=CONV, now=NOW)


@pytest.mark.parametrize("kw,reason", [
    (dict(source_message_ids=None), "no_source_message_ids"),          # a
    (dict(source_message_ids=[]), "no_source_message_ids"),
    (dict(is_active=False), "inactive"),                                # b
    (dict(conversation_id=None), "same_or_no_conversation"),            # c
    (dict(conversation_id=CONV), "same_or_no_conversation"),
    (dict(persona_id="p-other"), "other_persona"),                      # d
    (dict(flagged_conversation=True), "flagged_conversation"),          # e
    (dict(elicited_by_callback=True), "elicited_by_callback"),          # f
    (dict(offered_in_conversation=True), "already_offered_this_conversation"),  # g
    (dict(created_at=NOW - timedelta(days=1, hours=23)), "too_new"),     # h
    (dict(chain_offered_recently=True), "chain_cooldown"),              # i
    (dict(callback_blocked_at=NOW), "callback_blocked"),                # j
    (dict(original=None), "no_original"),                               # k
    (dict(original=""), "no_original"),
    (dict(score=0.3499), "below_floor"),                                # l
    (dict(), None),
    (dict(created_at=NOW - timedelta(days=2)), None),                   # exactly 2 days
    (dict(score=0.35), None),                                           # exactly the floor
])
def test_row_rules(kw, reason):
    assert _why(_row(**kw)) == reason


def test_the_first_failing_rule_is_the_one_named():
    """Order is the log's meaning: a row failing a and l reports a."""
    assert _why(_row(source_message_ids=None, score=0.0, persona_id="x")) == "no_source_message_ids"
    assert _why(_row(persona_id="x", flagged_conversation=True)) == "other_persona"


def test_choose_orders_by_score_then_newest_then_id_and_counts_exclusions():
    a = _row(id="b", score=0.6, created_at=NOW - timedelta(days=5))
    b = _row(id="a", score=0.6, created_at=NOW - timedelta(days=5))
    c = _row(id="c", score=0.6, created_at=NOW - timedelta(days=3))
    d = _row(id="d", score=0.9, persona_id="other")
    got, excluded = cs.choose([a, b, c, d], responder_persona_id=PERSONA,
                              current_conversation_id=CONV, now=NOW)
    assert got.id == "c"
    assert excluded == {"other_persona": 1}
    got, _ = cs.choose([a, b], responder_persona_id=PERSONA,
                       current_conversation_id=CONV, now=NOW)
    assert got.id == "a"


# ── 4. select_callback against a stand-in session ────────────────────────────

def _session(*results):
    db = MagicMock()
    savepoint = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    db.begin_nested = AsyncMock(return_value=savepoint)
    db.execute = AsyncMock(side_effect=list(results))
    return db, savepoint


def _scalar(value):
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _rows(*rows):
    r = MagicMock()
    r.fetchall.return_value = [MagicMock(_mapping=vars(x)) for x in rows]
    return r


async def _select(db, **kw):
    base = dict(user_id="u", conversation_id=CONV, responder_persona_id=PERSONA,
                user_plan="pro", gate_outcome="NORMAL", safety_level="none",
                deep_mode=False, user_text="I keep thinking about X.",
                query_vec=[0.1, 0.2], now=NOW)
    return await cs.select_callback(db, **{**base, **kw})


async def test_an_ineligible_turn_runs_no_query():
    db, _ = _session()
    assert await _select(db, user_plan="free") is None
    db.execute.assert_not_awaited()
    db.begin_nested.assert_not_awaited()


async def test_a_turn_without_a_query_vector_runs_no_query():
    db, _ = _session()
    assert await _select(db, query_vec=None) is None
    db.execute.assert_not_awaited()


async def test_the_user_cooldown_stops_before_the_pool_query():
    db, sp = _session(_scalar(True))
    assert await _select(db) is None
    assert db.execute.await_count == 1
    params = db.execute.await_args_list[0].args[1]
    assert params["since"] == NOW - timedelta(days=7)
    sp.commit.assert_awaited_once()


async def test_an_offer_carries_the_rendered_block_in_the_conversation_language():
    db, _ = _session(_scalar(False), _rows(_row(score=0.5, created_at=NOW - timedelta(days=9))))
    offer = await _select(db, user_text="Σκέφτομαι συνέχεια τη δουλειά μου.")
    assert offer.id == "r1" and offer.days == 9 and offer.language == "el"
    assert offer.block == cs.render_block("I struggle with X.", 9, "el")
    pool_params = db.execute.await_args_list[1].args[1]
    assert pool_params["chain_since"] == NOW - timedelta(days=30)
    assert pool_params["conversation_id"] == CONV


async def test_a_query_failure_rolls_back_the_savepoint_and_raises():
    db, sp = _session(RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await _select(db)
    sp.rollback.assert_awaited_once()


def test_record_offer_adds_the_ledger_row():
    db = MagicMock()
    offer = cs.CallbackOffer(id="m1", entry_type="struggle", content="c", score=0.42,
                             days=9, language="en", block="B")
    cs.record_offer(db, user_id="u", offer=offer, persona_id="p",
                    conversation_id="c", message_id="a")
    (row,), _ = db.add.call_args
    assert (row.user_id, row.memory_id, row.persona_id, row.conversation_id,
            row.message_id, row.score) == ("u", "m1", "p", "c", "a", 0.42)


# ── 5. Ruling 9's turn lookup ────────────────────────────────────────────────

U = "11111111-1111-1111-1111-111111111111"
A = "22222222-2222-2222-2222-222222222222"


def _one(**fields):
    r = MagicMock()
    r.one.return_value = MagicMock(**fields)
    return r


@pytest.mark.parametrize("ids", [None, [], [U], ["m1", "m2"], [U, "not-a-uuid"]])
async def test_a_pair_that_cannot_be_placed_is_neither_and_runs_no_query(ids):
    db, _ = _session()
    assert await cs.callback_turn_role(db, ids) == (False, False)
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("offer,reply", [(True, False), (False, True), (False, False), (True, True)])
async def test_turn_role_reads_both_flags(offer, reply):
    db, _ = _session(_one(offer_turn=offer, reply_turn=reply))
    assert await cs.callback_turn_role(db, [U, A]) == (offer, reply)
    params = db.execute.await_args.args[1]
    assert params == {"user_message_id": U, "assistant_id": A}


async def test_a_stand_in_row_marks_nothing():
    """C-06: a Mock field is truthy. `is True` keeps an unset stand-in from marking."""
    db, _ = _session(_one())
    assert await cs.callback_turn_role(db, [U, A]) == (False, False)


async def test_a_lookup_failure_is_treated_as_a_reply_turn():
    db, sp = _session(RuntimeError("boom"))
    assert await cs.callback_turn_role(db, [U, A]) == (False, True)
    sp.rollback.assert_awaited_once()


# ── 6. The rejection, against a stand-in session ─────────────────────────────

def _ledger(reaction=None):
    return MagicMock(id="cb-1", memory_id="m-1", user_id="u", reaction=reaction, reacted_at=None)


def _found(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


async def test_rejecting_another_users_callback_finds_nothing():
    db = MagicMock(execute=AsyncMock(return_value=_found(None)), flush=AsyncMock())
    assert await cs.reject_callback(db, user_id="u", callback_id="cb-x", now=NOW) is None
    assert db.execute.await_count == 1


async def test_a_second_rejection_changes_nothing():
    cb = _ledger(reaction="rejected")
    db = MagicMock(execute=AsyncMock(return_value=_found(cb)), flush=AsyncMock())
    out = await cs.reject_callback(db, user_id="u", callback_id="cb-1", now=NOW)
    assert out.already_rejected is True and (out.retired, out.blocked, out.blocked_near_duplicates) == (0, 0, 0)
    assert db.execute.await_count == 1
    db.flush.assert_not_awaited()


async def test_a_rejection_retires_blocks_and_records_the_reaction():
    cb = _ledger()
    chain = MagicMock()
    chain.fetchall.return_value = [MagicMock(id="11111111-1111-1111-1111-111111111111"),
                                   MagicMock(id="22222222-2222-2222-2222-222222222222")]
    db = MagicMock(execute=AsyncMock(side_effect=[
        _found(cb), chain, MagicMock(rowcount=1), MagicMock(rowcount=2), MagicMock(rowcount=3),
    ]), flush=AsyncMock())
    out = await cs.reject_callback(db, user_id="u", callback_id="cb-1", now=NOW)
    assert (out.retired, out.blocked, out.blocked_near_duplicates) == (1, 2, 3)
    assert cb.reaction == "rejected" and cb.reacted_at == NOW
    near_params = db.execute.await_args_list[4].args[1]
    assert near_params["threshold"] == 0.75
    assert [str(x) for x in near_params["chain_ids"]] == [
        "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"]
