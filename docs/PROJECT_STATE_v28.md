# GREAT MINDS — Project State v28

> **Range covered:** `#593` … `#615` (23 squash-merges on `main` since `7a0ab2e0`).
> **Verification SHA:** `e840053ceaadfba3b12c21164f98e949152c4ff4`.
> Backend measurements were taken at `076f74b7` and re-confirmed at `e840053c`;
> #615 is web-only and leaves `apps/api` byte-identical. Web measurements are at
> `e840053c`.
> **Date:** 2026-09-08.
>
> **This rotation's own PR number is deliberately not asserted**, and no unmerged
> work is described as if it existed. The range above is what is on `main`.
>
> **Companion documents:** `IMPLEMENTATION_BACKLOG_v28.md`, `HANDOFF_BRIEF_v28.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md`. v27 files are preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below is either VERIFIED THIS ROTATION with its method stated inline,
or explicitly marked FOUNDER-REPORTED / UNVERIFIED.** "Unchanged." is not evidence
and is not used as such. Every carried backlog item was re-verified against the code
before being written, not copied forward.

**Methods used this rotation:** `pytest`, `vitest` and `tsc` executed at `076f74b7`;
`alembic heads` and the C-04 naming script executed; the FastAPI app's `openapi()`
generated **in-process**; `WorkerSettings` imported and its `functions` and
`cron_jobs` counted; the persona registry and the safety lexicons imported and
counted; the question bank parsed; `git log`, `git log -L` and `git cat-file` over
the range and across branch boundaries; live source reads.

**No database, no Stripe dashboard, no Sentry project, no Render or Netlify
dashboard, no email inbox and no production logs were consulted.** Every claim that
would require any of those is marked FOUNDER-REPORTED below — meaning the founder
observed it and this document records that, not that this rotation checked it.

**Two carried claims were found false this rotation** and are corrected in §5: a PR
the previous state described as merged is not on `main`, and a count in three
docstrings was read against the wrong quantity by this rotation and is in fact
correct.

**Two corrections in this document were themselves wrong and were caught in review**
before the PR opened — both in §5c, both left visible with what went wrong rather
than silently repaired.

---

## 1. What this cycle did

Three threads closed, and all three were the ones v27 named as open.

### 1a. P0 — 13 of 13, with one observation still ahead

v27 recorded **12 of 13**, the one remaining item being **#6, letter delivery**. The
work is now merged in four PRs, verified present on `main` by commit title and by
source read:

**D-1 (#608)** — migration `058_letter_failed_status` widens
`ck_weekly_letters_status` to include `'failed'`, and the `CheckConstraint` in
`models/__init__.py` is widened to match. This is the failure row the generators had
always tried to write and the schema had always refused. Verified: the model's
constraint now reads `status IN ('generated', 'empty', 'suppressed', 'failed')`.

**PR-A (#609)** — migration `059_job_run` creates the `job_run` table
(`job_name`, `run_key`, `started_at`, `finished_at`, `status`, `candidate_count`,
`selected_count`, `enqueued_count`, `error`) with `uq_job_run_name_key` and
`ix_job_run_started_at`, and adds `weekly_letters.email_suppressed_reason`. Verified:
`059` **enables RLS on `job_run` in the same migration**, per C-05, and the
`email_suppressed_reason` column deliberately carries **no CHECK constraint** so a
sixth suppression reason stays a code change rather than becoming a production
migration (R2a).

**PR-B (#610)** — weekly and monthly dispatch move from APScheduler to ARQ
`cron_jobs`, each run opening and closing a `job_run` row; letter generation gets
`timeout=300`; the two APScheduler entries are deleted. Verified: `WorkerSettings`
sets `timezone = dt_timezone.utc` **explicitly**, so "Sunday 18:00 UTC" is a property
of this file rather than of the Render container's system timezone.

**PR-C (#611)** — the period becomes an explicit argument instead of being computed
from `datetime.now()` at execution (D-2), and automatic catch-up lands with
`job_run` reclaim. Verified: four ARQ cron entries —
`dispatch_weekly_letters` (Sun 18:00), `dispatch_monthly_letters` (day 28–31, 17:00),
`catch_up_weekly_letters` (Mon 09:00), `catch_up_monthly_letters` (day 2, 09:00).

**The rulings are committed verbatim** at
`docs/reports/LETTER_DURABILITY_RULINGS_2026-09-07.md` — R1–R10 locked 2026-09-07,
plus R2a, R8a and R9a added during execution. Read in full this rotation. What they
settle, in one line each:

- **R2** — unsent emails get a recorded reason (one of `localhost`, `no_email`,
  `opt_out`, `already_sent`, `send_failed`) and there is **no backdated batch
  resend, ever**.
- **R4** — only weekly and monthly moved to ARQ. The other three dispatch jobs
  follow later, in one PR, **only after a Sunday run proves the pattern**.
- **R6** — `job_run.detail` JSONB was ruled out; counts only for v1.
- **R7** — `run_key` derives from `period_start`, never from execution time.
  Weekly `%G-W%V` (`2026-W36`), monthly `%Y-%m` (`2026-09`).
- **R8 / R8a** — there is **no admin endpoint** for a manual run, deliberately. The
  manual trigger is the same dispatch function invoked with an explicit `run_key`.
  Automatic catch-up looks back **exactly one period**, because three backdated
  letters arriving together on a Monday reads as a broken product rather than a
  repair.
- **R9a** — Sentry coverage comes from the existing `LoggingIntegration` path
  (`logger.error(..., exc_info=True)`); an explicit `capture_exception` would
  **double-report**. The durable failure record is `job_run.status='failed'` plus
  `error`, not the Sentry event.
- **Reclaim** — a missed period is one whose `job_run` never reached `succeeded`.
  `succeeded` → skip; `failed` → reclaim; `running` older than 2h → reclaim
  (crashed); `running` newer than 2h → skip (in flight). **The live cron never
  reclaims** — only catch-up does.

**The observation is still ahead.** The gate is the **Sunday 2026-09-13 18:00 UTC**
run, which is the first period under the PR-C arithmetic. The Ops section of the
rulings doc carries the manual remedy and one hard constraint worth repeating here:
**do not use a weekly `run_key` earlier than `2026-W37`**, because an older key would
write a second letter for a week already delivered under the pre-PR-C period
arithmetic.

### 1b. P1 — Memory-v2, closed across #602–#606

No `v27.5` document exists, so this is written from
`docs/reports/MEMORY_V2_DESIGN_2026-09-03.md` (read in full) and from the PRs
themselves, not carried from a prior rotation.

The ten founder rulings are recorded verbatim in Greek in that design document, with
English glosses marked explicitly as glosses rather than as the ruling. Ruling 1 set
the order: **reliable recall first (a), then memory everywhere (d)**; visibility (b)
and evolution (c) are out of scope.

- **#602** — the design document itself.
- **#603** — counterview fails closed on orphaned insights: suppress when
  `conversation_id` is NULL (F-15, landed ahead of 057).
- **#604** — migration `057_memory_conv_fk_set_null` moves `memory_entries.conversation_id`
  and `insights.conversation_id` from `ON DELETE CASCADE` to `ON DELETE SET NULL`.
  Verified by reading the migration: both clauses present. Deleting a conversation
  now preserves what was learned and what the room noticed, nulling the reference
  rather than destroying the row.
- **#605** — hybrid recall (Ruling #5). Verified by source read: **Lane A**
  (`stated` / `self_portrait`) is always-in and **exempt from the relevance floor**;
  **Lane B** is floor-gated at `INFERRED_SCORE_FLOOR = 0.75` and per-type quota'd,
  and receives Lane A's unfilled slots one way only. The floor is documented in the
  source as a **ship-and-tune value** — it replaced an unmeasured `0.70` literal, and
  no measurement of either number against real embeddings exists.
- **#606** — the `<what_you_know>` standing-memory block in weekly and monthly
  letters (Ruling #1(d)). Verified: present in both letter paths, query-free, with
  prompt text instructing the model to treat the block as standing texture rather
  than as instructions or as lines to quote back.

Two supporting PRs made the above testable and honest: **#600** added a live-Postgres
fixture via a CI service container and the first DB-backed tests for recall and
cascades (Ruling #10, "TD-57 fix-first"), and **#599** removed dead surfaces — a
stale cron, an insight task, uncalled service methods and a `feeds` field
(Ruling #8). **#601**, **#598** and **#597** completed the cycle: quotes rebuilt from
the seed file rather than the seed script, council memory at the synthesis step only
(Ruling #4, keeping the four member calls cached), and the memory-dampening prompt
replaced with the founder-approved use directive (Ruling #6).

### 1c. Ruling #3 — the octagon is fully authored, 360/360

Ruling #3 said the octagon becomes answer-sensitive via per-pill weights on the 15
free questions first, with **"οι 345 αργότερα, σταδιακά"** — the other 345 later,
gradually. That is now finished.

| PR | Batch | Items |
|---|---|---|
| #607 | 1 | work_and_ambition 002–030 — 29 |
| #612 | tranche A | money, family, relationships, friendship — 115 |
| #613 | tranche B | fear, meaning, identity, conflict — 115 |
| #614 | tranche C | solitude, desire, mortality — 86 |

**Verified by parsing the bank: 360 of 360 questions carry `pill_weights`; zero
remain on the legacy per-tag fallback.** The scope pin in
`test_portrait_theme_scores.py` now asserts
`len(sp._BANK) - len(weighted) == 0`, which is kept rather than deleted because it is
the pin that a future question cannot ship unweighted.

Each batch was inserted at byte level rather than through a JSON round-trip, which
would have reformatted the whole file, and each was verified the same way: stripping
the inserted blocks reproduces the previous blob byte-for-byte, and every dict
matches the founder-locked source in **value and key order**, with keys checked as
set equality against the question's `theme_tags` rather than the subset the loader
would tolerate.

**#614 also repointed two tests**, and the reason is a lesson in its own right — see
§6. `test_an_unweighted_question_contributes_its_legacy_per_tag_count` and
`test_the_fallback_contributes_to_the_achievable_max_too_not_just_the_numerator`
each selected an unweighted specimen **out of the real bank** with `next(...)` and no
default. At 360/360 that generator is empty. Both now build the specimen from the
file's existing `_bank_file`/`BASE_Q` `tmp_path` helper and `monkeypatch.setitem` it
into `sp._BANK`; their assertions are unchanged.

---

## 2. Verified state — every row executed or read at `076f74b7`

| Claim | Method | Result |
|---|---|---|
| Backend suite | `pytest -q` executed | **1099 passed, 45 skipped, 0 failed** (v27: 912) |
| CI failure baseline | file read | **0 quarantined entries** — any red is new |
| Web unit suite | `vitest run` executed at `e840053c` | **13 failed / 248 passed** (261) — the same 13 as v26 and v27; #615 added 21 passing tests across 3 files |
| Web typecheck | `tsc --noEmit` executed | **11 errors** — unchanged |
| Alembic | `alembic heads` executed | single head, **`059_job_run`** |
| Migration naming | C-04 script over 59 files | **0 length violations**; longest id is 32 chars exactly (`024_saved_line_conclusion_source`). Two documented historical exceptions — §4. |
| API surface | `openapi()` in-process | **93 paths / 113 operations** |
| ARQ tasks | `len(WorkerSettings.functions)` | **12** |
| ARQ cron jobs | `len(WorkerSettings.cron_jobs)` | **4** — weekly + monthly dispatch, weekly + monthly catch-up |
| ARQ timezone | source read | `timezone = dt_timezone.utc` set explicitly, not inherited |
| APScheduler jobs | source read | **5** — `daily_rituals`, `stripe_reconcile`, `future_self_emails`, `weekly_mirror`, `preview_mirror` |
| Question bank | parsed | **360 / 360 weighted**, 0 unweighted |
| Personas | `PERSONA_REGISTRY` imported | **11**, of which **3** are `tier="free"` (`lao_tzu`, `marcus_aurelius`, `socrates`) |
| Persona forbidden lexicons | registry imported | **8 of 11** carry one; **3 do not** — `lao_tzu`, `niccolo_machiavelli`, `oscar_wilde` |
| Safety lexicons | imported and counted | **210** entries across the four bands (LOW 30, OUTPUT 33, HIGH 88, MEDIUM 59); **73** contain Greek script |
| `weekly_letters` schema | model read | `period_start`, `period_end`, `kind` — **there is no `week_start` column**; status CHECK includes `'failed'`; `uq_weekly_letters_user_period` on (user, period_start, kind) |
| `job_run` schema | model + migration read | `uq_job_run_name_key` unique on (job_name, run_key); RLS enabled in `059` per C-05 |
| Recall lanes | source read | `INFERRED_SCORE_FLOOR = 0.75`; Lane A floor-exempt, Lane B floor-gated and per-type capped |
| `<what_you_know>` | source read | present in both the weekly and the monthly letter path |
| SET NULL cascade | `057` read | both `memory_entries` and `insights` FKs are `ON DELETE SET NULL` |
| Live-DB tests | `pytest --collect-only` | **45 tests** across 4 files in `tests/db_live/`, run by the `db-tests` CI job |
| Stale-`running` threshold | source read | `STALE_RUNNING_AFTER = timedelta(hours=2)` |
| Free daily ceiling | imported and evaluated | `FREE_DAILY_LIMIT_PER_PERSONA = 5` × 3 reachable personas = **15/day**; `PRO_DAILY_FAIR_USE_LIMIT = 150`; a grep for `monthly_limit\|FREE_MONTHLY\|per_month` returns **nothing** |
| Upgrade page price | source read | still displays **"€99.99 / year"** |
| Greek crisis number | file read | `prompts/safety_response_el.jinja2` contains **no** `1018` — still deliberately country-neutral |
| Remote branches | `git ls-remote --heads` | **26** besides `main`, all stale (2026-05-09 … 2026-06-14). The 27th was deleted when #615 merged. |

### ⚠️ FOUNDER-REPORTED — not verified by this rotation

Recorded because the founder observed them. This document did not check any of them.

1. **`FROM_EMAIL` was set on both services on 2026-09-07.**
2. **OTP and future-self email are delivering from `hello@thewiseroom.app`**; the
   worker send path was proven on 2026-09-08.
3. **The worker and the API are deployed at the #611 SHA.**
4. **The Sunday 2026-09-06 run fired on time and found no eligible users** — which
   is the correct outcome for that date, not a defect.
5. **The locked-persona paywall change was smoke-tested on the Netlify preview on
   2026-09-02.** It was **unmerged at `076f74b7`** — verified by content, §5a — and
   **merged as #615 during this rotation**, which this document verified by content
   rather than by title.
6. **OPS-006**: €149 was charged against a locked price of €99.99. Test-mode is
   closed; live-mode is pending.
7. **Migrations `055`–`059` are applied on production** (`alembic_version` not read
   here).
8. **Sentry is initialised in the production environment.**
9. **`BETA_GRANT_PRO_TO_ALL`'s production value on Render.** It defaults to `False`
   in `config.py`; if it is enabled, the free cap does not apply to anyone.
10. **The "1.85× the heaviest usage day" figure** behind the fair-use cap. It was
    measured against the production database in #11's Step-1 investigation and has
    **not been re-read in v27 or here**.
11. **The domain cutover completed 2026-09-08 (evening).** `thewiseroom.app` is
    live on Netlify with a Let's Encrypt certificate; `FRONTEND_URL` is set on
    **both** Render services; `NEXT_PUBLIC_BASE_URL` is set on Netlify and the web
    app has been redeployed; OTP login on `https://thewiseroom.app` lands on
    `thewiseroom.app/app/today`. Only the TD-69 cleanup PR remains.
12. **The "Continue with Google" button does not render on `/auth` in
    production.** The runtime flag `GET /api/v1/auth/methods` returns
    `google: false`. Filed as OPS-008, verify-then-fix.

Items 3, 7 and 8 are the ones worth re-checking first if anything looks wrong later:
each is a deploy-time fact that leaves a trace — `alembic_version`, a Sentry release,
a running worker — and none of those traces was read here.

---

## 3. What the letter rebuild actually had to solve

The interesting part of #6 was not the cron move. It was that **a repair mechanism
and a safety mechanism wanted the same index**.

`uq_job_run_name_key` exists so a period cannot be dispatched twice — that is the
whole point of a `run_key` derived from the period rather than from the clock. But a
missed period is one whose row exists and did **not** succeed, so the same index that
prevents a double-dispatch also answers "already ran" to a repair attempt, and the
repair is refused for the exact reason it is needed.

The resolution is that reclaim is a **distinct, guarded path** rather than a relaxed
constraint: catch-up — and only catch-up — may take over an existing row, on rules
that distinguish the four states (`succeeded` skip, `failed` reclaim, `running` older
than 2h reclaim, `running` newer than 2h skip). The live cron never reclaims, so the
double-dispatch guarantee is untouched on the path where it matters.

Two consequences were accepted deliberately rather than discovered later. **The
first period of each job has no automatic catch-up**: the floor is
`min(job_run.started_at)` per job, so if the very first scheduled run never opens a
row, Monday's catch-up sees no history and skips. That is carried as TD-67 with a
one-line manual remedy. And **catch-up looks back exactly one period** — a product
decision, recorded as such in R8a, not a technical limit.

---

## 4. Documented historical exceptions

**C-04 rule 2 (filename == revision id) has two grandfathered violations**, both
predating the rule's codification on 2026-06-26 and both printed by the checker's
`RULE_2_ALLOWLIST`: `013_add_ondelete_conversation_fks.py` carries
`revision = '013_conv_fk_ondelete'`, and `014_user_oauth_columns.py` carries
`revision = '014_user_oauth_cols'`. Alembic reads the in-file id, so nothing is
broken; they are not backlog items and are not to be renamed.

---

## 5. Corrections to prior docs

### 5a. The locked-persona paywall change was not on `main` — and now is (#615)

**Carried as merged at `076f74b7`. It was not.** Verified by content rather than by
title, because a squash merge rewrites the SHA and an ancestry check cannot answer
the question. At `076f74b7`:

- The remote branch `origin/fix/web-locked-persona-paywall` still exists at
  `c4a72220`.
- **All four files the branch adds are absent from `main`** — `lib/personaLock.ts`,
  `lib/__tests__/personaLock.test.ts`,
  `components/personas/__tests__/PersonaPickerSheet.test.tsx` and
  `lib/__tests__/useTopicConversation.test.tsx`.
- On `main`, `PersonaPickerSheet.tsx` still answers a locked-persona tap with
  `toast.error('Could not open conversation. Try again.')`. On the branch, it gates
  on `is_accessible`, tracks `upgrade_clicked` with `surface: 'persona_locked'`, and
  routes to the upgrade page.
- `useTopicConversation.ts` on `main` has no lock routing at all.

It was **not merged under a different title** — the code was simply not there. The
`persona_locked` occurrences that did exist on `main` were the pre-existing
#576/#582 sites.

**It merged as #615 (`e840053c`) during this rotation**, and that was verified the
same way rather than taken on report: all four files are now present on `main`, and
`PersonaPickerSheet.tsx` imports `lockedPersonaUpgradeHref` and gates on
`is_accessible`. `vitest` at `e840053c` returns 248 passing where `076f74b7`
returned 227 — the 21 new tests the PR brought — with the same 13 failures.

**The lesson survives the fix, and is the reason this entry stays:** a smoke test on
a preview deploy is evidence about the branch, not about `main`, and a squash merge
means only content can answer whether work landed.

### 5b. `weekly_letters` has never had a `week_start` column

v27 described the table as keyed on `week_start`. Verified by reading the model: the
columns are `period_start`, `period_end` and `kind`, and the unique index is
`uq_weekly_letters_user_period` on `(user_id, period_start, kind)`. This matters
because the whole of D-2 and R7 is about what `period_start` is computed *from*; a
reader working from the old name would look for a column that does not exist.

### 5c. "22 swallowing handlers" was right, is still right, and lacked only a command

Three docstrings state that the `LoggingIntegration` default covers **22** sites:
`observability.py`, `test_observability.py:12` and `test_observability.py:110`.

**22 is correct, and has been correct at every SHA.** The antecedent is the sentence
immediately before it — "event_level=ERROR turns every `logger.error(..., exc_info=True)`
into an event" — so "those sites" are the `exc_info=True` **call sites**:

| SHA | `arq_worker.py` | `cron.py` | `letter_dispatch.py` | total |
|---|---|---|---|---|
| `a67ddadd` (#587) | 14 | 8 | — (file did not exist) | **22** |
| `f22ad6c6` (#611) | 13 | 5 | 4 | **22** |
| `076f74b7` (today) | 13 | 5 | 4 | **22** |

The composition changed completely — #610 created `letter_dispatch.py` and moved two
jobs out of `cron.py` — and the total did not move.

**No number was changed. What was added is the command that produces it**, embedded in
`observability.py` so the next measurement is the same measurement:

```
grep -h "exc_info=True" workers/{arq_worker,cron,letter_dispatch}.py   | grep -vc "^[[:space:]]*#"
```

The second `grep` is load-bearing. Two **comments** mention `exc_info=True` while
describing this very mechanism (`arq_worker.py:1357`, `letter_dispatch.py:335`);
counting them turns 22 into 24.

**This entry was wrong twice before it was right**, and both attempts are recorded
because the shape is the lesson. First it claimed 22 had never been true, on the
grounds that the paragraph's other numbers are "ARQ task (12) and cron job (9)" and
12 + 9 = 21 — attaching the number to the wrong antecedent and "correcting" it to a
different quantity. Then, told the definition was `exc_info=True` sites, it measured
with a bare `grep -c`, counted the two comments, and "corrected" 22 to 24. Both were
caught in review before the PR opened. **Each attempt was a competent measurement of
something the sentence did not mean.** See §6.

### 5d. "345 unauthored questions" is now zero

`self_portrait.py:219` and `test_portrait_theme_scores.py:113` both describe the
legacy fallback as carrying "the 345 unauthored questions". After #614 there are
none. **Both corrected this rotation — prose only.**

A third occurrence of `345`, at `test_portrait_theme_scores.py:310`, is a **verbatim
quotation of Ruling #3's Greek** (`"οι 345 αργότερα, σταδιακά"`) and is deliberately
left alone: it is a record of what was decided, not a claim about what is true today.
Neither module docstring contained a `345` claim, and neither was stale.

### 5e. The number of stale branches is 26, not 7

At `076f74b7` there were **27** remote branches besides `main`: twenty-six stale,
dating from 2026-05-09 to 2026-06-14, plus `fix/web-locked-persona-paywall`, which
was live unmerged work and would have been destroyed by a blanket cleanup. #615
merged it and deleted its branch, so **26 remain and all 26 are deletable.** The full
list is an appendix in `IMPLEMENTATION_BACKLOG_v28.md` so the NIKOS-ACTION is a
checklist rather than a count.

---

## 6. Lessons this rotation

**A rollback fixture and the code under test can each be correct and still be
incompatible.** Three `db_live` tests failed in CI with "no row could be read". The
`db` fixture hands every test one outer transaction and rolls it back at teardown;
`_open_job_run`'s collision path calls `db.rollback()`, which under that fixture
rolled back the **outer** transaction and erased a row the test had only flushed. The
cause was a seam, not a defect: in production `_open_job_run` runs on its own session
and the colliding row was committed by an earlier process. The repair was to seed
through a committed side session — that is, to make the fixture express "a row
committed by a previous process", which is the precondition the test was actually
about. Recorded in the docstring of `tests/db_live/test_letter_catch_up.py`.

**A test that depends on DATA STATE rather than on a contract breaks on the day the
data completes.** Two tests selected an unweighted question out of the real bank with
`next(...)`. They passed for months and would have gone red on #614 — not stale, red
— because the bank became fully authored. The property they check (the fallback
contributes equally to numerator and denominator) has nothing to do with how much of
the bank is authored, and once the specimen was synthetic the tests became
indifferent to authoring progress. The scope pin next to them is the deliberate
opposite: it depends on data state **on purpose**, so each batch is a visible edit
rather than a number that drifts.

**A count without a stated definition is not a verifiable claim — and a definition in
prose is still ambiguous. The command is the definition.** "22 swallowing handlers"
was correct at every SHA. This rotation attacked it twice and got two different wrong
answers: 21, by reading it as ARQ tasks plus cron jobs; then 24, by reading it as
`exc_info=True` sites but measuring with a `grep` that counted two comments *about*
`exc_info=True` as sites. The second attempt had the right definition in English and
still produced the wrong number, which is the whole point — "`exc_info=True` call
sites under `workers/`" sounds unambiguous and is not, because it does not say what
happens to a comment. The remedy shipped here is not a better sentence but an
executable one: the exact `grep` pipeline now sits beside the number, so the next
reader re-runs a measurement instead of reconstructing one. A number whose definition
must be inferred will be re-derived under a different one, and the re-derivation will
look like a fix.

**Env vars are per-service, and a worker inherits nothing.** Three times this cycle a
variable was set on the API and the worker went without it — and each default is
wrong in a way that is silent rather than loud: `SENTRY_DSN` defaults to `""` and
disables reporting, `API_BASE_URL` defaults to `http://localhost:8000` and trips the
letter guard's `localhost` suppression path, `FROM_EMAIL` defaults to
`noreply@philosopher.app`, a domain the product no longer uses. None of the three
raises. The checklist is now OPS-007 and is repeated in the handoff.

**A unique index that prevents a bad write also prevents the repair of one, unless
the repair is a distinct guarded path.** See §3. The generalisation worth carrying:
whenever a constraint encodes "this must happen at most once", ask what the recovery
story is for the case where it happened zero times *and left a row*.

**`LoggingIntegration` is the Sentry path here, and an explicit `capture_exception`
would double-report** (R9a). Every task catches its own exception and logs rather
than re-raising, so `ArqIntegration` — which only sees exceptions that escape — would
report nothing. What reports them is the SDK's default `event_level=ERROR` turning
`logger.error(..., exc_info=True)` into an event. That is a **default being relied
on**, which is why the test asserts it against the installed SDK rather than
describing it in a comment.

---

## 7. Changelog — `#593` … `#615`

| PR | Title |
|---|---|
| #615 | Route locked-persona taps to paywall with `source=persona_locked` instead of raw error toast |
| #614 | Pro pill-weights tranche C — solitude/desire/mortality (Ruling #3, batch 4/4, FINAL) — bank complete at 360/360 |
| #613 | Pro pill-weights tranche B — fear/meaning/identity/conflict (Ruling #3, batch 3/8) |
| #612 | Pro pill-weights tranche A — money/family/relationships/friendship (Ruling #3, batch 2/8) |
| #611 | Explicit period + catch-up with `job_run` reclaim (PR-C) |
| #610 | Weekly + monthly dispatch move to ARQ cron with a `job_run` row (PR-B) |
| #609 | `job_run` table + `weekly_letters.email_suppressed_reason` (059, PR-A) |
| #608 | Allow `status='failed'` — the failure row the generators had always tried to write (058, D-1) |
| #607 | Pro pill-weights batch 1/8 — work_and_ambition 002-030 (Ruling #3) |
| #606 | `<what_you_know>` standing-memory block in weekly and monthly letters (Ruling #1(d), PR-3) |
| #605 | Hybrid recall — two lanes, standing always-in, inferred floor 0.75 with per-type quota (Ruling #5, PR-2) |
| #604 | Conversation FKs to SET NULL on `memory_entries` and `insights` (057, PR-1) |
| #603 | Counterview fails closed on orphaned insights — suppress when `conversation_id` is NULL (F-15) |
| #602 | Memory-v2 design — hybrid recall, SET NULL cascade, memory-everywhere rollout |
| #601 | Build 048-state quotes from the seed file minus 049's inserts, not the seed script |
| #600 | Live-Postgres fixture via CI service container; first DB-backed tests for recall and cascades |
| #599 | Remove dead surfaces — stale cron, insight task, uncalled service methods, `feeds` field |
| #598 | Council synthesis step receives memory via shared recall; members stay cold by design |
| #597 | Replace memory dampening with founder-approved use directive |
| #596 | Answer-sensitive octagon — approved per-pill weights, share-of-achievable scoring, render max-normalize |
| #595 | Regenerate summary and forming preview on answer-set fingerprint change, not count delta |
| #594 | Resolve invoice subscription id across Basil relocation; guard None keys on nullable-column lookups |
| #593 | Rotation v27 — project state, backlog, handoff (#564–#592) |
