"""
send_payment_recovery_email_task — the dunning email actually sends.

#584 (2026-09-02) shipped this task calling select() without importing it. The
task's own try/except caught the NameError and logged "Payment recovery email
FAILED", so nothing raised and no email went out on the queue path — which is
the production path (main.py puts the ARQ queue on app.state). The router tests
mock the enqueue and the synchronous fallback, so none of them ran this body.

The assertions are on send_email being called AND on no error being logged,
because the task never raises: a regression here is only visible as a log line.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

USER_ID = "00000000-0000-0000-0000-00000000d0e5"


def _db_for(user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return db


async def _run(user):
    from workers.arq_worker import send_payment_recovery_email_task

    # PATCH TARGETS: the task imports AsyncSessionLocal and send_email inside
    # its body, so patch their home modules, not workers.arq_worker.
    with (
        patch("db.session.AsyncSessionLocal", return_value=_db_for(user)),
        patch("services.email_service.send_email") as send,
        patch("workers.arq_worker.logger") as m_logger,
    ):
        await send_payment_recovery_email_task({}, USER_ID)
    return send, m_logger


@pytest.mark.asyncio
async def test_a_failed_payment_sends_the_recovery_email():
    user = MagicMock()
    user.email = "past-due@example.test"

    send, m_logger = await _run(user)

    assert not m_logger.error.called, m_logger.error.call_args
    send.assert_called_once()
    assert send.call_args.kwargs["to"] == "past-due@example.test"
    assert "/app/account" in send.call_args.kwargs["html"]


@pytest.mark.asyncio
async def test_a_user_without_an_email_is_logged_not_sent():
    user = MagicMock()
    user.email = None

    send, m_logger = await _run(user)

    send.assert_not_called()
    assert m_logger.error.call_args.args[0] == "Payment recovery email: no user/email for %s"
