"""MEM2-C-1: the callback sample set is what its docstring says it is.

NO API CALLS.
"""
from collections import Counter

import pytest

from evals.callback_samples import (
    AGE_CYCLE,
    INELIGIBLE_KINDS,
    KIND_CANDIDATE,
    KIND_ELICITED,
    LANGUAGE_NAME,
    LANGUAGES,
    SCENARIOS,
    build_samples,
    load_threads,
    sample_set_hash,
)
from personas import PERSONA_REGISTRY
from text_utils import dominant_language

SAMPLES = build_samples()
BY_ID = {s.sample_id: s for s in SAMPLES}


def test_size_and_shape():
    assert len(SAMPLES) == len(PERSONA_REGISTRY) * len(LANGUAGES) * len(SCENARIOS) == 132
    assert Counter(s.scenario for s in SAMPLES) == {s: 22 for s in SCENARIOS}
    assert len(BY_ID) == len(SAMPLES)


def test_row_ids_are_unique_within_a_sample():
    for s in SAMPLES:
        ids = [r.id for r in s.rows]
        assert len(ids) == len(set(ids)), s.sample_id


def test_the_gate_offers_the_candidate_everywhere_except_L1():
    for s in SAMPLES:
        c = s.candidate()
        if s.scenario == "L1":
            assert c is None, "L1 must not re-offer inside the same conversation"
        else:
            assert c is not None and c.kind == KIND_CANDIDATE, s.sample_id


def test_every_bait_row_is_ineligible_by_a_named_rule():
    from evals.callback_gate import why_ineligible
    for s in SAMPLES:
        for r in s.rows:
            if r.kind in INELIGIBLE_KINDS:
                assert why_ineligible(r, responder_slug=s.persona_slug,
                                      current_conversation_id=s.conversation_id), \
                    (s.sample_id, r.kind)


def test_B_carries_all_four_bait_kinds_and_R_carries_none_of_the_topical_ones():
    for s in SAMPLES:
        kinds = {r.kind for r in s.rows}
        if s.scenario == "B":
            assert {"other_persona", "flagged", "onboarding_profile"} <= kinds
        if s.scenario == "R":
            assert not ({"other_persona", "flagged", "onboarding_profile"} & kinds)


def test_L2_differs_from_R2_only_by_the_elicited_row():
    for slug in PERSONA_REGISTRY:
        for lang in LANGUAGES:
            r2, l2 = BY_ID[f"R2::{slug}::{lang}"], BY_ID[f"L2::{slug}::{lang}"]
            assert r2.user_message == l2.user_message
            extra = [r for r in l2.rows if r.id not in {x.id for x in r2.rows}]
            assert [r.kind for r in extra] == [KIND_ELICITED]
            assert extra[0].elicited_by_callback


def test_L1_continues_R_in_the_same_conversation():
    for slug in PERSONA_REGISTRY:
        for lang in LANGUAGES:
            r, l1 = BY_ID[f"R::{slug}::{lang}"], BY_ID[f"L1::{slug}::{lang}"]
            assert l1.conversation_id == r.conversation_id
            assert l1.history[0] == {"role": "user", "content": r.user_message}
            assert l1.history[1]["role"] == "assistant"
            assert "{when}" not in l1.history[1]["content"]


def test_candidate_is_from_another_conversation_with_this_persona():
    for s in SAMPLES:
        c = s.candidate_row()
        assert c.persona_slug == s.persona_slug
        assert c.conversation_id != s.conversation_id
        assert c.source_message_ids and c.original


@pytest.mark.parametrize("lang", LANGUAGES)
def test_messages_are_in_the_sample_language(lang):
    for s in SAMPLES:
        if s.language != lang:
            continue
        assert dominant_language([s.user_message]) == LANGUAGE_NAME[lang], s.sample_id
        assert dominant_language([s.candidate_row().original]) == LANGUAGE_NAME[lang]


def test_every_thread_has_every_field_in_both_languages():
    data = load_threads()
    keys = set(data["threads"][0]["en"])
    for t in data["threads"]:
        for lang in LANGUAGES:
            assert set(t[lang]) == keys, (t["id"], lang)
            assert all(v.strip() for v in t[lang].values()), (t["id"], lang)
    assert set(data["when_el"]) == {
        "a few days ago", "last week", "a few weeks ago",
        "a couple of months ago", "some months ago"}


def test_every_age_bucket_is_exercised():
    from evals.callback_directive import when_bucket
    assert {when_bucket(d) for d in AGE_CYCLE} == {
        "a few days ago", "last week", "a few weeks ago",
        "a couple of months ago", "some months ago"}


def test_hash_is_stable():
    assert sample_set_hash() == sample_set_hash()
