# HANDOFF BRIEF v25 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-08-18
**Prior version on `main`:** `docs/HANDOFF_BRIEF_v24.md` (2026-07-19)
**Verification SHA:** `cace1016`

**Block trigger for this rotation:** 27 product/infra PRs (**#522–#548**) landed since the v24 doc, which stopped at PR #520 / `faa18600`. Nineteen of them close a numbered UAT finding. Two migrations (052 RLS, 053 token_version), one new service, and two silent-data-loss incidents.

---

> ## ⚠️ PROVENANCE — read before trusting anything below.
>
> **Every claim here is either VERIFIED THIS ROTATION with its method stated, or explicitly MARKED UNVERIFIED.** The word "Unchanged." is not used as evidence anywhere in this document. Claims from prior docs that could not be re-checked were **dropped**, not carried.
>
> **Verified at `cace1016`** (`main` == `origin/main`, 0/0 divergence, after `git fetch origin`) by: live code reads at that SHA; live queries against Supabase `bvzeuwzqgnqcghvqghtb`; **executed** backend `pytest` and frontend `vitest` + `tsc`; and `git log` derivation of the PR range.
>
> **Bounded-verification rule applied throughout** — every grep or slice behind a claim was bounded at both ends with its occurrence count recorded.
>
> **Four items are UNVERIFIED and named as such** in §"UNVERIFIED". They are not softened anywhere else.
>
> **This rotation's own PR number is deliberately not asserted anywhere in this file.** See §0 — that is the mistake being corrected.

---

## 0. ⚠️ READ THIS FIRST — the v25 that never existed

**A complete v25 doc rotation was written on 2026-08-06 and never reached the repository.** It lives on a local, unpushed, unmerged branch `docs/v25-rotation` @ `b15811c0`. Method: `git merge-base --is-ancestor b15811c0 main` → **NO**; `git ls-remote --heads origin docs/v25-rotation` → **empty**.

For twelve days the documented state on `main` was v24 while everyone believed it was v25. The corrections that rotation caught — RLS, dual tier resolution — were never applied to anything. **The `CLAUDE.md` fix it contained is still not landed** (see the top of the next-session queue).

**And the perfect miniature of the whole problem:** that document asserted, four times, that **"#529 — this rotation (docs only). Self-referential; no product surface."** #529 is `16b213a7`, `fix(prompt): stop the persona announcing it is an AI` — a product PR closing UAT A7. The document reserved a number for itself, said what was in it, and was wrong.

A document written to catalogue six claims copied forward without verification made a claim about **a PR that did not exist yet** — the same error, pointed forward in time. A claim about the future is unverifiable by construction; nothing would ever have caught it.

**Rule now in force:** a rotation document states the range it covers. It never asserts the number, content, or existence of its own PR or of any unmerged PR. If the number matters, record it after the merge.

**This file is that rotation, redone and extended**, renumbered v25 covering **#522–#548**, so the chain on `main` runs v24 → v25 with no gap. The old branch was **mined, not merged**.

---

## ✅ CORRECTIONS this rotation

Each with the method that established it.

1. **CORR-09 — the v25 rotation was never merged.** §0 above. The headline finding.
2. **CORR-10 — a document asserted a fact about a PR that did not exist.** §0 above.
3. **CORR-11 — `.env.local` has been git-ignored since 2026-05-28.** It sat on the P0 "do before any PR" blocker list for **twelve rotations**. Method: `git check-ignore -v .env.local` → `.gitignore:12:.env.*	.env.local`. **The history is the finding:** the claim was true when written in v13 (`#131`, 2026-05-28) and fixed by **`#132`, the very next commit, the same day** (`git rev-list --count 9fabf0aa..8e073e9d` = 1). A blocker true for the length of one commit, tracked for three months.
4. **CORR-12 — there IS a Node runtime on this machine.** Node **v20.18.1** / npm **10.8.2** at `C:\clwn\node-v20.18.1-win-x64`, verified by executing both. The prior doc said vitest and `tsc` "cannot be run locally at all" and instructed "do not claim a frontend test passes". Both wrong — this rotation ran the frontend suite twice.
5. **CORR-13 — "jsdom missing" was a lockfile fact, not a manifest fact.** Declared in `package.json:37` all along; absent from `package-lock.json` until #537. The break was `npm ci`, not the dependency list.
6. **CORR-14 — there is no local Postgres usable for Philosopher.** The PG 16.4 cluster at `C:\clwn\pgdata` reports `FATAL: role "philosopher" does not exist` and `ERROR: extension "vector" is not available` (no pgvector). The neighbouring `C:\clwn\cleo-wholesale` is a different product. Server not currently running.
7. **CORR-15 — TD-47's "8 production type errors" is 4.** Method: `npm run typecheck` executed at `cace1016`. 11 total, 4 production, 7 test-file. The "8" most likely counted raw output lines.
8. **CORR-16 — MIRROR_PROMPT was read as MONTHLY_PROMPT.** `MONTHLY_PROMPT` at `arq_worker.py:95`, `MIRROR_PROMPT` at `:147`. A slice bounded only at its start runs from one into the other. Exactly what the bounded-verification rule exists to prevent — and it happened anyway.
9. **CORR-05 re-verified, CORR-06 re-verified** — RLS re-measured live; dual-tier closure re-read at `auth.py:62-69`. Both carried **with method**, not copied.

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **🔴 THE `CLAUDE.md` CORRECTION — first item of the next session.** See the queue below. It is a two-minute PR and it has already been lost once.
2. **🔴 A8 is open and is costing a real user her letters.** The sign-in screen does not distinguish login from signup; the tester made three accounts by accident. Live query confirms her activity is split across two, and a weekly letter went to the **accidental** account on 2026-08-09 while her real account got none.
3. **🔴 A18c is open — and it has an unreported sibling.** `routers/mirrors.py` has **0** safety calls (its 1 "safety" string is a comment at `:100` about a downstream task); the ring-true note is stored unchecked at `:93`. **While verifying it, `routers/self_comparison.py` was found with 0 occurrences of "safety" and the same unchecked write at `:101`.** Do not fix one without the other — that is the A17 → A17b pattern for the third time.
4. **🔴 There is no backend CI (TD-50).** `.github/workflows/` contains **exactly one** file, `web-build.yml`, scoped to `apps/web/**`. `pytest` never runs in CI; nothing enforces C-04 or a single migration head; and the web job uses `npm install`, not `npm ci`, so #537's lockfile sync isn't actually enforced.
5. **🔴 29 backend tests are red (TD-45).** Re-verified by running: `29 failed, 513 passed`. Hard-coded `execute()` call indices in the mock harnesses. Billing counters, auto-title cadence, LLM retry and memory extraction have **no working coverage**. Combined with TD-50, nothing would ever report this except a human running pytest locally.
6. **🔴 62 frontend tests are red — 49 of them are one config line (TD-51).** `vitest.config.ts` has **0** occurrences of `globals: true`, so RTL's auto-cleanup never registers, and `cleanup()` is called **0** times anywhere in `apps/web`. Containers accumulate in `document.body` and `screen.*` sees every prior render.
7. **🔴 `npm run build` validates nothing (TD-47).** `ignoreBuildErrors` + `ignoreDuringBuilds` both true. A green Netlify check proves only that a bundle was produced.
8. **🔴 The Stripe price objects still hold the old amounts (OPS-006).** #539 fixed the *strings*. `STRIPE_PRICE_PRO_MONTHLY` / `_YEARLY` must be recreated at €11.99/€99.99 before the key switch — the commit body of `246a37c0` says so. The app currently displays one price and would charge another.
9. **🔴 Nothing watches whether letters arrive.** Three defects this rotation (A17, A18, A8) were found by querying data, never by a person using the app.

---

## 🔴 NEXT-SESSION QUEUE — item 1 is non-negotiable

### 1. Land the `CLAUDE.md` dual-tier correction (its own PR, nothing else in it)

Written 2026-08-06, never landed. The false text has been shaping briefs for months, and P-02 says one logical change per PR — so this ships alone.

- **File:** `CLAUDE.md`
- **Exact line range:** **314–325**, verified at `cace1016`
- **Currently there (FALSE):** `### Dual tier resolution (added PR4j-paywall-audit, 2026-05-23)` — claims `get_current_user_plan` and `get_user_tier` "are two parallel tier-resolution functions with different semantics", that `get_current_user_plan` "returns `"free" | "pro" | "premium"` from `Subscription.plan` directly", and that "the duplication remains".
- **Why false:** `get_current_user_plan` has delegated to `get_user_tier` since **#203** (2026-06-03). Verified at [auth.py:62-69](apps/api/auth.py#L62-L69) — it is a thin FastAPI dependency wrapper returning `(user, tier)`.
- **Replacement:** mark the section CLOSED, keep the entry *because* it was carried open for eight rotations, and state the true shape: `tier_service.get_user_tier` is the single resolver; every enforcement point goes through it, including expiry/status validation and the `BETA_GRANT_PRO_TO_ALL` bypass; the deleted text was false from #203 onward.
- **A drafted version exists:** `git show b15811c0 -- CLAUDE.md`. **Read and re-verify it — do not merge that branch to obtain it.**
- **Also:** one Failure Log entry on the copied-claim disease (drafted in the same diff).

### 2–9, in priority order

2. **Smoke test, at last (P-03).** Eighteen fixes are live and **not one has been seen by a human.** Highest value first: chat continuity past 20 turns (#522/#533); a weekly letter actually arriving; sign-out revoking a session on a second device (#543); the paywall showing a real reset time (#536/#540); council answering the person not the text (#530).
3. **A8 — the login/signup screen.** Open, unfixed, and actively misrouting a real user's letters.
4. **A18c + its sibling** — safety-check both ring-true write paths in one PR.
5. **TD-50 — stand up backend CI.** Smallest useful version: `pytest` + a single-head alembic check + a C-04 revision-id-length check. Switch the web job to `npm ci` in the same breath or the following PR.
6. **OPS-006 — recreate the Stripe price objects** before anything else in the TD-28 sequence.
7. **TD-51 — add `globals: true` to `apps/web/vitest.config.ts`. One line. Nothing else in the PR.** **Measured, not estimated:** `npx vitest run` at `cace1016` with and without the line gives **62 failed → 13 failed** (54 → 103 passed; 16 → 6 files). **Do not add a `cleanup()` to `vitest.setup.ts`** — RTL registers its own `afterEach` cleanup the moment a global `afterEach` exists, so the config line suffices, and a manual `cleanup()` would drag `@testing-library/react` and `react-dom` into the 4 node-environment test files that don't need them. **No tsconfig change** either: every test file imports `describe`/`it`/`expect` explicitly. The remaining 13 are stale assertions (`EmptyReflections` copy, `DateGrouper` styling, `QuickActionsRow` "Ask harder", `SavedLineCard` portrait fallback, 3 in `chat/conv/[id]`) — **a separate PR**.
8. **TD-45 — repair the 29 red harnesses** via shape-based dispatch. The pattern already exists in the file (`_is_history_query`).
9. **Open UAT:** A3 Self-Portrait stall (needs logs) · A4 "Next" discoverability · A6 Jung latency (needs measurement).

---

## ⚠️ UNVERIFIED — stated plainly, not softened

Four items. Nothing elsewhere in this document quietly assumes any of them.

- ⚠️ **`BETA_GRANT_PRO_TO_ALL` in production.** Code default is `False` (`config.py:50`). The live value is a **Render env var**, unreadable from this machine; `main.py:41-42` logs a warning at startup when it is on, but there is no Render log access here. **Not determined.** Whether billing defects are currently masked, and whether tier gates are live, both inherit this.
- ⚠️ **OPS-004 — the API's database role.** The RLS posture holds **only** if the API connects as the owner or a `BYPASSRLS` role. Circumstantial evidence: queries work. `DATABASE_URL` is not in the repo. **Not verified directly.**
- ⚠️ **TD-44 — prompt-cache reads.** `cache_read > 0` still never confirmed in production logs. No log access.
- ⚠️ **A1 — the Android keyboard fix has never run on a device.** Live since 2026-08-06.

**Promoted OUT of this set — the 49 / 13 split is now VERIFIED.** Method: `npx vitest run` executed at `cace1016` **twice**, with and without `globals: true` — **62 failed / 54 passed (16 of 24 files) → 13 failed / 103 passed (6 of 24 files)**. The 49 are measured, not inferred from the 2026-08-13 report, and the 13 stale tests are individually identified. See queue item 7.

---

## Verified state — the numbers, with methods

| | Value | Method |
|---|---|---|
| Migration head | **`053_token_version`** | Chain read (53 revisions, 52 down_revisions, exactly 1 head, 0 dupes, 0 branch points) **and** live `alembic_version` — agreeing |
| RLS | **35/35 tables enabled, 0 policies, 0 FORCE, owner `postgres`** | Live `pg_class`/`pg_policies` query |
| RLS durability | **Now in the chain** (052) | File read; closes OPS-005 |
| `users.token_version` | `integer NOT NULL DEFAULT 0` | Live `information_schema.columns` |
| Subscriptions with a Stripe id | **7** (4 pro/active, 1 pro/incomplete, 2 free/canceled) | Live aggregate query |
| Backend tests | **29 failed / 513 passed (542)** | `pytest` executed at `cace1016` |
| Frontend tests | **62 failed / 54 passed (116)**, 16 of 24 files | `vitest` executed at `cace1016` |
| Typecheck | **11 errors — 4 production, 7 test-file** | `tsc --noEmit` executed at `cace1016` |
| Personas | **11** | `PERSONA_REGISTRY` read |
| `anthropic` SDK | **0.99.0** | `requirements.txt:14` |
| Workflows | **1** (`web-build.yml`, `apps/web/**` only) | `ls .github/workflows/` |

---

## Changelog v24 → v25

Range **#522–#548** (27 PRs). Full table with SHAs and UAT mapping in `PROJECT_STATE_v25.md §"Changelog v24 → v25"`. #521 was the v24 doc PR.

Headline arcs: the **chat context window** (#522 → #532 → #533, ending in a growing budget-bounded window); the **letters arc** (#531, #534, #538, #541, #544, #545, #546, #547 — including two silent-loss incidents); **auth** (#535 refresh, #543 revocation + migration 053); **rate-limit truthfulness** (#536, #540); **council framing** (#530); **AI-disclosure** (#529); **safety events on ritual surfaces** (#548 + migration-free new service); **RLS codified** (#542).

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + C-01..C-05; **⚠️ the dual-tier bullet at :314-325 is FALSE and is item 1 of the next session**), architecture (§2 — **UNCARRIED**, not re-verified), test infra (§3 — **+ `tests/services/test_safety_event_log.py`, `tests/workers/test_letter_write_back.py`, `tests/routers/test_council_limits.py`; 29 backend red, 62 frontend red**), known limitations (§4 — **+ TD-50, TD-51, OPS-006, A18c and its sibling**), next-session entry point (§5 — the queue above), env config (§7 — **UNCARRIED**), key file paths (§8 — see `PROJECT_STATE_v25.md §Part A`), decision history (§9 — **+ C-05 RLS-on-create; + A18b's originating-surface rule**), migration plan (§11 — head **053**, verified two ways), deployment readiness (§12 — OPS-002/003/004/006 outstanding), session lessons (§13 — below), closing note (§14).

**Sections marked UNCARRIED were not re-verified this rotation and are therefore not restated.** Consult `HANDOFF_BRIEF_v24.md` for them and treat that content as unverified until checked.

---

### 13. Session lessons (v25)

- **13.60 — A check that cannot fail is not a check.** Three incidents this cycle, one shape. **(a)** A prompt slice bounded only at its start ran past `MONTHLY_PROMPT` into `MIRROR_PROMPT` — it had no end, so it could not have revealed the error. **(b)** A revert-verify where, after reverting the fix, **all the tests still passed** — read for a moment as reassurance when it is a finding: green there means the test does not exercise the fix. **(c)** Guards presented as proofs — a guard clause shows the case was thought about; only an execution that reaches it shows it fires. **Before trusting a check, name the observation that would make it fail. If you cannot, it is a ritual.**
- **13.61 — Prefer guarantees the diff can carry.** Applied four times: A17b's `label: str = "Letter"` kwarg (default *is* the old behaviour, so letter call sites stayed byte-identical); A18b's delegating `_log_safety_event` wrapper with an unchanged signature; and A18/A18-monthly's single shared definition of "ritual activity" behind both the cron count and the quiet-week gate. A reviewer can verify "these sites did not change" by reading the diff; verifying "I re-read them and they're fine" requires trusting a claim. **Prefer the change whose safety is visible over the change that is merely correct.**
- **13.62 — This shell collapses backslash-backslash inside quoted heredocs.** Build any backslash-bearing payload with `chr(92)` or via a file, then **AST/syntax-check it** — do not eyeball. A doubled backslash silently becomes single and often still parses. *(Also: a heredoc large enough to hold a full document exceeds this shell's spawn limit — use a file-writing tool.)*
- **13.63 — A masking patch is worse than the bug it hides.** Carried from the never-merged v25 and re-confirmed **twice** here. The original: the history-window `last_user_text` append made turn N+1 look right and turned amnesia into accusation. Re-confirmed by A17: **four** JSON parse sites shared one defect, **one** produced the symptom, and **two siblings stayed live** until A17b. Re-confirmed prospectively by A18c: two ring-true surfaces, one reported. **When you find the site, count the family before you fix the site.**
- **13.64 — "Unchanged." is not evidence.** This rotation is the proof: the document that first said so was itself never merged, and asserted a false fact about a PR that did not exist. Every claim here states a method or marks itself unverified.
- **13.65 — Verify the delivery, not just the write.** A17 (`j_failed=0` on a lost letter), A18 (zero-letter dispatch on the most active week on record) and A8 (a letter delivered to an account its owner didn't know she had) all share one shape: the system reported success or reported nothing while the user received nothing. **All three were found by querying data; none by a person using the app.**
- **13.66 — A doc that is not merged does not exist.** Twelve days of work, four files and a `CLAUDE.md` fix, invisible to every reader including the next session's brief-writer. Before a rotation is "done": push, open the PR, and confirm the files are on `main`.

---

**End of HANDOFF_BRIEF v25.** Authoritative as of 2026-08-18 at `cace1016`. Supersedes `HANDOFF_BRIEF_v24.md` (preserved byte-identical). Replaces the never-merged `docs/v25-rotation` draft, which was mined for re-verifiable claims and not merged. Where this conflicts with v24 or earlier, this wins.
