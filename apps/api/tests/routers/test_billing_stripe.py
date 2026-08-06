"""Tests for the Stripe-facing billing paths: /billing/checkout, /billing/portal
and the checkout.session.completed webhook handler.

These are the two defects that only surface when live keys are installed:
  1. stale test-mode stripe_customer_id → InvalidRequestError → 500 for every
     pre-existing user. _resolve_customer_id heals the row instead.
  2. checkout.session.completed granting plan=pro with a NULL current_period_end,
     which tier_service reads as "manual comp grant, no expiry".

Uses FastAPI TestClient with dependency overrides for DB and auth, matching
tests/routers/test_saved_lines.py. Stripe is patched at the router module level.

Run: cd apps/api && pytest tests/routers/test_billing_stripe.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import stripe
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

USER_ID     = "aaaaaaaa-0000-0000-0000-000000000001"
USER_EMAIL  = "seeker@example.com"
STALE_CID   = "cus_test_mode_stale"
NEW_CID     = "cus_live_mode_new"
SUB_ID      = "sub_live_123"
PRICE_PRO   = "price_pro_monthly_test"

CHECKOUT_URL = "/api/v1/billing/checkout"
PORTAL_URL   = "/api/v1/billing/portal"
WEBHOOK_URL  = "/api/v1/billing/webhook"

# Period end 30 days out, as Stripe would report it.
PERIOD_END_TS = int(datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc).timestamp())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user():
    u = MagicMock()
    u.id = USER_ID
    u.email = USER_EMAIL
    u.is_admin = False
    return u


def _make_sub(customer_id=STALE_CID):
    """A Subscription row stand-in. Plain object (not MagicMock) for the mutated
    fields so assertions read real values rather than auto-created attributes."""
    s = MagicMock()
    s.user_id = USER_ID
    s.stripe_customer_id = customer_id
    s.stripe_subscription_id = None
    s.plan = "free"
    s.status = "incomplete"
    s.current_period_end = None
    s.cancel_at_period_end = False
    return s


def _db_returning(sub):
    """AsyncSession mock whose execute() always resolves to `sub`."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sub
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


def _stripe_subscription(status="active", price_id=PRICE_PRO, period_end=PERIOD_END_TS):
    """Shape of stripe.Subscription.retrieve() — a dict-like StripeObject."""
    return {
        "id": SUB_ID,
        "status": status,
        "cancel_at_period_end": False,
        "items": {"data": [{"price": {"id": price_id}, "current_period_end": period_end}]},
    }


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db_holder = [_db_returning(_make_sub())]
    user_holder = [_make_user()]

    async def override_db():
        yield db_holder[0]

    async def override_user():
        return user_holder[0]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    tc = TestClient(app, raise_server_exceptions=True)
    tc._db = db_holder
    tc._user = user_holder

    yield tc

    app.dependency_overrides.clear()


# ── /billing/checkout — self-healing customer id ─────────────────────────────

def test_checkout_heals_stale_customer_id(client):
    """Stale test-mode id → Stripe 'no such customer' → new customer created,
    persisted on the row, and checkout proceeds with the NEW id."""
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    not_found = stripe.error.InvalidRequestError("No such customer", "customer")
    session = MagicMock()
    session.url = "https://checkout.stripe.test/session"

    with (
        patch.dict("routers.billing.PLANS", {"pro_monthly": PRICE_PRO}, clear=False),
        patch("routers.billing.stripe.Customer.retrieve", side_effect=not_found) as m_retrieve,
        patch("routers.billing.stripe.Customer.create", return_value=MagicMock(id=NEW_CID)) as m_create,
        patch("routers.billing.stripe.checkout.Session.create", return_value=session) as m_session,
    ):
        resp = client.post(CHECKOUT_URL, json={"plan": "pro", "interval": "monthly"})

    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://checkout.stripe.test/session"

    m_retrieve.assert_called_once_with(STALE_CID)
    m_create.assert_called_once_with(email=USER_EMAIL)

    # Row healed and committed…
    assert sub.stripe_customer_id == NEW_CID
    client._db[0].commit.assert_awaited()
    # …and the checkout used the new id, not the stale one.
    assert m_session.call_args.kwargs["customer"] == NEW_CID


def test_checkout_creates_customer_when_id_is_null(client):
    """Defensive path: the schema has stripe_customer_id NOT NULL, so this state
    cannot currently exist in the database. Covered anyway because the same branch
    guards an empty string and a future migration relaxing the column."""
    sub = _make_sub(customer_id=None)
    client._db[0] = _db_returning(sub)

    session = MagicMock()
    session.url = "https://checkout.stripe.test/session"

    with (
        patch.dict("routers.billing.PLANS", {"pro_monthly": PRICE_PRO}, clear=False),
        patch("routers.billing.stripe.Customer.retrieve") as m_retrieve,
        patch("routers.billing.stripe.Customer.create", return_value=MagicMock(id=NEW_CID)) as m_create,
        patch("routers.billing.stripe.checkout.Session.create", return_value=session),
    ):
        resp = client.post(CHECKOUT_URL, json={"plan": "pro", "interval": "monthly"})

    assert resp.status_code == 200
    m_retrieve.assert_not_called()          # nothing to verify
    m_create.assert_called_once_with(email=USER_EMAIL)
    assert sub.stripe_customer_id == NEW_CID


def test_checkout_other_stripe_error_is_502_and_creates_nothing(client):
    """A non-'not found' Stripe failure must surface as 502 — never a silent
    fallthrough that creates a duplicate customer."""
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    boom = stripe.error.APIConnectionError("Stripe is unreachable")

    with (
        patch.dict("routers.billing.PLANS", {"pro_monthly": PRICE_PRO}, clear=False),
        patch("routers.billing.stripe.Customer.retrieve", side_effect=boom),
        patch("routers.billing.stripe.Customer.create") as m_create,
        patch("routers.billing.stripe.checkout.Session.create") as m_session,
    ):
        resp = client.post(CHECKOUT_URL, json={"plan": "pro", "interval": "monthly"})

    assert resp.status_code == 502
    m_create.assert_not_called()
    m_session.assert_not_called()
    assert sub.stripe_customer_id == STALE_CID   # untouched


def test_checkout_keeps_valid_customer_id(client):
    """The healthy case: a live id verifies, so no customer is created."""
    sub = _make_sub(customer_id=NEW_CID)
    client._db[0] = _db_returning(sub)

    session = MagicMock()
    session.url = "https://checkout.stripe.test/session"

    with (
        patch.dict("routers.billing.PLANS", {"pro_monthly": PRICE_PRO}, clear=False),
        patch("routers.billing.stripe.Customer.retrieve", return_value=MagicMock(deleted=False)),
        patch("routers.billing.stripe.Customer.create") as m_create,
        patch("routers.billing.stripe.checkout.Session.create", return_value=session) as m_session,
    ):
        resp = client.post(CHECKOUT_URL, json={"plan": "pro", "interval": "monthly"})

    assert resp.status_code == 200
    m_create.assert_not_called()
    assert m_session.call_args.kwargs["customer"] == NEW_CID


# ── /billing/portal — same healing ───────────────────────────────────────────

def test_portal_heals_stale_customer_id(client):
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    not_found = stripe.error.InvalidRequestError("No such customer", "customer")
    session = MagicMock()
    session.url = "https://portal.stripe.test/session"

    with (
        patch("routers.billing.stripe.Customer.retrieve", side_effect=not_found),
        patch("routers.billing.stripe.Customer.create", return_value=MagicMock(id=NEW_CID)),
        patch("routers.billing.stripe.billing_portal.Session.create", return_value=session) as m_portal,
    ):
        resp = client.post(PORTAL_URL)

    assert resp.status_code == 200
    assert sub.stripe_customer_id == NEW_CID
    assert m_portal.call_args.kwargs["customer"] == NEW_CID


# ── webhook: checkout.session.completed must set an expiry ───────────────────

def _completed_event():
    return {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": STALE_CID, "subscription": SUB_ID}},
    }


def test_completed_populates_period_end_from_retrieved_subscription(client):
    """The Defect-2 regression: plan/status/current_period_end all come from the
    retrieved subscription, so Pro is never granted without an expiry."""
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    with (
        patch("routers.billing.stripe.Webhook.construct_event", return_value=_completed_event()),
        patch("routers.billing.config.STRIPE_PRICE_PRO_MONTHLY", PRICE_PRO),
        patch("routers.billing.stripe.Subscription.retrieve", return_value=_stripe_subscription()) as m_ret,
    ):
        resp = client.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert resp.status_code == 200
    m_ret.assert_called_once_with(SUB_ID)

    assert sub.stripe_subscription_id == SUB_ID
    assert sub.plan == "pro"
    assert sub.status == "active"
    assert sub.cancel_at_period_end is False
    # The whole point: an actual expiry, not NULL.
    assert sub.current_period_end is not None
    assert sub.current_period_end == datetime.fromtimestamp(PERIOD_END_TS, tz=timezone.utc)


def test_completed_leaves_grant_untouched_when_retrieve_fails(client):
    """Retrieve fails → plan/status/period stay as they were and the error is
    logged. customer.subscription.created will grant later; a delayed grant is
    safer than a permanent one."""
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    boom = stripe.error.APIConnectionError("Stripe is unreachable")

    with (
        patch("routers.billing.stripe.Webhook.construct_event", return_value=_completed_event()),
        patch("routers.billing.stripe.Subscription.retrieve", side_effect=boom),
        patch("routers.billing.logger") as m_logger,
    ):
        resp = client.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert resp.status_code == 200
    assert sub.plan == "free"
    assert sub.status == "incomplete"
    assert sub.current_period_end is None
    # The linkage id is still recorded — it is not a grant, and the reconcile
    # cron and invoice.* handlers need it to find this row.
    assert sub.stripe_subscription_id == SUB_ID
    m_logger.error.assert_called_once()


def test_completed_does_not_grant_when_session_has_no_subscription(client):
    """No subscription on the session → nothing to retrieve, nothing granted."""
    sub = _make_sub(customer_id=STALE_CID)
    client._db[0] = _db_returning(sub)

    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": STALE_CID, "subscription": None}},
    }

    with (
        patch("routers.billing.stripe.Webhook.construct_event", return_value=event),
        patch("routers.billing.stripe.Subscription.retrieve") as m_ret,
    ):
        resp = client.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert resp.status_code == 200
    m_ret.assert_not_called()
    assert sub.plan == "free"
    assert sub.current_period_end is None
