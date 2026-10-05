# GREAT MINDS — Project State v30

> **Range covered:** `#633` … `#780`: 147 squash-merges on `main` since v29's
> verification SHA `93aa0693`, carrying 146 distinct PR numbers (#730 appears on two
> commits). Two numbers in the range are not on `main`: **#657** and **#745**. Every
> number in 633–780 was tested against the `(#NNN)` suffixes of `git log`.
> **Verification SHA:** `cd38ba8ba8e56c9b746333e0007a0e6a24c4d243` (#780, MEM2-B5).
> **Date:** 2026-10-03. Production reads were taken between 16:20 and 16:35 UTC.
>
> **This rotation's own PR number is not asserted.** The range above is what is on
> `main`.
>
> **Companion documents:**
> - `IMPLEMENTATION_BACKLOG_v29.md` stays the live backlog. It is not rotated by this PR,
>   and its MEM2 section already records Phase B in full.
> - `HANDOFF_BRIEF_v30.md` (#648, 2026-09-14) is the last handoff brief.
> - v29 files are preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below was verified in this rotation, with its method stated inline, or
is explicitly marked FOUNDER-REPORTED or UNVERIFIED.** "Unchanged." is not evidence and
is not used as such (CLAUDE.md, failure log 2026-08-18).

**New this rotation: production was read, not assumed.** v29 consulted no database,
no dashboard and no logs. This rotation used:
- the production database, read-only `SELECT`s on the Oregon project
  (`bvzeuwzqgnqcghvqghtb`);
- the Render API (services, deploys, env-var names, and the values of non-secret flags
  only);
- the philosopher-worker log, read through the Render logs API;
- a public `curl`.

Code methods, all executed at `cd38ba8b`:
- `pytest -q`, `vitest run`, `tsc --noEmit`, `alembic heads`;
- a revision-id script over every migration file;
- `openapi()` generated in-process;
- `WorkerSettings` imported and counted;
- the persona registry, the safety lexicon bands and the universal forbidden lexicon
  imported and counted;
- the question bank parsed;
- `git ls-remote --heads`;
- `git log` / `git show` across the range.

**Not consulted:** Stripe, Sentry's project, Netlify, any email inbox.

---

## 1. Headline — Phase B of the epistemic memory (MEM2) is closed

MEM2 makes the memory honest about itself:
- whose claim each row is;
- what an insight was derived from;
- what a person's "no" removes;
- how often a theme returns;
- which rows say the same thing.

Phase A built the columns. Phase B built the behaviour. The rulings (R1–R11) and every
Phase B decision are recorded verbatim in `IMPLEMENTATION_BACKLOG_v29.md` § "MEM2-B".
This section records only what is **on `main`** and **what production shows**.

| Step | PR | Merge SHA | What it does |
|---|---|---|---|
| MEM2-A | #771 | `484d9a1c` | `provenance`, `source_surface`, `source_message_ids`, `supersedes_memory_id`, `inactive_reason` (migrations 070/071); a 'no' on a recurrence insight retires the rows it cites (R3) |
| B1 | #776 | `32de2e63` | Two insight budgets (recurrence, signal) instead of one; recurrence evaluated first |
| B1b | #777 | `b3fa03a7` | The ARQ worker gets a root log handler at INFO. Its INFO lines had never reached the log |
| B2 | #778 | `2d39daf7` | A 'yes' reactivates `user_rejected` rows; a no→yes ≥72h apart writes an opinion-shift memory row (migration 072) |
| B3+B4 | #779 | `7f5947d0` | Signal insights carry evidence (`kind` key; a belief cites its own row). `echo_count` / `last_echo_at`, counted before the gate (migration 073) |
| B5 | #780 | `cd38ba8b` | Write-time dedup judge: restatements are superseded and the more specific row survives |

**Production evidence, read 2026-10-03:**

| Step | Evidence | Read |
|---|---|---|
| Schema | `alembic_version` = **`073_memory_echo_strength`**, the code's single head | SELECT |
| B1 | **First recurrence card with evidence**: `pattern`, `evidence->>'kind' = 'recurrence'`, written 13:48:57 UTC. The backlog's 2026-10-03 read had found no recurrence card since #642 | SELECT |
| B1b | `insight_gate kind=recurrence decision=allowed …` and `Memory task: stored 2 entries …` appear in the worker log at 16:19:19 | Render logs |
| B2 | `verdict_history` is non-NULL on **2** insights; **0** `insight_verdict_shift` rows (none can be owed yet: a shift needs a no→yes 72h apart) | SELECT |
| B3 | A `dilemma` card with `kind = 'signal'`, 13:48:40 UTC | SELECT |
| B4 | **4** rows with `echo_count` set (1 each), stamped 13:48:57 and 13:59:35 UTC | SELECT |
| B5 | Deployed 16:08:58 UTC. One exchange since (16:19 UTC, the founder's smoke) wrote 2 chat rows. Their best eligible candidates scored **0.582** and **0.516**, under the 0.75 gate, and the two scored **0.581** to each other, under 0.90. So no judge call and no drop was correct. The log shows no Anthropic request between the commit and the recurrence gate. `superseded` chat rows: **0** | SELECT + logs |

**Memory, production, 2026-10-03:**
- 1,071 active rows: `system_inferred` 750, `user_selected` 307, `user_stated` 14.
- 22 inactive, **all** `superseded`.
- **0** `user_rejected`: R3 has still never fired in production.
- 34 insights, 2 of them with evidence (both written today).

### 1a. Watch — B5 post-merge observables

What to look for in the philosopher-worker log and the database. None of these has
fired yet; that is expected after one exchange.

- **`dedup_judge verdict=RESTATEMENT … chain_depth=N`.** The first real supersession. Then:
  `SELECT count(*) FROM memory_entries WHERE inactive_reason='superseded' AND source_surface='chat'`
  should become non-zero. **The RESTATEMENT path has not run in production yet.** Only
  the live-Postgres tests have exercised it.
- **`chain_depth` distribution.** Long chains are where a wrong retirement would hide.
  The ratchet guard should keep depth growth to rows the judge called more specific.
- **`note=dedup_ratchet_guard`.** How often the guard holds.
- **`verdict=CONTRADICTION`** (WARNING). The calibration found zero in 30 pairs, so any
  occurrence is worth reading.
- **`verdict=error`** (fail-open fired) and `dedup_judge_failed kind=…` (ERROR, with a
  traceback).
- **Cost.** One Haiku call per candidate at ≥0.75, at most 3 per new row. The cap of 3
  rows per extraction is in the prompt only (the code does not enforce it), so "≤9
  calls per exchange" is an expectation, not a bound. Accepted (#780 PR body).

**Known gaps, named rather than discovered later:**
1. **A row with no candidate writes no log line.** "B5 ran and found nothing" and "B5
   did not run" look the same in the log; today's smoke had to be confirmed from the
   absence of an Anthropic request. A one-line per-call summary would close this, in
   its own PR.
2. **A 'no' (R3) does not follow supersession.** The recall outcome is the same as
   before B5 (an uncited duplicate already survived a 'no'). Recorded in the backlog as
   a possible separate PR.
3. **`more_specific` has a measured order bias** toward the note shown first, which in
   production is the stored row (#4/#15 of the calibration). Accepted as calibrated and
   documented at `dedup_judge.parse_reply`. The ratchet guard bounds its effect.
4. **Kill switch:** `MEMORY_DEDUP_ENABLED=false` on the worker restores the pre-B5 path
   exactly. It is unset on both services today, so the default is on (Render API,
   2026-10-03).

### 1b. The rest of the cycle — an index, not a narrative

147 merges cannot be re-told here at the standard of §1 without becoming exactly the
copied text the 2026-08-18 entry warns about. This is an **index by PR title**,
verified only as "merged on `main` with this title" (`git log`). Each thread's detail,
and its verification, lives in the backlog entry its PR cites.

| Thread | PRs |
|---|---|
| Privacy and data rights (TD-59, TD-62, TD-72) | #636–#640 |
| Insight loop and letters: evidence, period recurrence, trajectory snapshots, ring-true, letter continuity, `_is_null_reply` removed | #634, #642–#644, #646, #647, #652, #654–#656, #659, #663, #664 |
| Limits and billing: free 10/day global (A2), Stripe Tax flag, Pro monthly ceiling, another-mind counted, dunning email fix | #649, #724–#726, #753 |
| Ops and reliability: nightly encrypted backup, pool pre-ping, worker absence alerting, OBS-001, OBS-002 | #650, #651, #668, #669, #772, #774 |
| Product surfaces: resume thread, Return to this, paywall batch, disclaimer, SEO, auth hydration gate, UI polish, nav feedback, share loop | #658, #661, #670, #671, #674–#677, #680, #681, #685, #686 |
| Memory and retrieval before MEM2: D3 recall diversity, corpus id fix, retrieval off the reply path | #666, #683, #775 |
| Evals and voice: harness, judges, placement arms, arm E shipped, persona voice fixes | #698–#702, #704, #706, #708–#711, #713, #715–#719, #722 |
| Personas and prompts: 057 backfill, misattributions, persona lexicon wired, brevity band, PROMPT-002 | #684, #689, #690, #692, #694, #705 |
| Safety: SAFETY-001 … SAFETY-012, crisis numbers, post-generation safety, context judge, HARD RULES 9–10 | #667, #727, #731, #732, #739–#741, #743, #746, #749, #750, #752, #755, #757, #759, #762, #764, #767, #768 |
| CI, tests and gates: live-test timestamptz binding, web CI gate, typecheck as a gate, self-hosted fonts, ruff F821, baseline-checker fix | #645, #679, #736, #738, #754, #761 |
| Process and docs | every other PR in the range, including #648 (handoff v30) and #770 (merge protocol) |

---

## 2. Verified state — every row executed or read at `cd38ba8b`

| Claim | Method | Result (v29 at `93aa0693`) |
|---|---|---|
| Backend suite | `pytest -q` executed | **4114 passed, 225 skipped, 0 failed** (1716 / 45) |
| CI failure baseline | `tests/ci_baseline_failures.txt`, non-comment lines | **0** entries |
| Web unit suite | `vitest run` (node v20.18.1, exit 0) | **628 passed / 628**; 76 / 76 files (13 failed / 272 passed) |
| Web typecheck | `tsc --noEmit` (exit 0) | **0 errors** (11). A merge gate since #736 |
| Alembic | `alembic heads` | single head **`073_memory_echo_strength`** (`059_job_run`) |
| Alembic, production | `SELECT version_num FROM alembic_version` | **`073_memory_echo_strength`**, matching the code |
| Migration naming (C-04) | script over `db/migrations/versions` | **73 files, 0 over 32 chars**; longest `024_saved_line_conclusion_source` (32); **2** documented filename≠revision exceptions (`013`, `014`) |
| RLS (C-05), production | `pg_tables.rowsecurity` | **40 / 40** public tables enabled; none disabled |
| API surface | `openapi()` in-process | **100 paths / 121 operations** (93 / 113) |
| ARQ tasks | `len(WorkerSettings.functions)` | **14** (12) |
| ARQ cron jobs | `len(WorkerSettings.cron_jobs)` | **7** (4) |
| ARQ timezone | attribute read | `UTC` |
| APScheduler jobs | `id="…"` in `workers/cron.py` | **6**: `daily_rituals`, `stripe_reconcile`, `future_self_emails`, `weekly_mirror`, `preview_mirror`, `job_expectations` (+1, from #669) |
| Question bank | parsed | **360 / 360 weighted** |
| Personas | `PERSONA_REGISTRY` | **11**; **3** `tier="free"` (`lao_tzu`, `marcus_aurelius`, `socrates`) |
| Persona forbidden lexicons | `forbidden_lexicon_persona_specific` counted | **11 / 11** |
| Safety lexicons | four bands imported and counted | **372** entries: HIGH 240, MEDIUM 52, OUTPUT 28, LOW 52; **127** contain Greek script (219 / 76). See §3a |
| Universal forbidden lexicon | `len(_UNIVERSAL_PHRASES)` | **196** across **12** categories (210). See §3b |
| Prompts stating a computed language | `language_directive(` call sites, non-test | **17** (17) |
| Free reply limit | `rate_limit_service` constants | `FREE_DAILY_LIMIT = 10`, **global**, not per persona (#649) (5 per persona × 3) |
| Pro fair use | constants | `PRO_DAILY_FAIR_USE_LIMIT = 150`; `PRO_MONTHLY_FAIR_USE_LIMIT = 400` (new, #725) |
| Live-DB tests | `pytest tests/db_live --collect-only` | **240 tests** across **20** files (45 / 4) |
| Stale-`running` threshold | `letter_dispatch.STALE_RUNNING_AFTER` | 2 hours |
| Upgrade page price | `apps/web/app/app/upgrade/page.tsx:153` | still **"€99.99 / year"** (OPS-006 unchanged in code) |
| Greek crisis numbers | `grep -c 1018 prompts/safety_response_el.jinja2` | **2**: 1018 and 10306 now present (0; #667) |
| `_is_null_reply` | grep, non-test | **0** occurrences: removed (#634) |
| Insight→counterview door | `routers/memory.py` | **capped**: `check_fair_use_limit` imported and called (#635) |
| `.env.production` | `git ls-files` | untracked |
| `metadataBase` | `layout.tsx:66,71` | `NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'` |
| Deployed SHA | Render API, latest deploy per service | **philosopher-api** and **philosopher-worker** both `live` at `cd38ba8b`, 16:08:58–16:09:11 UTC |
| Worker alive after the deploy | `job_run` heartbeat | last heartbeat 16:20:01 UTC |
| Remote branches | `git ls-remote --heads origin` | **17**: `main` + 16 others (1). See §3d |

### 2a. Previously FOUNDER-REPORTED, now verified

v29 listed these as unverified. This rotation checked them:

| v29 item | Method | Result |
|---|---|---|
| `api.thewiseroom.app` serves the API | `curl https://api.thewiseroom.app/health` | **200** |
| `FROM_EMAIL` set on both services | Render env (value is an address, not a secret) | both: `The Wise Room <hello@thewiseroom.app>` |
| Worker and API deployed at a recent SHA | Render deploys | both at `cd38ba8b` |
| Migrations applied on production | `alembic_version` | `073`, so 055–073 are all applied |
| Sentry initialised in production | Render env, key presence only | `SENTRY_DSN` set on **both** services. Initialisation itself is not observed |
| `BETA_GRANT_PRO_TO_ALL` in production | Render env | **api `false`, worker `true`**. See §3c |
| `PUBLIC_ASSET_BASE_URL` (#629) | Render env | both: `https://thewiseroom.app` |

### ⚠️ Still FOUNDER-REPORTED — not verified by this rotation

1. **Google OAuth enabled and brand-verified.**
2. **OPS-006:** the live-mode Stripe price objects. The page still displays €99.99/year.
3. **Email deliverability.** `FROM_EMAIL` is set; arrival in an inbox is not observed.
4. **The "1.85× the heaviest usage day" figure** behind the fair-use cap. Not re-read.

---

## 3. Corrections and changes against v29

v29's numbers were correct at `93aa0693`. Every change below is **attributed to the
commit that made it**, measured by counting at the commits on either side.

### 3a. Safety lexicons 219 → 372, in two steps

The same method v29 used (Greek-script regex over the four bands) gives v29's own
76 at `93aa0693`, so the comparison is like for like:

| at | HIGH | MEDIUM | OUTPUT | LOW | total | Greek-script |
|---|---|---|---|---|---|---|
| `93aa0693` (v29) | 95 | 50 | 22 | 52 | 219 | 76 |
| `ad84643b` (#740, input lexicon boundaries) | 149 | 52 | 28 | 52 | 281 | 106 |
| `cc714aae` (#750, continuation sweep) | **240** | 52 | 28 | 52 | **372** | **127** |

No other commit in the range touched `services/safety_lexicons.py`.

### 3b. Universal forbidden lexicon 210 → 196: a deliberate reduction

**#684** (word-bounded lexicon matching, UAT2-001) removed **14** entries.
`philosopher_brain/maps/universal_forbidden_lexicon.json`: 210 entries at
`cf9fd438~1`, 196 at `cf9fd438`, unchanged since. A reader comparing v29 to v30 without
this line would see a shrinking forbidden list and could read it as a regression. It is
not.

### 3c. FINDING — `BETA_GRANT_PRO_TO_ALL` differs between the two services

Read from the Render API on 2026-10-03: **`false` on philosopher-api, `true` on
philosopher-worker.**

By static reading this is **inert today**:
- `tier_service.get_user_tier` is the only reader of the flag;
- no module under `workers/` calls it;
- `workers/cron.py` mentions `tier_service` in a comment only;
- the worker's one import from `conversation_service` is a constant.

It is still a configuration that says two different things. A future worker task that
resolves a tier would silently treat every user as Pro. **Not changed by this rotation**:
production configuration is the founder's call, and the fix is one env-var edit on the
worker.

**CLOSED 2026-10-03, after this rotation's reads:** the founder set `BETA_GRANT_PRO_TO_ALL=false` on philosopher-worker and redeployed it (manual deploy of `cd38ba8b`, live 16:32:38 UTC); the Render API read at 16:35 UTC shows `false` on both services, so they now match.

### 3d. Remote branches 1 → 17

v29 closed NIKOS-ACTION 10 with `main` as the only remote branch. Today there are 16
others:
- `docs/ops-030-b-closed`, `docs/ops013-smoke-owed`, `docs/retrieval-001-finding`
- `evals/retrieval-forced-injection-arm`
- `feat/batch-e-ui-polish`, `feat/counterview-go-deeper-retry`, `feat/eval-arm-b`,
  `feat/greek-crisis-helpline`, `feat/insight-ring-true`, `feat/listening-calibration`,
  `feat/period-recurrence`, `feat/resume-thread`, `feat/share-loop-pr1`,
  `feat/share-loop-pr2`
- `fix/output-lexicon-word-bounded`, `fix/safety-003-crisis-text`

**Whether each is merged is NOT asserted.** Squash merges rewrite SHAs, so an ancestry
check answers nothing. They are left for the deferred branch-cleanup batch, which
re-maps each branch to its PR by title before deleting anything.

### 3e. `make state` retired

`Makefile`'s `state` / `state-help` targets and `scripts/generate_state.txt` are
deleted in this rotation:
- they wrote `docs/PROJECT_STATE_v4.md`, a file removed in #31 (2026-05-11);
- they ran a second Claude Code session against an open repository, which P-07 forbids
  by construction;
- `IMPLEMENTATION_BACKLOG_v8.md` had already recorded the target as broken in May
  ("`claude` CLI mismatch with founder's VS Code workflow"). That archived line stays
  byte-identical; it is cited here so the fact is found from the current document.

PROJECT_STATE documents are written by hand, and CLAUDE.md now says so.

---

## 4. Process change landed with this rotation

**Rotation trigger** (founder ruling 2026-09-24, now in CLAUDE.md § "Documentation
rotation"): **rotate at 30 merged PRs or at any migration, whichever comes first,**
counted from the merge of the previous rotation PR.

This rotation is owed many times over under that rule: 147 merges and 14 migrations
(060–073). The next one is owed at the first migration after this PR merges, or at its
30th merge.

---

## 5. What is not in this document

- **The open backlog.** `IMPLEMENTATION_BACKLOG_v29.md`, not rotated here. Its MEM2
  section is current to #780.
- **A per-PR narrative of #633–#780.** See §1b and the backlog entries each PR cites.
- **The handoff brief.** `HANDOFF_BRIEF_v30.md` (#648) is the last one, and predates
  most of this range.
