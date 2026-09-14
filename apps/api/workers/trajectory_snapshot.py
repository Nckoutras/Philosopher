"""Weekly trajectory snapshots — an ARQ cron dispatch plus a per-user job.

WHAT THIS IS. Once a week, for each person who did anything that week, record
what kept returning: the things they wrote in the period that echo things they
wrote before it. The record goes in trajectory_snapshots (061) and NOTHING READS
IT YET. Step D — the Sunday letter — is the intended reader; this file only
starts the history it will read.

WHY IT DISPATCHES INSTEAD OF LOOPING INLINE. WorkerSettings.job_timeout is 90s
and a cron_jobs entry cannot carry the per-function `func(fn, timeout=…)`
override that the two letter tasks use. An inline loop over every eligible user
would therefore be a cliff that appears exactly when the user count rises, and
fails as a timeout with a partial run behind it. So the shape is the letters'
shape: one dispatch that opens a job_run row, counts, and enqueues; one job per
user that does the work and owns its own row's status.

THE SCHEDULE IS SUNDAY 17:00 UTC, ONE HOUR BEFORE THE LETTER. That hour is
deliberate headroom for the fan-out to drain before step D would read it, and it
has one visible consequence worth stating rather than discovering: the live
window ends at 17:00, so material created in the hour between the snapshot and
the letter is in the LETTER's window and not in the snapshot's. It lands in next
week's snapshot instead. The alternative — snapshotting the full week to
23:59:59 — would mean reading a period that has not finished, which is the
mistake the letter's live path already avoids by ending its window at `now`.

IMPORTS OF arq_worker STAY INSIDE THE FUNCTION BODIES, exactly as
letter_dispatch says and for the same reason: arq_worker imports THIS module at
module level, because WorkerSettings needs both coroutines by reference. A
top-level `from workers.arq_worker import ritual_counts_by_user` here would be a
cycle. The import from workers.letter_dispatch below is NOT a cycle — that module
imports nothing from this one, and arq_worker already imports it at module level.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from workers.letter_dispatch import (
    _close_job_run,
    _open_job_run,
    week_period,
    weekly_run_key,
)

logger = logging.getLogger(__name__)

# job_run.job_name. A named constant for the reason letter_dispatch names its
# two: the (job_name, run_key) unique index is only an idempotency key if both
# halves are spelled the same way every time.
JOB_WEEKLY_TRAJECTORY = "weekly_trajectory_snapshot"

# trajectory_snapshots.kind. v1 has one cadence; the column and the unique index
# carry it so a later 'monthly' needs no migration.
KIND_WEEKLY = "weekly"

# payload.version. Bumped when the SHAPE changes in a way step D would have to
# handle — adding a field is not a break, renaming or re-nesting one is. This is
# the same rule data_export_service applies to its SCHEMA_VERSION.
PAYLOAD_VERSION = 1

# How many in-period entries are used as QUERIES, newest first. A bound rather
# than the whole week because each one is a separate pgvector search: a heavy
# week would otherwise turn one user's snapshot into an unbounded number of
# index scans. 40 is far above any real week measured so far and exists to cap
# the tail, not to shape the result.
MAX_QUERY_ENTRIES = 40

# How many matches are DENORMALISED into the payload per recurring question. The
# true count is recorded beside them as `match_count`, so the cap loses ordering
# detail rather than the fact of the match — the same NULL-vs-0 spirit 059 keeps
# for its counts. Matches arrive best-first (find_recurrences orders by cosine
# distance), so this keeps the strongest.
MAX_MATCHES_PER_QUESTION = 5

# changes_since_prior reasons. A closed vocabulary, pinned in the tests, because
# step D will branch on it and a free-form string is not something a reader can
# branch on safely.
NO_PRIOR_SNAPSHOT = "no_prior_snapshot"
PRIOR_SNAPSHOT_HAS_NO_PAYLOAD = "prior_snapshot_has_no_payload"


def _iso_z(value: datetime | None) -> str | None:
    """UTC ISO-8601 with an explicit Z, matching how the export renders times.

    A naive value is treated as UTC rather than dropped: every writer in this
    codebase uses datetime.now(timezone.utc), so naive is a storage artefact and
    not a different instant.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_utc(value) -> datetime:
    """An ISO string or datetime in, a TIMEZONE-AWARE UTC datetime out.

    TD-76 / #645: a timestamptz parameter must be bound from a datetime object,
    never from an ISO string, and a naive datetime compared against timestamptz
    is interpreted in the server's timezone rather than in UTC. Both period
    bounds cross Redis as strings (the letter task does the same, for the same
    readability reason), so this is the one place they are turned back.
    """
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# ── Dispatch ─────────────────────────────────────────────────────────────────

async def snapshot_weekly_trajectories(ctx, run_key: str | None = None):
    """Sunday 17:00 UTC — enqueue a trajectory snapshot for every user with >=1
    act in the ISO week, where an act is a user message OR a ritual.

    THE SNAPSHOT CHAIN CANNOT PRECEDE ITS SHIP DATE. This job writes one row per
    eligible user per week, starting with the first week it is deployed for.
    There is no backfill and there cannot be one that means anything: a snapshot
    is built against the memory corpus AS IT STOOD at the period boundary, and
    rows deactivated or conversations deleted since then have already changed
    that corpus. So a "what has changed over six months" question is answered by
    `WHERE period_start >= <the first deployed run>` and by nothing earlier, and
    CALLERS MUST NOT ASSUME HISTORY BEFORE THAT DATE. An absent week before the
    first run is not a quiet week; it is a week nobody looked at. Step D has to
    render those two differently or it will tell people something untrue about
    their own past.

    ELIGIBILITY IS >=1 ACT, AND IT IS THE LETTER'S CANDIDATE SET VERBATIM — the
    union of "wrote a user message" and "did a ritual", from the same
    ritual_counts_by_user helper the letter dispatch and the generator's
    quiet-week gate both use, so the three can never disagree about whether a
    week happened. The letter's >=5 bar is NOT applied here: that bar decides who
    is worth writing a letter to, which is a different question from whose week
    is worth recording. A user with 0 acts gets NO ROW — not an 'empty' row. See
    061's docstring for why that distinction is load-bearing.

    run_key=None is the LIVE run: the key is this moment's ISO week and the
    window ends now. A key passed in makes this a catch-up for a past week — the
    window is that whole week and the job_run row may be reclaimed. Live runs
    never reclaim. No catch-up cron is registered for this job yet; the parameter
    exists so a missed week can be repaired by hand with an explicit key, which
    uq_job_run_name_key makes safe to invoke twice.
    """
    logger.info("Cron: dispatching weekly trajectory snapshots")
    from db.session import AsyncSessionLocal

    catch_up = run_key is not None
    now = datetime.now(timezone.utc)
    if run_key is None:
        run_key = weekly_run_key(now)
        period_start, _ = week_period(run_key)
        # Ends NOW, not at Sunday 23:59:59 — see the module docstring on the
        # one-hour sliver this leaves to next week.
        period_end = now
    else:
        period_start, period_end = week_period(run_key)

    async with AsyncSessionLocal() as run_db:
        run = await _open_job_run(
            run_db, JOB_WEEKLY_TRAJECTORY, run_key, reclaim=catch_up,
        )
        if run is None:
            return

        try:
            async with AsyncSessionLocal() as db:
                eligible = await eligible_user_ids(db, period_start, period_end)

            # candidate_count, written as soon as it is known so a crash in the
            # enqueue loop still leaves the population on record (059's R3).
            run.candidate_count = len(eligible)
            await run_db.commit()

            if not eligible:
                logger.info("Cron: no trajectory-snapshot-eligible users")
                # 0, not NULL: the query ran and nobody was active. Different
                # from a run that died before looking.
                await _close_job_run(
                    run_db, run, status="succeeded", selected=0, enqueued=0,
                )
                return

            # selected_count equals candidate_count BY CONSTRUCTION here, and the
            # column is filled anyway rather than left NULL: >=1 act is both the
            # eligibility gate and the selection, so there is no second bar to
            # narrow the set. Leaving it NULL would read as "never got that far".
            enqueued = 0
            for uid in sorted(eligible):
                await ctx["redis"].enqueue_job(
                    "build_trajectory_snapshot_task", uid,
                    period_start.isoformat(), period_end.isoformat(),
                )
                enqueued += 1

            logger.info("Cron: enqueued %d trajectory snapshots", enqueued)
            await _close_job_run(
                run_db, run, status="succeeded",
                selected=len(eligible), enqueued=enqueued,
            )
        except Exception as e:
            # The durable failure record is the job_run row; this log line is the
            # alert. NO capture_exception, following letter_dispatch (R9a):
            # Sentry's LoggingIntegration already turns logger.error into an
            # event, so an explicit capture would report twice.
            logger.error("Cron trajectory snapshots failed: %s", e, exc_info=True)
            await _close_job_run(run_db, run, status="failed", error=str(e))


async def eligible_user_ids(db, period_start: datetime, period_end: datetime) -> set[str]:
    """Users with >=1 act in the window: a user message OR a ritual.

    THE LETTER'S candidate_ids EXPRESSION, reproduced rather than re-invented —
    the same message query and the same ritual_counts_by_user call, unioned the
    same way (letter_dispatch.dispatch_weekly_letters). A second, subtly
    different definition of "an act" is exactly the drift this reuse avoids.
    """
    from sqlalchemy import select

    from models import Conversation, Message
    from workers.arq_worker import ritual_counts_by_user

    # DISTINCT rather than the letter's GROUP BY + count: the letter needs
    # per-persona counts to elect a voice and a total to compare against 5.
    # Neither applies here — the only question is whether the person appears at
    # all — and a count this code would immediately discard would read as a
    # threshold that is not there.
    result = await db.execute(
        select(Conversation.user_id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(
            Message.role == "user",
            Message.created_at >= period_start,
            Message.created_at <= period_end,
        )
        .distinct()
    )
    message_users = {str(r.user_id) for r in result.all()}

    ritual_counts = await ritual_counts_by_user(db, period_start, period_end)
    return message_users | set(ritual_counts)


# ── The snapshot itself ──────────────────────────────────────────────────────

async def recurring_questions(db, user_id: str, period_start: datetime,
                              period_end: datetime) -> list[dict]:
    """The in-period entries that echo something written before the period.

    TWO DATE FILTERS, AND CONFLATING THEM IS A SILENT WRONG ANSWER — the naming
    in find_recurrences exists for this call site. The QUERIES are selected here,
    by period: entries written during the week. The CORPUS is bounded there, by
    `corpus_until=period_start`: entries written strictly before the week. Pass
    the window to the wrong side and the week is compared against itself.

    corpus_since stays None: the corpus is the person's whole history up to the
    boundary, which is what makes "this keeps coming back" mean anything.

    THE LOOP LIVES HERE, not in find_recurrences, and it does not break early —
    detect_recurrence stops at the first hit because it writes one card; a
    snapshot wants every hit. That difference is the reason the seam exists.
    """
    from sqlalchemy import select

    from models import MemoryEntry
    from services.memory_service import find_recurrences

    entries = (await db.execute(
        select(MemoryEntry)
        .where(
            MemoryEntry.user_id == user_id,
            MemoryEntry.is_active.is_(True),
            MemoryEntry.embedding.isnot(None),
            MemoryEntry.created_at >= period_start,
            MemoryEntry.created_at <= period_end,
        )
        .order_by(MemoryEntry.created_at.desc())
        .limit(MAX_QUERY_ENTRIES)
    )).scalars().all()

    questions: list[dict] = []
    for entry in entries:
        # No exclude_conversation: corpus_until already puts the whole period
        # out of the corpus, so an in-period entry cannot reach its own
        # conversation. find_recurrences excludes the row by its own id anyway.
        found = await find_recurrences(
            db, user_id, entry, corpus_until=period_start,
        )
        if found is None:
            continue
        matches, evidence = found
        prior = evidence["prior_matches"]
        questions.append({
            **evidence["recurring_entry"],
            # The TRUE number above the bar, beside a capped list of the
            # strongest. The cap loses ordering detail, never the fact.
            "match_count": len(prior),
            "top_score": prior[0]["score"] if prior else None,
            "prior_matches": prior[:MAX_MATCHES_PER_QUESTION],
        })
    return questions


def _anchor_ids(questions) -> set[str]:
    """The ids of the OLDER entries a set of recurring questions echoes.

    THE ANCHOR IS THE ECHOED MATERIAL, NOT THE QUERY ENTRY, and the choice is
    load-bearing. A query entry was by definition written during its own period,
    so week-over-week it is always a different row: comparing query entries would
    report total turnover every single week and measure nothing at all. What
    persists across weeks is the earlier material being returned to.

    THE LIMIT, NAMED: these ids are row identities, not meanings. The same
    thought re-extracted into a new memory row reads as a different anchor, so
    'new_since_prior' overstates novelty and 'absent_since_prior' overstates
    departure. And because the stored list is capped at MAX_MATCHES_PER_QUESTION,
    an anchor can go 'absent' merely by slipping out of the strongest few. This
    is a set comparison over ids; it is not a semantic diff, and step D must not
    render it as one.
    """
    return {
        m["memory_entry_id"]
        for q in (questions or [])
        for m in (q.get("prior_matches") or [])
    }


def changes_since_prior(questions, prior) -> tuple[dict | None, str | None]:
    """(changes, reason). Exactly one of the two is None.

    FIRST RUN PER USER IS null PLUS A REASON, not a zeroed diff. "Nothing changed
    since last week" and "there was no last week" are different facts, and an
    all-empty change record would state the first while meaning the second — the
    same failure 059 avoids with NULL-vs-0 counts. The reason is a value from a
    closed vocabulary rather than prose, because step D branches on it.
    """
    if prior is None:
        return None, NO_PRIOR_SNAPSHOT
    prior_payload = prior.payload or {}
    if not prior_payload:
        # A 'generated' or 'empty' row always carries a payload, so this is a
        # row written by something other than this job — recorded, not guessed at.
        return None, PRIOR_SNAPSHOT_HAS_NO_PAYLOAD

    now_anchors = _anchor_ids(questions)
    was_anchors = _anchor_ids(prior_payload.get("recurring_questions"))
    still = sorted(now_anchors & was_anchors)
    new = sorted(now_anchors - was_anchors)
    absent = sorted(was_anchors - now_anchors)
    return {
        "prior_period_start": _iso_z(prior.period_start),
        "prior_status": prior.status,
        "still_recurring": still,
        "new_since_prior": new,
        "absent_since_prior": absent,
        "counts": {
            "still_recurring": len(still),
            "new_since_prior": len(new),
            "absent_since_prior": len(absent),
        },
    }, None


async def _prior_snapshot(db, user_id: str, period_start: datetime):
    """The most recent snapshot for this user strictly before this period.

    'failed' rows are excluded: such a row records that we do not know what that
    week held, so diffing against it would compare this week to an unknown and
    report the difference as fact. The comparison reaches past it to the last
    week we actually looked at, and prior_period_start in the payload says which
    week that was rather than leaving a reader to assume it was the last one.
    """
    from sqlalchemy import select

    from models import TrajectorySnapshot

    return (await db.execute(
        select(TrajectorySnapshot)
        .where(
            TrajectorySnapshot.user_id == user_id,
            TrajectorySnapshot.kind == KIND_WEEKLY,
            TrajectorySnapshot.period_start < period_start,
            TrajectorySnapshot.status.in_(("generated", "empty")),
        )
        .order_by(TrajectorySnapshot.period_start.desc())
        .limit(1)
    )).scalars().first()


async def build_trajectory_snapshot_task(ctx, user_id: str, period_start: str,
                                         period_end: str):
    """Write one user's trajectory_snapshots row for one period.

    THE SNAPSHOT CHAIN CANNOT PRECEDE ITS SHIP DATE — the full statement is on
    snapshot_weekly_trajectories, which is the entry point a reader reaches
    first. In short: rows exist only for weeks this job actually ran, six-month
    questions are answered by `WHERE period_start >= <first deployed run>`, and a
    missing earlier week means nobody looked, not that nothing happened.

    period_start / period_end arrive as ISO-8601 strings because they cross
    Redis, and are turned back into TIMEZONE-AWARE datetimes before any query
    binds them (TD-76 / #645). period_start is both the start of the window and
    the corpus boundary.

    IDEMPOTENCY, IN TWO LAYERS, mirroring the letters. The dispatch layer is
    _open_job_run: a second run for a covered period never enqueues anything,
    because uq_job_run_name_key rejects the row. This layer is the letter task's
    dedup select plus the unique index behind it: an arq retry of an individual
    job finds the row already written and returns. A 'failed' row is the one that
    is overwritten in place — it holds no result, and re-running is the whole
    point of noticing it failed.

    STATUS IS OWNED HERE, NOT BY THE DISPATCH. 'generated' when at least one
    recurrence was found, 'empty' when the person was active and nothing echoed,
    'failed' when this raised. A user with no acts never reaches this function.
    """
    from db.session import AsyncSessionLocal

    from models import TrajectorySnapshot
    from services.memory_service import (
        RECURRENCE_LIMIT,
        RECURRENCE_SIM_THRESHOLD,
    )
    from sqlalchemy import select

    ps = _as_utc(period_start)
    pe = _as_utc(period_end)

    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(TrajectorySnapshot).where(
                TrajectorySnapshot.user_id == user_id,
                TrajectorySnapshot.period_start == ps,
                TrajectorySnapshot.kind == KIND_WEEKLY,
            )
        )).scalars().first()
        if existing is not None and existing.status != "failed":
            logger.info(
                "Trajectory snapshot already written for user=%s period=%s (status=%s)",
                user_id, _iso_z(ps), existing.status,
            )
            return

        try:
            questions = await recurring_questions(db, user_id, ps, pe)
            prior = await _prior_snapshot(db, user_id, ps)
            changes, reason = changes_since_prior(questions, prior)
            payload = {
                "version": PAYLOAD_VERSION,
                "recurring_questions": questions,
                "changes_since_prior": changes,
                "changes_since_prior_reason": reason,
                # The bounds and thresholds this snapshot was actually built
                # with, recorded for the same reason 060 records the detector:
                # they are ship-and-tune values, and a record whose bar is
                # unrecoverable cannot be read. Present on an 'empty' row too —
                # "found nothing" is only meaningful against the bar it cleared.
                "detector": {
                    "threshold": RECURRENCE_SIM_THRESHOLD,
                    "limit": RECURRENCE_LIMIT,
                    "max_query_entries": MAX_QUERY_ENTRIES,
                    "max_matches_per_question": MAX_MATCHES_PER_QUESTION,
                    "window": {"since": None, "until": _iso_z(ps)},
                },
            }
            status = "generated" if questions else "empty"
        except Exception as e:
            # A failed snapshot is still recorded (061): step D must be able to
            # tell "nothing happened" from "we did not manage to look".
            logger.error(
                "Trajectory snapshot FAILED user=%s period=%s: %s",
                user_id, _iso_z(ps), e, exc_info=True,
            )
            status = "failed"
            payload = {"version": PAYLOAD_VERSION, "error": str(e)[:2000]}

        if existing is not None:
            existing.status = status
            existing.payload = payload
            existing.period_end = pe
        else:
            db.add(TrajectorySnapshot(
                user_id=user_id, period_start=ps, period_end=pe,
                kind=KIND_WEEKLY, status=status, payload=payload,
            ))
        try:
            await db.commit()
        except IntegrityError:
            # uq_trajectory_snapshots_user_period_kind. The dedup select above
            # lost a race with a concurrent job for the same user and period —
            # the row exists, which is the outcome wanted, so this is an INFO.
            await db.rollback()
            logger.info(
                "Trajectory snapshot for user=%s period=%s was written concurrently",
                user_id, _iso_z(ps),
            )
            return
        logger.info(
            "Trajectory snapshot %s for user=%s period=%s (%d recurring)",
            status, user_id, _iso_z(ps), len(payload.get("recurring_questions") or []),
        )
