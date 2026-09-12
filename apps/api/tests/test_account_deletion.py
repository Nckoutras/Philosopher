"""Account deletion — the order, the abort, and the anonymisation.

WHY THIS FILE EXISTS. Three claims hold this feature up and none is visible at
the call site:

  1. "Stripe is cancelled before anything is deleted." If that inverts, a person
     who no longer has an account keeps being charged by a subscription no row
     points at any more. It is the one unrecoverable outcome here, so the order
     is asserted directly rather than inferred from the code reading correctly.

  2. "A Stripe failure deletes nothing." Not "rolls back" — never runs.

  3. "safety_events survive, anonymised, and that is lawful because raw_flags
     holds no user text." The third clause is a property of safety_service, not
     of this module, and it is what makes retaining these rows Art. 17-safe. If
     someone later stores a matched excerpt there, anonymised rows quietly
     become personal data retained forever. test_raw_flags_* pins it.

Real objects over MagicMock where a write must be observable — a MagicMock
absorbs an attribute write and still answers every read, which would make
"was this deleted?" unassertable (CLAUDE.md C-06).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.account_deletion_service import (
    BILLABLE_STATUSES,
    DELETED_DISTINCT_ID,
    StripeCancelFailed,
    _anonymise_safety_events,
    _cancel_stripe_subscription,
    delete_account,
)


class FakeSubscription:
    """Plain object, not a Mock: `status` and `stripe_subscription_id` drive
    branch conditions, and a Mock satisfies neither `in` nor `not`."""

    def __init__(self, *, status="active", stripe_subscription_id="sub_123", pro_since=None):
        self.status = status
        self.stripe_subscription_id = stripe_subscription_id
        self.pro_since = pro_since


class FakeUser:
    def __init__(self, user_id="u1", email="someone@example.com"):
        self.id = user_id
        # Read by _delete_otp_codes. Set explicitly (C-06): a MagicMock would
        # have supplied it silently, and the resulting WHERE email = <Mock>
        # would match no rows, commit cleanly, and pass.
        self.email = email


def _db_returning(sub, *, anonymised_rows=0, otp_rows=0):
    """An AsyncSession whose execute() answers by statement shape.

    Index-based dispatch is what made 17 tests in this repo fail for months
    (TD-45); this dispatches on what the statement IS.

    DELETE answers a rowcount because _delete_otp_codes reads one. A bare
    MagicMock would return a Mock there, which `or 0` accepts and then logs as a
    count — so the branch exists to keep the deleted-row number a number.
    """
    db = MagicMock()
    db.commit = AsyncMock()

    async def execute(stmt, *a, **kw):
        text = str(stmt)
        result = MagicMock()
        if text.startswith("SELECT"):
            result.scalar_one_or_none.return_value = sub
        elif text.startswith("UPDATE"):
            result.fetchall.return_value = [("id",)] * anonymised_rows
        elif text.startswith("DELETE FROM otp_codes"):
            result.rowcount = otp_rows
        return result

    db.execute = AsyncMock(side_effect=execute)
    return db


# ── Stripe cancel ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", sorted(BILLABLE_STATUSES))
async def test_a_billable_subscription_is_cancelled(status):
    db = _db_returning(FakeSubscription(status=status))
    with patch("stripe.Subscription.cancel") as cancel:
        assert await _cancel_stripe_subscription(db, "u1") is True
    cancel.assert_called_once_with("sub_123")


@pytest.mark.parametrize("status", ["canceled", "incomplete_expired"])
async def test_a_terminal_subscription_is_not_cancelled(status):
    db = _db_returning(FakeSubscription(status=status))
    with patch("stripe.Subscription.cancel") as cancel:
        assert await _cancel_stripe_subscription(db, "u1") is False
    cancel.assert_not_called()


async def test_no_subscription_row_is_not_an_error():
    db = _db_returning(None)
    with patch("stripe.Subscription.cancel") as cancel:
        assert await _cancel_stripe_subscription(db, "u1") is False
    cancel.assert_not_called()


async def test_a_free_row_with_no_stripe_id_is_skipped():
    db = _db_returning(FakeSubscription(stripe_subscription_id=None))
    with patch("stripe.Subscription.cancel") as cancel:
        assert await _cancel_stripe_subscription(db, "u1") is False
    cancel.assert_not_called()


async def test_a_stripe_failure_raises_rather_than_swallowing():
    db = _db_returning(FakeSubscription())
    with patch("stripe.Subscription.cancel", side_effect=Exception("card network down")):
        with pytest.raises(StripeCancelFailed):
            await _cancel_stripe_subscription(db, "u1")


# ── The abort: nothing is deleted when Stripe refuses ─────────────────────────

async def test_a_stripe_failure_deletes_nothing():
    """The claim is NOT 'it rolls back'. The DELETE never runs and nothing commits."""
    db = _db_returning(FakeSubscription())
    with patch("stripe.Subscription.cancel", side_effect=Exception("boom")):
        with pytest.raises(StripeCancelFailed):
            await delete_account(db, FakeUser(), plan="pro")

    statements = [str(c.args[0]) for c in db.execute.await_args_list]
    assert not any(s.startswith("DELETE") for s in statements), statements
    assert not any(s.startswith("UPDATE") for s in statements), (
        "safety events were anonymised despite the abort"
    )
    db.commit.assert_not_awaited()


async def test_a_stripe_failure_fires_no_analytics():
    db = _db_returning(FakeSubscription())
    with patch("stripe.Subscription.cancel", side_effect=Exception("boom")), \
         patch("services.account_deletion_service.analytics_service") as analytics:
        with pytest.raises(StripeCancelFailed):
            await delete_account(db, FakeUser(), plan="pro")
    analytics.track.assert_not_called()


# ── Order and completion ──────────────────────────────────────────────────────

async def test_stripe_is_cancelled_before_the_delete():
    """Order asserted directly. Reversed, this is the unrecoverable outcome."""
    calls = []
    db = _db_returning(FakeSubscription())

    original = db.execute.side_effect

    async def track_execute(stmt, *a, **kw):
        text = str(stmt)
        if text.startswith(("DELETE", "UPDATE")):
            calls.append(text.split()[0])
        return await original(stmt, *a, **kw)

    db.execute = AsyncMock(side_effect=track_execute)

    with patch("stripe.Subscription.cancel", side_effect=lambda *_: calls.append("STRIPE")), \
         patch("services.account_deletion_service.analytics_service"):
        await delete_account(db, FakeUser(), plan="pro")

    assert calls[0] == "STRIPE", calls
    assert calls[-1] == "DELETE", calls
    assert "UPDATE" in calls, "safety events were never anonymised"


async def test_a_free_user_is_deleted_without_touching_stripe():
    db = _db_returning(None)
    with patch("stripe.Subscription.cancel") as cancel, \
         patch("services.account_deletion_service.analytics_service"):
        summary = await delete_account(db, FakeUser(), plan="free")
    cancel.assert_not_called()
    assert summary["had_active_subscription"] is False
    assert any(str(c.args[0]).startswith("DELETE") for c in db.execute.await_args_list)
    db.commit.assert_awaited()


async def test_safety_events_are_anonymised_not_deleted():
    db = _db_returning(None, anonymised_rows=3)
    assert await _anonymise_safety_events(db, "u1") == 3
    stmt = str(db.execute.await_args_list[0].args[0])
    assert stmt.startswith("UPDATE safety_events"), stmt
    assert "DELETE" not in stmt


# ── Analytics ─────────────────────────────────────────────────────────────────

async def test_the_event_is_not_attributed_to_the_deleted_user():
    """distinct_id is the literal 'deleted_account'. Sending the real id would
    undo, in a new analytics record, the erasure the event reports."""
    db = _db_returning(None)
    with patch("services.account_deletion_service.analytics_service") as analytics:
        await delete_account(db, FakeUser(user_id="u-real-id"), plan="free")

    analytics.track.assert_called_once()
    event, distinct_id, props = analytics.track.call_args.args
    assert event == "account_deleted"
    assert distinct_id == DELETED_DISTINCT_ID == "deleted_account"
    assert "u-real-id" not in str(distinct_id)
    assert "u-real-id" not in str(props)
    assert set(props) == {"plan", "tenure_days", "had_active_subscription"}


async def test_analytics_fires_after_the_commit():
    """Best effort, and never able to block or undo a completed deletion."""
    order = []
    db = _db_returning(None)
    db.commit = AsyncMock(side_effect=lambda: order.append("COMMIT"))
    with patch("services.account_deletion_service.analytics_service") as analytics:
        analytics.track.side_effect = lambda *a, **k: order.append("TRACK")
        await delete_account(db, FakeUser(), plan="free")
    assert order == ["COMMIT", "TRACK"], order


# ── The property the anonymisation ruling depends on ──────────────────────────

async def test_raw_flags_carry_only_matcher_constants_never_user_text():
    """safety_events are RETAINED after deletion, anonymised rather than dropped.

    That is lawful only while raw_flags holds no user-authored text. Today it
    holds phrases from safety_service's own module-level constants — the matcher,
    not the match. If a future edit stores the user's sentence or a surrounding
    excerpt, retained rows silently become personal data and migration 056's
    reasoning collapses. This is the tripwire for that.
    """
    from services.safety_service import (
        OUTPUT_RISK_PHRASES, RISK_HIGH, RISK_MEDIUM, safety_service,
    )

    known = set(RISK_HIGH) | set(RISK_MEDIUM) | set(OUTPUT_RISK_PHRASES) | {
        "tired", "exhausted", "burden", "alone", "no one cares", "failure", "worthless",
    }

    secret = "my father died in April and I want to end my life"
    result = await safety_service.check_input(secret)

    assert result.trigger is None or result.trigger in known, (
        f"trigger {result.trigger!r} is not a matcher constant — it may be user text"
    )
    for flag in result.raw_flags:
        assert flag in known, f"raw_flag {flag!r} is not a matcher constant"
    # The decisive assertion: the user's own words never appear.
    assert "my father died in April" not in str(result.raw_flags)
    assert "my father died in April" not in str(result.trigger)


async def test_raw_flags_carry_only_matcher_constants_on_output_checks():
    from services.safety_service import OUTPUT_RISK_PHRASES, safety_service

    reply = "Here is the least painful way to do it, and my private notes about you."
    result = await safety_service.check_output(reply)
    for flag in result.raw_flags:
        assert flag in set(OUTPUT_RISK_PHRASES), flag
    assert "my private notes about you" not in str(result.raw_flags)


# ── otp_codes: the table the cascade cannot see (TD-72) ──────────────────────
#
# otp_codes carries no user_id, so migration 056 could not give it an ON DELETE
# clause and `DELETE FROM users` leaves it alone. The rows hold the person's
# email address, so before this it survived a deletion the privacy policy
# promises is total. These pin the explicit delete that closes it.

async def test_the_deletion_reaches_otp_codes_by_email():
    db = _db_returning(None, otp_rows=3)

    summary = await delete_account(db, FakeUser(email="someone@example.com"), plan="free")

    statements = [str(c.args[0]) for c in db.execute.await_args_list]
    assert any(s.startswith("DELETE FROM otp_codes") for s in statements), statements
    assert summary["otp_codes_deleted"] == 3


async def test_the_otp_delete_filters_on_email_not_user_id():
    """The whole point: this table has no user_id to filter on. A delete written
    against user_id would compile, match nothing, and leave the address behind."""
    db = _db_returning(None, otp_rows=1)

    await delete_account(db, FakeUser(), plan="free")

    stmt = next(
        s for s in (str(c.args[0]) for c in db.execute.await_args_list)
        if s.startswith("DELETE FROM otp_codes")
    )
    assert "otp_codes.email" in stmt, stmt
    assert "user_id" not in stmt, stmt


async def test_a_user_with_no_otp_rows_is_a_clean_no_op():
    """Every OAuth-only account. Zero rows is the ordinary case, not an error."""
    db = _db_returning(None, otp_rows=0)

    summary = await delete_account(db, FakeUser(), plan="free")

    assert summary["otp_codes_deleted"] == 0
    assert summary["had_active_subscription"] is False


async def test_the_otp_delete_runs_after_the_stripe_cancel():
    """Placement, asserted positively rather than left to the abort test alone.

    test_a_stripe_failure_deletes_nothing already fails if this runs early, which
    makes it a free ordering check — but it fails for a reason a reader has to
    infer. This says the order out loud."""
    db = _db_returning(FakeSubscription())
    order: list[str] = []

    original = db.execute.side_effect

    async def track_execute(stmt, *a, **kw):
        text = str(stmt)
        if text.startswith("DELETE FROM otp_codes"):
            order.append("otp_delete")
        return await original(stmt, *a, **kw)

    db.execute = AsyncMock(side_effect=track_execute)

    with patch("stripe.Subscription.cancel") as cancel:
        cancel.side_effect = lambda *a, **kw: order.append("stripe_cancel")
        await delete_account(db, FakeUser(), plan="pro")

    assert order == ["stripe_cancel", "otp_delete"], order


async def test_a_stripe_failure_leaves_the_otp_rows_alone():
    """The abort guarantee, restated for this table specifically: a deletion that
    did not happen must not have destroyed the person's OTP history on the way to
    failing."""
    db = _db_returning(FakeSubscription())

    with patch("stripe.Subscription.cancel", side_effect=Exception("boom")):
        with pytest.raises(StripeCancelFailed):
            await delete_account(db, FakeUser(), plan="pro")

    statements = [str(c.args[0]) for c in db.execute.await_args_list]
    assert not any(s.startswith("DELETE FROM otp_codes") for s in statements), statements


def test_both_otp_write_paths_lower_the_email_they_store():
    """THE ASSUMPTION THE DELETE RESTS ON, asserted instead of trusted.

    _delete_otp_codes matches on exact equality. That is only correct while every
    writer stores a lowered address — otp_request and otp_verify for otp_codes,
    and the two account-creating doors for users.email. If any door stops
    lowering, the delete matches nothing, commits cleanly and reports success: a
    silent no-op that looks exactly like a working fix.

    Source-level, deliberately. The alternative is a live round-trip per door,
    and what must hold is a property of the code rather than of one request.
    """
    from pathlib import Path

    api = Path(__file__).resolve().parents[1]
    auth = (api / "routers" / "auth.py").read_text(encoding="utf-8")
    oauth = (api / "routers" / "auth_oauth.py").read_text(encoding="utf-8")

    # otp_codes writers: both handlers lower before calling into otp_service.
    assert auth.count("email = body.email.lower()") == 2, (
        "otp_request and otp_verify must each lower the address before it is "
        "stored or looked up in otp_codes"
    )
    # users.email writers: the two account-creating doors.
    assert 'userinfo.get("email", "").lower()' in oauth, (
        "the OAuth door must lower the address before creating the user"
    )
    # And neither door may write a raw address.
    assert "User(email=body.email" not in auth, auth
    assert 'User(email=userinfo' not in oauth, oauth
