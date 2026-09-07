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
