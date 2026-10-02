"""MEM2-A R3 — which memory rows a recurrence insight's evidence cites.

`cited_memory_ids` is pure, so its edges live here and need no database: the live
half (the UPDATE, its scoping and its transaction) is in
tests/db_live/test_memory_epistemic_core.py.

The edge that matters most is the malformed one. The caller is a person saying
"that is not true of me"; a citation Postgres cannot cast to uuid would fail the
whole UPDATE, and with it the verdict. So anything malformed yields nothing.

Run: cd apps/api && pytest tests/services/test_memory_rejection.py -v
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import AsyncMock

import pytest

from services.memory_service import cited_memory_ids, reject_cited_memories

A = "aaaaaaaa-0000-0000-0000-000000000001"
B = "bbbbbbbb-0000-0000-0000-000000000002"
C = "cccccccc-0000-0000-0000-000000000003"


def _evidence(recurring, *priors):
    return {
        "recurring_entry": {"memory_entry_id": recurring, "text": "now"},
        "prior_matches": [{"memory_entry_id": p, "text": "before", "score": 0.8} for p in priors],
    }


def test_the_recurring_entry_and_every_prior_match_are_cited_in_order():
    assert cited_memory_ids(_evidence(A, B, C)) == [A, B, C]


@pytest.mark.parametrize("evidence", [None, {}, [], "evidence", 42, {"prior_matches": None}])
def test_absent_or_foreign_evidence_cites_nothing(evidence):
    assert cited_memory_ids(evidence) == []


def test_malformed_ids_are_dropped_not_raised():
    ev = _evidence("not-a-uuid", None, 17, B)
    ev["prior_matches"].append("a bare string, not a dict")
    assert cited_memory_ids(ev) == [B]


def test_a_row_cited_twice_is_returned_once():
    assert cited_memory_ids(_evidence(A, A, B)) == [A, B]


def test_ids_are_normalised_to_canonical_form():
    assert cited_memory_ids(_evidence(A.upper())) == [A]


@pytest.mark.asyncio
async def test_no_citations_means_no_query_at_all():
    """The no-op is real: a signal insight's 'no' never reaches the database."""
    db = AsyncMock()
    assert await reject_cited_memories(db, A, None) == 0
    db.execute.assert_not_called()
