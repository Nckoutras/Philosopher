"""Webhook idempotency, event ordering, billing interval, and lifecycle history.

WHAT WAS WRONG. The handler processed every delivery as if it were the first and
only one. Stripe retries on any non-2xx and guarantees at-least-once, not
exactly-once, and it can deliver out of order. So a retried
customer.subscription.deleted could land after a newer .updated and flip a
paying user to free; a duplicate checkout.session.completed fired
subscription_activated twice; and nothing recorded why a row was in its state.

C-06 IS THE REASON FOR THE FAKE. The existing suite's `_make_sub()` is a
MagicMock, and a MagicMock answers every attribute with a new Mock. That is what
hid the tenure_days defect these tests also cover: `_tenure_days` read
`created_at`, the mock auto-created it, the datetime subtraction raised, the
`except` swallowed it, and the event shipped `tenure_days: None` with nothing
failing. `FakeSub` below is a plain object with exactly the columns the row has,
so a field the code reads but the test forgot to set is an AttributeError, not a
silent None.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from models import StripeEvent, SubscriptionEvent

# feature_key -> the table its existence probe queries. Mirrors
# routers.billing._feature_sources; asserted against it below so the two cannot
# drift apart silently.
_FEATURE_TABLES = {
    "chat": "messages",
    "council": "council_cases",
    "counterview": "counterviews",
    "mirror": "mirrors",
    "you_vs_you": "self_comparisons",
    "letter": "weekly_letters",
    "self_portrait": "memory_entries",
    "future_self": "scheduled_emails",
}

WEBHOOK_URL = "/api/v1/billing/webhook"
USER_ID = "11111111-1111-1111-1111-111111111111"
SUB_ROW_ID = "22222222-2222-2222-2222-222222222222"
CUSTOMER_ID = "cus_test_1"
SUB_ID = "sub_test_1"
PRICE_PRO = "price_pro_monthly_test"

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
RENEWED_END = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)


class FakeSub:
    """A subscriptions row. Plain object, every column present — see the C-06
    note above. Reading a column this class does not define is an error, which
    is the entire point."""

    def __init__(self, **kw):
        self.id = SUB_ROW_ID
        self.user_id = USER_ID
        self.stripe_customer_id = CUSTOMER_ID
        self.stripe_subscription_id = SUB_ID
        self.plan = "free"
        self.status = "incomplete"
        self.current_period_end = None
        self.cancel_at_period_end = False
        self.interval = None
        self.pro_since = None
        self.last_stripe_event_at = None
        self.created_at = NOW - timedelta(days=400)
        for k, v in kw.items():
            assert hasattr(self, k), f"FakeSub has no column {k!r}"
            setattr(self, k, v)


class FakeDb:
    """AsyncSession double that RECORDS what was added, so the tests can assert
    on the stripe_events and subscription_events rows the handler writes."""

    def __init__(self, sub, flush_raises=False, features_present=()):
        self.sub = sub
        self.features_present = set(features_present)
        self.added = []
        self.flush_raises = flush_raises
        self.committed = 0
        self.rolled_back = 0
        self.deletes = []

    async def execute(self, stmt):
        # DELETE FROM stripe_events … — record it, return nothing useful.
        if stmt.__class__.__name__ == "Delete":
            self.deletes.append(stmt)
            return MagicMock()
        # The eight last_14d_features probes are SELECT model.id … LIMIT 1, and
        # the handler reads them with .first(). `features_present` names which
        # feature tables should answer "yes"; everything else answers None, so
        # an empty list is produced by a real absence rather than by a stub that
        # cannot answer at all.
        text = str(stmt)
        for key, table in _FEATURE_TABLES.items():
            if f"FROM {table}" in text:
                result = MagicMock()
                result.first.return_value = (1,) if key in self.features_present else None
                return result
        result = MagicMock()
        result.scalar_one_or_none.return_value = self.sub
        result.first.return_value = None
        return result

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        if self.flush_raises:
            raise IntegrityError("duplicate key", None, Exception())

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    # What was written, by type.
    def stripe_events(self):
        return [o for o in self.added if isinstance(o, StripeEvent)]

    def history(self):
        return [o for o in self.added if isinstance(o, SubscriptionEvent)]


@pytest.fixture
def client():
    from main import app
    from db.session import get_db

    holder = [FakeDb(FakeSub())]

    async def override_db():
        yield holder[0]

    app.dependency_overrides[get_db] = override_db
    tc = TestClient(app, raise_server_exceptions=False)
    tc._db = holder
    yield tc
    app.dependency_overrides.clear()


def _event(type_, obj, *, created=NOW, event_id="evt_1"):
    return {
        "id": event_id,
        "type": type_,
        "created": int(created.timestamp()),
        "data": {"object": obj},
    }


def _sub_obj(status="active", period_end=PERIOD_END, interval="month"):
    return {
        "id": SUB_ID,
        "customer": CUSTOMER_ID,
        "status": status,
        "cancel_at_period_end": False,
        "items": {"data": [{
            "price": {"id": PRICE_PRO, "recurring": {"interval": interval}},
            "current_period_end": int(period_end.timestamp()),
        }]},
    }


def _post(client, event, *, body=b"{}"):
    with (
        patch("routers.billing.stripe.Webhook.construct_event", return_value=event),
        patch("routers.billing.config.STRIPE_PRICE_PRO_MONTHLY", PRICE_PRO),
        patch("routers.billing.analytics_service") as analytics,
    ):
        resp = client.post(WEBHOOK_URL, content=body, headers={"stripe-signature": "sig"})
    return resp, analytics


# ── A. Idempotency ───────────────────────────────────────────────────────────

def test_the_event_id_is_recorded_before_anything_is_processed():
    """The insert is the lock. It must exist before side effects, not after."""
    db = FakeDb(FakeSub())
    from main import app
    from db.session import get_db

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        tc = TestClient(app, raise_server_exceptions=False)
        resp, _ = _post(tc, _event("customer.subscription.updated", _sub_obj()))
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    events = db.stripe_events()
    assert len(events) == 1
    assert events[0].id == "evt_1"
    assert events[0].type == "customer.subscription.updated"
    assert events[0].created == NOW
    assert events[0].processed_at is not None
    assert events[0].skipped is False


def test_a_duplicate_delivery_is_a_200_noop_and_fires_no_analytics(client):
    """THE REGRESSION. Stripe retries; the second delivery must do nothing.

    Asserting the 200 alone would not catch it — the old handler also returned
    200 while re-running every side effect. What proves the fix is that
    subscription_activated did NOT fire and the row was not touched.
    """
    sub = FakeSub(plan="pro", status="active", pro_since=NOW - timedelta(days=10))
    db = FakeDb(sub, flush_raises=True)
    client._db[0] = db

    resp, analytics = _post(client, _event("customer.subscription.updated", _sub_obj()))

    assert resp.status_code == 200
    assert resp.json() == {"received": True, "duplicate": True}
    analytics.track.assert_not_called()
    assert db.rolled_back == 1
    assert db.history() == []
    # The row is untouched: same tenure start, no new period end.
    assert sub.pro_since == NOW - timedelta(days=10)
    assert sub.current_period_end is None


def test_a_processing_crash_deletes_the_row_so_stripes_retry_can_reprocess(client):
    """A row left behind would make the retry a permanent duplicate-conflict:
    Stripe would keep delivering, the handler would keep answering 200, and the
    event would never be applied."""
    sub = FakeSub()
    db = FakeDb(sub)
    client._db[0] = db

    boom = _event("customer.subscription.updated", _sub_obj())
    with (
        patch("routers.billing.stripe.Webhook.construct_event", return_value=boom),
        patch("routers.billing.config.STRIPE_PRICE_PRO_MONTHLY", PRICE_PRO),
        patch("routers.billing._plan_from_stripe", side_effect=RuntimeError("kaboom")),
    ):
        resp = client.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    # 500 asks Stripe to retry at all...
    assert resp.status_code == 500
    # ...and the delete is what makes the retry able to succeed.
    assert len(db.deletes) == 1
    assert db.rolled_back == 1


# ── Signature and payload ────────────────────────────────────────────────────

def test_a_malformed_body_is_400_not_500(client):
    """A 5xx makes Stripe retry, and retrying an unparseable payload burns
    deliveries forever against something that can never succeed."""
    with patch(
        "routers.billing.stripe.Webhook.construct_event",
        side_effect=ValueError("not json"),
    ):
        resp = client.post(WEBHOOK_URL, content=b"<<<", headers={"stripe-signature": "sig"})
    assert resp.status_code == 400


# ── B. Ordering ──────────────────────────────────────────────────────────────

def test_a_stale_event_is_recorded_skipped_and_changes_nothing(client):
    """THE MONEY CASE. A retried .deleted arriving after a newer .updated used to
    flip a paying subscriber to free."""
    sub = FakeSub(
        plan="pro", status="active", pro_since=NOW - timedelta(days=30),
        last_stripe_event_at=NOW,
    )
    db = FakeDb(sub)
    client._db[0] = db

    stale = _event(
        "customer.subscription.deleted",
        {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"},
        created=NOW - timedelta(hours=1),
    )
    resp, analytics = _post(client, stale)

    assert resp.status_code == 200
    # Still Pro. This is the assertion the whole PR exists for.
    assert sub.plan == "pro"
    assert sub.status == "active"
    assert sub.pro_since == NOW - timedelta(days=30)
    analytics.track.assert_not_called()
    assert db.history() == []
    # Recorded, and recorded AS skipped — distinguishable from a crash.
    assert db.stripe_events()[0].skipped is True
    assert db.stripe_events()[0].processed_at is not None


def test_a_null_baseline_applies_the_event_because_of_the_reconcile_cron(client):
    """NULL last_stripe_event_at means APPLY. The 6-hourly reconcile cron writes
    status without going through the webhook, so a row it touched has no
    baseline and never will — treating NULL as "everything is stale" would
    freeze those rows permanently."""
    sub = FakeSub(last_stripe_event_at=None)
    client._db[0] = FakeDb(sub)

    resp, _ = _post(client, _event("customer.subscription.updated", _sub_obj()))

    assert resp.status_code == 200
    assert sub.plan == "pro"
    assert sub.last_stripe_event_at == NOW


def test_an_equal_timestamp_applies(client):
    """Stripe's `created` has one-second resolution, so two genuinely distinct
    events can share it. Refusing the second would drop a real transition to
    save a redundant one."""
    sub = FakeSub(last_stripe_event_at=NOW)
    client._db[0] = FakeDb(sub)

    resp, _ = _post(client, _event("customer.subscription.updated", _sub_obj(), created=NOW))

    assert resp.status_code == 200
    assert sub.plan == "pro"


def test_the_baseline_only_moves_forward(client):
    sub = FakeSub(last_stripe_event_at=NOW - timedelta(days=1))
    client._db[0] = FakeDb(sub)

    _post(client, _event("customer.subscription.updated", _sub_obj(), created=NOW))
    assert sub.last_stripe_event_at == NOW


def test_a_stale_payment_failed_does_not_past_due_a_recovered_account(client):
    """The hole the cancel path had, on the invoice path.

    payment_failed(t1) -> subscription.updated past_due(t2) -> card fixed ->
    subscription.updated active(t3) -> Stripe retries payment_failed from t1.
    Without the guard, an active paying subscriber is marked past_due by a
    delivery about a payment that was already resolved.
    """
    sub = FakeSub(
        plan="pro", status="active", pro_since=NOW - timedelta(days=60),
        last_stripe_event_at=NOW,
    )
    db = FakeDb(sub)
    client._db[0] = db

    resp, _ = _post(client, _event(
        "invoice.payment_failed", {"subscription": SUB_ID},
        created=NOW - timedelta(hours=2),
    ))

    assert resp.status_code == 200
    assert sub.status == "active"          # still paying
    assert db.history() == []              # no transition invented
    assert db.stripe_events()[0].skipped is True


def test_a_payment_failed_advances_the_baseline(client):
    """An applied invoice event must move the high-water mark, or the NEXT stale
    delivery is judged against a mark this one should have raised."""
    sub = FakeSub(plan="pro", status="active", last_stripe_event_at=NOW - timedelta(days=1))
    client._db[0] = FakeDb(sub)

    _post(client, _event("invoice.payment_failed", {"subscription": SUB_ID}, created=NOW))

    assert sub.status == "past_due"
    assert sub.last_stripe_event_at == NOW


def test_a_payment_succeeded_advances_the_baseline_even_when_nothing_changed(client):
    """Status was already active, so nothing is written — but the event WAS
    applied to this row, and the baseline has to reflect that."""
    sub = FakeSub(plan="pro", status="active", last_stripe_event_at=NOW - timedelta(days=1))
    db = FakeDb(sub)
    client._db[0] = db

    _post(client, _event("invoice.payment_succeeded", {"subscription": SUB_ID}, created=NOW))

    assert sub.status == "active"
    assert db.history() == []              # nothing to record
    assert sub.last_stripe_event_at == NOW  # but the mark still moves


def test_a_stale_payment_succeeded_is_skipped(client):
    sub = FakeSub(plan="pro", status="past_due", last_stripe_event_at=NOW)
    db = FakeDb(sub)
    client._db[0] = db

    resp, _ = _post(client, _event(
        "invoice.payment_succeeded", {"subscription": SUB_ID},
        created=NOW - timedelta(hours=3),
    ))

    assert resp.status_code == 200
    assert sub.status == "past_due"        # not healed by a stale event
    assert db.stripe_events()[0].skipped is True


# ── C. Renewal keeps its single writer ───────────────────────────────────────

def test_renewal_advances_the_period_end(client):
    sub = FakeSub(plan="pro", status="active", current_period_end=PERIOD_END)
    client._db[0] = FakeDb(sub)

    resp, _ = _post(client, _event(
        "customer.subscription.updated", _sub_obj(period_end=RENEWED_END),
    ))

    assert resp.status_code == 200
    assert sub.current_period_end == RENEWED_END


def test_invoice_payment_succeeded_records_the_event_but_writes_no_date(client):
    """current_period_end keeps ONE writer. This case heals status and nothing
    else — a second writer would be two paths to the field."""
    sub = FakeSub(plan="pro", status="past_due", current_period_end=PERIOD_END)
    db = FakeDb(sub)
    client._db[0] = db

    resp, _ = _post(client, _event(
        "invoice.payment_succeeded", {"subscription": SUB_ID},
    ))

    assert resp.status_code == 200
    assert sub.status == "active"
    assert sub.current_period_end == PERIOD_END  # untouched
    # Recorded in stripe_events regardless — that is what makes it idempotent.
    assert len(db.stripe_events()) == 1
    assert db.stripe_events()[0].type == "invoice.payment_succeeded"


# ── D. Interval ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("interval", ["month", "year"])
def test_the_interval_is_persisted_from_the_stripe_price(client, interval):
    sub = FakeSub()
    client._db[0] = FakeDb(sub)

    _post(client, _event("customer.subscription.updated", _sub_obj(interval=interval)))

    assert sub.interval == interval


# ── pro_since and tenure_days ────────────────────────────────────────────────

def test_pro_since_is_stamped_on_the_first_activation(client):
    sub = FakeSub(plan="free", status="incomplete", pro_since=None)
    client._db[0] = FakeDb(sub)

    _post(client, _event("customer.subscription.updated", _sub_obj()))

    assert sub.pro_since is not None


def test_pro_since_is_not_restarted_by_a_renewal(client):
    """Idempotent by design: if every renewal reset it, tenure would read as
    zero for a subscriber of two years."""
    started = NOW - timedelta(days=200)
    sub = FakeSub(plan="pro", status="active", pro_since=started)
    client._db[0] = FakeDb(sub)

    _post(client, _event("customer.subscription.updated", _sub_obj(period_end=RENEWED_END)))

    assert sub.pro_since == started


def test_cancel_clears_pro_since_so_a_resubscribe_starts_fresh(client):
    sub = FakeSub(plan="pro", status="active", pro_since=NOW - timedelta(days=90))
    client._db[0] = FakeDb(sub)

    _post(client, _event(
        "customer.subscription.deleted",
        {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"},
    ))

    assert sub.pro_since is None
    assert sub.plan == "free"
    assert sub.status == "canceled"


def test_tenure_days_is_a_real_integer_from_pro_since(client):
    """The C-06 hazard, made into an assertion. pro_since is set EXPLICITLY, so
    no auto-Mock can reach _tenure_days and make this pass as None."""
    sub = FakeSub(plan="pro", status="active", pro_since=datetime.now(timezone.utc) - timedelta(days=90))
    client._db[0] = FakeDb(sub)

    _, analytics = _post(client, _event(
        "customer.subscription.deleted",
        {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"},
    ))

    props = analytics.track.call_args[0][2]
    assert isinstance(props["tenure_days"], int)
    assert props["tenure_days"] == 90
    assert props["plan"] == "pro"  # the plan they CANCELLED, not "free"


def test_tenure_days_is_none_when_the_row_never_paid(client):
    """None, not zero: zero days of paid tenure is a real and different answer."""
    sub = FakeSub(plan="pro", status="active", pro_since=None)
    client._db[0] = FakeDb(sub)

    _, analytics = _post(client, _event(
        "customer.subscription.deleted",
        {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"},
    ))

    props = analytics.track.call_args[0][2]
    assert props["tenure_days"] is None


def test_tenure_days_no_longer_reads_created_at():
    """Direct unit check on the helper: a row with a year-old created_at and no
    pro_since must report None, not 365. That inversion IS the defect."""
    from routers.billing import _tenure_days

    sub = FakeSub(created_at=datetime.now(timezone.utc) - timedelta(days=365), pro_since=None)
    assert _tenure_days(sub) is None

    sub.pro_since = datetime.now(timezone.utc) - timedelta(days=7)
    assert _tenure_days(sub) == 7


# ── Grace: the recovery email ────────────────────────────────────────────────

def _deleted_event(details=None, created=NOW):
    obj = {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"}
    if details is not None:
        obj["cancellation_details"] = details
    return _event("customer.subscription.deleted", obj, created=created)


def test_entering_dunning_queues_exactly_one_recovery_email(client):
    """A recoverable card problem used to become a churn event in silence."""
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub)

    with patch("routers.billing._send_recovery_email") as send:
        _post(client, _event("invoice.payment_failed", {"subscription": SUB_ID}))

    assert sub.status == "past_due"
    assert send.await_count == 1
    assert send.await_args[0][2] == USER_ID


def test_a_second_failure_in_the_same_episode_sends_nothing(client):
    """Stripe retries a failed payment several times and sends payment_failed
    each time. The row is already past_due, so the user has been told."""
    sub = FakeSub(plan="pro", status="past_due")
    client._db[0] = FakeDb(sub)

    with patch("routers.billing._send_recovery_email") as send:
        _post(client, _event(
            "invoice.payment_failed", {"subscription": SUB_ID}, event_id="evt_2",
        ))

    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_sender_prefers_the_queue_and_never_raises():
    from routers.billing import _send_recovery_email

    request = MagicMock()
    request.app.state.arq_queue = AsyncMock()
    await _send_recovery_email(request, FakeDb(FakeSub()), USER_ID)

    request.app.state.arq_queue.enqueue_job.assert_awaited_once_with(
        "send_payment_recovery_email_task", USER_ID,
    )


@pytest.mark.asyncio
async def test_no_queue_falls_back_to_a_synchronous_send_not_to_silence():
    """A misconfigured queue must not quietly eat a revenue-recovery email."""
    from routers.billing import _send_recovery_email

    request = MagicMock()
    request.app.state.arq_queue = None
    db = FakeDb(FakeSub())
    user = MagicMock()
    user.email = "reader@example.test"
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)

    with patch("services.email_service.send_email") as send:
        await _send_recovery_email(request, db, USER_ID)

    send.assert_called_once()
    assert send.call_args.kwargs["to"] == "reader@example.test"


@pytest.mark.asyncio
async def test_a_failing_queue_also_falls_back_to_a_synchronous_send():
    """A queue that EXISTS but rejects the job is the same failure as no queue at
    all, from the user's side: the recovery email either goes or it does not.
    Covered separately because the absent-queue test cannot see this branch."""
    from routers.billing import _send_recovery_email

    request = MagicMock()
    request.app.state.arq_queue = AsyncMock()
    request.app.state.arq_queue.enqueue_job.side_effect = RuntimeError("redis down")

    db = FakeDb(FakeSub())
    user = MagicMock()
    user.email = "reader@example.test"
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)

    with patch("services.email_service.send_email") as send:
        await _send_recovery_email(request, db, USER_ID)

    send.assert_called_once()
    assert send.call_args.kwargs["to"] == "reader@example.test"


@pytest.mark.asyncio
async def test_a_send_failure_never_propagates():
    """The webhook has already applied a billing state change by this point. A
    failed email must not turn that into a 500 and a Stripe retry."""
    from routers.billing import _send_recovery_email

    request = MagicMock()
    request.app.state.arq_queue = AsyncMock()
    request.app.state.arq_queue.enqueue_job.side_effect = RuntimeError("redis down")
    db = FakeDb(FakeSub())
    db.execute = AsyncMock(side_effect=RuntimeError("db down too"))

    await _send_recovery_email(request, db, USER_ID)  # must not raise


# ── Cancel reason, feedback, and the 14-day feature window ───────────────────

@pytest.mark.parametrize("stripe_reason,expected", [
    ("payment_failed", "payment_failed"),
    ("payment_disputed", "payment_failed"),   # a dispute and a decline are one story
    ("cancellation_requested", "user_requested"),
    ("something_new_stripe_added", "other"),
    (None, "other"),
])
def test_the_cancel_reason_mapping(client, stripe_reason, expected):
    sub = FakeSub(plan="pro", status="active", pro_since=NOW - timedelta(days=10))
    client._db[0] = FakeDb(sub)
    details = {"reason": stripe_reason} if stripe_reason else {}

    _, analytics = _post(client, _deleted_event(details))

    assert analytics.track.call_args[0][2]["reason"] == expected


def test_a_deleted_event_with_no_cancellation_details_maps_to_other(client):
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub)

    _, analytics = _post(client, _deleted_event(None))

    assert analytics.track.call_args[0][2]["reason"] == "other"


def test_the_feedback_enum_is_passed_through(client):
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub)

    _, analytics = _post(client, _deleted_event(
        {"reason": "cancellation_requested", "feedback": "too_expensive"},
    ))

    assert analytics.track.call_args[0][2]["cancel_feedback"] == "too_expensive"


def test_feedback_is_none_when_absent(client):
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub)

    _, analytics = _post(client, _deleted_event({"reason": "payment_failed"}))

    assert analytics.track.call_args[0][2]["cancel_feedback"] is None


def test_the_free_text_comment_is_never_read(client):
    """cancellation_details.comment is text the customer typed, and it sits one
    attribute away from `reason`. Nothing in the props may be derived from it."""
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub)
    secret = "I am cancelling because my colleague Dana said it was rubbish"

    _, analytics = _post(client, _deleted_event({
        "reason": "cancellation_requested",
        "feedback": "low_quality",
        "comment": secret,
    }))

    props = analytics.track.call_args[0][2]
    assert "comment" not in props
    blob = repr(props)
    assert secret not in blob
    assert "Dana" not in blob
    assert "rubbish" not in blob


def test_last_14d_features_is_sorted_and_only_the_features_present(client):
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub, features_present={"council", "chat", "letter"})

    _, analytics = _post(client, _deleted_event({"reason": "payment_failed"}))

    assert analytics.track.call_args[0][2]["last_14d_features"] == [
        "chat", "council", "letter",
    ]


def test_an_empty_feature_list_is_a_real_answer(client):
    """A cancel having used nothing is the most actionable churn signal there
    is, and it must never be confused with a failure to look."""
    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub, features_present=set())

    _, analytics = _post(client, _deleted_event({"reason": "payment_failed"}))

    assert analytics.track.call_args[0][2]["last_14d_features"] == []


def test_the_feature_values_come_only_from_the_fixed_vocabulary(client):
    """THE LEAK GUARD for a list-valued property. The AST value check cannot see
    inside a list at runtime, so nothing else stops a future edit putting user
    content in here."""
    from routers.billing import FEATURE_VOCABULARY

    sub = FakeSub(plan="pro", status="active")
    client._db[0] = FakeDb(sub, features_present=set(_FEATURE_TABLES))

    _, analytics = _post(client, _deleted_event({"reason": "payment_failed"}))

    values = analytics.track.call_args[0][2]["last_14d_features"]
    assert set(values) <= set(FEATURE_VOCABULARY)
    assert values == sorted(values)
    for v in values:
        assert v.islower() and " " not in v and len(v) <= 32


def test_the_test_table_map_matches_the_implementation():
    """Guard on the guard: if _feature_sources gains a feature and this file's
    _FEATURE_TABLES does not, the probe stub silently answers None for it and
    every feature test above would keep passing while covering less."""
    from routers.billing import _feature_sources, FEATURE_VOCABULARY

    keys = {k for k, _m, _t, _e in _feature_sources()}
    assert keys == set(_FEATURE_TABLES)
    assert keys == set(FEATURE_VOCABULARY)


# ── E. Lifecycle history ─────────────────────────────────────────────────────

def test_a_history_row_is_written_with_the_before_and_after(client):
    sub = FakeSub(plan="free", status="incomplete", interval=None)
    db = FakeDb(sub)
    client._db[0] = db

    _post(client, _event("customer.subscription.updated", _sub_obj(interval="year")))

    rows = db.history()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == USER_ID
    assert row.subscription_id == SUB_ROW_ID
    assert row.stripe_event_id == "evt_1"
    assert row.event_type == "customer.subscription.updated"
    # Captured BEFORE the mutation — this is what makes the row worth having.
    assert row.from_plan == "free"
    assert row.to_plan == "pro"
    assert row.from_status == "incomplete"
    assert row.to_status == "active"
    assert row.interval == "year"


def test_the_cancel_transition_is_recorded(client):
    sub = FakeSub(plan="pro", status="active", pro_since=NOW - timedelta(days=5))
    db = FakeDb(sub)
    client._db[0] = db

    _post(client, _event(
        "customer.subscription.deleted",
        {"id": SUB_ID, "customer": CUSTOMER_ID, "status": "canceled"},
    ))

    row = db.history()[0]
    assert row.from_plan == "pro"
    assert row.to_plan == "free"
    assert row.from_status == "active"
    assert row.to_status == "canceled"


def test_the_past_due_transition_is_recorded(client):
    sub = FakeSub(plan="pro", status="active")
    db = FakeDb(sub)
    client._db[0] = db

    _post(client, _event("invoice.payment_failed", {"subscription": SUB_ID}))

    row = db.history()[0]
    assert row.from_status == "active"
    assert row.to_status == "past_due"


def test_an_unknown_event_type_is_recorded_and_changes_nothing(client):
    sub = FakeSub(plan="pro", status="active")
    db = FakeDb(sub)
    client._db[0] = db

    resp, analytics = _post(client, _event("customer.discount.created", {"id": "di_1"}))

    assert resp.status_code == 200
    assert db.history() == []
    analytics.track.assert_not_called()
    # Still recorded, so a retry of it is also a no-op.
    assert len(db.stripe_events()) == 1
