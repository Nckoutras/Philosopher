"""Portrait cache invalidation: the answer-set fingerprint, not a count delta.

WHAT WAS WRONG. Both cache gates in GET /preferences/self-portrait/portrait asked
"have PORTRAIT_REGEN_DELTA new answers arrived", computed as
`len(answers) - answer_count_watermark`. Re-answering an existing question rewrites
a value under a key that is already present, so `len(answers)` does not move and the
delta stays put. A user who revised every answer they had given saw the same summary
and the same forming lines forever — the prose half of the "self-portrait never
changes" report (MEMORY_V2_INVESTIGATION_2026-09-03 §2a, defect 2).

NOTE ON PRE-EXISTING COVERAGE. There was none. Before this file, a grep of tests/
for portrait_cache, generate_portrait, answer_count_watermark, in_failure_cooldown
or mark_failed returned nothing, so the failure-cooldown behaviour this change must
leave alone had no test pinning it either. The cooldown cases at the bottom are
therefore written here rather than inherited.

C-06: the preferences row is a plain FakePrefs, not a MagicMock. `portrait_cache` is
written by the endpoint and read back by the assertions, and a MagicMock would accept
any attribute write and still answer every read — making "was the cache updated?"
unassertable, which is most of what this file checks.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.self_portrait import free_question_ids
from services.self_portrait_summary import answers_fingerprint

PORTRAIT_URL = "/api/v1/preferences/self-portrait/portrait"
USER_ID = "11111111-1111-1111-1111-111111111111"

# A "ready" answer set: enough distinct categories to clear READY_CATEGORY_THRESHOLD.
# Built from the real bank so the state gate is exercised, not stubbed.
READY_ANSWERS = {qid: 0 for qid in sorted(free_question_ids())}
SUMMARY_TEXT = "You answer as someone who checks the ground before stepping."


def _generated(answers, text=SUMMARY_TEXT):
    """The exact dict generate_portrait returns, for a given answer set."""
    return {
        "text": text,
        "best_fit": [],
        "answers_fingerprint": answers_fingerprint(answers),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class FakePrefs:
    """A user_preferences row. Plain object — see the C-06 note above."""

    def __init__(self, answers, portrait_cache=None, need_most="clarity"):
        self.profile = {"answers": dict(answers)}
        self.portrait_cache = portrait_cache
        self.need_most = need_most
        self.themes = []
        self.other_text = None


class FakeDb:
    def __init__(self):
        self.committed = 0

    async def commit(self):
        self.committed += 1


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    user = MagicMock()
    user.id = USER_ID

    async def override_db():
        yield FakeDb()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _open_portrait(client, prefs, *, generated=None, preview=None):
    """GET the portrait with both LLM paths stubbed. Returns
    (response, generate_portrait mock, forming_reflection mock)."""
    gen = AsyncMock(return_value=generated)
    forming = AsyncMock(return_value=list(preview or []))
    with (
        patch("routers.preferences.get_user_preferences", new=AsyncMock(return_value=prefs)),
        patch("routers.preferences.self_portrait_summary.generate_portrait", new=gen),
        patch(
            "routers.preferences.self_comparison_service.forming_reflection",
            new=forming,
        ),
    ):
        resp = client.get(PORTRAIT_URL)
    return resp, gen, forming


# ── (a) The fingerprint itself ───────────────────────────────────────────────

def test_insertion_order_does_not_change_the_fingerprint():
    """Sorted by question id, so two dicts differing only in build order agree."""
    forward = {"a_001": 1, "b_002": 2, "c_003": 0}
    backward = {"c_003": 0, "b_002": 2, "a_001": 1}
    assert list(forward) != list(backward)  # key order genuinely differs
    assert forward == backward             # ...while the content is identical
    assert answers_fingerprint(forward) == answers_fingerprint(backward)


def test_a_re_answered_value_changes_the_fingerprint():
    """THE DEFECT, at the unit level: same keys, same length, different answers."""
    before = {"a_001": 1, "b_002": 2}
    after = {"a_001": 3, "b_002": 2}
    assert len(before) == len(after)
    assert answers_fingerprint(before) != answers_fingerprint(after)


def test_an_added_answer_changes_the_fingerprint():
    before = {"a_001": 1}
    after = {"a_001": 1, "b_002": 0}
    assert answers_fingerprint(before) != answers_fingerprint(after)


def test_a_removed_answer_changes_the_fingerprint():
    assert answers_fingerprint({"a_001": 1, "b_002": 0}) != answers_fingerprint({"a_001": 1})


def test_the_fingerprint_is_stable_across_calls_and_shaped_as_expected():
    """Deterministic within a process and hex-truncated to 32 chars."""
    fp = answers_fingerprint(READY_ANSWERS)
    assert fp == answers_fingerprint(dict(READY_ANSWERS))
    assert len(fp) == 32
    assert all(c in "0123456789abcdef" for c in fp)


def test_an_empty_answer_set_fingerprints_without_raising():
    assert isinstance(answers_fingerprint({}), str)
    assert answers_fingerprint({}) == answers_fingerprint(None)


# ── (b) Ready path: matching fingerprint means NO regeneration ───────────────

def test_a_matching_fingerprint_serves_the_cache_and_never_calls_the_llm(client):
    cache = _generated(READY_ANSWERS)
    prefs = FakePrefs(READY_ANSWERS, portrait_cache=cache)

    resp, gen, forming = _open_portrait(client, prefs)

    assert resp.status_code == 200
    assert resp.json()["summary"] == SUMMARY_TEXT
    gen.assert_not_awaited()
    # A served ready cache must never also pay for the forming path.
    forming.assert_not_awaited()
    assert prefs.portrait_cache is cache


# ── (c) Ready path: THE REGRESSION — a re-answer, length unchanged ───────────

def test_a_re_answer_regenerates_even_though_the_answer_count_is_unchanged(client):
    """THE REGRESSION TEST. Must fail against pre-fix code, where the gate read
    `len(answers) - watermark < PORTRAIT_REGEN_DELTA` and this delta is 0.

    The stale cache carries BOTH keys deliberately. Written with only the new key,
    this test passes against pre-fix code for the wrong reason: the old gate's
    `isinstance(watermark, int)` check fails on the missing key and it regenerates
    anyway, never exercising the count-delta path the defect lived in. With
    `answer_count_watermark` present and equal to len(answers), the old gate
    computes a delta of 0, calls the cache fresh, and serves the stale summary —
    which is precisely the production behaviour being fixed. It is also the real
    shape of a transitional row: written by the old code, read by the new.
    """
    cache = _generated(READY_ANSWERS, text="stale summary")
    cache["answer_count_watermark"] = len(READY_ANSWERS)

    revised = dict(READY_ANSWERS)
    first_qid = sorted(revised)[0]
    revised[first_qid] = revised[first_qid] + 1  # same keys, same length, new value
    assert len(revised) == len(READY_ANSWERS)

    prefs = FakePrefs(revised, portrait_cache=cache)
    fresh = _generated(revised, text="a summary that reflects the revision")

    resp, gen, _ = _open_portrait(client, prefs, generated=fresh)

    assert resp.status_code == 200
    gen.assert_awaited_once()
    assert resp.json()["summary"] == "a summary that reflects the revision"
    # The new fingerprint was persisted, so the NEXT open is a cache hit.
    assert prefs.portrait_cache["answers_fingerprint"] == answers_fingerprint(revised)
    assert prefs.portrait_cache["answers_fingerprint"] != cache["answers_fingerprint"]


# ── (d) Legacy rows written before this key existed ─────────────────────────

def test_a_legacy_cache_row_without_the_key_regenerates_once_then_self_heals(client):
    """Every production row predates `answers_fingerprint`. Treated as a mismatch:
    one regeneration on the next open, and the key is added."""
    legacy = {
        "text": "written before fingerprints existed",
        "best_fit": [],
        "answer_count_watermark": len(READY_ANSWERS),  # the old key, still present
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    prefs = FakePrefs(READY_ANSWERS, portrait_cache=legacy)
    fresh = _generated(READY_ANSWERS)

    resp, gen, _ = _open_portrait(client, prefs, generated=fresh)

    assert resp.status_code == 200
    gen.assert_awaited_once()
    assert prefs.portrait_cache["answers_fingerprint"] == answers_fingerprint(READY_ANSWERS)

    # Second open on the healed row: cache hit, no further generation.
    resp2, gen2, _ = _open_portrait(client, prefs)
    assert resp2.status_code == 200
    gen2.assert_not_awaited()


# ── (e) Forming path: the same pair ─────────────────────────────────────────

def _forming_answers():
    """Too few categories to be 'ready', so the forming branch runs."""
    two = sorted(free_question_ids())[:2]
    return {qid: 0 for qid in two}


def test_a_matching_forming_fingerprint_serves_the_preview_without_regenerating(client):
    answers = _forming_answers()
    prefs = FakePrefs(
        answers,
        portrait_cache={
            "forming": {
                "preview": ["a stable line", "a second stable line"],
                "answers_fingerprint": answers_fingerprint(answers),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    resp, gen, forming = _open_portrait(client, prefs)

    assert resp.status_code == 200
    assert resp.json()["state"] == "forming"
    assert resp.json()["preview"] == ["a stable line", "a second stable line"]
    forming.assert_not_awaited()
    gen.assert_not_awaited()


def test_a_forming_re_answer_regenerates_the_preview_and_stores_the_new_fingerprint(client):
    """The forming half of the regression. Same keys, same length, new value."""
    answers = _forming_answers()
    stale_fp = answers_fingerprint(answers)

    revised = dict(answers)
    first_qid = sorted(revised)[0]
    revised[first_qid] = revised[first_qid] + 1
    assert len(revised) == len(answers)

    prefs = FakePrefs(
        revised,
        portrait_cache={
            "forming": {
                "preview": ["a stale line"],
                "answers_fingerprint": stale_fp,
                # Both keys, for the reason given on the ready-path sibling: without
                # the old watermark the pre-fix gate short-circuits on its isinstance
                # check instead of computing the delta this defect lived in.
                "answer_count_watermark": len(revised),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    resp, _gen, forming = _open_portrait(
        client, prefs, preview=["a line about the revision", "and another"],
    )

    assert resp.status_code == 200
    assert resp.json()["preview"] == ["a line about the revision", "and another"]
    forming.assert_awaited_once()
    stored = prefs.portrait_cache["forming"]
    assert stored["answers_fingerprint"] == answers_fingerprint(revised)
    assert stored["answers_fingerprint"] != stale_fp


# ── (f) Failure cooldown — behaviour this change must NOT alter ─────────────

def test_a_recent_failure_suppresses_regeneration_and_serves_the_stale_summary(client):
    """The cooldown still wins over a fingerprint mismatch: an LLM outage must not
    re-fire the ~2-4s generation on every open, even though the answers changed."""
    stale = _generated(READY_ANSWERS, text="a stale but usable summary")
    stale["last_failed_at"] = datetime.now(timezone.utc).isoformat()

    revised = dict(READY_ANSWERS)
    revised[sorted(revised)[0]] = 1
    prefs = FakePrefs(revised, portrait_cache=stale)

    resp, gen, _ = _open_portrait(client, prefs, generated=_generated(revised))

    assert resp.status_code == 200
    gen.assert_not_awaited()
    assert resp.json()["summary"] == "a stale but usable summary"


def test_an_expired_cooldown_lets_the_mismatch_regenerate_again(client):
    """Self-heal: once the cooldown lapses, a mismatch regenerates as normal."""
    stale = _generated(READY_ANSWERS, text="a stale but usable summary")
    stale["last_failed_at"] = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat()

    revised = dict(READY_ANSWERS)
    revised[sorted(revised)[0]] = 1
    prefs = FakePrefs(revised, portrait_cache=stale)

    resp, gen, _ = _open_portrait(
        client, prefs, generated=_generated(revised, text="regenerated"),
    )

    assert resp.status_code == 200
    gen.assert_awaited_once()
    assert resp.json()["summary"] == "regenerated"
    # The fresh dict replaces the whole cache, dropping last_failed_at — the
    # self-heal generate_portrait's docstring describes.
    assert "last_failed_at" not in prefs.portrait_cache


def test_a_generation_failure_stamps_the_marker_without_losing_the_prior_summary(client):
    """generate_portrait returning None must mark_failed (merged) and still 200."""
    prior = _generated(READY_ANSWERS, text="the previous good summary")
    revised = dict(READY_ANSWERS)
    revised[sorted(revised)[0]] = 1
    prefs = FakePrefs(revised, portrait_cache=prior)

    resp, gen, _ = _open_portrait(client, prefs, generated=None)

    assert resp.status_code == 200
    gen.assert_awaited_once()
    assert "last_failed_at" in prefs.portrait_cache
    # The prior summary survives the merge and is what gets served.
    assert prefs.portrait_cache["text"] == "the previous good summary"
    assert resp.json()["summary"] == "the previous good summary"
