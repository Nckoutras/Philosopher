# Letter delivery rebuild (#6) — founder rulings

**Locked:** 2026-09-07. **Base SHA:** `d2eecf8ef4a50dc244a90c545585e94c061ec259`

---

## RULINGS (locked 2026-09-07, founder-approved verbatim)

R1. D-1 ships first, alone. Migration 058_letter_failed_status widens
    ck_weekly_letters_status to include 'failed' AND updates the CheckConstraint
    in models/__init__.py:369 to match. db_live test: insert status='failed'
    succeeds. Revert-verify required. job_run becomes migration 059.

R2. Unsent emails: (iii)+(i). Add weekly_letters.email_suppressed_reason
    (nullable text) in the job_run migration; guard writes one of
    localhost | no_email | opt_out | already_sent | send_failed. Values pinned
    in a test. (ii) ruled OUT — no backdated batch resend, ever.

R3. candidate_count in job_run: yes.

R4. cron→ARQ scope: weekly_letter + monthly_letter only. Their APScheduler
    entries are DELETED in PR-B; a test asserts scheduler job ids exclude both.
    The other three dispatch jobs follow later, in one PR, only after a Sunday
    run proves the pattern.

R5. Per-task timeout in PR-B: letter generation tasks timeout=300; dispatch
    jobs keep the default.

R6. job_run.detail JSONB: no. Counts only for v1.

R7. run_key derived from period_start, never from execution time.
    Weekly = ISO week (2026-W36), monthly = YYYY-MM. In PR-C dispatch computes
    the period once and passes it to every enqueued task.

R8. Manual trigger: no new admin surface. PR-C catch-up invoked with an
    explicit run_key is the manual trigger.

R9. Failed job_run → sentry capture_exception.

R10. This rulings block is committed verbatim as
    docs/reports/LETTER_DURABILITY_RULINGS_2026-09-07.md in this PR.

R2a (refinement, locked 2026-09-07, added in PR-A). PR-A is DDL + model only.
    R2 put the email_suppressed_reason COLUMN and the guard that WRITES it in
    one PR; they are split. 059 adds the nullable column and nothing reads or
    writes it. The guard, and the test pinning its five values
    (localhost | no_email | opt_out | already_sent | send_failed), move to PR-B
    — the guard lives in arq_worker.py, which PR-B already opens, and shipping
    it in PR-A would put a behaviour change in a schema PR (P-02).
    The column carries NO CHECK constraint, in PR-A or after: the five reasons
    are an application vocabulary, so a sixth must stay a code change and never
    become a production migration. R2's substance is unchanged — (iii)+(i)
    stands, (ii) stays ruled out, no backdated batch resend, ever.

R9a (2026-09-08). R9's "capture_exception" is satisfied by the existing
    LoggingIntegration path (logger.error with exc_info=True); an explicit
    capture_exception would double-report. The durable failure record is
    job_run.status='failed' + error, not the Sentry event.

R8a (2026-09-08, added in PR-C). Automatic catch-up looks back exactly ONE
    period — last week on Monday 09:00 UTC, last month on the 2nd at 09:00 UTC.
    Older gaps are repaired by hand with an explicit run_key (R8, and the Ops
    section below). This is a product decision, not a technical limit: three
    backdated letters arriving together on a Monday morning reads as a broken
    product rather than as a repair, and the letters carry their own dates, so
    a reader can see they are stale. The floor is min(job_run.started_at) per
    job_name — no job_run row predates PR-B, so nothing before it can be
    "missed", and a catch-up can never reach back across the PR-C period
    realignment.

    RECLAIM. A missed period is one whose job_run never reached 'succeeded' —
    which includes 'failed' rows and 'running' rows that never closed. Because
    uq_job_run_name_key would otherwise make the re-dispatch answer "already
    ran", catch-up (and ONLY catch-up) may take over the existing row:
    succeeded → skip; failed → reclaim; running older than 2h → reclaim
    (crashed); running newer than 2h → skip (in flight). Reclaiming resets the
    counts to NULL, per 059's NULL-vs-0 rule. The live cron never reclaims.

---

## Decomposition

D-1 (this PR) → PR-A (059_job_run + email_suppressed_reason, RLS per 052
posture) → PR-B (letters → ARQ cron_jobs, job_run rows, timeouts, APScheduler
entries removed) → PR-C (explicit period + catch-up).

---

## Verification

Revert-verify leg (a) (migration reverted → CheckViolation) was not
executed locally: no pgvector Postgres available. CI db-tests is the
authority for the migrated-schema insert. Leg (b) (model reverted →
constraintdef mismatch) was executed and failed as expected.

---

## Observed, not fixed

Recorded during the #6 Step-1 investigation. Each is real, none is in D-1's
scope, and none is to be edited by the PRs above without its own ruling.

**`tests/routers/test_weekly_letters.py:52` sets a letter's status to
`"delivered"`** — not one of the permitted values, in any version of the
constraint. It is harmless where it sits, because the letter is a `MagicMock`
and nothing validates a mock's attribute. It is noted because it is the same
shape as the defect 058 fixes: a status value that no layer checked. **Do not
edit that file.**

**`tests/routers/test_weekly_letters.py:204` pins `"status != 'failed'"` in the
list endpoint's compiled SQL only.** The assertion inspects generated SQL and
never executes it, so it has passed since it shipped while filtering on a value
the schema made impossible. It becomes meaningful the moment 058 lands. **Leave
it.**

**`generate_weekly_mirror_task` carries the same D-2 pattern** as the letter
tasks — the period is computed from `datetime.now()` at execution time rather
than passed in (`arq_worker.py:1096-1097`), so any future catch-up for mirrors
would duplicate rows the same way. Out of scope for #6 entirely; **to be logged
as tech debt in the next docs rotation.**

---

## D-2, for PR-C's brief

Not a "not fixed" item — it is PR-C's first task, recorded here so the reason is
not re-derived. `generate_weekly_letter_task(ctx, user_id, voice_persona_slug)`
takes no period; it computes `period_start` from `datetime.now()` at execution
(`arq_worker.py:1407-1408`). Dedup is `(user_id, period_start, kind)` via
`uq_weekly_letters_user_period`, so a catch-up run on a different day computes a
different `period_start`, misses the unique index, and writes a **second letter
for an overlapping week**. Catch-up is not implementable until the period is an
explicit argument — which is what R7 settles.

---

## Ops — manual catch-up

R8: there is NO admin endpoint for this, deliberately. The manual trigger is the
same dispatch function the cron calls, invoked with an explicit `run_key`. Run it
in the **worker** service's Render shell (the worker runs
`arq workers.arq_worker.WorkerSettings`; see README and
`infra/docker-compose.prod.yml`), from the app directory:

```bash
python -c "
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from config import config
from workers.letter_dispatch import dispatch_weekly_letters
async def main():
    pool = await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
    await dispatch_weekly_letters({'redis': pool}, run_key='2026-W37')
asyncio.run(main())
"
```

For a month, swap the import and the key:

```bash
python -c "
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from config import config
from workers.letter_dispatch import dispatch_monthly_letters
async def main():
    pool = await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
    await dispatch_monthly_letters({'redis': pool}, run_key='2026-09')
asyncio.run(main())
"
```

Notes, all of them load-bearing:

- **`run_key` format is exact**: `%G-W%V` for weeks (`2026-W36`, zero-padded —
  `2026-W6` is not a key) and `%Y-%m` for months (`2026-09`). The period is
  derived FROM the key, so a malformed key is a malformed period.
- **Passing a `run_key` enables reclaim.** A `failed` or crashed-`running` row for
  that key is taken over; a `succeeded` row is left alone and the command is a
  no-op. Running it twice is safe.
- **It does not bypass the per-user dedup.** Users who already have a letter for
  that period are skipped inside the generator, before any LLM call or email, so
  nobody is emailed twice (R2 (i)).
- **It bypasses the floor and the one-period lookback** — that is the whole point
  of the manual path. An arbitrarily old `run_key` will be dispatched, including
  one from before the PR-C period realignment, which would write a second letter
  for a week already delivered under the old arithmetic. **Do not use a weekly
  `run_key` earlier than `2026-W37`** (the first aligned week; the last pre-PR-C
  run was Sunday 2026-09-06 and the first aligned run is Sunday 2026-09-13).
- **Run it on the worker, not the API.** Both would work, but the worker is where
  this code and its Redis settings live, and the API service has no reason to
  hold a dispatch.
- **The first period has no automatic catch-up.** The floor is
  min(job_run.started_at) per job, so if the very first scheduled run
  (weekly: Sunday 2026-09-13; monthly: 2026-09-30) never opens a row at
  all, Monday's catch-up sees no history and skips. From the second period
  on, catch-up covers a fully missed run. Remedy for the first: the manual
  command above with run_key='2026-W37' (or '2026-09').
