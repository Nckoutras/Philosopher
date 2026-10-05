# GREAT MINDS — Project State v31

> **Range covered:** `#781` … `#785`: 5 squash-merges on `main` since v30's
> verification SHA `cd38ba8b`. Every number 781–785 is on `main` (`git log`).
> **Verification SHA:** `4b0a573db4b5bcb1c327c29c077fa833c7484208` (#785, MEM2-C-2).
> **Date:** 2026-10-05. Production reads were taken between 13:42 and 13:46 UTC.
>
> **Why this rotation is owed:** migration `074_memory_callbacks` (#785). Under the
> CLAUDE.md trigger (30 merged PRs or any migration, counted from the previous
> rotation's merge, #781) it is owed at 4 merges and 1 migration.
>
> **This rotation's own PR number is not asserted.**
>
> **Companion documents:**
> - `IMPLEMENTATION_BACKLOG_v29.md` stays the live backlog. Its MEM2 sections record
>   every ruling of this range verbatim (§ "MEM2 Lane B floor", § "MEM2-C").
> - `PROJECT_STATE_v30.md` is preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below was verified in this rotation, with its method stated inline, or
is explicitly marked FOUNDER-REPORTED, NOT RUN or UNVERIFIED.** "Unchanged." is not
evidence and is not used as such (CLAUDE.md, failure log 2026-08-18). Where a value
equals v30's, it was re-read, not copied; v30's value is shown in parentheses.

Sources used:
- the production database, read-only `SELECT`s on the Oregon project
  (`bvzeuwzqgnqcghvqghtb`);
- the Render API (services, deploys, logs, and the values of four non-secret flags
  only);
- the CI job log of #785's `pytest (live Postgres)` run, read through the GitHub REST
  API **with authentication**. GitHub serves Actions job logs only to an authenticated
  caller, even on this public repository (an unauthenticated request returns 403;
  §3b.7). The request carried the token held by Git Credential Manager on the
  verifying machine, a read-only use the founder authorised on 2026-10-05. The token
  was never printed or stored, and the log was deleted after it was read.

Code methods, all executed at `4b0a573d`:
- `pytest -q`, `vitest run`, `tsc --noEmit`, `alembic heads`;
- `.github/scripts/check_migration_naming.py` and a revision-id length scan;
- `openapi()` generated in-process;
- `WorkerSettings` imported and counted;
- the persona registry, safety lexicon bands, universal forbidden lexicon, question
  bank and rate-limit constants imported and counted;
- `git ls-remote --heads`; `git log` / `git grep` across the range.

**Not consulted:** Stripe, Sentry's project, Netlify, any email inbox.

**Could not be consulted, and why:**
- **PostHog.** No personal API key exists on the verifying machine (only the
  client-side ingest variables). `memory_count` is recorded nowhere else, so the
  smoke it was needed for was run by replay against the production database instead
  (§1a), and is labelled as a replay wherever it is cited.
- **The API's public path.** The verifying machine sits behind a TLS-inspecting
  Fortinet firewall. `api.thewiseroom.app` arrives re-signed by the firewall's CA
  (`SEC_E_UNTRUSTED_ROOT`), and with verification off the firewall answers **403**.
  That is a statement about this machine's network, not about the API. Liveness is
  taken from Render and the worker heartbeat instead (§2), and is not asserted from
  a public request.

---

## 1. Headline — MEM2 Phase C begins, flag off; Lane B recall made reachable

| PR | Merge SHA | What it does |
|---|---|---|
| #781 | `7f9e60fc` | PROJECT_STATE v30; `make state` retired |
| #782 | `0c23c9f6` | MEM2-B5.1: B5 logs `verdict=no_candidates` when a row has no dedup candidate (closes v30 gap 1) |
| #783 | `8c8520da` | MEM2-C-1: callback measurement harness (evals only) and its first run |
| #784 | `0118144d` | Lane B recall floor `INFERRED_SCORE_FLOOR` **0.75 → 0.45**, measured; `scripts/lane_b_reach.py` |
| #785 | `4b0a573d` | MEM2-C-2: callback gate + `memory_callbacks` ledger + Ruling 9 marking + rejection endpoint, behind `CALLBACKS_ENABLED` (default **off**); migration **074** |

Phase C is a persona explicitly calling back something the person wrote in an
earlier conversation. Its rulings (Phase C 1–9, C1-a…f, the STEP 0 and STEP 1
decisions D1–D7) are recorded verbatim in the backlog § "MEM2-C". This section
records only what is **on `main`** and **what production shows**.

**Production evidence, read 2026-10-05 13:42–13:46 UTC:**

| Claim | Evidence | Read |
|---|---|---|
| Schema | `alembic_version` = **`074_memory_callbacks`**, the code's single head | SELECT |
| Ledger exists, locked down | `memory_callbacks`: RLS **on**, **0** policies | SELECT (`pg_class`, `pg_policies`) |
| Nothing offered | `memory_callbacks` **0** rows; `elicited_by_callback` true on **0** rows; `callback_blocked_at` set on **0** rows | SELECT |
| Flag off on both services | `CALLBACKS_ENABLED` **unset** on philosopher-api and philosopher-worker → code default `False` (`config.py`) | Render API + code |
| Gate silent | **0** `callback_gate` lines on philosopher-api since the #785 deploy | Render logs |
| Deployed | both services `live` at **`4b0a573d`**: worker 13:31:21, api 13:31:44 UTC | Render API |

### 1a. The Lane B floor (#784) and its smoke — **CLOSED BY REPLAY (founder, 2026-10-05): Lane B fired at 14:14:18 UTC**

**What changed.** Lane B (inferred rows) is admitted to recall at cosine > 0.45 to the
message, down from 0.75. The measurement behind it (founder-run, production,
2026-10-05): over 95 messages from 9 users, the max cosine to that user's prior Lane
B rows had median 0.419 and max 0.709; **0 exceeded 0.75** (0 of 62 non-admin).
Lane B recall had never fired. The floor is shared by **all four** recall callers:
chat, another_mind, go_deeper and the Council synthesis. Dedup and recurrence
thresholds stay 0.75 (they compare a row to a row, not to the query).

**The smoke owed on merge** compares `memory_count` per turn before and after
the deploy (#784 live on philosopher-api at **13:20:20 UTC**, Render deploys).

**Where `memory_count` is recorded: only in PostHog.** `stream_response` computes it
as `len(memories)` and sends it in the `message_sent` event; `POSTHOG_API_KEY` is set
on philosopher-api (Render, presence only), so it is not logged, and no table stores
it or the block's rows. The verifying machine has no PostHog read key. **So the
smoke was run by REPLAY, not read**: production's own `RECALL_SQL` (the vector bound
once in a CTE; otherwise unchanged), executed read-only against production, for each
turn's message embedded with the app's `embedding_client`, over the rows that existed
**before** that turn (`created_at <` the turn), at the floor live at that moment.

**The turns.** The founder's 4-turn Socrates conversation after the deploy
(`POST /messages` at 13:48:41, 13:49:10, 13:49:36 and 13:50:17 UTC in the API log),
against the only turn in the 24 h before it (08:28:20 UTC, also the founder's, also
Socrates). This account has **no Lane A rows** (no `stated` / `self_portrait`), so
`memory_count` here is exactly the number of Lane B rows admitted.

| Turn (UTC) | Floor live | Lane B rows seen | Best Lane B score | > 0.45 | > 0.75 | Lane B admitted → `memory_count` |
|---|---|---|---|---|---|---|
| 08:28:20 (baseline) | 0.75 | 122 | **0.7094** | 3 | 0 | **0** |
| 13:48:41 | 0.45 | 125 | 0.4441 | 0 | 0 | **0** |
| 13:49:10 | 0.45 | 126 | 0.3344 | 0 | 0 | **0** |
| 13:49:36 | 0.45 | 126 | 0.3660 | 0 | 0 | **0** |
| 13:50:17 | 0.45 | 128 | 0.4121 | 0 | 0 | **0** |

**First result (13:48–13:50): Lane B rows did not appear in the block on any of these
four turns.** All four messages were short ("Lost time is a lot on my mind
lately", …) and none came within 0.005 of 0.45. This is not evidence against the
deploy: the baseline turn, a long and specific message, scored 0.7094 (the same
maximum the founder's `lane_b_reach.py` run reported), cleared 0.45 three times, and
was admitted **0** rows only because 0.75 was live at 08:28. Under 0.45 it would have
received Lane B rows.

**Precision.** Vectors were rounded to 5 decimals for transport; the cosine error that
introduces is far below the closest margin in the table (0.0059).

**Second result (14:13–14:15): Lane B fired.** The founder then sent three turns to
Orwell, the only user messages in production between 14:13 and 14:19 UTC (SELECT).
Same replay method, floor 0.45 live:

| Turn (UTC), Orwell | Message | Lane B rows seen | Best Lane B score | > 0.45 | Lane B admitted → `memory_count` |
|---|---|---|---|---|---|
| 14:13:08 | "Should I quit my job? Or bear with it and provide my family" | 130 | 0.4501 | 1 (`struggle`) | **0 or 1: indeterminate** (0.0001 over the floor, inside the replay's error) |
| 14:14:18 | "Toward freedom . Away from meaningless conflict. I try to have a clear mind and decide correctly and timely" | 132 | **0.5060** | 1 (`onboarding_profile`) | **1** |
| 14:14:50 | "Nothing changes . Except my life becoming less" | 134 | 0.3518 | 0 | **0** |

**The smoke is CLOSED (founder ruling, 2026-10-05), on the 14:14:18 turn.** Its row
cleared 0.45 by **0.056**, far outside the replay's error, so it was in the block:
`memory_count` = 1 where the 0.75 floor would have given 0. **This is the first Lane B
row in any production memory block.** It is a reconstruction, not an observation; the
observed value is PostHog `message_sent.memory_count` for that turn, expected 1.

**FINDING — the first Lane B row is an onboarding tap, not an inferred memory.** The
row admitted at 14:14:18 is `entry_type = 'onboarding_profile'`: a self-reported pill
the person chose at onboarding (`provenance = 'user_selected'`), not a row chat
extraction wrote. Lane A is keyed on `STANDING_TYPES = ('stated', 'self_portrait')`
only, so every other type, `onboarding_profile` included, competes in Lane B. The
0.45 floor therefore admits onboarding taps on a modest match. That bears on the
parked backlog item (MEM2-C, "not C") that Haiku recites self-portrait and onboarding
taps as traits under Ruling #6: before #784 a tap reached the block only through the
guaranteed profile block; it can now also arrive as a recalled memory row. **Not
acted on here; named so it is decided rather than discovered.**

**Precision, both replays.** Vectors were rounded to 5 decimals for transport, and
OpenAI embeddings vary slightly between calls; together they cannot move a score by
anything like 0.056. They can move one by 0.0001, which is why 14:13:08 is left
undecided.

`memory_count` is both lanes together; for accounts with Lane A rows the Lane B share
is the change, not the value.

### 1b. Watch — MEM2-C-2 (flag OFF: nothing to observe yet)

**With the flag off there is nothing to watch, by design.** The send path is
byte-identical to before C-2 (pinned by a test), and the ledger stays empty (§1).
Two parts of C-2 are **live even with the flag off**:
- `POST /api/v1/memory/callbacks/{id}/reject`: answers 404 for every id while the
  ledger is empty.
- The Ruling 9 lookup in `extract_memory_task`: one indexed query per extraction;
  with an empty ledger it marks nothing.

**What to watch from the day the flag first flips (C-3a canary):**
- `callback_gate outcome=offered|none|skipped` lines on philosopher-api, with per-rule
  exclusion counts. No content is logged.
- `memory_callbacks` rows, one per offer. The first live smoke is owed **then**, not at
  #785's merge.
- `elicited_by_callback` rows appearing only on the turn **after** an offer.
- `callback_rejected` lines when the endpoint is used (no web control until C-3a).

**First executions of C-2's SQL**: CI's `pytest (live Postgres)` on #785's head
(job 111784320409) ran **254 passed, 0 failed, 0 skipped**, including all **14**
`test_memory_callbacks_live.py` tests by name (read from the job log).

### 1c. Watch — B5, carried from v30 §1a, re-read

| v30 watch item | Status, 2026-10-05 | Read |
|---|---|---|
| First real RESTATEMENT supersession | **Happened**, 2026-10-04 07:08:18 UTC: `kept=new retired=old score=0.809 more_specific=new chain_depth=1`. A `belief` from another conversation superseded; survivor active, `echo_count` 1 | worker log + SELECT |
| `superseded` chat rows | **1** (0) | SELECT |
| `verdict=CONTRADICTION` | **0** lines since the B5 deploy | Render logs |
| `note=dedup_ratchet_guard` | **0** | Render logs |
| `verdict=error` / `dedup_judge_failed` | **0** / **0** | Render logs |
| B5.1 silent-path line | seen once: `verdict=no_candidates … rows=3`, 2026-10-05 08:28:36 UTC, the turn after the morning's only user message | Render logs |

**Memory, production, 2026-10-05:**
- **1,080** active rows (1,071): `system_inferred` 759 (750), `user_selected` 307
  (307), `user_stated` 14 (14).
- **23** inactive (22), **all** `superseded`.
- **0** `user_rejected`: R3 has still never fired in production.
- Rows with `echo_count` set: **5** (4). Insights: **36** (34), **4** with evidence (2).
  `insight_verdict_shift` rows: **0** (0).

---

## 2. Verified state — every row executed or read at `4b0a573d`

| Claim | Method | Result (v30 at `cd38ba8b`) |
|---|---|---|
| Backend suite | `pytest -q` executed | **4305 passed, 250 skipped, 0 failed** (4114 / 225) |
| CI failure baseline | `tests/ci_baseline_failures.txt`, non-comment lines | **0** entries (0) |
| Web unit suite | `vitest run` (node v20.18.1) | **628 passed / 628**; 76 / 76 files (628; 76) |
| Web typecheck | `tsc --noEmit` | exit 0, **0 errors** (0) |
| Alembic | `alembic heads` | single head **`074_memory_callbacks`** (`073_memory_echo_strength`) |
| Alembic, production | `SELECT version_num FROM alembic_version` | **`074_memory_callbacks`**, matching the code |
| Migration naming (C-04) | `check_migration_naming.py` + id-length scan | **74 files, 0 violations, 0 over 32 chars**; longest still `024_saved_line_conclusion_source` (32); **2** documented exceptions (`013`, `014`) (73 files) |
| RLS (C-05), production | `pg_tables.rowsecurity` | **41 / 41** public tables enabled (40 / 40); the new one is `memory_callbacks` |
| API surface | `openapi()` in-process | **101 paths / 122 operations** (100 / 121); the added one is `POST /api/v1/memory/callbacks/{callback_id}/reject` |
| ARQ tasks / cron jobs / tz | `WorkerSettings` | **14** / **7** / `UTC` (14 / 7 / UTC) |
| APScheduler jobs | `id="…"` in `workers/cron.py` | **6**, same six ids |
| Question bank | parsed | **360 / 360** with `pill_weights` (360 / 360) |
| Personas | `PERSONA_REGISTRY` | **11**; **3** `tier="free"`: `lao_tzu`, `marcus_aurelius`, `socrates` (11; 3) |
| Persona forbidden lexicons | counted | **11 / 11** (11 / 11) |
| Safety lexicons | four bands imported and counted | **372**: HIGH 240, MEDIUM 52, OUTPUT 28, LOW 52; **127** with Greek script (372; 127) |
| Universal forbidden lexicon | `len(_UNIVERSAL_PHRASES)` | **196** across **12** categories (196; 12) |
| Prompts stating a computed language | `language_directive(` call sites, non-test | **17** (17) |
| Free / Pro limits | `rate_limit_service` constants | `FREE_DAILY_LIMIT = 10` (global); `PRO_DAILY_FAIR_USE_LIMIT = 150`; `PRO_MONTHLY_FAIR_USE_LIMIT = 400` (same) |
| Lane B recall floor | `memory_service.INFERRED_SCORE_FLOOR` | **0.45** (0.75), #784 |
| Dedup / recurrence thresholds | constants | **0.75** / **0.75** (0.75 / 0.75) |
| Callback gate constants | `callback_service` | floor **0.35**; min row age **2 d**; per-user cooldown **7 d**; chain cooldown **30 d**; plans `pro`, `premium` (new) |
| Flags, code defaults | `config.Settings` | `CALLBACKS_ENABLED` **False** (new); `MEMORY_DEDUP_ENABLED` True; `SAFETY_JUDGE_ENABLED` True |
| Live-DB tests | `pytest tests/db_live --collect-only` | **254** across **21** files (240 / 20) |
| Stale-`running` threshold | `letter_dispatch.STALE_RUNNING_AFTER` | 2 hours (2 hours) |
| Upgrade page price | `apps/web/app/app/upgrade/page.tsx:153` | still **"€99.99 / year"** (OPS-006 unchanged in code) |
| Greek crisis numbers | count of `1018` in `prompts/safety_response_el.jinja2` | **2** (2) |
| `_is_null_reply` | `git grep`, non-test | **0** (0) |
| Insight→counterview door | `routers/memory.py` | **capped**: `check_fair_use_limit` present (capped) |
| `.env.production` | `git ls-files` | untracked (untracked) |
| `metadataBase` | `layout.tsx:66,71` | `NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'` (same) |
| Deployed SHA | Render API, latest deploy per service | **philosopher-api** and **philosopher-worker** both `live` at **`4b0a573d`**, 13:31:21–13:31:44 UTC |
| Worker alive after the deploy | `job_run` `worker_heartbeat` | last 13:40:01 UTC; 6 runs in the hour before 13:45 |
| Public health path | `curl https://api.thewiseroom.app/health` | **UNVERIFIED from the verifying machine**: TLS-inspecting firewall (see PROVENANCE). v30 read **200** |
| Remote branches | `git ls-remote --heads origin` | **17**: `main` + the same **16** others as v30 §3d (17) |

### 2a. Render environment, read 2026-10-05

Values of non-secret flags only. "Unset" means the code default applies.

| Flag | philosopher-api | philosopher-worker | Code default |
|---|---|---|---|
| `CALLBACKS_ENABLED` | unset | unset | `False`: **callbacks off** |
| `MEMORY_DEDUP_ENABLED` | unset | unset | `True`: B5 on (worker-only reader) |
| `SAFETY_JUDGE_ENABLED` | unset | unset | `True` |
| `BETA_GRANT_PRO_TO_ALL` | `false` | `false` | — . v30 §3c's closure **holds**: the services still match |

### ⚠️ Still FOUNDER-REPORTED — not verified by this rotation

Carried from v30, re-listed rather than dropped:
1. **Google OAuth enabled and brand-verified.**
2. **OPS-006:** the live-mode Stripe price objects. The page still displays €99.99/year
   (§2).
3. **Email deliverability.** Not observed.
4. **The "1.85× the heaviest usage day" figure** behind the fair-use cap. Not re-read.

---

## 3. Known gaps — v30's, with status; then this range's

### 3a. Carried from v30 §1a

| # | v30 gap | Status 2026-10-05 | Verified by |
|---|---|---|---|
| 1 | A row with no dedup candidate wrote no log line | **CLOSED by #782.** `memory_service.py:1569` logs `verdict=no_candidates`, and the line is in production's worker log (08:28:36 UTC) | code + Render logs |
| 2 | A 'no' (R3) does not follow supersession | **OPEN.** `reject_cited_memories` still retires `MemoryEntry.id.in_(ids)` only, the cited ids. C-2's callback rejection walks the chain in both directions, but only for a callback, not for an insight 'no' | code |
| 3 | `more_specific` order bias toward the note shown first | **ACCEPTED, unchanged.** Documented at `dedup_judge.py:120`. The one production supersession (§1c) chose `new`, the note shown second | code + log |
| 4 | Dedup kill switch | **Unchanged.** `MEMORY_DEDUP_ENABLED` unset on both services, default on (§2a) | Render API |
| — | v30 §3d: 16 non-`main` remote branches | **Unchanged list**, still awaiting the deferred cleanup batch (re-map to PRs by title first). Both branches merged in this range (#784, #785) are already gone | `git ls-remote` |

### 3b. New in this range, named so they are not discovered later

1. **The `memory_count` smoke for #784 is CLOSED by replay** (§1a, founder ruling):
   Lane B admitted 1 row at 14:14:18 UTC (score 0.5060). PostHog would give the
   observed value; not read (no key).
2. **The first Lane B row in production is an `onboarding_profile` tap** (§1a). Lane B
   admits taps at 0.45, which bears on the parked "Haiku recites onboarding taps as
   traits" item. Undecided, not acted on.
3. **C-2's live behaviour is unobserved by design**: flag off. The first live smoke is
   owed when the flag first flips.
4. **Owed to C-3**, recorded in the backlog § "MEM2-C":
   - the Ruling 9 exception ("unless an independently stated proposition") is not
     built; every row of a reply turn is marked. A named shortcut, first C-3 fix;
   - the use detector (fills `memory_callbacks.used`) must accept «…» as well as "…";
   - the L2 rise in the Greek re-run (2/10 → 6/11) is a named watch item.
5. **`memory_count` counts an appended callback row** when the flag is on (recall + 1).
   Cosmetic, flag-off unchanged.
6. **A stale count in a code comment**: `account_deletion_service.py:13,193` say "21
   tables cascade". At least migrations 061, 067 and 074 have each added a table that
   cascades on the user since that was written; the full current count was not taken.
   The comment was not edited: touching it is code, not this docs PR.
7. **CI per-test results need an authenticated log read.** The live-Postgres job
   publishes no summary, and GitHub serves job logs only to an authenticated caller.
   A small CI PR to publish per-test results is queued (it changes a gate, so ⛔).
8. **OPS-006** stands (§2).

---

## 4. Rotation trigger

Unchanged rule (CLAUDE.md § "Documentation rotation"): **rotate at 30 merged PRs or at
any migration, whichever comes first,** counted from the merge of the previous
rotation PR. The next rotation is owed at the first migration after this PR merges,
or at its 30th merge.

---

## 5. What is not in this document

- **The open backlog.** `IMPLEMENTATION_BACKLOG_v29.md`, not rotated here.
- **A per-PR narrative** beyond §1. Each PR's rulings and detail live in the backlog
  entry it cites.
- **The handoff brief.** `HANDOFF_BRIEF_v30.md` (#648) is still the last one.
