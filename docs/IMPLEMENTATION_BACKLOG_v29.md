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

**Founder-reported context, recorded as such:** surfaced by **UAT-1 BUG-021**
during the **14-16 September 2026** incident window. That artifact is NOT in this
repository — a case-insensitive grep for `BUG-021` across `docs/` and `apps/`
returns nothing at `78e98c71` — so this line records who reported it and when,
not a document a reader here can open. If UAT-1 is filed somewhere durable, link
it here.

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
- `PRO_DAILY_FAIR_USE_LIMIT = 150` (`:107`).
- A grep for `monthly_limit|FREE_MONTHLY|per_month` across `apps/api` returns
  **nothing**. The July intent of "5/day + 30/month, server-side" has a per-persona
  daily cap and **no monthly cap at all**.

A global 5/day would be 3× stricter than today. Tightening a live free limit changes
what existing users can do, so it stays a product decision to take with usage data.

**Caveat, not verified here:** `BETA_GRANT_PRO_TO_ALL` defaults to `False` in
`config.py`. If enabled on Render, every user resolves to Pro and the free cap
applies to nobody.

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
