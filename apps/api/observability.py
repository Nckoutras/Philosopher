"""Sentry error monitoring — one init, two entrypoints, and a scrubber.

WHY THIS EXISTS. Production errors were visible only if someone happened to read
Render logs. A broken webhook, a crashing letter job or a 500 on checkout could
run for days unseen; the 0/22 letters incident and the eight-day red CI both
happened for exactly that reason. With paying users, silent breakage is silent
churn.

WHAT REACHES SENTRY. Errors carry IDS — user_id, conversation_id, event id.
Never conversation content, message text, memory entries, letter text, email
addresses or names. That is the product's core promise, and four separate
mechanisms below enforce it because `send_default_pii=False` alone does NOT:

  1. max_request_body_size="never". THE load-bearing line. Request bodies are
     gated on THIS option, not on send_default_pii — verified in the 2.68.1
     source: StarletteRequestExtractor attaches JSON bodies by size (default
     "medium"), while send_default_pii gates cookies. Left at the default,
     POST /conversations/{id}/messages would ship raw message text on any 500.

  2. The Anthropic and OpenAI integrations are DISABLED by name. Both are
     auto-enabling, both default include_prompts=True, and the OpenAI one
     records embeddings input — which is user text. Their prompt recording is
     gated on send_default_pii and they only write to spans (none, with tracing
     off), so they are already closed twice over. Disabling them explicitly is
     one auditable line instead of two defaults that have to stay true across
     every future SDK upgrade.

  3. include_local_variables=False. Found by end-to-end test, not by reading
     the option list: Sentry captures EVERY local variable of EVERY stack frame
     by default, so a crash inside generate_weekly_letter_task would have
     shipped `letter_text`, `messages` and `content` as frame vars — the whole
     letter — while every other control above reported clean. The stack trace,
     which is the part that debugs, is unaffected.

  4. before_send + before_breadcrumb, below. The net, not the fix.

WHY LOGGING IS THE MECHANISM. Every ARQ task (13) and cron job (8) catches its
own Exception and logs rather than re-raising, so ArqIntegration — which only
sees exceptions that ESCAPE a task — would report nothing at all. What does
report them is the default LoggingIntegration: event_level=ERROR turns every
logger.error(..., exc_info=True) into an event carrying its stack trace. Those
22 sites are therefore covered with no code change, and test_observability.py
pins that reliance so an SDK upgrade cannot quietly remove it.

NO TRACING. traces_sample_rate=0 — this is error monitoring, not the
performance product. It also means no spans exist for an LLM integration to
attach prompt data to.
"""
import logging
import os
import re
from typing import Any

from config import config

logger = logging.getLogger(__name__)

# Deliberately broad. This is a scrubber of last resort, so it prefers a false
# positive (redacting something harmless) over a miss. It is NOT an address
# validator and must not be reused as one.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

_REDACTED = "[redacted]"

# Keys whose VALUES are user-authored text anywhere in this codebase. Matched
# case-insensitively against the leaf keys of any dict in the event payload.
# If a field is in doubt, it belongs here: dropping a debuggable field costs a
# support round-trip, leaking one costs the promise the product is sold on.
_CONTENT_KEYS = frozenset({
    "content", "text", "message", "messages", "body", "prompt", "completion",
    "letter", "letter_text", "reply", "answer", "question", "belief",
    "excerpt", "snippet", "quote", "note", "entry", "memory", "reflection",
    "title", "full_name", "name", "email", "password", "token",
    "access_token", "code", "traits", "properties",
})


def _scrub_string(value: str) -> str:
    """Redact any email-like substring, leaving the rest of the message intact."""
    return _EMAIL_RE.sub(_REDACTED, value)


def _scrub_value(value: Any, depth: int = 0) -> Any:
    """Walk a JSON-ish structure, dropping content keys and redacting emails.

    Depth-bounded: Sentry payloads are finite, but a bug upstream that produced a
    self-referential structure must not turn error reporting into a hang.
    """
    if depth > 12:
        return _REDACTED
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in _CONTENT_KEYS:
                out[k] = _REDACTED
            else:
                out[k] = _scrub_value(v, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_scrub_value(v, depth + 1) for v in value]
    if isinstance(value, str):
        return _scrub_string(value)
    return value


def _scrub(event: dict, hint: dict) -> dict:
    """before_send: strip request bodies, content fields, emails, and user PII.

    Runs on every event. Returning the event (never None) keeps the error
    itself — the point is to report the failure without its payload.
    """
    # 1. Request bodies are never sent, whatever max_request_body_size does.
    #    Belt and braces: option 1 above should mean "data" is never populated,
    #    and this makes a regression in that option non-fatal.
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        # A query string can carry an email (unsubscribe links, OAuth callbacks).
        if isinstance(request.get("query_string"), str):
            request["query_string"] = _scrub_string(request["query_string"])

    # 2. The user context keeps its id and nothing else. Sentry populates
    #    username/email/ip_address from several sources; only "id" is debuggable
    #    AND non-identifying here.
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}

    # 3. Log message and exception text. This is the path that matters most:
    #    LoggingIntegration turns logger.error() into an event whose TITLE is the
    #    formatted message, so an f-string that interpolated an address would put
    #    it in the issue title.
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        # BOTH fields, and "formatted" is the one that matters: "message" is the
        # %s format string, "formatted" is the rendered result, and Sentry uses
        # formatted for the issue title. Scrubbing only "message" looks correct
        # and leaks every address logged via %s — which is how the two auth
        # sites logged them. Caught by the end-to-end run, not by a unit test.
        for field in ("message", "formatted"):
            if isinstance(logentry.get(field), str):
                logentry[field] = _scrub_string(logentry[field])
        if isinstance(logentry.get("params"), (list, tuple, dict)):
            logentry["params"] = _scrub_value(logentry["params"])
    if isinstance(event.get("message"), str):
        event["message"] = _scrub_string(event["message"])

    for entry in (event.get("exception") or {}).get("values") or []:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("value"), str):
            entry["value"] = _scrub_string(entry["value"])
        # Frame locals. include_local_variables=False in the init means these
        # should not exist at all; this is what makes a regression in that
        # option non-fatal rather than a silent content leak. Dropped whole
        # rather than filtered by key: a local can hold user text under ANY
        # name (`row`, `payload`, `t`), so a key allowlist would not hold.
        for frame in (entry.get("stacktrace") or {}).get("frames") or []:
            if isinstance(frame, dict):
                frame.pop("vars", None)

    # 4. Structured context set by us or by an integration.
    for key in ("extra", "contexts", "tags"):
        if key in event:
            event[key] = _scrub_value(event[key])

    return event


def _scrub_breadcrumb(crumb: dict, hint: dict) -> dict | None:
    """before_breadcrumb: drop any breadcrumb whose message contains an address.

    LoggingIntegration records logger.info() and above as breadcrumbs. Our INFO
    lines are id-based, so this drops nothing today — it is here so that a future
    log line that interpolates an address cannot ride along attached to an
    unrelated error.
    """
    message = crumb.get("message")
    if isinstance(message, str) and _EMAIL_RE.search(message):
        return None
    return crumb


def init_sentry() -> bool:
    """Initialise Sentry if a DSN is configured. Returns whether it did.

    A no-op when SENTRY_DSN is unset, which is the case for local development
    and CI — same convention as analytics_service and the POSTHOG_API_KEY gate.
    Called from BOTH entrypoints: main.py (the API, which also runs the eight
    APScheduler cron jobs in-process) and workers/arq_worker.py (a separate
    process that never imports main).
    """
    if not config.SENTRY_DSN:
        return False

    # NOTHING in here may stop the process from booting. SENTRY_DSN is pasted by
    # hand into the Render dashboard on two services, and a stray character in it
    # would otherwise raise at import time and take down BOTH the API and the
    # worker — error monitoring causing the outage it exists to catch. The import
    # is inside the try for the same reason: a broken install degrades to "no
    # monitoring", never to "no service".
    try:
        import sentry_sdk
        from sentry_sdk.integrations.anthropic import AnthropicIntegration
        from sentry_sdk.integrations.openai import OpenAIIntegration

        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            environment=config.ENV,
            # Render injects this on every service; None locally, which Sentry
            # accepts as "no release".
            release=os.environ.get("RENDER_GIT_COMMIT"),
            send_default_pii=False,
            max_request_body_size="never",
            # See mechanism 3 above. Frame locals in this codebase hold letter
            # text, message rows and memory entries.
            include_local_variables=False,
            traces_sample_rate=0,
            before_send=_scrub,
            before_breadcrumb=_scrub_breadcrumb,
            disabled_integrations=[AnthropicIntegration(), OpenAIIntegration()],
        )
    except Exception as e:
        # Deliberately logger.error: with Sentry down this reaches Render's log,
        # which is the only channel left.
        logger.error("Sentry init failed, continuing WITHOUT error monitoring: %s", e)
        return False

    logger.info("Sentry initialised [env=%s]", config.ENV)
    return True
