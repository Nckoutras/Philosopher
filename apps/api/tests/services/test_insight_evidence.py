"""The evidence a recurrence insight keeps (060), and the pin that stops it drifting.

WHAT THIS CLOSES. `detect_recurrence` found the memory rows that echoed what the
person had just raised, then discarded them: the whole match set became
`source_count = len({...}) + 1`, and the shift classifier's two-sided comparison
survived only as its verdict. The rows that justified the card were unrecoverable
the moment it was written — and the detector's SELECT never fetched their ids at
all, so it did not know what it was collapsing.

THE ASSERTION THAT MATTERS MOST is test_source_count_and_the_evidence_describe_the
_same_match_set. Either half alone is a fact about one field; together they are a
pin, and it is the pin that closes the defect class. A future change that
recomputes one without the other — a filter added to the count, a slice added to
the evidence — fails here rather than shipping a citation that does not match the
number printed beside it.

NULL IS NOT A FAILURE, and the tests scope accordingly. `evidence IS NULL` means
one of two things: written before 060, or not a recurrence insight at all (the
signal path has no match set by construction and is NULL forever). So an assertion
that evidence is populated is only ever valid on the recurrence path.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import memory_service as ms
from services.memory_service import RECURRENCE_MIN_PRIOR, RECURRENCE_SIM_THRESHOLD

USER_ID = "11111111-1111-1111-1111-111111111111"
CONV_ID = "22222222-2222-2222-2222-222222222222"

CLASSIFIED = json.dumps({
    "insight_type": "pattern",
    "content": "The question of whether to leave your job has come up again.",
})


def _match(mid, conv, score, text):
    """A row as the detector's SELECT returns it — id included, since 060.

    SimpleNamespace rather than MagicMock, deliberately (C-06): a field this code
    reads and the fixture forgets must raise, not arrive as a Mock that pydantic
    and JSONB would both accept.
    """
    return SimpleNamespace(id=mid, content=text, conversation_id=conv, score=score)


async def _run(matches, *, entry_conv=CONV_ID):
    """Drive detect_recurrence from detection onward against a fixed match set."""
    added = []

    entry = SimpleNamespace(
        id="e1", content="the row that triggered it", embedding=[0.1] * 8,
        conversation_id=entry_conv,
    )

    db = AsyncMock()
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.commit = AsyncMock()
    rows = MagicMock()
    rows.fetchall.return_value = matches
    db.execute = AsyncMock(return_value=rows)

    async def complete(**kw):
        return CLASSIFIED

    with patch.object(ms.memory_service, "_insight_gate_blocked", new=AsyncMock(return_value=None)), \
         patch("services.llm_client.llm_client.complete", new=complete):
        await ms.memory_service.detect_recurrence(
            db=db, user_id=USER_ID, conversation_id=CONV_ID, persona_id="p1",
            new_entries=[entry], language="English",
        )
    return added


# ── The evidence is kept at all ───────────────────────────────────────────────

async def test_a_recurrence_insight_carries_the_rows_it_was_derived_from():
    """REVERT-VERIFY LEG 1. Drop the persistence — or drop `id` from the SELECT —
    and this is the test that goes red."""
    added = await _run([
        _match("m1", "conv-a", 0.91, "an earlier row"),
        _match("m2", "conv-b", 0.83, "another earlier row"),
    ])

    assert len(added) == 1
    ev = added[0].evidence
    assert ev is not None, "a recurrence insight with no evidence is the defect 060 closed"
    assert len(ev["prior_matches"]) >= RECURRENCE_MIN_PRIOR
    for m in ev["prior_matches"]:
        assert m["memory_entry_id"], m


async def test_every_citation_carries_its_text_beside_its_id():
    """The reason there are no foreign keys. A memory row can be deactivated and
    057 lets its conversation be deleted, so a citation that resolved by id alone
    would stop rendering the thing it cites."""
    added = await _run([_match("m1", "conv-a", 0.91, "an earlier row")])

    ev = added[0].evidence
    assert ev["recurring_entry"]["text"] == "the row that triggered it"
    assert ev["recurring_entry"]["memory_entry_id"] == "e1"
    assert ev["prior_matches"][0]["text"] == "an earlier row"


# ── The pin ───────────────────────────────────────────────────────────────────

async def test_source_count_and_the_evidence_describe_the_same_match_set():
    """REVERT-VERIFY LEG 2, AND THE ONE THAT CLOSES THE DEFECT CLASS.

    source_count is "distinct prior conversations + 1". If the evidence is built
    from a different set than the count — a filter on one, a slice on the other —
    the card prints a number its own citations cannot support. Recomputing the
    count FROM the stored evidence is what makes that impossible to do quietly.
    """
    added = await _run([
        _match("m1", "conv-a", 0.91, "one"),
        _match("m2", "conv-a", 0.88, "two — same conversation as m1"),
        _match("m3", "conv-b", 0.80, "three"),
    ])

    insight = added[0]
    ev = insight.evidence

    from_evidence = len({m["conversation_id"] for m in ev["prior_matches"]}) + 1
    assert insight.source_count == from_evidence == 3, (
        f"source_count={insight.source_count} but the stored evidence describes "
        f"{from_evidence} distinct conversations"
    )


# ── What was stored, and what was merely shown ───────────────────────────────

async def test_all_matches_are_stored_not_only_the_five_the_classifier_saw():
    """Both facts matter: what the detector found, and what the verdict was
    actually based on. The prompt is built from prior_matches[:5]."""
    added = await _run([_match(f"m{i}", f"conv-{i}", 0.9, f"row {i}") for i in range(8)])

    ev = added[0].evidence
    assert len(ev["prior_matches"]) == 8
    assert ev["shown_to_classifier"] == 5


async def test_shown_to_classifier_never_overstates_a_short_set():
    added = await _run([_match("m1", "conv-a", 0.91, "only one")])

    assert added[0].evidence["shown_to_classifier"] == 1


# ── The bar is frozen with the citation ──────────────────────────────────────

async def test_the_detector_constants_are_recorded_at_write_time():
    """RECURRENCE_SIM_THRESHOLD is a ship-and-tune value. If it moves, a citation
    written under the old bar is uninterpretable without knowing which bar it
    cleared — so the bar travels with the evidence."""
    added = await _run([_match("m1", "conv-a", 0.91, "an earlier row")])

    det = added[0].evidence["detector"]
    assert det["threshold"] == RECURRENCE_SIM_THRESHOLD
    assert det["limit"] == 20


async def test_the_window_is_null_because_this_detector_is_lifetime():
    """Reserved for the period-filtered caller. NULL means lifetime, which is what
    this detector is and must stay: "you raised this in March and again today" is
    the observation worth having, and a window would destroy exactly that."""
    added = await _run([_match("m1", "conv-a", 0.91, "an earlier row")])

    assert added[0].evidence["detector"]["window"] is None


def test_the_recurrence_query_selects_the_id_and_a_mock_cannot_tell_you_that():
    """SOURCE-LEVEL, and the docstring is the point.

    The detector never fetched identities — its SELECT listed content,
    conversation_id and score. Adding `id` IS the change 060 rests on, and it is
    the one part of it a mocked test cannot verify: the fake session returns
    fixture rows whatever the SQL string says, so removing `id` from the query
    leaves every test above green. Verified by trying it.

    A live schema would catch it, and that is a db_live test — CI-only, by the
    decision recorded in TD-57. This source assertion is the local substitute,
    in the same shape as test_the_mirror_query_still_filters_to_the_person.
    """
    import inspect

    # Re-pointed when the mechanics were extracted: the query now lives in
    # find_recurrences, which detect_recurrence is one caller of. The assertion is
    # unchanged — only its subject moved.
    src = inspect.getsource(ms.find_recurrences)
    assert "SELECT id, content, conversation_id," in src, (
        "the recurrence query must fetch `id`: without it the evidence has no "
        "identities to cite, and no mocked test in this file can see the loss"
    )


# ── Nulls, and what they are not ─────────────────────────────────────────────

def test_the_column_is_nullable_because_null_means_two_things():
    """Written before 060, OR not a recurrence insight at all. The signal path has
    no match set by construction, so NULL is correct for it forever — which is why
    no test may assert "every insight has evidence"."""
    from models import Insight

    assert Insight.__table__.columns["evidence"].nullable is True


def test_the_signal_path_writes_no_evidence():
    """Source-level, because the signal write is inside extract_and_store's larger
    flow. It sets source_count=None and passes no evidence; if it ever starts
    passing one, the two NULL meanings collapse and the docstrings go stale."""
    import inspect

    src = inspect.getsource(ms.MemoryService.extract_and_store)
    assert "source_count=None," in src
    assert "evidence=" not in src


async def test_the_export_carries_both_fields():
    """The export builds an explicit dict, so a new column reaches an Art. 15
    request only if someone adds it. source_count had been missing since the
    export shipped; the completeness guard could not see it because it is
    table-level, not column-level (TD-74)."""
    import inspect

    from services import data_export_service

    src = inspect.getsource(data_export_service.build_export)
    insights_block = src[src.index("insights = ["):src.index("# ── Letters")]
    assert '"evidence": i.evidence' in insights_block
    assert '"source_count": i.source_count' in insights_block
