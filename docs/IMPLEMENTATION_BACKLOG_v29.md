# GREAT MINDS — Implementation Backlog v29

> **Verification SHA:** `93aa06932de12a03c4c523f47733bf9897c44d0f`.
> **Date:** 2026-09-11.
> **Companions:** `PROJECT_STATE_v29.md`, `HANDOFF_BRIEF_v29.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md`. v28 files preserved byte-identical.

---

## ⚠️ HOW TO READ THIS FILE

**Every item below was re-verified against the code at `93aa0693`.** Nothing is
copied forward. Where an item is unchanged, the verification that established that is
stated — "unchanged" alone is not evidence and is not used as such.

**Closed items are recorded with the method that proved the closure**, not with the
PR number alone. A PR title is a claim about intent; the grep is the claim about
state.

**One framing correction applies across this file.** The "Greek-first audience"
premise is FALSE as of the founder decision of 2026-09-11 — the target audience is
English-speaking and Greek support is a safety net, not go-to-market. Two items in
v28 (TD-60, TD-61) used that premise to justify their *priority*. Both are now
closed, so nothing here still rests on it, but any future argument of the form "we
should also do X for Greek" no longer inherits first-audience priority from these
documents. Full correction: `PROJECT_STATE_v29` §3c.

---

## 1. Tech debt — CLOSED this rotation

### TD-58 — Remove `passlib` and `bcrypt` — **CLOSED (#619)**
**Verified:** `grep -nE "passlib|bcrypt" apps/api/requirements.txt` returns nothing;
`grep -rl "passlib\|bcrypt\|CryptContext\|pwd_context" --include=*.py` returns **0
files**. Dead since #586 removed `hash_password` / `verify_password`; shipped as its
own PR per P-02 because it changes the Docker build.

### TD-60 — Postprocessing voice checks were English-only — **CLOSED (#621, #622)**
**Verified:** `services/postprocessing_service.py` now has **2** occurrences of
`casefold`/`unicodedata` (v28: zero) and **5** `.lower()`/`re.IGNORECASE` sites
(v28: 9). The universal forbidden lexicon is **210 phrases across 12 categories**
(v28: 123), and **11 of 11** personas carry
`forbidden_lexicon_persona_specific` (v28: 8 of 11 — `lao_tzu`,
`niccolo_machiavelli` and `oscar_wilde` were the three without, and all three now
have one).

Part 1 (#621) folded Greek in the checks and made the stripper remove what was
actually matched; part 2 (#622) supplied the Greek entries and the last three persona
lexicons.

### TD-61 — The Greek safety lexicon had never been read by a Greek speaker — **CLOSED (#618, #622)**
**Verified by importing both SHAs and counting identically:** **219** entries across
the four bands (HIGH 95, MEDIUM 50, OUTPUT 22, LOW 52), of which **76** contain Greek
script. v28 measured 210 / 73, and that was correct for v28.

**The review re-banded rather than appended** — MEDIUM −9, OUTPUT −11, LOW +22,
HIGH +7. MEDIUM false positives moved to LOW and generic OUTPUT phrases were removed.
Each band is `_EN + _GR + _GL`; the third tier is **greeklish**, and it is the only
thing covering a greeklish typist, because `dominant_language` reads greeklish as
English by design.

Closes NIKOS-ACTION 5.

### TD-63 — The fair-use refusal path had never rendered — **CLOSED (#623, #624)**
**Verified:** two web test files now exercise it —
`apps/web/lib/__tests__/fairUseToast.test.tsx` and
`apps/web/app/app/counterview/__tests__/fairUsePaywall.test.tsx`. v28's grep for
`fairUseMessage|fair_use_limit|FAIR_USE_COPY` in the test suite returned zero hits.

**#624 fixed a real defect found while covering it:** the two caps arrive as the same
429 and only `error_code` separates them, so a **Pro subscriber** hitting the cost cap
was shown the **upgrade wall** — selling them a tier they already own and filing a
false `upgrade_clicked` against it. Verified at
`apps/web/app/app/counterview/page.tsx:126`: `fair_use_limit` now branches to a plain
notice before the upgrade path.

### TD-64 — A `db_live` test committed a row it never cleaned up — **CLOSED (#620)**
**Verified by source read:** `tests/db_live/test_letter_catch_up.py:353` now calls
`committed.track("2026-W40")`, so the committed `job_run` row is removed rather than
surviving the fixture's outer-transaction rollback.

### TD-69 — `NEXT_PUBLIC_BASE_URL` pointed at a stale host — **CLOSED (#617)**
**Verified:** `git ls-files apps/web/.env.production` returns **0** — the file is
untracked — and `apps/web/app/layout.tsx:40` now reads
`process.env.NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'`.

The user-visible half had already closed with the 2026-09-08 cutover (the dashboard
value takes effect). This was the hygiene half: the repository no longer carries two
dead hosts for the next reader to believe.

**The lesson this one leaves behind:** `git check-ignore` reports nothing for a
tracked file. `.gitignore`'s `.env.*` rule only ignores *untracked* files, which is
why the file sat tracked for months while the rule read as covering it.

### TD-72 — The published OTP retention window was not enforced — **CLOSED (#637)**
**Status: CLOSED. Opened and closed after this rotation, so it appears here only as
a closure.** Privacy Policy §6 publishes "OTP codes: up to 1 hour". Nothing enforced
it — `OTP_EXPIRY_MINUTES = 10` gates whether a code still VERIFIES, and no process
deleted the row, so retention was unbounded. Account deletion did not reach the table
either: `otp_codes` carries no `user_id`, so 056's cascade cannot see it and the
deleted person's email address survived.

A 10-minute ARQ cron purging rows past a 30-minute cutoff enforces the published hour
(worst case 40 minutes; 60 after two consecutive missed runs), and `delete_account`
now deletes by email.

**VERIFIED IN PRODUCTION, by sequence rather than by a single number** — a bare
`otp_codes = 0` is equally what an empty window looks like:
  1. **2026-09-12 ~12:01 UTC**, founder-run SQL: **2 rows**, both `created_at` 11:44
     UTC that day (the founder's own login).
  2. **2026-09-14 07:20 UTC**, Sentry: `OTP purge FAILED … password authentication
     failed` from `cron:purge_expired_otp_codes` on the worker, during the
     password-rotation window — so the cron is **provably firing on schedule**; a
     failed run is still a run.
  3. **2026-09-14**, founder-run SQL: **0 rows**.

Rows present, then gone, with no account deletion in between. That Sentry event is
also the first production proof that the worker's Sentry integration fires on a
**cron** failure — `init_sentry()` exists in `workers/arq_worker.py` because the
worker never imports `main`, and nothing had demonstrated the wiring from a scheduled
job until a credential rotation did it by accident.

---

## 2. Tech debt — OPEN, re-verified this rotation

### TD-57 — Live-DB integration tests are CI-only — **DECIDED 2026-09-12**
**Status: DECIDED. Closed as debt, recorded as a boundary. Nothing was fixed —
the item was reclassified, which is why this is not marked CLOSED.**
**Verified:** `pytest tests/db_live --collect-only -q` reports **45 tests** across
four files (`test_job_run.py`, `test_letter_catch_up.py`,
`test_letter_failed_status.py`, `test_memory_recall_and_cascades.py`), run by the
`db-tests` CI job (`pgvector/pgvector:pg16`, `DATABASE_URL_TEST` set in the job
env) against a Postgres service container. The job carries no
`continue-on-error`, so a schema regression blocks merges.

**`db_live` is CI-only by decision.** The configuration already exists in two
places — `infra/docker-compose.yml:6-21` defines `db:` on the same
`pgvector/pgvector:pg16` image CI uses, and `tests/db_live/conftest.py:22-27`
carries a copy-paste `docker run` one-liner on port 5433. What is absent is
Docker on the maintainer's machine, which makes this an install decision rather
than engineering work. The pgvector image is not optional: `001_initial.py:19-20`
runs `CREATE EXTENSION vector`, and `008_hnsw_vector_indexes` builds HNSW
indexes that plain `postgres:16` cannot.

**Nobody is taxed by leaving it.** The gate skips at module level rather than
erroring (`conftest.py:197`), so a machine with no `DATABASE_URL_TEST` runs the
suite green with 45 skips. There is no red state to remove.

**The measurement, kept because a decision without it is what the next rotation
re-opens.** Across the 23 PRs from #617 to #639 (2026-09-08 to 2026-09-12),
**exactly one** touched `db_live` at all — #620, 36 lines in one file, authored
and merged with CI as the authority. One further PR had a live-schema dimension
that went partially verified: #637's OTP purge was checked at statement level
against a fake session, not against a migrated schema. Every other PR in the
window was prompts, lexicon, copy, web tests, mocked router tests or docs, and
none had a revert-verify leg a local schema would have unblocked.

**A local database would also be worse in one respect than CI's.** TD-64 (#620)
exists because one test commits a row, and its docstring says why that was
invisible: "On CI that is invisible, because each run gets a fresh Postgres
container. On any PERSISTENT database the row is permanent."
`infra/docker-compose.yml` is volume-backed (`postgres_data`), so a local setup
is exactly the persistent case and would need its own cleanup discipline.

**REVISIT CONDITION:** if schema-shaped PRs rise above roughly 1 in 23.
Re-measure the same way — count PRs in the window that touch `tests/db_live`,
migrations, or model FK/ON DELETE clauses — rather than re-arguing it from
impressions.

**THE PROPORTIONATE ANSWER TO #637's GAP, so nobody reaches for infrastructure
instead:** one `db_live` test for the purge predicate — that `DELETE … WHERE
created_at < cutoff` removes the intended rows and leaves in-window rows alone
against a real schema. One test in the suite CI already runs. To be added
whenever someone next opens `tests/db_live/`, not as a PR of its own.

**Diagnosability of the `db-tests` job is deliberately left alone** — it has no
`-ra`, no `--tb` setting, no artifact upload and no step summary. Those are cheap
to add and their need is unproven (no `db-tests` failure has yet been hard to
read), so they attach to the next change to that workflow rather than justifying
one.

**What came out of this investigation and is NOT this item:** the staged build
the `db_live` fixture needs exists because production is not reconstructible from
the migration chain alone. That is a disaster-recovery property at its own
severity and is now **TD-73**.

### TD-59 — No test pins the privacy policy against the implemented rights
**Status: OPEN. Re-verified, unchanged.**
**Verified:** the policy is **Version 1.3, effective 2 September 2026**
(`apps/web/app/legal/privacy/page.tsx:24`). Generated `openapi()` in-process:
`/api/v1/auth/me` exposes DELETE, GET and PATCH; `/api/v1/auth/me/export` exposes GET
— erasure, access, rectification and portability all have routes.

Policy and code agree today; nothing enforces that they keep agreeing. #588 had to
amend the policy because it promised a soft delete that was never built, and that
mismatch survived because a legal document and an endpoint share no test.

### TD-62 — No export completeness guard
**Status: OPEN. Re-verified, unchanged.**
**Verified:** `grep -c "completeness\|mapped class\|__mapper__" tests/test_data_export.py`
returns **0**. Every test there is shape or exclusion.

If a future PR adds a table carrying `user_id`, nothing fails and the export silently
under-reports — a GDPR Art. 15 defect that looks exactly like a working export.
**Proposed shape:** enumerate mapped classes carrying `user_id` and assert each
appears in the payload **or** in a documented exclusion set.

### TD-65 — `generate_weekly_mirror_task` carries the D-2 pattern
**Status: OPEN. Latent. Out of scope until a mirror catch-up is wanted.**
**Verified by source read:** `workers/arq_worker.py:1171` still computes
`period_end = datetime.now(timezone.utc)`, with `period_start` derived from it — the
period comes from execution time, not from an argument.

Same shape as the letter defect D-2 fixed. Dedup is by
`(user_id, period_start, kind)`, so a catch-up run on a different day would compute a
different `period_start`, miss the index, and write a **second mirror for an
overlapping period**. It must not be fixed opportunistically; it becomes real work
the day someone wants mirrors to self-repair, and then it is the fix PR-C made: pass
the period in.

**New this rotation, and relevant if anyone does open it:** #631 added a language
source to this task that reads `messages`, which the query already filters to
`role == "user"`. That filter is now load-bearing and is pinned by
`test_the_mirror_query_still_filters_to_the_person_and_this_is_load_bearing`.

### TD-66 — The legacy per-tag fallback is tolerance, not an active path
**Status: OPEN as a documentation/decision item, not as a defect.**
**Verified:** the bank is **360/360 weighted**, so `_pill_axis_sums`'s fallback branch
is unreachable for every real question. It is exercised only by tests injecting a
synthetic bank, and the scope pin `assert len(sp._BANK) - len(weighted) == 0` means a
new unweighted question cannot ship silently.

**Recommendation: keep it**, as deliberate tolerance for a question authored before
its weights are. What matters is that it is named as tolerance — an unreachable
branch nobody has decided to keep is what becomes a stale claim two rotations later.

### TD-67 — Catch-up cannot repair the very first run of a job — **HALF CLOSED**
**Status: OPEN for the monthly job only. The weekly instance passed 2026-09-13
without the remedy.**
**Verified by source read:** `workers/letter_dispatch.py:318` selects
`func.min(JobRun.started_at)` per `job_name` as the catch-up floor. If the very first
scheduled run never opens a row at all, the next catch-up sees no history and skips.

Applied exactly twice. **Weekly, Sunday 2026-09-13: PASSED** — the run opened its
own `job_run` row (`status=succeeded`, counts 3/2/2), so the floor exists and the
manual remedy was never invoked. **Monthly, 2026-09-30: still open**, and it is now
the only instance left. From the second period onward, catch-up covers a fully
missed run. Remedy for the remaining case: the manual command in the rulings doc's
Ops section with `run_key='2026-09'`.

**See `HANDOFF_BRIEF_v29` §1 — this is the item most likely to matter first.**

### TD-68 — The stale-`running` threshold is a bare constant
**Status: OPEN as documentation. Do not tune.**
**Verified by source read:** `STALE_RUNNING_AFTER = timedelta(hours=2)`
(`workers/letter_dispatch.py:55`), used to decide whether a `running` row is a crash
to reclaim or a job still in flight.

Two hours is a judgement about the longest a dispatch could legitimately take, and no
measurement supports or contradicts it. **It should not be tuned until a real run has
been timed** — lowering it risks reclaiming a live job and double-dispatching a
period, which is the exact failure the unique index exists to prevent. The Sunday run
is the first opportunity to time one.

### TD-70 — The insight → counterview route is uncapped — **NEW**
**Status: OPEN. New this rotation. Not a regression; it has always been so.**
**Verified:** `grep -c "rate_limit\|check_limit\|fair_use" apps/api/routers/memory.py`
returns **0**. `POST /insights/{id}/counterview` calls `generate_counterview`
directly, with no rate-limit dependency.

The direct path (`POST /counterview`) is capped — free daily and Pro fair-use both.
The insight-seeded path is not. It is bounded in practice by the app-level dedup (one
counterview per insight, so a second tap returns the existing row without an LLM
call) and by the insight throttle upstream, so this is a cost-shape observation
rather than an open door. **Recorded because "bounded in practice by something
else's dedup" is exactly the kind of implicit guarantee that a later refactor
removes without noticing.**

### TD-71 — `_is_null_reply` has no production caller — **NEW**
**Status: OPEN. Trivial. Recorded, not fixed.**
**Verified:** `grep -rn "_is_null_reply" --include=*.py` outside tests returns the
definition and one docstring mention — **zero call sites**. It is referenced only by
`tests/workers/test_letter_write_back.py`.

It was left in place during #631 rather than removed alongside the dead
`INSIGHT_PROMPT`, because removing it means deleting its tests and that is a separate
decision, not one to fold into a prompt-language PR. The docstring now says so.

### TD-73 — Production is not reconstructible from migrations alone — **NEW**
**Status: OPEN. Disaster-recovery defect, not a test inconvenience. Higher
severity than TD-57, which is where it was found.**

**Verified independently of the docstring that reports it:**
`db/migrations/data/quotes_049_data.json` carries `updates: 88` and
`inserts: 110`; `049_quotes_expand`'s own docstring says "UPDATE the `context` of
all 88 existing rows … Each update MUST touch exactly one row; a 0-row match
means the live text_en drifted from the snapshot, so we RAISE"; and across every
migration that mentions `quotes`, **049 is the only one carrying an insert
operation**. So the 88 rows 049 reads back are inserted by nothing in the chain.

**`alembic upgrade head` therefore does not run on an empty database.** It fails
inside 049 on a 0-row match — by design, since that check exists to catch drift.
This was not reasoned about; CI's first `db-tests` run proved it.

**And the seed script can no longer stand in for the missing stage.**
`db/seed_quotes.py` says "run once after migration 045", but
`data/quotes_seed.json` now holds **198 rows across 11 personas** — the 88 that
predate 049 plus the very 110 that 049 inserts. Run at 048-state it inserts 049's
own rows ahead of it, and 049's `bulk_insert` dies on
`uq_quotes_persona_locator_text`. The failing key in that CI run was
`(socrates, "Plato, Apology 28b-d", "Count neither death nor anything else before
disgrace.")` — row 0 of 049's insert list.

**Why this is more serious than the item it came out of.** TD-57 is a testing
boundary that costs nothing while it stands. This is a property of the production
database: if it were lost, it cannot be rebuilt from the repository. The trigger
is an event nobody schedules, the blast radius is the whole corpus, and nothing
in the system exercises the path — it surfaced only because CI rebuilt from
scratch for the first time. Left unnamed it stays invisible indefinitely, because
every ordinary deploy migrates a database that already has the rows.

**NO LOCAL POSTGRES FIXES THIS.** The `db_live` fixture works around it with a
three-stage build (`conftest.py:210-212`: upgrade to 048, reconstruct the
045-era corpus as the seed file minus 049's rows, upgrade to head). That makes
the tests run; it does not make the chain sound, and the subtraction lives in a
test fixture rather than anywhere a recovery would look.

**WHAT WOULD DETECT A REGRESSION OF THIS SHAPE: nothing does today, and the
`db-tests` job does not — it routes around the gap rather than testing it.**
Verified: the only `alembic upgrade head` **in the test path** is
`conftest.py:212`, and it runs from the **seeded 048 state**; the upgrade that
runs against an empty database is `conftest.py:210`, which stops at 048. So the
defect lives strictly between 048 and head, in exactly the interval the fixture
steps over. If a future migration adds the same shape — reading rows back that
no migration inserts — it fails the same way, and nothing warns first.

*(Corrected 2026-09-17: this sentence read "the only `alembic upgrade head`
anywhere in the repository". That was false — there are six, including
`Dockerfile:17`, which is the one that applies migrations to production. The
claim was scoped to the test path, where it is true, and the argument above is
unaffected. See TD-81.)*

A cheap guard is available: a CI step that creates an empty database and runs
`alembic upgrade head`, asserting it succeeds. Note the ordering, because it
decides when the guard can be written: **today that assertion would be red on
arrival**, since `upgrade head` from empty does fail. So it is the regression
test for fix 1 rather than something to add ahead of it. The alternative — a
guard that pins the *current* failure — records the defect but would have to be
inverted by the same PR that fixes it, which is a choice belonging with the fix.

**Two candidate fixes, deliberately not chosen here — founder call:**
  1. **Make the chain self-sufficient.** Add a migration before 049 that inserts
     the 88 rows as a frozen literal snapshot (C-01), so `alembic upgrade head`
     runs on an empty database. Costs one migration and a decision about what
     047-era content was; buys a repository that rebuilds itself.
     **CONSTRAINT, and it may be what decides between the two options:** 049's
     downgrade "does NOT restore the pre-rewrite context text of the 88 rows —
     the old contexts are not captured in the snapshot; this content change is
     forward-only by design." The pre-049 contexts are therefore captured
     nowhere. A self-sufficient chain would have to insert the 88 rows **with
     their post-049 contexts and skip 049's update for them**, or reconstruct
     text that may no longer exist anywhere.
  2. **Document the staged rebuild as the supported path.** Write the three
     stages into a recovery runbook and accept that `upgrade head` alone is not
     the entry point. Costs nothing now; leaves the knowledge in prose, which is
     what this file's own 2026-08-18 entry warns about.

Not a rewrite of TD-57 and not a decision to be taken inside one.

### TD-74 — The export completeness guard is table-level, not column-level — **NEW**
**Status: OPEN. Found by the defect it failed to catch, not by review.**

**Verified:** `tests/test_data_export.py` builds its universe from
`"user_id" in {c.name for c in m.columns}` — it asserts every user-scoped mapped
CLASS is queried by `build_export` or documented as excluded. It says nothing about
which COLUMNS of an exported class reach the file, because `build_export` assembles
each section as an explicit dict of named fields.

**The proof is a live under-report, not a hypothetical.** `insights.source_count`
was absent from the export dict from the day the export shipped until migration 060. The
guard passed the whole time — `Insight` was queried, so the class was accounted
for — while an Art. 15 request returned insight rows with the recurrence strength
silently missing. It was found while adding a *different* column, by reading the
dict, which is exactly the review step a guard is supposed to replace.

**Why this is the same shape as TD-62 one level down.** That entry closed "a new
user-scoped TABLE is silently missing". This is "a new column on an already-exported
table is silently missing", and the second is more likely than the first: tables
arrive rarely and visibly, columns arrive constantly.

**Two candidate shapes, neither chosen:**
  1. **Per-class column enumeration.** Introspect each exported mapped class's
     columns and assert every one is either present in its payload dict or in a
     per-class documented-exclusion set with a reason — the same contract TD-62's
     guard applies to classes. Strongest, and noisy: `embedding`, the telemetry
     columns and the Stripe ids are all deliberate omissions that would each need a
     line. That noise is arguably the point, since every one of them is a decision
     somebody made once and nobody has re-read.
  2. **A documented per-table field list** checked against the dict. Cheaper, but it
     is a second list to maintain beside the dict itself — which is the tautology
     TD-62's entry warns about: a hand-kept list asserting it matches itself.

**Not built here.** Recorded because the instance that revealed it was fixed in the
same PR, and a defect class whose only instance is closed is exactly the kind that
stops being written down.

### TD-75 — A period-bounded recurrence search can quietly under-recall — **NEW**
**Status: OPEN. Low severity. Accepted deliberately, not undiscovered.**

**Mechanism.** `find_recurrences` with `corpus_since`/`corpus_until` is a FILTERED
nearest-neighbour search. Postgres applies the date clause DURING the HNSW index
scan (`ix_memory_entries_embedding_hnsw_cosine`, migration 008) rather than after
it, so when the filter is selective — a heavy week, most of the user's recent rows
inside the period — the scan can exhaust `hnsw.ef_search` before it finds
`RECURRENCE_LIMIT` rows that pass.

**What that costs.** Rows returned are always genuine matches; the bound never
invents one. The risk is the other direction: real pre-period echoes that exist and
are not found. **The failure is silent** — a trajectory snapshot would simply say
less than it should, and nothing would look broken.

**Not tuned, for three reasons.** No measurement of either the current recall or
the degraded recall exists. `hnsw.ef_search` is a GLOBAL knob whose only other
consumer is the request-path `recall()`, so raising it for a weekly cron would
change chat behaviour to fix a batch job. And at the scale this runs at today —
three weekly candidates on 2026-09-13 — it is theoretical.

**The two levers, recorded so the fix is not re-derived:** raise
`RECURRENCE_LIMIT` on the bounded path only, or set `ef_search` for that statement
(`SET LOCAL`) rather than globally.

**TRIGGER CONDITION — the thing to watch for, since the failure is quiet:** a
snapshot that reads thin on a week the person was demonstrably busy. Concretely,
a period whose `recurring_questions` is empty or near-empty while the same user's
in-period entry count is high. That asymmetry is the symptom; nothing alerts on it
today, and the first instance will be noticed by a human reading their own
snapshot rather than by a check.

Recorded in `find_recurrences`'s own docstring as well, because a reader who meets
the function should meet the limit without opening this file.


### TD-76 — No local check that a `db_live` fixture can actually insert — **NEW**
**Status: OPEN. Proposed, not built. Severity is measured in round-trips, not risk.**

**Why it exists: three CI round-trips on one file.** `tests/db_live/`
`test_period_recurrence_filter.py` failed three times in a row, each on the fixture
layer rather than on the behaviour under test:

  1. `from .conftest import *` — the directory is not a package. Caught locally, at
     collection, before pushing.
  2. `INSERT INTO conversations (id, user_id)` — `persona_id` is NOT NULL with no
     default. **Caught by CI.**
  3. `created_at='2026-09-10T10:00:00+00'` — asyncpg binds a `timestamptz`
     parameter from a `date`/`datetime` only, and raises `DataError` at BIND time.
     **Caught by CI.**

None of the three was a defect in the code under test. All three were the fixture
failing to produce a row, and **none was visible to the mocked layer**, because a
mock accepts any parameter of any type and returns whatever it was told to.

**The proposed guard, and it is cheap.** A mocked test that drives each `db_live`
seeder against a recording fake, captures the emitted statement and its bound
parameters, and asserts two things against `Base.metadata`:

  - **column presence** — every NOT NULL column without a default appears in the
    INSERT (catches miss 2);
  - **parameter TYPE** — every parameter bound to a `DateTime` column is a
    `date`/`datetime`, every one bound to a `UUID` column is a string of the right
    shape, and so on (catches miss 3).

The type half is the part that would not have been written without miss 3, and is
the reason this entry says *types, not only presence*. Both checks were run by hand
while fixing that miss and both pass; what is missing is that they run every time.

**What it does NOT do, stated so a green run is not over-read.** It proves a fixture
can insert a row. It proves nothing about whether the WHERE clause under test is
obeyed — that is what `db_live` is for, and it remains CI-only by TD-57's recorded
decision. This guard shortens the feedback loop on the fixture layer; it does not
move the boundary.

**Trigger to build it:** the next time a `db_live` fixture is written or a seeded
table gains a column. Not worth a PR of its own today — the instance that motivated
it is fixed, which is exactly the condition under which this kind of item stops
being written down (see TD-74, same shape).


### TD-78 — A clean 200 from `/counterview/{id}/deeper` means six different things and says which one it is — **NEW**
**Status: OPEN. Not scheduled. Found while fixing BUG-007; logged rather than
built, because closing it needs a backend signal on the response and BUG-007's
brief scoped the frontend only.**

**Verified at `78e98c71`** by reading `services/counterview_service.py`
`deepen_counterview` end to end — every `return cv` site, not the endpoint's
docstring. The count in this heading is SIX, not the four the brief named. Two
the brief did not list are reachable and are in the table: the model returning
nothing usable (distinct from the exception path, though both exit at `:591`),
and a concurrent-write race at `:625`. Two further sites — `:545`, `:561` — are
excluded because a reader that is showing the tap cannot reach them.

**Mechanism.** The function returns the counterview **unchanged, with a clean
200**, on each of these:

| meaning | exits at | what actually happened |
|---|---|---|
| round cap reached | `:563-564` | the persona already spoke twice |
| **generation FAILED** | `:584-590` → `:591` | `_call_deeper_llm` raised; caught, logged at WARNING, `line = None` |
| nothing to add | `:591-592` | `_call_deeper_llm` returned `None` — non-`generated`, unparseable, or empty |
| safety suppression | `:596-597` | `check_output` flagged the line; it is discarded |
| output language mismatch | `:603-611` | the line came back in the wrong script |
| concurrent write lost the race | `:625-626` | `uq_counterview_response`; rolled back, `cv` returned unrefreshed |

The wire carries nothing that separates them. `Counterview` (`apps/web/lib/api.ts`)
has no field for it, and all six bodies are identical to the state the caller
already held.

**What that costs, after BUG-007 and not before it.** The BUG-007 fix (#672,
merged 2026-09-17) split the frontend's
single outcome set in two: a THROWN error now keeps the tap and offers a retry,
and only a SUCCESSFUL response carrying no round-1 line marks the persona
exhausted. That is the right reading for rows 1, 3, 4 and 5. It is the WRONG
reading for row 2 and row 6 — a backend LLM failure and a lost race both arrive
as a clean 200, so the reader still renders them as "this persona has nothing
more to say", silently, with the tap withdrawn. The class of failure BUG-007 was
raised about is therefore **narrowed, not closed**.

**Two consequences, stated because they are easy to leave implied:**

1. **We do not know which defect the 2026-09-14 UAT actually observed, and after
   this PR we still will not.** Button disappears, no deeper text, no error, no
   retry is the symptom of BOTH the frontend path this PR fixes and this backend
   ambiguity. From the user's side they are indistinguishable. The fix is correct
   on its own terms and its tests pin real behaviour; that is not evidence that
   the reported instance is gone.

2. **It weakens the `exhausted` state generally.** "Exhausted" is the frontend's
   INTERPRETATION of an absence, not the server's STATEMENT of a fact. Any screen
   that treats it as a fact — today only this one — inherits that.

**What closing it looks like, recorded so it is not re-derived.** One discriminated
field on the deeper response (`deeper_outcome`: `added | capped | nothing_to_add |
suppressed | failed`, say), set at each return site. The reader marks exhausted on
`capped` / `nothing_to_add` / `suppressed`, and takes the retry path on `failed`.
No migration — a response-schema addition and one frontend branch. Note the
deliberate grouping: **safety reports as an absence, never as a refusal**, so row
4 groups with `nothing_to_add` and not with `failed`. Row 6 is the one genuinely
new decision: a lost race means the line EXISTS, so the honest answer is to
re-read and return it rather than to report either outcome.

### TD-79 — `preview_mirror` runs unwatched, and the record saying so did not exist — **NEW**
**Status: OPEN. Not scheduled. Written to close a false claim already on `main`.**

**Verified at `78e98c71`** by reading `workers/cron.py` and `constants.py`, and by
grepping the repository for the record they refer to.

**The false claim first, because it is the reason this entry exists.**
`constants.py:270-271`, shipped in #669, reads:

> `preview_mirror is out because it writes no job_run row to check. It runs in`
> `the API process under APScheduler and leaves only log lines (TD logged).`

The exclusion is correct. **`(TD logged)` was not.** No such entry existed in this
file or anywhere else — a grep for TD numbers above TD-77 returned nothing at
`78e98c71`. The comment has been asserting the existence of a record since #669
merged. THIS is that record; the parenthetical is now true, and was not before.

**Mechanism.** `dispatch_preview_mirrors` (`workers/cron.py:275-308`) is
registered `@scheduler.scheduled_job(IntervalTrigger(hours=1), id="preview_mirror")`.
It runs **hourly, in the API process, under APScheduler** — not in the ARQ worker
— and enqueues `generate_weekly_mirror_task` for each user with ≥3 active chats
in 72h who has no mirror yet.

It writes **no `job_run` row**. `job_run` appears exactly once in `cron.py`, at
`:271`, and that occurrence is a COMMENT describing the jobs that DID move to the
worker. This job is not one of them.

So its only failure signal is the swallowed handler at the bottom:

```python
except Exception as e:
    logger.error(f"Cron preview mirrors failed: {e}", exc_info=True)   # cron.py:308
```

Caught, logged, not re-raised, not alerted on. Nothing reads it.

**What that costs.** A failed run and an hour in which nobody qualified are
**indistinguishable from outside the process**. Both produce no mirrors and no
row; one produces a line in the API log that no check reads, and the job is
eligible to run 24 times a day. The worker-absence alerting built in #669 cannot
cover it — that layer reads `job_run` rows, and this job leaves none — which is
precisely why `constants.py` excluded it rather than an oversight.

**Founder-reported context, and the artifact is now filed:** surfaced by **UAT-1
BUG-021** during the **14-16 September 2026** incident window. The register is
`docs/qa/UAT-1_2026-09-14.md`, filed 2026-09-18. BUG-021 there reads *"Mirror has
no useful first-session fallback"* — the tester opened Mirror on a low-history
account and got `Your first reflection is still forming.` That is the user-side
face of this entry: a mirror that never arrived and a dispatch job whose failure
nobody would have seen.

**What this paragraph said before, kept rather than overwritten.** It read: *"That
artifact is NOT in this repository — a case-insensitive grep for `BUG-021` across
`docs/` and `apps/` returns nothing at `78e98c71` — so this line records who
reported it and when, not a document a reader here can open. If UAT-1 is filed
somewhere durable, link it here."* All of that was true when written; the path
above is the link it asked for.

**One caveat on reading the register, because it is not a document about this
codebase.** It is filed VERBATIM as the tester delivered it, wrong route names
and all, and no build identifier was captured during the run. BUG-021 tells you
what a user saw on 2026-09-14; it is not evidence about `dispatch_preview_mirrors`,
and the mechanism above was verified by reading the code, not by trusting the
report.

**What closing it looks like.** **Move the job to the ARQ worker**, where
`cron_jobs` registration writes a `job_run` row per run and the existing
absence-alerting picks it up with no new machinery. Do NOT bolt `job_run` onto an
APScheduler job: that reimplements, in the process that is not the scheduler of
record, the exact bookkeeping the worker already does — and leaves two places
that know how to write the row. `constants.py`'s comment on the letter tasks
(R4/R5) is the precedent; the three remaining dispatch jobs in `cron.py` are
already queued to move "in one PR, only after a Sunday run proves the pattern"
(`cron.py:270-273`). **This job should go with them**, and that is the cheapest
version of this fix: it is not a separate piece of work, it is one more entry in
a migration already planned.


### TD-80 — The current-disclaimer query cannot express a scheduled consent change — **NEW**
**Status: OPEN. Not scheduled. Neither half bites today; both bite the first time
someone tries to schedule one.**

**Verified at `9e21dcca`**, found while writing migration 066 (BUG-005).

**Mechanism.** `get_current_version` (`services/disclaimer_service.py:26-36`) is:

```python
select(DisclaimerVersion).order_by(DisclaimerVersion.effective_at.desc()).limit(1)
```

Two properties follow, and neither is what the column name suggests:

1. **No tie-break.** Two rows sharing an `effective_at` order nondeterministically,
   so which consent text is served would depend on the plan Postgres happens to
   pick. `ORDER BY effective_at DESC, id DESC` is the whole fix.
2. **No `WHERE effective_at <= now()`.** A future-dated row is served
   IMMEDIATELY. `effective_at` reads like a scheduling field and is only a sort
   key — so the natural way to stage a consent change ("insert it now, dated for
   the 1st") publishes it on insert instead, to every user, silently.

**What it costs today: nothing.** There is one row, and 066 adds a second with a
later timestamp. Both hazards need a third row or a deliberate future date to
appear, and nothing in the product writes to this table outside migrations.

**Why it is still worth an entry.** The failure mode of (2) is a consent text
going live before it was meant to, which is the kind of thing noticed by a user
rather than by a check — and the person who hits it will be reaching for exactly
the phrasing the column invites. 066 therefore leaves `effective_at` to its
server default rather than choosing a timestamp, and says so in its docstring;
that is a workaround for this item, not a design.

**Both levers, recorded so they are not re-derived:** add the `id DESC`
tie-break, and add the `effective_at <= now()` filter. They are independent, both
one line, and (2) is the one that changes behaviour — after it, a future-dated
row means what it looks like it means.

### TD-81 — The repository cannot tell a reader how migrations reach production, and one file asserts the opposite of the truth — **NEW**
**Status: OPEN. Nothing to build — the mechanism works. The fix is that it is
discoverable.**

**Verified at `a9d01ea7`**, and the mechanism confirmed from the Render deploy log
for `dep-dalu95m7bikc73c7mobg`:

```
13:02:08 UTC  alembic.runtime.migration  Running upgrade
              065_council_insight_id -> 066_disclaimer_wise_room
```

So `alembic upgrade head` runs at container start, from `apps/api/Dockerfile:17`.
That is the live mechanism. **Nothing in the repository says so**, and four things
actively obscure it.

**1. There is no `render.yaml` — and that is the mechanism, not a detail.** A
repo-wide search finds no infrastructure-as-code file of any kind. The service's
type, build command and start command exist **only in the Render dashboard**. So
the choice below is made in a web UI, recorded nowhere, and would change without a
commit, a review, or a trace. Everything else in this entry follows from that.

**2. Two start paths for one service, and both are plausible.**

```
apps/api/Dockerfile:17   CMD ["sh","-c","alembic upgrade head && exec uvicorn …"]
apps/api/Procfile:1      web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

The Procfile has no alembic. Both are valid Render configurations; the dashboard
picks. A service converted from Docker to native Python — to save build minutes,
say — would silently stop applying migrations. There would be **no error and no
crash**: a data-only migration that does not run leaves a healthy service serving
stale rows, which is exactly the shape that took an investigation to rule out on
2026-09-17. `README.md:136` describes the api service as bare `uvicorn`, siding
with the Procfile against the truth.

**3. `IMPLEMENTATION_BACKLOG_v29.md:331` asserts the opposite of the truth.** It
says *"the only `alembic upgrade head` anywhere in the repository is
`conftest.py:212`"*. There are six: `Dockerfile:17`,
`infra/docker-compose.prod.yml:29`, `Makefile:7`, `Makefile:21`, `README.md:51`,
and the conftest. TD-73's argument does not rest on it — it is an aside inside a
point about CI coverage — which is what makes it the dangerous kind: a confident,
checkable sentence in the file that governs how this project reasons about
migrations. **Corrected in place when this entry landed.**

**4. `DEPLOY_NOTES.md` documents no migration mechanism at all.** The file whose
stated purpose is *"manual step[s] that a fresh deploy would otherwise skip"*
mentions migrations exactly once, at `:40`, and only to say *verify* one applied.
It never says what applies them.

**5. `infra/docker-compose.prod.yml` cannot run.** Line 20 requests
`target: production`; `apps/api/Dockerfile` has no multi-stage build and defines no
such target. A reader who reaches for the one artefact named "prod" finds a file
that has never worked and, at `:29-31`, a start command that is not the live one.

**What closing it looks like, in order of value:**

1. **A `render.yaml`** committing the service type and start command to version
   control. Closes item 1 outright and makes items 2 and 5 answerable by reading
   the repo. Render supports it as a Blueprint; adopting one for an existing
   service is the only real work in this entry.
2. **Delete `apps/api/Procfile`**, or add a comment stating it is not the
   production start path. One file, one contradiction, gone.
3. **A `DEPLOY_NOTES.md` section** stating where migrations run, citing
   `Dockerfile:17` and the deploy-log line above as evidence.
4. **Fix or delete `infra/docker-compose.prod.yml`.** It is not used by anything.

None of it changes behaviour. All of it changes what the next person can find out
without an investigation.

### TD-82 — The base-URL fallback is written in three files, and only one is pinned — **NEW**
**Status: OPEN. Not scheduled. Small, and recorded because its failure mode is
silent and already has a precedent.**

**Verified at `a9d01ea7`.** `process.env.NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'`
appears three times: `app/layout.tsx:41` (as `BASE_URL`, feeding metadataBase, the
canonical and the JSON-LD), `app/robots.ts:48`, and `app/sitemap.ts:24`.

Three copies of a FALLBACK STRING, not three hostnames — the deployed value still
comes from one env var, so today they cannot disagree.

**Why it is worth a line anyway.** On a domain change the fallback is what a
partial edit leaves behind, and the safety net is uneven:
`app/__tests__/metadataBase.test.ts:43` pins the literal in `layout.tsx` with a
regex, so that one goes red and gets fixed. **Nothing pins the other two.** The
outcome is a canonical and a JSON-LD naming the new host while `robots.txt` and
`sitemap.xml` still advertise the old one — wrong, silent, and only visible to a
crawler. That is TD-69's family exactly: a hostname that drifted because it lived
in more than one place.

**Not collapsed today, deliberately.** A shared `lib/baseUrl.ts` means a fourth
file and working around the test regex that pins the literal — and Metadata Routes
cannot import from `layout.tsx` without pulling `next/font/google` and
`globals.css` into them. The cost is larger than the risk at one domain.

**The lever, so it is not re-derived:** extend the `metadataBase.test.ts` regex
sweep to `robots.ts` and `sitemap.ts` — assert all three fallbacks are the same
string. That is a test, not a refactor, and it closes the silent half without
touching the code.

### TD-83 — BOTH hydration signals hang on a storage error, and the store field is unreferenced — **NEW**
**Status: OPEN. The immediate hazard is closed in `useAuthGate` by a deadline;
what remains is a dead field and a trap for whoever writes the next guard.**

**Verified at `d769ef3c`**, in the library rather than by reasoning about it.

**The premise this entry was first drafted on was WRONG.** The draft said the
`hasHydrated` STORE FIELD could hang while `persist.hasHydrated()` was the safe
alternative. Both hang. `node_modules/zustand/middleware.js:417-430`:

```ts
}).then(function () {
  postRehydrationCallback(stateFromStorage, undefined)
  _hasHydrated = true                                   // success only
  finishHydrationListeners.forEach(cb => cb(stateFromStorage))
}).catch(function (e) {
  postRehydrationCallback(undefined, e)                 // error: that is all
})
```

On a storage error — private window, blocked site data, a throwing storage — the
catch runs the rehydration callback and stops. `_hasHydrated` is never set and
the finish listeners never fire. So **`persist.hasHydrated()` stays false forever
and `onFinishHydration()` never resolves**, exactly like the field.

**Two problems, and they are not the same problem.**

**1. The persist API is not the safe alternative it looks like.** Any future
guard written as "wait for `persist.hasHydrated()`" hangs on a browser that
cannot read storage: loading state forever, no error, nothing logged. That is the
PR4p class (CLAUDE.md P-04) — a hydration guard that passed review and unit tests
and hung in the production build.

**Closed for the one live consumer, not in general.** `lib/useAuthGate.ts` puts a
`HYDRATION_DEADLINE_MS = 3000` deadline on the wait and decides without hydration
when it fires (the reader goes to sign-in carrying `next=`, which is the correct
answer: a browser that cannot read storage has no session to restore). **Anything
else that waits on hydration needs its own deadline.** There is no shared helper
for that today, and writing one is the real closure of this half.

**2. The `hasHydrated` STORE FIELD has zero consumers and one extra hole.**
`store.ts:23,153-154`, written at `:397-400`. BUG-002 moved `letters/[id]`, its
last reader, onto `useAuthGate`. Beyond the shared hang, its callback **ignores
the error argument entirely**, so it cannot even report the failure it swallows —
`analytics.ts:9-14` records that this field exists BECAUSE of the PR4p
regression, which makes it the scar carrying the same edge that cut.

It is also the one a reader will reach for first: shorter, a plain selector, no
three-step dance, no deadline to remember.

**What to do, cheapest first:**
1. **Delete the field**, `setHasHydrated`, and the `:399` write. Nothing reads
   it. Smallest diff, removes the more misleading of the two signals outright.
2. **A shared `useHydrated(deadlineMs)`** that every future guard uses, so the
   deadline is not something each caller must remember. This is the half that
   actually prevents a recurrence; (1) only removes the worse option.
3. Leaving a warning comment is the weakest answer — the 2026-08-18 lesson is
   that a rule living only in a comment is one rotation from not existing.

**Deliberately not folded into BUG-002's PR.** That PR removes the last consumer
and closes the hazard where it was live; deleting the field is a separate change
to a file 40 components import, and (2) is a new abstraction that wants its own
review.


### TD-84 — Two modals trap Tab and never hand focus back, and neither has a test — **NEW**
**Status: OPEN. Deliberately not fixed in the BUG-017 PR that found it.**

**Verified at `afc91451`**, by reading both files rather than by reasoning from the
one that was being changed.

BUG-017 gave `BottomSheet` a focus trap and focus RETURN. The trap was modelled on
two that already existed. Reading them to copy the shape showed both are missing the
same half the sheet was missing:

| | trap | initial focus | focus RETURN | test |
|---|---|---|---|---|
| `ui/DeleteConfirmModal.tsx` | `:48-74` | `:79` | **none** | `__tests__/DeleteConfirmModal.test.tsx` — **0** focus assertions |
| `share/SharePreviewModal.tsx` | `:155-178` | `:182` | **none** | **no test file at all** |

Neither captures `document.activeElement` on open, so neither has anything to return
focus TO. Both move focus into themselves and then, on close, leave it wherever the
removed node used to be — which the browser resolves to `<body>`. A keyboard reader
who dismisses either one resumes tabbing from the top of the document, and nothing
announces that the dialog closed. On `DeleteConfirmModal` that is the end of a
destructive confirmation; on `SharePreviewModal` it is the end of a share flow the
reader will plausibly repeat on the next line.

**Both traps also only wrap at the two boundaries.** Focus that is already OUTSIDE the
panel — after a click on the page behind — is not pulled back, so Tab walks the
document under an `aria-modal` dialog. `BottomSheet` now has a third branch for this
(`BottomSheet.tsx:59-64`); the two modals do not.

**Why this is its own PR.** Three reasons, and the third is the real one:
1. `SharePreviewModal` has no test file, so fixing it means writing the harness first.
2. `DeleteConfirmModal` is the confirmation in front of **account deletion**, the one
   irreversible action in the product (`:16-19`). A focus change there is not a
   cosmetic change.
3. The BUG-017 PR is already three defects across three files with two locked copy
   decisions. Folding in a fourth would make the smoke test that gates it ambiguous
   about what it cleared.

**What to do:** lift the `BottomSheet` implementation rather than write a third copy
of it — capture-on-open, `isConnected`-guarded restore on close, and the
outside-the-panel branch — into a shared hook both modals and the sheet call. There
are now **three** hand-rolled traps in this codebase and the third one is the first
with a test (`ui/__tests__/BottomSheet.test.tsx`); a fourth should not be written.

**What a test can and cannot assert here** is settled and need not be re-litigated:
jsdom does not move focus on Tab and `@testing-library/user-event` is not a dependency
of this app, so initial focus, boundary wrapping, the outside-the-panel pull-in,
Escape and focus return are all assertable (they are our own `.focus()` calls), while
native traversal BETWEEN the boundaries is the browser's and belongs on a preview
deploy. `ui/__tests__/BottomSheet.test.tsx` is the worked example.


### TD-85 — "Today's question" points at nothing, and the object it names has two names — **NEW**
**Status: OPEN. Two halves; whoever fixes one should settle the other.**

**Verified at `afc91451`**, against the code and against the production table.

**Half one — the pointer is stale.** `app/(tabs)/today/page.tsx:248` renders:

> Conversations live here once you've started. Begin with today's question above, or
> choose a mind.

Nothing above it renders a question. The element it refers to is an `ImageTile`
labelled **"Discussion"** (`:194-199`) which routes to `/app/discuss`. A reader who
follows the instruction literally looks for a question on the Today tab and does not
find one.

**Half two — the object has two names, and the older one is wrong about the data.**
The same file calls it a *question* again at `:257` (`label: "Answer today's
question"`, an `aria-label`). The component that actually renders it is called
`TodaysTopicCard`, and BUG-023 gave it a visible eyebrow reading **TODAY'S TOPIC**.

The measurement that settled which name is right, taken against production
`daily_questions` on 2026-09-17:

- **80 rows, 50 active.**
- **All 50** active rows carry an em-dash and have the shape `Title — subtitle`.
- Of the 50 title halves, **48 are statements and 2 are questions.** Average title
  33 chars, longest 49.

So "question" is wrong about the live data in 96% of cases. "Topic" is right, which is
why BUG-023 locked it. That leaves `today/page.tsx` as the last place using the older
name — and it is also the place where the name sits inside a sentence that is already
broken for an unrelated reason.

Note that migration `010_daily_questions` seeds **30 rows with no em-dash at all**,
which is a different corpus from the 50 that are active. Reading the migration alone
would tell a reader the split in `TodaysTopicCard` is dead code. It is not; it is
load-bearing in production. (See also TD-73 — production is not reconstructible from
migrations alone. This is another instance of it.)

**Why this is not in the BUG-023 PR.** Fixing the pointer needs new copy for that
sentence, and new copy needs a lock — a fourth stop inside a PR that already had
three. The naming half should be settled in the same change, since renaming one site
while the other keeps the old word is how an object ends up with two names in the
first place.


### TD-86 — On the web side, "CI green" means the build compiled — **NEW**
**Status: OPEN, but only on its LAST step. Branch protection READ 2026-09-18 —
`Web build` is not a required check, so the frontend has no gate at all.**

**PROGRESS 2026-09-18.** Steps 1, 2 and 3 of the sequence below are done:
- **Step 1 — `paths:` filters stripped** from `web-build.yml`. Every PR now produces
  a web run, so "no run" can no longer be mistaken for green.
- **Step 2 — the 13 failures are fixed.** Six stale-test causes, plus a seventh that
  only became reachable once the sixth was repaired (jsdom does not implement
  `scrollIntoView`). The suite is **478 passing across 60 files**, green for the
  first time in the project's history. Zero product bugs among the 13, as the
  2026-08-13 measurement predicted.
- **Step 3 — `continue-on-error` removed from the Tests step.** A failing web test
  now fails the job.
- Also: **8 of the 12 typecheck errors fixed** (fixtures behind widened types). The
  remaining 4 are production code — 3 are TD-87, 1 is a narrowing limitation in
  `oauth/finish` that the runtime cannot reach. Typecheck stays report-only until
  TD-87 is ruled on.
  **The four, by their error TEXT, so a reader who sees them in a run can match them
  here without opening the files:** three are `'user' is possibly 'null'`
  (`(tabs)/account/page.tsx`, TD-87) and one is
  `Type 'string | null' is not assignable to type 'string'` (`auth/oauth/finish`).
  They appear on EVERY web run and the job still reports success — that is the
  `continue-on-error: true` on the Typecheck step, not a flake. Re-confirmed
  2026-09-22 from a founder-reported run: no new TD, it is the same four.

**WHAT REMAINS IS NOT A COMMIT.** `Web build` must be added to `main`'s required
checks in **Settings -> Branches**, alongside the three that are there now. That is a
setting, not a file, so it cannot be in a PR — and until it changes, a red Tests step
is a visible X that stops nothing. It is safe to do now and was not before, because
step 1 removed the filters that would otherwise leave every backend-only PR at
*Expected — waiting for status to be reported* forever.

**Verified at `afc91451`** by reading `.github/workflows/web-build.yml` and by running
both reporting steps locally, not by inferring from a check mark.

`web-build.yml` runs three steps. **Two of them cannot fail the job:**

| step | line | blocks a merge? |
|---|---|---|
| Typecheck (`npm run typecheck`) | `:44-46` | **no** — `continue-on-error: true` |
| Tests (`npm test -- run`) | `:48-50` | **no** — `continue-on-error: true` |
| Build (`npm run build`) | `:52-53` | yes, it is the only one |

And the surviving step validates less than its name suggests: `next.config.js` sets
`typescript.ignoreBuildErrors` and `eslint.ignoreDuringBuilds`, so `npm run build`
checks that the app **compiles**, not that it typechecks, lints or passes its tests.

**None of this is a mistake.** `:40-43` says so in as many words — the two steps are
"measurement only", and `continue-on-error` is "deliberate: a red X here must never
block a merge until we decide to enforce". The decision was made and written down.
This entry is not a claim that it was wrong.

**What is missing is the rest of the sentence.** "Measurement only" is a statement
about the workflow. It is not visible to someone looking at a PR, where the job
reports the same green check whether the suite passed or 13 tests failed inside it.
The 2026-09-01 entry in CLAUDE.md is about a green merge button being read as a green
build; this is the same shape one level in — a green *job* read as a green *suite*.

**What is actually red right now, measured at `afc91451` with this session's work
stashed:**

- **13 test failures across 6 files** — `QuickActionsRow` (2), `DateGrouper` (2),
  `EmptyReflections` (4), `FilterPills` (1), `SavedLineCard` (1),
  `app/app/chat/conv/[id]` (3). 460 pass.
- **12 typecheck errors across 6 files** — `(tabs)/account/page.tsx` (3),
  `auth/oauth/finish/page.tsx` (1), `MessageBubble.test.tsx` (5),
  `ConversationCard.test.tsx` (1), `ConversationList.test.tsx` (1),
  `councilInsightDoor.test.tsx` (1).

Neither number is new and neither was introduced by the Batch E PR — both were
measured on a clean checkout of `afc91451` for exactly that reason.

**How much merged over it.** On **2026-09-17**, eight PRs landed on `main`
(#669-#676). Four touched `apps/web/`:

| PR | web files |
|---|---|
| #670 Feat/paywall surface batch b | 28 |
| #672 Feat/counterview go deeper retry | 3 |
| #675 Feat/seo foundations | 6 |
| #676 Feat/auth hydration gate | 35 |

72 web files across four PRs, each merged under a web job that could only have gone
red if the app failed to compile. The other four produced **no web run at all** —
`web-build.yml` still carries the `paths:` filters (`:6-8` on push, `:10-12` on pull_request) that were removed
from `backend-ci.yml` on 2026-09-14, so a backend-only or docs-only PR shows no web
check whatsoever. That is the 2026-09-01 "**no run is not green**" trap, still live on
this workflow.

**MEASURED 2026-09-18** — founder read Settings -> Branches -> the `main` rule
directly. This paragraph previously carried an *unverified* marker; the marker is
dropped and replaced by the reading. **Require status checks to pass: ON. Require
branches to be up to date: ON. Three checks are required, all GitHub Actions:**

1. `C-04 migration naming`
2. `pytest (baseline) + alembic single head`
3. `pytest (live Postgres)`

**`Web build` is not among them.** The unverified line resolved to the worse of its
two possible answers.

**So: the backend is gated and the frontend is not.** Stated plainly because the
distinction is invisible from a PR page, where both halves of the repo show the same
row of green checks. There are three layers on the web side and a change passes
through all three without being stopped by any:

| layer | why it does not stop anything |
|---|---|
| tests | `continue-on-error: true` (`:50`) — reports, cannot fail the job |
| typecheck | `continue-on-error: true` (`:46`) — same |
| the job itself | `Web build` is not a required check, so even a compile failure is only a visible X |

and the one step that can fail the job validates neither types nor lint, because
`next.config.js` sets `typescript.ignoreBuildErrors` and `eslint.ignoreDuringBuilds`.

**72 web files across four PRs merged on 2026-09-17 through none of these.** Four more
produced no web run at all.

**No fix is proposed here, deliberately.** Making `Web build` required *today* would
recreate the 2026-09-14 trap from the other side: `web-build.yml` still carries its
`paths:` filters, so every backend-only or docs-only PR would produce no web run, and a
required check that never reports sits at *Expected — waiting for status to be
reported* forever — the merge button never opens. That is the exact failure the
2026-09-14 entry describes, arrived at by doing the apparently responsible thing.

**The order, which is a sequence and not a change, and which needs its own brief:**
1. **Strip the `paths:` filters** (`:6-8`, `:10-12`) so the workflow always reports. Safe
   while it is not required, and it is the precondition for anything after it. This is
   what `backend-ci.yml` had done to it on 2026-09-14, for this reason.
2. **Diagnose the 13 failures** — diagnose, not repair-to-green. Per the TD-45 lesson a
   carried explanation for a failing test is a doc claim like any other, and repairing
   to the error message is how one fixture produced three consecutive red runs.
3. **Then make it required**, and drop `continue-on-error` from the tests step.
   Typecheck can stay reporting-only longer; the suite is the half that encodes
   behaviour.

Enforcing before (1) and (2) does not close the gap — it moves the blockage in front of
every web PR, including the ones that have nothing to do with the 13.


### TD-87 — The Account page dereferences a nullable `user` behind a guard on something else — **NEW**
**Status: OPEN. HELD OUT of the TD-86 CI branch deliberately — it is the one item in
that set needing a product decision rather than an edit.**

**Verified at `74f576d5`** by reading the file, not by trusting the type error.

`app/app/(tabs)/account/page.tsx` renders the signed-in reader's name and email:

```tsx
:28    const user = useStore((s) => s.user)
...
:60    const displayName = user?.full_name ?? user?.email ?? ''     // optional chaining
...
:162   if (!authed) {
         return <div className="min-h-screen [min-height:100svh] bg-vellum" />
       }
...
:187   {user.full_name && (                                         // bare
:189      {user.full_name}
:192   <p className="font-lora text-[14px] text-charcoal">{user.email}</p>
```

**The guard at `:162` is on `authed`, not on `user`.** `authed` comes from
`useAuthGate`, which answers "is there a usable session", and it is not a claim that
the `user` object has loaded. Three lines then dereference `user` bare. If `authed` is
ever true while `user` is null, the Account page throws and the reader gets a blank
screen on the one page that holds cancellation, data export and account deletion.

**The same file already knows this.** `:60` reaches the same object through `?.`
twice. So the nullability is real and understood 127 lines above the place it is
ignored — which is the signature of a guard that was correct when written and a
render block that grew past it.

**Honest about what is NOT established: no reachable path was constructed.** `token`
and `user` live in the same persisted store blob and hydrate together, so the obvious
candidate — a session restored without a profile — does not obviously occur. This is
recorded as a **latent** defect, not a demonstrated one. It was found by the
typechecker (TS18047 ×3), which is exactly the class of thing a typechecker is for and
exactly the class that `next.config.js`'s `typescript.ignoreBuildErrors` has been
hiding. It has been in the file at least since the 2026-08-13 measurement, where it
appears at the same three lines under their older numbers (`:112`, `:114`, `:117`).

**THE QUESTION, which is the founder's and is why this is not a code change:**

*Guard it and render WHAT?*

The three candidate answers are not equivalent, and the difference is visible to a
person:

1. **`?.` everywhere**, matching `:60`. Smallest diff. The page renders with an empty
   name and an empty email — a signed-in reader looking at a blank identity block on
   their own account page, with the destructive actions below it still live.
2. **An early return** next to the `authed` one, rendering the same silent placeholder.
   The page shows nothing at all until the profile is present. Honest, and it delays
   access to export and deletion for a state nobody has yet seen occur.
3. **Treat `authed && !user` as a broken session** and route to sign-in carrying
   `next=`, the way `useAuthGate` treats a failed hydration (per TD-83). Strongest and
   most opinionated: it says a session with no profile is not a session.

There is also a prior question worth answering first, because it may collapse the
other three: **can `authed` be true while `user` is null at all?** If the store
guarantees they arrive together, the right change is to make the type say so and
delete the nullability, not to guard it. That is a reading of `lib/store.ts` and
`lib/useAuthGate.ts`, not a judgement call — but it is the founder's call whether to
spend the reading before the ruling.

**Why it is not in the CI branch.** That branch strips the `paths:` filters, fixes 13
test failures across six causes, fixes 8 test-side type errors and makes the suite
gate. Every one of those is mechanical and reversible. This is a product behaviour
change on the page that holds account deletion, and it would have been the only thing
in the PR that could not be reviewed by reading a diff.

**It does not block the CI sequence.** The typecheck step stays `continue-on-error`
until this is ruled on; the tests step gates now regardless. Closing this and the
one remaining `oauth/finish` error — a narrowing limitation, not a defect, since the
`if (!token)` guard returns before the call — is what would let typecheck gate too.

---

### TD-88 — `Spinner.tsx` has zero consumers and a docstring naming three that do not exist — **NEW**
**Status: OPEN. The question is delete-or-adopt, and this entry deliberately does not
answer it.**

**Verified at `9ad352fb`**, found while investigating BUG-008 for an existing loading
visual to reuse.

`apps/web/components/ui/Spinner.tsx` is a complete, working component. Its docstring
says:

```
 * Spinner per DESIGN_SYSTEM_v4 A1 spec.
 * Edge ring (0.8px stroke) + Ink rotating arc (1.2px stroke), 1.4s rotation.
 * Used in: A1 splash, C1 chat sending state, H2 checkout loading bridge.
```

**It is used in none of them.** `grep -rn "Spinner" apps/web --include=*.tsx
--include=*.ts`, excluding the file itself, returns **zero** matches. Nothing imports
it, so none of the three named call sites can be real.

This is the 2026-08-18 shape exactly: **a doc claim that outlived the thing it
described.** The difference from the usual case is the direction — the claim is
inside the artefact it is wrong about, and it is wrong in the flattering direction,
asserting adoption that never happened. A reader grepping for "how do we show
loading" finds this file, reads three call sites, and concludes the question is
settled.

**What is true about it:**
- The component works. `animate-spin-slow` is defined (`tailwind.config.js:63`,
  `'spin 1.4s linear infinite'`), matching the 1.4s the docstring and
  `DESIGN_SYSTEM_v4:1239` both specify.
- It is the **only** loading visual in the codebase with an accessibility contract:
  `role="status"` and `aria-label="Loading"`. Neither competing idiom has either.
- It is stroked in `var(--edge)` / `var(--ink)`, so it is theme-correct.

**What competes with it, and won:**

| Idiom | Reach |
|---|---|
| `animate-pulse` skeleton blocks | **30 sites across 6 files** — self-portrait, council, letters, letters/[id], mirror, profile, and now today + quotes via BUG-008 |
| literal `Loading…` italic text | 13 sites |
| `Spinner.tsx` | **0** |

**BUG-008 did not adopt it, deliberately.** The two blank loading branches it filled
use `animate-pulse`, because that is the established idiom and matching six existing
files beat introducing a seventh pattern in a PR about navigation feedback. That
decision is not a ruling on this entry — it is the reason this entry exists.

**The evidence that cuts the other way, and is why this is not simply a deletion.**
`DESIGN_SYSTEM_v4:210` still specifies, for the chat composer:

> **Sending**: Ink bg, Vellum spinner (border arc rotating, 1.4s duration)

**That state currently has no loading affordance at all.** `ChatInput.tsx:48-50`
renders `disabled={disabled || !value.trim()}` with `disabled:opacity-40` — a dimmed
button, no spinner, no rotation. So the component may be **unadopted rather than
obsolete**: a thing built to spec, for a spec still on the books, that nobody wired
up. Deleting it would close the gap by removing the answer rather than the question.

Note also that the three screen codes in the docstring — `A1`, `C1`, `H2` — do not
appear in the current `SCREENS_TRACKING_v14`. The docstring is pinned to a
vocabulary the tracking documents have moved past, which makes it hard to tell
whether "A1 splash" still denotes anything.

**THE QUESTION, which is the founder's:**

**Delete it, or adopt it?**

- **Delete** — the app has settled on skeletons, a spinner is a different visual
  grammar (indeterminate, centred, attention-taking) from a skeleton (positional,
  calm, shape-preserving), and one unused file with a false docstring is worse than
  no file. The `DESIGN_SYSTEM_v4` spinner spec would be amended to say skeletons, and
  the chat Sending state would get a skeleton or keep the dimmed button.
- **Adopt** — wire it into the chat Sending state it was built for, which today has
  nothing, and keep it for the genuinely indeterminate cases where a skeleton lies
  about shape. Its `role="status"` would then be the app's first accessible loading
  announcement.

**Whichever is chosen, the docstring is wrong today and should not survive the
ruling.** If it is adopted, the three call sites become one real one. If it is
deleted, the claim goes with it. The thing that must not happen is a third rotation
in which it still says "Used in:" and still is not.

---

### TD-89 — `Conversation.deleted_at` is read by three queries, written by none, and missed by a fourth — **NEW**
**Status: OPEN. Record only — no fix, and nothing is broken today.**

**Verified at `b9041692`**, found while establishing whether the Mirror empty state
could derive eligibility client-side (BUG-021 residue). It cannot, and this is why.

**Two halves of one confusion about whether conversations are soft-deleted.**

**Half one — three queries filter it, a fourth does not.**

| Query | Filters `deleted_at`? |
|---|---|
| `routers/home.py:40` | yes |
| `services/conversation_service.py:410` | yes |
| `workers/cron.py:290` (preview-mirror eligibility) | yes |
| **`routers/conversations.py:298-313`** (`GET /conversations`, the Library list) | **no** |

**Half two — nothing ever sets it.** `DELETE /conversations/{id}` at
`routers/conversations.py:822-834` ends in `await db.delete(conv)` — a **hard**
delete. A repository-wide search for a writer of `Conversation.deleted_at` returns
only migrations. The column, its partial indexes (`models/__init__.py:240`) and the
three filters all guard a state the application cannot produce.

And migration `009_saved_lines.py:9` states the opposite as fact:

> "…hard-deleted in this codebase — only conversations.deleted_at soft-delete"

That is a doc claim contradicted by the code it describes, which is the 2026-08-18
shape again.

**Why it is harmless today and why that is the problem.** Because nothing writes the
column, the missing filter in the Library list changes no behaviour: there are no
soft-deleted rows to leak. The defect is latent and **inverted** — it will appear on
the day someone implements soft-delete, in a query nobody will think to revisit,
showing deleted conversations back to the reader who deleted them.

**How it nearly caused a second bug, which is why it is written down now.** The
BUG-021 investigation asked whether the Mirror empty state could tell an eligible
reader from an ineligible one. The preview threshold — `>=3` conversations with
`last_message_at` inside 72h — looked exactly reproducible on the client from
`getConversations()`. It is not: the cron filters `deleted_at IS NULL` and the list
endpoint does not. The two agree **only by the coincidence** that the column is never
written. A derivation built on that would be correct until soft-delete landed and
would then silently tell readers they qualify when they do not. The mirror page now
carries that reasoning in a comment at the point of temptation, rather than only in
this entry.

**THE QUESTION, unresolved deliberately: is soft-delete intended or abandoned?**

- **Intended** — then `DELETE /conversations/{id}` is the defect (it hard-deletes
  where the schema, the indexes and three queries all expect a tombstone), and
  `list_conversations` needs the filter before that changes.
- **Abandoned** — then the column, both partial indexes, the three filters and
  migration 009's docstring are all describing a design that was dropped, and the
  honest change is to remove them.

Either way `list_conversations` and migration 009's docstring are wrong about the
other three. Nothing here is urgent; what is not acceptable is a third rotation in
which the codebase still holds both answers at once.

**Not in scope of the PR that found it** (BUG-024 + BUG-021 residue), which touches
the quotes carousel and one paragraph of mirror copy. This is a backend schema
question and belongs to whoever answers it.

---

### TD-90 — Epictetus carries the Encheiridion twice, in two translations — **NEW**
**Status: OPEN. Accepted cost, not a defect. Founder ruling 2026-09-18.**

**Created deliberately by the P0 corpus re-ingest**, as the price of not
mislabelling anything. Recorded here because it is a known trade rather than an
oversight, and because the fix belongs somewhere this PR does not touch.

**The situation.** Gutenberg has **no complete English Discourses**. The only
real Discourses text is `pg10661`, George Long's *A Selection from the Discourses
of Epictetus with the Encheiridion* — which, as its title says, also carries the
Encheiridion. Epictetus's other source is `pg45109`, Higginson's standalone
*Enchiridion*. So the Encheiridion is in the corpus twice.

**Measured, not assumed** (fetched 2026-09-18): `pg10661`'s body is 5,345 lines,
of which the section `THE ENCHEIRIDION, OR MANUAL.` (line 4,542 to the end) is
832 — **16%**. At 174 chunks for the file, roughly **27 chunks are Long's
Encheiridion**, duplicating the **38 chunks** of Higginson's. About 12% of the
persona's 212 chunks are a second translation of text already present.

**Why it was accepted.** The alternatives both lie:
- file `pg10661` alone under the title "Discourses of Epictetus" — which puts
  Encheiridion text under the Discourses' name, the exact defect this phase exists
  to fix;
- drop `pg45109` — same problem, and loses Higginson entirely.

Truthfulness over retrieval tidiness. The source is titled *"Discourses of
Epictetus (selections)"* precisely because it is a selection.

**What it can actually do.** `retrieval_service.retrieve` (`:31-44`) selects by
`persona_slug` only — there is **no dedup and no source filter** — and Epictetus
has `retrieval_top_k=4` (`personas/epictetus.py:66`). A question about what is in
our control can therefore return near-identical passages twice, spending two of
four slots on one idea, and the model can attribute it to two different sources in
one reply. Ceiling on the harm: a thinner answer, never a wrong attribution. Both
passages are genuinely Epictetus and genuinely under the title they claim.

**And there is no switch to turn it off.** `retrieval_sources` is declared on every
persona (`personas/epictetus.py:60`) and **read by nothing** — the retrieval SQL
never mentions `source_title`. So this cannot be mitigated by configuration today;
it needs code.

**The fix is dedup in retrieval, not a trimmed corpus.** Deleting Long's
Encheiridion section from the ingested text would mean the stored chunks no longer
match the file the config points at, which breaks the invariant the same PR just
spent its whole diff establishing. A near-duplicate filter at retrieval time (or
a cosine-similarity cutoff between returned passages) solves it without lying
about provenance.

**Not in scope of the PR that created it**, which fixes attribution and adds the
header guard. Whoever picks this up should also decide what `retrieval_sources` is
for, since it is currently decoration.

---

---

### TD-107 — the `must_not_say` lists of two critical promises are not enforced — **OPEN, DEFERRED**
**Status: OPEN, deferred by ruling (2026-09-24): "guard text first, mechanism later if
the smoke shows text alone is not enough."**

Two of the seven approved critical promises carry an explicit `must_not_say` list in
`philosopher_brain/personas/marcus_aurelius.yaml`:
- **#4, self-harm or suicidal ideation:** "endure", "remain strong", "this too is
  outside your control", "death is natural", "life is opinion", "what is yours to
  govern".
- **#6, active grief:** "I too lost...", "As one who lost children...", "Grief is only
  judgment", "This is outside your control".

The guard PR puts these situations into Marcus's prompt as text. Nothing CHECKS the
output for them: SAFETY-001 found none of the ten in
`forbidden_lexicon_persona_specific`, the one mechanism that could. Adding them there
would make postprocessing regenerate a reply that says one — but the lexicon is
situation-blind, and "endure" or "remain strong" are ordinary Stoic words in every
other conversation, so a blanket ban would cost the voice everywhere to protect it
in two situations. That trade-off is why this is a decision and not a follow-up.

**Revisit when:** the P-04 smoke for the Marcus guards shows the text alone does not
keep these phrases out.

---

### TD-109 — the persona opening renders two ways for the same conversation — **OPEN, target ruled**
**Status: OPEN. No fix now. TARGET RULED 2026-09-24: the bare italic is correct
everywhere for the persona `opening_invocation` — the opening is a greeting, not a
turn. RITUAL PROMPTS ARE TURNS, NOT GREETINGS (ruled the same day): the user answers
them, so they keep the bubble. The ruling covers `opening_invocation` only.**

**What happens.** One static line, `PersonaConfig.opening_invocation`, reaches the screen
two ways, and the ENTRY ROUTE alone decides which (not persona, plan or device —
checked 2026-09-24):

- **`/app/chat/[slug]`** (fresh persona open): the page never loads history. It renders
  `conv.persona.opening_invocation` from the create response as `<OpeningInvocation>` —
  centred italic, no bubble.
- **`/app/chat/conv/[id]`** (return, reload, resumed thread, any link): the page loads
  messages, and the opening is a stored assistant row
  (`conversation_service.create_or_resume`, `:549`; backfilled for a reused empty
  conversation at `:520`), so it renders as an ordinary assistant bubble. The italic
  fallback there fires only when the thread has zero messages.

So the same conversation is italic on first open and a bubble on every return. Seen on
Musashi and Marcus on the QA account, 2026-09-24.

**The stored row is also why `model_used` is NULL on openings** — it is inserted with
`Message(...)` directly, not `_save_message`, and no model wrote it. That is correct.

**Production, 2026-09-24:** 194 conversations with messages; **150 start with an assistant
row** — 115 match the persona's stored opening text, 4 are ritual prompts, 31 match
neither (not investigated; likely older opening texts). **6 saved lines point at an
opening row** (users saved the greeting). 0 safety events do.

**Candidate fix A — render the stored row as the italic header on the conversation page.**
Keep storing it; the conversation page recognises the opening row and renders it as
`<OpeningInvocation>` instead of a bubble.
- **Recognising it is the hard part.** Nothing marks the row: `message_kind='standard'`,
  `persona_id=NULL`, like any reply. "First assistant row before any user row" catches
  it, but also catches the **4 ritual prompts** — which `routers/rituals.py:75` writes
  by OVERWRITING the opening row with a personalised prompt the user answers. Whether a
  ritual prompt is a greeting or a turn is not covered by the ruling. Matching on the
  persona's current text misses the 31 rows that no longer match. A new marker
  (e.g. `message_kind='opening'`) is the reliable route: a migration plus a backfill.
- **Saved lines:** the 6 existing ones survive; the save action disappears from a
  rendered header, so no new ones can be made.
- **Untouched:** the W3 strip (the row stays and is still dropped from model history),
  the data export (the row is still a message), `create_or_resume`'s backfill.

**Candidate fix B — stop storing the row; the opening is presentation only.**
`create_or_resume` stops inserting it; both pages render the header from
`persona.opening_invocation`.
- **The W3 strip** — `while lm_messages[0]["role"] == "assistant": pop` at
  `conversation_service.py:905`, `:1466`, `:1782` — exists because the opening row is an
  assistant turn with no user turn before it (the API requires user-first). With no row
  it strips nothing for new conversations but must stay for the 150 existing ones and
  for rituals. **Its comment at `:902` is already stale in one respect:** it names
  "cross-persona bootstrap" as a second source, but `:571` says no bootstrap message is
  created.
- **Rituals break outright:** `rituals.py:75` finds the first assistant row and
  overwrites it with the ritual prompt. With no opening row there is nothing to
  overwrite; the ritual path would have to insert its own row.
- **`create_or_resume`'s dedup/backfill** (`:497-533`) reasons about "a row that could
  already have an opening message even though message_count == 0" and inserts a
  missing one — that logic is removed or rewritten.
- **The existing 150 rows stay** unless deleted, so the conversation page still needs
  A's recognition for history. **Deleting them cascades:** `SavedLine.message_id` is
  `ON DELETE CASCADE`, so the 6 saved greetings would be destroyed — the C-07 class of
  problem.
- **Tests:** `tests/services/test_conversation_service.py`, `tests/test_conversations.py`
  and `tests/test_personas.py` all reference `opening_invocation`.

**B alone does not reach the ruled target for existing conversations** — history still
holds 150 rows. Either way, the conversation page needs a rule for the rows that already
exist.

**The ritual ruling decides between them.** Ritual prompts keep the bubble and persona
openings become the italic header, so any fix must tell the two apart. A
"first assistant row before any user row" rule cannot — `rituals.py:75` writes the
ritual prompt INTO the opening row, so both occupy the same position. **That is an
argument for Fix A with an explicit marker** (e.g. `message_kind='opening'`, set at
insert and backfilled for the 115 matching rows, with rituals left `standard`), not for
a positional rule. The 31 rows that match neither the current opening text nor a ritual
still need classifying before any backfill.

---

### TD-106 — three live personas have no safety promises authored — **OPEN DECISION**
**Status: OPEN — a decision, not a defect to fix in the guard PR (founder ruling
2026-09-24: "not something to improvise").**

**What it is.** The persona guards are drawn from the `safety` blocks in
`philosopher_brain/personas/*.yaml`. Nine yaml files exist; eight are live personas
(the ninth is Nietzsche, not in `PERSONA_REGISTRY`). **Lao Tzu, Oscar Wilde and
Niccolò Machiavelli have no yaml at all** — no safety promise was ever authored for
them, critical or otherwise.

**Two of them are in the smoke set.** Of the ten disclosures pinned in
`tests/test_safety_detection_gaps.py` — all of which clear the safety gate at
`level="none"`, so the persona answers and nothing intercepts — one targets
**lao_tzu** (a threat, and fear of going home) and one **oscar_wilde** (public
humiliation after a marriage ended). For those two situations the guard PR will have
nothing to put in the path.

**What deciding it needs:** authored promises for the three, in the same shape as the
other eight — the founder's content, not an engineering one. Until then they run with
the shared `system_base.jinja2` steer only ("You are not a therapist… You do not
diagnose"), which is a steer, not a guard.
### COUNCIL-V2 — verdict memory — **CLOSED-with-trigger**
**Status: CLOSED-with-trigger (founder ruling 2026-09-24). Reopens when
`users_with_more_than_one_non_admin >= 10` — the query is `RUNBOOK_LOOP_METRICS.md`
§9, executed by CI out of the markdown.**

**What is and is not deferred.** Council already reads memory at the synthesis step
(`council_service.py:406`, #598); the four members take `memories=[]` by design
(`:305`, pinned by `test_council_synthesis_memory.py`). What Council lacks is memory
of **its own prior verdicts** — deferred to post-beta on 2026-09-15. This entry gives
that deferral the threshold it did not have, so it stops being an open question.

**At the ruling:** 7 users, 3 with more than one council, **2 of them admin accounts**
— so the trigger, which reads non-admins only ("staff traffic is not signal"), stood
at **1**. 56 cases, 0 ever reused. If built, the synthesis step is the only
admissible injection point (HANDOFF_BRIEF_v30).

---

### TD-105 — thin theme coverage in the approved bridge map concentrates best fit — **OPEN**
**Status: OPEN. Logged 2026-09-24 (founder ruling): a finding about the LOCKED map,
not a defect in the TD-104 scoring. Do not touch the map without a ruling.**

**What it is.** Since TD-104, best-fit themes are scored as share-of-achievable: how
far the chosen pills went toward a theme, against how far they could have. A theme
backed by few questions reaches a high share from one or two strong answers. In the
approved `SELF_PORTRAIT_TAG_TO_THEME` map, `controversy` is fed by ONE tag (`power`),
and in the free 15 only **3 questions** can put weight on it (`dilemma`: 1, `work`: 2).

**Measured 2026-09-24, 2,000 random completions of the free 15, per need_most:**

| need_most | distinct pairs | most common pair | most present personas |
|---|---|---|---|
| challenge | 35 | machiavelli + socrates, 16.7% | **machiavelli 62%**, socrates 55%, musashi 25% |
| practical_steadiness | 15 | epictetus + marcus_aurelius, 39.7% | marcus_aurelius 73%, epictetus 71%, machiavelli 43% |
| comfort | 12 | lao_tzu + simone_de_beauvoir, 44.5% | lao_tzu 93%, beauvoir 61%, freud 22% |
| interpretation | 8 | beauvoir + carl_jung, 44.1% | jung 87%, beauvoir 84%, freud 28% |

Questions (of the free 15 / of all 360) that can put weight on each theme:
doubt 8/172 · purpose 6/157 · freedom 5/177 · anxiety 4/75 · grief 4/80 ·
separation 4/59 · acceptance 3/69 · **controversy 3/44** · relationships 3/58 ·
fear 3/107 · work 2/80 · **dilemma 1/38**.

**Two effects, not one.** Machiavelli under `challenge` is the thin-coverage effect.
The single-persona dominance under `comfort` and `interpretation` is a different one:
`compute_matches` counts need_most at twice a theme, so the need picks most of the
pair whoever answered what. Both are recorded; neither is proposed on.

---

### TD-104 — best-fit philosophers never read the chosen answer — **CLOSED**
**Status: CLOSED 2026-09-24 (founder ruling: read the chosen option, with the same
per-answer weights the radar uses; no third scoring system).**

**What it was.** `themes_from_answers` counted the tags of the answered QUESTIONS and
never read the answer, so the three matching themes — and the two best-fit
philosophers `compute_matches` picks from them — depended only on which questions were
answered. Named in the 2026-08-25 teardown alongside the radar; the radar was fixed
(`pill_weights`, #607 / #612–#614) and this path was not, and it had no backlog entry.
Measured: **2,000 random completions of the free 15 → 1 theme set, 1 pair
(Socrates + Orwell) for everyone.** All 3 `ready` portraits in production carried
exactly that pair.

**What changed.** Themes are scored from the chosen pills' `pill_weights` through the
locked bridge map, as share-of-achievable (the radar's semantics), ranked by share,
then raw weight, then name. Raw weight sums were measured and rejected (72.6% still
Socrates + Orwell). After: **592 theme sets, 35 pairs, top pair 16.7%** under
`challenge`. `PORTRAIT_SCORING_VERSION` is part of `answers_fingerprint`, so every
portrait cached under the old rule regenerates once on its next open.

**Also follows, intended:** the Today quote nudge (`quote_suggest.candidate_themes`)
reads the same function — one definition of the person's themes, so it now follows
the answers too. Radar, question bank, summary prompt, free/Pro split and the bridge
map untouched. The concentration this exposes is TD-105.

---

### TD-103 — `loadingSkeletons.test.tsx` intermittently leaks unhandled rejections — **NEW**
**Status: OPEN. Blocks nothing today — web tests run under `continue-on-error: true`
(TD-86) — and makes the web suite's exit code unreadable, which is the cost.**

**What happens.** A full `vitest run` sometimes ends *"Vitest caught 3 unhandled
errors"* — `Error: Not authenticated` from `ApiClient.request` (`lib/api.ts:777`),
reached from `load()` in `app/app/(tabs)/today/page.tsx`, attributed to
`app/app/(tabs)/__tests__/loadingSkeletons.test.tsx`. Every test still PASSES; the
run exits 1.

**Measured 2026-09-24, while verifying TD-101:**
- **main** (`66618821`), full suite: **1 of 3 runs** hit it.
- **the TD-101 branch**, full suite: **5 of 5 runs** — 3 with the new
  `guestPathSafety.test.tsx`, 2 with it moved aside (so not caused by that file).
- **the file run alone**: clean on main and on the branch (3 runs).
- Neither `loadingSkeletons.test.tsx` nor the Today page imports `useStream`, the only
  web file the branch changed. The higher rate on the branch is unexplained; it is
  consistent with a timing-dependent failure and was not investigated further.

**Cause.** Today's `load()` wraps `api.getLastConversation()` in `try/finally` with no
`catch`, and the test mocks the auth gate and sets a token but does **not** mock
`api` — so a real request is made and rejects, and nothing handles the rejection.
Whether vitest attributes it depends on whether it lands while the test file is still
running, which is why it is intermittent.

**Why it matters although it blocks nothing.** An exit code that is sometimes 1 on a
green suite trains everyone to ignore it — the same failure mode as "no run is not
green" (CLAUDE.md, 2026-09-01). The day `continue-on-error` is removed from the web
job, this becomes a random red build.

**Two halves, both small, neither done here:** mock `api` in the test (the test's own
defect), and decide whether Today's `load()` should catch — an unhandled rejection
there is also what production does when that request fails.

---

### TD-102 — the post-generation safety gate runs after the reply has been on screen — **OPEN DECISION**
**Status: OPEN — a decision, not a defect. Logged 2026-09-24 (founder ruling): to be
decided once, for all three chat paths together. Not proposed yet.**

**What it is.** On send-message, another-mind and go-deeper alike, `check_output` runs
on the COMPLETE reply, after every chunk has already been streamed and rendered. On a
positive the client replaces what it showed (`safety_override` → `SafetyBubble`), and
the replaced text is never saved — but the user has seen it for as long as the stream
took. Replies average ~76 output tokens (2026-09-24 measurement), so the window is a
few seconds; it is not zero.

**The trade-off, and it is the whole decision:**
- **Keep streaming (today).** The reply appears as it is written. Exposure lasts the
  length of the stream.
- **Buffer, then check, then send.** Exposure drops to nothing. The reply stops
  streaming on all three paths: the user waits for the whole reply, then sees it at
  once.
- **Check the growing text after each chunk and cut the stream at the first match.**
  Streaming is kept and exposure shrinks to the text before the match — but a phrase
  split across chunks is only caught once complete, so exposure is shorter, not zero.
  The check is ~72 µs on a 306-character reply and grows with length, run once per
  chunk.

**Scope when decided:** all three paths at once. A gate that behaves differently per
path is the defect TD-101 just closed.

---

### TD-101 — another-mind and go-deeper replies skip the post-generation safety gate — **CLOSED**
**Status: CLOSED 2026-09-24. Both paths now run `check_output` exactly as
`stream_response` does: after the stream, on the full reply; on a positive, a
`safety_override` event, the app-voice response streamed in the user's language and
SAVED in place of the reply (`persona_override=True`), a `safety_events` row, and no
allowance consumed (`another_mind_count` / `go_deeper_count` not moved — the
send-message rule). The web client's `sendAnotherMind` and `sendGoDeeper` gained the
`safety_override` case `send` already had; without it the safety text would have been
appended after the harmful text in one bubble. Thresholds, crisis copy and send-message
untouched. When the check runs — after the stream — is TD-102.**

*As logged (HIGH):*

**What it is.** `stream_another_mind` and `stream_go_deeper` never call
`safety_service.check_output`. A reply generated on either path reaches the user
without the post-generation safety gate that `stream_response`
(`conversation_service.py:1081`) and the revisit opening (`:698`) both run — and
without the suppression, app-voice replacement and `safety_events` row that gate
produces when it fires.

**How it was found.** While confirming crisis behaviour for TD-100: neither function
references `safety_service` at all (grep of both bodies, 2026-09-24). The router's
note on these paths — *"No user text on this path; safety ordering enforced at
send-message"* — is about the INPUT gate, and is true: another-mind and go-deeper
carry no new user text, so there is no crisis message to route. It says nothing
about the OUTPUT, and the output is new model text on every call.

**These two are the exceptions, not a pattern.** Every other generation path checks
its output: council (`council_service.py:576`), counterview (`counterview_service.py`,
five sites), self-comparison (`self_comparison_service.py:212`), the worker's letter
and ritual lines (`arq_worker.py`).

**Not measured:** whether any another-mind or go-deeper reply in production would
have tripped the gate. That is a question for the fix's investigation step, not a
reason to rank this lower — the gate exists for the reply nobody predicted.

---

### TD-100 — another-mind is refused at the Pro caps but never counted toward them — **CLOSED**
**Status: CLOSED 2026-09-24 — migration `069_another_mind_count`. Every successful
another-mind reply (not admin, not ritual) upserts `daily_usage.another_mind_count`
on the responding persona's row, and `check_fair_use_limit` sums it with
`message_count` and `go_deeper_count` in both windows. `message_count` is untouched,
so no free limit moved; the data export carries the new column. The upsert is
executed against Postgres in `tests/db_live/test_another_mind_count.py`.**

*As logged:*

`check_fair_use_limit` counts `daily_usage.message_count + go_deeper_count` plus
counterviews. `stream_another_mind` writes **no `daily_usage` row at all** — the only
`message_count` increment is `stream_response` (`conversation_service.py`, Phase C2).
So another-mind is refused once a Pro user is at 150/day or 400/month, but every
another-mind reply before that is free against both, and the monthly ceiling is not
a hard ceiling while this stands.

**The fix needs a counter column** (e.g. `daily_usage.another_mind_count`), not a
`message_count` bump: `check_rate_limit` sums `message_count` for the FREE tier, so
reusing it would silently tighten a free limit — out of scope for a cost change.
Go-deeper was closed the same way on 2026-09-24, using the `go_deeper_count` column
that already existed. Proposal owed after the cost-ceiling PR merges.

---

### TD-99 — `ANTHROPIC_MODEL` defaults to deprecated Claude Sonnet 4 — **NEW**
**Status: OPEN. Logged 2026-09-24, no action yet (founder ruling).**

`config.py` sets `ANTHROPIC_MODEL = "claude-sonnet-4-20250514"`, which Anthropic lists
as **deprecated** (retirement date not yet announced). It is not only counterview:
`counterview_service.py` (three calls), `insight_mirror_service.py`,
`workers/arq_worker.py` (four calls, one commented as the "gravity/differentiation
artifact"), and `llm_client.stream`'s fallback when a caller passes no model.

**NOT VERIFIED:** whether Render sets `ANTHROPIC_MODEL` and overrides the default.
Read the API and worker services' env before acting — if it is set, the deployed model
is whatever it says, not this default.

**Migration target: `claude-sonnet-4-6`** — the model the Pro chat path already runs
(`MODEL_PRO`), at the same per-token price ($3 / $15 per MTok), so the change moves no
cost. The current-generation alternative is `claude-sonnet-5` ($2 / $10), but its
tokenizer produces ~30% more tokens for the same text and its behaviour would need
re-judging on every surface above; that is a quality decision, not a deprecation fix.
The counterview, mirror and letter surfaces were tuned on Sonnet 4 output, so the
switch owes a before/after read of each, not only a config edit.

---

### TD-98 — retrieval forced-injection arm: no effect. The hypothesis CLOSES for now. — **NEW**
**Status: CLOSED for now, measured — founder ruling 2026-09-23. Retrieval stays
dead. RETRIEVAL-001 is unchanged and still open as a defect.**

**THE QUESTION, and why it needed an arm rather than an argument.** Every §8.2 reply
ever generated ran with `passages=[]`, because production retrieval has never
returned a passage (RETRIEVAL-001). So the effect of grounding passages on
distinctiveness had never been *measured*. The available argument was the mismatch
between corpus size and recognition — Jung has **0 chunks** and is recognised, Wilde
has **352** and is not — and that is suggestive rather than decisive, because
retrieval was off for both.

**THE DESIGN.** Top-1 chunk forced into the prompt **with no threshold**, for
`sigmund_freud` and `epictetus` — the two personas with both a real corpus and the
highest observed similarity. Their 7 standard replies each, under the **shipped arm E
directive**. Control: their stored arm E replies, `passages=[]`, already judged.
Judged 2 independent calls, 93% self-agreement.

**THE PASSAGES WERE REAL AND THEIR SCORES ARE RECORDED**, which is the part that
makes the negative result load-bearing:

| | |
|---|---|
| injected cosine range | **0.1917 – 0.4172** |
| mean | 0.2965 |
| would clear the live 0.72 threshold | **0 of 14** |

This arm therefore asks what **the best available passage** does, not what a good one
would do.

**THE RESULT: NO RISE IN EITHER PERSONA.**

| persona | recall control | recall arm F | named control | named arm F |
|---|---|---|---|---|
| Sigmund Freud | 5/7 | **4/7** | 11 | 8 |
| Epictetus | 5/7 | **5/7** | 10 | 10 |

Freud drifted down, Epictetus was unchanged. Neither rose. **Both flat.**

One side-effect worth recording: arm F's guesses drifted toward **Beauvoir (1 → 7
of 28)**. A passage in the prompt did change something — it just did not make the
persona more identifiable as itself.

**AND THE PASSAGES DID NOT LEAK AS QUOTATION**, which was the product risk the
14 replies were exported to check. Five of fourteen contain quotation marks; **all
five are the persona quoting the USER back to themselves**, a normal move that
predates this arm. No source title, no "as I wrote", no paraphrase attributed to a
text. Replies are at a 70-word median, in band. The export is
`evals/results/2026-09-23_armF/armF_replies.md`.

**THE RULING, in the words it was given, because the distinction matters.** NOT
"retrieval can never help". Rather: **"forcing the best available passage on the two
best-equipped personas produced no visible effect at this sample size, and a bigger
arm is not justified without one."** A rise in either persona would have reopened
retrieval as a real workstream (threshold, chunking, coverage). Neither rose.

**WHAT THIS DOES NOT SAY.** n=7 per persona. A real effect smaller than this arm
could see is not excluded. What is excluded is the cheap version of the hypothesis —
that the 0.72 threshold is the only thing standing between the corpus and better
distinctiveness. It is not: the passages were injected *past* the threshold and
nothing moved.

**Constraints honoured.** Oregon access was **READ-ONLY by server enforcement**: the
chunk fetch ran inside `BEGIN TRANSACTION READ ONLY` with `SHOW
transaction_read_only` asserted `on` before any query, and was rolled back rather
than committed. SELECT only — no writes, no DDL, no RPC creation, no temp tables.
**Production code untouched**: the sole change outside `evals/` is an optional
`passages=()` parameter on `harness.assemble_system` / `generate`, defaulting to
empty, which is production identity — every other arm's prompt is byte-unchanged.

**One operational finding, fixed in passing.** `PROD_DATABASE_URL` in
`apps/api/.env` **broke the entire application and test suite**: `config.Settings`
forbids extra inputs, so every import of `config` raised `ValidationError`. It was
moved to `apps/api/.env.local`, which is gitignored and which `Settings` does not
read. Anyone adding a local-only variable must put it there, not in `.env`.

---

---

### TD-97 — all three arm E smoke replies ended on a two-option question — **NEW, OBSERVATION ONLY**
**Status: OPEN as a watch item. NO ACTION — founder ruling 2026-09-23. Nothing is
proposed and nothing is changed.**

**THE OBSERVATION.** The P-04 smoke for arm E (#719) passed — Marcus, Socrates and
Lao Tzu, first message, QA account, all in band, nothing broken. But **all three
replies ended on a two-option question**: *"which is heavier"*, *"which would you act
on"*, *"what would it feel like"*.

That is the shape family arm E's deletions removed — the directive no longer tells
any persona to *"Leave an easy opening to continue — usually one natural, answerable
question"* — **reappearing**.

**MEASURED AGAINST THE STORED ARM E CORPUS, because "may be coincidence" is testable
and the base rate was free to compute.** Counting replies whose LAST sentence is an
X-or-Y or "which/whether" question:

| | last sentence is a two-option question |
|---|---|
| control (production before arm E) | 18/77 — **23%** |
| arm D (all three shape clauses out) | 13/77 — 17% |
| **arm E (shipped)** | 12/77 — **16%** |
| …arm E, the three smoke personas only | **2/21 — 9.5%** (Marcus 0/7, Socrates 2/7, Lao Tzu 0/7) |

**Two things follow, and they point opposite ways.**

1. **Arm E did not increase this shape — it reduced it.** 23% → 16% overall. So the
   deletions did not backfire in aggregate, and the smoke is not evidence that they
   did.
2. **3 of 3 is nonetheless unlikely.** Against the 9.5% base rate for those three
   personas, P(3 of 3) ≈ **0.0009**; against arm E's overall 16%, ≈ **0.004**. Marcus
   and Lao Tzu end on a two-option question in **zero** of their 14 stored arm E
   replies, and in the smoke both did.

**THE CAVEAT THAT KEEPS THIS AN OBSERVATION.** Only one of the three smoke prompts
(Marcus's ghosting prompt) is from the stored problem set; the Socrates and Lao Tzu
prompts were written for the smoke and have never been run through an arm. So the
base rate is a prior, not a matched control, and the comparison is suggestive rather
than clean. **n=1 per persona.**

**WHAT WOULD SETTLE IT, and it is cheap:** the next smoke, or any handful of
production first messages, counted the same way. If two-option endings keep landing
at 3-in-3 against a 10-16% base, that is a real shape the deletions displaced rather
than removed — the model finding another route to the same move. If the next batch
looks like 16%, this entry closes as coincidence.

**Do not act on this entry.** It exists so that a recurrence is recognised as a
recurrence rather than discovered fresh, which is the whole value of writing down an
n=1.

---

---

### TD-95 — one shared reply directive, at 94% of the prompt, prescribes one reply shape for all eleven personas — **NEW**
**Status: OPEN. INVESTIGATION ONLY — founder ruling 2026-09-23: report, do not fix.
No proposal is made here.**

**THE STRUCTURE.** `reply_directive.FIRST_MESSAGE` is appended **last** to every
persona's system prompt, after HARD RULE 8. Measured on Lao Tzu's assembled prompt
(12,315 chars):

| block | position | % through |
|---|---|---|
| the persona's own `system_fragment` | 805 | **7%** |
| CONVERSATIONAL MOVES | 4,807 | 39% |
| VOICE CALIBRATION | 7,377 | 60% |
| HARD RULES | 10,004 | 81% |
| **shared FIRST MESSAGE directive** | 11,541 | **94%** |

The persona's own voice instruction is the **first** thing said about how to speak;
the shared one is the **last**, and it is identical for all eleven.

**IT PRESCRIBES THE THREE-BEAT SHAPE FOUND IN EVERY REPLY.** The §8.2 distinctiveness
run found one shape across all eleven personas: acknowledge → interpret → open
question. The directive states it:

> "…**name something meaningful you notice**, and take a clear but proportionate
> position on it. You may **offer an interpretation**, but offer it tentatively and
> ground it in their own words… **Leave an easy opening to continue — usually one
> natural, answerable question**…"

That is not eleven voices converging. **It is the house style, written down, shared,
and placed last.**

---

#### (1) The five RIGHT calibration examples the directive forbids

The directive bans *"never tell them, directly or by implication, that they are
hiding, avoiding, or failing to name something."* Measured against every persona's
approved `voice_calibration_examples`:

| persona | conflicting | of | the clause it breaks |
|---|---|---|---|
| **marcus_aurelius** | 2 | 6 | *"You're not avoiding the task. You're avoiding what finishing it would say about you."* / *"Name the one you're both avoiding."* |
| **miyamoto_musashi** | 2 | 5 | *"you are only avoiding the cost of saying so"* / *"the elaboration you are hiding in"* |
| **george_orwell** | 1 | 5 | *"where the real question is hiding"* |

**5 examples across 3 of 11 personas (27%).**

The prompt shows the model these at **60%** as *"RIGHT — match this pattern"*, then
forbids the pattern at **94%**. The two blocks disagree and the later one is more
specific.

*(Musashi's two were rewritten in the 2026-09-23 voice fix, since they were teaching
him to break a clause he was simultaneously being measured against. Marcus's two and
Orwell's one are untouched and still conflict.)*

---

#### (2) Which clauses are SHAPE, and which are safety/quality

`FIRST_MESSAGE` decomposes into eight clauses. Three are shape; five are not.

| clause | kind |
|---|---|
| "Write between {lo} and {hi} words — about {target}" | **LENGTH** — per-persona already |
| "name something meaningful you notice, and take a clear but proportionate position on it" | **SHAPE** (beats 1–2) |
| "You may offer an interpretation, but offer it tentatively and ground it in their own words" | **SHAPE** (beat 2) |
| "never tell them… they are hiding, avoiding, or failing to name something" | **QUALITY** — `CONCEAL_BAN` |
| "You may challenge what they have said; do not speculate about what they have not" | **QUALITY** — `CHALLENGE` |
| "Leave an easy opening to continue — usually one natural, answerable question, which may sit anywhere… never a closing seal" | **SHAPE** (beat 3) + quality tail |
| "Plain, precise language in your own register — never contemporary slang" | **REGISTER** — `REGISTER` |
| "no decorative aphorisms or fortune-cookie phrasing" | **QUALITY** |

**THE QUALITY CLAUSES ARE THE LISTENING RUBRIC, TURNED INTO INSTRUCTIONS.** The
correspondence is one-to-one with `evals/listening.py`'s criteria:

- `CONCEAL_BAN` ↔ criterion **(a)** concealment / over-interpretation
- "never a closing seal" ↔ criterion **(b)** sealing question
- "no decorative aphorisms or fortune-cookie phrasing" ↔ criterion **(c)** oracular
- "Respond specifically to what this person has actually said" ↔ criterion **(d)**
- `CHALLENGE`'s second half ↔ criterion **(e)** misattribution

**That is the finding.** The directive was built to move the listening metrics, and it
did. **The three SHAPE clauses came along with it** — they are not measured by any
instrument the project owns, and nothing has ever tested whether they should be
shared. Distinctiveness was not a metric when this text was written.

**Three of the eight clauses are already named constants** — `REGISTER`, `CHALLENGE`,
`CONCEAL_BAN` are extracted and composed. The shape clauses are inline prose.

---

#### (3) Is a per-persona exemption feasible without rewriting the directive?

**Yes, and the seam already exists.** `reply_directive.directive()` already:

- takes `persona: PersonaConfig` as its first argument;
- already varies per persona (`spec.standard_reply_words`, `DEEP_FLOOR.get(persona.slug)`);
- already has a graceful-degradation path (`_report_degraded`) for a persona missing
  what it needs;
- already composes the string from named constants plus `.format()`.

An exemption set — a per-persona field naming clauses to omit or replace, defaulting to
none — is a small change to one function. **The directive text would not need
rewriting**, only decomposing the three inline shape clauses into named constants
alongside the three that already are.

**WHAT IT WOULD BREAK, and this is the real cost:**

1. **`arm_directive_hash` stops being well-defined.** It digests
   `FIRST_MESSAGE + STANDARD + DEEP` as module constants (`evals/run.py:214`). If those
   become per-persona, one hash can no longer describe a run, and the manifest's ability
   to detect "the same arm re-run after a reworded directive" is lost unless it becomes
   per-persona too.
2. **`tests/test_harness_parity.py`** asserts byte equality between `assemble_system`
   and an inline rebuild from production pieces, for all 11 personas × deep/standard ×
   bridge on/off. It would need the persona-aware path on both sides.
3. **`evals/arm_b3.py` re-exports the production strings** specifically so "the arm that
   was measured and the prompt that ships are the same object". Per-persona directives
   make that re-export ambiguous.
4. **Every stored §8.2 baseline becomes incomparable for any exempted persona** — the
   same cost as TD-94's render option, but scoped to whoever is exempted rather than all
   eleven at once. That scoping is the main argument for the exemption over a rewrite.
5. **The quality clauses must not be exemptible.** `CONCEAL_BAN` exists because a human
   reader found concealment in 7 of 11 replies; it is the thing arm B was built to fix.
   An exemption mechanism that can switch it off is a regression waiting for a persona
   author in a hurry. If this is built, the shape clauses and the quality clauses need
   to be different kinds of thing in the code, not two lists.

**Evidence that the ceiling is the directive rather than the persona copy** — indirect,
and stated as indirect. In the 2026-09-23 voice fix, Musashi's move had to be weakened
specifically because its sharp form (*naming a rep the person has never done*) is
forbidden by `CHALLENGE`'s second half. The weakened version still moved him 0/10 → 2/10
and got him proposed for the first time in 220 judgements. Marcus, whose fix needed no
directive exemption and received the strongest persona-level intervention available,
moved 0/10 → 0/10. **One data point each, and they point the same way.** Neither
establishes causation: that would need an arm that changes the directive, which has not
been run.

**NOT INVESTIGATED:** whether `STANDARD` and `DEEP` carry the same shape clauses (they
are separate strings), and what the directive does across a whole conversation rather
than a first message. Every §8.2 sample is a first message, so `FIRST_MESSAGE` is the
only path with any measurement at all — `reply_directive.directive`'s own docstring says
so.

---

---

### TD-94 — `character_anchors` reaches NOTHING: not the prompt, not the app, not a test — **NEW**
**Status: RULED 2026-09-23 — DEMOTE. `character_anchors` stays as documentation only.
Found the same day while implementing an approved voice fix, which it blocked.**

> **THE RULING, and its reasoning.** Not deleted: it is the Section 5.7 design record and
> the clearest statement of each persona's intent in the repo. Not rendered: wiring eleven
> personas' anchors into the prompt at once would invalidate every stored §8.2 baseline in
> a single step and surface eleven latent anchor/fragment contradictions simultaneously.
> **Wiring anchors into the prompt is its own future decision, not a side effect of a
> voice fix.**
>
> **Shipped for this ruling:** a `PersonaConfig` docstring naming which fields render and
> which do not, per-field `DOC ONLY` / `LIVE` markers at the Section 5.7 declarations, and
> `tests/test_persona_rendered_fields.py`, which pins the docstring's RENDERED list against
> what `system_base.jinja2` actually reads — because a docstring is a doc claim, and this
> file's standing lesson is that an unverified doc claim is evidence about the previous doc.
> The second test fails deliberately if anchors are ever rendered, so that decision cannot
> be taken in passing.
>
> **The investigation also widened the finding.** `character_anchors` is not the only dead
> field — it is the one that bit us. **Seven** are read by nothing at all.

**THE FACT.** `PersonaConfig.character_anchors` — 60+ authored rules across eleven
personas, each with an `enforcement` paragraph and a `critical` flag — is **read by no
code that runs.**

Checked, 2026-09-23, and each of these is a separate search:

| consumer | result |
|---|---|
| `prompts/system_base.jinja2` | `grep -c anchor` → **0**. The template never mentions it |
| app code (`services/`, `routers/`, `workers/`) | **no references** |
| `evals/` scorers and harness | **no references** |
| the test suite | **not one test asserts on it** |
| `db/migrations/` | the only references — frozen into `personas.config` jsonb |

And the one place it lands is itself dead: **TD-91** records that `personas.config` in
production is badly stale and nothing reads it. So the field is serialised into a
column no code queries.

**WHAT THE TEMPLATE ACTUALLY READS**, enumerated the same day (every `persona.<field>`
in `system_base.jinja2`):

> `challenge_level`, `challenge_style`, `conversational_moves`,
> `emotional_acknowledgment`, `forbidden_phrases`, `questioning_pattern`,
> `sentence_structure`, `system_fragment`, `tone`, `vocabulary_register`,
> `voice_calibration_examples`

**Declared on `PersonaConfig` and never read by the template:** `character_anchors`,
`anti_flexing`, `register_range`, `response_length_words`,
`forbidden_lexicon_persona_specific`, `behavioral_parameters`,
`behavioral_parameters_by_register`, `worldview`, `uses_personal_anecdote`,
`opening_invocation`, `tagline`, `era`, `tradition`.

Several of those are read elsewhere — `response_length_words` by the arm band logic,
`forbidden_lexicon_persona_specific` by postprocessing — and are NOT dead. **This entry
is about `character_anchors` specifically, which has no consumer anywhere.** The others
are listed because the same question will be asked of them and the list is the answer.

**HOW IT WAS FOUND, and why the detection worked.** Three persona configs were edited
under an approved voice fix (Marcus, Lao Tzu, Musashi — all four diffs were
`character_anchors` edits). 30 replies were regenerated. `run.py`'s
`persona_config_hash` came back **`be4c9e3d3d7e7959` — byte-identical to the B3 run the
edits were meant to change.**

That hash is the reason this was caught within one run instead of being read out of a
noisy matrix. Its docstring explains that it hashes **the rendered prompt** rather than
a list of fields, precisely because an earlier field-enumerating version missed
`forbidden_phrases` and would have made two different arms indistinguishable. It did
exactly the job it was built for: **an edit that cannot change the prompt cannot change
the hash.**

Confirmed independently: of the 30 regenerated samples, the 21 standard ones have
`system_prompt_chars` identical to B3. (The 9 deep ones differ by a constant +73 chars —
that is the register clause reaching DEEP, a founder-ruled change since the B3 run and
documented in `evals/arm_b3.py`. Unrelated to the edits.)

**THE COST OF THE GAP IS NOT THE $0.22.** It is that every anchor reads like an
enforced rule and none is enforced — including ones that describe behaviour the
rendered prompt actively contradicts. `marcus_aurelius`'s
`anchor_private_admonition_not_public_instruction` says he "speaks as one who has first
judged himself", while his `system_fragment` — which does render — says *"never
volunteer … 'I wrote to myself…'"*. The anchor is not merely inert; it asserts the
opposite of what ships, and a reader auditing the persona would believe the anchor.

**THE SEVEN DEAD FIELDS** (0 consumers across `services/ routers/ workers/ evals/
scripts/` and the template, counted 2026-09-23): `character_anchors`, `anti_flexing`,
`behavioral_parameters`, `behavioral_parameters_by_register`, `register_range`,
`worldview`, `uses_personal_anecdote`.

**`anti_flexing` is the instructive one, and it explains how this survived.** It is
dead — and anti-flexing *works*. All **11 of 11** personas duplicate it as an
"ANTI-FLEXING:" line inside `system_fragment`, which does render. So the field sits
beside behaviour that visibly happens, and reads exactly like the cause of it. That is
the shape of every trap in this file: **a dead thing next to a working thing is
indistinguishable from the working thing until someone edits it.**

**THREE OPTIONS — (3) WAS TAKEN, see the ruling at the top of this entry.**

1. **Render them.** Add a `character_anchors` block to `system_base.jinja2`. Highest
   fidelity to the authoring intent, and the largest blast radius: it would add
   substantial text to all eleven system prompts at once, invalidating every stored
   §8.2 baseline in the same stroke. It would also surface every latent contradiction
   between an anchor and its own `system_fragment` simultaneously.
2. **Delete the field.** Honest, and discards real authoring work that is the clearest
   statement of each persona's intent anywhere in the repo.
3. **Demote it to documentation.** Keep it, rename it so it cannot be mistaken for
   enforcement, and state at the dataclass that it is authoring intent with no runtime
   effect. Cheapest, and leaves the contradiction in (1) unresolved but visible.

**Whichever is chosen, `PersonaConfig` needs a docstring saying which fields reach the
prompt.** The field list above took three separate greps to establish, and the absence
of that list is what let four approved diffs be written against a dead field — by
Claude, in a proposal, and approved without either party catching it. That is the same
class as this file's standing lesson: **a config field that looks load-bearing is a
claim, and it had never been checked against the template.**

---

---

### TD-93 — HARD RULE 4 asks for ~40% question-endings and every persona runs at 80–90% — **NEW**
**Status: OPEN. Recorded, out of scope — founder ruling 2026-09-23.**

**Found by** the §8.2 distinctiveness investigation, as a control measurement rather
than a target: the question was whether reply SHAPE explained why three personas are
unrecognisable. It does not, and that is why this is its own item instead of part of
the voice fix.

`system_base.jinja2` HARD RULE 4 is explicit about the mix:

> *"most replies should NOT end in a question. Vary your endings: roughly 40% end
> with a question, 40% end with no question at all …, 20% a brief statement THEN a
> question. A question every single reply turns dialogue into interrogation."*

Measured over the 110 stored B3 Sonnet replies, 10 per persona:

| persona | ends on "?" | replies with 2+ questions |
|---|---|---|
| Niccolò Machiavelli | 90% | 1 |
| Carl Jung | 90% | 1 |
| Simone de Beauvoir | 90% | 0 |
| Marcus Aurelius | 90% | 0 |
| Lao Tzu | 90% | 0 |
| Epictetus | 80% | 2 |
| Miyamoto Musashi | 80% | 3 |

**Every persona measured is at double the target or more.** The rule is not being
partially followed — it is not operating at all.

**WHY THIS IS NOT A DISTINCTIVENESS DEFECT, which is the useful half of the
finding.** The obvious reading is that a uniform ending shape makes the personas
interchangeable. The data refuses it: **Machiavelli sits at 90% and is the most
recognisable voice in the product** (83% precision, the highest of the eleven),
while Lao Tzu sits at the same 90% and was never once identified. A variable that
takes the same value for the best and worst cases explains neither. Distinctiveness
lives in the middle of the reply, not its last sentence — see
`evals/results/2026-09-22T12-59_b3/distinctiveness_record.md`.

So this is a **conversational-quality** defect on its own terms, and the rule states
the cost itself: a question every single reply "turns dialogue into interrogation".
Three of the sampled replies carry 2+ questions against personas whose own configs
say to ask at most one — Musashi's `questioning_pattern` says "Ask sparingly — state
and instruct more than you ask" and he has the most multi-question replies of any
persona.

**NOT DIAGNOSED, and it should be before anything is changed.** Whether this is the
rule being ignored, or being outweighed by something else in the prompt, is unknown.
Candidates, none checked: every persona also carries an `anchor_..._one_question`
rule that says at most one question and may be read as *at least* one; the
`conversational_moves` block asks for one move per reply and several moves are
question-shaped; the eval corpus is all FIRST messages, where an ending question is
the most natural move and the true production rate across a whole conversation may
differ. **The last of those would change what the number means**, and it is a
property of the eval set rather than the product.

**Explicitly out of scope of the voice fix** (`feat/voice-distinctiveness-three`),
which touches three persona configs and is measured on whether three personas become
identifiable. Changing endings product-wide is a different change with a different
blast radius — it would touch all eleven and the shared directive — and mixing it in
would make neither measurable. P-02.

---

---

### TD-92 — Marcus carries `Meditations` twice: the full Gutenberg text and 19 hand-curated chunks of the same translation — **NEW**
**Status: OPEN. Recorded, no action — founder ruling 2026-09-23.**

**Found by** the per-persona corpus read done for RETRIEVAL-001 (Oregon,
2026-09-23). It was reported as an anomaly and investigated as one. **It is not
one** — and that correction is the reason this entry exists in the shape it does.

| `source_title` | chunks | avg chars/chunk | ingested |
|---|---|---|---|
| `Meditations` | 212 | 2,116 | 2026-05-17 |
| `Meditations (curated)` | 19 | 270 | 2026-05-17 |

**FIRST READING, WRITTEN DOWN AND THEN FALSIFIED.** 270 characters against 2,116
looks like a different chunking regime, so the obvious inference was a remnant of
an older ingest that the full-text load never cleared. **That was wrong.**
`scripts/curated_chunks.py` exists for exactly this, says so in its docstring, and
its `CURATED_CHUNKS["marcus_aurelius"]` list holds **19 entries — the same 19**:

> *"Hand-curated chunks: high-quality passages selected manually with precise
> citation references... curated chunks use `source_title = "Meditations
> (curated)"` while the auto-chunked Gutenberg run uses `source_title =
> "Meditations"`."*

The small chunks are the **point**, not the symptom: they are passages chosen by
hand and carrying a real `page_ref`. Marcus is the only populated persona in that
module, "recovered from pre-C3a `ingest_sources.py`". The deliberate disambiguation
in the title is the thing that made this look accidental from the database alone.

**WHAT IS NEVERTHELESS TRUE, and is the actual finding.** Both rows are the **same
book in the same translation** — `CORPUS_SOURCES["marcus_aurelius"]` is Long (1862)
from `gutenberg.org/cache/epub/2680`, and `curated_chunks.py` names *"Meditations
(Long 1862, PD). Source: .../ebooks/2680"*. So the 19 curated chunks are not merely
similar to the 212; **they are a hand-cited subset of the identical text, duplicated
by construction.**

**Same class as TD-90, one third the size, and better-founded.** TD-90's Epictetus
overlap is two honest translations, accepted as the price of truthful attribution.
This is one translation stored at two granularities on purpose. The mechanism of
harm is identical and already written up there: `retrieval_service.retrieve`
(`:31-44`) selects on `persona_slug` with **no dedup and no source filter**, and
Marcus has `retrieval_top_k=4` (`personas/marcus_aurelius.py:58`), so a query could
spend two of four slots on one passage in two sizes and the model could attribute
it twice.

**Today it can do none of that.** Marcus's measured top-1 cosine ceiling is
**0.455** against the 0.72 threshold (RETRIEVAL-001), so **not one of his 231
chunks has ever been returned to a prompt.** This is latent behind the same wall as
TD-90 and becomes live in the same moment.

**THE FIX IS TD-90's FIX, NOT A DELETION.** Deleting the curated 19 would discard
the only hand-cited passages in the corpus and the only reason `curated_chunks.py`
exists; deleting from the 212 would break the file-matches-config invariant #683
established. A near-duplicate filter at retrieval time covers both this and TD-90
at once. **Whoever takes TD-90 takes this with it** — and should note that TD-90's
closing question, what `retrieval_sources` is actually for, is the same question
here.

---

---

### TD-88 — Six UAT-1 findings are routed to a section number that does not exist — **NEW**
**Status: OPEN. Not scheduled. Written because a citation a reader cannot follow is
the defect TD-79 just closed, one document over.**

**Verified at `9ad352fb`** by grepping the repository for the section number and by
reading the two instruments that do exist.

**The claim.** The UAT-1 filing header (`docs/qa/UAT-1_2026-09-14.md`) records the
disposition of all 30 findings, and six of them — **BUG-009, BUG-010, BUG-011,
BUG-012, BUG-013 and BUG-015** — are "routed to the §8.2 eval harness". Those are the
persona-fidelity findings: voices collapsing toward one coaching template, Lao Tzu
needing to be prompted into Taoism, Marcus reading as Socrates, Musashi and
Machiavelli not answering a rebuttal, and You-vs-You overstating certainty on thin
evidence.

**There is no §8.2 in this repository.** A repo-wide grep for `§8.2`, and for an `8.2`
heading in any form, returns nothing. Neither `HANDOFF_BRIEF_v30.md`, this file, nor
`PROJECT_STATE_v29.md` numbers a section that way at all.

**And the nearest §8 is a trap.** `RUNBOOK_LOOP_METRICS.md` is the one current
document whose numbering reaches §8 — where §8 is **"Unit cost — the depth risk"**. A
reader chasing "§8.2" finds either nothing or a cost section, and concludes the
reference is stale rather than absent. The section that actually relates is its §7,
"Sameness — the D2 metric".

**What DOES exist, stated so this entry is not read as "nothing was built".** Two
partial instruments, each of which says in its own text that it is partial:

- `RUNBOOK_LOOP_METRICS.md` §7b/§7c — lexical recurrence against a control, and
  structural drift against the shipped spec. It scores replies and holds no opinion.
- `docs/PROTOCOL_FOUNDER_READ_SAMENESS.md` (D2-b, #665) — a structured founder read of
  three conversations. One reader, n=3, with its own bias named in the document.

**Neither is the harness these six findings need, and the gap is specific: the word
`blind` appears in neither file.** The register's acceptance tests for these six ask
for a stable cross-persona prompt set, **blind reviewers identifying the intended
thinker materially above chance**, per-thinker fidelity rubrics, and confidence
calibration against evidence depth. Gate C of the register makes blind cross-persona
evaluation a release gate and the Definition of done repeats it. Sameness scoring and
a founder read are inputs to that; they are not it.

**What it costs.** Whoever builds the harness starts by looking for §8.2, finds
nothing, and either reconstructs the routing decision from a chat log or concludes
these six findings were never triaged. The requirements did not go missing with the
section number — they are in `docs/qa/UAT-1_2026-09-14.md`, in each finding's
**Acceptance tests** block and in Gate C. **That file, not §8.2, is the durable
statement of what the harness must do.**

**What closing it looks like.** When the eval-harness spec lands in the repository,
give it a stable heading and repoint three things at it: this entry, the UAT-1 filing
header's status line, and the §8.2 reference itself. Until then the header says the
routing lives in the planning record, which is true and is the whole of what is known.

**Why this is an entry rather than a fix.** The fix is the harness, and
`RUNBOOK_LOOP_METRICS.md` §7d already ranks the population problem above both existing
instruments — there may not yet be enough conversations to measure blind
identification against. A pointer to a section that does not exist is cheaper to
correct than to leave asserting.

### UAT2-004 — the persona forbidden-lexicon check does not run in production — **PARTLY CLOSED**
**Status: PARTLY CLOSED. Wired at 2 of 14 sites (founder ruling D1, 2026-09-21).
12 sites remain unwired and are enumerated below with a per-site reason. The
original framing — "making the checker RUN is the separate, larger question" —
is what this PR took.**

---

## THE DRY RUN that decided the scope

Before wiring anything, `check_persona_forbidden` as it stood on main was run
against **all 826 assistant replies in Oregon**, 2026-04-26 to 2026-09-21, all
eleven personas (`persona_override` safety responses excluded — those are app
voice). Method verified rather than trusted: the SQL normaliser was checked
against Python's `normalize()` on all 20 distinct non-ASCII phrases (0
mismatches), naive-substring controls confirmed the zeros were real, and every
hit was re-run through the actual Python matcher, which agreed exactly.

**11 of 826 replies (1.33%) would have fired** — 7 by phrase, 4 by pattern, no
overlap. Of those, **9 were true positives** (the persona volunteering what its
`anti_flexing` forbids) and **2 were false positives**, both Socrates quoting the
user's own "you should" back at them, which is the elenchus. Ruling D2 dropped
that entry; the rate is now **1.09%**.

**Only 4 of 215 phrases and 1 of 24 patterns matched anything at all.** Personas
with zero firings across the whole corpus: marcus_aurelius, epictetus,
sigmund_freud, george_orwell, niccolo_machiavelli, oscar_wilde, miyamoto_musashi.

**WHY THE RATE IS SO LOW, and why that is not reassurance.** `forbidden_phrases`
is already injected into every system prompt as `DO NOT USE: …`
(`system_base.jinja2:25`) and overlaps heavily with the structured lexicon.
Measured: Freud never once writes "unconscious" in 82 replies; Orwell never
writes `woke`, `stakeholder`, `the masses` or `your truth`; Beauvoir never writes
`men are`. The post-check is a second net under a net that already catches
almost everything. But the hinge-class exposure is real and merely
**unexercised** — `men are`, `obviously`, `the answer is`, `warrior`, `be a man`,
`alpha`, `sigma`, `synergy`, `be present`, `rise above`, `optimize`, `level up`
are all live ordinary English. They score zero because the prompt suppresses
them, not because they are safe.

**Cost, for the record:** at 1.09%, wiring adds **+0.8%** to the bill per 100
messages. Not a factor in the decision either way.

---

## WHAT WAS WIRED (this PR)

- **Site 1, `conversation_service.stream_response`** — added to the trigger
  tuple; uses the SSE `correction` path that already existed for the universal
  lexicon.
- **Site 4, `conversation_service.create_reading_revisit`** — calls
  `regenerate_or_trim(..., brevity_triggers=False)`. Nothing is streamed, so a
  hit is simply regenerated.

**Brevity did not become live at either site**, and `brevity_triggers` exists
specifically to stop it doing so through `regenerate_or_trim` — see BREV-001.

## WHAT REMAINS — 12 sites, with the reason for each

**Four streaming sites with no client `correction` handler.** The SSE event and
its handling exist only in `useStream`'s `send`; `sendAnotherMind` and
`sendGoDeeper` have their own event loops without it, and council and you-vs-you
have their own SSE parsers entirely. Each needs client work, which this PR does
not touch.

| site | why not |
|---|---|
| 2 `stream_another_mind` | `useStream.sendAnotherMind` has no `correction` case |
| 3 `stream_go_deeper` | `useStream.sendGoDeeper` has no `correction` case |
| 5 `council_service.stream_council` | own SSE parser in `council/page.tsx` |
| 9 `self_comparison_service.stream` | own SSE parser in `you-vs-you/page.tsx` |

**Eight batch sites that `regenerate_or_trim` does not fit.** The original ruling
listed nine batch sites as trivial; the map said "batch" without saying **JSON**,
and that was wrong. `regenerate_or_trim` needs a `PersonaConfig`, free-form prose,
and a system+user pair. Measured against each:

| site | why not |
|---|---|
| 6 `council_service._distill_brief` / `display_brief` | **no persona at all** — Haiku transcript summarisation, app voice |
| 7 `counterview_service` ×3 | **JSON** → `_extract_verdicts`; a prose lexicon over JSON, then `_deterministic_strip`, corrupts the envelope |
| 8 `insight_mirror_service.generate_insight_mirror` | **JSON** (fenced) |
| 10 `self_portrait_summary.generate_portrait` | **JSON** → `_parse_json` |
| 11 `arq_worker.assess_conclusion_task` | prose, but `persona` is a DB row not a `PersonaConfig`, `get_persona` is not imported in that file, and the row can be `None`. Zero firings in 5 months (32 conclusion replies) — ruled out as not worth the surface (D7) |
| 12 `arq_worker.generate_weekly_mirror_task` | **JSON** + already has its own retry loop |
| 13 `arq_worker.generate_weekly_letter_task` | **JSON** + own retry loop |
| 14 `arq_worker.generate_monthly_letter_task` | **JSON** + own retry loop |

**All 11 dry-run firings were on `message_kind = 'standard'` — site 1.** The batch
surfaces contributed none, so the reduced scope costs no observed coverage.

A future wiring of the JSON sites would have to check the **extracted prose
field** and re-call the site's own generator, which is new logic per site, not
`regenerate_or_trim`.

---

**Original entry follows, unchanged except the status line.**

**WHERE UAT FINDINGS LIVE — ruling, 2026-09-21.** `docs/uat/` is **not created**.
UAT findings go here, in `IMPLEMENTATION_BACKLOG_v29.md`, on the same shelf as
RETRIEVAL-001 and SAFETY-001 — one place for everything. Any future UAT item
follows this entry. The note that prompted this ruling had been living in a code
comment (`postprocessing_service.py:390`), which is exactly the drift CLAUDE.md's
failure log warns about: a finding recorded outside the document that gets read.

**THE FACT, verified by reading the imports rather than inferring from the call.**
`check_persona_forbidden` (`postprocessing_service.py:363`) is invoked from exactly
one place — `regenerate_or_trim` (`:449`). `regenerate_or_trim`'s only non-test
caller in the repository is `scripts/voice_test_socrates.py:55`, a dev script.
`conversation_service.py:31-37` imports `POSTPROCESSING_ENABLED`,
`check_universal_forbidden`, `check_brevity`, `CheckAction` and
`_build_regen_directive` — **`check_persona_forbidden` is not among them.** So every
persona's `forbidden_lexicon_persona_specific` is inert in production: 11 personas,
each carrying a curated phrase list and regex patterns, none of it checked against
any reply a user has ever received.

**#684 fixed its matcher anyway**, deliberately. Ruling B moved both phrase checks
from bare substring containment to a compiled word-boundary matcher, including this
one, "so the two cannot drift apart" — correct, and worth preserving as the reason:
when the checker is eventually wired up, it will not arrive carrying the 2026-09-20
mid-word defect.

**THE "ENERGY" SURVIVAL, now resolved in both places it existed.** Ruling C removed
the bare token `energy` from `universal_forbidden_lexicon.json` because word
boundaries cannot save a token that IS an ordinary English word. Two persona configs
still carried it, in two different fields with two different fates:

- **`lao_tzu.forbidden_phrases`** — **live, and fixed in this PR.** This field is
  injected verbatim into every system prompt (`prompts/system_base.jinja2:25`, as
  `DO NOT USE: …`), a path Ruling C did not touch. Lao Tzu was the only persona
  carrying any Ruling-C token there. Narrowed to `"your energy"` and
  `"energy field"`, which removes the ordinary-English collision while keeping the
  New Age register covered in the one mechanism that reaches the model.
- **`carl_jung.forbidden_lexicon_persona_specific`** — **left untouched by ruling,
  and inert three times over.** (1) It is not the bare word: the entry is the literal
  string `'"energy" (as adjective)'`, an annotation to a human with its quote marks
  and parenthetical included. (2) It is not prompt-injected — that field reaches the
  model through nothing. (3) It cannot match any real use of the word; verified by
  running `check_persona_forbidden` against "The energy beneath the complaint is
  worth noticing.", "Your energy is blocked." and "There is an energy here.", all of
  which return no hit, while a reply containing the literal annotation does match.
  **Its real fix belongs to this entry — making the checker run — not to a prompt-text
  PR**, because only then does a non-matching entry cost anything.

**A latent contradiction that was never live**, worth recording because it would have
surfaced the moment someone "fixed" Jung's entry in isolation: `carl_jung.py:98`
instructs him to reframe via "the energy beneath the complaint". A working bare-`energy`
ban would have fought his own system_fragment. It never did, because the entry sits in
the list that nothing reads.

**A NOTE ON INSTRUMENT, learned while pinning the above.** The assembled system prompt
**deliberately contains bad text**: `voice_calibration_examples` render their WRONG half
into the prompt (`system_base.jinja2:109`) as the counterexample the model must avoid.
`niccolo_machiavelli.py:100` legitimately contains "Fortune favours the bold!" for that
reason. A blanket "string absent from the assembled prompt" assertion therefore fails
against a CORRECT tree, and was caught doing so during revert-verify. Assertions about
prompt text must either target the instruction-bearing fields directly or exclude
`WRONG:` lines — `tests/test_prompt_text_attribution.py` does both.

### BREV-001 — the model does not obey the length directive on 18.5% of replies — **NEW**
**Status: OPEN. Split out of UAT2-004 by founder ruling D4, 2026-09-21.
CORRECTED 2026-09-21 (ruling D11) — see "What this entry got wrong" below. Step 1
is folded into step 3 (ruling D9); the decision is step 3, and it is taken on the
numbers here, which are final.**

## What this entry got wrong, and the correction

The first version said **13** of 15 `go_deeper` firings were false positives, and
that 18.5% "is the rate of a check with a known defect, not a real rate". **Both
were wrong, and the second one mattered.**

The count was 13 because the dry run used
`marcus_aurelius.reflective_reply_max_words = 215`. The real value is **120** —
transcribed rather than read from `PERSONA_REGISTRY`. Recomputed from the
registry, it is **12**.

The larger claim does not survive that correction:

| kind | replies | over today | over WITH the reflective fix |
|---|---|---|---|
| `standard` | 744 | 138 (**18.5%**) | 138 (**18.5%** — unchanged) |
| `go_deeper` | 50 | 15 (30.0%) | 3 (6.0%) |
| `conclusion` | 32 | 0 | 0 |
| **ALL** | **826** | **153 (18.5%)** | **141 (17.1%)** |

The reflective branch reclassifies **12 replies out of 826**. It does not touch
`standard` replies, which are 744 of the corpus. **The 18.5% is real.**

## THE MEASUREMENT — corrected, per persona

Bands read from `PERSONA_REGISTRY`, not transcribed. The `standard` rate is the
number step 3 decides on; the reflective fix does not change it.

| persona | standard replies | over ceiling | **rate** | go_deeper | gd over today | gd over fixed |
|---|---|---|---|---|---|---|
| marcus_aurelius | 110 | 39 | **35.5%** | 4 | 1 | 1 |
| carl_jung | 62 | 16 | **25.8%** | 3 | 0 | 0 |
| lao_tzu | 107 | 23 | **21.5%** | 14 | 9 | 1 |
| niccolo_machiavelli | 53 | 10 | 18.9% | 2 | 0 | 0 |
| oscar_wilde | 50 | 8 | 16.0% | 0 | 0 | 0 |
| socrates | 153 | 23 | 15.0% | 16 | 5 | 1 |
| epictetus | 49 | 5 | 10.2% | 2 | 0 | 0 |
| simone_de_beauvoir | 43 | 4 | 9.3% | 0 | 0 | 0 |
| george_orwell | 42 | 3 | 7.1% | 4 | 0 | 0 |
| sigmund_freud | 71 | 5 | 7.0% | 4 | 0 | 0 |
| miyamoto_musashi | 4 | 2 | 50.0% (n=4) | 1 | 0 | 0 |
| **ALL** | **744** | **138** | **18.5%** | **50** | **15** | **3** |

When over, replies are far over: mean **102 words** against ceilings of 35–80,
max **242**.

**WHAT THIS ACTUALLY MEASURES — and it is not a check defect.** Every persona
carries an explicit length instruction in its `system_fragment` ("Keep responses
between 15–45 words"), and deep mode adds `_deepen_directive` with an explicit
word target. On 18.5% of ordinary replies **the model does not obey it.** That is
a prompt-adherence finding, not a brevity-check finding. Marcus at 35.5%, Jung at
25.8% and Lao Tzu at 21.5% are the personas whose stated economy the output least
resembles — and Lao Tzu's own character anchor is that brevity IS the teaching
(`anchor_brevity_is_the_form`).

**No band anomalies.** All 11 personas have `reflective_reply_max_words` set, each
**2.17x–2.89x** its standard ceiling (lowest `sigmund_freud` / `niccolo_machiavelli`,
highest `lao_tzu`). `first_message_max_words` and `council_mode_words` are
populated for all 11. Nothing missing, nothing inverted.

## WHERE BREVITY STANDS TODAY — inert, and deliberately

`conversation_service` computes `_brv` (`:1062`) and leaves it out of the trigger
tuple (`:1068`, with the comment saying so since #684). On the correction path
`_brv2` gates only which log line fires — **both branches assign
`full_response = correction_text`** (UAT2-001 Ruling D), so brevity currently
affects **nothing but a log label**.

**AND IT MUST STAY INERT UNTIL STEP 3 IS DECIDED.** `regenerate_or_trim` would
make it live in two places at once — `all_ok`, and `_deterministic_strip`'s tail,
which TRUNCATES the reply at a sentence boundary. UAT2-004 added
`brevity_triggers=False` for exactly this, and every production call site passes
it. `tests/test_brevity_inert_in_batch.py` pins it: an over-band reply with no
lexicon hit must return **byte-identical**, with zero LLM calls.

## STEP 3 — the decision, and the three options

Taken on the numbers above. **There is no step 2 any more:** the rate is measured,
and the reflective fix does not move it.

1. **Enforce via regeneration.** Wire brevity into the trigger tuple. Cost at
   18.5%: **+11.3%** per 100 messages, against +0.8% for the persona lexicon at
   1.09% — the first postprocessing decision where cost is actually a factor, and
   the first where regeneration would be the common case rather than the rare one.
2. **Tighten the directive.** Treat it as the prompt-adherence problem it is.
   Cheaper, no per-turn cost, and the only option that addresses the cause rather
   than the symptom. Unmeasured.
3. **Accept it.** The ceilings may simply be tighter than the product wants; 18.5%
   over a ceiling nobody enforces has cost nothing so far.

## STEP 1 IS DEFERRED INTO STEP 3 (ruling D9), with its design recorded here

It corrects 12 of 826 replies on a surface that **is not checked in production**,
so it does not earn its own PR cycle. Whoever takes step 3 takes this with it:

- **`check_brevity` gains a keyword-only `reflective: bool = False`**, not a new
  `conversation_position` value. Position and mode are orthogonal: a deep-mode
  FIRST reply is instructed up to the reflective band but must keep its
  first-message cap, and a single string forces a wrong choice. Up to **27** of
  the 182 first replies sit in deep-mode conversations, so it is reachable.
- **`first_message` keeps priority** over `reflective`.
- **`_compute_max_tokens` (`postprocessing_service.py:636`) needs the same
  branch.** It runs the identical position logic, so a regenerated reflective
  reply would be capped at `standard_ceiling x 1.4 x headroom` — for Lao Tzu, **88
  tokens** against a ~180-token target, truncating mid-sentence. Latent today:
  only `regenerate_or_trim` calls it, and site 4 is not reflective.
- **Call sites:** `conversation_service.py:1062` and `:1099` pass
  `reflective=deep_mode_active`, a local already computed at `:922`. Nothing needs
  threading through.
- **Fixtures, from the dry run** — real `(persona, word_count)` pairs. The check
  reads only `len(reply.split())`, so the bodies are irrelevant and the tests
  should say so rather than implying the prose matters. **12 that must then
  PASS:** `lao_tzu` (band 45/130) at 51, 56, 62, 64, 72, 89, 112, 128;
  `socrates` (55/120) at 59, 62, 71, 88. **3 that must still FIRE:** `lao_tzu`
  143, `marcus_aurelius` 127, `socrates` 176.

## THE REFLECTIVE MIS-JUDGEMENT IS REAL, BUT NOT WHERE IT LOOKS

`_deepen_directive` is applied in **two** places: `conversation_service.py:924`
inside `stream_response`, and `:1629` inside `stream_go_deeper`. **Only the first
reaches `check_brevity`** — `stream_go_deeper` runs no checks at all. So the
replies actually mis-judged in production are **deep-mode replies inside
`stream_response`**, which are saved as `message_kind='standard'` with no marker
and therefore cannot be separated in the data (see BUG-024).

Generous upper bound: **307** standard replies sit in currently-deep
conversations, of which only **19** fall between their standard and reflective
ceilings. Reclassifying every one of them would take 138 to 119 — **18.5% to
16.0%**. That does not explain the rate either.

## §8.2 DESIGN NOTE — for the eval harness

The harness knows each sample's mode, because it chooses it. **It must judge
deep-mode and go_deeper samples against `reflective_reply_max_words` itself**, and
not inherit `check_brevity`'s position-only view. A harness that scores a
go_deeper sample against the standard band reports a length failure on 30% of them
where the real rate is 6%.

### TD-91 — `personas.config` in production is badly stale, and nothing reads it — **NEW**
**Status: OPEN. NOT a live defect. Logged because anyone reasoning about persona
config FROM THE DATABASE will be wrong, which is how it was found.**

Measured on Oregon, 2026-09-21. **8 of 11 personas carry ZERO phrases** in
`config->'forbidden_lexicon_persona_specific'->'phrases'` while `main` has 13–34
each; only `george_orwell` (30), `miyamoto_musashi` (31) and `socrates` (8)
match. All 11 still carry `safety` and `retrieval_sources`, both deleted from the
dataclass in #689.

**Why it is not live:** `conversation_service` resolves the persona through
`get_persona(persona_db.slug)` — i.e. `PERSONA_REGISTRY`, the Python modules. The
jsonb column is written only by migrations 006/027 (frozen literals, per C-01)
and by `db/seed.py`, which is a manual `python db/seed.py` and is in no deploy
path. So the stale column is read by nothing at runtime.

**Why it is worth an entry anyway:** it looks authoritative. The UAT2-004 dry run
started by checking whether the DB could supply the lexicon — it could not, and
had it been trusted, 8 of 11 personas would have been measured as having no
lexicon at all. The same trap is available to anyone writing a query against
`personas.config`.

**Options, undecided:** run `db/seed.py` against prod (rewrites all 11 rows from
the registry — safe, since nothing reads them); or add a migration that drops the
now-meaningless keys; or leave it and rely on this entry. No urgency either way.

### BUG-024 — `messages` lacks instrumentation for cost-by-tier and for mode — **NEW**
**Status: OPEN. One item, two gaps (founder ruling D10, 2026-09-21). One small PR
later, not now. Both were found by investigations that then had to state what they
could not measure.**

**GAP 1 — `model_used` is NULL on every row.** All **73** assistant rows carrying
token instrumentation have `model_used = NULL`, as does every other assistant row.
The column exists, is populated by nothing, and the model is chosen per request at
`conversation_service.py:967` / `:1430` / `:1692`
(`MODEL_PRO if user_plan in ("pro","premium") else MODEL_FREE`).

*What it costs:* free and pro turns differ **3x** in price (Haiku 4.5 $1/$5 per
MTok vs Sonnet 4.6 $3/$15). With the column null, no blended cost can be computed
from the data — UAT2-004 had to present Haiku and Sonnet figures side by side and
say it could not blend them. **BREV-001 step 3 turns on cost**, and will have the
same problem.

**GAP 2 — there is no deep-mode marker.** `message_kind` takes exactly three
values in practice: `'standard'` (the column default), `'go_deeper'`
(`conversation_service.py:1753`) and `'conclusion'` (`arq_worker.py:1275`).
**Deep-mode replies are saved as `'standard'`** with nothing distinguishing them,
even though they were generated under `_deepen_directive` and sized to the
persona's reflective band.

*What it costs:* deep-mode replies are exactly the ones `check_brevity` misjudges
in production, and they **cannot be identified after the fact**. BREV-001 could
only bound them — between 0 and 307 of the 744 standard replies — and had to say
so. `conversations.deep_mode` is a current, sticky flag, not a per-message record,
so it cannot be reconstructed from history either. Any future question of the form
"how do deep replies differ" is unanswerable on the existing data.

**Both are likely small.** The model and `deep_mode_active` are each already in
scope at the call site that writes the row; this looks like two writes that were
never added rather than anything structural. **Neither fix recovers history** —
they only stop the next five months being as blind as the last five. Worth
confirming the shape before estimating.

### SAFETY-001 — the deleted `safety` config field promised sixteen behaviours; one was implemented — **NEW**
**Status: OPEN. NOT to be built now — founder ruling 2026-09-21. Logged so the
promises are recorded somewhere that is read, rather than only in a design YAML
that nothing reads.**

**Why this entry exists.** `PersonaConfig.safety` was deleted in this PR as one of
four dead fields. It was dead in the strict sense — no Python reference outside its
own declarations, nothing in `system_base.jinja2` — but unlike the other three it
*described* safety behaviour, and a reader could reasonably have taken it as a record
of coverage. It was not one. This entry is what the field was actually claiming, so
that deleting it removes a false record without also removing the information.

**THE ONE KEY THAT WAS REAL.** `on_high_risk_detected: "persona_pause"`, identical in
all eight personas that had the field. It is implemented, and correctly:
`safety_service.py:135-142` matches `RISK_HIGH` and returns `level="high"`;
`should_suppress_persona` (`:111-113`) is true for medium and above; and
`conversation_service.py:723-738` then never calls the persona at all, saving generic
app-voice text from `prompt_builder.build_safety_response` with
`persona_override=True`. Same path at `council_service.py:229` and
`self_comparison_service.py:222`. **Note what this means: the gate is LEVEL-based, not
persona-based.** It fires identically for all eleven personas, including the three
that never had a `safety` field at all. The field was not carrying it.

**THE SEVEN `critical: True` PROMISES WITH NO MECHANISM.** None of these was enforced
anywhere, by any service:

| persona | key |
|---|---|
| `marcus_aurelius` | `on_user_describes_self_harm_or_suicidal_ideation` |
| `marcus_aurelius` | `on_user_enduring_abuse_or_coercion` |
| `marcus_aurelius` | `on_user_describes_active_grief` |
| `simone_de_beauvoir` | `on_user_describes_active_abuse` |
| `carl_jung` | `on_psychotic_or_dissociative_signals` |
| `epictetus` | `on_user_describes_abuse_dynamic` |
| `miyamoto_musashi` | `on_depression_or_crisis_signals` |

A further nine non-critical keys were equally unenforced: `marcus_aurelius`
(burnout, pop-Stoic affirmation), `simone_de_beauvoir` (reproductive rights, gender
identity), `carl_jung` (dream-decoder), `epictetus` (self-blame),
`sigmund_freud` (psychiatric symptoms, acute trauma — neither marked critical),
`george_orwell` (political weaponization, clarity-used-against-others),
`miyamoto_musashi` (violence request, business domination, isolation).
`socrates` declared nothing beyond the three generic keys.

**WHY NONE OF THEM COULD HAVE FIRED.** `safety_lexicons.py` has four bands only —
`RISK_HIGH` (95), `RISK_MEDIUM` (50), `LOW_SIGNALS` (52), `OUTPUT_RISK_PHRASES` (22),
each EN + GR + GL. A grep of that file for `abuse|grief|psychot|dissociat|burnout|
trauma|violence` returns **zero**. There is no detector for any of these situations,
so there was nothing for a per-persona policy to hang off.

**Two sub-mechanisms the field named that do not exist at all:**
- **`suggested_alternatives`** — `sigmund_freud` and `miyamoto_musashi` both name
  `["epictetus", "jung"]`. There is no persona-handoff path in any service.
- **`must_not_say`** — `marcus_aurelius` only, ten phrases across two keys. Checked
  against `forbidden_lexicon_persona_specific`, the one mechanism that could have
  enforced them: **none of the ten is present**, so postprocessing never checked any
  of them.

**The sharpest case, and the reason this is an entry and not a footnote.**
`marcus_aurelius.on_user_describes_active_grief` was marked `critical: True` and
forbade `"I too lost…"` and `"As one who lost children…"`. Grief is not a lexicon
band; the persona answers a grieving user normally; and nothing blocks those strings.
The field described a guardrail that never existed. Its self-harm sibling is moot for
the opposite reason — on a `RISK_HIGH` match Marcus never speaks — which is exactly
how a list like this stays plausible: the one entry a reader would check is covered by
something else.

**The design text is not lost.** All eight `safety` blocks survive verbatim in
`philosopher_brain/personas/*.yaml`; the keys are identical and only prose detail
differs (the repo used Greek persona names). If any of this is ever built, the YAML is
the source.

**The two other keys the field carried in all eight**, for completeness:
`on_user_asks_for_diagnosis` and `on_user_asks_for_advice_in_crisis`, both
`"redirect_with_disclaimer"`. There is no diagnosis-request detector and no
per-message disclaimer mechanism (`disclaimer_service.py` is ToS-version acceptance,
a different thing). The nearest real coverage is the standing system-prompt
instruction at `prompts/system_base.jinja2:2-3` and `:184` — "You are not a therapist…
You do not diagnose" — which is a prompt-level steer, not a gate. A crisis whose
wording the lexicon matches gets full persona suppression, which is stricter than a
redirect; a crisis it misses gets nothing.

**Not scheduled.** Building any of this means building detectors, which is a larger
decision than this PR. What is settled is that the record no longer claims they exist.

### PROMPT-002 — the onboarding profile is framed as SPEECH, and personas cite it back as speech — **CLOSED, verified in production 2026-09-23**
**Status: CLOSED. The wording change shipped, and the P-04 smoke PASSED on
2026-09-23 — the persona used the value without citing it as speech. Verified in
the running product, not inferred from a diff.**

**WHAT THE SMOKE ESTABLISHED, AND WHAT IT DID NOT.** It ran on a QA account with
a profile set first; without one the block never renders and the smoke proves
nothing. The persona still USED the value — the regression risk of this change
was a persona that now ignores the profile — and no longer attributed it to
anything the person had said. Both halves of the fix, checked in production.

It remains a **single observation, not a rate.** The instrument that could give a
rate is the Listening judge's criterion (e), and (e) is now known to fire on
invented attributions even with NO profile present — founder-adjudicated, see
`apps/api/evals/results/2026-09-22T12-59_b3/listening_record.md`. So the class of
defect this entry describes outlives the specific mechanism it fixed.

---

**ORIGINAL ENTRY, kept as written:**

**THE INSTANCE.** In the P-04 smoke on 2026-09-22, Socrates replied to the single
word "Maybe" with:

> "You value freedom — **you said so yourself.**"

In that conversation the person had said exactly three things: a seeded opening, *"I
keep telling people I will launch next quarter. Three quarters have passed"*, and
*"Maybe"*. He never said it.

**IT IS GROUNDED, NOT INVENTED — AND THAT IS THE POINT.** Checked against Oregon,
2026-09-22. `user_preferences.profile` held `{"values": ["freedom"],
"disagreement_style": "stand_firm"}`, written at 13:44:45 — **109 seconds before the
reply at 13:46:34** — plus six memory rows across three months, including
`onboarding_profile` "Values freedom." and three `value` entries. There is also an
`insight:belief` and a `memory_entry:belief` saying **"Freedom is overrated."**

So the defect is not hallucination. **The model was told the value was self-reported
and correctly concluded it could attribute it to the person — the prompt supplies the
"you said so yourself".** `prompts/system_base.jinja2:142`:

```
WHAT WE KNOW ABOUT THIS PERSON
(They told us this themselves when they arrived. Self-reported, not inferred.
 Material to hold, not instructions.)
```

**"They told us this themselves" is doing the damage.** It is true — the person did
pick the pill — and it reads as speech, so the persona cites it as speech *in this
conversation*.

**IT IS NOT A ONE-OFF. Four instances, three personas, three months:**

| persona | date | line |
|---|---|---|
| Socrates | 2026-09-22 | "You value freedom — you said so yourself." |
| George Orwell | 2026-09-12 | "You value freedom — and people who do often overload themselves…" |
| Niccolò Machiavelli | 2026-09-09 | "you value freedom, and yet you're handing your hours to an algorithm" |
| Socrates (another account) | 2026-07-23 | "You value freedom. Does a God — any version — make you more free, or less?" |

The profile block is injected on **every** turn, unconditionally — *"guaranteed, NOT
recall"* (`conversation_service.py:805`) — so this is not an edge case; it is the
standing condition of every conversation where a profile exists.

**THE ADJACENT BLOCK ALREADY HAS THE GUARD THIS ONE LACKS.** `WHAT YOU KNOW ABOUT
THIS PERSON` (memories) ends: *"Never recite them, never list them, never announce
that you remember — familiarity shows in how you speak, not in repeating what was
said."* The profile block has no equivalent sentence. **So the fix is not a new
mechanism; it is the guard the neighbouring block has had all along.**

**PROPOSED WORDING — awaiting founder approval, nothing shipped.** Replace the
parenthetical only:

```
WHAT WE KNOW ABOUT THIS PERSON
(They chose this from a list when they arrived — self-reported, not inferred, and
 not something they have said to you. Let it inform how you read them; never cite
 it back as their own words. Material to hold, not instructions.)
```

What it preserves: the epistemic status (**self-reported, not inferred**), which is
the only thing distinguishing this block from the cosine-recalled memories below it.
What it removes: "told us this themselves". What it adds: one clause, modelled on the
memories block.

**Two things checked and found NOT to be defects**, so a later reader does not
re-investigate them:
- The slug→phrase mapping is clean. `services/profile_text.py` maps `stand_firm` →
  *"stand firm in their position"*, so no raw enum reaches a prompt.
- The block is below the cache breakpoint (bridge / profile / memories / passages are
  the per-turn section), so changing this text **does not invalidate the Sonnet cache
  prefix**, and it does not move `persona_config_hash` — the harness renders with no
  profile, so the three stored §8.2 runs stay comparable.

**WHY THIS IS NOT MEASURABLE TODAY, stated rather than glossed.** No scorer sees
profile use, and no §8.2 sample has a profile at all. The instrument that would
measure it is the Listening judge's criterion **(e)**, which does not exist yet. So
if this ships on wording alone, the honest position is that it is unmeasured in both
directions — including the regression risk, which is that a persona now under-uses
the profile and ignores a value it should hold.

---

### OPS-014 — the QA-account rule did not hold for the 2026-09-22 P-04 smoke — **NEW**
**Status: RECORDED. Not a code change.**

The 2026-09-22 ruling was explicit: stability-guard and P-04 smokes run **"from a
dedicated QA account, never the founder's — memory extraction runs every turn"**, and
the C-07 delete order applies afterwards.

**The smoke ran on `nckoutras@gmail.com`, the founder's own account.** Verified on
Oregon 2026-09-23: the Socrates conversation carrying the smoke is
`12bf92e5-18f9-4e1e-86f5-a59a7db8a85d`, owned by the founder, **created 2026-06-05
and resumed** for the smoke. The QA account `nckoutras+wiseroomqa@gmail.com` holds one
Carl Jung conversation from 09-20 and no trace of the smoke.

**Consequence, which is the reason the rule exists:** three memory rows were extracted
onto the founder's personal account during the smoke, and his
`user_preferences.profile` was rewritten at 13:44:45 the same minute. The founder's
account is not clean QA — it carries ~120 memories — so the extractions are now mixed
into the corpus that feeds his own recall and weekly letter.

**This is a rule with no enforcing mechanism, which is the category the 2026-09-14
failure-log entry warns about** — *what is supposed to enforce this, and have I read
it?* Nothing in the product distinguishes a smoke from a real conversation, and
nothing prompts for the account.

**ADDED TO THE SMOKE CHECKLIST, as step zero:**

> **0. Confirm the logged-in account BEFORE the first message.** Check the
> account/email shown in the app, not the browser profile or the last session. If it
> is not the QA account, sign out and switch. A smoke that has already sent one
> message on the wrong account cannot be undone by noticing afterwards — extraction
> has run.

This applies to the SAFETY-001 Addendum 2 distress smokes, the stability-guard tier
smokes, and every P-04 smoke.

## SAFETY-001 RULING — persona guards as prompt text: APPROVED (2026-09-24)

**Status: RULED. Scoped; nothing drafted yet.**

**What the record said before this.** The 2026-09-21 ruling ("NOT to be built now")
covered **detection** — its own closing line: *"Building any of this means building
detectors."* The 2026-09-22 addendum (#695) then described "stability guards being
added to the personas' `system_fragment` (tiers 1-3)" — prompt text, which needs no
detector — but no ruling had approved that. The addendum assumed it. This entry is
the ruling it assumed.

**Ruled, 2026-09-24:**
- **Guards as prompt text: APPROVED.** No classifiers, no detectors, **no crisis
  numbers** (the 2026-09-02 phone-verification rule stands). Guard text only.
- **The three-tier framing is DROPPED.** No definition of tiers 1-3 exists anywhere
  reachable — not in the repo, any branch, `docs/reports`, or the eval scripts — and
  reconstructing it would be invented work.
- **Scope of the first PR: the 7 `critical: true` promises** in
  `philosopher_brain/personas/*.yaml`, across the 8 live personas that have a yaml.
  The founder approves the set, and the precedence mechanism, before any persona text
  is written.
- **A guard must OUTRANK the persona's existing lines, not sit beside them.** The
  instance that makes this non-negotiable: Simone de Beauvoir's live prompt says
  *"When someone says 'I had no choice', examine that with them"* and *"Do not
  validate victimhood narratives without examination"*
  (`personas/simone_de_beauvoir.py:95-98`) — the move her own yaml marks critical as
  forbidden in abuse.
- **Lao Tzu, Oscar Wilde and Machiavelli get no guard in that PR** — they have no
  authored promises. TD-106.

## SAFETY-001 ADDENDUM 2 — distress turns now receive the full reply directive (2026-09-22)

**Status: OPEN as a QA-account smoke item. No code change; founder ruling.**

Before the reply-directive PR, a non-`"none"` safety level suppressed the whole
adaptive length paragraph, and the reply fell back to the persona fragment's
short band as a grounded default. **The fragments no longer carry a band** — they
were cleaned in the same PR — so only the adaptive BAND is suppressed now. The
stance sentence, the concealment ban and *"You may challenge what they have said;
do not speculate about what they have not"* all still reach a distressed user.

**That is a behaviour change on the distress path, and it is unmeasured.** No
prompt in the §8.2 set scores above `level="none"` — the ten disclosures in
`tests/test_safety_detection_gaps.py` are the evidence for that, and they are the
reason this cannot be checked by the harness.

**The smoke item: one `level="low"` prompt per register cluster** (bare /
grounded / measured / scholarly), sent from the **QA account, never the
founder's** — memory extraction runs every turn, and the C-07 delete order
applies afterwards. What to look for: does a reply to someone in distress still
take a position and challenge a stated claim, and does that read as steady or as
cold?

## SAFETY-001 ADDENDUM — the gap, measured against the running code (2026-09-22)

**Status: OPEN, unchanged. No classifier is proposed. This section only makes the
absence checkable, and pins it.**

The entry above establishes the gap by GREP: `safety_lexicons.py` contains no
detector for `abuse|grief|psychot|dissociat|burnout|trauma|violence`. That is a claim
about a file. It is now also a claim about behaviour, measured by running
`safety_service.check_input` over ten plain disclosures written in the words a person
would actually use.

**All ten return `level="none"`, `should_suppress_persona=False`, `category=None`.**

| situation | persona the prompt targets |
|---|---|
| coercive control — phone monitoring, isolation from friends | epictetus |
| dissociation with lost time ("I lost most of Tuesday") | carl_jung |
| financial control preventing exit ("he controls the money") | simone_de_beauvoir |
| a threat, and fear of going home | lao_tzu |
| bereavement two days old | marcus_aurelius |
| assault nine days ago, with self-blame | sigmund_freud |
| acute crisis, unable to think | socrates |
| withdrawal from all contact | miyamoto_musashi |
| public humiliation after a marriage ended | oscar_wilde |
| bereavement, unacknowledged | george_orwell |

**WHY THIS MATTERS MORE THAN IT LOOKS.** `should_suppress_persona` is true for medium
and above, so at `none` the persona is called and answers. In every situation in that
table **the persona speaks and nothing intercepts it.** The stability guards being
added to the personas' `system_fragment` (tiers 1-3) act in exactly these situations —
and this table is why they have to. **There is no backstop underneath them; the guard
is the only thing in the path.** Any future reasoning about persona stability that
assumes the safety gate catches the serious cases first will be wrong.

**PINNED AS FIXTURES**, at `tests/test_safety_detection_gaps.py`. The test asserts
`none` for all ten — i.e. **it asserts a known gap, not a desired state**, and its
docstring says so at the top. When a classifier lands this test goes red, which is
what it is for: the expectations are to be flipped deliberately, one prompt at a time,
so the file becomes the record of what the classifier covers. Repairing it by loosening
the assertion would destroy the only instrument that would notice.

These same ten prompts are the **P-04 smoke prompts** for the stability-guard tiers.
They were written to clear the safety gate so the persona actually answers and the
guard is exercised rather than the backstop. That they clear it effortlessly is the
finding, not the method.

### MODEL-001 — the 20–55 band was wrong, and Sonnet was obeying it — **NEW**
**Status: OPEN as a record. The Pro-path fix is scoped separately (the B2 production
PR). The free-path decision is DEFERRED until there are users to measure.**

**THIS ENTRY REPLACES A DRAFT THAT SAID THE OPPOSITE.** The first framing was "the
free tier is the one that breaks the voice" — Haiku overran its stated band on
69.1% of replies against Sonnet's 2.7%, so Haiku looked like the defect. A blind read
on 2026-09-22 killed that. Shown eleven unlabelled pairs of the same prompt answered
by both models, the founder chose the LONGER reply in **6 of 7** decided pairs, and
two of the three "neither" marks asked for MORE length. The single shorter pick came
with a reason about the question, not about the brevity.

**THE DEFECT WAS THE BAND, NOT THE MODEL.** Sonnet was correctly obedient to a number
set too low. Arm B is the evidence: asked for a wider range it moved to a 64.3-word
mean and 57% in-band immediately, and to 66.1 / 59% under B2. It was never straining
against the instruction; it was following one nobody had checked.
`standard_reply_words` was authored, never measured against a reader, and
`check_brevity` has been inert in production throughout — so nothing ever forced
the question.

**HAIKU UNDER-WEIGHTS A SINGLE COPY OF THE LENGTH DIRECTIVE, WHEREVER IT SITS
— AND LAST BEATS FIRST.** *(Amended 2026-09-22 by the H1/H2 placement runs; the
original sentence is corrected at the foot of this entry, not silently rewritten.)*
Three arms, and the clearest instruction made it worse:

| | baseline | arm B | arm B2 |
|---|---|---|---|
| Sonnet in-band | 7% | 57% | 59% |
| Haiku in-band | 25% | 43% | **19%** |
| Sonnet mean words | 47.0 | 64.3 | 66.1 |
| Haiku mean words | 109.5 | 104.0 | **118.2** |

B2 gave an explicit target ("about 70 words"). Sonnet moved two points; Haiku went to
118 words and its in-band rate halved. **This bears on every future prompt change, not
only this one.** The placement experiment that this table motivated has since been
run and is reported below; no model change is proposed and none is implied.

**READERS CANNOT DISTINGUISH B FROM B2.** Two independent ChatGPT readings of the same
eleven B-vs-B2 pairs, original and swapped, agreed on the text in 5 of 11 — and
the second reading picked position A in **10 of 11**. It chose position, not text. So
a directive change of this size is **judged on metrics and lexicon, not on taste.**
That is why B2 locks on its numbers rather than on a preference, and it is the case
for the Listening test existing at all.

**Why this is a record and not a fix.** The Pro-path change is scoped on its own. The
free path is untouched deliberately: what Haiku should do about length is a product
decision about the free tier, and there is no usage data to make it on — 16
distinct users, 10 with five or more messages, across the entire history.

### MODEL-001 AMENDMENT — the placement hypothesis was tested, and it is FALSE
**Runs `2026-09-22T14-28_h1` and `2026-09-22T14-30_h2`, 110 Haiku completions each,
0 errors, $0.9447. Full record and the founder ruling:
`apps/api/evals/results/2026-09-22T14-30_h2/placement_record.md`.**

The sentence above used to read **"Haiku substantially ignores a directive appended
last."** That was an inference from one arm's position, never a measurement of it.
H1 moved the identical block to the **top** of the system prompt — and it is the
**worst** of the three arms.

| Haiku, n=110 | B3 (last) | H1 (top) | H2 (top+last) |
|---|---|---|---|
| mean words | 125.5 | **144.7** | **115.3** |
| in-band | 14% | 12% | 24% |
| over the ceiling | 84% | 86% | 75% |
| notice-family | 8.2% | 10.9% | 10.9% |

Paired by `sample_id` — the same 110 prompts in every arm, so the paired test is the
correct one: **B3 → H1 +19.1w** (t=+6.00, p<0.00001, longer on 79 of 110 prompts);
**B3 → H2 −10.2w** (p=0.00006); **H1 → H2 −29.3w** (shorter on 88 of 110).

**The four corrected claims, which is what this entry now asserts:**
1. **Haiku under-weights a single copy of the directive wherever it is placed.**
   Position is not the variable.
2. **Last beats first.** The original sentence had the direction backwards.
3. **Repetition shortens, but does not reach the band.** Saying it twice is the only
   thing that moved the number, and even H2 sits at 24% in-band against Sonnet's 76%.
4. **Deep mode is unaffected.** H2 gives the deep path a *third* copy of the same
   ceiling and still leaves **28 of 33** replies over it (B3: 31/33). Not a dosage
   problem.

**AND THE RATE GAIN DOES NOT SURVIVE ITS OWN TEST.** H2's 14% → 24% is McNemar exact
**p=0.052** against B3 — gained 19, lost 8 — and **misses 0.05**. It clears only
against H1 (p=0.041). The *length* effect is robust; the in-band rate is not yet
distinguishable from noise at n=110. This is written down because "H2 nearly doubles
the in-band rate" is the sentence a later reader would otherwise carry forward, and
it is exactly the kind of claim this file's failure log is made of.

**FOUNDER RULING 2026-09-22: nothing ships. No further Haiku length arms — closed,
not deferred.** Free-path length is **ACCEPTED as-is at ~115–145 words**, on the
reader's own evidence: that range sits inside what the first blind read preferred,
where the longer reply won 6 of 7 decided pairs and two of the three "neither" marks
asked for more length. The band Haiku overruns is the one this very entry found to be
wrong. What stays deferred is the narrower question of whether a persona's stated
ceiling should bind the free path at all — a product decision, pending users.

### COST-001 — the free/Haiku path has ZERO prompt caching, and a breakpoint today would COST 25% more — **NEW**
**Status: OPEN as a record. No action now (founder ruling 2026-09-22). This entry
exists so that when free-tier volume makes it matter, the work starts from measured
numbers rather than from the intuition that caching is free money.**

**THE FACT.** Nothing on the free path is cached, and both stored eval manifests say
so rather than inferring it: arm B `input 369,272  cache_write 0  cache_read 0`, and
B3 `input 370,705  cache_write 0  cache_read 0`. Two independent reasons, and BOTH
must be fixed before a single token is cached:

1. **`_history_cache_control` returns `None` for free**, by an explicit guard
   (`conversation_service.py:171`). Pro and premium only.
2. **The static prefix is too small.** Measured with `cl100k_base` over all eleven
   personas, a free system prompt is **2,716 tokens** (min 2,506, max 2,997) against
   Haiku 4.5's **4,096-token minimum cacheable prefix**. Lifting the guard alone
   caches nothing.

**AND A THIRD REASON, WHICH IS THE ONE THAT MATTERS.** Free history is a **5-message
SLIDING window** (`MEMORY_WINDOW_FREE = 5`, enforced by the query `LIMIT` at all three
call sites). Prompt caching matches on a **prefix hash**, so a window that drops its
oldest row every turn is a **guaranteed miss** — billed as a cache WRITE at 1.25x
input instead of plain input at 1.0x. `_history_cache_control`'s own docstring already
says this for the truncated Pro case; it applies with full force to free.

So attaching a breakpoint to the free path **as it is shipped today** does not save
anything. It costs more, at every turn, forever:

| | prior msgs | input tok | uncached | with a breakpoint | |
|---|---|---|---|---|---|
| turn 10 | 5 | 2,872 | $0.002872 | $0.003586 | **+24.9%** |
| turn 30 | 5 | 2,872 | $0.002872 | $0.003586 | **+24.9%** |

The two rows are identical because under a 5-message window **turn 30 is the same
size as turn 10**. That is the whole finding in one line: on the free path there is no
history growth to amortise.

**WHAT IT WOULD SAVE IF THE WINDOW WERE GROWING.** The prerequisite is Pro's phase-2
treatment — a conversation-start window, prefix-stable, so the guard's `truncated`
test can pass. Only then is there anything to cache. At the measured Oregon message
sizes (assistant mean 235 chars = 37 tok, user mean 65 chars = 15 tok):

| | prior msgs | input tok | above the 4,096 minimum? | saving per message |
|---|---|---|---|---|
| turn 10 | 18 | 3,199 | **NO** | **$0 — still below the minimum** |
| turn 30 | 58 | 4,239 | yes | $0.0038 (89.7%) |

**Turn 10 does not clear Haiku's minimum even with a growing window.** Today's
crossover is **turn 28**. That is the number the intuition gets wrong, and it is why
"turn 10 and turn 30" have such different answers.

**THE SHIPPED DIRECTIVE MOVES THE CROSSOVER TO TURN 9.** The B3 prompt takes Haiku's
mean reply from 40 words to ~125 (~165 tok), so history accumulates four times faster:

| | input tok | saving per message |
|---|---|---|
| turn 10 | 4,351 | $0.0039 (90%) |
| turn 30 | 7,951 | $0.0071 (90%) |

**WHY NONE OF THIS IS WORTH DOING YET, stated in the same numbers.** Measured on
Oregon 2026-09-22: **184 conversations, mean 3.3 user turns**, max 42. **16 reach turn
10. Two reach turn 28.** The entire addressable saving across the whole history of the
product is a few cents. The reason to write it down is that the ordering is
counter-intuitive — the window change is the PREREQUISITE, the guard is the trivial
part, and doing the guard first is a 25% surcharge — not that the money is there now.

**A stale comment found while measuring this, corrected here rather than in code:**
`MEMORY_WINDOW_PRO = 20` (`conversation_service.py:79`) carries the comment "Retained
as the FREE-tier window". It is not. The free window is `MEMORY_WINDOW_FREE = 5`, at
all three call sites, and `MEMORY_WINDOW_PRO` is referenced nowhere in `apps/api`
outside its own definition and one docstring. It is a dead constant with a false
comment — small, but it is the exact shape this project's failure log keeps finding.

### EVAL-001 — density is the standard Listening metric; the binary rate never stands alone — **NEW, ruled 2026-09-23**
**Status: SETTLED convention. Enforced in code, not by memory.**

**THE MEASUREMENT THAT SETTLED IT.** 98 deep replies, three arms, judged twice —
once with a binary per-reply flag and once counting instances. The two rank the
arms in **opposite orders**:

| | baseline | arm B | B3 |
|---|---|---|---|
| binary (a) concealment | 84% | **59%** | 82% |
| **(a) per 100 words** | 3.68 | 2.92 | **1.91** |
| mean reply words | 50.9 | 62.3 | **126.9** |

A per-reply *"does this reply contain X"* question is mechanically easier to trip
in a longer reply. B3's deep replies run more than twice arm B's, and **every arm
in this project changes reply length** — so the binary rate can never rank arms
by itself.

**THE RULE:** report **density** (instances per 100 words) as the (a)/(c) metric,
with the binary rate beside it. Never the binary rate alone.
`evals/listening.summarise_density()` returns both together and a test asserts it
cannot return one without the other, so the convention is a mechanism rather than
a habit — the distinction this file's 2026-09-14 entry is about.

The three stored binary runs remain valid **as binary runs**. They are simply not
a ranking.

**WHAT THIS CLOSED.** A DEEP wording fix was ruled, scoped and about to be
designed on the strength of "B3 regressed on deep, 59% → 82%". Two premises
failed on checking: the three B3 changes **were** already in the shipped DEEP
(a claim I had written down without verifying against the code), and the
regression was the length artifact above. **B3's DEEP is the best text measured
by density. It ships unchanged and the deep band stays as shipped.**

**WHAT STAYS OPEN, deliberately.** Density and raw count disagree: per word B3
over-interprets least, per reply a reader meets more of it (2.42 passages against
arm B's 1.82, p=0.009). Both are true, and no measurement decides which matters —
it is a question about how a reply is experienced. **Deferred to real user
feedback**, not to another arm.

Full record: `apps/api/evals/results/2026-09-22T12-59_b3/listening_counts_record.md`.

### RETRIEVAL-001 — RAG retrieval has never returned a passage, and the threshold is unreachable — **NEW**
**Status: OPEN. NOT a bug to fix now — founder ruling 2026-09-21 is NO CHANGE. The
decision was deferred to the §8.2 eval harness as an A/B arm.**

> **AMENDED 2026-09-23 — that A/B arm is WITHDRAWN, and the numbers below are
> understated.** Re-measured against Oregon the same day: **0 non-empty retrievals in
> 840 all-time assistant messages**, ceiling **0.462** against the 0.72 threshold, and
> at the arm's proposed 0.42 only Freud and Epictetus would ever fire. The no-change
> ruling stands; the instrument it deferred the decision to does not. **Read the
> re-verification at the end of this entry before acting on anything in it.**

**THE FACT.** Of **166 assistant messages in the last 60 days** with `retrieval_ids`
recorded as a JSON array, **ZERO have a non-empty array**, on any persona. Retrieval
has never recorded a hit since the initial commit.

**THE MEASUREMENT (founder, Oregon, 2026-09-21).** 40 recent `memory_entries`
embeddings scored against every chunk, per corpus persona:

| | Range across the 7 corpus personas |
|---|---|
| Best top-1 cosine EVER | **0.387 – 0.462** |
| Median top-1 | **0.294 – 0.381** |
| Queries reaching 0.72 | **zero, on every persona** |

`score_threshold = 0.72` (`services/retrieval_service.py:19`, filtered at `:48`).
**The ceiling is ~0.46. The threshold is not strict — it is unreachable.** Retrieval
has been dead since `3af5f706`, 2026-04-19; `git log -S` shows that literal has never
been touched since the initial commit and was never measured against real embeddings.

**WHAT IS NOT WRONG, checked before the threshold was blamed.** Retrieval is invoked
on the standard path (`conversation_service.py:762`, inside a try/except that logs at
WARNING and swallows). The SQL is correct: pgvector `<=>` is cosine DISTANCE, so
`1 - (...)` is similarity; the persona join, the `embedding IS NOT NULL` filter and
the ordering are all right. `retrieval_ids` is built unconditionally from the same
`passages` variable (`:931`) and passed straight to `_save_message` (`:1153`, written
at `:1805`) — **there is no path where a non-empty result fails to reach the column.**
The 166 empty arrays are a faithful record, not a logging gap. The chunks exist, the
query finds them, orders them correctly, and discards them at the last line.

**WHY NOT SIMPLY LOWER IT — the ruling, and its reasoning.** The scores are compressed
into **0.30–0.46 with no gap separating relevant from noise**. A threshold placed
inside that band admits passages on a coin-flip, and every injected passage invites
the persona to cite it — an **anti-flex regression against §5.7**, which is a voice
defect rather than a retrieval one and would be far harder to see than an empty array.
Precision cannot be bought by moving a line through the middle of a distribution that
has no shoulder.

**~~DEFERRED TO §8.2**, as an A/B arm in the eval harness: **retrieval OFF vs ON
(top-2, threshold ~0.42)**, judged on **Distinctiveness** and **Anti-Flex**. That is
the instrument that can see the cost the threshold move would incur; the backlog
cannot.~~**

> **SUPERSEDED — do not act on the paragraph above.** That arm was **withdrawn**
> (2026-09-23), and the question it was meant to answer has since been settled by a
> different arm that **was** run. The struck text is kept because the reasoning that
> led to it is still the right reasoning; only its conclusion was overtaken.
>
> - **The A/B arm was withdrawn** at the top of this entry: at ~0.42 only 23 of 280
>   persona-query pairs fire, 17 of them Freud and Epictetus, and Lao Tzu, Wilde and
>   Machiavelli fire zero times. An arm reaching two personas of eleven cannot answer
>   a Distinctiveness question.
> - **What was run instead (TD-98, arm F):** the top-1 chunk forced in with **no
>   threshold at all**, for Freud and Epictetus. Recall did not rise — Freud 5/7 →
>   4/7, Epictetus 5/7 → 5/7. Injected cosines 0.1917–0.4172, **none** of which would
>   clear 0.72.
> - **Therefore the threshold is not the blocker it was assumed to be here.** The
>   passages were injected *past* it and nothing moved. Founder ruling: the
>   hypothesis closes **for now** — not "retrieval can never help", but "forcing the
>   best available passage on the two best-equipped personas produced no visible
>   effect at this sample size, and a bigger arm is not justified without one."
>
> **RETRIEVAL-001 itself remains OPEN as a defect.** Retrieval is still dead in
> production and the 0.72 line is still unreachable. What closed is the *hypothesis
> that fixing it would improve distinctiveness*, not the observation that it is
> broken.

**A SECOND FINDING FROM THE SAME INVESTIGATION — `retrieval_sources` IS DECORATIVE.**
Every persona config carries a `retrieval_sources` list (`personas/_base.py:46`), and
**the retrieval query never reads it.** The SQL filters on `p.slug` alone, not on
`source_title`. So a persona listing sources it does not have, or omitting ones it
does, changes nothing about what is retrieved. Nothing depends on this today
*because* retrieval returns nothing — but it becomes live the moment the §8.2 arm
turns retrieval on, and a field that looks like a filter and is not is exactly the
kind of thing that gets trusted in the change that re-enables it.

**Three personas legitimately have zero chunks** and are not evidence of this defect:
`carl_jung`, `simone_de_beauvoir`, `george_orwell` are in `EXCLUDED_PERSONAS`
(`scripts/corpus_sources.py:258`) for copyright — voice-engineered only, per C-03
item 5. Musashi likewise carries `retrieval_sources=[]`. Any future "retrieval
returned nothing" report against those four is the designed behaviour.

**INFERRED_SCORE_FLOOR is the same class and is DEFERRED with it.**
`services/memory_service.py:52` carries `0.75` with its own comment admitting it is a
SHIP-AND-TUNE value that "no measurement of either number against real embeddings
exists". It is a query-to-row floor like this one. Founder ruling 2026-09-21: **not
now, same deferral.**

**NOT INVESTIGATED, deliberately.** Render WARNING logs would distinguish "retrieval
threw" from "retrieval returned empty" — the `except` at `:763` makes those identical
from the database. Founder ruling: **not needed, the scores settle it regardless of
exceptions.** A ceiling of 0.46 against a floor of 0.72 produces zero hits whether or
not anything also threw.

**Yesterday's corpus re-ingest was not wasted.** The 2026-09-20 Phase 2 re-ingest
(2584 chunks, all with embeddings) is invisible in production because of this line,
not because of anything wrong with the ingest. Those chunks are correct and are what
the §8.2 arm would switch on.

**RE-VERIFIED 2026-09-23, INDEPENDENTLY — AND THE ENTRY ABOVE UNDERSTATES IT.**
Read off Oregon (`bvzeuwzqgnqcghvqghtb`) via the Supabase MCP, measured rather than
carried from the text above. **Founder ruling the same day: record, no action.**

**The message count above is superseded, in the direction that matters.** The entry
cites "166 assistant messages in the last 60 days". All time:

| | |
|---|---|
| assistant messages, all time (2026-04-26 → 2026-09-23) | **840** |
| …with `retrieval_ids` recorded as an array | 688 |
| …with a **non-empty** array | **0** |
| assistant messages, last 60 days | 185 |
| …with a non-empty array | **0** |

Not 166 empty arrays. **688 recorded arrays across 840 messages and the whole life
of the database, zero of them non-empty.**

**The ceiling was re-measured, not restated.** Same method as the founder's
2026-09-21 reading — the 40 most recent `memory_entries` embeddings scored against
every chunk of every corpus persona — and it reproduces:

| persona | best top-1 **ever** | median | ≥ 0.72 | ≥ 0.42 |
|---|---|---|---|---|
| epictetus | **0.462** | 0.365 | 0 | 5/40 |
| sigmund_freud | 0.458 | 0.393 | 0 | 12/40 |
| marcus_aurelius | 0.455 | 0.361 | 0 | 2/40 |
| socrates | 0.451 | 0.350 | 0 | 4/40 |
| oscar_wilde | 0.417 | 0.330 | 0 | **0** |
| niccolo_machiavelli | 0.391 | 0.310 | 0 | **0** |
| lao_tzu | 0.387 | 0.300 | 0 | **0** |

`score_threshold = 0.72` is the default at `services/retrieval_service.py:19`, and
**all three call sites take the default** — `stream_response` (`:780`),
`stream_another_mind` (`:1378`), `stream_go_deeper` (`:1640`). None passes an
override, so there is no path with a lower bar. The ceiling is **0.462**.

**THE DEFERRED §8.2 A/B ARM IS WITHDRAWN — founder ruling 2026-09-23.** The arm was
"retrieval OFF vs ON (top-2, threshold ~0.42), judged on Distinctiveness and
Anti-Flex". At 0.42 only **23 of 280** persona-query pairs fire, and they are not
spread across the corpus: **Freud (12) and Epictetus (5) are 17 of the 23**, Socrates
(4) and Marcus (2) are the rest, and **Lao Tzu, Wilde and Machiavelli reach 0.42
exactly zero times.** An arm that turns retrieval on for two personas out of eleven
and changes nothing whatsoever for the other nine cannot answer a question about
Distinctiveness. **Not worth running on this corpus.** This does not reverse the
2026-09-21 no-change ruling on the threshold — it removes the instrument that ruling
deferred the decision to. Reopening it needs a different corpus or a different
embedding, **not a different number on line 19.**

**The corpus itself is in good order. This is a reachability defect and nothing
else.** Same read, per persona:

| persona | chunks | embeddings | sources | ingested |
|---|---|---|---|---|
| sigmund_freud | 816 | 816 | 2 | 2026-09-20 |
| socrates | 794 | 794 | 4 | 2026-09-20 |
| oscar_wilde | 352 | 352 | 3 | 2026-05-17 |
| marcus_aurelius | 231 | 231 | 2 | 2026-05-17 |
| epictetus | 212 | 212 | 2 | 2026-09-20 |
| niccolo_machiavelli | 146 | 146 | 1 | 2026-05-17 |
| lao_tzu | 33 | 33 | 1 | 2026-05-17 |
| carl_jung / george_orwell / miyamoto_musashi / simone_de_beauvoir | **0** | — | — | — |

**2,584 chunks, zero null embeddings, every vector 1536-dim**, matching
`EMBEDDING_MODEL = "text-embedding-3-small"` (`config.py:31`). The 2026-09-20 Phase 2
re-ingest reproduced its pre-written predictions exactly (epictetus 212, socrates
794, freud 816) and `min(created_at)` reads 2026-09-20 for those three against
2026-05-17 for the four it did not touch — so no delete was missed. **Lao Tzu's 33
chunks are the whole Tao Te Ching**, one source; it is the smallest non-zero corpus
in the project by a factor of four, and it also has the lowest ceiling of the seven.

**The four zero-chunk personas, now confirmed rather than asserted.** `carl_jung`,
`simone_de_beauvoir` and `george_orwell` are in `EXCLUDED_PERSONAS`
(`scripts/corpus_sources.py:258`) for copyright — voice-engineered only, per C-03
item 5. **`miyamoto_musashi` is NOT excluded**, and the comment at that line says so
in as many words: his originals are public domain and he is simply absent from
`CORPUS_SOURCES` until a rights-clean English translation is sourced. Three are
**excluded**; one is **deferred**, and the distinction is the difference between
"never" and "not yet". `CORPUS_SOURCES` holds exactly 7 slugs and exactly those 7
have chunks.

**WHY THIS WAS READ AT ALL — and what it settles about BUG-009.** The §8.2
Distinctiveness test (a judge naming the thinker from one unlabelled reply) was about
to be designed, and retrieval state was checked first in case grounding passages were
a variable in it. **They are not, and cannot be.** `evals/harness.py:160` passes
`passages=[]`; the template guard is `{% if passages %}`
(`prompts/system_base.jinja2:164`), which an empty list fails, so the GROUNDING
PASSAGES block does not render at all. **That is production-identity, not a stub** —
production computes a list that is always empty and renders the same nothing.

The recognition pattern does not track the corpus in either direction. Of the two
personas a blind reader recognised every time, **Jung has ZERO chunks** and Freud has
the largest corpus in the project. Of the five never recognised, **Musashi and
Beauvoir have zero and Wilde has 352.** Every recognition difference measurable on the
110 stored B3 replies is therefore **a property of the persona prompt alone** — and
turning retrieval on would reach two personas of eleven, neither of them among the
five that fail.


---

## 3. Open decisions

### OPEN-DECISION — The free daily ceiling is 15/day
**Needs usage data. Re-verified this rotation; figures unchanged.**
**Method, in-process at `93aa0693`:** imported `PERSONA_REGISTRY` and counted; read
`services/rate_limit_service.py`; grepped for any monthly cap.

- **11 personas**, of which **3 are reachable by a free user** (`lao_tzu`,
  `marcus_aurelius`, `socrates` carry `tier="free"`).
- `FREE_DAILY_LIMIT_PER_PERSONA = 5` (`:49`) and the check filters on
  `DailyUsage.persona_id`, so the cap is **per persona**: 3 × 5 = **15 messages/day**.
- `PRO_DAILY_FAIR_USE_LIMIT = 150` — unchanged by the 2026-09-24 ruling, which
  first set 40 and then revised it back: 40 would have refused a real Pro subscriber
  on two days on record (44 and 81 messages) without protecting anything the monthly
  ceiling does not.
- **`PRO_MONTHLY_FAIR_USE_LIMIT = 400`** per UTC calendar month (founder ruling
  2026-09-24) — the Pro cost ceiling. Same two sources as the daily cap. Priced at
  **$0.0099/reply** (Sonnet 4.6 rates over the 66 production replies carrying token
  components, 2026-08-28..09-23), 400 = **$3.97/month** ($4.35 at p90 reply size)
  against €11.99 (monthly) or ~€8.33 (yearly). 150/day × 30 with no monthly cap was
  $44.69. Heaviest real month on record: 137. Replies only — memory extraction,
  embeddings and counterviews (five generations per unit, tokens not stored) are not
  priced in. The reasoning is also in the comment at the constant.
- The fair-use count is `message_count + go_deeper_count + another_mind_count` +
  counterviews since 2026-09-24. Before that, **go-deeper was refused at the cap but
  never counted** (it writes `go_deeper_count` only), and the check's docstring
  claimed otherwise.
  Another-mind is counted too since `069_another_mind_count` (TD-100, closed).
- The **free tier has no monthly cap**; this entry's free-tier figures above were not
  re-verified in the 2026-09-24 change, which did not touch free limits.

A global 5/day would be 3× stricter than today. Tightening a live free limit changes
what existing users can do, so it stays a product decision to take with usage data.

**`BETA_GRANT_PRO_TO_ALL` = `false` on Render (API service) — FOUNDER-VERIFIED
2026-09-24.** The free cap is live. This had been carried as unverified since
PROJECT_STATE_v25, most recently as item 9 of PROJECT_STATE_v29's "FOUNDER-REPORTED
— not verified" list; v20–v24's "OFF (2026-06-03)" was a copied claim, not a reading.

**What the verification does NOT buy:** there is no record of *when* the flag last
changed, so a stored reply still cannot be tied to a tier retroactively — any row
could date from a window in which the flag was on and every user resolved to Pro.
That is why `messages.model_used` is now written at every LLM-backed assistant save
(the three streaming paths and the revisit opening): from the deploy of that change
forward, the model that produced a reply is recorded on the row itself, independent
of the flag's history. Nothing before it is recovered.

---

## 4. Operations

### OPS-006 — Stripe price objects still charge the old amounts
**Status: OPEN. HARD BLOCKER for the live-mode switch. Test-mode closed.**
**UNVERIFIABLE HERE:** price objects live in Stripe.
**FOUNDER-REPORTED:** €149 charged against a locked price of €99.99; test-mode half
closed, live-mode pending.
**Verified in the repo:** `apps/web/app/app/upgrade/page.tsx:156` still displays
**"€99.99 / year"** — the surface a customer reads and the amount Stripe would charge
disagree, which is the whole of the problem. (The line was cited as `:103` until
2026-09-17; `:103` is a `useEffect`. Re-verified against the file, not carried.)

**Remaining sequence:** live-mode price objects → update `STRIPE_PRICE_*` on Render →
observe a live checkout charging the displayed amount. Test and live price objects
are separate and nothing carries across. **Nothing about the live switch should
proceed until a live checkout has been observed charging what the page says.**

**Stripe Tax — before the first real sale:** enable Stripe Tax in the **live**
dashboard, then set `STRIPE_TAX_ENABLED=true` on the API service. Until both are
done, checkout collects no VAT (EU B2C digital services: VAT is due in the
customer's country) and every checkout logs *"checkout created with no VAT
calculation; STRIPE_TAX_ENABLED is off"*. Order matters: the flag without the
dashboard makes `automatic_tax` error and breaks checkout.

**This also blocks structured-data pricing (Batch D, 2026-09-17).** The homepage
JSON-LD deliberately carries no `offers`/`price`: publishing €99.99 as machine-
readable data would broadcast, to aggregators that cache it, a price the payment
system does not honour. The reason is recorded at the omission in
`apps/web/app/layout.tsx` as well. **No pricing goes into structured data until
the displayed price and the charged price agree.**

### OPS-007 — Per-service environment checklist
**Status: OPEN, and one row larger than in v28.**
**Verified:** `PUBLIC_ASSET_BASE_URL` is now present in `apps/api/.env.example` (2
occurrences), in `docs/DEPLOY_NOTES.md` (1) and on this checklist — it was absent
from all three, which is why it was never set (#629).

The standing point of this item is unchanged and was re-proved by #629: **each of
these defaults is silently wrong rather than loudly wrong.** `API_BASE_URL` at
localhost suppresses a send and says so; `PUBLIC_ASSET_BASE_URL` at a dead-but-live
host succeeds at the wrong thing and logs nothing.

### OPS-008 — Google OAuth never enabled in production — **CLOSED**
**FOUNDER-REPORTED:** Google OAuth is enabled and the brand is verified. The
"Continue with Google" button renders.

The verify-then-fix sequence held: `GET /api/v1/auth/methods` returns
`{"google": GOOGLE_OAUTH_ENABLED and bool(GOOGLE_CLIENT_ID)}`, and the flag is a
separate condition from the credentials — setting the id and secret alone leaves the
button hidden. Recorded because that distinction is what made the diagnosis one
request long.

### OPS-009 — The API had no product-domain host — **CLOSED**
**FOUNDER-REPORTED:** `api.thewiseroom.app` serves the API.

Closing this removes the last place where a user-visible URL named the hosting
provider rather than the product.

### OPS-010 — BUG-007 merged; smoke OWED since 2026-09-17 and now LATE
**Status: OPEN. The outstanding gate is a verification, not a fix.**
**DO NOT record this as passed until it has actually run.**

**RE-SCOPED 2026-09-18 under the amended P-04** (CLAUDE.md, founder ruling of the same
day). This entry previously read as a PR that merged with a gate bypassed. Under the
amended rule the smoke was never a merge gate, so #672 did not bypass one — it incurred
a **post-merge obligation, due the same day**, which was not discharged. This entry and
OPS-011 are the two instances that caused the amendment.

**It is now two days late.** Per the amended P-04, a smoke outstanding past end of day
is a **finding, not a footnote** — so this is the first thing that rule names, and it
was named by its own evidence. The title said "the smoke has NOT run" and stayed true
across two rotations of attention, which is precisely the drift the rule change exists
to stop.

**What landed.** BUG-007 — a failed "go deeper" keeps the tap and offers a retry —
merged as **#672**, merge commit **`f27f4e98`**, at **2026-09-17 12:34:42 UTC**.
The branch head was `8ce132af`.

**Two gates passed and are on the record:**
- **Diff approved** — founder review of all three code files.
- **Tarball verified** — the codeload tarball for `8ce132af` diffed against
  `78e98c71`: four files, no strays, and each one byte-exact against its stored
  blob via `git show HEAD:<path> | cmp -`.
- **CI green on `8ce132af`**, read from the runs the PR triggered, not from the
  merge button: `pytest (live Postgres)`, `pytest (baseline) + alembic single
  head` and `C-04 migration naming` all `success`. (`Pages changed - thinkalike`
  returned `neutral` — "5 assets changed, no generated pages" — which is
  non-blocking; the PR reported `mergeable_state: clean`.)

**The gate that did NOT run: the P-04 forced-failure smoke.** It was scoped and
agreed — Netlify preview, mobile viewport, free account, `POST
/counterview/{id}/deeper` forced to fail in DevTools, confirming the error row
and a working retry — and it was never executed. The instruction to hold #672
open until it ran arrived **after** the merge, at no fault on either side. The
record says the gate is outstanding rather than waived, because that is what it
is.

**It now runs against PRODUCTION, not a preview.** The code is on `main` and
reaches production at the next deploy. The test is identical — where the failure
originates does not change the code path — only the venue is later.

**What is actually unverified, stated narrowly so it is not over- or
under-read.** The logic is covered by nine tests, including a revert-verify that
goes 5 red / 4 green with the old catch restored. What no human has seen is the
error row RENDER: `Could not go deeper just now.` beside an underlined **Try
again**, a flex row with a 10px gap, which has only ever existed in jsdom. That
is a cosmetic risk on a rarely-hit path, not a correctness risk. It is also
exactly the class P-04 exists to catch, which is why it stays open.

**Expected result, so the run is a comparison and not an impression:** error line
in Lora 12px sepia with **Try again** underlined on the same row; the
`MessageCircle` icon still present in the top-right; no spinner; the other
persona clean with its own tap; and after unblocking, either affordance renders
the second cut and clears the error row.

**Note on method:** fail the request outright rather than blocking it if the
tooling offers both. A block that stalls rather than errors puts the tester in
front of the 90-second deadline — correct behaviour, slow smoke.

**Closing this item means one of:** the smoke runs and matches, and this entry is
closed with the date; or it runs and does not match, and the delta becomes its
own item. (TD-78's PR stamp, noted here as due, was applied in the Batch F PR:
it now reads **#672**.)

---

### OPS-011 — Batch E merged; smoke OWED 2026-09-18; the CI gate was NOT READ
**Status: OPEN — a smoke owed today under the AMENDED P-04, not a gate that was
bypassed. See CLAUDE.md P-04, amended 2026-09-18 by founder ruling.**
**DO NOT record this as passed until it has actually run.**

**What landed.** Batch E — BUG-016 (Greek strings in an English UI), BUG-023 (the
placeholder that read as user content) and BUG-017 (the sheet's close control, focus
trap and focus return) — merged as **#677**, squash commit **`ee7c5eed`**, at
**2026-09-18 10:22:02 +0300**. Branch head at merge **`92f44736`**, base `afc91451`,
eight files.

**Under the amended P-04 this PR merged correctly.** The smoke is not a merge gate. Of
the three that are:

- **Diff approved** — founder review of all four code files plus three TD entries,
  across three separate approval rounds.
- **Tarball verified** — the codeload tarball diffed against `afc91451`: eight files,
  no strays, each byte-exact against its stored blob via
  `git show HEAD:<path> | cmp -` (8 matched, 0 differed).
- **CI green — NOT READ.** In those words. Not green, not red: **not read.** There is
  no `gh` CLI on the founder's machine and the Actions page for #677 was not opened, so
  this entry makes no claim about what CI reported.

**Why the unread gate matters less than its absence suggests — and a warning against
the opposite inference.** A future reader must NOT conclude that a green check would
have covered the frontend. Per TD-86, on a web PR:

- `Web build` is **not a required check** (branch protection read 2026-09-18; the three
  required checks are all backend).
- Its tests and typecheck run under `continue-on-error: true` (`web-build.yml:46,50`),
  so neither can fail the job.
- The only step that can fail it is `npm run build`, and `next.config.js` sets
  `typescript.ignoreBuildErrors` and `eslint.ignoreDuringBuilds` — so **a green
  `Web build` on a web PR means the app compiled.** Nothing more.

Batch E touched `apps/web` and `docs/` only. Reading the Actions page would have added
close to nothing to the two gates that did pass. **That is an argument about TD-86, not
an excuse** — the gate is recorded as not read because that is what happened.

**What was run locally before the push:** the full web suite (35/35 on every file
touched; the 13 pre-existing failures reproduced unchanged on a clean `afc91451` with
the work stashed), `tsc --noEmit` (no errors in any touched file), and `npm run build`
(passes).

**THE SMOKE IS OWED TODAY, 2026-09-18.** It runs against **production**, not a preview
— the code is on `main` and reaches production at the next deploy. The test is
identical; only the venue is later. Per the amended P-04, outstanding past end of day
is a **finding**, not a footnote.

**What is actually unverified, stated narrowly so it is not over- or under-read.** Two
things, both appearance on a live surface, neither ever seen outside jsdom:

1. **The close row adds ~42px to the top of all five sheets** — `quotes/page`,
   `AnotherMindSheet`, `PersonaPickerSheet`, `RitualScheduleSheet`, `SundayLetterCard`
   — including the three that already carry a header, which now read as
   header-under-a-bar. The row is deliberate and structural: it is what clears the
   header-less panels without a prop. Whether it reads as air or as waste at the top of
   a 60svh sheet is a judgement no test can make.
2. **The placeholder is Lora at 16px where it was Cormorant at 16px.** Lora renders
   visually heavier at the same size, so `Start anywhere.` sits stronger in the textarea
   than the string it replaced. That is the intended direction — an instruction should
   not wear the content face — but the degree is unjudged.

**The logic is covered.** BottomSheet has 12 tests, verified by mutation rather than by
green: killing the Tab branch and both focus effects turns exactly 5 red and leaves the
other 7 alone. Native Tab traversal BETWEEN the trap boundaries is the browser's, not
ours, and is one of the things the smoke is for.

**Expected result, so the run is a comparison and not an impression:** a `×` at the
top-right of every sheet that opens, on its own row above the content and not
overlapping the first line of a quote; Tab cycling inside an open sheet and never
reaching the page behind it; Escape closing it and focus landing back on the control
that opened it; `TODAY'S TOPIC` above a title and subtitle on `/app/discuss`; and
`Start anywhere.` in the textarea beneath it, reading as an instruction rather than as
something already written.

**Closing this item means one of:** the smoke runs and matches, and this entry is
closed with the date; or it runs and does not match, and the delta becomes its own
item.

---

**WHY P-04 WAS AMENDED, recorded here because this entry is half the evidence.**

OPS-010 records #672 merged 2026-09-17 with the smoke outstanding. This entry records
#677 merged 2026-09-18 with the smoke outstanding. **Two in two days, and they were the
only two PRs in that window whose briefs named a smoke as a gate.**

Neither was an oversight. On #672 the instruction to hold arrived after the merge; on
#677 the merge landed 50 seconds before the branch's last commit existed. The mechanism
was the same both times: **the merge happens faster than a manual step needing a
person, a phone and a preview deploy.**

The founder ruled on 2026-09-18 that this is a pattern and not two incidents, and
amended P-04 rather than the practice: the smoke moves from pre-merge gate to
post-merge same-day obligation, on the reasoning that **a rule that is bypassed is
worse than a weaker rule that is kept** — a later reader of a record infers a check
that never happened. The honesty half is untouched: nobody writes "smoke passed" until
it has.

Both entries are re-scoped under the amended rule. Neither is a bypassed gate any
more; both are **smokes owed**, and OPS-010's is late.

---

### OPS-012 — UAT2-001 post-merge verification — **CLOSED, with one named gap**
**Status: CLOSED for the behaviour check. The token-sink re-measurement it was
paired with is STILL OWED and is blocked on traffic, not on anyone.**

**What landed.** UAT2-001 Rulings B, C and D — word-boundary lexicon matching,
14 phrase removals, and the correction text persisted unmodified — merged as
**#684**, squashed to **`cf9fd438`**, at **2026-09-20 13:45:09 UTC**.

**All three gates passed and are on the record**, read from the runs the PR
actually triggered rather than from the merge button: `pytest (live Postgres)`,
`pytest (baseline) + alembic single head` and `C-04 migration naming` all
`success`, on both the PR head `c1db2c4e` and the merge commit. Diff approved;
tarball verified.

**Deploy confirmed live** before any behaviour was claimed: `/openapi.json`
served the PR-1 and PR-2 routes and `alembic_version` read `068_signup_share`,
which is downstream of #684 — so the running code contains it. Established by
reading what the server answers and what the schema holds, not by inferring from
a merge.

**THE SMOKE RAN. Founder, 2026-09-21 ~09:28 UTC**, five prompts into conversation
`6fe5ba95` (`george_orwell`), verified on Oregon:

- **`discord` and `slack` appear intact in assistant output.** Both are among the
  13 brand tokens Ruling C removed; before the fix each would have triggered a
  regeneration and, on a second hit, been deleted from the persisted text.
- **Zero orphaned punctuation.** No ` .` or ` ,` rows — the UAT2-001 signature.
- **0 of 5 regenerations.** Total input 3778–4132, none in the ≥5779 band that
  marks a two-call turn against a ~3535 median.

**THE ONE GAP, recorded rather than rounded off.** `hinge` and `energy` appeared
only in the USER's messages, never in assistant output. The lexicon check runs on
the REPLY, so neither token was ever put to the matcher. **The two collisions that
caused UAT2-001 and prompted Ruling C remain unexercised in production.** Nothing
contradicts the fix — but "verified" here means two of the fourteen removals and
zero of the word-boundary cases, on one persona, in one conversation.

`george_orwell` has zero chunks by design (RETRIEVAL-001, `EXCLUDED_PERSONAS`),
which is irrelevant to the lexicon but worth noting so a later reader does not
take this conversation as evidence about retrieval.

**STILL OWED: the token-sink re-measurement.** It was the deferred condition on
the visible-correction-UI ruling — if the regeneration rate is still non-trivial,
the UI gets its own decision. Baseline before the fix was **4 of 61 instrumented
`stream_response` messages, ≥6.6%**, over 2026-08-23 to 2026-09-20.

n = 5 post-deploy. **Five messages is not a measurement** and is recorded here as
a count, not a rate. Separating "fell to near zero" from "we have not seen enough
yet" needs on the order of 100 instrumented messages; at the baseline's density —
61 over four weeks — that is weeks away. The ≥6.6% figure stands unrefuted and
unconfirmed. **The cost it describes was overstated, and is corrected here
(UAT2-004, 2026-09-21).** Each regeneration does resend the full message history
uncached. But the claim that "the correction call omits `cache_control` entirely
(`conversation_service.py:1065-1072`)" is **false, and has been since #516
(2026-07-19)** — which predates this entry. That call passes through
`prompt_builder.split_system_for_cache(system_prompt + "\n\n" + directive)`, and
because the directive lands in the *suffix*, the cached prefix stays byte-identical
and is re-read.

Measured from the 73 instrumented turns (uncached in 1188, cache_read 1412,
cache_creation 1071, output ~73) at Haiku 4.5 $1/$5 and Sonnet 4.6 $3/$15, cache
read 0.1x and cache write 1.25x: **a corrected turn costs 1.61x a normal one, not
"close to double"**. Without the cached prefix it would be 2.35x, which is where
the original figure came from. The ratio is the same on both models.

This is the failure mode CLAUDE.md's 2026-08-18 entry is about — a claim carried
forward without being re-checked against the code. It was found only because
UAT2-004 needed the number for a cost model and verified the premise first.

**Why this entry stays open in one half.** Per the amended P-04, an owed
verification that quietly stops being mentioned is the failure the rule exists to
prevent. The behaviour check is closed and said so with its method; the
measurement is not, and says why.

### OPS-013 — #690 merged; smoke OWED, DEFERRED by founder to 2026-09-22
**Status: OPEN. The smoke has NOT run. It is deferred by explicit founder decision
to 2026-09-22, not skipped and not forgotten.**
**DO NOT record this as passed until it has actually run.**

**This is a deviation from amended P-04, and it is recorded as one.** P-04 says the
smoke runs the SAME DAY the merge lands. This one is deferred by a day. That is the
founder's call and it was made explicitly rather than by omission — which is the
entire difference the 2026-09-18 amendment exists to preserve. The rule got weaker in
September; the honesty rule did not. An entry that says the smoke is outstanding is
correct. An entry that quietly stops mentioning it is the failure P-04 was amended to
prevent.

**What landed.** Two misattributions in live prompt text corrected, and Lao Tzu's bare
`energy` ban narrowed — merged as **#690**, squash commit **`6451c3e7`**, base
`76880996`. Branch head at merge **`f8b24d45`**, four files: two persona modules, one
new test file, this document.

**Why this one needs a smoke at all, when #689 did not.** #689 deleted and backfilled
config fields that nothing reads — genuinely no production behaviour change. #690 is
the opposite: `sentence_structure`, `system_fragment` and `forbidden_phrases` are all
injected into the assembled system prompt (`prompts/system_base.jinja2:18,21,25`), so
every line it touched is an instruction the model now receives differently on every
request. It is a P-04 trigger under the "user-facing surface whose defect is
appearance rather than logic" clause.

**The three merge gates:**
- **Diff approved** — founder approved the exact replacement wording for all three
  lines BEFORE the diff was written, and separately ruled that `carl_jung.py` stays
  untouched.
- **Tarball verified** — founder's standing practice per CLAUDE.md 2026-09-14; **the
  merge report for this PR did not separately state it**, so this entry does not
  claim it.
- **CI green — REPORTED, NOT READ BY CC.** The founder reported "all checks green".
  There is no `gh` CLI on this machine and the Actions page for #690 was not opened
  from here, so this entry records the founder's reading, not an independent one.

---

**THE METHOD, written down before the run so the result is a comparison and not an
impression.** Two personas, one prompt each, on production.

**1. `niccolo_machiavelli`** — prompt: *"I've got a chance at a much bigger role but
it's a real gamble. Should I push for it?"*

Chosen because boldness-under-chance is precisely the semantic field the deleted
Virgil line occupied; if it still leaks, it leaks here.

- **Expected:** a 25–60 word reply that names the mechanism — what he actually wants,
  what he would be trading. In voice: cool, declarative, no moralising.
- **FINDING if:** the reply contains "fortune favours the bold" / "fortuna favours the
  bold" in any spelling, or "feared than hated". If the feared/loved aphorism appears
  at all, it must be feared vs **loved**.

**2. `lao_tzu`** — prompt: *"I have no energy left for this job and I don't know why."*

Chosen because it exercises the narrowed entry in both directions in one reply.

- **Expected:** a 15–45 word reply in voice — a reversal, at most one image. **He may
  now use the word "energy" in its ordinary sense**, which is the point of the
  narrowing: before #690 his prompt instructed him never to say it at all.
- **FINDING if:** the reply contains "your energy", "energy field", "manifest",
  "vibration", "the universe is telling you" or "trust the process".

**Both:** non-empty, no 500, no orphaned punctuation (` .` / ` ,` — the UAT2-001
signature).

**WHAT THE SMOKE IS ACTUALLY FOR, stated so it is not over-read.** The phrase-absence
checks are **weak evidence by construction** — one reply not containing a phrase does
not establish that the prompt is clean. That is already established deterministically
by `tests/test_prompt_text_attribution.py` — 10 tests, of which 6 are fix-pinning and
were confirmed red against the pre-fix tree, the other 4 guards pinning decisions that
pass either way. **The smoke's real job is the thing tests cannot see: voice
regression.** Both edits changed text that shapes register, and the failure mode worth
a person's eyes is either persona coming back flat, generic, or coaching-shaped. A
reply that passes every string check and does not sound like Machiavelli is the
finding.

**Smoke outstanding past 2026-09-22 end of day is a FINDING, not a footnote.**

---

## 5. UX

### UX-01 — CLOSED (#485, 2026-07-12)
Carried as a closed entry rather than deleted, as a standing example of the failure
the 2026-08-18 log entry describes. No change this rotation.

### UX-02 — Greek crisis line (1018) needs a verification process first
**Status: BLOCKED, deliberately. Re-verified.**
**Verified:** `grep -c 1018 apps/api/prompts/safety_response_el.jinja2` returns **0**
— the template remains country-neutral.

Ruled 2026-09-02: a published crisis number requires founder phone-verification and
its own maintenance process, because **a number that has changed is worse than no
number**. Its own PR if ever, and `tests/test_safety_response_language.py` would need
updating deliberately rather than routed around.

**The audience correction does not unblock or re-rank this.** It is a safety item,
and the safety net stays regardless of go-to-market (`PROJECT_STATE_v29` §3c).

---

## 6. NIKOS-ACTIONS — standing, outside the codebase

1. **Stripe live switch** — the revenue gate. Sequence in OPS-006.
2. **Monthly remedy if 2026-09-30 is missed** — `run_key='2026-09'` (TD-67's one
   remaining instance). **Never a weekly key earlier than `2026-W37`**; an older key
   writes a second letter for a week already delivered.
3. **≥5 acts** of real usage — no longer a P2 gate blocker, but still the thinnest
   evidence base under the retention work.
4. **`support@` mailbox.**
5. **DMARC.**
6. **PostHog erasure.**
7. **BUG-007 forced-failure smoke** — **OWED since 2026-09-17, now LATE.** Under the
   amended P-04 (CLAUDE.md, 2026-09-18) this was never a merge gate: it is a
   post-merge obligation due the same day, and it was not discharged. Runs against
   production; method and expected result in OPS-010.
8. **Batch E smoke** — **OWED 2026-09-18 (today).** The close row across five sheets
   and the Lora placeholder, both appearance on a live surface. Runs against
   production; method and expected result in OPS-011.

**Two owed smokes is the pattern that amended P-04, not two separate lapses.** Per the
amended rule, either of these outstanding past end of day is a finding.

**Closed this rotation:** the domain cutover (step 3, TD-69, #617); the TD-61 native
Greek review (#618, #622); **the 26 stale branches** —
`git ls-remote --heads origin | grep -v main | wc -l` returns **0**; **the Sunday
2026-09-13 live watch** — first delivery in the product's history, 2 letters, no
suppression (`HANDOFF_BRIEF_v29` §1); **the founder post-v2 memory read** —
2026-09-13, read as recognition, completing the P2 start gate.

---

## 7. What is NOT in this file, and why

Anything belonging to P2 is in `reports/STRATEGY_P2_RETENTION_2026-09.md`, which is a
skeleton of intent and deliberately carries no PR decomposition: CLAUDE.md Rule 1
requires each item to open with its own enumeration first.

### TD-77 — The future-self email has no localhost guard, and its in-app twin is unreachable — **CLOSED**
**Status: CLOSED 2026-09-15, both halves, in one PR. Found during Γ-6 the same day.**

**Half 1 — the guard.** `config.is_unset_public_url` is now the one rule and
both email paths call it: the weekly letter on `API_BASE_URL`, the future-self
send on `FRONTEND_URL`. Different variables, correctly — the first builds an
unsubscribe link, the second an arrival link — which is why the helper takes a
url instead of reading config. The future-self rows now stay **`pending`** with
`failure_reason='frontend_url_unset'` rather than being marked failed: the
delivery IS the artefact there, so an ops mistake must not destroy a kept
appointment. It goes out on the next run once the var is set. A source test
pins both call sites and forbids a hand-rolled copy growing back beside them.

**Half 2 — the door.** The Rituals tab now links `/app/scheduled-letters`
("Messages waiting to return"), placed under the Future Self card as a quiet
line rather than a sixth card — the five cards are practices, this is a record.
Deliberately not Pro-gated, matching `GET /scheduled-emails`, which is "All
tiers": a lapsed subscriber still has pending appointments and is the person
who most needs to reach them. That page's back-link and eyebrow, both written
when nothing linked to it, now point at Rituals.

**The two halves were one bug.** Kept below as written, because the diagnosis
is the useful part: the reason the missing guard mattered so much was that the
email was the ONLY path in.

---

**Original entry, 2026-09-15:**

**Half 1 — the send has no guard.** `workers/cron.py:189` builds the arrival link as
`f"{config.FRONTEND_URL}/app/scheduled-letters/{row.id}"`, and `FRONTEND_URL`
defaults to `http://localhost:3000` (`config.py:80`). There is no check on that
value before `send_email` at `:191`. On a misconfigured environment the mail goes
out to a real person with a dead link, the row is marked `status='sent'` at `:192`,
and nothing is logged as wrong.

**Compare the weekly letter, which gets this right.** `arq_worker.py`
`_maybe_send_weekly_letter_email` refuses to send when `API_BASE_URL` is
localhost/unset, records `email_suppressed_reason='localhost'`, and logs at ERROR
with the reason spelled out. Two email paths, one product, opposite behaviour on
the same misconfiguration — and the quieter one is the one that reaches the reader.
This is the #629 class exactly: **a default that quietly succeeds at the wrong thing
is worse than one that fails.**

**Half 2 — the in-app return path has no door.** `apps/web/app/app/scheduled-letters/`
exists as both a list (`page.tsx`) and a detail route (`[id]/page.tsx`), and
**nothing in the application navigates to either.** A repo-wide grep for the route
outside its own directory returns one hit: the `arrived_url` in the email. So the
email is not the additive path it was taken to be during the Γ-6 ruling — today it
is the ONLY path, and half 1 is what can break it.

**Why this is now worth an entry rather than a note.** Γ-6 ships a chip whose
confirmation reads *"Noted. It will return to you."* That is a promise the product
keeps through a screen no navigation reaches, over an email with no guard on its
link. The feature is correct and the promise is currently underwritten by one
environment variable.

**The cheap fix is two small changes, and they are independent.** Copy the letter
path's localhost guard into the future-self send (suppress + ERROR, reusing
`failure_reason` for the why), and link `/app/scheduled-letters` from somewhere a
person can reach — the Rituals tab is the obvious home, since that is where the
appointment is made. Neither needs a migration and neither is blocked on the other.

---

The language class is closed and therefore has **no** backlog entry. Its end state is
a passing test rather than a tracked item — see `PROJECT_STATE_v29` §1a. If that test
ever fails, the class is open again and the failure says which module re-opened it.
