"""Γ-1 — the letter loop's return half: ?src=email, email_opened_at, letter_open_to_app.

WHY THIS FILE EXISTS. `email_sent_at` and `read_at` have always sat on the same
row, so "opened within 72h of delivery" was computable before this change. What
was not computable is whether the EMAIL caused it: `read_at` is written by the
first authenticated fetch from ANY door — the Home card and the letters list
write it exactly as an email click does. Blueprint §16 asks that a delivered
letter CAUSE an authenticated return, and `read_at` answers a weaker question.

So these tests are about one distinction, and each asserts a different side of it:
`read_at` keeps its old meaning, and `email_opened_at` gets a narrower one.

THE 422 TEST IS THE POINT OF THE `str | None` TYPING. `src` is not a Literal, so
a mangled or rewritten link still renders the letter. A test that only checked the
happy path would pass identically against a Literal that 422s a real reader out of
their own letter, which is why test_an_unrecognised_src_is_ignored_not_refused
asserts the status code and not just the absence of a stamp.

Run: cd apps/api && pytest tests/routers/test_letter_attribution.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID   = "aaaaaaaa-0000-0000-0000-000000000001"
LETTER_ID = "cccccccc-0000-0000-0000-000000000001"
URL       = f"/api/v1/weekly-letters/{LETTER_ID}"

# 2026-09-07 is a Monday in ISO week 37; period_start is what `week` is read from.
PERIOD_START = datetime(2026, 9, 7, tzinfo=timezone.utc)
EXPECTED_WEEK = "2026-W37"


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = "user@example.com"
    return u


def _make_letter(email_opened_at=None, read_at=None):
    """A delivered letter with no persona row loaded.

    C-06: every field the endpoint and _to_out actually read is set explicitly,
    `email_opened_at` above all. A MagicMock would auto-create it as a Mock, and
    `letter.email_opened_at is None` would then be False — so the endpoint would
    take the "already opened" branch and every assertion below would pass or fail
    for a reason that has nothing to do with the code under test.
    """
    letter = MagicMock()
    letter.id = LETTER_ID
    letter.user_id = USER_ID
    letter.period_start = PERIOD_START
    letter.period_end = PERIOD_START + timedelta(days=6)
    letter.status = "generated"
    letter.kind = "weekly"
    letter.payload = {"pull_quote": "You already know."}
    letter.read_at = read_at
    letter.write_back_text = None
    letter.write_back_at = None
    letter.email_sent_at = PERIOD_START + timedelta(days=6)
    letter.email_opened_at = email_opened_at
    letter.voice_persona_id = None   # single-query path, no persona lookup
    return letter


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user_plan
    from db.session import get_db

    db_holder   = [AsyncMock()]
    auth_holder = [(_make_user(), "pro")]

    async def override_db():
        yield db_holder[0]

    async def override_auth():
        return auth_holder[0]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_plan] = override_auth

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    yield tc
    app.dependency_overrides.clear()


def _patch_db_for(client, letter):
    result = MagicMock()
    result.scalar_one_or_none.return_value = letter

    async def fake_execute(q):
        return result

    client._db[0].execute = fake_execute
    client._db[0].commit = AsyncMock()


# ── The stamp ────────────────────────────────────────────────────────────────

def test_src_email_stamps_email_opened_at_and_fires_the_event(client):
    letter = _make_letter()
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.get(URL, params={"src": "email"})

    assert resp.status_code == 200
    assert letter.email_opened_at is not None, "an email-attributed open must stamp the column"
    assert letter.email_opened_at.tzinfo is not None, "timestamp must be tz-aware (TD-76)"
    client._db[0].commit.assert_awaited()

    analytics.track.assert_called_once()
    name, user_id, props = analytics.track.call_args[0]
    assert name == "letter_open_to_app"
    assert user_id == USER_ID
    assert props == {"week": EXPECTED_WEEK, "host": None}


def test_the_event_joins_letter_delivered_on_week_and_host(client):
    """The pair IS the §16 gate, so the two events must agree on the join keys.
    A `week` computed differently on the two sides would produce a funnel that
    silently never joins — and a 0% gate reads exactly like a product failure."""
    from constants import ANALYTICS_EVENTS

    delivered = ANALYTICS_EVENTS["letter_delivered"]
    opened    = ANALYTICS_EVENTS["letter_open_to_app"]
    assert set(opened) == {"week", "host"}
    assert set(opened).issubset(set(delivered)), (
        f"letter_open_to_app props {opened} must be a subset of letter_delivered {delivered}"
    )

    # And the same strftime format on both sides, asserted against the source so a
    # future edit to either cannot drift the join silently.
    import inspect
    import routers.weekly_letters as wl
    import workers.arq_worker as aw
    fmt = "%G-W%V"
    assert fmt in inspect.getsource(wl.get_weekly_letter)
    assert fmt in inspect.getsource(aw)


# ── Idempotence ──────────────────────────────────────────────────────────────

def test_a_second_visit_from_the_email_does_not_overwrite(client):
    """The timestamp means "the first time this letter's email brought someone
    back". A forwarded link opened weeks later must not move it, and must not
    emit a second event — which would double-count the gate's numerator."""
    first = datetime(2026, 9, 13, 9, 30, tzinfo=timezone.utc)
    letter = _make_letter(email_opened_at=first, read_at=first)
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.get(URL, params={"src": "email"})

    assert resp.status_code == 200
    assert letter.email_opened_at == first, "a second email open must not move the timestamp"
    analytics.track.assert_not_called()
    client._db[0].commit.assert_not_awaited()


# ── read_at is untouched ─────────────────────────────────────────────────────

def test_a_visit_without_src_leaves_email_opened_at_null(client):
    """The in-app doors (Home card, letters list) still write read_at and must
    NOT write email_opened_at — that separation is the whole reason the column
    exists."""
    letter = _make_letter()
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.get(URL)

    assert resp.status_code == 200
    assert letter.read_at is not None, "read_at behaviour is unchanged: any door writes it"
    assert letter.email_opened_at is None, "no marker, no attribution"
    analytics.track.assert_not_called()


def test_src_email_also_writes_read_at_on_a_first_open(client):
    """One fetch, both meanings: an email click is still a read."""
    letter = _make_letter()
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service"):
        resp = client.get(URL, params={"src": "email"})

    assert resp.status_code == 200
    assert letter.read_at is not None
    assert letter.email_opened_at is not None


# ── The deviation: no free text, and no refusal ──────────────────────────────

@pytest.mark.parametrize("value", [
    "Email",                     # case matters — only the exact marker counts
    "email ",                    # a trailing space from a rewritten link
    "web",
    "https://safelinks.example/?u=email",
    "x" * 500,                   # an absurd value must still not refuse
])
def test_an_unrecognised_src_is_ignored_not_refused(client, value):
    """Analytics is an observer and may not change what the product does.

    A Literal["email"] annotation would answer 422 here and the reader would lose
    their letter to an analytics annotation. This is the CheckoutRequest.source
    rationale (schemas/__init__.py) applied one level up: a value this endpoint
    does not recognise is a reporting gap, never a reason to refuse.
    """
    letter = _make_letter()
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        resp = client.get(URL, params={"src": value})

    assert resp.status_code == 200, f"src={value!r} must not refuse the letter"
    assert letter.email_opened_at is None, f"src={value!r} must not be treated as the marker"
    analytics.track.assert_not_called()


def test_src_is_never_sent_as_an_event_property(client):
    """The strongest form of "no free text in analytics" is that the free text has
    no path to the event at all: `src` is read once, compared, and dropped. The
    properties are read off the letter row, never off the request."""
    letter = _make_letter()
    _patch_db_for(client, letter)

    with patch("routers.weekly_letters.analytics_service") as analytics:
        client.get(URL, params={"src": "email"})

    _, _, props = analytics.track.call_args[0]
    assert "src" not in props
    assert set(props) == {"week", "host"}
    for v in props.values():
        assert v is None or isinstance(v, str)


# ── The two ends of the link ─────────────────────────────────────────────────

def test_the_letter_email_read_link_carries_the_marker():
    """A SOURCE assertion, deliberately — the #578 precedent. The runtime
    alternative would need a rendered email and a config'd FRONTEND_URL, and it
    would be measuring the test harness as much as the decision. What matters is
    that the call site still appends the marker."""
    import inspect
    import workers.arq_worker as aw

    src = inspect.getsource(aw)
    assert '/app/letters/{letter.id}?src=email' in src, (
        "the weekly-letter email's read link must carry ?src=email — without it "
        "email_opened_at is never written and the §16 gate reads 0%"
    )


def test_both_ends_of_the_loop_use_the_same_marker_string():
    """The link writes it and the router compares against it. If either side is
    renamed alone the loop breaks SILENTLY: letters still deliver, letters still
    read, and the gate quietly reports nothing. Nothing else in the system would
    notice, which is exactly why this assertion exists."""
    import inspect
    import workers.arq_worker as aw
    import routers.weekly_letters as wl

    marker = "email"
    assert f"?src={marker}" in inspect.getsource(aw)
    assert f'src == "{marker}"' in inspect.getsource(wl.get_weekly_letter)
