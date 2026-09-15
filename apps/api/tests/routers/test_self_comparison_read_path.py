"""The You-vs-You read path (G-8): list past runs, reopen one.

The payload has been written since migration 021 and read by almost nothing --
Reflections pulls only closing.sentence_owed, and only for saved runs. A run was
visible once, while it streamed, and then unreadable forever. These tests cover
the two endpoints that close that.

Run: cd apps/api && pytest tests/routers/test_self_comparison_read_path.py -v
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
COMPARISON_ID = "33333333-0000-0000-0000-000000000001"
LIST_ENDPOINT = "/api/v1/self-comparison"
DETAIL_ENDPOINT = f"/api/v1/self-comparison/{COMPARISON_ID}"


def _payload(**overrides):
    """A complete, current-shape payload, exactly as the service persists one."""
    base = {
        "then": {
            "answer": "I was bracing for it.",
            "start": "2026-01-05T00:00:00+00:00",
            "end": "2026-01-19T00:00:00+00:00",
        },
        "now": {
            "answer": "I notice I stopped bracing.",
            "start": "2026-08-01T00:00:00+00:00",
            "end": "2026-09-10T00:00:00+00:00",
        },
        "closing": {
            "observation": "Then you braced. Lately you wait.",
            "question": "Does that reading sit right with you?",
            "then_quote": {
                "text": "I keep expecting it to go wrong",
                "date": "2026-01-07T10:00:00+00:00",
            },
            "now_quote": {
                "text": "it went fine, again",
                "date": "2026-09-02T10:00:00+00:00",
            },
            "hidden_continuity": "You still watch the door.",
            "sentence_owed": "You are allowed to stop rehearsing the fall.",
        },
    }
    base.update(overrides)
    return base


# An explicit sentinel, because None is a VALUE this fixture must be able to
# express: payload is a nullable column, and "give me the default payload" and
# "give me a NULL payload" are different requests. Defaulting on `is None` made
# them the same one, and the null-payload test silently received a full payload
# and asserted against it -- present, and wrong (TD-76).
_DEFAULT_PAYLOAD = object()


class FakeComparison:
    """A plain object, not a MagicMock (C-06). Every attribute the endpoint reads
    is set explicitly, including the ones whose correct value is None -- a
    MagicMock would auto-create `status` and make the 'ready' gate pass for a
    pending row, which is precisely the branch these tests exist to pin."""

    def __init__(self, *, status="ready", payload=_DEFAULT_PAYLOAD, ring_true=None, ring_true_at=None):
        self.id = COMPARISON_ID
        self.user_id = USER_ID
        self.prompt = "Am I still afraid of the same thing?"
        self.created_at = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
        self.status = status
        self.payload = _payload() if payload is _DEFAULT_PAYLOAD else payload
        self.ring_true = ring_true
        self.ring_true_note = None
        self.ring_true_at = ring_true_at


class FakeListRow:
    def __init__(self, id_, prompt, created_at):
        self.id = id_
        self.prompt = prompt
        self.created_at = created_at


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.is_admin = False
    return u


def _make_db(*results):
    """db.execute returns each prepared result in order, and records the
    statements it was handed so a test can assert on the query itself."""
    db = AsyncMock()
    db.executed = []

    async def _execute(stmt, *a, **kw):
        db.executed.append(stmt)
        return results[min(len(db.executed) - 1, len(results) - 1)]

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    return db


def _result(*, all_=None, scalar=None):
    r = MagicMock()
    r.all.return_value = all_ or []
    r.scalar_one_or_none.return_value = scalar
    return r


@contextmanager
def _client(db):
    from main import app
    from auth import get_current_user
    from db.session import get_db

    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# -- route ordering -----------------------------------------------------------

def test_status_route_is_declared_before_the_id_route():
    """GET /self-comparison/status must not be swallowed by /{comparison_id}.

    FastAPI resolves in declaration order, so this is an ordering invariant, not
    a naming one -- and it is invisible until someone moves a decorator. Asserted
    against real resolution: the FIRST route that matches the path wins, so that
    route is the one that will answer.
    """
    from main import app

    path = "/api/v1/self-comparison/status"
    matched = [
        r
        for r in app.routes
        if getattr(r, "path_regex", None) is not None
        and r.path_regex.match(path)
        and "GET" in (getattr(r, "methods", None) or set())
    ]
    assert matched, "no GET route matches the status path at all"
    assert matched[0].name == "get_self_comparison_status", (
        "GET {0} resolves to {1!r}; the id route was declared above /status "
        "and now shadows it".format(path, matched[0].name)
    )


# -- list ---------------------------------------------------------------------

def test_list_returns_slim_rows_newest_first():
    rows = [
        FakeListRow("id-new", "the newer question", datetime(2026, 9, 10, tzinfo=timezone.utc)),
        FakeListRow("id-old", "the older question", datetime(2026, 8, 1, tzinfo=timezone.utc)),
    ]
    db = _make_db(_result(all_=rows))

    with _client(db) as client:
        resp = client.get(LIST_ENDPOINT)

    assert resp.status_code == 200
    body = resp.json()
    assert [item["id"] for item in body] == ["id-new", "id-old"]
    assert body[0]["prompt"] == "the newer question"
    # Slim by design: the payload is NOT in the list response.
    assert set(body[0]) == {"id", "prompt", "created_at"}


def test_list_query_filters_to_ready_and_orders_newest_first():
    """The three claims the endpoint's docstring makes, pinned against the SQL.

    A mocked db.execute never runs the filter, so asserting on the compiled
    statement is the only way this test can see it. Without this, dropping the
    status filter would leave every other test in this file green while the list
    started offering pending rows that reopen to nothing.
    """
    db = _make_db(_result(all_=[]))

    with _client(db) as client:
        client.get(LIST_ENDPOINT)

    sql = str(db.executed[0].compile(compile_kwargs={"literal_binds": True}))
    assert "status" in sql and "ready" in sql, sql
    assert "ORDER BY" in sql and "DESC" in sql, sql
    assert "LIMIT 10" in sql, sql


# -- detail -------------------------------------------------------------------

def test_detail_returns_what_generation_showed():
    db = _make_db(_result(scalar=FakeComparison()), _result(scalar=None))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    assert resp.status_code == 200
    body = resp.json()
    assert body["prompt"] == "Am I still afraid of the same thing?"
    assert body["then"]["answer"] == "I was bracing for it."
    assert body["now"]["answer"] == "I notice I stopped bracing."
    # The windows are the ones the run USED, read from the payload, not recomputed.
    assert body["then"]["start"] == "2026-01-05T00:00:00+00:00"
    assert body["closing"]["observation"] == "Then you braced. Lately you wait."
    assert body["closing"]["hidden_continuity"] == "You still watch the door."
    assert body["closing"]["sentence_owed"] == "You are allowed to stop rehearsing the fall."
    assert body["closing"]["then_quote"]["text"] == "I keep expecting it to go wrong"
    assert body["saved"] is False
    assert body["ring_true"] is None


def test_detail_reports_the_saved_state_and_an_existing_verdict():
    """Both exist so a reopened run renders its own state instead of an empty row
    -- the same reason InsightOut carries ring_true."""
    row = FakeComparison(
        ring_true="partly",
        ring_true_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    db = _make_db(_result(scalar=row), _result(scalar="a-live-save-row"))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    body = resp.json()
    assert body["saved"] is True
    assert body["ring_true"] == "partly"
    assert body["ring_true_at"] is not None
    # The note has no reader on this ritual and is deliberately not returned.
    assert "ring_true_note" not in body


def test_detail_404s_for_a_row_that_is_not_this_users():
    db = _make_db(_result(scalar=None))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    assert resp.status_code == 404


def test_detail_404s_for_a_pending_row():
    """A run whose stream died has a row but a NULL payload. It is not listed, so
    reaching it means a stale id; returning a half-record would be worse."""
    db = _make_db(_result(scalar=FakeComparison(status="pending", payload=None)))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    assert resp.status_code == 404


def test_detail_reopens_a_legacy_payload_without_the_r1a_beats():
    """Rows written before hidden_continuity / sentence_owed existed carry neither
    key. A strict schema would 500 on the oldest runs -- the ones most worth
    reopening. Null quotes and a missing 'now' side take the same path."""
    legacy = {
        "then": {"answer": "an older answer", "start": "2026-01-05T00:00:00+00:00", "end": None},
        "closing": {
            "observation": "an older observation",
            "question": "an older question",
            "then_quote": None,
            "now_quote": None,
        },
    }
    db = _make_db(_result(scalar=FakeComparison(payload=legacy)), _result(scalar=None))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    assert resp.status_code == 200
    body = resp.json()
    assert body["closing"]["observation"] == "an older observation"
    assert body["closing"]["hidden_continuity"] is None
    assert body["closing"]["sentence_owed"] is None
    assert body["closing"]["then_quote"] is None
    assert body["now"]["answer"] == ""


def test_detail_survives_a_payload_that_is_not_a_dict():
    """Defensive, and cheap: payload is a nullable JSONB column, so the type is a
    convention rather than a guarantee."""
    db = _make_db(_result(scalar=FakeComparison(payload=None)), _result(scalar=None))

    with _client(db) as client:
        resp = client.get(DETAIL_ENDPOINT)

    assert resp.status_code == 200
    body = resp.json()
    assert body["then"]["answer"] == ""
    assert body["closing"]["observation"] == ""
