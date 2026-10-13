# GREAT MINDS — Project State v32

> **Range covered:** `#787` … `#791`: 5 squash-merges on `main` since v31's rotation
> PR (#786). Every number 787–791 is on `main` (`git log`).
> **Verification SHA:** `d92495224db4c28a835c0199ca1eba170bb734ba` (#791, UAT-TOPIC-001 PR-B).
> **Date:** 2026-10-13. Production reads were taken between 07:44 and 07:59 UTC.
>
> **Why this rotation is owed:** migration `075_not_user_words` (#791). Under the
> CLAUDE.md trigger (30 merged PRs or any migration, counted from the previous
> rotation's merge, #786), it is owed at 5 merges and 1 migration.
>
> **This rotation's own PR number is not asserted.**
>
> **Companion documents:**
> - `IMPLEMENTATION_BACKLOG_v29.md` stays the live backlog. This PR updates its
>   MEM2-C heading and records the UAT Pro grant there (§3b).
> - `PROJECT_STATE_v31.md` is preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below was verified in this rotation, with its method stated inline, or
is explicitly marked FOUNDER-REPORTED or UNVERIFIED.** "Unchanged." is not evidence
and is not used as such (CLAUDE.md, failure log 2026-08-18). Where a value equals
v31's, it was re-read, not copied; v31's value is shown in parentheses.

Sources used:
- the production database, read-only `SELECT`s on the Oregon project
  (`bvzeuwzqgnqcghvqghtb`);
- the CI job log of #791's `pytest (live Postgres)` run on its merged head
  `1c5be549` (job 115175716159). The log was read through the GitHub REST API with the
  Git Credential Manager token, the read-only use the founder authorised on
  2026-10-05. The token was never printed or stored, and the log was deleted after it
  was read;
- the Render deploy-log line of migration 075, **pasted by the founder** (§1a).

Code methods, all executed at `d9249522`:
- `pytest -q`, `pytest tests/db_live --collect-only`, `vitest run`, `tsc --noEmit`,
  `alembic heads`;
- `.github/scripts/check_migration_naming.py` and a revision-id length scan;
- `openapi()` generated in-process;
- `WorkerSettings` imported and counted;
- the persona registry, safety lexicon bands, universal forbidden lexicon, question
  bank, rate-limit, recall and callback constants imported and counted;
- `git ls-remote --heads`; `git log` / `git grep` across the range.

**Not consulted:** Stripe, Netlify, any email inbox.

**Could not be consulted, and why:**
- **Render (API, deploys, logs, environment).** No Render API key exists on the
  verifying machine this rotation (v31 had one). So the deployed SHA per service, the
  values of the four flags, and every log count v31 took from Render are
  **UNVERIFIED** here. Where the database settles a question, it is used instead and
  labelled as such.
- **Sentry.** No access. Whether PHILOSOPHER-API-F was marked resolved after #789
  deployed is **UNVERIFIED**.
- **PostHog.** No read key, as in v31.
- **The API's public host.** `api.thewiseroom.app` still fails TLS from this machine
  (curl exit 60: the TLS-inspecting firewall v31 describes). Render's own service URL
  `philosopher-api-z9l9.onrender.com/health` answered **200** at 07:59:31 UTC. That is
  liveness of the Render service, not of the public path.

---

## 1. Headline — the callback canary merged; auto-sent topics stop being remembered

| PR | Merge SHA | What it does |
|---|---|---|
| #787 | `75b5d624` | docs(v31): the #784 smoke closed by replay; the first Lane B row is an onboarding tap |
| #788 | `f9ab8336` | MEM2-C-3a: callback use detector (`detect_callback_use_task`) + "That's not right" under a used callback |
| #789 | `4aee61d0` | `extract_and_store` returns an `ExtractionResult` on every path (Sentry PHILOSOPHER-API-F, latent since #776) |
| #790 | `b38923c3` | UAT-TOPIC-001 PR-A: a seeded first turn matching `daily_questions` is stored `message_kind='daily_topic'` and not extracted |
| #791 | `d9249522` | UAT-TOPIC-001 PR-B: migration **075** retires topic-derived memory to `not_user_words` and re-marks the historical topic turns |

### 1a. UAT-TOPIC-001 — verified in production

**The defect.** Quick start with an empty textarea auto-sends the day's topic as the
first user turn. It was stored as an ordinary user message, and memory extraction
attributed the topic's claim to the person. Full record: backlog § UAT-TOPIC-001.

| Claim | Evidence | Read |
|---|---|---|
| Schema | `alembic_version` = **`075_not_user_words`**, the code's single head | SELECT |
| Constraint widened | `ck_memory_entries_inactive_reason` includes `not_user_words` | `pg_get_constraintdef` |
| 075 ran with its count guard | `075: before topics=47 standard=47 derived=91 active=85; retired=85 marked=47; after standard=0 active=0` | Render deploy log, **FOUNDER-REPORTED** (pasted) |
| Rows retired | **85** rows `not_user_words`, all topic-derived; **0** topic-derived rows active; the **6** already `superseded` untouched | SELECT, 075's own rule |
| Turns re-marked | **47** historical topic turns `daily_topic`; **0** still `standard` | SELECT |
| PR-A on a real turn | Quick start on `nckoutras+testn`, 07:44:21 UTC (conversation `b33717d6`): the user row is `daily_topic`; **0** memory rows by link or by timing at 07:45:30 and at 07:49:46; title generated ("Recognizing Imbalanced Relationships") | SELECT |

**Not seen:** the API's `daily_topic_turn … extraction=skipped` line and the worker's
job log (Render, see PROVENANCE). The PR-A check rests on the database alone.

**First executions.** CI's `pytest (live Postgres)` on #791's merged head: **266
passed, 0 failed**. By name, all of these PASSED: the four `test_not_user_words_075.py`
tests, the four `test_daily_topic_live.py` tests, both
`ck_memory_entries_inactive_reason` constraint tests, and
`test_070_and_071_downgrade_cleanly_and_upgrade_again` (which now runs through 075's
downgrade). The first head (`3db29503`) was red on a fixture error. The test padded
the topic with a newline, which `btrim` does not strip. The fixture was corrected; the
rule was not changed. Production has no padded topic turns (SELECT).

### 1b. The callback canary (#788) — **0 offers in 8 days, and the data explains why**

**The flag.** `CALLBACKS_ENABLED=true` on philosopher-api since 2026-10-05:
**FOUNDER-REPORTED, UNVERIFIED here** (no Render read). The code default is still
`False` (`config.py:51`).

**The ledger, read 07:58 UTC.** `memory_callbacks`: **0** rows, so 0 used, 0 unused,
0 reacted, and 0 repeated memories. `elicited_by_callback` is true on **0** rows.
`callback_blocked_at` is set on **0** rows.

**Why zero is not yet evidence about the flag or the gate.** Since #788 merged
(2026-10-05 16:51 UTC), production has received **33** Pro turns, from **2** accounts:
- **`nckoutras+uatpro1`**: 32 turns, 2026-10-05 17:48 to 10-06 08:10 UTC. The account
  was created at 17:06 on 10-05. None of its 63 memory rows was 2 days old at any of
  those turns, so `MIN_ROW_AGE` (2 days) excluded every candidate.
- **`nckoutras+testn`**: 1 turn, 2026-10-13 07:44. It was a daily-topic turn, and the
  account's only 2 aged rows were topic-derived, retired by 075 at 07:27.

No other active Pro or Premium account (16 active) has sent a message since #788.
**So the canary has had no eligible turn.** A zero would be the same with the flag on
or off, and only Render's `callback_gate outcome=` lines can tell them apart.

**The canary's first real exercise is this week.** `uatpro1`'s rows are now old
enough. All 26 of its active rows are well past the 2-day minimum, and every one is
≥7 days old by 2026-10-13 08:11 UTC (SELECT; none is callback-blocked or
reply-elicited). The UAT Area C and D probes (2026-10-14 and 2026-10-16) are therefore
the first turns that **can** produce an offer.

**Founder ruling, 2026-10-13:**
- the UAT Pro grants are extended through **2026-11-04**, which is day 30;
- the C-3b day-30 judgement on synthetic traffic is **indicative only**;
- the binding verdict comes from Phase 3 real users.

**Not yet applied.** At 08:06 UTC all three grants still read `current_period_end`
2026-10-19 17:14:51 UTC (SELECT). The extending UPDATE is owed before 10-19.

**The 24-hour check owed on 2026-10-06** (ledger, Render log counts, L2 watch) has no
record in `docs/`. Its status is **UNVERIFIED**, not passed. The ledger part reads 0 today.

### 1c. #789 — the extraction crash

`extract_and_store` returned a bare list on its parse-failure path, and
`extract_memory_task` read attributes off it. Any model output that did not parse
crashed the task. Fixed at the source; three tests run the real producer on
malformed JSON. **Sentry PHILOSOPHER-API-F resolved: UNVERIFIED** (no Sentry access).

The founder's lesson from this fix is now in CLAUDE.md's failure log (2026-10-05
entry, this PR), verbatim.

### 1d. Memory, production, 2026-10-13 07:58 UTC

- **1,044** active rows (1,080): `system_inferred` 723 (759), `user_selected` 307
  (307), `user_stated` 14 (14). The fall is 075's 85 retirements, net of new rows.
- **134** inactive (23): `superseded` **49** (23), `not_user_words` **85** (new).
- **0** `user_rejected`: R3 has still never fired in production.
- Rows with `echo_count` > 0: **35** (5). Insights: **40** (36), **8** with evidence (4).
  `insight_verdict_shift` rows: **0** (0).

**Both rises are explained (founder, 2026-10-13); no trace is owed.** `superseded`
23 → 49 (+26) matches B5's 26 retirements on `uatpro1` (the 2026-10-12 verification).
`echo_count` 5 → 35 is B4 counting cross-conversation echoes of the UAT same-message
burst. Checked by SELECT: all 26 rows `superseded` since v31 belong to `uatpro1`, and so
do all 30 new rows with an echo. The echo mechanism is the founder's explanation; it was
not re-derived here.

---

## 2. Verified state — every row executed or read at `d9249522`

| Claim | Method | Result (v31 at `4b0a573d`) |
|---|---|---|
| Backend suite | `pytest -q` executed | **4346 passed, 251 skipped, 0 failed** (4305 / 250) |
| CI failure baseline | `tests/ci_baseline_failures.txt`, non-comment lines | **0** entries (0) |
| Web unit suite | `vitest run` (node v20.18.1) | **632 passed / 632**; 77 / 77 files (628; 76) |
| Web typecheck | `tsc --noEmit` | exit 0 (exit 0) |
| Alembic | `alembic heads` | single head **`075_not_user_words`** (`074_memory_callbacks`) |
| Alembic, production | `SELECT version_num FROM alembic_version` | **`075_not_user_words`**, matching the code |
| Migration naming (C-04) | `check_migration_naming.py` + id-length scan | **75 files, 0 violations, 0 over 32 chars**; longest still `024_saved_line_conclusion_source` (32) (74 files) |
| RLS (C-05), production | `pg_tables.rowsecurity` | **41 / 41** public tables enabled (41 / 41). 075 creates no table |
| API surface | `openapi()` in-process | **101 paths / 122 operations** (101 / 122). #788 changed a response, not a route |
| ARQ tasks / cron jobs / tz | `WorkerSettings` | **15** / **7** / `UTC` (14 / 7 / UTC). The added task is `detect_callback_use_task` (#788) |
| APScheduler jobs | `id="…"` in `workers/cron.py` | **6** (6) |
| Question bank | parsed | **360 / 360** with `pill_weights` (360 / 360) |
| Personas | `PERSONA_REGISTRY` | **11**; **3** `tier="free"`: `lao_tzu`, `marcus_aurelius`, `socrates` (11; 3) |
| Persona forbidden lexicons | counted | **11 / 11** (11 / 11) |
| Safety lexicons | four bands imported and counted | **372**: HIGH 240, MEDIUM 52, OUTPUT 28, LOW 52; **127** with Greek script (372; 127) |
| Universal forbidden lexicon | `len(_UNIVERSAL_PHRASES)` | **196** across **12** categories (196; 12) |
| Prompts stating a computed language | `language_directive(` call sites, non-test | **17** (17) |
| Free / Pro limits | `rate_limit_service` constants | `FREE_DAILY_LIMIT = 10`; `PRO_DAILY_FAIR_USE_LIMIT = 150`; `PRO_MONTHLY_FAIR_USE_LIMIT = 400` (same) |
| Lane B recall floor | `memory_service.INFERRED_SCORE_FLOOR` | **0.45** (0.45) |
| Dedup / recurrence thresholds | constants | **0.75** / **0.75** (0.75 / 0.75) |
| Callback gate constants | `callback_service` | floor **0.35**; min row age **2 d**; per-user cooldown **7 d**; chain cooldown **30 d**; plans `pro`, `premium` (same) |
| Flags, code defaults | `config.Settings` | `CALLBACKS_ENABLED` **False**; `MEMORY_DEDUP_ENABLED` True; `SAFETY_JUDGE_ENABLED` True (same) |
| `inactive_reason` vocabulary | model + live constraint | `superseded`, `user_removed`, `user_rejected`, **`not_user_words`** (075) |
| Live-DB tests | `pytest tests/db_live --collect-only` | **266** across **23** files (254 / 21) |
| Stale-`running` threshold | `letter_dispatch.STALE_RUNNING_AFTER` | 2 hours (2 hours) |
| Upgrade page price | `apps/web/app/app/upgrade/page.tsx:153` | still **"€99.99 / year"** (OPS-006 unchanged in code) |
| Greek crisis numbers | count of `1018` in `prompts/safety_response_el.jinja2` | **2** (2) |
| `_is_null_reply` | `git grep`, `*.py`, non-test | **0** (0). Docs still mention it 8 times; that is history |
| Insight→counterview door | `routers/memory.py` | **capped**: `check_fair_use_limit` present (capped) |
| `.env.production` | `git ls-files` | untracked (untracked) |
| `metadataBase` | `layout.tsx:66,71` | `NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'` (same) |
| Deployed SHA | Render API | **UNVERIFIED** (no Render key). The database shows an API deploy carrying 075 ran: `alembic_version` = 075, and the founder-pasted log line (§1a). The worker's SHA is not settled by anything read here |
| Worker alive | `job_run` `worker_heartbeat` | last 07:50:01 UTC; **6** runs in the hour before 07:58 (6) |
| Health, Render service URL | `curl philosopher-api-z9l9.onrender.com/health` | **200** at 07:59:31 UTC |
| Public health path | `curl https://api.thewiseroom.app/health` | **UNVERIFIED** from this machine (TLS, see PROVENANCE) |
| Active Pro/Premium subscriptions | SELECT | **16** (13 on 2026-10-05, backlog § MEM2-C) |
| Remote branches | `git ls-remote --heads origin` | **18**: `main` + v31's **16** + `docs/project-state-v31` (17) |

### 2a. Render environment

**UNVERIFIED this rotation** (no Render key). v31's reading (2026-10-05, before the
C-3a flip) is not carried forward as current. The one change known since is
`CALLBACKS_ENABLED=true` on philosopher-api, **FOUNDER-REPORTED**.

### ⚠️ Still FOUNDER-REPORTED — not verified by this rotation

Carried from v31, re-listed rather than dropped:
1. **Google OAuth enabled and brand-verified.**
2. **OPS-006:** the live-mode Stripe price objects. The page still displays €99.99/year
   (§2).
3. **Email deliverability.** Not observed.
4. **The "1.85× the heaviest usage day" figure** behind the fair-use cap. Not re-read.
5. **New:** `CALLBACKS_ENABLED=true` on philosopher-api (§1b), and the 075 deploy-log
   line (§1a).

---

## 3. Known gaps — v31's, with status; then this range's

### 3a. Carried from v31 §3a–§3b

| # | v31 gap | Status 2026-10-13 | Verified by |
|---|---|---|---|
| v30-2 | A 'no' (R3) does not follow supersession | **OPEN.** `reject_cited_memories` still retires `MemoryEntry.id.in_(ids)` only (`memory_service.py:756`) | code |
| v30-3 | `more_specific` order bias | **ACCEPTED, unchanged.** Documented at `dedup_judge.py:117-124` | code |
| v30-4 | Dedup kill switch | **UNVERIFIED** (Render). Code default on | code |
| 3b.2 | The first Lane B row is an onboarding tap | **Undecided, not acted on** | backlog |
| 3b.3 | C-2's live behaviour unobserved | **Still unobserved**, now for a different reason: the flag is reportedly on, and no eligible turn has occurred (§1b) | SELECT |
| 3b.4 | Owed to C-3: Ruling 9 exception | **OPEN.** `arq_worker.py:884` marks every row of a reply turn `elicited_by_callback=reply_turn` | code |
| 3b.4 | Owed to C-3: the detector accepts «…» | **CLOSED by #788** (`callback_use.py:55`, `QUOTE_PAIRS`) | code |
| 3b.4 | L2 watch in the Greek re-run | **UNVERIFIED**: the 24h check has no record (§1b) | — |
| 3b.5 | `memory_count` counts an appended callback row | **Unchanged in code** (`conversation_service.py:1075`); unobservable while no offer has been made | code |
| 3b.6 | Stale "21 tables cascade" comment | **OPEN**: still at `account_deletion_service.py:13,193`. Not edited here (code, not docs) | code |
| 3b.7 | CI per-test results need an authenticated log read | **OPEN**: `backend-ci.yml` publishes no step summary or JUnit report | code |
| 3b.8 | OPS-006 | Stands (§2) | code |
| — | v30 §3d: 16 non-`main` remote branches | **Unchanged list, plus one**: `docs/project-state-v31` is #787's branch (same title, a byte-identical `PROJECT_STATE_v31.md`), squash-merged and not deleted. Still awaiting the deferred cleanup batch | `git ls-remote` |

### 3b. New in this range, named so they are not discovered later

1. **The callback canary has had no eligible turn yet** (§1b). Its first real exercise
   is the UAT Area C and D probes (2026-10-14 and 2026-10-16). The grants are ruled
   extended to 2026-11-04, but the database still reads 2026-10-19: the UPDATE is owed.
   The day-30 judgement on synthetic traffic is indicative only (founder ruling).
2. **The 24-hour canary check owed on 2026-10-06 has no record** (§1b).
3. **TD-123:** letters, mirrors, trajectory snapshots, You-vs-You, counterview, and
   conclusion and Council summaries still read a `daily_topic` turn as the person's
   words. For the 47 historical turns, a filter on `message_kind` now covers them,
   because 075 re-marked them.
4. **TD-124:** `PATCH /memory/{id}` reactivates any inactive row, `not_user_words`
   included. No web caller today. Fix it with the TD-111 memory screen.
5. **The UAT Pro grant is now on record** (backlog § MEM2-C): 3 accounts, comp,
   no Stripe id. The database reads Pro until 2026-10-19 17:14:51 UTC (SELECT, the
   first verification of a grant the reviewer ran). It is ruled extended to
   2026-11-04, and that UPDATE is owed (item 1).

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
