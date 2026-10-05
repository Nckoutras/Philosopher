"""MEM2-C-3a — the callback use detector (services/callback_use.py).

TWO THINGS ARE PINNED:

  1. THE MEASUREMENT. The detector is run over every offered Pro completion of the two
     stored runs it was chosen on, and compared with the C-1 judge's call-1 verdict
     "called back item A". The four cells of each confusion table are asserted
     exactly, so a change to any signal, threshold or normalisation shows up here as a
     moved count, not as a silent drift. Production-shaped sets only: Pro (Sonnet,
     C1-e), English from C-1, Greek from the STEP 0(b) run under the Greek directive
     that production ships.

  2. EACH SIGNAL. One test per signal, including the «…» quote owed to C-3 by the
     C-2 STEP 0 ruling, and the Greek final-sigma fold that broke the first prototype.

mark_use's query is mocked here. The SQL itself — the original-message join, the
"user message this reply answered" subquery, the used-IS-NULL guard — is executed in
tests/db_live/test_memory_callbacks_live.py § 5.
"""
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals.callback_samples import build_samples
from services import callback_use as cu
from services.callback_service import when_bucket

RESULTS = Path(cu.__file__).resolve().parent.parent / "evals" / "results"


# ── 1. The measurement ───────────────────────────────────────────────────────

# The runs' completions.jsonl are gitignored (generated, large), so the offered Pro
# rows the measurement needs are frozen here; the judge verdicts are read from the
# tracked callback_judge.csv.
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "callback_use_measurement.json"


def _confusion(run: str, language: str) -> Counter:
    judge = {}
    with open(RESULTS / run / "callback_judge.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # A parse failure is excluded, never counted as "no" (the C-1 rule).
            if r["call"] == "1" and not r["raw_error"].strip():
                judge[r["key"]] = r["cb_v"] == "1" and "A" in (r["items"] or "").split()
    samples = {s.sample_id: s for s in build_samples()}
    stored = json.loads(FIXTURE.read_text(encoding="utf-8"))["runs"][run]
    assert stored["language"] == language
    out: Counter = Counter()
    for c in stored["rows"]:
        assert c["key"] in judge, f"fixture row with no call-1 verdict: {c['key']}"
        original = samples[c["sample_id"]].candidate_row().original
        days = c["candidate_days"]
        signals = cu.detect(c["reply"], original, c["user_message"],
                            [when_bucket(days, "en"), when_bucket(days, "el")])
        out[(judge[c["key"]], signals.used)] += 1
    return out


def test_english_pro_against_the_c1_judge():
    got = _confusion("2026-10-05_mem2c1", "en")
    # (judge says used, detector says used): 36 caught, 1 missed, 0 false, 18 agreed-unused
    assert got == Counter({(True, True): 36, (True, False): 1, (False, False): 18})


def test_greek_pro_under_the_greek_directive_against_the_judge():
    got = _confusion("2026-10-05_mem2c2_el", "el")
    # 54 judged (one call-1 parse failure excluded): 20 caught, 1 missed, 32 agreed,
    # and 1 flagged that the judge did not mark — an unannounced echo of the
    # original's words («Αυτή η λίστα που μεγαλώνει κάθε φορά που την κοιτάς…»),
    # caught by the shared run alone.
    assert got == Counter({(True, True): 20, (True, False): 1,
                           (False, True): 1, (False, False): 32})


# ── 2. Each signal ───────────────────────────────────────────────────────────

ORIGINAL_EN = ("Every Sunday I drive three hours to see my father in the care home, "
               "and every Sunday I count the minutes until I can leave.")
ORIGINAL_EL = ("Κάθε Κυριακή οδηγώ τρεις ώρες για να δω τον πατέρα μου στο γηροκομείο, "
               "και κάθε Κυριακή μετράω τα λεπτά μέχρι να μπορέσω να φύγω.")
NO_WHEN: list[str] = []


def test_normalize_strips_tonos_folds_case_and_final_sigma():
    assert cu.normalize("Έγραψες «ΚΆΤΙ»!") == "εγραψεσ κατι"


@pytest.mark.parametrize("o,c", [('"', '"'), ("“", "”"), ("«", "»"),
                                 ("„", "“")])
def test_a_quoted_span_from_the_original_is_a_use_in_every_quote_style(o, c):
    reply = f"There it is: {o}count the minutes until I can leave{c}. Stay with that."
    s = cu.detect(reply, ORIGINAL_EN, "", NO_WHEN)
    assert s.quote and s.used


def test_guillemets_in_greek():
    reply = "Το είπες κάποτε: «μετράω τα λεπτά μέχρι να μπορέσω να φύγω». Μείνε εκεί."
    assert cu.detect(reply, ORIGINAL_EL, "", NO_WHEN).quote


def test_a_short_or_foreign_quote_is_not_a_quote_use():
    assert not cu.detect('You call it "my father" here.', ORIGINAL_EN, "", NO_WHEN).quote
    assert not cu.detect('"Nothing like the original at all."', ORIGINAL_EN, "", NO_WHEN).quote


def test_the_when_phrase_framed_as_something_said_is_a_use():
    reply = "A few weeks ago you said the drive back was the hardest part."
    s = cu.detect(reply, "unrelated words", "", ["a few weeks ago"])
    assert s.when and s.used


def test_the_greek_when_phrase_with_a_greek_verb_is_a_use():
    reply = "Πριν από αρκετούς μήνες έγραψες ότι κάτι άλλο έπρεπε πρώτα να γίνει."
    assert cu.detect(reply, "άσχετα λόγια", "", ["πριν από αρκετούς μήνες"]).when


def test_a_when_phrase_with_no_said_verb_is_not_a_use():
    reply = "Last week the weather turned and the light changed."
    assert not cu.detect(reply, "unrelated words", "", ["last week"]).when


def test_a_shared_run_is_a_use_unless_the_person_just_said_it_again():
    original = "I count the minutes until I can leave."
    # Three shared words in a row is not a run.
    assert not cu.detect("You count the minutes, then leave.", original, "", NO_WHEN).shared_run
    reply = "And yet you count the minutes until you can leave, every time."
    assert cu.detect(reply, original, "", NO_WHEN).shared_run
    assert not cu.detect(reply, original, "I count the minutes until I can leave again.",
                         NO_WHEN).shared_run


def test_when_phrases_for_uses_the_rows_age_at_offer_in_both_languages():
    offered = datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert cu.when_phrases_for(offered - timedelta(days=20), offered) == [
        "a few weeks ago", "πριν από μερικές εβδομάδες"]


# ── mark_use (mocked session) ────────────────────────────────────────────────

OFFERED = datetime(2026, 10, 5, tzinfo=timezone.utc)


def _row(**kw):
    base = dict(id="cb-1", used=None, offered_at=OFFERED,
                row_created_at=OFFERED - timedelta(days=20),
                reply='A few weeks ago you said you "count the minutes until I can leave".',
                original=ORIGINAL_EN, user_text="Today was the same.")
    base.update(kw)
    return SimpleNamespace(**base)


def _db(row):
    db = MagicMock()
    result = MagicMock()
    result.one_or_none.return_value = row
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_mark_use_writes_used_true_once_and_only_where_null():
    db = _db(_row())
    signals = await cu.mark_use(db, "msg-1")
    assert signals.used and signals.quote and signals.when
    sql, params = db.execute.await_args_list[1].args
    assert "used IS NULL" in str(sql)
    assert params == {"used": True, "id": "cb-1"}


@pytest.mark.asyncio
async def test_mark_use_writes_used_false_for_an_unused_offer():
    db = _db(_row(reply="Tell me more about today."))
    signals = await cu.mark_use(db, "msg-1")
    assert signals.used is False
    assert db.execute.await_args_list[1].args[1] == {"used": False, "id": "cb-1"}


@pytest.mark.asyncio
@pytest.mark.parametrize("row", [None, _row(used=True), _row(used=False), _row(original=None)])
async def test_mark_use_writes_nothing_without_an_unmarked_offer_and_its_original(row):
    db = _db(row)
    assert await cu.mark_use(db, "msg-1") is None
    assert db.execute.await_count == 1
