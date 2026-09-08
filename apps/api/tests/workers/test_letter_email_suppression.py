"""weekly_letters.email_suppressed_reason — the five values, pinned verbatim.

THE FIRST TEST EVER WRITTEN AGAINST THE EMAIL GUARD. Until this file, nothing in
the repository imported a letter task or its helpers;
tests/workers/test_letter_write_back.py says so in its own docstring ("No
letter-generation test harness exists in this repo"). The three existing files in
this directory test pure renderers. So the guard has shipped untested — which is
part of why a suppressed email left no record of itself to begin with.

WHAT THE COLUMN IS FOR. The letter is generated and saved either way; the email
is best-effort and the helper never raises. Before 059 that meant a letter with
email_sent_at NULL and no way to tell whether the recipient opted out, the config
was wrong, or the send actually failed. Those want different responses, and two
of them are ops incidents.

WHY THE VALUES ARE PINNED HERE AND NOT IN THE SCHEMA. The column carries no CHECK
constraint, deliberately (R2a): the five reasons are an APPLICATION vocabulary, so
adding a sixth must stay a code change and never become a production migration.
The cost of that choice is that nothing in the database defends the spelling — so
this file is the defence. If you add a reason, add it here in the same commit.

FAKES, NOT MagicMock (C-06). The whole question is "was the reason written to the
letter row, and was it committed?" — and a MagicMock answers yes to that whether
or not the code did anything, because it accepts every attribute write and invents
every read. The same reasoning as the ring-true safety tests (#557).
"""
import inspect
import re

import pytest

from workers.arq_worker import _maybe_send_weekly_letter_email

# The vocabulary, written out. Not derived from the source, not derived from the
# helper — an assertion that computed its expectation from the thing under test
# could not fail. This is the independent statement of the rule.
EXPECTED_REASONS = {"localhost", "no_email", "opt_out", "already_sent", "send_failed"}


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeLetter:
    """A real object with real attributes, so an unwritten reason stays None."""

    def __init__(self, email_sent_at=None):
        self.id = "11111111-1111-1111-1111-111111111111"
        self.email_sent_at = email_sent_at
        self.email_suppressed_reason = None
        self.period_start = None


class FakeUser:
    def __init__(self, email="reader@example.test", opt_out=False):
        self.id = "22222222-2222-2222-2222-222222222222"
        self.email = email
        self.weekly_email_opt_out = opt_out


class FakePersona:
    name = "Carl Jung"
    slug = "carl_jung"


class FakeDB:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


PAYLOAD = {
    "title": "A letter",
    "opening": "o",
    "references": "r",
    "pull_quote": "q",
    "forward_gesture": "f",
}


@pytest.fixture
def sendable(monkeypatch):
    """Config that would let a send proceed, so each test isolates ONE guard."""
    from config import config

    monkeypatch.setattr(config, "API_BASE_URL", "https://api.example.test", raising=False)
    monkeypatch.setattr(config, "FRONTEND_URL", "https://app.example.test", raising=False)


async def _run(db, user, letter, persona=None):
    await _maybe_send_weekly_letter_email(
        db, user, letter, PAYLOAD, persona or FakePersona(),
    )


# ── The five reasons ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_localhost_config_is_recorded(monkeypatch):
    """A misconfigured API_BASE_URL means the unsubscribe link would be broken, so
    the send is refused. This one is an ops incident, not a user choice — and it
    used to be distinguishable only by reading the log at the right moment."""
    from config import config

    monkeypatch.setattr(config, "API_BASE_URL", "http://localhost:8000", raising=False)
    db, letter = FakeDB(), FakeLetter()

    await _run(db, FakeUser(), letter)

    assert letter.email_suppressed_reason == "localhost"
    assert letter.email_sent_at is None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_a_user_with_no_address_is_recorded(sendable):
    db, letter = FakeDB(), FakeLetter()

    await _run(db, FakeUser(email=""), letter)

    assert letter.email_suppressed_reason == "no_email"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_a_missing_user_row_is_also_no_email(sendable):
    """`user is None` shares the branch. The letter row is still available, so the
    reason is still recordable — which is the point of writing it to the LETTER
    rather than to the user."""
    db, letter = FakeDB(), FakeLetter()

    await _run(db, None, letter)

    assert letter.email_suppressed_reason == "no_email"


@pytest.mark.asyncio
async def test_an_opted_out_reader_is_recorded(sendable):
    """A user choice, not a fault. It must stay distinguishable from the two
    failures above, which is the entire reason this column is not a boolean."""
    db, letter = FakeDB(), FakeLetter()

    await _run(db, FakeUser(opt_out=True), letter)

    assert letter.email_suppressed_reason == "opt_out"


@pytest.mark.asyncio
async def test_an_already_sent_letter_is_recorded(sendable):
    from datetime import datetime, timezone

    db = FakeDB()
    letter = FakeLetter(email_sent_at=datetime(2026, 9, 6, tzinfo=timezone.utc))

    await _run(db, FakeUser(), letter)

    assert letter.email_suppressed_reason == "already_sent"


@pytest.mark.asyncio
async def test_a_failing_send_is_recorded_and_does_not_raise(sendable, monkeypatch, caplog):
    """The nested try/except is scoped to send_email ALONE — the outer try also
    covers token minting and HTML rendering, and a template crash is not a send
    failure. The exception is re-raised into the outer handler so its
    logger.error(..., exc_info=True) still runs: that line is the Sentry path
    (observability.py:37-46), and eating it would delete the alert this reason
    exists to explain."""
    import services.email_service as email_service

    def _boom(**kwargs):
        raise RuntimeError("resend is down")

    monkeypatch.setattr(email_service, "send_email", _boom)
    db, letter = FakeDB(), FakeLetter()

    with caplog.at_level("ERROR"):
        await _run(db, FakeUser(), letter)  # must not raise — the letter is saved

    assert letter.email_suppressed_reason == "send_failed"
    assert letter.email_sent_at is None
    assert "resend is down" in caplog.text


# ── The success path leaves no reason ────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_successful_send_records_no_reason(sendable, monkeypatch):
    """NULL means "the email went out". If the success path ever wrote a reason,
    every one of the assertions above would still pass while the column became
    meaningless."""
    import services.email_service as email_service

    sent = []
    monkeypatch.setattr(email_service, "send_email", lambda **kw: sent.append(kw))
    db, letter = FakeDB(), FakeLetter()

    await _run(db, FakeUser(), letter)

    assert letter.email_suppressed_reason is None
    assert letter.email_sent_at is not None
    assert len(sent) == 1


# ── The vocabulary itself ────────────────────────────────────────────────────

def test_the_guard_writes_exactly_these_five_reasons_and_no_others():
    """THE PIN. With no CHECK constraint on the column (R2a), nothing in the
    database defends this vocabulary — so a sixth reason, or a typo in an
    existing one, would reach production silently and only show up as an
    unreadable value in an ops query months later.

    Read off the source rather than exercised, because the alternative is a test
    per branch that still could not prove the ABSENCE of a sixth."""
    source = inspect.getsource(_maybe_send_weekly_letter_email)
    written = set(re.findall(r'_suppress\(\s*"([^"]+)"\s*\)', source))

    assert written == EXPECTED_REASONS


def test_the_column_has_no_check_constraint(monkeypatch):
    """R2a, from the other side. If someone later adds a CHECK to
    email_suppressed_reason, adding a sixth reason silently becomes a production
    migration — the exact coupling 059 refused. This fails when that happens, and
    points at the decision rather than at a migration error."""
    from models import WeeklyLetter

    checks = [
        c for c in WeeklyLetter.__table__.constraints
        if "email_suppressed_reason" in str(getattr(c, "sqltext", ""))
    ]
    assert checks == []
