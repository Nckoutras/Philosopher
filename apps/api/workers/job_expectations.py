"""Was each scheduled job's most recent due run actually recorded? (Layer A)

THE GAP THIS CLOSES. A job that FAILS raises, and the exception reaches Sentry.
A job that never runs at all raises nothing, so it reports nothing, so nobody
learns. Mon 14 -> Wed 16 September 2026 the ARQ worker held a wrong
DATABASE_URL: every job in it stopped, and the outage was found three days later
by accident. `job_run` (migration 059) already records what DID run; this module
is the half that notices what did not.

WHY IT LIVES IN A PLAIN MODULE rather than inside the APScheduler job that calls
it. Every rule here is arithmetic over (expectation, now) plus two queries, and
all of it is worth testing directly. The existing cron tests reach into
setup_cron's closure to get at a job body (tests/services/test_cron_pending_emails.py:50-69);
there is no reason to add a third caller to that pattern when the logic can
simply be a function. workers/cron.py's job is a five-line wrapper over
`missed_expectations`.

THE EVALUATION, IN FULL. For each expectation:

  1. Compute the ONE run_key whose success is already due, given `now` and the
     expectation's grace. Never a range: a job that has been dead for six weeks
     should report the most recent miss, not six of them. The current period is
     never due -- a run that has not been asked for yet cannot be missing.
  2. Ask whether that (job_name, run_key) reached 'succeeded'. This reuses
     letter_dispatch._period_succeeded rather than restating the rule, so
     "a missing row, a failed row and a row still 'running' are all MISSED"
     has exactly one definition in the codebase.
  3. Consult the history floor. ABSENCE OF HISTORY IS NOT EVIDENCE OF A MISS --
     the rule _history_floor was written for, and it applies unchanged here: a
     period that predates the job's first-ever row was never expected to have
     one, and alerting on it would make every deploy of a NEW expectation
     announce a backlog of outages that never happened.

WHAT THE FLOOR COSTS, STATED PLAINLY RATHER THAN DISCOVERED LATER. A job that
has NEVER written a single row is invisible to this checker, because it has no
floor to be above. For the two weekly jobs that is moot -- both have written rows
since PR-B. For `worker_heartbeat` it is the difference between silence during a
rolling deploy (the API restarts with the checker before the worker restarts
with the heartbeat) and a false alarm every ten minutes for that window. The
window is the cost; the false alarm is the thing avoided.

That gap is not left open. It is covered by Layer C, the GitHub Actions check,
which asks the absolute question -- "is there a heartbeat row in the last N
minutes" -- against a database neither process owns, and which therefore cannot
be talked out of an answer by the absence of history. The two layers fail in
opposite directions on purpose.
"""
from datetime import datetime, timedelta, timezone

# The run_key format for an interval cadence: the START of the bucket, in UTC,
# to the minute. 17 characters against run_key's VARCHAR(32).
#
# THE PERIOD, NEVER THE EXECUTION TIME -- 059's R7 rule, and it applies to a
# 10-minute bucket exactly as it does to an ISO week. A key built from the
# moment the job happened to fire would make two runs inside one bucket look
# like two periods, and uq_job_run_name_key would stop being an idempotency key.
INTERVAL_KEY_FORMAT = "%Y-%m-%dT%H:%MZ"


def interval_run_key(moment: datetime, every_minutes: int) -> str:
    """The interval bucket a moment falls in, e.g. '2026-09-17T09:10Z'.

    Floors to the bucket, so every moment inside one window yields one key. Both
    the writer (workers/heartbeat.py) and this checker call THIS function; a
    second copy of the arithmetic anywhere would be a silent mismatch that reads
    as a permanently missing job.
    """
    span = every_minutes * 60
    epoch = int(moment.timestamp())
    start = epoch - (epoch % span)
    return datetime.fromtimestamp(start, tz=timezone.utc).strftime(INTERVAL_KEY_FORMAT)


def due_run_key(expectation: dict, now: datetime) -> tuple[str, datetime]:
    """The (run_key, period_start) whose success is already due at `now`.

    Returns the most recent period past its deadline -- never the one in flight.
    """
    cadence = expectation["cadence"]
    if cadence == "weekly":
        return _weekly_due(expectation, now)
    if cadence == "interval":
        return _interval_due(expectation, now)
    raise ValueError(f"unknown cadence {cadence!r} for {expectation['job_name']}")


def _weekly_due(expectation: dict, now: datetime) -> tuple[str, datetime]:
    """Fixed ISO weekday + hour UTC, keyed by ISO week.

    The key comes from the FIRE MOMENT, not from `now`, which is what makes it
    agree with weekly_run_key: a Sunday 18:00 fire falls on the last day of its
    own ISO week (ISO weeks start Monday), so the key names the week that is
    ending -- the window the letter covers.
    """
    iso = now.isocalendar()
    fire = datetime.fromisocalendar(iso[0], iso[1], expectation["isoweekday"]).replace(
        hour=expectation["hour"], tzinfo=timezone.utc
    )
    # Before this week's deadline, the run already OWED is last week's.
    if now < fire + timedelta(minutes=expectation["grace_minutes"]):
        fire -= timedelta(days=7)
    return fire.strftime("%G-W%V"), fire


def _interval_due(expectation: dict, now: datetime) -> tuple[str, datetime]:
    """Every N minutes, keyed by the N-minute bucket.

    A bucket starting at S is due once S + N + grace has passed: N for the window
    itself to elapse, grace on top. So the largest due bucket is the one
    containing (now - N - grace), found by flooring rather than by looping back
    from the present.
    """
    span = expectation["every_minutes"] * 60
    cutoff = int(now.timestamp()) - span - expectation["grace_minutes"] * 60
    start = cutoff - (cutoff % span)
    due = datetime.fromtimestamp(start, tz=timezone.utc)
    return interval_run_key(due, expectation["every_minutes"]), due


async def missed_expectations(db, now: datetime | None = None) -> list[dict]:
    """Every expectation whose due run never reached 'succeeded'.

    Returns dicts rather than log lines so a test can assert on the finding
    itself, and so the caller owns the wording that reaches Sentry.
    """
    from constants import JOB_EXPECTATIONS
    from workers.letter_dispatch import _history_floor, _period_succeeded

    now = now or datetime.now(timezone.utc)
    missed: list[dict] = []

    for expectation in JOB_EXPECTATIONS:
        job_name = expectation["job_name"]
        run_key, period_start = due_run_key(expectation, now)

        if await _period_succeeded(db, job_name, run_key):
            continue

        # Absence of history is not evidence of a miss (see the module docstring).
        floor = await _history_floor(db, job_name)
        if floor is None or floor > period_start:
            continue

        missed.append({
            "job_name": job_name,
            "run_key": run_key,
            "period_start": period_start,
            "overdue_minutes": int((now - period_start).total_seconds() // 60),
        })

    return missed
