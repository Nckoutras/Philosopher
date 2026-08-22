"""GET /preferences/self-portrait must report category coverage from the UNFILTERED
stored answers, not from the tier-filtered `answers` it returns.

THE DEFECT THIS PINS. `answers` in the response is filtered to the questions the
caller's tier may see. The frontend used to derive the coverage bar from that filtered
set, which UNDERCOUNTS for a lapsed Pro->free user: they answered questions while Pro
whose ids are no longer in the free visible set, so the categories those answers cover
vanished from the count. The fix moves the count server-side, computed from `stored`.

WHY THE ASSERTION IS `== 1` AND NOT MERELY "present". Asserting the field exists would
pass even if someone wired `answered_category_count(answers)` — the filtered dict — which
is the exact bug. The fixture answers ONE question that is not free-visible, so:

    answered_category_count(stored)  == 1   <- correct, what we assert
    answered_category_count(answers) == 0   <- the regression, which this fails on

Both the id and its category are resolved FROM THE BANK at runtime rather than
hardcoded, so this keeps testing the same property if the bank is re-authored.

Run: cd apps/api && pytest tests/routers/test_self_portrait_coverage.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from services.self_portrait import _BANK, free_question_ids, total_category_count

USER_ID = "aaaaaaaa-0000-0000-0000-000000000002"
URL = "/api/v1/preferences/self-portrait"


def _a_non_free_question_id() -> str:
    """A bank question the FREE tier cannot see. This is the id whose answer the old
    client-side derivation threw away."""
    free = free_question_ids()
    for qid in sorted(_BANK):
        if qid not in free:
            return qid
    raise AssertionError("bank has no non-free question — the free tier sees everything")


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = "lapsed-pro@example.com"
    u.is_admin = False
    return u


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    async def override_db():
        yield AsyncMock()

    async def override_auth():
        # FREE tier — this is what filters `answers` and produced the undercount.
        return (_make_user(), "free")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_plan] = override_auth

    yield TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()


def test_coverage_count_comes_from_stored_not_filtered_answers(client):
    """A free user whose ONLY stored answer is a question their tier cannot see still
    has one category covered."""
    qid = _a_non_free_question_id()
    expected_category = _BANK[qid]["category"]

    prefs = MagicMock()
    prefs.profile = {"answers": {qid: 0}}

    with patch(
        "routers.preferences.get_user_preferences",
        AsyncMock(return_value=prefs),
    ):
        resp = client.get(URL)

    assert resp.status_code == 200
    body = resp.json()

    # The premise: this tier genuinely cannot see the answered question, so the
    # returned `answers` is empty. If this ever fails the fixture has stopped
    # exercising the defect and the assertion below proves nothing.
    assert qid not in body["answers"], (
        f"{qid} is visible to the free tier — fixture no longer reproduces the undercount"
    )
    assert body["answers"] == {}

    # The fix: the count is computed from `stored`, so the category still counts.
    assert body["answered_category_count"] == 1, (
        f"expected 1 (category {expected_category!r} answered via {qid}); "
        f"got {body['answered_category_count']} — this is the filtered-set undercount"
    )


def test_total_category_count_is_derived_from_the_bank(client):
    """The denominator is the bank's own category count, never a hardcoded 12."""
    prefs = MagicMock()
    prefs.profile = {"answers": {}}

    with patch(
        "routers.preferences.get_user_preferences",
        AsyncMock(return_value=prefs),
    ):
        resp = client.get(URL)

    assert resp.status_code == 200
    assert resp.json()["total_category_count"] == total_category_count()


def test_no_answers_reports_zero_categories(client):
    """A fresh user with no preferences row: 0 covered, denominator still real."""
    with patch(
        "routers.preferences.get_user_preferences",
        AsyncMock(return_value=None),
    ):
        resp = client.get(URL)

    assert resp.status_code == 200
    body = resp.json()
    assert body["answered_category_count"] == 0
    assert body["total_category_count"] > 0
