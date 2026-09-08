"""Weekly and monthly letter dispatch — ARQ cron jobs, with a job_run audit row.

WHAT MOVED, AND WHAT DID NOT. The two dispatch bodies below came out of
workers/cron.py (the `weekly_letter` and `monthly_letter` @scheduled_job blocks)
VERBATIM. Their queries, their eligibility arithmetic, their voice election and
their log lines are unchanged. What changed is where they run and what they leave
behind:

  - they run in the ARQ WORKER process, as cron_jobs, not in the API process
    under APScheduler;
  - the enqueue target is ctx['redis'] (an ArqRedis, set by the worker at
    worker.py:361) instead of the closed-over `arq_queue`;
  - each run opens and closes a job_run row.

The generator tasks are untouched. They still compute their own period_start;
nothing here passes a period to them. That is D-2, and it is PR-C.

WHY THE MOVE. Dispatch in the API process leaves no trace of itself. If Sunday
18:00 passes and nothing fires, the only evidence is an absence of letters, which
looks exactly like a week where nobody qualified. It also means the schedule
lives in whichever process happens to be the API — a deploy, a restart or a
crashed lifespan takes the letters with it, silently. job_run is the record; the
worker is where the work already was.

THE NEW FAILURE MODE, STATED PLAINLY: if the ARQ worker service is down, letters
stop and the API still reports healthy. That is a real consequence of this PR.
It is also the thing job_run exists to make visible — an unfinished 'running' row,
or no row at all for a period, is now an answerable question.

IMPORTS OF arq_worker STAY INSIDE THE FUNCTION BODIES. arq_worker imports THIS
module at module level (WorkerSettings needs the two coroutines), so a top-level
`from workers.arq_worker import ...` here would be a cycle. The bodies already
imported that way in cron.py, so nothing had to be rewritten to keep it safe —
the property was already there. Do not lift these imports to the top of the file.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

# job_run.job_name values. Named constants because the (job_name, run_key) unique
# index is only an idempotency key if both halves are spelled the same way every
# time; a typo would silently create a second series of runs that never collide.
JOB_WEEKLY = "weekly_letter"
JOB_MONTHLY = "monthly_letter"


def weekly_run_key(now: datetime) -> str:
    """The ISO week the run covers, e.g. '2026-W36' (R7).

    Derived from the period, never from execution time — though at Sunday 18:00
    those coincide, and deliberately so. ISO weeks start on MONDAY, so a Sunday
    run falls on the LAST day of its own ISO week: %G-W%V therefore names the week
    that is ending, which is the window the letter covers. That is correct but not
    obvious, which is the only reason this function exists instead of an inline
    strftime.
    """
    return now.strftime("%G-W%V")


def monthly_run_key(now: datetime) -> str:
    """The calendar month the run covers, e.g. '2026-09' (R7)."""
    return now.strftime("%Y-%m")


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


async def _open_job_run(db, job_name: str, run_key: str):
    """Open a 'running' row for this (job, period), or return None if one exists.

    RETURNING None MEANS "ALREADY RAN — SKIP", not "failed". The insert races
    against uq_job_run_name_key (059), so the unique index — not a check-then-act
    read — is what decides. That closes three cases at once with no extra code:
    two workers waking together, a redeploy re-firing a schedule, and the monthly
    job's day={28,29,30,31} window if the last-day guard above were ever wrong.

    The row is opened BEFORE the work, which is the only ordering under which the
    index can prevent a double dispatch. Opening it afterwards would record runs
    accurately and prevent nothing.
    """
    from models import JobRun

    run = JobRun(job_name=job_name, run_key=run_key, status="running")
    db.add(run)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "Cron: %s already ran for run_key=%s — skipping", job_name, run_key,
        )
        return None
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


# ── Weekly ────────────────────────────────────────────────────────────────────

async def dispatch_weekly_letters(ctx):
    """Sunday 18:00 UTC — enqueue a weekly letter for users with >=5 acts in the last
    7 days, where an act is a user message OR a ritual (council session, generated
    counterview rebuttal, annotated mirror, you-vs-you). Voiced by the persona they
    conversed with most that week; for a week with no chat at all, by their mirror
    host (A18)."""
    logger.info("Cron: dispatching weekly letters")
    from db.session import AsyncSessionLocal

    now = datetime.now(timezone.utc)
    run_key = weekly_run_key(now)

    async with AsyncSessionLocal() as run_db:
        run = await _open_job_run(run_db, JOB_WEEKLY, run_key)
        if run is None:
            return

        try:
            from models import Message, Conversation, Persona, User
            from sqlalchemy import select, func
            from workers.arq_worker import ritual_counts_by_user

            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
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
                        Message.created_at >= cutoff,
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
            from collections import defaultdict
            user_persona_counts: dict = defaultdict(list)
            for row in rows:
                user_persona_counts[str(row.user_id)].append((str(row.persona_id), row.msg_count))

            # A18 — the week is chat AND rituals. Counting messages alone enqueued ZERO
            # letters on 2026-08-16 for a user who spent the week in 1 council, 3
            # counterview rebuttals, 2 mirror notes and a you-vs-you. The ritual count
            # comes from the SAME helper the generator's quiet-week gate uses, so cron
            # and the generator can never disagree about whether a week happened.
            async with AsyncSessionLocal() as db:
                ritual_counts = await ritual_counts_by_user(
                    db, cutoff, datetime.now(timezone.utc)
                )

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
                    await ctx["redis"].enqueue_job("generate_weekly_letter_task", uid, slug)
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
            # event_level=ERROR (observability.py:37-46, pinned by
            # test_observability), so an explicit capture would report twice.
            logger.error(f"Cron weekly letters failed: {e}", exc_info=True)
            await _close_job_run(run_db, run, status="failed", error=str(e))


# ── Monthly ───────────────────────────────────────────────────────────────────

async def dispatch_monthly_letters(ctx):
    """Last day of month 17:00 UTC — enqueue a monthly 'season' letter for users with
    >= MONTHLY_MIN_MESSAGES acts this calendar month, where an act is a user message
    OR a ritual (council session, generated counterview rebuttal, annotated mirror,
    you-vs-you). Voiced by the persona they conversed with most that month; for a
    month with no chat at all, by their mirror host (A18-monthly).

    The schedule fires on day={28,29,30,31}; the last-day guard below discards the
    runs that are not the final day, BEFORE any database access."""
    now = datetime.now(timezone.utc)
    if not is_last_day_of_month(now):
        # Not an error and not worth an INFO on three days out of four in most
        # months — this is the schedule doing exactly what it was built to do.
        logger.debug("Cron: monthly letters skipped, %s is not the last of the month", now.date())
        return

    logger.info("Cron: dispatching monthly letters")
    from db.session import AsyncSessionLocal

    run_key = monthly_run_key(now)

    async with AsyncSessionLocal() as run_db:
        run = await _open_job_run(run_db, JOB_MONTHLY, run_key)
        if run is None:
            return

        try:
            from models import Message, Conversation, Persona, User
            from sqlalchemy import select, func
            from collections import defaultdict
            from workers.arq_worker import MONTHLY_MIN_MESSAGES, ritual_counts_by_user

            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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
                        Message.created_at >= month_start,
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
            # Same shared helper the generator's quiet-month gate uses. The windows are not
            # identical (cron ends at its own `now`, the generator at the last day 23:59:59)
            # but they agree in the SAFE direction: the generator's window is a superset, so
            # it can never count fewer than cron and a dispatched user cannot fall through
            # into a false 'empty' row.
            async with AsyncSessionLocal() as db:
                ritual_counts = await ritual_counts_by_user(
                    db, month_start, datetime.now(timezone.utc)
                )

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
                    await ctx["redis"].enqueue_job("generate_monthly_letter_task", uid, slug)
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
