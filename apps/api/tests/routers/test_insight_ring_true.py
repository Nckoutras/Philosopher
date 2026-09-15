"""Γ-2 — PATCH /insights/{id}/ring-true, the recognition loop's record.

WHAT THIS IS FOR. Until now the only durable thing a reader could do with a claim
the product made about them was dismiss it, and `is_dismissed` conflates "wrong
about me" with "seen, done with it". Someone who read an insight and thought
*yes, exactly* left no trace at all.

THE TWO ASSERTIONS THAT MATTER MOST are not about the happy path:

  - test_a_no_does_not_dismiss. The verdict is independent of is_dismissed, and
    that is mechanical rather than editorial: the 6h insight throttle counts
    NON-dismissed rows, so a 'no' that dismissed would quietly widen how often
    the room may notice anything — as a side effect of someone disagreeing.
  - test_the_event_fires_after_the_commit. get_db commits in its TEARDOWN, after
    the handler returns, so an event fired without the router's explicit commit
    would report a write that had not happened yet.

Run: cd apps/api && pytest tests/routers/test_insight_ring_true.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER_ID = "bbbbbbbb-0000-0000-0000-000000000002"
INSIGHT_ID = "cccccccc-0000-0000-0000-000000000003"
URL = f"/api/v1/insights/{INSIGHT_ID}/ring-true"


def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = "reader@example.com"
    return u


def _make_insight(insight_type="pattern", ring_true=None, is_dismissed=False):
    """C-06: every field InsightOut validates is set explicitly.

    InsightOut is a pydantic model, so a MagicMock attribute it happens to read
    would raise a ValidationError inside the router rather than in the test — the
    TD-45 failure mode. `ring_true=None` in particular must be a real None: a Mock
    there would serialise as a Mock and the response assertions would be checking
    the fixture rather than the handler.
    """
    i = MagicMock()
    i.id = INSIGHT_ID
    i.user_id = USER_ID
    i.content = "You keep returning to the same decision."
    i.insight_type = insight_type
    i.source_count = 3
    i.conversation_id = None
    i.is_dismissed = is_dismissed
    i.ring_true = ring_true
    i.ring_true_at = None
    i.created_at = datetime.now(timezone.utc)
    return i


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db_holder = [AsyncMock()]
    user_holder = [_make_user()]

    async def override_db():
        yield db_holder[0]

    async def override_user():
        return user_holder[0]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    yield tc
    app.dependency_overrides.clear()


def _patch_db_for(client, insight):
    result = MagicMock()
    result.scalar_one_or_none.return_value = insight

    async def fake_execute(q):
        return result

    client._db[0].execute = fake_execute
    client._db[0].commit = AsyncMock()


# ── The write ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("verdict", ["yes", "partly", "no"])
def test_each_verdict_is_written_with_a_timestamp(client, verdict):
    insight = _make_insight()
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service"):
        resp = client.patch(URL, json={"ring_true": verdict})

    assert resp.status_code == 200
    assert insight.ring_true == verdict
    assert insight.ring_true_at is not None
    assert insight.ring_true_at.tzinfo is not None, "timestamp must be tz-aware (TD-76)"


def test_the_response_carries_the_new_verdict(client):
    insight = _make_insight()
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service"):
        resp = client.patch(URL, json={"ring_true": "partly"})

    assert resp.json()["ring_true"] == "partly"


def test_a_verdict_can_be_changed(client):
    """A person may change their mind, and the timestamp moves with the answer."""
    insight = _make_insight(ring_true="yes")
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service"):
        resp = client.patch(URL, json={"ring_true": "no"})

    assert resp.status_code == 200
    assert insight.ring_true == "no"


# ── The independence that protects the throttle ──────────────────────────────

@pytest.mark.parametrize("verdict", ["yes", "partly", "no"])
def test_a_no_does_not_dismiss(client, verdict):
    """THE ONE THAT GUARDS THE THROTTLE.

    is_dismissed gates the 6h insight throttle (memory_service). If a 'no' ever
    dismissed, disagreeing with the room would widen how often the room is allowed
    to speak — and it would do so invisibly, because both behaviours look correct
    on the card. Discard stays the only dismissal.
    """
    insight = _make_insight(is_dismissed=False)
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service"):
        client.patch(URL, json={"ring_true": verdict})

    assert insight.is_dismissed is False, f"a {verdict!r} verdict must not dismiss the insight"


# ── The vocabulary ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["Yes", "maybe", "", "not really", "no ", "x" * 40, None])
def test_an_off_vocabulary_verdict_is_refused_at_the_edge(client, bad):
    """422 from the Literal, before the handler runs — so nothing can reach the
    column that its CHECK would reject with a 500, and nothing off-vocabulary can
    reach analytics."""
    insight = _make_insight()
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service") as analytics:
        resp = client.patch(URL, json={"ring_true": bad})

    assert resp.status_code == 422, f"{bad!r} should be refused by the schema"
    assert insight.ring_true is None
    analytics.track.assert_not_called()


def test_a_missing_body_is_refused(client):
    _patch_db_for(client, _make_insight())
    with patch("routers.memory.analytics_service"):
        assert client.patch(URL, json={}).status_code == 422


# ── Ownership ────────────────────────────────────────────────────────────────

def test_another_users_insight_is_not_found(client):
    """The query filters on user_id, so someone else's insight resolves to None
    and 404s — the same shape as /dismiss. Asserted because this endpoint is NOT
    Pro-gated, so it is the least-guarded write on the insight surface."""
    _patch_db_for(client, None)

    with patch("routers.memory.analytics_service") as analytics:
        resp = client.patch(URL, json={"ring_true": "yes"})

    assert resp.status_code == 404
    analytics.track.assert_not_called()


def test_it_is_not_pro_gated(client):
    """Correcting a claim the product made about you is not a paid feature. The
    router depends on get_current_user, not get_current_user_plan; this asserts a
    free user gets a 200 rather than the 403 every other insight door returns."""
    import inspect
    import routers.memory as m
    from auth import get_current_user, get_current_user_plan

    # The SIGNATURE, not the source text — the docstring names the dependency it
    # deliberately does not use, and a substring check would trip on the
    # explanation rather than on the behaviour.
    deps = [
        pd.default.dependency
        for pd in inspect.signature(m.set_insight_ring_true).parameters.values()
        if hasattr(pd.default, "dependency")
    ]
    assert get_current_user in deps, "the route must authenticate"
    assert get_current_user_plan not in deps, "a verdict must not be Pro-gated"

    _patch_db_for(client, _make_insight())
    with patch("routers.memory.analytics_service"):
        assert client.patch(URL, json={"ring_true": "no"}).status_code == 200


# ── The event ────────────────────────────────────────────────────────────────

def test_the_event_carries_three_enums_and_nothing_else(client):
    """Γ-5 added `surface`. Still an exact-equality assertion rather than a
    subset: this event's whole safety property is that its payload is closed,
    and a subset check would stop noticing the fourth key someone adds."""
    insight = _make_insight(insight_type="belief")
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service") as analytics:
        client.patch(URL, json={"ring_true": "partly"})

    analytics.track.assert_called_once()
    name, user_id, props = analytics.track.call_args[0]
    assert name == "memory_feedback"
    assert user_id == USER_ID
    assert props == {
        "insight_type": "belief", "verdict": "partly", "surface": "insight",
    }


def test_a_legacy_insight_with_no_type_sends_none(client):
    """insight_type is nullable. None rather than a stand-in string, so the
    dashboard can tell "no type recorded" from a type literally called unknown —
    the letter_delivered precedent."""
    insight = _make_insight(insight_type=None)
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service") as analytics:
        client.patch(URL, json={"ring_true": "yes"})

    _, _, props = analytics.track.call_args[0]
    assert props["insight_type"] is None


def test_the_insight_content_never_becomes_a_property(client):
    """The card's content is the reader's own material, distilled. It is the most
    sensitive string on this route and must never ride along."""
    insight = _make_insight()
    _patch_db_for(client, insight)

    with patch("routers.memory.analytics_service") as analytics:
        client.patch(URL, json={"ring_true": "yes"})

    _, _, props = analytics.track.call_args[0]
    assert set(props) == {"insight_type", "verdict", "surface"}
    assert insight.content not in str(props)


def test_the_event_fires_after_the_commit(client):
    """get_db commits in its TEARDOWN — after the handler returns. So without the
    router's own explicit commit, this event would report a write that had not
    happened, and would still report it if the teardown commit then failed.

    Asserted by ORDER, not by presence: the commit must already have been awaited
    at the moment track() is called.
    """
    insight = _make_insight()
    _patch_db_for(client, insight)

    order = []
    client._db[0].commit = AsyncMock(side_effect=lambda: order.append("commit"))

    with patch("routers.memory.analytics_service") as analytics:
        analytics.track.side_effect = lambda *a, **k: order.append("track")
        client.patch(URL, json={"ring_true": "yes"})

    assert order == ["commit", "track"], f"expected commit before track, got {order}"


# ── The blast radius: what a verdict must NOT change ─────────────────────────

def test_the_insight_throttle_ignores_the_verdict():
    """The 6h gate counts NON-DISMISSED insights and must keep doing exactly that.

    This is the other half of test_a_no_does_not_dismiss, from the throttle's side.
    Two ways the frequency guard could be loosened without anyone meaning to:
    a verdict that set is_dismissed (covered above), or a throttle taught to skip
    rejected rows (covered here). Either would let the room speak more often
    BECAUSE a reader disagreed with it, which inverts what disagreement should do.

    A rejected insight still occupies its 6h window. It happened; the reader
    said it was wrong; that is not a licence to immediately try again.
    """
    import inspect
    import services.memory_service as ms

    src = inspect.getsource(ms.MemoryService._insight_gate_blocked)
    assert "is_dismissed" in src, "the gate must still count only non-dismissed insights"
    assert "ring_true" not in src, (
        "the insight throttle must not consider the verdict — a rejected insight "
        "still occupies its window, or disagreeing with the room would let the room "
        "speak sooner"
    )
