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
