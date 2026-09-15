"""One rule for "this base URL is not publishable", used by both email paths.

WHY A SHARED RULE AT ALL (TD-77). The product sends two kinds of mail that carry
a link back into itself, and until now they disagreed about the same
misconfiguration:

  weekly letter   guarded API_BASE_URL — suppressed, recorded the reason on the
                  row, logged at ERROR
  future-self     guarded NOTHING — built the arrival link from FRONTEND_URL,
                  sent anyway, and marked the row 'sent'

One product, two paths, opposite behaviour, and the silent one is the one that
reached a real reader with a dead link. The rule is now `is_unset_public_url` and
both call it.

WHY THE HELPER TAKES A URL rather than reading config itself: the two guard
DIFFERENT VARIABLES, correctly. The letter builds an unsubscribe link, which
lives on the API, so it checks API_BASE_URL. The future-self letter builds an
arrival link, which lives on the frontend, so it checks FRONTEND_URL. A helper
that picked the variable would be wrong for one of them. What must not drift is
the rule.

Behavioural tests live with their paths — tests/services/test_cron_pending_emails.py
and tests/workers/test_letter_email_suppression.py. This file owns the rule.

Run: cd apps/api && pytest tests/test_outbound_link_guard.py -v
"""
import pathlib

import pytest

from config import is_unset_public_url

API_ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("url", [
    "http://localhost:3000",
    "https://localhost",
    "http://localhost:8000/api",
    "http://127.0.0.1:8000",
    "https://127.0.0.1",
])
def test_localhost_forms_are_refused(url):
    assert is_unset_public_url(url) is True


@pytest.mark.parametrize("url", ["", "   ", None])
def test_empty_counts_as_unset(url):
    """NOT the same check as "localhost", and this is the case the original guard
    would have let through.

    A var set explicitly to "" produces `"" + "/app/scheduled-letters/<id>"` — a
    relative path, dead in every mail client, and containing no "localhost" for a
    substring test to match. The widening is deliberate and is the only behaviour
    change the letter path sees from adopting this helper.
    """
    assert is_unset_public_url(url) is True


@pytest.mark.parametrize("url", [
    "https://thewiseroom.app",
    "https://philosopher-api-z9l9.onrender.com",
    "https://thewiseroom.app/",
    "http://staging.internal.example",
])
def test_real_urls_are_allowed(url):
    """The control. A rule that refused everything would pass every test above
    and silently stop both email paths in production."""
    assert is_unset_public_url(url) is False


def test_a_hostname_merely_containing_localhost_is_still_refused():
    """Recorded as ACCEPTED IMPRECISION rather than fixed.

    `https://localhost.example.com` is a real, routable hostname and this rule
    rejects it. Tightening to a parsed-host comparison would be more correct and
    is not worth it: nobody serves this product from such a domain, the failure
    mode is a refused send that logs loudly at ERROR, and the opposite error —
    letting a placeholder through — is the one that reaches a reader in silence.
    If this ever bites, parse the host; do not loosen the substring.
    """
    assert is_unset_public_url("https://localhost.example.com") is True


def test_both_email_paths_use_the_rule():
    """Asserted at the SOURCE, because this is a claim about two files agreeing
    that no runtime test of either one can make."""
    letter = (API_ROOT / "workers" / "arq_worker.py").read_text(encoding="utf-8")
    cron = (API_ROOT / "workers" / "cron.py").read_text(encoding="utf-8")

    assert "is_unset_public_url(config.API_BASE_URL)" in letter, (
        "the weekly-letter guard no longer uses the shared rule"
    )
    assert "is_unset_public_url(config.FRONTEND_URL)" in cron, (
        "the future-self guard no longer uses the shared rule"
    )


def test_neither_path_keeps_a_hand_rolled_copy():
    """The drift this is really guarding against: a future edit that adds a
    localhost check back inline, next to the shared one, so the two rules exist
    again and only one of them gets the next fix."""
    offenders = []
    for name in ("arq_worker.py", "cron.py"):
        src = (API_ROOT / "workers" / name).read_text(encoding="utf-8")
        for needle in ('"localhost" in config.', '"127.0.0.1" in config.'):
            if needle in src:
                offenders.append(f"{name}: {needle}")
    assert not offenders, (
        f"hand-rolled placeholder checks are back: {offenders} — use is_unset_public_url"
    )
