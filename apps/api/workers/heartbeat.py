"""The worker says it is alive, every ten minutes, in the one place the API can see. (Layer B)

WHY A HEARTBEAT AT ALL, since job_run already records real work. Because every
other writer of that table is WEEKLY. `weekly_letter` and
`weekly_trajectory_snapshot` both fire on Sunday; `monthly_letter` once a month.
So without a signal at this cadence, the earliest a dead worker could be noticed
is the next Sunday -- a mean time to detect of about three and a half days and a
worst case of seven. September's outage ran from Monday to Wednesday and was
found by accident; a checker that could only have caught it the following Sunday
would not have caught it at all.

The heartbeat is what makes the 20-minute grace in JOB_EXPECTATIONS mean
something. It is the only entry there whose cadence is faster than the outage it
is meant to detect.

NOT A LIVENESS ENDPOINT, deliberately. An HTTP route served by the worker would
be a thing the worker reports about itself, and a process that is dead cannot
answer that it is dead. A row is evidence that outlives the process that wrote
it: the API reads it, and so does GitHub Actions, without either of them asking
the worker anything.

IT COSTS ~52,000 ROWS A YEAR, and that is accepted as a known property rather
than a problem to solve. job_run holds an id, two short strings, two timestamps,
a status and three nullable ints; at this cadence that is a few megabytes a year
against a table with an index on started_at. No retention job, no partitioning.
If that ever stops being true it will be visible in exactly the table this
module writes to.

NEVER RAISES. A failed heartbeat must not take the worker down -- the same rule
purge_expired_otp_codes states for itself, and for the same reason: the next run
is ten minutes away and retries by construction. The failure is logged at ERROR
so it reaches Sentry directly, because the most likely cause of a heartbeat that
cannot write is the exact condition this whole feature exists for -- a worker
that cannot reach the database.
"""
import logging
from datetime import datetime, timezone

from workers.job_expectations import interval_run_key

logger = logging.getLogger(__name__)

# job_run.job_name. A named constant for the reason letter_dispatch and
# trajectory_snapshot name theirs: the (job_name, run_key) unique index is only
# an idempotency key if both halves are spelled the same way every time. This
# literal also appears in constants.JOB_EXPECTATIONS, and
# tests/test_job_expectations.py asserts the two agree.
JOB_HEARTBEAT = "worker_heartbeat"

# Must match the `every_minutes` of the worker_heartbeat entry in
# JOB_EXPECTATIONS. The same test pins that too: a writer on a 10-minute bucket
# and a checker looking for 15-minute buckets would never find a single row, and
# would report a healthy worker as permanently dead.
HEARTBEAT_EVERY_MINUTES = 10


def heartbeat_run_key(moment: datetime) -> str:
    """The 10-minute bucket a moment falls in, e.g. '2026-09-17T09:10Z'."""
    return interval_run_key(moment, HEARTBEAT_EVERY_MINUTES)


async def worker_heartbeat(ctx):
    """Write one job_run row for the current 10-minute bucket, and close it.

    OPENED AND CLOSED IN ONE BREATH, unlike a dispatch. The two letter jobs open
    a row BEFORE their work so that a crash leaves finished_at NULL as evidence;
    there is no work here to crash between the two calls, and a heartbeat that
    sat in 'running' would be indistinguishable from the crash signature it is
    supposed to help diagnose. A heartbeat is 'succeeded' or it is absent.

    THE COUNTS STAY NULL. 059's rule is that NULL means "never got that far" and
    0 means "counted, and there were none"; a heartbeat counts nothing, so
    claiming zero candidates would be a small lie in a table read by an operator.

    A SKIPPED BUCKET IS NOT A FAILURE. _open_job_run returns None when
    uq_job_run_name_key already holds this (job, bucket) -- two workers awake
    together, or a restart landing inside a bucket already written by
    run_at_startup. The row that is already there says exactly what this one
    would have said.
    """
    from db.session import AsyncSessionLocal
    from workers.letter_dispatch import _close_job_run, _open_job_run

    run_key = heartbeat_run_key(datetime.now(timezone.utc))
    try:
        async with AsyncSessionLocal() as db:
            run = await _open_job_run(db, JOB_HEARTBEAT, run_key)
            if run is None:
                return
            await _close_job_run(db, run, status="succeeded")
    except Exception as e:
        # ERROR, not warning: a heartbeat that cannot reach the database is the
        # September failure reporting itself directly, one layer earlier than
        # the API-side checker would.
        logger.error(
            "Worker: heartbeat failed for run_key=%s: %s", run_key, e, exc_info=True,
        )
