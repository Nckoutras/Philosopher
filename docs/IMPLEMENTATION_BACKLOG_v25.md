# THE WISE ROOM — Implementation Backlog v25

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
>
> **v25 = v24 baseline (2026-07-19, through PR #520) + 2026-07-19→2026-08-18 delta (#522–#548):** a **UAT-response rotation**. Nineteen of the twenty-seven PRs close a numbered tester finding. Two migrations (**052 RLS**, **053 token_version**), one new service (`safety_event_log`), two silent-data-loss incidents found from data.
>
> **Migration head 051 → `053_token_version`.**
>
> **⚠️ This file replaces an earlier, never-merged `IMPLEMENTATION_BACKLOG_v25.md`.** See §0.
>
> **Generated:** 2026-08-18 · **Current main `cace1016`**
>
> **How to read this file:** v25 supersedes v24 and all prior backlog files. Where v25 conflicts with v24, v25 wins. **Production reality always wins over docs.**
>
> **Companion documents:** `PROJECT_STATE_v25.md`, `HANDOFF_BRIEF_v25.md`, `SCREENS_TRACKING_v13.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

> ## ⚠️ PROVENANCE
>
> **Every item below is either VERIFIED THIS ROTATION with its method stated, or explicitly MARKED UNVERIFIED.** "Unchanged." is not used as evidence anywhere in this file. Items from v24 that could not be re-checked are marked **UNCARRIED** rather than restated.
>
> **Verification SHA `cace1016`** (`main` == `origin/main`, 0/0 divergence after `git fetch`). Methods: live code reads at that SHA; live queries against Supabase `bvzeuwzqgnqcghvqghtb`; **executed** `pytest`, `vitest` and `tsc`; `git log` derivation of the PR range.
>
> **Bounded-verification rule applied** — every grep or slice behind a claim was bounded at both ends with its occurrence count recorded.
>
> **This rotation's own PR number is deliberately not asserted.** See §0.

---

## 0. Why this file replaces one with the same name

**The v25 rotation was written 2026-08-06 and never merged.** It exists only on the local, unpushed branch `docs/v25-rotation` @ `b15811c0` (`git merge-base --is-ancestor b15811c0 main` → **NO**; `git ls-remote --heads origin docs/v25-rotation` → **empty**). `docs/` on `main` stopped at v24.

That document also asserted, four times, that **"#529 is this rotation (docs only)"**. #529 is `16b213a7`, a product PR closing UAT A7. A document written to catalogue six unverified copied-forward claims made a false claim about **a PR that did not exist yet** — the same error aimed forward in time, and unverifiable by construction.

**Rule now in force:** a rotation document states the range it covers and never asserts the number, content or existence of its own PR or any unmerged PR.

The old branch was **mined, not merged** — claims re-verified at `cace1016` were carried with their method; the rest were dropped.

---

## 2026-08-18 Consolidation Summary — UAT response · letters · auth · safety · RLS codified

> Appended as v25. Where this conflicts with earlier sections, this section wins. **Current main `cace1016`.**

**Code shipped (merged to main; #522–#548):**

| Area | What shipped | PRs |
|---|---|---|
| **Chat context** | Newest-N window fix → cache anchor → **growing, budget-bounded window** | #522, #532, #533 |
| **Letters — write-backs** | Honest copy; write-back survives a voice re-election; monthly cadence too; feeds the memory pipeline | #531, #534, #541, #538 |
| **Letters — resilience** | Malformed LLM JSON: shared parser, one retry, visible failure row — then extended to mirror + insight | #544, #546 |
| **Letters — eligibility** | Rituals count as activity for both weekly and season letters | #545, #547 |
| **Auth** | `POST /auth/refresh` (session survives); `token_version` revocation + migration 053 | #535, #543 |
| **Rate limits** | CORS `expose_headers`; `X-RateLimit-Reset` on council + you-vs-you | #536, #540 |
| **Council** | The matter is framed as a person's matter, not a text to appraise | #530 |
| **Persona voice** | The AI-disclosure line reframed from a proposition to a constraint | #529 |
| **Safety** | One `SafetyEvent` writer; six new ritual call sites | #548 |
| **Database** | Live RLS posture codified as migration 052 | #542 |
| **Copy / infra** | Pricing strings aligned; lockfile synced with declared jsdom/RTL deps | #539, #537 |

**Migrations:** 052, 053. **Dependencies:** frontend lockfile sync only (no `package.json` change). **New screens:** none.

---

## 1. Current Launch Interpretation

The revenue chain's remaining work is **operational plus one code gap**:

- **Operational:** live keys, a live-mode webhook, `ENVIRONMENT=production`, `API_BASE_URL`, and the OPS-002/003 data decisions.
- **Code/config gap (NEW):** **OPS-006** — the Stripe price objects still hold the old amounts. #539 aligned only the displayed strings.

**⚠️ `BETA_GRANT_PRO_TO_ALL`'s production value is UNVERIFIED** (§3, UNVERIFIED set). The sequencing of the key switch depends on it and it has not been determined.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate — before or alongside the next code PR

- 🔴 **Land the `CLAUDE.md` dual-tier correction.** Its own PR (P-02). Exact line range **314–325**; full detail in `HANDOFF_BRIEF_v25.md §"NEXT-SESSION QUEUE"`. Written 2026-08-06, lost once already.
- 🔴 **Smoke test the eighteen unseen fixes (P-03).** Eighteen user-facing fixes are live in production and **not one has been confirmed by a human**. This is now the largest unmanaged risk in the project.
- ✅ ~~`.gitignore` / `.env.local`~~ — **REMOVED. Was never real.** See §3 CORR-11.

### 2.1–2.5

**UNCARRIED from v24** — not re-verified this rotation, so not restated. Two changes are certain: **RLS is not a blocker** (verified live, and now durable via 052), and **`.env.local` is not a blocker** (CORR-11).

### 2.6 Pending verification set (run before cold beta)

- **The eighteen unseen fixes** — see the priority list in `HANDOFF_BRIEF_v25.md`.
- **Letters actually arriving.** Three defects this rotation (A17, A18, A8) shared the shape "system reported success or nothing; user received nothing", and all three were found by querying data. **Nothing currently watches delivery.**
- **Android keyboard on a real device** (A1) — live since 2026-08-06, never run on hardware.
- Carried from v24 and **not re-verified**: Dimitris repetition retest, empathy mini-eval, cache-read confirmation (TD-44), PR3a memory bugs.

---

## 3. Tech debt items

### CORR — Corrections to prior docs (v25)

Verified at `cace1016`; methods stated. Full text in `PROJECT_STATE_v25.md §19.1`.

- **CORR-09** — the v25 rotation was never merged (§0). **CORR-10** — a document asserted a fact about a PR that did not exist (§0).
- **CORR-11** — `.env.local` git-ignored since 2026-05-28; on the P0 blocker list for **twelve rotations**; true for the length of **one commit** (`#131` → `#132`, same day).
- **CORR-12** — Node v20.18.1 / npm 10.8.2 exist at `C:\clwn\node-v20.18.1-win-x64`.
- **CORR-13** — "jsdom missing" was a lockfile fact; it was in `package.json:37` all along.
- **CORR-14** — no local Postgres usable for Philosopher (`role "philosopher" does not exist`; no pgvector).
- **CORR-15** — TD-47's production type-error count is **4**, not 8.
- **CORR-16** — `MIRROR_PROMPT` (`:147`) read as `MONTHLY_PROMPT` (`:95`) via a slice bounded only at its start.
- **CORR-05 / CORR-06** — re-verified with method, not copied.

### ⚠️ UNVERIFIED set — four items, not softened

- ⚠️ **`BETA_GRANT_PRO_TO_ALL` production value.** Code default `False` (`config.py:50`); the live value is a Render env var and is **not determined**.
- ⚠️ **OPS-004** — the API's database role. Not directly verified; `DATABASE_URL` not in the repo.
- ⚠️ **TD-44** — `cache_read > 0` never confirmed in production logs.
- ⚠️ **A1** — Android keyboard fix never run on a device.

**No longer in this set — the 49 / 13 split is VERIFIED.** Method: `npx vitest run` executed at `cace1016` with and without `globals: true` — **62 failed → 13 failed** (54 → 103 passed; 16 → 6 files). The split is measured, not inferred from the 2026-08-13 report. See TD-51.

### A18c — Ring-true notes are never safety-checked at write time (P1, NEW)

**Verified at `cace1016`.** `routers/mirrors.py` contains **1** occurrence of "safety" — a **comment** at `:100` describing gating inside a *downstream* memory task. There is **no safety call in the file**. `mirror.ring_true_note = body.note` is persisted unchecked at `:93`.

The only place that text is ever checked is the weekly/monthly letter block — and per **A18b's locked decision** that the originating surface owns the record, that check writes **no `SafetyEvent`**. A user's own words therefore enter the system, are stored and are surfaced back with no safety record anywhere.

**⚠️ SIBLING — do not fix A18c alone.** `routers/self_comparison.py` contains **0** occurrences of "safety"; its `set_ring_true` handler (`:85-102`) writes `row.ring_true_note = body.note` at `:101` with the same absence of a check. **Two ring-true surfaces, one reported.** Fixing only the reported one reproduces the A17 → A17b pattern for the third time this rotation.

Logged in #548's PR description.

### TD-50 — There is no backend CI at all (P1, NEW)

**Verified:** `.github/workflows/` contains **exactly one** file, `web-build.yml`, triggered only on `apps/web/**` paths and `.github/workflows/web-build.yml`.

Four independent consequences:

1. **`pytest` never runs in CI.** The 29 red backend tests are invisible to everyone except a human running them locally — and this machine is the only place that happens.
2. **Nothing enforces C-04** (revision id ≤ 32 chars; filename == revision id). That rule exists *because* violating it crashed a production deploy (#371).
3. **Nothing enforces a single migration head.** A branch-point would surface at deploy time.
4. **The web job runs `npm install`, not `npm ci`** — so #537's lockfile sync is not enforced by the very job that motivated it. A drifted lockfile passes.

**Smallest useful fix:** a backend job running `pytest`, plus `alembic heads` asserting exactly one head, plus a revision-id length check. Switch the web job to `npm ci` in the same PR or the next.

**This is the largest structural gap on the list.** It is why TD-45 can sit at 29 red for rotations without anyone noticing.

### TD-51 — RTL auto-cleanup never registers (P1, NEW number, pre-existing defect)

**Verified:** `apps/web/vitest.config.ts` contains **0** occurrences of `globals: true`; `cleanup()` appears **0** times anywhere in `apps/web` outside `node_modules`.

`@testing-library/react` registers auto-cleanup only inside `if (typeof afterEach === 'function')`. Without `globals: true` that guard fails, cleanup never registers, and every `render()` appends a container to `document.body` that is never unmounted — so `screen.*` queries, which search the whole body, see all prior renders.

**49 of the 62 frontend failures are this one config line — VERIFIED BY EXECUTION, not inferred.** Method: `npx vitest run` executed at `cace1016` twice, with and without the config line:

| | Tests | Files |
|---|---|---|
| Baseline | **62 failed / 54 passed** (116) | 16 of 24 failing |
| With `globals: true` alone | **13 failed / 103 passed** (116) | 6 of 24 failing |

**The fix is exactly one line — `globals: true` in `apps/web/vitest.config.ts`.** Nothing else.

- **No `cleanup()` in `vitest.setup.ts`.** `@testing-library/react` registers its own `afterEach` cleanup as soon as a global `afterEach` exists, so the config line is sufficient on its own. Adding a manual `cleanup()` would also pull `@testing-library/react` (and `react-dom`) into the **4 node-environment test files that do not need it**.
- **No `tsconfig` change.** Every test file imports `describe` / `it` / `expect` explicitly, so no ambient global types are required.

The remaining **13** are stale assertions against components that have since changed — `EmptyReflections` copy, `DateGrouper` styling, the `QuickActionsRow` "Ask harder" chip, the `SavedLineCard` portrait fallback, and 3 in `chat/conv/[id]`. **They are a separate PR** and must not be bundled with the config line.

### OPS-006 — Stripe price objects still hold the old amounts (P0-revenue, NEW)

#539 aligned the **displayed strings** — verified at `cace1016`: `€99.99 / year` (`upgrade/page.tsx:56`), `€11.99 / month` (`:77`), and the Terms billing sentence (`terms/page.tsx:65`).

The commit body of `246a37c0` states plainly: `STRIPE_PRICE_PRO_MONTHLY` / `STRIPE_PRICE_PRO_YEARLY` **"still point at the old price objects — must be recreated at €11.99/€99.99 before the live-key switch."**

**The app currently displays one price and would charge another.** First item in the TD-28 operational sequence.

### TD-45 — Index-based DB test harnesses (P1, carried, RE-VERIFIED)

**Re-verified by execution** at `cace1016`: **`29 failed, 513 passed`** (542 total). Composition unchanged from the prior measurement:

| File | Failures |
|---|---|
| `tests/services/test_conversation_service.py` | 17 (2 `daily_usage`, 7 `auto_title`, 3 `llm_*`, 5 `memory_extraction`) |
| `tests/routers/test_share.py` | 4 |
| `tests/test_postprocessing.py` | 3 |
| `tests/test_conversations.py` | 2 |
| `tests/services/test_counterview_rebuttal.py` | 2 |
| `tests/routers/test_conversations.py` | 1 |

Cause: the mocks use ordered `execute()` side-effect lists with **hard-coded call indices**, so inserting any query ahead of the one under test shifts every index and the harness silently asserts against the wrong statement.

**Billing counters, auto-title cadence, LLM retry and memory extraction have no working coverage.** A red suite is worse than no suite — it trains everyone to ignore the output. **Fix:** shape-based dispatch; the pattern already exists in the file (`_is_history_query`). **Compounded by TD-50** — nothing in CI reports this.

### TD-47 — `npm run build` validates nothing (P1, carried, RE-VERIFIED)

**Re-verified:** `apps/web/next.config.js` sets `typescript.ignoreBuildErrors: true` and `eslint.ignoreDuringBuilds: true`. The production build succeeds on code that neither typechecks nor lints; a green Netlify check proves only that a bundle was produced.

**Real numbers, executed at `cace1016`:** 11 typecheck errors — **4 production** (`app/app/(tabs)/account/page.tsx:112,114,117` TS18047; `app/auth/oauth/finish/page.tsx:33` TS2345) and **7 test-file**. The previously stated "8 production" was wrong (CORR-15). **Four errors in two files is a small enough fallout that removing `ignoreBuildErrors` is a realistic near-term decision.**

### TD-46 / TD-48 / TD-49 (carried)

- **TD-46 (P1)** — vitest CI enforcement decision, still unmade. The measurement exists (#525 + the #537 report); the decision does not. Pairs with TD-47 and TD-51.
- **TD-48 (P2)** — Stripe webhook has no idempotency or event ordering. No processed-event store; `event["id"]` never read. Duplicate delivery double-counts `subscription_activated`; out-of-order delivery can **resurrect a cancelled subscription**. **Deferred until real payment traffic, by decision.** Last known correctness gap in billing. **Not re-verified this rotation** — carried from the prior session's reading.
- **TD-49 (P3)** — vestigial `userPlan` params. **Verified: 4 occurrences** in `apps/web/lib/api.ts` (`:940` `streamMessage`, `:970` `streamAnotherMind`, `:1003` `streamGoDeeper`, plus the explanatory comment at `:937`); 5 repo-wide in `apps/web`. Harmless. Clean up next time those files are touched.

### TD-01 through TD-44

**UNCARRIED** — not re-verified this rotation, so not restated. See `IMPLEMENTATION_BACKLOG_v24.md §3` and treat that content as unverified. Two exceptions carried **with method**: **TD-44** remains unconfirmed (UNVERIFIED set above), and **TD-28** now has OPS-006 as its first operational step.

---

## 4. Database schemas

**Two migrations this rotation.** Head **`053_token_version`**, verified two independent ways (chain read: 53 revisions, 52 down_revisions, exactly 1 head, 0 duplicates, 0 branch points; live `alembic_version` query — agreeing).

- **052_enable_rls** (#542) — codifies the live posture: RLS on **34 literal, named** tables, zero policies, no FORCE. No-op against production by construction. `alembic_version` excluded deliberately, so a rebuilt database reports 34 and production reports 35 — both correct. Establishes **C-05**.
- **053_token_version** (#543) — `users.token_version`, additive, `NOT NULL DEFAULT 0`. **Verified live:** `integer | NO | 0`.

RLS state and the subscription-row inventory: see `PROJECT_STATE_v25.md §4`, both re-measured live this rotation.

### C-05 — new convention (locked)

**Every future migration that creates a public table must enable RLS on it in the same migration.** 052 is a one-time catch-up for 001–051, not a pattern to re-run. It retrofits nothing: 001–051 stay byte-identical.

---

## 5–10.

**UNCARRIED from v24** — not re-verified this rotation. See `IMPLEMENTATION_BACKLOG_v24.md`.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work (do first)

- 🔴 **`CLAUDE.md` dual-tier correction** — own PR, lines 314–325, detail in `HANDOFF_BRIEF_v25.md`.
- 🔴 **Smoke-test the eighteen unseen fixes** (P-03).

### 11.1 P0 (launch blockers)

- 🔴 **OPS-006 (NEW)** — recreate the Stripe price objects at €11.99/€99.99. Display and charge currently disagree.
- 🔴 **A8 (UAT, NEW to this list)** — the sign-in screen does not distinguish login from signup. **Not cosmetic:** the tester made three accounts by accident, her activity is split across two, and a weekly letter went to the **accidental** account on 2026-08-09 while her real account got none. Verified by live query this cycle.
- 🔴 **TD-28 operational remainder** — live keys, live price IDs (OPS-006), live-mode webhook, `ENVIRONMENT=production`, `API_BASE_URL`.
- 🔴 **OPS-002 / OPS-003** — decide before the key switch so post-switch logs are readable.
- 🔴 Carried, **not re-verified**: cold beta, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, UAT completion, PR3a memory bugs, source_chunks re-ingest, post-Oregon smoke test.
- ✅ **RLS** — not a blocker (verified live; durable via 052). ✅ **`.env.local`** — never was one (CORR-11).
- 🟢 **Pricing — LOCKED 2026-08-06.** Single Pro tier, **€11.99/mo · €99.99/yr**, no trial, no founding discount, no Premium in v1. **⚠️ The UAT willingness-to-pay validation was deliberately NOT run** — cost model plus competitive analysis only. A named, accepted risk. Copy now matches; **the price objects do not** (OPS-006).

### 11.2 P1 (post-revenue)

- **A18c + its sibling** — safety-check both ring-true write paths in **one** PR.
- **TD-50** — stand up backend CI (`pytest`, single-head check, revision-id length check; `npm ci` for web).
- **TD-51** — `globals: true` in `apps/web/vitest.config.ts`, **one line, nothing else**. Measured: clears 49 of the 62 frontend failures (62 → 13). No `cleanup()`, no tsconfig change. The remaining 13 stale tests are a separate PR.
- **TD-45** — repair the 29 red harnesses via shape-based dispatch.
- **TD-46 / TD-47** — the enforcement decisions. TD-47's real fallout is 4 production errors in 2 files.
- **OPS-002 / OPS-003** — the stale subscription rows (7 rows re-verified live).
- **OPS-004 (verification)** — confirm the API's database role. ⚠️ UNVERIFIED.
- Carried: **OPS-001** (ote.gr re-sync), **TD-44** cache-read (⚠️ UNVERIFIED), **TD-43** ritual_id FK.
- ✅ **OPS-005 — CLOSED** by migration 052.

### 11.3 P2

- **TD-48** webhook idempotency + event ordering (deferred until real payment traffic).
- Carried and **not re-verified**: TD-37, TD-39, TD-40 (CONDITIONAL), TD-41, TD-42, and the v24 tuning set.

### 11.4 P3 / 11.5 P4

- **TD-49** vestigial `userPlan` params (4 occurrences in `lib/api.ts`).
- **CORR-08 follow-up** — the two stale `zoom: 1.15` comments. **Not re-verified this rotation** — confirm against `globals.css:57` before acting.
- **Open UAT:** A3 Self-Portrait stall (needs logs) · A4 "Next" discoverability · A6 Jung latency (needs measurement).
- Otherwise **UNCARRIED** from v24.

---

## 12. Plan A vs Plan B

**UNCARRIED from v24** — not re-verified this rotation.

---

**End of IMPLEMENTATION_BACKLOG v25.** Authoritative as of 2026-08-18 at `cace1016`. Supersedes `IMPLEMENTATION_BACKLOG_v24.md` (preserved byte-identical). Replaces the never-merged `docs/v25-rotation` draft, which was mined for re-verifiable claims and not merged.
