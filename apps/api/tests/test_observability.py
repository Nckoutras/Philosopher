"""The Sentry contract, pinned.

WHY THIS FILE EXISTS. Two claims hold this feature up, and neither is visible in
the code that relies on them:

  1. "send_default_pii=False keeps content out." FALSE on its own. Request
     bodies are gated on max_request_body_size, whose default is "medium" — so
     a dropped line in the init would ship raw message text from
     POST /conversations/{id}/messages on the next 500, silently, and no test
     that merely called init() would notice.

  2. "LoggingIntegration covers the 22 swallowing handlers." True today, and
     true only because the SDK defaults event_level to ERROR. An upgrade that
     changed that default, or an edit that passed integrations=[...] explicitly,
     would leave every ARQ task and cron job reporting nothing — which is the
     exact silence this feature exists to end.

HOW THESE FAIL. test_init_kwargs asserts the WHOLE kwargs object by equality
(the #580 pattern), so removing any privacy option — or adding one nobody
reviewed — fails it rather than passing quietly. The scrubber tests plant a
body, an address and a content key in an event and assert each is gone; each
one fails if its branch in _scrub is removed. test_logging_integration_is_active
pins claim 2 against the real SDK default rather than against a comment.
"""
import logging
from unittest.mock import patch

import pytest

import observability
from observability import _scrub, _scrub_breadcrumb, init_sentry


# ── init: gating and the exact option set ─────────────────────────────────────

def test_init_is_a_no_op_without_a_dsn():
    """Local and CI run with SENTRY_DSN unset. That must touch nothing."""
    with patch.object(observability.config, "SENTRY_DSN", ""), \
         patch("sentry_sdk.init") as mock_init:
        assert init_sentry() is False
        mock_init.assert_not_called()


def test_init_kwargs_are_exactly_the_reviewed_set():
    from sentry_sdk.integrations.anthropic import AnthropicIntegration
    from sentry_sdk.integrations.openai import OpenAIIntegration

    with patch.object(observability.config, "SENTRY_DSN", "https://k@o.ingest.sentry.io/1"), \
         patch.object(observability.config, "ENV", "production"), \
         patch.dict("os.environ", {"RENDER_GIT_COMMIT": "abc123"}), \
         patch("sentry_sdk.init") as mock_init:
        assert init_sentry() is True

    mock_init.assert_called_once()
    args, kwargs = mock_init.call_args
    assert args == ()

    disabled = kwargs.pop("disabled_integrations")
    # Compared by type: the SDK takes instances, and instances are not equal by
    # value, so an equality assert on the whole object would be untestable.
    assert [type(i) for i in disabled] == [AnthropicIntegration, OpenAIIntegration]

    # The whole remaining object, by equality. Dropping max_request_body_size —
    # the one line that actually stops request bodies — fails HERE.
    assert kwargs == {
        "dsn": "https://k@o.ingest.sentry.io/1",
        "environment": "production",
        "release": "abc123",
        "send_default_pii": False,
        "max_request_body_size": "never",
        "include_local_variables": False,
        "traces_sample_rate": 0,
        "before_send": observability._scrub,
        "before_breadcrumb": observability._scrub_breadcrumb,
    }


def test_a_failing_init_never_blocks_boot():
    """A malformed DSN must degrade to "no monitoring", never to "no service".

    SENTRY_DSN is pasted by hand into the Render dashboard on two services, and
    init_sentry() runs at IMPORT time in both. Unwrapped, one stray character
    would take down the API and the worker together — error monitoring causing
    the outage it exists to catch.
    """
    with patch.object(observability.config, "SENTRY_DSN", "not-a-valid-dsn"),          patch("sentry_sdk.init", side_effect=ValueError("Unsupported scheme")):
        assert init_sentry() is False  # returns, does not raise


def test_a_failing_init_is_logged_as_an_error(caplog):
    """With Sentry down, Render's log is the only channel left — so this one
    must be ERROR, not debug."""
    with patch.object(observability.config, "SENTRY_DSN", "not-a-valid-dsn"),          patch("sentry_sdk.init", side_effect=ValueError("Unsupported scheme")),          caplog.at_level(logging.ERROR, logger="observability"):
        init_sentry()
    assert any(
        r.levelno == logging.ERROR and "continuing WITHOUT error monitoring" in r.getMessage()
        for r in caplog.records
    )


def test_release_is_none_when_render_does_not_inject_a_sha():
    with patch.object(observability.config, "SENTRY_DSN", "https://k@o.ingest.sentry.io/1"), \
         patch.dict("os.environ", {}, clear=True), \
         patch("sentry_sdk.init") as mock_init:
        init_sentry()
    assert mock_init.call_args.kwargs["release"] is None


def test_logging_integration_still_turns_logger_error_into_an_event():
    """The load-bearing default. 22 swallowing handlers depend on it.

    Asserted against the installed SDK, not against a comment: if a future
    version stops defaulting event_level to ERROR, every ARQ task and cron job
    goes silent and this fails.
    """
    from sentry_sdk.integrations.logging import (
        LoggingIntegration, DEFAULT_EVENT_LEVEL, DEFAULT_LEVEL,
    )
    from sentry_sdk.integrations import _DEFAULT_INTEGRATIONS

    assert DEFAULT_EVENT_LEVEL == logging.ERROR
    assert DEFAULT_LEVEL == logging.INFO
    assert any(
        path.endswith("LoggingIntegration") for path in _DEFAULT_INTEGRATIONS
    ), "LoggingIntegration is no longer a default integration"
    assert LoggingIntegration().identifier == "logging"


# ── scrubber ──────────────────────────────────────────────────────────────────

def test_request_body_is_dropped():
    """The mutation: delete request.pop("data") in _scrub and this fails."""
    event = {"request": {
        "url": "https://api/api/v1/conversations/c1/messages",
        "method": "POST",
        "data": {"content": "I have been thinking about my father's death."},
        "cookies": {"session": "abc"},
    }}
    out = _scrub(event, {})
    assert "data" not in out["request"]
    assert "cookies" not in out["request"]
    assert "father" not in repr(out)
    # The error itself survives — scrubbing is not suppression.
    assert out["request"]["url"].endswith("/messages")


def test_email_is_redacted_from_a_log_message():
    """Models the real leak: routers/auth.py logged the address, and
    LoggingIntegration puts a log message in the issue TITLE."""
    event = {"logentry": {
        "message": "OTP request failed for someone@gmail.com: timeout",
        "params": ["someone@gmail.com"],
    }}
    out = _scrub(event, {})
    assert "someone@gmail.com" not in repr(out)
    assert "[redacted]" in out["logentry"]["message"]
    # The diagnosis is kept.
    assert "timeout" in out["logentry"]["message"]


def test_the_rendered_log_message_is_scrubbed_not_just_the_format_string():
    """logger.error("failed: %s", addr) produces BOTH fields, and Sentry titles
    the issue from "formatted". Scrubbing only "message" passes a naive test and
    leaks every address logged via %s — which is exactly how the two auth sites
    log them now. Found by the end-to-end run against the real SDK."""
    event = {"logentry": {
        "message": "OTP request failed for domain=%s: %s",
        "formatted": "OTP request failed for domain=someone@gmail.com: timeout",
        "params": ["someone@gmail.com", "timeout"],
    }}
    out = _scrub(event, {})
    assert "someone@gmail.com" not in repr(out)
    assert "[redacted]" in out["logentry"]["formatted"]
    assert "timeout" in out["logentry"]["formatted"]


def test_email_is_redacted_from_an_exception_value():
    event = {"exception": {"values": [
        {"type": "ValueError", "value": "bad address user.name+tag@sub.example.co.uk"},
    ]}}
    out = _scrub(event, {})
    assert "user.name+tag@sub.example.co.uk" not in repr(out)
    assert out["exception"]["values"][0]["type"] == "ValueError"


def test_content_keys_are_dropped_wherever_they_appear():
    """The mutation: remove the _CONTENT_KEYS branch and this fails."""
    event = {"extra": {
        "conversation_id": "c1",
        "content": "the raw message text",
        "nested": {"letter": "Dear friend, ...", "user_id": "u1"},
        "list": [{"prompt": "system prompt"}],
    }}
    out = _scrub(event, {})
    assert out["extra"]["content"] == "[redacted]"
    assert out["extra"]["nested"]["letter"] == "[redacted]"
    assert out["extra"]["list"][0]["prompt"] == "[redacted]"
    # Ids are the point of the whole exercise — they must survive.
    assert out["extra"]["conversation_id"] == "c1"
    assert out["extra"]["nested"]["user_id"] == "u1"


def test_frame_local_variables_are_dropped():
    """The leak the unit tests missed and the end-to-end run caught.

    Sentry captures every local of every frame by default. In this codebase a
    frame local is `letter_text`, `messages`, `content` — so a crash inside a
    letter task would have shipped the letter while request bodies, user
    context and log messages all reported clean.

    include_local_variables=False in the init means `vars` should never arrive;
    this is the net under that option. The stack trace itself survives, because
    that is the part that debugs.
    """
    event = {"exception": {"values": [{
        "type": "RuntimeError",
        "value": "boom",
        "stacktrace": {"frames": [
            {"function": "generate_weekly_letter_task", "lineno": 1700,
             "vars": {"letter_text": "Dear friend, I have watched you...",
                      "user_id": "u1"}},
            {"function": "_maybe_send_weekly_letter_email", "lineno": 1400,
             "vars": {"addr": "someone@gmail.com"}},
        ]},
    }]}}
    out = _scrub(event, {})
    frames = out["exception"]["values"][0]["stacktrace"]["frames"]
    assert all("vars" not in f for f in frames)
    assert "Dear friend" not in repr(out)
    assert "someone@gmail.com" not in repr(out)
    # The trace is intact — scrubbing must not cost the diagnosis.
    assert frames[0]["function"] == "generate_weekly_letter_task"
    assert frames[0]["lineno"] == 1700


def test_user_context_keeps_only_the_id():
    event = {"user": {
        "id": "u1", "email": "someone@gmail.com",
        "username": "Real Name", "ip_address": "1.2.3.4",
    }}
    out = _scrub(event, {})
    assert out["user"] == {"id": "u1"}


def test_user_context_without_an_id_becomes_empty():
    out = _scrub({"user": {"email": "someone@gmail.com"}}, {})
    assert out["user"] == {}


def test_query_string_is_scrubbed():
    out = _scrub({"request": {"query_string": "email=someone@gmail.com&t=1"}}, {})
    assert "someone@gmail.com" not in repr(out)


def test_scrub_survives_a_bare_event():
    """Not every event has a request, a user, or an exception."""
    assert _scrub({}, {}) == {}


def test_scrub_is_depth_bounded():
    event: dict = {"extra": {}}
    node = event["extra"]
    for _ in range(40):
        node["nested"] = {}
        node = node["nested"]
    node["content"] = "deep"
    _scrub(event, {})  # must return rather than recurse without limit


# ── breadcrumbs ───────────────────────────────────────────────────────────────

def test_breadcrumb_with_an_email_is_dropped():
    assert _scrub_breadcrumb({"message": "sent to someone@gmail.com"}, {}) is None


def test_ordinary_breadcrumb_survives():
    crumb = {"message": "weekly letter sent user=u1 letter=l1"}
    assert _scrub_breadcrumb(crumb, {}) is crumb


def test_breadcrumb_without_a_message_survives():
    crumb = {"category": "query"}
    assert _scrub_breadcrumb(crumb, {}) is crumb


# ── the log lines this PR fixed ───────────────────────────────────────────────

@pytest.mark.parametrize("path,forbidden", [
    ("routers/auth.py", 'f"OTP request failed for {email}'),
    ("routers/auth_oauth.py", 'f"OAuth user creation failed for {email}"'),
])
def test_the_two_log_sites_no_longer_interpolate_an_address(path, forbidden):
    """Read as source. The scrubber is the net; these are the fix, and a revert
    of either f-string would otherwise be invisible once the net catches it."""
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / path
    assert forbidden not in source.read_text(encoding="utf-8")
