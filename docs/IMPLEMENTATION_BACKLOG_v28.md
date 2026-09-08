# GREAT MINDS — Implementation Backlog v28

> **Verification SHA:** `e840053ceaadfba3b12c21164f98e949152c4ff4`.
> **Date:** 2026-09-08.
> **Companion documents:** `PROJECT_STATE_v28.md`, `HANDOFF_BRIEF_v28.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md`. v27 files preserved byte-identical.

---

## ⚠️ HOW TO READ THIS FILE

Every item below was **re-verified against the code at `076f74b7`, and re-confirmed
at `e840053c`**,
with the method stated. An item that says "Verified" was checked here; an item that
says UNVERIFIABLE HERE or FOUNDER-REPORTED was not, and says which.

**A carried item is not evidence.** The 2026-08-18 failure-log entry exists because
items survived rotations by being copied rather than re-checked. Nothing in this file
was copied forward without re-running its check — and this rotation that discipline
again paid, twice: see `PROJECT_STATE_v28` §5a and §5c.

**A count in this file states the COMMAND that produced it**, not just what was
counted. Every number below names its definition and its scope — "45 tests across
four files in `tests/db_live/`", "210 entries across the four bands", "9 matching
sites using `.lower()` or `re.IGNORECASE`" — because a bare number is not a
verifiable claim.

This rotation demonstrated the cost twice on one figure. The docstring "22 swallowing
handlers" is **correct, and was correct at every SHA** — 14+8 at #587, 13+5+4 at #611
and today, the composition changing while the total held. It was attacked twice here
and produced two wrong answers: first **21**, by reading it as ARQ tasks plus cron
jobs (12 + 9); then **24**, by reading it as `exc_info=True` sites — the right
definition — but measuring with a bare `grep -c` that counted two *comments* about
`exc_info=True` as if they were call sites. The founder caught both before the PR
opened.

**A definition in prose is still ambiguous; the command is the definition.** "`exc_info=True`
call sites under `workers/`" reads as unambiguous and is not, because it says nothing
about comments. `observability.py` now carries the exact pipeline
(`grep -h … | grep -vc "^[[:space:]]*#"`) beside the number. When re-verifying
someone else's count, run their command; if they did not leave one, establish what
they were counting before concluding they were wrong — a plausible neighbouring
definition yields a plausible neighbouring number, and the substitution looks like a
fix. See `PROJECT_STATE_v28` §5c and §6.

---

## 1. Tech debt

### TD-57 — Live-DB integration tests: PARTIALLY PAID
**Status: OPEN, materially reduced. Was "no live-DB tests exist at all".**
**Verified:** `pytest tests/db_live --collect-only` reports **45 tests** across four
files — `test_job_run.py`, `test_letter_catch_up.py`, `test_letter_failed_status.py`,
`test_memory_recall_and_cascades.py`. `backend-ci.yml:100` runs them as a separate
`db-tests` job against a Postgres service container.

Ruling #10 required this before any v2 PR touching DDL or recall SQL, and #600
delivered it. The DDL and cascade behaviours that mocks cannot express — a real
`ON DELETE SET NULL`, a real unique-index collision, a real CHECK constraint refusing
`'failed'` — are now asserted against a real database.

**What remains open:** these run **in CI only**. There is no local Postgres in the
development environment, so revert-verify legs that need a migrated schema cannot be
executed locally and CI is the sole authority — as the letter rulings doc records for
D-1's leg (a). The broad body of router and service tests still mocks the session.

### TD-58 — Remove `passlib` and `bcrypt`
**Status: OPEN. Standalone chore. Unchanged from v27, re-verified.**
**Verified:** `requirements.txt` lines 10–11 still pin `passlib==1.7.4` and
`bcrypt==4.0.1`; a grep for `passlib|bcrypt|CryptContext|pwd_context` across
`apps/api/**/*.py` returns **zero importing files**. Dead since #586 removed
`hash_password` / `verify_password`.

Its own PR, because removing them changes the Docker build and P-02 says one logical
change per PR.

### TD-59 — No test pins the privacy policy against the implemented rights
**Status: OPEN. Unchanged, re-verified.**
**Verified:** the policy is **Version 1.3, effective 2 September 2026**
(`apps/web/app/legal/privacy/page.tsx:24`). Generated `openapi()` in-process:
`/api/v1/auth/me` exposes **DELETE, GET and PATCH**, and `/api/v1/auth/me/export`
exposes **GET** — so erasure, access, rectification and portability all have routes.

Policy and code agree today; nothing enforces that they keep agreeing. #588 had to
amend the policy because it promised a soft delete that was never built, and that
mismatch survived because a legal document and an endpoint share no test.

### TD-60 — Postprocessing voice checks are English-only
**Status: OPEN. Unchanged, re-verified.**
**Verified:** `services/postprocessing_service.py` has **9** matching sites using
`.lower()` or `re.IGNORECASE`, and **zero** occurrences of `casefold` or
`unicodedata`.

#589 fixed the safety gates; these are the *voice-quality* checks. A Greek reply
cannot trip the forbidden-lexicon check at all. Not a safety hole — `check_output` is
a separate path and was fixed — but persona-voice enforcement silently does nothing
for the product's first audience.

### TD-61 — The Greek safety lexicon has never been read by a Greek speaker
**Status: OPEN. Still the highest-value review item in this file.**
**Verified by importing and counting:** **210 entries across the four bands**
(LOW_SIGNALS 30, OUTPUT_RISK_PHRASES 33, RISK_HIGH 88, RISK_MEDIUM 59), of which
**73 contain Greek script**. This reproduces v27's count exactly.

They pass their tests and produce no false positives against this repository's
English prose. None of that is a substitute for a native reader checking that the
phrases are what a distressed Greek speaker actually types. Two entries were flagged
by the author as most likely to over-trigger — `αυτοκτονια` and `αυτοκτονω`, bare
noun and verb forms that will fire on academic or third-person discussion — and are
in deliberately, under the over-trigger ruling.

### TD-62 — No export completeness guard
**Status: OPEN. Unchanged, re-verified.**
**Verified:** `tests/test_data_export.py` contains no completeness assertion; every
test there is shape or exclusion.

If a future PR adds a table carrying `user_id`, nothing fails and the export silently
under-reports — a GDPR Art. 15 defect that looks exactly like a working export.
**Proposed shape:** enumerate mapped classes carrying `user_id` and assert each
appears in the payload **or** in a documented exclusion set.

### TD-63 — The fair-use refusal path has never rendered
**Status: OPEN. Unchanged, re-verified.**
**Verified:** grepping the web test suite for `fairUseMessage`, `fair_use_limit` and
`FAIR_USE_COPY` returns **zero hits**. `PRO_DAILY_FAIR_USE_LIMIT = 150`
(`services/rate_limit_service.py:107`). The backend refusal is covered; the thing a
person would actually see is not, in tests or in production.

The cap needs 150 messages in one UTC day, which the v27 document reports as 1.85×
the heaviest usage day ever recorded — a figure measured against the production
database in #11's Step-1 and **not re-read in v27 or here**. So its first execution
will be a real Pro subscriber.
**Cheap remedy:** set the constant to 2 on a staging account for one session and look
at the toast.

### TD-64 — A `db_live` test commits a row it never cleans up
**Status: OPEN. New this rotation. Low severity, will bite exactly once.**
**Verified by code read:** `_open_job_run` calls `await db.commit()`
(`workers/letter_dispatch.py:223`). `test_opening_a_fresh_period_still_inserts_normally`
(`tests/db_live/test_letter_catch_up.py:319`) calls it with `run_key="2026-W40"` and
takes no cleanup action, so the committed `job_run` row survives the `db` fixture's
outer-transaction rollback.

Harmless on CI, which gets a fresh Postgres service container per run. On any
persistent database the row is permanent, and a second run meets
`uq_job_run_name_key` and takes the collision path instead of the insert path — so
the test would be exercising a different branch than its name claims. **Remedy:**
delete the row in the test, or give it a unique per-run key.

### TD-65 — `generate_weekly_mirror_task` carries the D-2 pattern
**Status: OPEN. New this rotation. Out of scope until a mirror catch-up is wanted.**
**Verified by code read:** the task is defined at `workers/arq_worker.py:1096` and
computes `period_end = datetime.now(timezone.utc)` with `period_start` derived from
it at `:1106-1107` — the period comes from execution time, not from an argument.

This is the same shape as the letter defect D-2 fixed: dedup is by
`(user_id, period_start, kind)` via `uq_mirrors_user_period_kind`, so a catch-up run
on a different day would compute a different `period_start`, miss the index, and
write a **second mirror for an overlapping period**. It is latent rather than live —
there is no mirror catch-up — and it must not be "fixed" opportunistically. It
becomes real work the day someone wants mirrors to self-repair, and then it is the
same fix PR-C made: pass the period in.

Recorded in the letter rulings doc's "Observed, not fixed" section with the
instruction to log it here.

### TD-66 — The legacy per-tag fallback is now tolerance, not an active path
**Status: OPEN as a documentation/decision item, not as a defect.**
**Verified:** the bank is 360/360 weighted, so `_pill_axis_sums`'s fallback branch is
unreachable for every real question. It is exercised only by tests that inject a
synthetic bank.

The code is correct and cheap, and the scope pin's
`assert len(sp._BANK) - len(weighted) == 0` means a new unweighted question cannot
ship silently. **Recommendation: keep it**, as deliberate tolerance for a future
question authored before its weights are. What matters is that it is now named as
tolerance — an unreachable branch that nobody has decided to keep is the thing that
becomes a stale claim two rotations later.

### TD-67 — Catch-up cannot repair the very first run of a job
**Status: OPEN. One-off, with a known manual remedy.**
**Verified by code read and by the rulings doc (R8a):** the catch-up floor is
`min(job_run.started_at)` per `job_name`. If the very first scheduled run never opens
a row at all, the next catch-up sees no history and skips.

This applies exactly twice: weekly on **Sunday 2026-09-13**, monthly on
**2026-09-30**. From the second period onward, catch-up covers a fully missed run.
**Remedy** is the manual command in the rulings doc's Ops section, invoked with
`run_key='2026-W37'` or `'2026-09'`. It closes itself after those two dates.

### TD-68 — The stale-`running` threshold is a bare constant
**Status: OPEN as documentation. Do not tune.**
**Verified by code read:** `STALE_RUNNING_AFTER = timedelta(hours=2)`
(`workers/letter_dispatch.py:55`), used at `:178` to decide whether a `running` row
is a crash to reclaim or a job still in flight to leave alone.

Two hours is a judgement about the longest a dispatch could legitimately take, and no
measurement supports or contradicts it yet. It is recorded here so the number is
visible rather than buried. **It should not be tuned until a real run has been
timed** — lowering it risks reclaiming a live job and double-dispatching a period,
which is the exact failure the unique index exists to prevent.

### TD-69 — `NEXT_PUBLIC_BASE_URL` points at a stale host in both branches
**Status: OPEN. New this rotation. VERIFY-THEN-FIX — the defect is not confirmed.**
**Verified in the repository; NOT verified in the deploy environment.**

Two halves, both read from source:

- **(a)** `apps/web/.env.production` is **tracked in git** — it predates the
  `.gitignore` `.env.*` rule, which only ignores untracked files — and sets
  `NEXT_PUBLIC_BASE_URL=https://thinkalike-q9pldzo20-nckoutras-projects.vercel.app`,
  a stale preview host. It contains **no secrets**; both variables in it are
  `NEXT_PUBLIC_*`.
- **(b)** `apps/web/app/layout.tsx:40` reads
  `process.env.NEXT_PUBLIC_BASE_URL ?? 'https://philosopher.app'` — so the hardcoded
  fallback is *also* a domain the product no longer uses.

That value is the **only** consumer of the variable in the web app, and it feeds
`metadataBase`, which builds the absolute `og:image` URL that #574 shipped. So a
shared link's preview image may be resolving against a dead host.

**Why this is verify-then-fix and not a confirmed defect:** an env var set in the
deploy platform's dashboard overrides the file, and the deploy platform was not read
this rotation. Check the dashboard value first.
**Fix, when confirmed:** a separate chore PR — untrack `apps/web/.env.production` and
change the fallback to `https://thewiseroom.app`. **Not in this rotation.**
**Cross-reference:** the domain-cutover checklist in `HANDOFF_BRIEF_v28` §1. **The
cutover completed 2026-09-08** (FOUNDER-REPORTED): `NEXT_PUBLIC_BASE_URL` is
dashboard-set on Netlify and the app redeployed, so the live `metadataBase` is now
correct and **the user-visible half of this item is closed**. What remains is
hygiene: the repository still carries a tracked file and a hardcoded fallback that
both name dead hosts, and they will be believed by the next person who reads them or
by any build where the dashboard value is absent. That is the chore PR.

---

## 2. Open decisions

### OPEN-DECISION — The free daily ceiling is 15/day
**Needs usage data. Not a gap-fill. Re-verified this rotation, figures unchanged.**

**Method, in-process at `076f74b7`:** imported `PERSONA_REGISTRY` and counted;
read `services/rate_limit_service.py`; grepped for any monthly cap.

- **11 personas**, not 12. **3 are reachable by a free user** — `lao_tzu`,
  `marcus_aurelius`, `socrates` carry `tier="free"`; the other eight are `tier="pro"`.
- `FREE_DAILY_LIMIT_PER_PERSONA = 5` (`:49`) and the check filters on
  `DailyUsage.persona_id`, so the cap is **per persona**: 3 × 5 = **15 messages/day**.
- A grep for `monthly_limit|FREE_MONTHLY|per_month` across `apps/api` returns
  **nothing**. The July intent of "5/day + 30/month, server-side" has a per-persona
  daily cap and **no monthly cap at all**.

A global 5/day would be 3× stricter than today, not 12× as an older figure implied.
Tightening a live free limit still changes what existing users can do, so it remains
a product decision to take with usage data.

**Caveat, not verified here:** `BETA_GRANT_PRO_TO_ALL` defaults to `False` in
`config.py`. If it is enabled on Render, every user resolves to Pro and the free cap
does not apply to anyone.

---

## 3. Operations

### OPS-006 — Stripe price objects still charge the old amounts
**Status: OPEN. HARD BLOCKER for the live-mode switch. Test-mode closed.**
**UNVERIFIABLE HERE:** price objects live in Stripe, not in this repository.
**FOUNDER-REPORTED:** €149 was charged against a locked price of €99.99; the
test-mode half is now closed and live-mode is pending.

**Verified in the repo:** `apps/web/app/app/upgrade/page.tsx:103` still displays
**"€99.99 / year"** — so the surface a customer reads and the amount Stripe would
charge disagree, which is the whole of the problem.

**Remaining sequence:** live-mode price objects → update `STRIPE_PRICE_*` on Render
→ observe a live checkout charging the displayed amount. Test and live price objects
are separate and nothing carries across. **Nothing about the live switch should
proceed until a live checkout has been observed charging what the page says.**

### OPS-007 — Per-service environment checklist
**Status: OPEN. New this rotation. Cheap and overdue.**
**Verified by reading `config.py` and every read site:** three variables were set on
the API and missed on the worker this cycle, and **each default is silently wrong
rather than loudly wrong**:

| Variable | Default in `config.py` | What the default does |
|---|---|---|
| `SENTRY_DSN` | `""` (line 49) | `observability.py:195` returns early — **error reporting is off and nothing says so** |
| `API_BASE_URL` | `http://localhost:8000` (line 68) | `arq_worker.py:1316` sees `localhost` and takes the **email-suppression** path; unsubscribe links at `:1341` would be unreachable anyway |
| `FROM_EMAIL` | `noreply@philosopher.app` (line 43) | `email_service.py:20` and `arq_worker.py:1083` send **from a domain the product no longer uses** |

These three are the checklist's first three rows. **The rule the checklist encodes:
the worker is a separate service and inherits nothing from the API.** Any variable
added to one must be explicitly considered for the other, and the answer recorded
even when it is "not needed there".

The deeper fix, not in scope here, is that a default which silently degrades is worse
than no default. `SENTRY_DSN=""` disabling reporting is defensible for local
development; `FROM_EMAIL` defaulting to a dead domain is not.

### OPS-008 — Google OAuth has never been enabled in production
**Status: OPEN. New this rotation. VERIFY-THEN-FIX.**
**FOUNDER-REPORTED:** the "Continue with Google" button does not render on `/auth` in
production.
**Verified in code:** the button is gated by `GET /api/v1/auth/methods`, which returns

```python
{"google": config.GOOGLE_OAUTH_ENABLED and bool(config.GOOGLE_CLIENT_ID)}
```

(`routers/auth_oauth.py:33`). Both routes exist in the generated `openapi()` —
`/api/v1/auth/oauth/google` and `/api/v1/auth/oauth/google/callback` — so the code is
shipped and dormant, not missing.

**Three settings must all be right, and all three default to off**
(`config.py:70-74`, whose own comment says "dormant until GOOGLE_OAUTH_ENABLED=true +
credentials set on Render"):

| Setting | Default | Needed |
|---|---|---|
| `GOOGLE_OAUTH_ENABLED` | `False` | `true` |
| `GOOGLE_CLIENT_ID` | `""` | the OAuth client id |
| `GOOGLE_CLIENT_SECRET` | `""` | the OAuth client secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/oauth/google/callback` | the same path on the **Render API host** |

**Note the flag is a separate condition from the credentials.** Setting the client id
and secret alone leaves the button hidden, because `GOOGLE_OAUTH_ENABLED` is checked
first — so "the credentials are set" is not sufficient evidence that this is fixed.

**Verify first:** call `GET /api/v1/auth/methods` against production and read the
value. That single request distinguishes "flag off" from "credentials missing" from
"something else", and costs nothing.

**Then fix:** set all four on the **API service** (OPS-007 — the worker does not need
them, and that answer should be recorded rather than left implicit), and register the
redirect URI in the Google Cloud console **exactly** as
`https://<render-api-host>/api/v1/auth/oauth/google/callback`. Google matches the
redirect URI as an exact string; a trailing slash or a scheme mismatch fails at the
callback rather than at the button, which is a much more confusing symptom.

**Not urgent:** OTP login works, so this is a missing convenience rather than a broken
path. It is filed because a dormant feature nobody has decided about is the thing that
becomes a stale claim.

---

---

## 4. UX

### UX-01 — CLOSED (#485, 2026-07-12)
Carried as a closed entry rather than deleted, as a standing example of the failure
the 2026-08-18 log entry describes. See `PROJECT_STATE_v27` §5. No change this
rotation.

### UX-02 — Greek crisis line (1018) needs a verification process first
**Status: BLOCKED, deliberately. Re-verified.**
**Verified:** `prompts/safety_response_el.jinja2` contains **no** occurrence of
`1018` and remains country-neutral.

Ruled 2026-09-02: a published crisis number requires founder phone-verification and
its own maintenance process, because **a number that has changed is worse than no
number** — it sends a person in crisis to a dead line. Its own PR if ever, and
`tests/test_safety_response_language.py` would need updating deliberately rather than
routed around.

---

## 5. NIKOS-ACTIONS — standing, outside the codebase

1. **Stripe live switch** — the revenue gate. Sequence in OPS-006.
2. **Sunday 2026-09-13 live watch.** The first run under the PR-C period arithmetic
   and the gate on P0 #6. Watch that a `job_run` row opens and closes `succeeded`.
   If W37 is missed entirely, the manual remedy is in the rulings doc's Ops section —
   and note TD-67: the *first* run has no automatic catch-up.
3. **Manual W37 remedy if needed** — `run_key='2026-W37'`. **Never a weekly key
   earlier than `2026-W37`**; an older key writes a second letter for a week already
   delivered under the pre-PR-C arithmetic.
4. **≥5 acts** of real usage before the P2 gate reads.
5. **TD-61 native Greek review** — the highest-value review item in this file.
6. **Domain cutover — DONE 2026-09-08** (FOUNDER-REPORTED): `thewiseroom.app` live on
   Netlify with a Let's Encrypt certificate, `FRONTEND_URL` set on **both** Render
   services, `NEXT_PUBLIC_BASE_URL` set on Netlify and the web app redeployed; OTP
   login lands on `thewiseroom.app/app/today`. **Remaining: the TD-69 chore PR only**
   (untrack `.env.production`, change the `layout.tsx:40` fallback).
7. **`support@` mailbox.**
8. **DMARC.**
9. **PostHog erasure.**
10. **Delete the 26 stale branches** — checklist in Appendix A. All 26 are deletable:
    the 27th, `fix/web-locked-persona-paywall`, merged as #615 and its branch is gone.
11. **P2 gate reads** — tester (Dimitris / Komninos) post-v2 memory read, and the
    first v2 Sunday letter. See `reports/STRATEGY_P2_RETENTION_2026-09.md`.

---

## Appendix A — the 26 stale remote branches

All are dead work from 2026-05-09 to 2026-06-14, verified by
`git for-each-ref --sort=committerdate refs/remotes/origin`. After #615 merged and
its branch was deleted, these **26 are the complete set** of remote branches besides
`main`, and all 26 are safe to delete.

| # | Last commit | Branch |
|---|---|---|
| 1 | 2026-05-09 | `fix/a4-mailto-and-card-reframe` |
| 2 | 2026-05-11 | `feat/web-legal-pages` |
| 3 | 2026-05-16 | `chore/c-recon-1-investigation` |
| 4 | 2026-05-16 | `chore/c-recon-2-path-a-investigation` |
| 5 | 2026-05-16 | `c5a-investigation/streaming-audit` |
| 6 | 2026-05-18 | `c3-follow-up-bugfixes-2` |
| 7 | 2026-05-20 | `docs/v9-sync-2026-05-20` |
| 8 | 2026-05-21 | `hotfix/cron-arq-enqueue-method` |
| 9 | 2026-05-22 | `feat/pr4h-splash-redesign` |
| 10 | 2026-05-23 | `feat/pr4m-hotfix` |
| 11 | 2026-05-23 | `fix/pr4m-revision-id-length` |
| 12 | 2026-05-24 | `docs/v11-rotation` |
| 13 | 2026-05-24 | `chore/pr4v-cleanup-bundle` |
| 14 | 2026-05-25 | `docs/pr4w-session-addendum` |
| 15 | 2026-05-25 | `fix/pr4ab-feedback-and-stuck-state` |
| 16 | 2026-05-25 | `feat/l1-add-fk-indexes` |
| 17 | 2026-05-26 | `docs/v12-rotation` |
| 18 | 2026-05-28 | `feat/prd-greeting-personalization` |
| 19 | 2026-05-29 | `docs/session-addendum-2026-05-29` |
| 20 | 2026-05-29 | `feat/splash-wise-room` |
| 21 | 2026-05-30 | `fix/mirror-tone-balance` |
| 22 | 2026-06-03 | `docs/update-revenue-chain-state` |
| 23 | 2026-06-08 | `fix/socrates-question-anchors` |
| 24 | 2026-06-10 | `docs/v11-smoke-test-findings` |
| 25 | 2026-06-13 | `feat/ritual-share-cards` |
| 26 | 2026-06-14 | `fix/ios-share-native-sheet` |

---

## 6. What is NOT in this file, and why

**The 13 vitest failures and the 11 `tsc` errors.** Both counts are unchanged since
v26 and are recorded in `PROJECT_STATE_v28` §2 as measured state. They are not
backlog entries because no one has decided to fix them; promoting a measurement to a
backlog item without that decision is how a file like this stops being read.

**Anything in `reports/STRATEGY_P2_RETENTION_2026-09.md`.** That document is a
strategy skeleton behind a start gate, not committed work. Nothing in it is a backlog
item until the gate opens and CLAUDE.md Rule 1 investigation has run.

**The two C-04 filename exceptions.** Grandfathered in the checker's
`RULE_2_ALLOWLIST` and recorded in `PROJECT_STATE_v28` §4. Not work.
