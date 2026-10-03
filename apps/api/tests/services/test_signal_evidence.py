"""MEM2-B3 — the two evidence shapes, as pure functions.

`cited_memory_ids` decides which rows a 'no' retires and a 'yes' returns, so
reading the wrong shape retires the wrong rows. `signal_evidence` decides what a
signal card cites, so a belief must cite its own row and nothing beside it. The
end-to-end path through Postgres and the ring-true handler is in
tests/db_live/test_signal_evidence_echo_live.py.
"""
import uuid
from types import SimpleNamespace

from services.memory_service import cited_memory_ids, signal_evidence

A, B, C = (str(uuid.uuid4()) for _ in range(3))


def _row(entry_type, content, rid=None):
    return SimpleNamespace(id=rid or str(uuid.uuid4()), entry_type=entry_type, content=content)


# ── cited_memory_ids: the signal shape ───────────────────────────────────────

def test_a_signal_cites_its_memory_entry_ids():
    assert cited_memory_ids({"kind": "signal", "memory_entry_ids": [A, B]}) == [A, B]


def test_a_signal_without_memory_ids_cites_nothing():
    """A dilemma or aspiration: no row written, so nothing to retire."""
    assert cited_memory_ids({"kind": "signal", "source_message_ids": [A, B]}) == []


def test_a_signal_never_reads_the_recurrence_keys():
    """source_message_ids are MESSAGE ids. They must never be read as memory ids,
    nor may a stray recurrence key on a signal dict be."""
    ev = {"kind": "signal", "source_message_ids": [A],
          "recurring_entry": {"memory_entry_id": B}, "memory_entry_ids": [C]}
    assert cited_memory_ids(ev) == [C]


def test_signal_ids_are_validated_and_deduplicated():
    ev = {"kind": "signal", "memory_entry_ids": [A, "not-a-uuid", None, A, 7]}
    assert cited_memory_ids(ev) == [A]


def test_a_malformed_signal_list_cites_nothing():
    assert cited_memory_ids({"kind": "signal", "memory_entry_ids": A}) == []


# ── cited_memory_ids: the recurrence shape, with and without kind ────────────

def _recurrence(**extra):
    return {
        "recurring_entry": {"memory_entry_id": A},
        "prior_matches": [{"memory_entry_id": B}, {"memory_entry_id": C}],
        **extra,
    }


def test_new_recurrence_evidence_carries_kind_and_reads_as_before():
    assert cited_memory_ids(_recurrence(kind="recurrence")) == [A, B, C]


def test_legacy_evidence_without_kind_is_read_as_recurrence():
    assert cited_memory_ids(_recurrence()) == [A, B, C]


def test_an_unknown_kind_cites_nothing_rather_than_guessing():
    assert cited_memory_ids(_recurrence(kind="something_new")) == []


# ── signal_evidence: what a signal card records ──────────────────────────────

def test_a_belief_cites_only_its_own_row():
    """Founder ruling Q1, 2026-10-03: a 'no' on a belief must not retire the
    unrelated rows written beside it in the same call."""
    belief = _row("belief", "If I don't handle everything myself, it won't be done right.")
    rows = [
        _row("struggle", "User is weighing a hard decision about work."),
        belief,
        _row("value", "User places high importance on honesty."),
    ]
    ev = signal_evidence("belief", belief.content, rows, [A, B])
    assert ev == {"kind": "signal", "source_message_ids": [A, B],
                  "memory_entry_ids": [str(belief.id)]}


def test_a_row_of_another_type_with_the_same_text_is_not_cited():
    text = "If I don't handle everything myself, it won't be done right."
    ev = signal_evidence("belief", text, [_row("pattern", text)], None)
    assert ev["memory_entry_ids"] == []


def test_a_belief_with_no_matching_row_cites_nothing():
    ev = signal_evidence("belief", "a belief", [_row("belief", "another belief")], [A, B])
    assert ev["memory_entry_ids"] == []


def test_a_belief_with_no_rows_handed_over_cites_nothing():
    assert signal_evidence("belief", "a belief", None, None)["memory_entry_ids"] == []


def test_dilemma_and_aspiration_record_only_kind_and_messages():
    for t in ("dilemma", "aspiration"):
        ev = signal_evidence(t, "whether to go", [_row("belief", "whether to go")], [A, B])
        assert ev == {"kind": "signal", "source_message_ids": [A, B]}
        assert cited_memory_ids(ev) == []


def test_missing_message_ids_are_stored_as_null_not_guessed():
    """R9: a job queued before 070 carries no ids, and none are invented."""
    assert signal_evidence("dilemma", "x", [], None)["source_message_ids"] is None


def test_message_ids_are_stored_as_strings():
    """A driver-native uuid must not reach a JSONB write."""
    ev = signal_evidence("dilemma", "x", [], [uuid.UUID(A), B])
    assert ev["source_message_ids"] == [A, B]
