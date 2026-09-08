"""Weekly and monthly letter dispatch — ARQ cron jobs, with a job_run audit row.

WHAT MOVED, AND WHAT DID NOT (PR-B). The two dispatch bodies came out of
workers/cron.py (the `weekly_letter` and `monthly_letter` @scheduled_job blocks)
VERBATIM. Their queries, their eligibility arithmetic, their voice election and
their log lines are unchanged. What changed is where they run and what they leave
behind:

  - they run in the ARQ WORKER process, as cron_jobs, not in the API process
    under APScheduler;
  - the enqueue target is ctx['redis'] (an ArqRedis, set by the worker at
    worker.py:361) instead of the closed-over `arq_queue`;
  - each run opens and closes a job_run row.

WHAT PR-C ADDED. The period is now EXPLICIT end to end (D-2):

  - the period is aligned to the ISO week, so run_key really is derived from
    period_start (R7) rather than merely correlated with it — see week_period;
  - dispatch computes the period ONCE and passes it to the generator, which no
    longer recomputes its own window from `now`;
  - a catch-up pass finds a period whose run never succeeded and re-dispatches
    it, reclaiming the failed or crashed job_run row (R8).

THE NEW FAILURE MODE, STATED PLAINLY: if the ARQ worker service is down, letters
stop and the API still reports healthy. That is a real consequence of PR-B. It is
also the thing job_run exists to make visible — and, since PR-C, the thing the
catch-up pass repairs the next morning.

IMPORTS OF arq_worker STAY INSIDE THE FUNCTION BODIES. arq_worker imports THIS
module at module level (WorkerSettings needs the coroutines), so a top-level
`from workers.arq_worker import ...` here would be a cycle. The bodies already
imported that way in cron.py, so nothing had to be rewritten to keep it safe —
the property was already there. Do not lift these imports to the top of the file.
"""
import calendar
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# job_run.job_name values. Named constants because the (job_name, run_key) unique
# index is only an idempotency key if both halves are spelled the same way every
# time; a typo would silently create a second series of runs that never collide.
JOB_WEEKLY = "weekly_letter"
JOB_MONTHLY = "monthly_letter"

# How long a job_run may sit in status='running' before catch-up treats it as a
# crashed run rather than one still in flight. The weekly dispatch is a handful
# of queries and N enqueues — seconds, not minutes — and the letter GENERATION
# that follows is a separate job with its own 300s timeout, so it does not hold
# this row open. Two hours is therefore enormous slack, chosen so that a slow
# database or a paused worker is never mistaken for a crash.
STALE_RUNNING_AFTER = timedelta(hours=2)


# ── Periods (R7) ──────────────────────────────────────────────────────────────

def weekly_run_key(now: datetime) -> str:
    """The ISO week a moment falls in, e.g. '2026-W36' (R7).

    Sunday 18:00 falls on the LAST day of its own ISO week (ISO weeks start
    MONDAY), so the live run's key names the week that is ending — which is the
    window the letter covers. See week_period for the other direction.
    """
    return now.strftime("%G-W%V")


def monthly_run_key(now: datetime) -> str:
    """The calendar month a moment falls in, e.g. '2026-09' (R7)."""
    return now.strftime("%Y-%m")


def week_period(run_key: str) -> tuple[datetime, datetime]:
    """'2026-W36' -> (Mon 2026-08-31 00:00Z, Sun 2026-09-06 23:59:59Z).

    THE ROUND TRIP IS THE POINT. weekly_run_key(week_period(k)[0]) == k for every
    k, including the awkward ones: 2026-W01 starts 2025-12-29, in the previous
    calendar YEAR, and 2026-W53 ends 2027-01-03. That is what makes R7 literally
    true — run_key is derived from period_start, not merely correlated with it —
    and it is what lets catch-up reconstruct a period from a key alone, without
    reference to the clock it is running on.

    Before PR-C the weekly period was (now - 7 days) floored to midnight, which
    for a Sunday run is the PREVIOUS Sunday — ISO week W35 for a run keyed W36.
    The key and the period named different weeks, so R7 could not hold.
    """
    year, week = run_key.split("-W")
    start = datetime.fromisocalendar(int(year), int(week), 1).replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=6, hours=23, minutes=59, seconds=59)


def month_period(run_key: str) -> tuple[datetime, datetime]:
    """'2026-09' -> (2026-09-01 00:00Z, 2026-09-30 23:59:59Z).

    Unchanged arithmetic: the monthly period ALREADY satisfied R7 before PR-C,
    because run_key is the month of period_start by construction. This function
    only moves it out of the generator so dispatch and generator share one
    expression instead of two that happen to agree.
    """
    year, month = (int(p) for p in run_key.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    return start, datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)


def is_last_day_of_month(now: datetime) -> bool:
    """True when `now` falls on the final calendar day of its month.

    APScheduler's CronTrigger(day='last') has NO ARQ equivalent — arq's cron
    matches a field against an int or a set/list/tuple and raises RuntimeError on
    anything else (arq/cron.py:_get_next_dt), so 'last' cannot be expressed as a
    schedule. The schedule therefore fires on day={28,29,30,31} and this guard
    discards the 0-3 runs that are not the last day.

    Cheap by construction: it is one timedelta and one attribute compare, and it
    runs BEFORE any database access and before the job_run row is opened, so a
    non-last-day wakeup costs nothing and leaves no trace.
    """
    return (now + timedelta(days=1)).month != now.month


# ── job_run bookkeeping ───────────────────────────────────────────────────────

async def _reclaim_job_run(db, job_name: str, run_key: str):
    """Take over an existing job_run row for a period that did not succeed.

    CATCH-UP ONLY. This is the other half of the gap query: a run_key with a
    'failed' or crashed-'running' row IS a missed period, but the unique index
    would make _open_job_run answer "already ran" and the catch-up would repair
    nothing — the #1 failure mode, silently unfixable. So the collision is read
    rather than assumed.

    The four cases, and why each is what it is:
      succeeded  -> None. The period is done; nothing to repair.
      failed     -> reclaim. This is exactly what catch-up is for.
      running, started < now - STALE_RUNNING_AFTER -> reclaim. finished_at NULL
                    with a stale start is the crash signature 059 records.
      running, started recently -> None. A run is genuinely in flight; two
                    dispatches for one period is the thing the index prevents.

    Reclaiming RESETS the counts to NULL rather than keeping the failed run's
    numbers. 059's rule is that NULL means "never got that far", and a fresh
    attempt has not got anywhere yet; carrying the old counts forward would
    describe the previous attempt while claiming to describe this one.

    Re-dispatch is safe for users who already received a letter for the period:
    the generator's own per-user dedup (weekly_letters, user+period_start+kind,
    excluding 'failed') skips them before any LLM call or email.
    """
    from sqlalchemy import select

    from models import JobRun

    existing = (await db.execute(
        select(JobRun).where(JobRun.job_name == job_name, JobRun.run_key == run_key)
    )).scalar_one_or_none()

    if existing is None:
        # The colliding row disappeared between the failed INSERT and this read.
        # Nothing sane deletes job_run rows, so this means something unusual is
        # happening and guessing is worse than declining.
        logger.warning(
            "Cron: %s run_key=%s collided but no row could be read — not reclaiming",
            job_name, run_key,
        )
        return None

    if existing.status == "succeeded":
        logger.info(
            "Cron: %s run_key=%s already succeeded — nothing to catch up",
            job_name, run_key,
        )
        return None

    if existing.status == "running":
        age_cutoff = datetime.now(timezone.utc) - STALE_RUNNING_AFTER
        if existing.started_at is not None and existing.started_at >= age_cutoff:
            logger.info(
                "Cron: %s run_key=%s is still running (started %s) — not reclaiming",
                job_name, run_key, existing.started_at,
            )
            return None

    logger.info(
        "Cron: reclaiming %s run_key=%s (was status=%s, started %s)",
        job_name, run_key, existing.status, existing.started_at,
    )
    existing.status = "running"
    existing.started_at = datetime.now(timezone.utc)
    existing.finished_at = None
    existing.error = None
    existing.candidate_count = None
    existing.selected_count = None
    existing.enqueued_count = None
    await db.commit()
    return existing


async def _open_job_run(db, job_name: str, run_key: str, *, reclaim: bool = False):
    """Open a 'running' row for this (job, period), or return None to skip.

    RETURNING None MEANS "DO NOT RUN", not "failed". The insert races against
    uq_job_run_name_key (059), so the unique index — not a check-then-act read —
    is what decides. That closes three cases at once with no extra code: two
    workers waking together, a redeploy re-firing a schedule, and the monthly
    job's day={28,29,30,31} window if the last-day guard were ever wrong.

    The row is opened BEFORE the work, which is the only ordering under which the
    index can prevent a double dispatch. Opening it afterwards would record runs
    accurately and prevent nothing.

    reclaim=False is the LIVE CRON path and is unchanged: a collision means the
    period already ran, full stop. Only catch-up passes reclaim=True, and only it
    may take over a row — see _reclaim_job_run for the four cases.
    """
    from models import JobRun

    run = JobRun(job_name=job_name, run_key=run_key, status="running")
    db.add(run)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if not reclaim:
            logger.info(
                "Cron: %s already ran for run_key=%s — skipping", job_name, run_key,
            )
            return None
        return await _reclaim_job_run(db, job_name, run_key)
    return run


async def _close_job_run(db, run, *, status: str, candidate=None, selected=None,
                         enqueued=None, error=None) -> None:
    """Close a run: counts, finished_at, and how it ended.

    The counts stay None unless a value is passed. 059's rule: NULL is "never got
    that far", 0 is "counted, and there were none" — so a crash before the
    eligibility query must leave them NULL rather than claim zero. Callers pass
    each count only once it has genuinely been computed.

    Best-effort by design. This runs in the failure path too, and a letter run
    that already failed must not also raise out of its own bookkeeping.
    """
    if run is None:
        return
    try:
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        if candidate is not None:
            run.candidate_count = candidate
        if selected is not None:
            run.selected_count = selected
        if enqueued is not None:
            run.enqueued_count = enqueued
        if error is not None:
            # TEXT column, but a driver traceback can be enormous and this is an
            # operator hint, not a log. The full trace goes to Render and Sentry
            # via the logger.error below.
            run.error = error[:2000]
        await db.commit()
    except Exception as e:
        logger.error("Cron: failed to close job_run %s: %s", run_key_of(run), e, exc_info=True)


def run_key_of(run) -> str:
    """(job_name, run_key) for a log line, tolerant of a half-built row."""
    return f"{getattr(run, 'job_name', '?')}/{getattr(run, 'run_key', '?')}"


# ── Catch-up: which period, and was it missed? ────────────────────────────────

async def _period_succeeded(db, job_name: str, run_key: str) -> bool:
    """Did this (job, period) ever finish successfully?

    A run_key with NO row, a 'failed' row, or a 'running' row that never closed
    all count as MISSED. Only 'succeeded' is done. That is the whole gap query,
    and it is deliberately this small: every richer definition ("succeeded but
    enqueued zero", "succeeded but the letters failed") is a question about the
    LETTERS, not about the run, and belongs to a different tool.
    """
    from sqlalchemy import select

    from models import JobRun

    found = (await db.execute(
        select(JobRun.id).where(
            JobRun.job_name == job_name,
            JobRun.run_key == run_key,
            JobRun.status == "succeeded",
        )
    )).scalar_one_or_none()
    return found is not None


async def _history_floor(db, job_name: str):
    """The earliest run this job has any record of, or None if it has none.

    THE FLOOR EXISTS BECAUSE ABSENCE OF HISTORY IS NOT EVIDENCE OF A MISS. No
    job_run row predates PR-B, so every period before the first row is "missed"
    by the gap query and by nothing else. Without this, the first catch-up after
    deploy would re-dispatch a week that was delivered normally by the
    APScheduler dispatch, and the reader would get a duplicate — or, once the
    lookback is one period, at least one wrong letter.

    A timestamp rather than a min(run_key): lexicographic ordering happens to
    work for both key formats today (%V zero-pads, so W05 < W09 < W36), but that
    is a property of the format rather than of the data, and a future key shape
    would break it silently.
    """
    from sqlalchemy import func, select

    from models import JobRun

    return (await db.execute(
        select(func.min(JobRun.started_at)).where(JobRun.job_name == job_name)
    )).scalar_one_or_none()


async def _catch_up(ctx, *, job_name: str, run_key: str, period_end: datetime, dispatch):
    """Shared body for both catch-up passes: floor, gap, then re-dispatch.

    ONE PERIOD OF LOOKBACK, NEVER MORE (R8a). Older gaps are repaired by hand
    with an explicit run_key. Three backdated letters arriving together on a
    Monday morning reads as a broken product, not as a repair — and the letters
    carry their own dates, so the reader can see they are stale.
    """
    from db.session import AsyncSessionLocal

    # Swallowed and logged, like every other cron job in this codebase. The
    # dispatch call below has its own handler and never raises; what this guards
    # is the floor and gap queries, which touch the database before any job_run
    # row exists to record a failure. logger.error(exc_info=True) is the Sentry
    # path (observability.py; R9a) — no explicit capture_exception.
    try:
        async with AsyncSessionLocal() as db:
            floor = await _history_floor(db, job_name)
            if floor is None:
                logger.info(
                    "Cron: no %s history yet — nothing can be missed, skipping catch-up",
                    job_name,
                )
                return
            if period_end < floor:
                logger.info(
                    "Cron: %s run_key=%s predates the first recorded run (%s) — skipping",
                    job_name, run_key, floor,
                )
                return
            if await _period_succeeded(db, job_name, run_key):
                logger.info("Cron: %s run_key=%s already succeeded — no catch-up needed",
                            job_name, run_key)
                return

        logger.info("Cron: %s run_key=%s was missed — catching up", job_name, run_key)
        await dispatch(ctx, run_key=run_key)
    except Exception as e:
        logger.error(
            f"Cron {job_name} catch-up failed for run_key={run_key}: {e}", exc_info=True,
        )


async def catch_up_weekly_letters(ctx):
    """Monday 09:00 UTC — re-dispatch last week's letters if Sunday never ran.

    Fifteen hours after the Sunday 18:00 dispatch, and before most readers'
    Monday morning. The key is the ISO week of YESTERDAY, which on a Monday is
    the week that just ended — the same key Sunday's run would have written.
    """
    now = datetime.now(timezone.utc)
    run_key = weekly_run_key(now - timedelta(days=1))
    _, period_end = week_period(run_key)
    await _catch_up(
        ctx, job_name=JOB_WEEKLY, run_key=run_key, period_end=period_end,
        dispatch=dispatch_weekly_letters,
    )


async def catch_up_monthly_letters(ctx):
    """2nd of the month 09:00 UTC — re-dispatch last month if its run never fired.

    The key is the month of the LAST DAY of the previous month, reached by
    stepping back one day from the 1st. Not `now.month - 1`, which is wrong every
    January.
    """
    now = datetime.now(timezone.utc)
    run_key = monthly_run_key(now.replace(day=1) - timedelta(days=1))
    _, period_end = month_period(run_key)
    await _catch_up(
        ctx, job_name=JOB_MONTHLY, run_key=run_key, period_end=period_end,
        dispatch=dispatch_monthly_letters,
    )


# ── Weekly ────────────────────────────────────────────────────────────────────

async def dispatch_weekly_letters(ctx, run_key: str | None = None):
    """Sunday 18:00 UTC — enqueue a weekly letter for users with >=5 acts in the
    ISO week, where an act is a user message OR a ritual (council session,
    generated counterview rebuttal, annotated mirror, you-vs-you). Voiced by the
    persona they conversed with most that week; for a week with no chat at all, by
    their mirror host (A18).

    run_key=None is the LIVE run: the key is this moment's ISO week and the window
    ends now. A key passed in makes this a CATCH-UP for a past week: the window is
    that whole week, and the job_run row may be reclaimed (R8). Live runs never
    reclaim.
    """
    logger.info("Cron: dispatching weekly letters")
    from db.session import AsyncSessionLocal

    catch_up = run_key is not None
    now = datetime.now(timezone.utc)
    if run_key is None:
        run_key = weekly_run_key(now)
        period_start, _ = week_period(run_key)
        # The live window ends NOW, not at Sunday 23:59:59: material created in
        # the six hours after dispatch belongs to the next letter, not to one
        # that has already been written.
        period_end = now
    else:
        period_start, period_end = week_period(run_key)

    async with AsyncSessionLocal() as run_db:
        run = await _open_job_run(run_db, JOB_WEEKLY, run_key, reclaim=catch_up)
        if run is None:
            return

        try:
            from collections import defaultdict

            from sqlalchemy import func, select

            from models import Conversation, Message, Persona, User
            from workers.arq_worker import ritual_counts_by_user

            async with AsyncSessionLocal() as db:
                # Fetch per-(user, persona) message counts for the window
                result = await db.execute(
                    select(
                        Conversation.user_id,
                        Conversation.persona_id,
                        func.count(Message.id).label("msg_count"),
                    )
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(
                        Message.role == "user",
                        Message.created_at >= period_start,
                        Message.created_at <= period_end,
                    )
                    .group_by(Conversation.user_id, Conversation.persona_id)
                    .order_by(
                        Conversation.user_id,
                        func.count(Message.id).desc(),
                        Conversation.persona_id.asc(),  # deterministic tie-break
                    )
                )
                rows = result.all()

            # Group by user; keep only users with total >=5 messages; pick top persona
            user_persona_counts: dict = defaultdict(list)
            for row in rows:
                user_persona_counts[str(row.user_id)].append((str(row.persona_id), row.msg_count))

            # A18 — the week is chat AND rituals. Counting messages alone enqueued ZERO
            # letters on 2026-08-16 for a user who spent the week in 1 council, 3
            # counterview rebuttals, 2 mirror notes and a you-vs-you. The ritual count
            # comes from the SAME helper the generator's quiet-week gate uses, so cron
            # and the generator can never disagree about whether a week happened.
            async with AsyncSessionLocal() as db:
                ritual_counts = await ritual_counts_by_user(db, period_start, period_end)

            # candidate_count (R3): everyone with at least one act in the window,
            # before the >=5 threshold. Written as soon as it is known, so a crash
            # in voice election still leaves the population on record.
            candidate_ids = set(user_persona_counts) | set(ritual_counts)
            run.candidate_count = len(candidate_ids)
            await run_db.commit()

            targets: list[tuple[str, str]] = []  # [(user_id, persona_id)]
            ritual_only: list[str] = []          # eligible, but no chat to elect a voice
            for uid in candidate_ids:
                entries = user_persona_counts.get(uid, [])
                total = sum(c for _, c in entries) + ritual_counts.get(uid, 0)
                if total < 5:
                    continue
                if entries:
                    top_persona_id = entries[0][0]  # already ordered desc by count, asc by id
                    targets.append((uid, top_persona_id))
                else:
                    # Voice election is UNCHANGED for anyone who chatted. With zero chat
                    # there is no top persona to elect, so the letter is voiced by the
                    # mirror host — an explicit user choice with a shipped default,
                    # resolved with the same expression insight_mirror_service uses.
                    ritual_only.append(uid)

            if ritual_only:
                async with AsyncSessionLocal() as db:
                    host_result = await db.execute(
                        select(User.id, User.mirror_host_slug).where(User.id.in_(ritual_only))
                    )
                    host_by_user = {str(r.id): (r.mirror_host_slug or "carl_jung") for r in host_result.all()}
                    wanted = set(host_by_user.values()) or {"carl_jung"}
                    pid_result = await db.execute(
                        select(Persona.id, Persona.slug).where(Persona.slug.in_(wanted))
                    )
                    id_by_slug = {r.slug: str(r.id) for r in pid_result.all()}
                for uid in ritual_only:
                    pid = id_by_slug.get(host_by_user.get(uid, "carl_jung"))
                    if pid:
                        targets.append((uid, pid))
                    else:
                        logger.warning(f"Cron: no persona row for weekly-letter fallback voice, user={uid}")

            if not targets:
                logger.info("Cron: no weekly-letter-eligible users")
                # 0, not NULL: the query ran and nobody cleared the bar. That is a
                # different fact from a run that died before looking.
                await _close_job_run(
                    run_db, run, status="succeeded", selected=0, enqueued=0,
                )
                return

            # Resolve persona_ids → slugs in one query
            async with AsyncSessionLocal() as db:
                persona_ids = list({pid for _, pid in targets})
                slug_result = await db.execute(
                    select(Persona.id, Persona.slug).where(Persona.id.in_(persona_ids))
                )
                id_to_slug = {str(r.id): r.slug for r in slug_result.all()}

            dispatched = 0
            for uid, pid in targets:
                slug = id_to_slug.get(pid)
                if slug:
                    await ctx["redis"].enqueue_job(
                        "generate_weekly_letter_task", uid, slug,
                        period_start.isoformat(), period_end.isoformat(),
                    )
                    dispatched += 1

            logger.info(f"Cron: enqueued {dispatched} weekly letters")
            await _close_job_run(
                run_db, run, status="succeeded",
                selected=len(targets), enqueued=dispatched,
            )
        except Exception as e:
            # The durable failure record is the job_run row; this log line is the
            # alert. NO capture_exception here, deliberately (R9a): Sentry's
            # LoggingIntegration turns every logger.error into an event at
            # event_level=ERROR (observability.py, pinned by test_observability),
            # so an explicit capture would report twice.
            logger.error(f"Cron weekly letters failed: {e}", exc_info=True)
            await _close_job_run(run_db, run, status="failed", error=str(e))


# ── Monthly ───────────────────────────────────────────────────────────────────

async def dispatch_monthly_letters(ctx, run_key: str | None = None):
    """Last day of month 17:00 UTC — enqueue a monthly 'season' letter for users
    with >= MONTHLY_MIN_MESSAGES acts this calendar month, where an act is a user
    message OR a ritual (council session, generated counterview rebuttal,
    annotated mirror, you-vs-you). Voiced by the persona they conversed with most
    that month; for a month with no chat at all, by their mirror host
    (A18-monthly).

    The schedule fires on day={28,29,30,31}; the last-day guard below discards the
    runs that are not the final day, BEFORE any database access. A run_key passed
    in makes this a CATCH-UP for a past month and skips that guard entirely — the
    2nd of the month is not the last day of anything.
    """
    catch_up = run_key is not None
    now = datetime.now(timezone.utc)

    if run_key is None:
        if not is_last_day_of_month(now):
            # Not an error and not worth an INFO on three days out of four in most
            # months — this is the schedule doing exactly what it was built to do.
            logger.debug("Cron: monthly letters skipped, %s is not the last of the month", now.date())
            return
        run_key = monthly_run_key(now)
        period_start, _ = month_period(run_key)
        period_end = now
    else:
        period_start, period_end = month_period(run_key)

    logger.info("Cron: dispatching monthly letters")
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as run_db:
        run = await _open_job_run(run_db, JOB_MONTHLY, run_key, reclaim=catch_up)
        if run is None:
            return

        try:
            from collections import defaultdict

            from sqlalchemy import func, select

            from models import Conversation, Message, Persona, User
            from workers.arq_worker import MONTHLY_MIN_MESSAGES, ritual_counts_by_user

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(
                        Conversation.user_id,
                        Conversation.persona_id,
                        func.count(Message.id).label("msg_count"),
                    )
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(
                        Message.role == "user",
                        Message.created_at >= period_start,
                        Message.created_at <= period_end,
                    )
                    .group_by(Conversation.user_id, Conversation.persona_id)
                    .order_by(
                        Conversation.user_id,
                        func.count(Message.id).desc(),
                        Conversation.persona_id.asc(),  # deterministic tie-break
                    )
                )
                rows = result.all()

            user_persona_counts: dict = defaultdict(list)
            for row in rows:
                user_persona_counts[str(row.user_id)].append((str(row.persona_id), row.msg_count))

            # A18-monthly — the month is chat AND rituals, mirroring the weekly dispatch.
            # Same shared helper the generator's quiet-month gate uses, over the SAME
            # window the generator will use: since PR-C the period is computed once here
            # and passed to the task, so the two can no longer disagree at all.
            async with AsyncSessionLocal() as db:
                ritual_counts = await ritual_counts_by_user(db, period_start, period_end)

            candidate_ids = set(user_persona_counts) | set(ritual_counts)
            run.candidate_count = len(candidate_ids)
            await run_db.commit()

            targets: list[tuple[str, str]] = []  # [(user_id, persona_id)]
            ritual_only: list[str] = []          # eligible, but no chat to elect a voice
            for uid in candidate_ids:
                entries = user_persona_counts.get(uid, [])
                total = sum(c for _, c in entries) + ritual_counts.get(uid, 0)
                if total < MONTHLY_MIN_MESSAGES:
                    continue
                if entries:
                    top_persona_id = entries[0][0]  # ordered desc by count, asc by id
                    targets.append((uid, top_persona_id))
                else:
                    # Voice election is UNCHANGED for anyone who chatted. With zero chat
                    # there is no top persona to elect, so the season letter is voiced by the
                    # mirror host — the same expression the weekly dispatch uses.
                    ritual_only.append(uid)

            if ritual_only:
                async with AsyncSessionLocal() as db:
                    host_result = await db.execute(
                        select(User.id, User.mirror_host_slug).where(User.id.in_(ritual_only))
                    )
                    host_by_user = {str(r.id): (r.mirror_host_slug or "carl_jung") for r in host_result.all()}
                    wanted = set(host_by_user.values()) or {"carl_jung"}
                    pid_result = await db.execute(
                        select(Persona.id, Persona.slug).where(Persona.slug.in_(wanted))
                    )
                    id_by_slug = {r.slug: str(r.id) for r in pid_result.all()}
                for uid in ritual_only:
                    pid = id_by_slug.get(host_by_user.get(uid, "carl_jung"))
                    if pid:
                        targets.append((uid, pid))
                    else:
                        logger.warning(f"Cron: no persona row for monthly-letter fallback voice, user={uid}")

            if not targets:
                logger.info("Cron: no monthly-letter-eligible users")
                await _close_job_run(
                    run_db, run, status="succeeded", selected=0, enqueued=0,
                )
                return

            async with AsyncSessionLocal() as db:
                persona_ids = list({pid for _, pid in targets})
                slug_result = await db.execute(
                    select(Persona.id, Persona.slug).where(Persona.id.in_(persona_ids))
                )
                id_to_slug = {str(r.id): r.slug for r in slug_result.all()}

            dispatched = 0
            for uid, pid in targets:
                slug = id_to_slug.get(pid)
                if slug:
                    await ctx["redis"].enqueue_job(
                        "generate_monthly_letter_task", uid, slug,
                        period_start.isoformat(), period_end.isoformat(),
                    )
                    dispatched += 1

            logger.info(f"Cron: enqueued {dispatched} monthly letters")
            await _close_job_run(
                run_db, run, status="succeeded",
                selected=len(targets), enqueued=dispatched,
            )
        except Exception as e:
            # See the weekly handler: R9a — one Sentry event, via logger.error.
            logger.error(f"Cron monthly letters failed: {e}", exc_info=True)
            await _close_job_run(run_db, run, status="failed", error=str(e))
