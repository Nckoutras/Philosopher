"""One way to hand work to the ARQ queue from a request path, that never goes quiet.

WHY THIS EXISTS (OBS-001, ruling 6). Every request-path enqueue used to be one
of two shapes, and both could lose work without a trace:

  1. `if arq_queue is not None: await arq_queue.enqueue_job(...)` with no try.
     A Redis hiccup at that moment raised out of the SSE generator, which ended
     the stream without its `done` event (conversation_service) or turned a
     counterview that was ALREADY SAVED into a 500 (routers/counterview).
  2. The same guard with a try/except that logged — but the guard itself was
     silent. When ARQ/cron startup fails in lifespan, the API boots healthy
     with app.state.arq_queue unset (main.py), and from then on every site
     skips its enqueue with no log line at all. Memory extraction, titles,
     conclusion assessment, the dunning email: all dropped, nothing said.

This helper is the one place both cases are handled, so a new call site cannot
reintroduce either by copying the wrong neighbour.

ABSENT QUEUE: ONE ERROR PER JOB PER BOOT, THEN WARNINGS. The first skip of each
job name is an ERROR, which Sentry's LoggingIntegration turns into an event
(observability.py); later skips of the same job are WARNINGs, which it keeps
as breadcrumbs. A process with no queue takes every request, so ERROR on each
would be hundreds of events saying one thing. The set lives in process memory
and resets on restart — on purpose: a restart that STILL has no queue should
say so again. GET /health/deep is the detection; this line is the diagnosis
(which job, how often).

ENQUEUE FAILURE: ERROR WITH THE TRACE, RETURN FALSE. The caller decides what
"not enqueued" means for its own response; for every current site it means
"carry on, the primary write is already committed".

`context` IS FOR IDENTIFIERS ONLY — user ids, conversation ids, a source label.
Never text. It goes into a log message that becomes a Sentry event title.
"""
import logging

logger = logging.getLogger(__name__)

# Job names whose absent-queue skip has already been reported at ERROR in this
# process. Module-level and unguarded: the worst race is two ERRORs for one job.
_absent_reported: set[str] = set()


async def safe_enqueue(queue, job_name: str, *args, context: str = "") -> bool:
    """Enqueue `job_name` with `args`, or say why not. Never raises.

    Returns True when the job was accepted by Redis, False otherwise.
    """
    if queue is None:
        level = logging.WARNING if job_name in _absent_reported else logging.ERROR
        _absent_reported.add(job_name)
        logger.log(
            level,
            "Enqueue skipped, no queue: job=%s %s -- app.state.arq_queue is None, "
            "so ARQ/cron startup failed in lifespan and background work is being "
            "dropped on every request",
            job_name, context,
        )
        return False
    try:
        await queue.enqueue_job(job_name, *args)
        return True
    except Exception as e:  # noqa: BLE001 — a request path must not die for a lost side-effect
        logger.error("Enqueue failed: job=%s %s: %s", job_name, context, e, exc_info=True)
        return False


def reset_absent_reports() -> None:
    """Tests only: forget which jobs have already been reported."""
    _absent_reported.clear()
