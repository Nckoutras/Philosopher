"""Tests for the send_pending_future_self_emails cron function.

Extracts the inner async function from setup_cron and exercises it directly
with a mocked DB session and patched email_service.send_email.

Run: cd apps/api && pytest tests/services/test_cron_pending_emails.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call


PERSONA_ID = "dddddddd-0000-0000-0000-000000000001"
LINE_ID    = "eeeeeeee-0000-0000-0000-000000000001"
EMAIL_ID   = "ffffffff-0000-0000-0000-000000000001"
EMAIL_ID_2 = "ffffffff-0000-0000-0000-000000000002"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_persona():
    p = MagicMock()
    p.id = PERSONA_ID
    p.name = "Marcus Aurelius"
    p.portrait_url = "/portraits/marcus.jpg"
    return p


def _make_pending_row(email_id=EMAIL_ID, saved_line_id=LINE_ID):
    row = MagicMock()
    row.id = email_id
    row.persona_id = PERSONA_ID
    row.saved_line_id = saved_line_id
    row.note = "Stay curious."
    row.recipient_email = "user@example.com"
    row.scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=1)
    row.status = "pending"
    row.sent_at = None
    row.failure_reason = None
    return row


# ── Extract the cron function from setup_cron ─────────────────────────────────

def _get_cron_fn():
    """
    Calls setup_cron with a dummy arq_queue and captures the registered job
    function 'send_pending_future_self_emails' from APScheduler.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from workers.cron import setup_cron, shutdown_cron

    dummy_queue = MagicMock()
    scheduler = AsyncIOScheduler()

    # Monkeypatch the module-level scheduler so setup_cron registers against it
    import workers.cron as cron_mod
    original_scheduler = cron_mod.scheduler
    cron_mod.scheduler = scheduler

    try:
        setup_cron(dummy_queue)
        job = scheduler.get_job("future_self_emails")
        fn = job.func
        scheduler.shutdown(wait=False)
    finally:
        cron_mod.scheduler = original_scheduler
        cron_mod.shutdown_cron()

    return fn


# ── The outbound-link precondition (TD-77) ────────────────────────────────────

@pytest.fixture(autouse=True)
def deliverable_frontend_url(monkeypatch):
    """Every test below this line needs a REAL FRONTEND_URL, and did not used to.

    TD-77 added a guard: this job now refuses to send when FRONTEND_URL is a
    localhost/empty placeholder, because the arrival link it carries would be
    dead. The four send-path tests in this file were written before that guard
    and ran on the localhost DEFAULT — so without this fixture they now exercise
    the suppression path and fail, correctly, for a reason that has nothing to do
    with what they assert.

    Autouse so the precondition is stated once rather than copied into each test,
    and the guard's own tests below override it explicitly.
    """
    monkeypatch.setattr("workers.cron.config.FRONTEND_URL", "https://thewiseroom.app")


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sends_due_email_marks_sent(monkeypatch):
    row = _make_pending_row()
    persona = _make_persona()

    db = AsyncMock()
    db.get = AsyncMock(return_value=persona)

    # Message content from saved line join
    msg_result = MagicMock()
    msg_result.scalar_one_or_none.return_value = "You have power over your mind."
    db.execute = AsyncMock(return_value=msg_result)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    # Scalars chain for pending query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [row]
    pending_result = MagicMock()
    pending_result.scalars.return_value = scalars_mock

    call_count = [0]

    async def fake_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return pending_result   # first call: pending query
        return msg_result           # second call: message content

    db.execute = fake_execute

    fake_send = MagicMock()

    monkeypatch.setattr("workers.cron.config.PUBLIC_ASSET_BASE_URL", "https://test.example.com")

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", fake_send),
        patch("workers.cron.render_future_self_email", return_value="<html>test</html>"),
    ):
        fn = _get_cron_fn()
        await fn()

    assert row.status == "sent"
    assert row.sent_at is not None
    fake_send.assert_called_once()
    call_args = fake_send.call_args
    assert call_args.kwargs["to"] == "user@example.com"
    assert "Marcus Aurelius" in call_args.kwargs["subject"]


@pytest.mark.asyncio
async def test_skips_future_email(monkeypatch):
    row = _make_pending_row()
    row.scheduled_for = datetime.now(timezone.utc) + timedelta(hours=2)  # future
    row.status = "pending"

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []   # future rows excluded by WHERE clause

    pending_result = MagicMock()
    pending_result.scalars.return_value = scalars_mock

    db = AsyncMock()
    db.execute = AsyncMock(return_value=pending_result)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    fake_send = MagicMock()

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", fake_send),
    ):
        fn = _get_cron_fn()
        await fn()

    fake_send.assert_not_called()
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_marks_failed_on_send_error(monkeypatch):
    row = _make_pending_row()
    persona = _make_persona()

    call_count = [0]

    async def fake_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [row]
            result = MagicMock()
            result.scalars.return_value = scalars_mock
            return result
        msg_result = MagicMock()
        msg_result.scalar_one_or_none.return_value = "Some quote."
        return msg_result

    db = AsyncMock()
    db.get = AsyncMock(return_value=persona)
    db.execute = fake_execute
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr("workers.cron.config.PUBLIC_ASSET_BASE_URL", "https://test.example.com")

    def exploding_send(**kwargs):
        raise Exception("Resend API unavailable")

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", exploding_send),
        patch("workers.cron.render_future_self_email", return_value="<html></html>"),
    ):
        fn = _get_cron_fn()
        await fn()

    assert row.status == "failed"
    assert "Resend API unavailable" in row.failure_reason


@pytest.mark.asyncio
async def test_failure_does_not_block_next_row(monkeypatch):
    row1 = _make_pending_row(email_id=EMAIL_ID)
    row2 = _make_pending_row(email_id=EMAIL_ID_2)
    persona = _make_persona()

    call_count = [0]

    async def fake_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [row1, row2]
            result = MagicMock()
            result.scalars.return_value = scalars_mock
            return result
        msg_result = MagicMock()
        msg_result.scalar_one_or_none.return_value = "Some quote."
        return msg_result

    db = AsyncMock()
    db.get = AsyncMock(return_value=persona)
    db.execute = fake_execute
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    send_call_count = [0]

    def sometimes_fail(**kwargs):
        send_call_count[0] += 1
        if send_call_count[0] == 1:
            raise Exception("first send failed")

    monkeypatch.setattr("workers.cron.config.PUBLIC_ASSET_BASE_URL", "https://test.example.com")

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", sometimes_fail),
        patch("workers.cron.render_future_self_email", return_value="<html></html>"),
    ):
        fn = _get_cron_fn()
        await fn()

    assert row1.status == "failed"
    assert row2.status == "sent"


@pytest.mark.asyncio
async def test_null_saved_line_sends_without_quote(monkeypatch):
    row = _make_pending_row(saved_line_id=None)
    row.saved_line_id = None
    persona = _make_persona()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [row]
    pending_result = MagicMock()
    pending_result.scalars.return_value = scalars_mock

    db = AsyncMock()
    db.get = AsyncMock(return_value=persona)
    db.execute = AsyncMock(return_value=pending_result)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    render_calls = []

    def capture_render(**kwargs):
        render_calls.append(kwargs)
        return "<html></html>"

    fake_send = MagicMock()
    monkeypatch.setattr("workers.cron.config.PUBLIC_ASSET_BASE_URL", "https://test.example.com")

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", fake_send),
        patch("workers.cron.render_future_self_email", capture_render),
    ):
        fn = _get_cron_fn()
        await fn()

    assert row.status == "sent"
    assert len(render_calls) == 1
    assert render_calls[0]["quote_content"] is None
    fake_send.assert_called_once()


# ── The guard itself (TD-77) ──────────────────────────────────────────────────
#
# WHAT WAS WRONG. This email exists to carry ONE link — back to the arrival
# screen. It built that link from FRONTEND_URL (default http://localhost:3000)
# and had no guard at all: it sent anyway and set status='sent'. A real reader
# got a dead appointment and the row recorded success. The weekly letter has
# refused the same misconfiguration since it shipped; the two now share one rule.
#
# THE DIVERGENCE FROM THE LETTER IS DELIBERATE and is pinned below. A suppressed
# letter is TERMINAL, because the letter still exists and is readable in-app —
# only a notification was lost. Here the delivery IS the artefact: somebody asked
# for this to come back to them. So the row stays 'pending' and goes out on the
# next run once the config is fixed, rather than being marked 'failed' and lost.

def _guard_db(rows):
    """The pending-query half of the harness above. The guard returns before any
    second query, so this deliberately does not model the message-content call."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    pending_result = MagicMock()
    pending_result.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=pending_result)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("placeholder", [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "",            # explicitly unset: builds a RELATIVE link, dead in mail, and
                   # containing no "localhost" for a substring test to catch
])
async def test_a_placeholder_frontend_url_sends_nothing(monkeypatch, placeholder):
    """The defect, in one assertion: nothing leaves the building."""
    monkeypatch.setattr("workers.cron.config.FRONTEND_URL", placeholder)
    row = _make_pending_row()
    fake_send = MagicMock()

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=_guard_db([row])),
        patch("workers.cron.send_email", fake_send),
        patch("workers.cron.render_future_self_email", return_value="<html/>"),
    ):
        await _get_cron_fn()()

    fake_send.assert_not_called()


@pytest.mark.asyncio
async def test_suppressed_rows_stay_pending_with_a_reason(monkeypatch):
    """NOT 'sent' — that was the bug, a success record for a failure. NOT
    'failed' either: an ops mistake must not destroy a kept appointment."""
    monkeypatch.setattr("workers.cron.config.FRONTEND_URL", "http://localhost:3000")
    rows = [_make_pending_row(), _make_pending_row()]
    db = _guard_db(rows)

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=db),
        patch("workers.cron.send_email", MagicMock()),
        patch("workers.cron.render_future_self_email", return_value="<html/>"),
    ):
        await _get_cron_fn()()

    assert [r.status for r in rows] == ["pending", "pending"]
    assert [r.sent_at for r in rows] == [None, None]
    assert [r.failure_reason for r in rows] == ["frontend_url_unset"] * 2
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_it_logs_once_per_run_not_once_per_row(monkeypatch, caplog):
    """Process config, not row state. This job runs every five minutes, so fifty
    identical ERROR lines per run would bury the one fact an operator needs."""
    monkeypatch.setattr("workers.cron.config.FRONTEND_URL", "http://localhost:3000")
    rows = [_make_pending_row() for _ in range(10)]

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=_guard_db(rows)),
        patch("workers.cron.send_email", MagicMock()),
        patch("workers.cron.render_future_self_email", return_value="<html/>"),
        caplog.at_level("ERROR"),
    ):
        await _get_cron_fn()()

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1, f"expected one ERROR for the run, got {len(errors)}"
    assert "FRONTEND_URL" in errors[0].getMessage()


@pytest.mark.asyncio
async def test_an_idle_run_on_a_broken_config_stays_quiet(monkeypatch, caplog):
    """The guard keys on there BEING something due, so a misconfigured but idle
    deployment does not page anyone every five minutes forever."""
    monkeypatch.setattr("workers.cron.config.FRONTEND_URL", "http://localhost:3000")

    with (
        patch("workers.cron.AsyncSessionLocal", return_value=_guard_db([])),
        patch("workers.cron.send_email", MagicMock()),
        patch("workers.cron.render_future_self_email", return_value="<html/>"),
        caplog.at_level("ERROR"),
    ):
        await _get_cron_fn()()

    assert [r for r in caplog.records if r.levelname == "ERROR"] == []
