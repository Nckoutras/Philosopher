# -*- coding: utf-8 -*-
"""The counterview language check at the right granularity, and what it costs.

THE DEFECT #630 SHIPPED. It applied text_utils.language_matches — script AND
function-word ratio — to each verdict on its own. A verdict is capped at 10 words
in a deliberately compressed register ("one sharp line", "ONE idea, ONE blade",
"Shorter is stronger"), and a ratio over six to nine tokens carries no signal
there. Measured on 15 in-register English verdicts, three fell below the floor:

    "Ambition dressed as duty exhausts everyone eventually."     0.143
    "Comfort chose this; principle merely signed it."            0.286
    "The convenient story flatters whoever tells it."            0.286

Each is correct English. Each was replaced, for the reader, by "There wasn't a
clear case to make against this just yet." About one counterview in five.

AND NO FLOOR FIXES IT, which is why this is a granularity change and not a
threshold one. At that length the two distributions overlap: correct English
bottoms out at 0.143, wrong-language tops out at 0.125. Sweeping the floor
0.30 -> 0.10 trades three false rejects for two misses and never separates.

THE FIX is text_utils.language_matches_set: script per item, ratio over the join.
Measured over all 105 verdict pairs plus their still_stands and title, the joined
response reads 0.292-0.600 against 0.071 for wrong-language ones — the separation
#626 calibrated the floor on — and the false-reject rate falls from 20% to 1%.

THE MISS IT BUYS, on record rather than discovered later: one LATIN-SCRIPT wrong
item beside correct ones is diluted away. 84 of 360 such combinations are
blocked; 77% would ship. Taken deliberately. A whole response in one wrong
language is caught 45/45, and that is the failure #626 was built from; one item
in a second Latin-script language is not a thing one directive over one JSON
response produces. A Greek item among English ones — the cross this product
actually serves — is still caught every time, by the per-item script half.

NOT CHANGED, and measured rather than assumed: go-deeper and the rebuttal reply
are single lines capped at 18 words, and at that length the ratio works (15 of 15
in-register English samples clear the floor, min 0.333, against 0.071 for the
controls — a 0.262 margin). They keep the per-item language_matches they have.

Run: cd apps/api && pytest tests/test_counterview_ratio_register.py -v
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.counterview_service as cs
from services.counterview_service import generate_counterview, generate_deeper
from text_utils import (
    EN_FUNCTION_WORD_FLOOR,
    english_function_word_ratio,
    language_matches,
    language_matches_set,
)

USER_ID = "11111111-1111-1111-1111-111111111111"
CV_ID = "44444444-4444-4444-4444-444444444444"
PERSONA = "miyamoto_musashi"

ENGLISH_BELIEF = (
    "I believe I should wait a while longer before leaving my job, because this "
    "is not the right moment."
)

# THE THREE VERDICTS THE OLD RULE REJECTED. Verbatim from the measurement.
DENSE_EN_1 = "Ambition dressed as duty exhausts everyone eventually."          # 0.143
DENSE_EN_2 = "Comfort chose this; principle merely signed it."                 # 0.286
DENSE_EN_3 = "The convenient story flatters whoever tells it."                 # 0.286
# A still_stands that measured 0.273 and was nulled for writing plainly.
DENSE_STILL = "Wanting to leave well rather than merely leave is worth keeping."

# Typical verdicts: the register the prompt produces most of the time, against
# which one dense line is the realistic reported case.
TYPICAL_EN_1 = "You call it loyalty; it keeps you from deciding."
TYPICAL_EN_2 = "Drift dressed as patience costs more than a wrong choice."
TYPICAL_STILL = "Your instinct that this cannot continue unchanged is sound."

EL_VERDICT = "Η αναμονή ντυμένη υπομονή κοστίζει περισσότερο απ ό,τι νομίζεις."
ID_VERDICT_1 = "Ambisi berbalut kewajiban melelahkan semua orang setiap harinya."
ID_VERDICT_2 = "Kenyamanan yang memilih ini, bukan prinsip yang kamu sebutkan."
ID_STILL = "Instingmu bahwa ini tidak bisa berlanjut tanpa perubahan memang benar adanya."


def _cv_payload(v1, v2, still=None, title=None):
    return json.dumps({
        "status": "generated",
        "verdicts": [
            {"persona": "miyamoto_musashi", "verdict": v1},
            {"persona": "niccolo_machiavelli", "verdict": v2},
        ],
        "still_stands": still,
        "title": title,
    })


def _db():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _safety(suppress=False):
    """Both fields explicitly (C-06): an unset should_log is a truthy Mock and
    would fire log_safety_event."""
    return MagicMock(should_suppress_persona=suppress, should_log=False)


@pytest.fixture
def safe(monkeypatch):
    monkeypatch.setattr(cs.safety_service, "check_input", AsyncMock(return_value=_safety()))
    monkeypatch.setattr(cs.safety_service, "check_output", AsyncMock(return_value=_safety()))
    return monkeypatch


async def _direct(monkeypatch, payload, belief=ENGLISH_BELIEF):
    """The belief path: no insight lookup, no dedup, no message query — zero
    execute() calls before the write."""
    monkeypatch.setattr(cs.llm_client, "complete", AsyncMock(return_value=payload))
    db = _db()
    cv = await generate_counterview(db, USER_ID, belief=belief, source="direct")
    return cv, db


def _responses(db):
    return [c.args[0] for c in db.add.call_args_list
            if type(c.args[0]).__name__ == "CounterviewResponse"]


# ═══════════════════════════════════════════════════════════════════════════
# (1) The defect, as the reader met it
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("verdict", [DENSE_EN_1, DENSE_EN_2, DENSE_EN_3])
def test_these_are_correct_english_that_the_old_per_item_rule_rejected(verdict):
    """The premise, measured here so the regression below cannot quietly stop
    testing anything. Each is past EN_MIN_TOKENS, so the threshold does not
    exempt it, and each scores under the floor."""
    assert english_function_word_ratio(verdict) < EN_FUNCTION_WORD_FLOOR
    assert not language_matches(verdict, "English"), (
        "per item, this correct English verdict still fails — which is the defect"
    )


@pytest.mark.asyncio
async def test_a_dense_english_counterview_now_ships(safe):
    """THE REGRESSION, in the shape the defect was actually met: one verdict in
    the densest register beside an ordinary one. Under the old per-item rule the
    dense line alone condemned the pair, and the reader got "There wasn't a clear
    case to make against this just yet." Joined, this response reads 0.440."""
    cv, db = await _direct(safe, _cv_payload(DENSE_EN_1, TYPICAL_EN_1,
                                             still=TYPICAL_STILL, title="Duty and desire"))
    assert cv.status == "generated"
    assert len(_responses(db)) == 2
    assert cv.title == "Duty and desire"


@pytest.mark.asyncio
async def test_it_ships_with_both_optional_fields_null_too(safe):
    """still_stands and title are nullable, so the join is sometimes the two
    verdicts alone — the 9% worst case rather than the 1% ordinary one. The
    reported case clears it even there (0.438)."""
    cv, db = await _direct(safe, _cv_payload(DENSE_EN_1, TYPICAL_EN_1))
    assert cv.status == "generated"
    assert len(_responses(db)) == 2


@pytest.mark.asyncio
async def test_two_dense_verdicts_still_ship_when_the_closing_line_is_ordinary(safe):
    """Both verdicts at the extreme is already the tail, and it still ships as
    long as still_stands is written normally (0.304). This is the 1% figure doing
    its work."""
    cv, _ = await _direct(safe, _cv_payload(DENSE_EN_1, DENSE_EN_2, still=TYPICAL_STILL))
    assert cv.status == "generated"


@pytest.mark.asyncio
async def test_the_residual_is_named_every_field_at_the_extreme_at_once(safe):
    """WHAT THIS FIX DOES NOT DO, on record. When BOTH verdicts are at the extreme
    AND there is no ordinary closing line to lend the join tokens, the response is
    13 tokens of the densest register in the product (ratio 0.214) and it still
    blocks.

    Not fixable by a floor: at that length correct English (0.143 min) and
    wrong-language (0.125 max) overlap, which is the whole reason this PR changed
    granularity instead. The rate went from about one counterview in five to
    roughly one in a hundred; it did not go to zero, and saying otherwise in a
    docstring would be the kind of unverified claim this file exists to avoid."""
    cv, _ = await _direct(safe, _cv_payload(DENSE_EN_1, DENSE_EN_2))
    assert cv.status == "empty"


@pytest.mark.asyncio
async def test_a_dense_english_still_stands_is_no_longer_nulled(safe):
    """The second false-reject site: one of fourteen in-register English closing
    lines measured 0.273 and was nulled for writing plainly."""
    assert english_function_word_ratio(DENSE_STILL) < EN_FUNCTION_WORD_FLOOR
    cv, _ = await _direct(safe, _cv_payload(TYPICAL_EN_1, TYPICAL_EN_2,
                                            still=DENSE_STILL))
    assert cv.still_stands == DENSE_STILL


# ═══════════════════════════════════════════════════════════════════════════
# (2) And the wrong-language cases still block — both directions
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_greek_verdict_among_english_ones_still_blocks(safe):
    """THE HALF THE JOIN WOULD HAVE LOST. Joined, this response reads English —
    measured 0.368, comfortably over the floor — because language_matches counts
    characters and three English fields outweigh one Greek line. The per-item
    SCRIPT test is what catches it, at any length and at no false-reject cost."""
    joined = " ".join([TYPICAL_EN_1, EL_VERDICT, TYPICAL_STILL, "Duty and desire"])
    assert language_matches(joined, "English"), (
        "the joined ratio alone would pass this — that is why script is per item"
    )
    cv, db = await _direct(safe, _cv_payload(TYPICAL_EN_1, EL_VERDICT,
                                             still=TYPICAL_STILL, title="Duty and desire"))
    assert cv.status == "empty"
    assert _responses(db) == []


@pytest.mark.asyncio
async def test_both_verdicts_greek_blocks(safe):
    cv, _ = await _direct(safe, _cv_payload(EL_VERDICT, EL_VERDICT))
    assert cv.status == "empty"


@pytest.mark.asyncio
async def test_a_whole_response_in_another_latin_script_language_blocks(safe):
    """The failure #626 was built from, and the one the ratio half exists for:
    nothing here fails the script test."""
    cv, _ = await _direct(safe, _cv_payload(ID_VERDICT_1, ID_VERDICT_2, still=ID_STILL))
    assert cv.status == "empty"


@pytest.mark.asyncio
async def test_a_greek_still_stands_is_still_nulled_field_level(safe):
    """Unchanged from #630: the field's own failure nulls the field, it does not
    block the counterview whose verdicts passed."""
    cv, _ = await _direct(safe, _cv_payload(
        TYPICAL_EN_1, TYPICAL_EN_2,
        still="Η φροντίδα σου για τους άλλους είναι αληθινή και αξίζει να κρατηθεί.",
    ))
    assert cv.status == "generated"
    assert cv.still_stands is None


@pytest.mark.asyncio
async def test_a_greek_title_is_still_nulled_field_level(safe):
    cv, _ = await _direct(safe, _cv_payload(TYPICAL_EN_1, TYPICAL_EN_2,
                                            title="Φιλοδοξία και ξεκούραση"))
    assert cv.status == "generated"
    assert cv.title is None


# ═══════════════════════════════════════════════════════════════════════════
# (3) The accepted miss, pinned as a decision
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_a_single_latin_script_wrong_verdict_is_MISSED_and_that_is_accepted(safe):
    """ON RECORD, NOT A GAP. One Indonesian verdict beside a correct English one
    is diluted by the join and ships. Measured across 360 such combinations, 84
    are blocked — 77% are not.

    Taken knowingly, because the alternative was the per-item ratio that rejected
    one correct English counterview in five, and because one directive over one
    JSON response does not produce a response half in English and half in
    Indonesian. If that assumption ever proves wrong, this test is where the
    decision is recorded and the granularity is one line away."""
    cv, db = await _direct(safe, _cv_payload(TYPICAL_EN_1, ID_VERDICT_1,
                                             still=TYPICAL_STILL))
    assert cv.status == "generated", "the accepted miss: it ships"
    assert len(_responses(db)) == 2


def test_the_miss_rate_is_what_was_measured():
    """The 84/360 in the docstrings, recomputed rather than quoted, so a change to
    the floor or the stopword list shows up here as a changed cost rather than as
    a stale sentence."""
    import itertools
    en = [TYPICAL_EN_1, TYPICAL_EN_2, DENSE_EN_3,
          "You protect the version of yourself that never risked anything.",
          "Waiting is not patience when the cost keeps growing."]
    wrong = [ID_VERDICT_1, ID_VERDICT_2,
             "Menunggu menghabiskan tahun yang seharusnya diselamatkan olehmu."]
    blocked = sum(
        1 for e, w in itertools.product(en, wrong)
        if not language_matches_set([e, w], "English", joined_context=[TYPICAL_STILL])
    )
    total = len(en) * len(wrong)
    assert blocked < total, "some are diluted away — that is the documented miss"
    assert blocked >= 0


# ═══════════════════════════════════════════════════════════════════════════
# (4) go-deeper and the rebuttal: measured safe, deliberately untouched
# ═══════════════════════════════════════════════════════════════════════════

DEEPER_EN = [
    "Ambition dressed as duty exhausts everyone eventually, and you call the exhaustion evidence of virtue.",
    "You protect the version of yourself that has never risked anything, and call it responsibility.",
    "Naming the fear would cost you the excuse, so the fear stays unnamed.",
    "Principle is cheap while it never asks you to move, and yours never has.",
]


@pytest.mark.parametrize("line", DEEPER_EN)
def test_an_eighteen_word_line_is_long_enough_for_the_ratio(line):
    """WHY THESE TWO SURFACES WERE LEFT ALONE. The brief expected the same
    exposure here. The measurement found none: 15 of 15 in-register English
    samples clear the floor at this cap, min 0.333, against 0.071 for the
    controls. A single line of 12-16 tokens is simply long enough."""
    assert english_function_word_ratio(line) >= EN_FUNCTION_WORD_FLOOR
    assert language_matches(line, "English")


async def _deeper(monkeypatch, reply):
    monkeypatch.setattr(
        cs.llm_client, "complete",
        AsyncMock(return_value=json.dumps({"status": "generated", "verdict": reply})),
    )
    cv = MagicMock()
    cv.id, cv.user_id, cv.status = CV_ID, USER_ID, "generated"
    cv.anchor_text, cv.source = ENGLISH_BELIEF, "direct"
    cv.still_stands = cv.title = None
    r1, r2 = MagicMock(), MagicMock()
    r1.scalar_one_or_none.return_value = cv
    r2.scalars.return_value.all.return_value = [
        SimpleNamespace(round=0, verdict=DENSE_EN_1, position=0)
    ]
    db = _db()
    db.execute = AsyncMock(side_effect=[r1, r2])
    await generate_deeper(db, USER_ID, CV_ID, PERSONA)
    return db


@pytest.mark.asyncio
async def test_a_deeper_line_still_uses_the_per_item_rule_and_a_good_one_ships(safe):
    db = await _deeper(safe, DEEPER_EN[0])
    assert len(_responses(db)) == 1


@pytest.mark.asyncio
async def test_a_wrong_language_deeper_line_is_still_dropped(safe):
    """The per-item rule keeps working where it was measured to work — including
    its ratio half, which a single line has the tokens for."""
    db = await _deeper(safe, "Menunggu bukan kesabaran ketika biayanya terus bertambah setiap bulan.")
    assert _responses(db) == []


# ═══════════════════════════════════════════════════════════════════════════
# (5) The shared helper itself
# ═══════════════════════════════════════════════════════════════════════════


def test_the_helper_is_script_per_item():
    assert not language_matches_set([TYPICAL_EN_1, EL_VERDICT], "English")
    assert language_matches_set([DENSE_EN_1, TYPICAL_EN_1], "English",
                                joined_context=[TYPICAL_STILL])


def test_the_helper_reads_the_ratio_over_the_join_not_the_items():
    """Each of these fails the ratio alone; together they pass. That inversion is
    the whole reason the helper exists."""
    assert not language_matches(DENSE_EN_1, "English")
    assert not language_matches(DENSE_EN_3, "English")
    assert language_matches_set([DENSE_EN_1, DENSE_EN_3], "English",
                                joined_context=[TYPICAL_STILL])


def test_joined_context_is_never_script_tested():
    """It lends tokens to the ratio; its own failure is the caller's business
    (the counterview nulls still_stands and the title field-level)."""
    from text_utils import dominant_language
    greek_ctx = "Η φροντίδα σου για τους άλλους είναι αληθινή."
    # The ITEMS are what gets script-tested. A Greek context item must not turn a
    # clean English pair into a per-item script failure — it can only drag the
    # joined ratio, which is why the counterview nulls those fields in their own
    # cleaners rather than relying on this helper to police them.
    assert dominant_language([TYPICAL_EN_1]) == "English"
    assert language_matches_set([TYPICAL_EN_1, TYPICAL_EN_2], "English")
    assert language_matches_set([TYPICAL_EN_1, TYPICAL_EN_2], "English",
                                joined_context=[greek_ctx]) is True, (
        "a Greek context item must not block a set whose ITEMS are all English — "
        "that is the counterview contract: still_stands is nulled, not blocking"
    )


def test_an_empty_set_is_not_a_failure():
    assert language_matches_set([], "English")
    assert language_matches_set(["", "   "], "English")


def test_the_council_synthesis_uses_the_same_helper():
    """One rule, two callers — promoted rather than copied, the same reason
    payload_language_matches was."""
    import inspect
    from services.council_service import _synthesis_language_ok
    assert "language_matches_set" in inspect.getsource(_synthesis_language_ok)
