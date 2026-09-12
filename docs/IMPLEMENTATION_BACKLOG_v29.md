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

### TD-67 — Catch-up cannot repair the very first run of a job
**Status: OPEN. One-off, with a known manual remedy. LIVE THIS WEEKEND.**
**Verified by source read:** `workers/letter_dispatch.py:318` selects
`func.min(JobRun.started_at)` per `job_name` as the catch-up floor. If the very first
scheduled run never opens a row at all, the next catch-up sees no history and skips.

Applies exactly twice: weekly on **Sunday 2026-09-13**, monthly on **2026-09-30**.
From the second period onward, catch-up covers a fully missed run. Remedy: the manual
command in the rulings doc's Ops section with `run_key='2026-W37'` or `'2026-09'`.

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
Verified: the only `alembic upgrade head` anywhere in the repository is
`conftest.py:212`, and it runs from the **seeded 048 state**; the upgrade that
runs against an empty database is `conftest.py:210`, which stops at 048. So the
defect lives strictly between 048 and head, in exactly the interval the fixture
steps over. If a future migration adds the same shape — reading rows back that
no migration inserts — it fails the same way, and nothing warns first.

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
**Verified in the repo:** `apps/web/app/app/upgrade/page.tsx:103` still displays
**"€99.99 / year"** — the surface a customer reads and the amount Stripe would charge
disagree, which is the whole of the problem.

**Remaining sequence:** live-mode price objects → update `STRIPE_PRICE_*` on Render →
observe a live checkout charging the displayed amount. Test and live price objects
are separate and nothing carries across. **Nothing about the live switch should
proceed until a live checkout has been observed charging what the page says.**

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
2. **Sunday 2026-09-13 live watch.** The first run under the PR-C period arithmetic
   and the gate on P0 #6. Queries and suppression reasons in `HANDOFF_BRIEF_v29` §1.
   **Note TD-67: the first run has no automatic catch-up.**
3. **Manual W37 remedy if needed** — `run_key='2026-W37'`. **Never a weekly key
   earlier than `2026-W37`**; an older key writes a second letter for a week already
   delivered under the pre-PR-C arithmetic.
4. **≥5 acts** of real usage before the P2 gate reads.
5. **`support@` mailbox.**
6. **DMARC.**
7. **PostHog erasure.**
8. **The founder post-v2 memory read.** Dimitris is unavailable, so this is
   explicitly a **founder** read — see `reports/STRATEGY_P2_RETENTION_2026-09.md`,
   where the bias is named rather than hidden.

**Closed this rotation:** the domain cutover (step 3, TD-69, #617); the TD-61 native
Greek review (#618, #622); **the 26 stale branches** —
`git ls-remote --heads origin | grep -v main | wc -l` returns **0**.

---

## 7. What is NOT in this file, and why

Anything belonging to P2 is in `reports/STRATEGY_P2_RETENTION_2026-09.md`, which is a
skeleton of intent and deliberately carries no PR decomposition: CLAUDE.md Rule 1
requires each item to open with its own enumeration first.

The language class is closed and therefore has **no** backlog entry. Its end state is
a passing test rather than a tracked item — see `PROJECT_STATE_v29` §1a. If that test
ever fails, the class is open again and the failure says which module re-opened it.
