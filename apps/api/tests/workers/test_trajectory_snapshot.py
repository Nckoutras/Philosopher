"""Trajectory snapshots: the gate, the two idempotency layers, the three
statuses, and the first-run null.

WHAT THIS PINS. Step C writes trajectory_snapshots (061) and nothing reads it,
so every guarantee here is a guarantee to a caller that does not exist yet. That
makes the assertions MORE load-bearing rather than less: step D will be written
against these shapes, and a wrong one will not be caught by a failing screen.

  - eligibility is >=1 act and the letter's >=5 bar is NOT applied (a user with
    one message must be snapshotted);
  - a user with 0 acts gets NO ROW — not an 'empty' one;
  - the corpus bound goes to corpus_until and the query entries come from the
    period, which are the two halves find_recurrences names apart because
    swapping them is a silent wrong answer;
  - the first run per user is null PLUS a machine-readable reason, never a
    zeroed diff;
  - both idempotency layers hold: the dispatch's job_run collision and the
    task's per-row dedup;
  - 'failed' is recorded rather than swallowed, at both levels.

NO DATABASE HERE. The unique index, the status CHECK and the RLS posture are
properties of Postgres and are asserted in tests/db_live/test_trajectory_snapshots.py,
which is where they belong; a fake cannot enforce an index and pretending
otherwise would be theatre.

FAKES, NOT MagicMock (C-06), following test_letter_dispatch.py. A MagicMock
accepts every attribute write and answers every read, so "was the row written
with status='empty'?" and "was NO row added?" would both be unassertable — it
would answer yes either way.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

import workers.trajectory_snapshot as ts
from workers.arq_worker import WorkerSettings

WEEK = "2026-W38"
PERIOD_START = datetime(2026, 9, 14, tzinfo=timezone.utc)   # Monday of W38
PERIOD_END = datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc)


# ── Fakes ────────────────────────────────────────────────────────────────────

class Row:
    """Plain object, not MagicMock: a Mock supplies every attribute, so a field
    the code stopped reading would still 'pass'."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def scalars(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None


class FakeDB:
    """A session that dispatches execute() on the entity being selected and
    records everything written to it.

    Keyed by mapped-class NAME rather than call order — index-based dispatch is
    what made 17 tests in this repo fail for months (TD-45).
    """

    def __init__(self, tables=None, commit_raises=None):
        self.tables = tables or {}
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self._commit_raises = commit_raises

    async def execute(self, stmt, *a, **kw):
        name = None
        try:
            entity = stmt.column_descriptions[0]["entity"]
            name = entity.__name__
        except Exception:
            pass
        return FakeResult(self.tables.get(name, []))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self._commit_raises is not None:
            exc, self._commit_raises = self._commit_raises, None
            raise exc
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeRun:
    """The job_run row, as _open_job_run hands it back."""

    def __init__(self):
        self.job_name = ts.JOB_WEEKLY_TRAJECTORY
        self.run_key = WEEK
        self.status = "running"
        self.finished_at = None
        self.candidate_count = None
        self.selected_count = None
        self.enqueued_count = None
        self.error = None


class FakeRedis:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args):
        self.jobs.append((name, args))


def _session_factory(db):
    """A stand-in for AsyncSessionLocal handing out the SAME session every time.

    The production code opens several short sessions per run; the fake collapses
    them so a test can assert on one object. That is a simplification of session
    LIFETIME only — nothing under test depends on two sessions being distinct.
    """

    class _Ctx:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *a):
            return False

    return lambda: _Ctx()


def _frozen(now: datetime):
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    return _Frozen


def _integrity_error(constraint: str) -> IntegrityError:
    return IntegrityError(
        "INSERT ...", {},
        Exception(f'duplicate key value violates unique constraint "{constraint}"'),
    )


def _evidence(entry_id: str, prior_ids, text="I keep asking about work"):
    """What find_recurrences returns, in its real shape (memory_service:460)."""
    matches = [Row(id=p, content=f"prior {p}", conversation_id=None, score=0.9)
               for p in prior_ids]
    evidence = {
        "recurring_entry": {
            "memory_entry_id": entry_id, "text": text, "conversation_id": "c1",
        },
        "prior_matches": [
            {"memory_entry_id": p, "text": f"prior {p}",
             "conversation_id": None, "score": 0.9}
            for p in prior_ids
        ],
        "shown_to_classifier": len(prior_ids[:5]),
        "detector": {"threshold": 0.75, "limit": 20, "window": None},
    }
    return matches, evidence


# ── 1. The schedule ──────────────────────────────────────────────────────────

def _cron_job(name: str):
    return next(c for c in WorkerSettings.cron_jobs if c.coroutine.__name__ == name)


def test_the_snapshot_runs_one_hour_before_the_letter():
    """The gap is the design, not a coincidence: the snapshot fans out one job
    per eligible user and that fan-out has to drain before step D would read it.
    Asserted as a RELATIONSHIP so shifting either schedule alone fails here."""
    snapshot = _cron_job("snapshot_weekly_trajectories")
    letter = _cron_job("dispatch_weekly_letters")

    assert (snapshot.weekday, snapshot.hour, snapshot.minute) == ("sun", 17, 0)
    assert snapshot.weekday == letter.weekday
    assert snapshot.hour == letter.hour - 1


def test_the_snapshot_cron_carries_the_defaults_this_design_relies_on():
    """unique so N workers enqueue one dispatch; max_tries=1 so a half-finished
    fan-out does not silently re-run; run_at_startup False so a deploy does not
    snapshot."""
    job = _cron_job("snapshot_weekly_trajectories")
    assert job.unique is True
    assert job.max_tries == 1
    assert job.run_at_startup is False


def test_the_per_user_task_is_registered_and_keeps_the_default_timeout():
    """It must be registered or every enqueue is a job arq cannot run. And it
    stays on the 90s default deliberately — the whole reason this job dispatches
    instead of looping is that a cron_jobs entry cannot carry an override, so a
    long-running per-user task would mean the fan-out was sized wrong, not that
    the timeout should rise."""
    entry = next(
        f for f in WorkerSettings.functions
        if getattr(f, "__name__", getattr(getattr(f, "coroutine", None), "__name__", None))
        == "build_trajectory_snapshot_task"
    )
    assert getattr(entry, "timeout_s", None) is None


# ── 2. Time handling (TD-76 / #645) ──────────────────────────────────────────

def test_an_iso_string_becomes_a_timezone_aware_datetime():
    """The bounds cross Redis as strings; a timestamptz parameter must be bound
    from a datetime object, never from the string itself."""
    got = ts._as_utc("2026-09-14T00:00:00+00:00")
    assert got == PERIOD_START
    assert got.tzinfo is not None


def test_a_naive_value_is_read_as_utc_rather_than_as_server_local():
    """A naive datetime compared against timestamptz is interpreted in the
    server's timezone. Every writer here uses datetime.now(timezone.utc), so
    naive is a storage artefact and UTC is the right reading."""
    assert ts._as_utc(datetime(2026, 9, 14)) == PERIOD_START
    assert ts._as_utc("2026-09-14T00:00:00") == PERIOD_START


def test_a_non_utc_offset_is_converted_not_stripped():
    from datetime import timedelta
    aware = datetime(2026, 9, 14, 3, 0, tzinfo=timezone(timedelta(hours=3)))
    assert ts._as_utc(aware) == PERIOD_START


# ── 3. Eligibility — >=1 act, and NOT the letter's >=5 bar ───────────────────

async def _eligible(monkeypatch, message_user_ids, ritual_counts):
    import workers.arq_worker as aw

    async def _rituals(db, ps, pe, user_id=None):
        return dict(ritual_counts)

    monkeypatch.setattr(aw, "ritual_counts_by_user", _rituals)
    db = FakeDB({"Conversation": [Row(user_id=u) for u in message_user_ids]})
    return await ts.eligible_user_ids(db, PERIOD_START, PERIOD_END)


async def test_one_single_message_is_enough(monkeypatch):
    """THE DIFFERENCE FROM THE LETTER, and the reason this is its own gate. The
    letter's >=5 bar decides who is worth writing TO; that is a different
    question from whose week is worth recording. Applying it here would leave
    the lightest users with no trajectory at all."""
    assert await _eligible(monkeypatch, ["u1"], {}) == {"u1"}


async def test_a_ritual_with_no_chat_counts_as_an_act(monkeypatch):
    """A18: a week spent in council, counterview rebuttals, mirror notes and
    you-vs-you is a week that happened. Counting messages alone enqueued ZERO
    letters on 2026-08-16 for exactly such a user."""
    assert await _eligible(monkeypatch, [], {"u2": 3}) == {"u2"}


async def test_the_two_sources_are_unioned_not_intersected(monkeypatch):
    assert await _eligible(monkeypatch, ["u1"], {"u2": 1}) == {"u1", "u2"}
    assert await _eligible(monkeypatch, ["u1"], {"u1": 4}) == {"u1"}


async def test_a_user_with_no_acts_is_simply_absent(monkeypatch):
    assert await _eligible(monkeypatch, [], {}) == set()


# ── 4. Dispatch ──────────────────────────────────────────────────────────────

async def _dispatch(monkeypatch, eligible, *, run=None, now=None, raises=None):
    """Drive snapshot_weekly_trajectories with the job_run layer faked out."""
    import db.session as dbsession

    run = FakeRun() if run is None else run
    run_db = FakeDB()
    closed = {}

    async def _open(db, job_name, run_key, *, reclaim=False):
        closed["opened"] = (job_name, run_key, reclaim)
        return run

    async def _close(db, r, *, status, candidate=None, selected=None,
                     enqueued=None, error=None):
        closed["closed"] = {
            "status": status, "candidate": candidate, "selected": selected,
            "enqueued": enqueued, "error": error,
        }

    async def _eligible_ids(db, ps, pe):
        if raises is not None:
            raise raises
        closed["window"] = (ps, pe)
        return set(eligible)

    monkeypatch.setattr(ts, "_open_job_run", _open)
    monkeypatch.setattr(ts, "_close_job_run", _close)
    monkeypatch.setattr(ts, "eligible_user_ids", _eligible_ids)
    monkeypatch.setattr(
        ts, "datetime",
        _frozen(now or datetime(2026, 9, 20, 17, 0, tzinfo=timezone.utc)),
    )
    monkeypatch.setattr(dbsession, "AsyncSessionLocal", _session_factory(run_db))

    redis = FakeRedis()
    await ts.snapshot_weekly_trajectories({"redis": redis})
    return redis, run, closed


async def test_the_run_key_is_the_iso_week_and_the_window_starts_on_its_monday(monkeypatch):
    """R7: the key names the PERIOD, never the execution moment. Sunday falls on
    the LAST day of its own ISO week, so a Sunday run keyed W38 covers the week
    that is ending, and period_start is that week's Monday."""
    redis, run, closed = await _dispatch(monkeypatch, ["u1"])

    assert closed["opened"] == (ts.JOB_WEEKLY_TRAJECTORY, WEEK, False)
    assert closed["window"][0] == PERIOD_START


async def test_the_live_window_ends_now_not_at_sunday_midnight(monkeypatch):
    """Material written after the snapshot belongs to next week's, not to one
    already written. The hour between 17:00 and the letter is the visible cost
    of that rule and is documented rather than hidden."""
    redis, run, closed = await _dispatch(monkeypatch, ["u1"])
    assert closed["window"][1] == PERIOD_END


async def test_every_eligible_user_gets_one_job_with_iso_bounds(monkeypatch):
    redis, run, closed = await _dispatch(monkeypatch, ["u1", "u2", "u3"])

    assert [j[0] for j in redis.jobs] == ["build_trajectory_snapshot_task"] * 3
    assert {j[1][0] for j in redis.jobs} == {"u1", "u2", "u3"}
    for _, args in redis.jobs:
        assert args[1] == PERIOD_START.isoformat()
        assert args[2] == PERIOD_END.isoformat()


async def test_nobody_eligible_records_zero_rather_than_null(monkeypatch):
    """059's rule one level up: the query ran and nobody was active. That is a
    different fact from a run that died before looking, and NULL is reserved for
    the second."""
    redis, run, closed = await _dispatch(monkeypatch, [])

    assert redis.jobs == []
    assert run.candidate_count == 0
    assert closed["closed"] == {
        "status": "succeeded", "candidate": None, "selected": 0,
        "enqueued": 0, "error": None,
    }


async def test_the_candidate_count_is_written_before_the_fan_out(monkeypatch):
    """So a crash mid-enqueue still leaves the population on record (R3)."""
    redis, run, closed = await _dispatch(monkeypatch, ["u1", "u2"])
    assert run.candidate_count == 2
    assert closed["closed"]["selected"] == 2
    assert closed["closed"]["enqueued"] == 2


async def test_a_collision_on_the_job_run_index_enqueues_nothing(monkeypatch):
    """IDEMPOTENCY LAYER 1. _open_job_run returns None when uq_job_run_name_key
    rejects the insert, which means "this period already ran" — so a second
    dispatch for the same week must not fan out again."""
    import db.session as dbsession

    async def _open(db, job_name, run_key, *, reclaim=False):
        return None

    async def _never(db, ps, pe):
        raise AssertionError("eligibility must not be queried after a collision")

    monkeypatch.setattr(ts, "_open_job_run", _open)
    monkeypatch.setattr(ts, "eligible_user_ids", _never)
    monkeypatch.setattr(dbsession, "AsyncSessionLocal", _session_factory(FakeDB()))

    redis = FakeRedis()
    await ts.snapshot_weekly_trajectories({"redis": redis})
    assert redis.jobs == []


async def test_an_explicit_run_key_reclaims_and_uses_the_whole_week(monkeypatch):
    """The hand-repair path. A key passed in is a catch-up for a past week, so
    the window is that whole week rather than one ending now, and the job_run row
    may be taken over."""
    import db.session as dbsession

    seen = {}

    async def _open(db, job_name, run_key, *, reclaim=False):
        seen["reclaim"] = reclaim
        return FakeRun()

    async def _close(db, r, **kw):
        pass

    async def _eligible_ids(db, ps, pe):
        seen["window"] = (ps, pe)
        return {"u1"}

    monkeypatch.setattr(ts, "_open_job_run", _open)
    monkeypatch.setattr(ts, "_close_job_run", _close)
    monkeypatch.setattr(ts, "eligible_user_ids", _eligible_ids)
    monkeypatch.setattr(dbsession, "AsyncSessionLocal", _session_factory(FakeDB()))

    await ts.snapshot_weekly_trajectories({"redis": FakeRedis()}, run_key="2026-W36")

    assert seen["reclaim"] is True
    assert seen["window"][0] == datetime(2026, 8, 31, tzinfo=timezone.utc)
    assert seen["window"][1] == datetime(2026, 9, 6, 23, 59, 59, tzinfo=timezone.utc)


async def test_a_dispatch_that_raises_closes_its_run_as_failed(monkeypatch):
    """The durable failure record is the job_run row. Without it, "the worker was
    down" and "nobody was active" look identical from the outside."""
    redis, run, closed = await _dispatch(
        monkeypatch, ["u1"], raises=RuntimeError("pool exhausted"),
    )
    assert redis.jobs == []
    assert closed["closed"]["status"] == "failed"
    assert "pool exhausted" in closed["closed"]["error"]


# ── 5. The corpus bound — the half that is a silent wrong answer ─────────────

async def test_the_period_bounds_the_queries_and_the_corpus_stops_at_its_start(monkeypatch):
    """find_recurrences names corpus_* apart from the query selection because
    conflating them compares a week against itself. The entries are chosen BY
    period; the corpus is cut AT period_start, exclusive, with no lower bound."""
    import services.memory_service as ms

    calls = []

    async def _find(db, user_id, entry, **kw):
        calls.append(kw)
        return _evidence(entry.id, ["p1"])

    monkeypatch.setattr(ms, "find_recurrences", _find)
    db = FakeDB({"MemoryEntry": [Row(id="e1", content="x", conversation_id="c1")]})

    await ts.recurring_questions(db, "u1", PERIOD_START, PERIOD_END)

    assert calls == [{"corpus_until": PERIOD_START}]
    assert "corpus_since" not in calls[0]


async def test_the_loop_does_not_stop_at_the_first_hit(monkeypatch):
    """detect_recurrence breaks early because it writes ONE card. A snapshot
    wants every hit — that difference is the whole reason the seam exists."""
    import services.memory_service as ms

    async def _find(db, user_id, entry, **kw):
        return _evidence(entry.id, ["p1"])

    monkeypatch.setattr(ms, "find_recurrences", _find)
    db = FakeDB({"MemoryEntry": [Row(id=f"e{i}", content="x", conversation_id="c1")
                                 for i in range(3)]})

    questions = await ts.recurring_questions(db, "u1", PERIOD_START, PERIOD_END)
    assert [q["memory_entry_id"] for q in questions] == ["e0", "e1", "e2"]


async def test_an_entry_below_the_bar_is_skipped_not_recorded_empty(monkeypatch):
    import services.memory_service as ms

    async def _find(db, user_id, entry, **kw):
        return None if entry.id == "e1" else _evidence(entry.id, ["p1"])

    monkeypatch.setattr(ms, "find_recurrences", _find)
    db = FakeDB({"MemoryEntry": [Row(id="e1", content="x", conversation_id=None),
                                 Row(id="e2", content="y", conversation_id=None)]})

    questions = await ts.recurring_questions(db, "u1", PERIOD_START, PERIOD_END)
    assert [q["memory_entry_id"] for q in questions] == ["e2"]


async def test_the_true_match_count_survives_the_denormalisation_cap(monkeypatch):
    """The cap loses ordering detail, never the fact of the match — so a reader
    can tell "three matches, showing three" from "twelve matches, showing five"."""
    import services.memory_service as ms

    async def _find(db, user_id, entry, **kw):
        return _evidence(entry.id, [f"p{i}" for i in range(12)])

    monkeypatch.setattr(ms, "find_recurrences", _find)
    db = FakeDB({"MemoryEntry": [Row(id="e1", content="x", conversation_id=None)]})

    q = (await ts.recurring_questions(db, "u1", PERIOD_START, PERIOD_END))[0]
    assert q["match_count"] == 12
    assert len(q["prior_matches"]) == ts.MAX_MATCHES_PER_QUESTION == 5
    assert q["top_score"] == 0.9


# ── 6. changes_since_prior — the first run is null PLUS a reason ─────────────

def _snapshot(period_start, questions, status="generated"):
    return Row(
        period_start=period_start, status=status,
        payload={"recurring_questions": questions},
    )


def _q(entry_id, prior_ids):
    return {
        "memory_entry_id": entry_id, "text": "t", "conversation_id": None,
        "match_count": len(prior_ids), "top_score": 0.9,
        "prior_matches": [{"memory_entry_id": p, "text": "p",
                           "conversation_id": None, "score": 0.9}
                          for p in prior_ids],
    }


def test_the_first_run_is_null_with_a_machine_readable_reason():
    """NOT a zeroed diff. "Nothing changed since last week" and "there was no
    last week" are different facts, and an all-empty change record would state
    the first while meaning the second — the failure 059 avoids with NULL-vs-0."""
    changes, reason = ts.changes_since_prior([_q("e1", ["p1"])], None)
    assert changes is None
    assert reason == ts.NO_PRIOR_SNAPSHOT == "no_prior_snapshot"


def test_exactly_one_of_changes_and_reason_is_ever_set():
    """So a reader can branch on either without checking both."""
    for questions, prior in (
        ([], None),
        ([_q("e1", ["p1"])], None),
        ([], _snapshot(PERIOD_START, [])),
        ([_q("e1", ["p1"])], _snapshot(PERIOD_START, [_q("e0", ["p1"])])),
    ):
        changes, reason = ts.changes_since_prior(questions, prior)
        assert (changes is None) != (reason is None)


def test_a_prior_row_carrying_no_payload_says_so_rather_than_diffing_nothing():
    changes, reason = ts.changes_since_prior([_q("e1", ["p1"])], Row(
        period_start=PERIOD_START, status="generated", payload=None,
    ))
    assert changes is None
    assert reason == ts.PRIOR_SNAPSHOT_HAS_NO_PAYLOAD


def test_the_diff_is_over_the_echoed_material_not_the_query_entries():
    """THE CHOICE THAT MAKES THE DIFF MEAN ANYTHING. A query entry was by
    definition written during its own period, so week over week it is always a
    different row: diffing query entries would report total turnover every week
    and measure nothing. What persists is the earlier material returned to.

    Here both weeks echo p1 through DIFFERENT in-period entries. That is the
    same thread, and it must read as still_recurring rather than as one
    departure plus one arrival."""
    prior = _snapshot(datetime(2026, 9, 7, tzinfo=timezone.utc), [_q("old", ["p1"])])
    changes, reason = ts.changes_since_prior([_q("new", ["p1"])], prior)

    assert reason is None
    assert changes["still_recurring"] == ["p1"]
    assert changes["new_since_prior"] == []
    assert changes["absent_since_prior"] == []


def test_the_three_sets_partition_the_anchors():
    prior = _snapshot(datetime(2026, 9, 7, tzinfo=timezone.utc),
                      [_q("old", ["p1", "p2"])])
    changes, _ = ts.changes_since_prior([_q("new", ["p2", "p3"])], prior)

    assert changes["still_recurring"] == ["p2"]
    assert changes["new_since_prior"] == ["p3"]
    assert changes["absent_since_prior"] == ["p1"]
    assert changes["counts"] == {
        "still_recurring": 1, "new_since_prior": 1, "absent_since_prior": 1,
    }


def test_the_diff_names_the_week_it_compared_against():
    """Rather than leaving a reader to assume it was the immediately preceding
    one — it is the last week we actually looked at, which after a failure is
    further back."""
    prior = _snapshot(datetime(2026, 9, 7, tzinfo=timezone.utc), [], status="empty")
    changes, _ = ts.changes_since_prior([], prior)

    assert changes["prior_period_start"] == "2026-09-07T00:00:00Z"
    assert changes["prior_status"] == "empty"


# ── 7. The per-user task: three statuses, and layer 2 of idempotency ─────────

async def _run_task(monkeypatch, *, existing=None, prior=None, questions=None,
                    raises=None, commit_raises=None):
    import db.session as dbsession

    tables = {}
    if existing is not None:
        tables["TrajectorySnapshot"] = [existing]
    db = FakeDB(tables, commit_raises=commit_raises)

    async def _questions(_db, user_id, ps, pe):
        if raises is not None:
            raise raises
        return list(questions or [])

    async def _prior(_db, user_id, ps):
        return prior

    monkeypatch.setattr(ts, "recurring_questions", _questions)
    monkeypatch.setattr(ts, "_prior_snapshot", _prior)
    monkeypatch.setattr(dbsession, "AsyncSessionLocal", _session_factory(db))

    await ts.build_trajectory_snapshot_task(
        {}, "u1", PERIOD_START.isoformat(), PERIOD_END.isoformat(),
    )
    return db


async def test_a_recurrence_writes_a_generated_row(monkeypatch):
    db = await _run_task(monkeypatch, questions=[_q("e1", ["p1"])])

    assert len(db.added) == 1
    row = db.added[0]
    assert row.status == "generated"
    assert row.kind == "weekly"
    assert row.user_id == "u1"
    assert row.period_start == PERIOD_START and row.period_start.tzinfo is not None
    assert row.period_end == PERIOD_END
    assert [q["memory_entry_id"] for q in row.payload["recurring_questions"]] == ["e1"]


async def test_an_active_week_with_no_recurrence_writes_an_empty_row(monkeypatch):
    """'empty' means WE LOOKED. The absence of a row means there was nothing to
    look at. Collapsing the two would tell step D that a silent week and an
    un-run week are the same thing."""
    db = await _run_task(monkeypatch, questions=[])

    assert len(db.added) == 1
    assert db.added[0].status == "empty"
    assert db.added[0].payload["recurring_questions"] == []


async def test_a_failure_is_recorded_rather_than_swallowed(monkeypatch):
    db = await _run_task(monkeypatch, raises=RuntimeError("vector op blew up"))

    assert len(db.added) == 1
    assert db.added[0].status == "failed"
    assert "vector op blew up" in db.added[0].payload["error"]


async def test_a_failed_payload_carries_no_half_built_result(monkeypatch):
    """A partial result under status='failed' would be read as data by anything
    that checked the field before the status."""
    db = await _run_task(monkeypatch, raises=RuntimeError("boom"))
    assert set(db.added[0].payload) == {"version", "error"}


async def test_the_detector_bar_is_recorded_even_on_an_empty_snapshot(monkeypatch):
    """"Found nothing" is only meaningful against the bar it cleared, and those
    are ship-and-tune values — a record whose bar is unrecoverable cannot be
    read (060's reasoning, applied a level up)."""
    from services.memory_service import RECURRENCE_LIMIT, RECURRENCE_SIM_THRESHOLD

    db = await _run_task(monkeypatch, questions=[])
    detector = db.added[0].payload["detector"]

    assert detector["threshold"] == RECURRENCE_SIM_THRESHOLD
    assert detector["limit"] == RECURRENCE_LIMIT
    assert detector["window"] == {"since": None, "until": "2026-09-14T00:00:00Z"}


async def test_the_payload_carries_only_the_two_v1_fields(monkeypatch):
    """evolving_beliefs is deferred behind the version-chain question and
    unresolved_threads is out because no signal exists. A field appearing here
    without a decision is the thing this asserts against."""
    db = await _run_task(monkeypatch, questions=[])
    assert set(db.added[0].payload) == {
        "version", "recurring_questions", "changes_since_prior",
        "changes_since_prior_reason", "detector",
    }
    assert db.added[0].payload["version"] == ts.PAYLOAD_VERSION == 1


async def test_a_first_snapshot_stores_the_null_and_the_reason(monkeypatch):
    db = await _run_task(monkeypatch, questions=[_q("e1", ["p1"])], prior=None)

    assert db.added[0].payload["changes_since_prior"] is None
    assert db.added[0].payload["changes_since_prior_reason"] == "no_prior_snapshot"


async def test_a_second_snapshot_stores_the_diff_and_no_reason(monkeypatch):
    prior = _snapshot(datetime(2026, 9, 7, tzinfo=timezone.utc), [_q("old", ["p1"])])
    db = await _run_task(monkeypatch, questions=[_q("e1", ["p1", "p2"])], prior=prior)

    payload = db.added[0].payload
    assert payload["changes_since_prior_reason"] is None
    assert payload["changes_since_prior"]["still_recurring"] == ["p1"]
    assert payload["changes_since_prior"]["new_since_prior"] == ["p2"]


async def test_an_existing_row_is_not_rewritten(monkeypatch):
    """IDEMPOTENCY LAYER 2, the letter task's dedup select. An arq retry of one
    job finds the row already written and returns — no second row, no commit."""
    existing = Row(status="generated", payload={"recurring_questions": []},
                   period_start=PERIOD_START, period_end=PERIOD_END)
    db = await _run_task(monkeypatch, existing=existing, questions=[_q("e1", ["p1"])])

    assert db.added == []
    assert db.commits == 0
    assert existing.payload == {"recurring_questions": []}


async def test_an_empty_row_also_blocks_a_rewrite(monkeypatch):
    """'empty' is a RESULT, not a gap. Re-running over it would spend the work
    again to reach the same answer."""
    existing = Row(status="empty", payload={"recurring_questions": []},
                   period_start=PERIOD_START, period_end=PERIOD_END)
    db = await _run_task(monkeypatch, existing=existing, questions=[])

    assert db.added == []
    assert db.commits == 0


async def test_a_failed_row_is_overwritten_in_place(monkeypatch):
    """It holds no result, and re-running is the entire point of having noticed
    it failed. In place, not alongside — a second row would violate
    uq_trajectory_snapshots_user_period_kind."""
    existing = Row(status="failed", payload={"error": "boom"},
                   period_start=PERIOD_START, period_end=PERIOD_END)
    db = await _run_task(monkeypatch, existing=existing, questions=[_q("e1", ["p1"])])

    assert db.added == []
    assert db.commits == 1
    assert existing.status == "generated"
    assert [q["memory_entry_id"] for q in existing.payload["recurring_questions"]] == ["e1"]


async def test_losing_the_race_to_a_concurrent_job_is_not_an_error(monkeypatch):
    """The dedup select can lose to a concurrent job for the same user and
    period; the unique index then rejects the insert. The row exists, which is
    the outcome wanted — so this rolls back and returns rather than raising into
    an arq retry that would only lose the same race again."""
    db = await _run_task(
        monkeypatch, questions=[_q("e1", ["p1"])],
        commit_raises=_integrity_error("uq_trajectory_snapshots_user_period_kind"),
    )
    assert db.rollbacks == 1
    assert db.commits == 0


async def test_the_bounds_are_bound_as_datetimes_not_strings(monkeypatch):
    """TD-76 / #645. They arrive as ISO strings over Redis and must never reach
    a timestamptz parameter in that form."""
    db = await _run_task(monkeypatch, questions=[])
    row = db.added[0]

    assert isinstance(row.period_start, datetime)
    assert isinstance(row.period_end, datetime)
    assert row.period_start.tzinfo is not None
    assert row.period_end.tzinfo is not None


# ── 8. The model agrees with the migration ───────────────────────────────────

def test_the_model_status_vocabulary_is_the_three_the_migration_allows():
    """Stated a third time, independently of the model and of the live
    constraint — an assertion that computed its expectation from the thing under
    test could not fail. The live comparison is in tests/db_live."""
    import re

    from models import TrajectorySnapshot

    check = next(
        c for c in TrajectorySnapshot.__table__.constraints
        if getattr(c, "name", None) == "ck_trajectory_snapshots_status"
    )
    assert set(re.findall(r"'([^']*)'", str(check.sqltext))) == {
        "generated", "empty", "failed",
    }


def test_the_unique_key_is_user_period_kind():
    """The idempotency key layer 2 relies on. Without `kind` a later monthly
    cadence sharing a period_start would collide with the weekly row."""
    from models import TrajectorySnapshot

    index = next(
        i for i in TrajectorySnapshot.__table__.indexes
        if i.name == "uq_trajectory_snapshots_user_period_kind"
    )
    assert index.unique is True
    assert [c.name for c in index.columns] == ["user_id", "period_start", "kind"]


def test_the_user_fk_cascades():
    """The payload keeps denormalised snippets of the person's own words with no
    foreign keys, so the CASCADE on user_id is the ONLY thing that removes them
    on erasure."""
    from models import TrajectorySnapshot

    fk = next(iter(TrajectorySnapshot.__table__.c.user_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


@pytest.mark.parametrize("column", ["user_id", "period_start", "period_end",
                                    "kind", "status", "created_at"])
def test_the_not_null_columns_are_not_null(column):
    """C-06's sibling for schema work: every NOT NULL column checked against the
    model, so a db_live insert cannot fail on a column nobody listed."""
    from models import TrajectorySnapshot

    assert TrajectorySnapshot.__table__.c[column].nullable is False
