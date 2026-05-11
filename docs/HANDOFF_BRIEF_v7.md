# HANDOFF BRIEF v7 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + mentor instance
**Date updated:** 2026-05-10
**Prior version:** `docs/HANDOFF_BRIEF_v6.md` (2026-05-09) + `HANDOFF_BRIEF_v6_ADDENDUM_2026_05_10.md`

**Status:** Phase 3 ✅ closed. Phase 4 ✅ closed. Phase 4 stabilization sequence ✅ closed. Setup PR + Greenfield scaffold ✅ closed (2026-05-07). **Block A — Authentication ✅ FULLY CLOSED in production (5/5 line items, 2026-05-10).** Legal pages ✅ shipped as templates (2026-05-10). Vercel parallel deployment ✅ disconnected (2026-05-10). Phase 5 P3 post-feedback. Phase 6 P1 post-revenue. **43-screen UI build remains the P0 work surface; Block A done, Block B next (paused awaiting 4 strategic decisions). Plan A confirmed 2026-05-10. Web/PWA only for v1.**

> **Update note for v7:** This is a **full merge** of `HANDOFF_BRIEF_v6.md` + `HANDOFF_BRIEF_v6_ADDENDUM_2026_05_10.md`. All v6 content preserved; 2026-05-10 session delta merged inline at semantically correct sections (not append-only). New changelog sub-section captures 2026-05-10 session. §17.1.6 + §17.2 + §17.2.5 + §17.3 + §19 + §20 + §21 + §22 all extended with 2026-05-10 facts. New §24 documents Block B planning (4 strategic decisions pending). New §25 closing note for next instance on stakes context elevation.

> **Conflict resolution:** Where v7 conflicts with v6, **v7 wins**. v6 reality-check on Supabase as live DB still authoritative (DATABASE_URL on Render points to `aws-0-eu-west-1.pooler.supabase.com:5432/postgres`; queries returned production data including 2 users, 50 conversations, 139 messages, 1 disclaimer_acceptances row). Render `philosopher-db` decommissioning status remains unverified — verify in next session.

---

## Changelog v6 → v7 (2026-05-10 session)

### 2026-05-10 — Block A 5/5 closure + legal templates + Vercel disconnect

**6 production-merged PRs in ~7 hours sustained focus session, zero rollbacks.**

#### A. Vercel disconnect — RESOLVED

Founder deleted `thinkalike.vercel.app` Vercel project via dashboard. GitHub integration cleanup confirmed. Production canonical is exclusively `thinkalike.netlify.app`. Closes v6 §17.2 urgent prerequisite.

#### B. A4 Trouble accessing email — CLOSED (3 PRs)

- **PR #22** `feat(web): A4 trouble accessing email screen` — initial implementation, single Option card with mailto + Contact support CTA.
- **PR #23** `fix(web): A4 mailto + card reframe` — `<button>` → `<a href="mailto:>` (Chrome incognito redirected programmatic mailto to Google search). Card reframed to muted future-state placeholder.
- **Small fix PR** `fix(web): A4 text-center` — 1-line fix; orphaned commit re-applied on fresh `fix/a4-text-center` branch. Origin of new operating principle §16.A.13 ("centered" means BOTH layout-centered AND text-aligned-center).

New env var: `NEXT_PUBLIC_SUPPORT_EMAIL` = `nckoutras@gmail.com` (placeholder until real `support@thegreatminds.app` mailbox).

#### C. A6+A7 Disclaimer chain — CLOSED (3 PRs)

- **PR #24** `feat(api): A6+A7 disclaimer schema migration` (commit `acb910c`) — alembic migration 003: `disclaimer_versions` + `disclaimer_acceptances` tables, v1.0 seed with age_copy + positioning_copy. alembic_version advanced `002_otp_codes` → `003_disclaimer_acceptances`. DB went from 13 to 15 public tables. Both new tables created with RLS DISABLED matching existing convention.
- **PR #25** `feat(api): A6+A7 disclaimer backend endpoint` (commit `4941296` → `8667778`) — `apps/api/services/disclaimer_service.py` (99 lines, module-level async functions matching `otp_service.py` convention), `apps/api/routers/disclaimer.py` (65 lines, GET /disclaimer/current public + POST /disclaimer/accept auth-required), ORM models appended to `apps/api/models/__init__.py`, Pydantic schemas appended to `apps/api/schemas/__init__.py`, `UserOut` extended with `needs_disclaimer: bool = False`. Auth router extended on **all 4 paths** (`register`, `login`, `/me`, `/otp/verify`) to compute `needs_disclaimer` — prevents disclaimer bypass via legacy login endpoints.
- **PR #26** `feat(web): A6+A7 disclaimer frontend page + routing` (commit `614dc51` → `17c48a6`) — `apps/web/app/auth/disclaimer/page.tsx` (172 lines, `'use client'`), API client extensions in `apps/web/lib/api.ts` (3 new types, 2 new methods), conditional routing in `/auth/verify` (routes to `/auth/disclaimer` if `needs_disclaimer`, else `/app/dashboard`). `BronzeDivider` primitive finally consumed in production at `/auth/disclaimer`.

End-to-end verified with real acceptance row in `disclaimer_acceptances` for founder (`nckoutras@gmail.com`, 2026-05-10 19:53:29 UTC), full audit fields populated (user_id, version_id, confirmed_age_18=true, confirmed_non_therapy=true, locale='en', ip_address, user_agent, accepted_at).

#### D. Legal pages — TEMPLATES SHIPPED

- **PR #28** `feat(web): add Terms of Service + Privacy Policy pages` — `/legal/terms` (Server component, 123 lines, 16 sections) + `/legal/privacy` (Server component, 121 lines, 13 sections, GDPR-aware). Also fixes `'#'` fallback URLs in 2 auth pages (`/auth/page.tsx`, `/auth/verify/page.tsx`) → `'/legal/terms'` and `'/legal/privacy'`. `NEXT_PUBLIC_TERMS_URL` / `NEXT_PUBLIC_PRIVACY_URL` env vars remain UNSET in Netlify; setting them later overrides without code change.

**New P0 — Lawyer review of legal templates.** Greek consumer law specifics, Stripe billing T&Cs, AI-content liability scope all unchecked. Pre-public-launch blocker.

#### E. PR #27 — closed without merge

Earlier failed-push attempt at legal pages, abandoned after diagnostic. `refs/pull/27/head` persisted as ghost reference — origin of new operating principle §16.A.15 (trust-but-verify CC pushes via `git ls-remote`).

#### F. OTP rate limiter — VERIFIED WORKING

Founder hit 5-requests-in-6-minutes ceiling during testing, received 429 Too Many Requests as designed. Specific limit values (per-email, per-IP, per-day) documented in regenerated `PROJECT_STATE_v7.md`.

#### G. Plan A confirmed

Founder confirmed Plan A (build all 43 screens before launch) at start of 2026-05-10 session. Plan B remains documented in `IMPLEMENTATION_BACKLOG_v7.md` §17.5 for reversibility but not actively considered.

### Inherited pending from v6 (still open)

- Custom domain `thegreatminds.app` DNS + SSL (registered 2026-05-07, not configured)
- Render API plan upgrade decision (free tier still active; `WEB_CONCURRENCY=1`, 15-min idle cold-start)
- Stripe wiring (calendar-gated 2026-05-11 — now)
- `PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation in Render env vars
- Resend domain verification (blocks public launch — currently can only reliably send to founder's email)
- RLS audit on Supabase 15 tables (all disabled, mitigated by FastAPI gateway)

### New items introduced 2026-05-10

- **Block B 4 strategic decisions** pending founder input (see §24)
- **Lawyer review of legal templates** (new P0)
- **A6+A7 disclaimer endpoint integration tests** (P1; shipped without tests for speed)
- **A6+A7 lazy-load monitoring** (P1; watch for `MissingGreenlet` in Render logs)
- **A4 mailto visible support email fallback** (P1; when real mailbox exists)
- **A5 polish** (P3; per-digit OTP boxes, expiry countdown, resend cooldown)
- **Stale branch cleanup** (P4; periodic batch every 1-2 weeks)
- **gh CLI install on founder's Windows** (P4; `winget install --id GitHub.cli` to eliminate manual compare URL flow)
- **Legal pages `target="_blank"` rel hardening** (P4; explicit noopener noreferrer)
- **Render `philosopher-db` decommissioning verification** (P4; carry-forward from v6)
- **`apps/api/scripts/` untracked decision** (P4; gitignore/commit/delete)

---

---

## Changelog v5 → v6

### 2026-05-08 — Block A backend infrastructure (prior thread)

- **PR #18 (`feat(api): passwordless OTP endpoints`)** — `/auth/otp/request` (202) and `/auth/otp/verify` (200 with JWT). 6-digit code, hashed + salted in DB, 10-minute expiry, max 5 attempts, then locked.
- **Dockerfile fix in same PR** — added `alembic upgrade head` to container start CMD: `sh -c "alembic upgrade head && exec uvicorn ..."`. Solves migration-on-deploy plumbing for all future schema PRs.
- **Upstash Redis provisioned** — `philosopher-prod`, free tier, eu-west-1, endpoint `feasible-mammal-118733.upstash.io:6379`. Resolves earlier silent breakage of ARQ background tasks (`extract_memory_task`, `generate_insight_task`, `send_ritual_reminder_task`) that had been broken in production for unknown duration due to missing `REDIS_URL`.
- **Resend account created**, `RESEND_API_KEY` set in Render env vars.
- **FROM_EMAIL** env var set: `Great Minds <onboarding@resend.dev>` (Resend test sender — works without verified domain, suitable for dev/test sends to the account owner email; **must switch to verified domain before sending to any other recipient**).
- **Supabase confirmed as live DB** — DATABASE_URL hostname is `aws-0-eu-west-1.pooler.supabase.com`. Project `plecolxlzshkfvybszgs`.

### 2026-05-09 — Block A frontend completion + alembic plumbing fix (this thread)

- **`fix/alembic-versions-layout` PR** — moved `001_initial.py` and `002_otp_codes.py` into `apps/api/db/migrations/versions/` subdirectory. Root cause: alembic looks in `<script_location>/versions/` by default; flat layout meant zero migrations discovered. After fix + alembic_version stamp = `'002_otp_codes'` via Supabase MCP, alembic operates correctly for all future schema work.
- **Manual SQL** applied via Supabase MCP to create `otp_codes` table during go-live (since alembic was non-functional at that point). Schema matches `002_otp_codes.py` 1:1: id (UUID), email, code_hash, salt, expires_at, attempts, used_at, created_at + index on (email, created_at DESC).
- **PR #20 (`feat(web): A5 verify UI`)** — passwordless OTP code entry screen at `/auth/verify`:
  - Reads `email` from URL query, validates 6-digit numeric code
  - Calls new `api.verifyOtp()` method (added to `apps/web/lib/api.ts`)
  - Persists token via `api.setToken()` (localStorage `ph_token` + cookie `ph_token`, 7-day, SameSite=Lax)
  - Updates Zustand store via `useStore.getState().setAuth(user, token)`
  - Routes to `/app/dashboard` on success (404 currently — page does not exist; auth still completes)
  - Mirrors A2/A3 styling verbatim (Tailwind classes, fonts, color tokens, footer Terms/Privacy)
- **Two prerender hotfixes in same PR** — initial deploy failed Netlify build due to `useSearchParams()` requiring Suspense boundary. `dynamic = 'force-dynamic'` alone insufficient; final fix wraps inner `VerifyForm` in `<Suspense fallback={null}>`. Belt-and-suspenders kept.
- **End-to-end auth verified live** — 2026-05-09 ~12:25 AM:
  - POST `/auth/otp/request` → 202
  - Email arrives from Great Minds with 6-digit code
  - POST `/auth/otp/verify` → 200 with `{ access_token, token_type: "bearer", user }`
  - JWT cookie + localStorage set
  - Redirect to `/app/dashboard` → 404 (expected, page not built yet)
- **Vercel parallel deployment confusion confirmed live** — founder testing accidentally landed on `thinkalike.vercel.app` instead of `thinkalike.netlify.app` due to browser autocomplete. Both domains serve the same code (both auto-deploy from `main`). Vercel disconnect promoted to urgent priority.

### Inherited pending from v5

- Custom domain `thegreatminds.app` DNS + SSL (registered 2026-05-07, not configured)
- Render API plan upgrade decision (free tier still active; `WEB_CONCURRENCY=1`, 15-min idle cold-start)
- Stripe wiring (planned ~2026-05-11)
- `PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation in Render env vars
- Resend domain verification (blocks public launch — currently can only reliably send to founder's email)

### New flag introduced 2026-05-09

- **Founder stakes context** — financial motivation for project is family income support. This raises the bar for stakes-aware mentoring: harder pushback against rabbit holes, no false politeness, monetization-first remains paramount even within engineering decisions. See §23.

---

## 1–14 — UNCHANGED FROM v1/v2/v3

[Sections 1 through 14 are deliberately not reproduced. Placeholder/preserved-from-v1-v2-v3 content; prior versions no longer in active project knowledge. If needed, retrieve from git history.]

---

## 15. SECTION 5.7 FRAMEWORK — STATUS UNCHANGED FROM v5

§15.1 – §15.4 unchanged from v3.

### 15.5 Implementation status

| Element | Status |
|---|---|
| Character anchors (schema) | ✅ Optional field on PersonaConfig |
| Character anchors (data) | ✅ Populated for all 6 personas (PR #7-12) |
| Register architecture (schema) | ✅ RegisterRange + RegisterOverride dataclasses |
| Register architecture (data + classifier) | ⏳ Data populated. Runtime UI chip selection + classifier deferred to **P3 post-feedback** |
| Brevity discipline (schema) | ✅ ResponseLengthSpec 4-mode dataclass |
| Brevity discipline (runtime check) | ✅ check_brevity() + 3-layer sentence-boundary fix shipped (`2bf9244`) |
| Anti-flexing (schema) | ✅ AntiFlexingRules dataclass |
| Anti-flexing (data + enforcement) | ✅ Populated for all 6 personas, postchecked |
| Modern phenomenology bridge | ✅ Infrastructure shipped + map expanded 33→78 entries + 14-test verification confirms bridge active and modern terms not leaking. **Note:** `PHENOMENOLOGY_BRIDGE_ENABLED` flag state to confirm in Render env vars before launch. |
| Universal forbidden lexicon (runtime) | ✅ Live via check_universal_forbidden() |
| Persona-specific forbidden (schema) | ✅ ForbiddenLexicon dataclass |
| Persona-specific forbidden (data) | ✅ Populated for all 6 personas |
| Eval suite | ⏳ Reclassified to **P1 post-revenue**. Not a launch blocker. |

For full backlog status table see `IMPLEMENTATION_BACKLOG_v5.md` §8.1.

---

## 16. MIGRATION PLAN — STATUS UNCHANGED FROM v5

§16.1, §16.3, §16.4, §16.5 unchanged from v3.

### 16.2 Six-phase plan — implementation status

**Phase 1** ✅ COMPLETE + MERGED 2026-05-02 (commit `0ade549`).

**Phase 2** ✅ COMPLETE + MERGED 2026-05-02 (commit `6e2daad`).

**Phase 3** ✅ COMPLETE + MERGED 2026-05-03 to 2026-05-04 (PRs #7-12). All 6 production personas have populated 8 Section 5.7 structured fields.

**Phase 4 — Modern phenomenology bridge** ✅ COMPLETE + IN PRODUCTION

- Infrastructure shipped via Phase 4 PR Α (5 commits: `96761fb`, `ea41d2e`, `a0b54b7`, `5f14ddf`, `fe23a10`)
- Map expanded 33 → 78 entries (`ae58479`, `54a8be4`)
- Bridge verified via 14-test session 2026-05-04/05
- Sentence-boundary truncation 3-layer fix (`2bf9244`)
- **Outstanding:** `PHENOMENOLOGY_BRIDGE_ENABLED` flag state to confirm in Render env vars before launch
- **Phase 4 PR Β** (Marcus shading content, 33 strings) → P3 post-launch

**Phase 5 — Register architecture + UI chips + classifier** ⏳ P3 post-feedback (reclassified 2026-05-06).

**Phase 6 — Eval suite + CI** ⏳ P1 post-revenue (reclassified 2026-05-06).

---

## 17. NEXT WORK SURFACE — 43-SCREEN UI BUILD (UPDATED v6)

### 17.1 Phase 4 stabilization sequence — CLOSED 2026-05-05

8 items closed and remain closed (Bug #33, #34, items 1.3-1.7, 2.1). See v5 §17.1 for details. Do not reopen unless a launch test fails.

### 17.1.5 Setup PR + Greenfield scaffold — CLOSED 2026-05-07

- Setup PR — design tokens, Cormorant + Lora fonts, BronzeDivider/Spinner primitives (`ad24d15`)
- Greenfield scaffold — drop 19 legacy frontend files, placeholder home with spec tokens (`474f081`)

Frontend foundation now spec-compliant. Backend integration preserved (`apps/web/lib/`, `middleware.ts`).

### 17.1.6 Block A — Authentication — ✅ FULLY CLOSED 2026-05-10 (5/5 in production)

| Screen | PR | Status |
|---|---|---|
| A1 — Splash | #15 (`ad24d15`) | ✅ live (2026-05-08) |
| A2 / A3 — Sign-in (email entry) | #17 (`e2dcf9f`) | ✅ live (2026-05-09) |
| A4 — Trouble accessing email | #22, #23, + text-center fix | ✅ live (2026-05-10) |
| A5 — Verify (OTP code entry) | #20 (`b58d273` + `8283498` + final squash) | ✅ live (2026-05-09); P3 polish queued (per-digit boxes) |
| A6+A7 — Age + positioning disclaimer (combined) | #24 schema, #25 backend, #26 frontend | ✅ live (2026-05-10) |

**Backend support shipped:**
- PR #18 — `/auth/otp/request` (202) + `/auth/otp/verify` (200) endpoints
- PR #25 — `/disclaimer/current` (200) + `/disclaimer/accept` (200) endpoints, all 4 auth response paths extended with `needs_disclaimer` field
- Resend integration with FROM_EMAIL env var
- Upstash Redis with REDIS_URL env var (rate limiting via `rate_limit_service.py` — **VERIFIED WORKING 2026-05-10**: founder hit 5-req/6-min ceiling, received 429 as designed)
- Supabase `otp_codes` table with `(email, created_at DESC)` index
- Supabase `disclaimer_versions` + `disclaimer_acceptances` tables (NEW 2026-05-10, alembic migration 003)
- Alembic plumbing fixed (versions/ subdirectory + stamped alembic_version); current head `003_disclaimer_acceptances`
- JWT issuance, cookie + localStorage persistence, Zustand store sync
- Disclaimer re-acceptance flow: idempotent INSERT via UNIQUE constraint catch; version-check + skip for already-accepted users routes directly to `/app/dashboard`

**Block A audit complete.** End-to-end verified live 2026-05-10 with real `disclaimer_acceptances` row for founder. All A-block mentor flags from v6 resolved.

### 17.2 Block-by-block remaining work — 43-screen UI build

Per founder decision 2026-05-06, confirmed 2026-05-10. Order follows `SCREENS_TRACKING_v4.md`:

| Block | Scope | Items | Status |
|---|---|---|---|
| **A** | Authentication | A1, A2/A3, A4, A5, A6+A7 | **✅ 5/5 line-items LIVE** (2026-05-10) |
| **B** | Onboarding | B1–B6 | ⏸ **Planning paused — 4 strategic decisions pending** (see §24). B6 deferred until Stripe. |
| **C** | Chat experience | C1–C9 | ⚠️ Some partially live from earlier engine work; verify against spec |
| **D** | Discovery | D1, D2, D3 | ❌ Not started |
| **F** | Reflection | F1, F2, F3, F4, F6 | ❌ Not started |
| **H** | Subscription & Billing | H1, H2, H3, H4, H4b, H5, H6 | ❌ Not started — Stripe wiring after this block |
| **I** | Account & Settings | I1, I2, I3, I4, I5, I6 | ❌ Not started |
| **J** | Empty/error states | J1, J2, J3, J5 | ❌ Not started |

**Total: 43 effective specced screens** (45 line items because A2/A3 and A6/A7 are merged screens). **8 of 45 closed**; 37 remaining. Authoritative ordering and parallel-work plan in `IMPLEMENTATION_BACKLOG_v7.md` §17.

### 17.2.5 Plan A/B Fork — Plan A CONFIRMED 2026-05-10

Founder confirmed Plan A (build all 43 screens before launch) at start of 2026-05-10 session. Plan B remains documented for reversibility but is not actively considered.

**Plan A — Continue 43-screen sequence (founder's 2026-05-06 decision, confirmed 2026-05-10)**

Next item: Block B — Onboarding (B1–B5; B6 deferred). Pending 4 strategic decisions documented in §24. ~9-13 weeks to first paying user (revised down from 10-14 since Block A fully closed and legal templates live).

**Plan B — Minimum-to-revenue interrupt (mentor recommended, NOT active)**

Documented in `IMPLEMENTATION_BACKLOG_v7.md` §17.5 in full. Available as pivot option if circumstances change (timeline pressure, runway concerns, signal from early testers).

**Mentor rationale (preserved):**

- Family income context (§23) raises cost of long timelines
- 43 screens before any paying user = many weeks of zero validation
- Building 30+ retention screens before knowing if anyone pays is anti-pattern
- Trade-off alternatives preserved per §19.6 — pivoting to Plan B at any point does not invalidate prior decisions

**Founder's call stands. Mentor flagged for reconsideration at next stakes-relevant moment** (UAT signal, runway change, Stripe wiring delay, etc.).

### 17.3 Calendar-gated parallel work (UPDATED v7)

- **Stripe wiring** — available from 2026-05-11 (now). Can start parallel with Block H once those screens exist in placeholder form.
- ~~**Vercel disconnect**~~ ✅ **RESOLVED 2026-05-10**
- ~~**Legal copy** (Terms, Privacy Policy, disclaimer)~~ ✅ **TEMPLATES SHIPPED 2026-05-10** (PR #28 + PR #24 disclaimer seed). **Lawyer review still required** before public launch (NEW P0).
- **Email infrastructure verification** — Resend domain verification (`thegreatminds.app`) blocks public launch since current setup only sends reliably to founder email.
- **DNS configuration** for `thegreatminds.app` — required before Resend domain verification + before brand-consistent launch.
- **Founder runbooks** (refund, account recovery, GDPR fulfillment, cancellation override, safety escalation) — parallelizable.

### 17.4 Pre-launch verification (after UI complete)

- Production smoke test (8 closed Phase 4 items + all 43 screens)
- Confirm `PHENOMENOLOGY_BRIDGE_ENABLED` flag state in Render env vars
- UAT with 3-5 mixed testers (close + acquaintances + strangers)
- Decision gate: ≥2/5 spontaneous "I'd pay" → public launch (web/PWA)
- If <2/5 → iterate before launch
- **Block A specific (already complete but for the audit trail):** verify auth flow on `thegreatminds.app` once DNS is live, with FROM_EMAIL switched to verified domain sender

### 17.5 "Bring another mind" — preserved from v3/v4

Still deferred until after Phase 5 (register architecture). Phase 5 is now P3 post-feedback, so "Bring another mind" follows it.

---

## 18. CLAUDE.AI PROJECT KNOWLEDGE — STATUS (UPDATED v6)

**Files currently in Claude.ai Project Knowledge (verified 2026-05-09):**

Top-level state and continuity docs:
- `PHILOSOPHER.docx` — product spec (unchanged)
- **`HANDOFF_BRIEF_v6.md` — this document (continuity for next session, replaces v5)**
- `PROJECT_STATE_v5.md` — live state snapshot — **needs v6 update for Block A completion + DB clarification**
- `IMPLEMENTATION_BACKLOG_v5.md` — work item priority source of truth — **needs v6 update reflecting Block A done + Plan A/B fork**

UX design docs (active per 2026-05-06 decision):
- `DESIGN_SYSTEM_v4.md`
- `SCREENS_TRACKING_v4.md` — **A4 status to verify; A5 to mark live; A6/A7 boundary with Block B to clarify**
- `USER_FLOW_v4.md`

Brain content (Section 5.7 design source — also in repo at `apps/api/philosopher_brain/`):
- `marcus_aurelius_yaml.txt` (uploaded as .txt, content is YAML)
- `socrates.yaml`, `de_beauvoir.yaml`, `epictetus.yaml`, `freud.yaml`, `jung.yaml`, `nietzsche.yaml`
- `modern_phenomenology.json` — 78 entries, last_reviewed 2026-05-05
- `persona_specific_forbidden.json` — design template
- `universal_forbidden_lexicon.json`
- `master_system_prompt.md` — design source (runtime template at `apps/api/prompts/system_base.jinja2`)
- `eval_suite_spec.md` — design source for Phase 6 (deferred to P1 post-revenue)
- `ten_modern_problems.json` — eval test cases

**Removed during v6 cycle (do not re-upload):**
- `HANDOFF_BRIEF_v5.md` — superseded by this document
- All earlier v1-v4 briefs and backlog variants — superseded

**Repo-side handoff doc:**
- `HANDOFF_BRIEF_FOR_CLAUDE_CODE.md` (referenced in earlier session) — purpose-built for Claude Code task context. Should be kept in sync with this v6 brief. If changes are needed for Claude Code to operate effectively, update both.

---

## 19. SESSION LESSONS

### 19.1 Full diffs, not grep summaries (preserved from v4)

The 1.7 hotfix (`0256f97`) was required because grep for `build_system` missed a caller at `conversation_service.py:159`. 10-minute production crash resulted. Rule: for parameter/schema changes, paste full diff of every modified file before commit, grep for every caller, paste diff of every caller — even those marked "no change needed."

### 19.2 Defense in depth over single-point fixes (preserved from v4)

The 1.5 empty-conversation fix used both backend dedup and frontend in-flight flag. Layer independent defenses at each boundary.

### 19.3 Conftest.py must own credential stubs (preserved from v4)

`conftest.py` sets `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` as dummy values before any test module imports run.

### 19.4 message_count == 0 is the correct empty signal (preserved from v4)

Opening invocations are written to `messages` table but do NOT increment `message_count`. Only user-message + assistant-reply pairs increment by +2. Therefore `message_count == 0` is the exact condition for "user has never sent a message in this conversation."

### 19.5 Cross-check HANDOFF status table against PROJECT_STATE before publishing (v5)

Rule: when patching HANDOFF, run a 5-minute cross-check of every status row against PROJECT_STATE before committing. PROJECT_STATE is the runtime/deploy authority; HANDOFF must follow it, not lead it.

### 19.6 Decision reversibility documentation (v5)

When the founder reverses a prior strategic call, preserve the rationale and the alternative paths, not just the new direction. Plan B alternatives stay live in §17.4 of the backlog so circumstances change → pivot without re-litigation.

### 19.7 Build-time vs request-time Next.js rendering semantics (NEW v6)

PR #20 deploy preview failed twice before passing. First attempt: page used `useSearchParams()` directly — Next.js prerender failed. Added `export const dynamic = 'force-dynamic'`. Second attempt: still failed because Next.js's build-time check is independent from runtime dynamic-rendering opt-in. Final fix: wrap component using `useSearchParams()` in `<Suspense>` boundary. **Rule:** when Next.js complains about hooks needing Suspense, do not assume `dynamic = 'force-dynamic'` will suppress the build-time error. Either move forward with Suspense (idiomatic) or refactor the param-reading into a deferred chunk. Trust the error message; do not fight it.

### 19.8 Stamp + code-change order for alembic plumbing (NEW v6)

When fixing alembic discovery (e.g., moving migration files into `versions/` subdirectory), the order matters:

1. Code change (move files) committed and ready to deploy
2. Stamp `alembic_version` to current head via direct DB tool *before* merge
3. Merge, deploy

**Wrong order:** stamp first while old code is live → next container restart (auto-redeploy from env var change, etc.) tries to upgrade from stamped-head to head, fails with `Can't locate revision`, deploy crashes. We hit this exact failure 2026-05-09 ~midnight; recovered by `DELETE FROM alembic_version` + manual redeploy.

**Rule:** for any alembic plumbing change that includes both code and DB-state alignment, document the dependency order explicitly in the PR description and execute it in dependency order, not in parallel.

### 19.9 Always disconnect parallel deployments before they cause confusion (NEW v6)

The Vercel project had been "still attached, disconnect when ready" since at least v4 / project init. On 2026-05-09 testing the live auth flow, founder accidentally landed on `thinkalike.vercel.app` instead of `thinkalike.netlify.app` due to browser autocomplete picking the more recently visited domain. Both deployments serve identical code, so the test passed — but only by luck. Had Vercel had stale env vars or been on an older deploy, the test would have produced misleading results.

**Rule:** when two deployments of the same app exist for any reason (migration, accidentally-attached CI, leftover staging), disconnect the non-canonical one immediately. Cost is ~5 minutes; cost of leaving it is cumulative cognitive friction every PR plus risk of debugging the wrong environment.

### 19.10 Stakes-aware mentoring requires explicit founder context (NEW v6)

On 2026-05-09 founder revealed that Great Minds is a financial necessity for family support, not a side project. This information arrived after multiple sessions of generic monetization-first mentoring. With the new context, mentor recommendations rebalance: harder pushback against rabbit holes, more aggressive against feature creep, more willingness to interrupt sequence-following with revenue-blocking concerns.

**Rule:** mentor relationship benefits from explicit stakes signal. If a founder shares their financial/personal stakes context, document it in HANDOFF so subsequent sessions inherit the right calibration.

### 19.11 Trust-but-verify CC pushes via `git ls-remote` (NEW v7 — 2026-05-10)

**Pattern §C.1.** On 2026-05-10, Claude Code reported successful push of legal-pages branch ("Branch live on remote") but GitHub UI showed no branch. Investigation revealed CC had hit an intermediate error; the success message was a misread of partial output. PR #27 ended up as a ghost (`refs/pull/27/head` persisted in repo refs but never had a real branch). Eventually abandoned; redone as PR #28.

**Rule:** for high-stakes branches (production blockers, schema migrations, anything where re-push has cost), insert a verification step before opening the compare URL:
```
git ls-remote origin <branch-name>
```
~5 seconds. Returns the SHA if the branch exists on remote, returns nothing if not. Catches the misread before it propagates into open PR confusion. Apply selectively — for trivial work-branch pushes, don't bother. For anything where you're about to ask the founder to "open this PR", verify first.

### 19.12 Complete PR cycles before queuing new work (NEW v7 — 2026-05-10)

When energy is high mid-session and there's a temptation to start the next PR before the current one is open / tested / merged, mentor pushes back. Compound-risk avoidance: 2 PRs in flight without verification means 3× harder debugging if something breaks — we don't know which PR introduced the issue.

Discipline cost: ~5-10 minutes to close a PR cycle (verify on production, document, close branch). Debug cost when this fails: hours of bisecting + reverting + recommit.

**Held twice in 2026-05-10 session** — post-A6+A7 frontend (founder wanted to start legal pages immediately; mentor blocked until disclaimer flow was verified end-to-end), and post-legal-pages-push (mentor blocked further changes until PR #27 ghost was diagnosed). Prevented messy state both times.

**Rule:** open → verify on production → merge → close → THEN queue next. Mentor enforces.

### 19.13 Spec word "centered" means BOTH layout-centered AND text-aligned-center (NEW v7 — 2026-05-10)

Origin: A4 trouble screen iteration 2026-05-10. Initial implementation centered the option card block via `mx-auto` but left text inside left-aligned. Founder reviewed and noted the screen "still felt off" — the block was centered horizontally on the page, but the text within sat at the left edge of the card. One-line fix added `text-center`.

**Rule:** when a screen spec says "centered" without qualification, default interpretation is `text-center` class on inner content container PLUS `mx-auto` for block-level centering. Both are usually expected. If the founder wanted only one, they would specify "block-centered" or "left-aligned text in a centered container". Apply across all future Block B–J screens.

---

## 20. DEPLOYMENT READINESS — STATUS (UPDATED v7)

### Live infrastructure

```
✅ Backend                Render web service philosopher-api
                          srv-d7ijct6gvqtc739a0pdg
                          philosopher-api-z9l9.onrender.com

✅ Database               Supabase project plecolxlzshkfvybszgs (eu-west-1)
                          DATABASE_URL points to aws-0-eu-west-1.pooler.supabase.com:5432
                          alembic_version = '003_disclaimer_acceptances' (advanced 2026-05-10)
                          15 public tables (+ disclaimer_versions, + disclaimer_acceptances)
                          RLS DISABLED on all (flag #22, pre-launch blocker)
                          ⚠️ v5 §20 stated Render PostgreSQL philosopher-db was live and
                             Supabase was dormant. Reality 2026-05-08: Supabase is live.
                             Either an undocumented migration occurred, or v5 was wrong.
                             Render philosopher-db status: VERIFY whether dormant, deleted,
                             or if there are stale references in PROJECT_STATE.

✅ Cache (Redis)          Upstash philosopher-prod (eu-west-1) free tier
                          feasible-mammal-118733.upstash.io:6379
                          REDIS_URL set in Render env, ARQ + APScheduler operational
                          Rate limiter VERIFIED WORKING 2026-05-10 (5 req / 6 min ceiling → 429)
                          (Resolved: silent breakage of background tasks)

✅ Email                  Resend free tier
                          RESEND_API_KEY set in Render env
                          FROM_EMAIL = "Great Minds <onboarding@resend.dev>"
                          ⚠️ Test sender only — sends reliably to founder's email
                             Verified domain required before any other recipient
                             (blocks public launch — flag #19)

✅ Frontend (canonical)   Netlify thinkalike.netlify.app
                          Auto-deploys from main branch
                          NEXT_PUBLIC_API_URL not explicitly set;
                          api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1
                          NEXT_PUBLIC_SUPPORT_EMAIL = nckoutras@gmail.com (placeholder)
                          NEXT_PUBLIC_TERMS_URL / NEXT_PUBLIC_PRIVACY_URL unset;
                          hardcoded fallbacks to /legal/terms and /legal/privacy (PR #28)

✅ Disclaimer flow        Live in production 2026-05-10
                          GET /api/v1/disclaimer/current → 200 (public)
                          POST /api/v1/disclaimer/accept → 200 (auth-required)
                          v1.0 seeded with age + positioning copy
                          Idempotent INSERT via UNIQUE(user_id, version_id) constraint
                          Version-skip routes already-accepted users to /app/dashboard
                          1 real acceptance row for founder (2026-05-10 19:53:29 UTC)

✅ Legal pages            /legal/terms (16 sections), /legal/privacy (13 sections, GDPR-aware)
                          Templates shipped via PR #28 — lawyer review REQUIRED before launch

❌ Frontend (legacy)      ~~Vercel thinkalike.vercel.app~~
                          DISCONNECTED 2026-05-10 — project deleted via Vercel dashboard

⏳ Custom domain          thegreatminds.app registered 2026-05-07
                          DNS + SSL not configured
                          Required for: brand consistency + Resend domain verification

⏳ API plan upgrade       Free-tier limits still active
                          WEB_CONCURRENCY=1, 15-min idle cold-start, 30-60s wake-up
                          Mentor recommendation: upgrade now (~$7/mo) before any UAT

⏳ Stripe wiring          Calendar-gated start 2026-05-11 (now)
                          Not yet integrated; no products/prices/webhooks configured

⏳ PHENOMENOLOGY_BRIDGE_ENABLED flag state to confirm in Render env
                          Was true during 14-test session 2026-05-04/05;
                          unknown current state
```

### Auth pipeline status — VERIFIED LIVE 2026-05-10 (extended)

End-to-end pipeline functional in production, with disclaimer gate:

```
1.  /auth                                                                ✓
2.  POST /api/v1/auth/otp/request                  →  202 Accepted        ✓
2a. Rate limiter ceiling (5 req / 6 min)           →  429 (verified)      ✓
3.  Email delivered from Great Minds                                      ✓
4.  /auth/verify?email=<encoded>                                          ✓
5.  POST /api/v1/auth/otp/verify                   →  200 OK              ✓
6.  Response: { access_token, token_type, user.needs_disclaimer }         ✓
7.  Token persisted: localStorage(ph_token) + cookie(ph_token, 7-day)     ✓
8.  Zustand store updated: philosopher-store with user object             ✓
9.  IF needs_disclaimer:  /auth/disclaimer                  →  200        ✓ (NEW 2026-05-10)
10. POST /api/v1/disclaimer/accept                 →  200 OK              ✓ (NEW 2026-05-10)
11. acceptance row written with audit fields                              ✓ (NEW 2026-05-10)
12. Redirect to /app/dashboard                     →  404 (page missing)  ❌ EXPECTED
12'. Returning users (already accepted): skip disclaimer, go straight to step 12  ✓
```

**Status: Block A complete (5/5). Auth pipeline + disclaimer flow functional. The 404 at step 12 remains the next gap; resolves with Block B sequence or Plan B `/app/dashboard` placeholder.**

---

## 21. DECISION HISTORY (EXTENDED v7)

### 2026-05-04 evening — Engine-first execution decided

- Mentor proposed distribution-first
- Founder pushed back: engine quality is the differentiator
- Sequence accepted: Phase 4 → 5 → 6 → critical UX subset → Stripe → UAT → public launch
- Compromise: NOT all 43 v4 UX screens — only Block 6 billing critical screens + pricing page
- 3-day soft cap per phase
- Estimated timeline: ~6-7 weeks to first paying user

### 2026-05-05 — Phase 4 stabilization sequence closed

- 8 ship items closed (see §17.1)
- Engine-first sequence declared complete in v4

### 2026-05-06 — UI scope reversal: build all 43

- Founder reversed the 2026-05-04 critical-subset compromise
- All 43 specced screens will ship before public launch (block order A→B→C→D→F→H→I→J)
- Phase 5 → P3 post-feedback. Phase 6 → P1 post-revenue. Native app → v2.
- v1 is web/PWA only
- Estimated timeline revised: ~12-16 weeks to first paying user
- Mentor pushed back on time cost; founder confirmed
- Trade-off alternatives (Plan B critical subset + revenue first; Plan C parallel UAT during build) preserved in `IMPLEMENTATION_BACKLOG_v5` §17.4 for future reconsideration

### 2026-05-06 — Infrastructure: DB upgraded to paid tier

- Render PostgreSQL `philosopher-db` upgraded from free to paid tier
- API web service upgrade decision still pending

### 2026-05-07 — Greenfield UI rebuild + Netlify hosting confirmed

- Founder reversed 2026-05-06 in-place refactor approach in favor of greenfield rewrite
- Two PRs landed: #13 Setup tokens (`ad24d15`), #14 Greenfield scaffold (`474f081`, deleted 19 files / 2183 lines)
- Frontend hosting clarified as Netlify (`thinkalike.netlify.app`), not Vercel
- Custom domain `thegreatminds.app` registered; DNS + SSL deferred
- Fallback documented: `git revert` to `85555d3` (pre-Setup main) if greenfield breaks

### 2026-05-08 — Block A backend infrastructure shipped (NEW v6)

- PR #18 merged: passwordless OTP endpoints + Dockerfile alembic plumbing
- Upstash Redis provisioned (`philosopher-prod`)
- Resend account + API key + FROM_EMAIL configured
- Discovered: existing ARQ background tasks had been silently broken in production for unknown duration due to missing REDIS_URL — fixed by adding env var
- Discovered: Supabase confirmed as live DB (DATABASE_URL hostname analysis), conflicting with v5 §20 statement — flagged for verification
- Mentor wavered on Dockerfile vs Web Shell migration approach; final answer Dockerfile (νοικοκυρεμένη path)

### 2026-05-09 — Block A frontend completion + alembic plumbing fix (NEW v6)

- `fix/alembic-versions-layout` PR merged: moved migration files into `versions/` subdir, fixed alembic discovery
- Manual SQL applied via Supabase MCP to create `otp_codes` table (since alembic plumbing was broken at go-live)
- Stamped alembic_version = '002_otp_codes' to align DB state with code state
- PR #20 merged: A5 verify UI + 2 prerender hotfixes
- End-to-end auth pipeline verified live in production
- Mentor flagged Vercel parallel deployment as urgent priority after observed autocomplete confusion during testing

### 2026-05-09 — Founder stakes context revealed (NEW v6)

- Founder clarified that Great Minds is being built to support family financially, not as a side project
- Mentor calibration adjusted: stakes-aware mentoring (§19.10), harder pushback against rabbit holes, monetization-first elevated within engineering decisions
- Plan B (minimum-to-revenue interrupt) added as explicit alternative to 2026-05-06 Plan A (43-screen sequence) — see §17.2.5
- No formal decision yet on which plan to take next; founder discretion at start of next session

### 2026-05-10 — Plan A confirmed by founder (NEW v7)

- Founder confirmed Plan A (continue 43-screen sequence) at start of 2026-05-10 session
- Plan B (minimum-to-revenue interrupt) remains documented in `IMPLEMENTATION_BACKLOG_v7.md` §17.5 for reversibility but not actively considered
- Mentor accepted decision; flagged for reconsideration at next stakes-relevant moment (UAT signal, runway change, Stripe wiring delay, etc.)

### 2026-05-10 — Block A 5/5 closed (NEW v7)

- 3 PRs merged on A4 trouble screen: PR #22 (initial), PR #23 (mailto + card reframe), small text-center fix
- 3 PRs merged on A6+A7 disclaimer chain: PR #24 (schema migration 003), PR #25 (backend service + router + auth extension), PR #26 (frontend page + routing)
- A4 origin of new operating principle §19.13 ("centered" means BOTH layout-centered AND text-aligned-center)
- A6+A7 shipped without integration tests (founder speed-vs-coverage trade-off); P1 backlog item created
- End-to-end verified with real `disclaimer_acceptances` row for founder (`nckoutras@gmail.com`, 2026-05-10 19:53:29 UTC)

### 2026-05-10 — Vercel parallel deployment disconnected (NEW v7)

- Founder deleted `thinkalike.vercel.app` Vercel project via dashboard
- GitHub integration cleanup confirmed
- Production canonical is exclusively `thinkalike.netlify.app`
- Closes v6 §17.2 urgent prerequisite + flag #1

### 2026-05-10 — Legal pages templates shipped (NEW v7)

- PR #28: `/legal/terms` v1.0 (16 sections), `/legal/privacy` v1.0 (13 sections, GDPR-aware) — both as templates pending lawyer review
- Disclaimer v1.0 copy seeded via PR #24 (age_copy + positioning_copy in `disclaimer_versions` table)
- `'#'` fallback URLs in 2 auth pages replaced with `/legal/terms` and `/legal/privacy`
- New P0: lawyer review of legal templates before public launch (Greek consumer law, Stripe billing T&Cs, AI-content liability scope)

### 2026-05-10 — OTP rate limiter verified working (NEW v7)

- Founder hit 5-requests-in-6-minutes ceiling during testing, received 429 Too Many Requests as designed
- Specific limit values documented in regenerated `PROJECT_STATE_v7.md`
- Confirms `rate_limit_service.py` operational against Upstash Redis production

### 2026-05-10 — Block B 4 strategic decisions queued (NEW v7)

- Block A 5/5 closure surfaced Block B as next, but Block B planning paused awaiting 4 founder decisions
- Mentor recommendations documented in §24 + `IMPLEMENTATION_BACKLOG_v7.md` §17.7
- Decisions: (1) B2/B3 answer persistence backend vs frontend-only; (2) matching algorithm backend vs frontend; (3) B6 Pro-locked variant timing; (4) `user_preferences` schema shape wide vs narrow
- Founder to confirm at start of next session before work resumes

---

## 22. BLOCK A COMPLETION REPORT (NEW v6)

This section consolidates everything Block A produced so the next session can audit / extend / debug without re-deriving context.

### 22.1 PRs merged

```
PR #18    feat(api): passwordless OTP endpoints
          + Dockerfile alembic on container start
          Merged 2026-05-08

(no #)    fix(api): move alembic migrations into versions/ subdirectory
          (single PR, branch fix/alembic-versions-layout)
          Merged 2026-05-09 ~late evening

PR #20    feat(web): A5 verify UI — passwordless OTP code entry
          + fix(web): opt /auth/verify out of static prerendering
          + fix(web): wrap useSearchParams in Suspense boundary
          Merged 2026-05-09 ~12:15 AM
```

### 22.2 Backend — files touched

```
apps/api/Dockerfile
  CMD changed to: sh -c "alembic upgrade head && exec uvicorn ..."

apps/api/db/migrations/
  ├── env.py                                 (unchanged)
  ├── versions/                              (new directory)
  │   ├── 001_initial.py                     (moved from migrations/)
  │   └── 002_otp_codes.py                   (moved from migrations/, NEW migration)
  └── (no flat .py files anymore)

apps/api/services/
  ├── email_service.py                       (existing — uses FROM_EMAIL config)
  ├── otp_service.py                         (existing — implements OTP request/verify logic)
  └── rate_limit_service.py                  (existing — Redis-backed; NO try/except,
                                              raises on Redis failure)

apps/api/config.py
  FROM_EMAIL: str = "noreply@philosopher.app"     (default — overridden by env var,
                                                   stale brand string — flag #20)

apps/api/routes/auth.py (or equivalent)
  POST /auth/otp/request    → 202 Accepted
  POST /auth/otp/verify     → 200 OK with AuthResponse
  Error codes: 401 wrong, 410 expired, 423 locked, 422 malformed
```

### 22.3 Frontend — files touched

```
apps/web/lib/api.ts
  Added api.verifyOtp(email, code) method, mirrors api.login() / api.register():
    - POST /auth/otp/verify
    - Body: { email, code }
    - On success: this.setToken(data.access_token)
    - Returns: AuthResponse

apps/web/app/auth/verify/page.tsx
  Replaced 5-line placeholder with full A5 implementation:
    - 'use client' directive
    - export const dynamic = 'force-dynamic'  (defense in depth, may be removable
      now that Suspense is in place — leave for safety)
    - VerifyForm() inner component:
      * useRouter, useSearchParams, useStore from existing app patterns
      * 6-digit numeric input (single field, inputMode="numeric",
        autoComplete="one-time-code")
      * Submit handler: api.verifyOtp() → setAuth → router.push('/app/dashboard')
      * Error branching: 410 expired / 423 locked / 401 invalid / generic
      * setIsLoading(false) only in catch (success navigates away)
      * Layout, fonts, colors, footer Terms/Privacy mirror /auth/page.tsx
    - VerifyPage() outer default export:
      * <Suspense fallback={null}><VerifyForm /></Suspense>
```

### 22.4 Database changes (Supabase)

Two state changes applied during go-live:

```sql
-- 1. Created otp_codes table (since alembic was non-functional)
CREATE TABLE otp_codes (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL,
    code_hash   VARCHAR(128) NOT NULL,
    salt        VARCHAR(32)  NOT NULL,
    expires_at  TIMESTAMPTZ  NOT NULL,
    attempts    INTEGER      NOT NULL DEFAULT 0,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_otp_codes_email_created ON otp_codes (email, created_at DESC);

-- 2. Stamped alembic_version to chain head
DELETE FROM alembic_version;  -- defensive cleanup
INSERT INTO alembic_version (version_num) VALUES ('002_otp_codes');
```

### 22.5 Environment variables (Render backend)

Set or verified during Block A:

```
DATABASE_URL              (existing, points to Supabase)
RESEND_API_KEY            (set 2026-05-08, Resend production token)
FROM_EMAIL                "Great Minds <onboarding@resend.dev>"  (set 2026-05-08)
REDIS_URL                 rediss://default:<token>@feasible-mammal-118733.upstash.io:6379
                          (set 2026-05-08, after one false-start with malformed value)
JWT_SECRET                (existing, used by token issuance)
```

### 22.6 Outstanding cleanup items from Block A — UPDATED v7

- ~~**A4 status:** verify against `SCREENS_TRACKING_v4`~~ ✅ **RESOLVED 2026-05-10** — A4 built and shipped (PRs #22, #23, + text-center fix). See §22.7.
- ~~**A6/A7 ownership:** clarify if they belong to Block A or Block B~~ ✅ **RESOLVED 2026-05-10** — A6/A7 confirmed as Block A (combined disclaimer screen, shipped together via PRs #24, #25, #26). See §22.8.
- **`FROM_EMAIL` default in config.py:** still hardcoded as `noreply@philosopher.app` — cleanup to `noreply@thegreatminds.app` once domain is verified (flag #20)
- **`/app/dashboard` page:** currently 404, blocks the post-auth UX from feeling complete. Resolves with Block B sequence (Plan A) or `/app/dashboard` placeholder (Plan B).
- ~~**Vercel disconnect:** urgent~~ ✅ **RESOLVED 2026-05-10** (flag #1 closed)

### 22.7 A4 Trouble Accessing Email — Completion Report (NEW v7)

**PRs merged 2026-05-10:** #22 (initial), #23 (mailto + card reframe), + small `fix/a4-text-center` PR.

**File touched:** `apps/web/app/auth/trouble/page.tsx` (~95 lines, `'use client'`)

**Design:**
- Single Option card with muted future-state placeholder content
- Contact Support CTA via `<a href="mailto:${NEXT_PUBLIC_SUPPORT_EMAIL}">` (NOT `<button>` — Chrome incognito redirected programmatic mailto to Google search; fixed in PR #23)
- `text-center` on inner container PLUS `mx-auto` on outer block (one-line fix added separately; origin of operating principle §19.13)
- Layout, fonts, colors mirror existing auth screens

**Env var added:** `NEXT_PUBLIC_SUPPORT_EMAIL` = `nckoutras@gmail.com` (placeholder until real `support@thegreatminds.app` mailbox)

**P1 backlog item:** swap placeholder to verified support mailbox when DNS + email infra are in place.

### 22.8 A6+A7 Combined Disclaimer — Completion Report (NEW v7)

**3 PRs merged 2026-05-10:** #24 (schema), #25 (backend), #26 (frontend) — chained intentionally with verification between each.

#### 22.8.1 Schema (PR #24, commit `acb910c`)

Alembic migration `003_disclaimer_acceptances` (55 lines):

```sql
CREATE TABLE disclaimer_versions (
    id                INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    version_string    VARCHAR(20) UNIQUE NOT NULL,
    age_copy          TEXT NOT NULL,
    positioning_copy  TEXT NOT NULL,
    effective_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE disclaimer_acceptances (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version_id              INTEGER NOT NULL REFERENCES disclaimer_versions(id),
    accepted_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    locale                  VARCHAR(10) NOT NULL DEFAULT 'en',
    confirmed_age_18        BOOLEAN NOT NULL,
    confirmed_non_therapy   BOOLEAN NOT NULL,
    ip_address              INET,
    user_agent              TEXT,
    UNIQUE (user_id, version_id)
);
CREATE INDEX ix_disclaimer_acceptances_user ON disclaimer_acceptances (user_id);
```

Seeded with v1.0:
- `age_copy`: "I am 18 years or older."
- `positioning_copy`: "I understand Great Minds is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional."

Both tables created with RLS DISABLED matching existing convention. alembic_version advanced `002_otp_codes` → `003_disclaimer_acceptances`.

#### 22.8.2 Backend (PR #25, commit `4941296` → `8667778`)

**Files added:**
- `apps/api/services/disclaimer_service.py` (99 lines, module-level async functions matching `otp_service.py` convention)
  - `get_current_version(db)` — SELECT ORDER BY effective_at DESC LIMIT 1
  - `user_needs_acceptance(user_id, db)` — bool; catches `NoVersionAvailable` internally and returns False (don't block login on misconfigured DB)
  - `accept(user_id, flags, locale, ip, ua, db)` — INSERT with idempotent IntegrityError catch on UNIQUE(user_id, version_id) → query existing row and return as success
- `apps/api/routers/disclaimer.py` (65 lines)
  - `GET /api/v1/disclaimer/current` (public, no auth) → `DisclaimerCurrentOut`, 503 if NoVersionAvailable
  - `POST /api/v1/disclaimer/accept` (auth required via `get_current_user`) → `DisclaimerAcceptOut`, 400 if either confirmation flag is False
  - IP extraction: `x-forwarded-for` header first, else `request.client.host`
  - User-agent: from `request.headers`

**Files modified:**
- `apps/api/models/__init__.py` — appended `DisclaimerVersion` + `DisclaimerAcceptance` ORM models (single-file flat layout); added `INET` import from `sqlalchemy.dialects.postgresql`, `UniqueConstraint` + `Index` from `sqlalchemy`
- `apps/api/schemas/__init__.py` — appended 3 new Pydantic schemas (`DisclaimerAcceptRequest`, `DisclaimerAcceptOut`, `DisclaimerCurrentOut`); extended `UserOut` with `needs_disclaimer: bool = False`
- `apps/api/routers/auth.py` — extended **all 4 auth response paths** (`register`, `login`, `/me`, `/otp/verify`) to compute `needs_disclaimer` via `user_needs_acceptance()`. `/me` endpoint signature extended with `db: AsyncSession = Depends(get_db)`. This is defensive against bypass via legacy login/register endpoints.
- `apps/api/main.py` — registered disclaimer router under `/api/v1` prefix

#### 22.8.3 Frontend (PR #26, commit `614dc51` → `17c48a6`)

**Files added:**
- `apps/web/app/auth/disclaimer/page.tsx` (172 lines, `'use client'`)
  - Fetches `/disclaimer/current` on mount to display v1.0 copy
  - Two checkboxes: age confirmation, positioning confirmation
  - Submit calls `acceptDisclaimer({ confirmed_age_18, confirmed_non_therapy, locale })`
  - On success: `router.push('/app/dashboard')`
  - `BronzeDivider` component finally consumed in production at this screen (was earmarked since shipping)

**Files modified:**
- `apps/web/lib/api.ts` — `User` interface extended with `needs_disclaimer?: boolean`; 3 new types (`DisclaimerCurrent`, `DisclaimerAcceptRequest`, `DisclaimerAcceptResponse`); 2 new methods (`getDisclaimerCurrent()`, `acceptDisclaimer()`). URL paths used relative to `API_BASE` which already includes `/api/v1`.
- `apps/web/app/auth/verify/page.tsx` — conditional disclaimer routing (4 lines added): `if (data.user.needs_disclaimer) router.push('/auth/disclaimer'); else router.push('/app/dashboard')`. `User` type propagates automatically through Zustand store (imported from `./api`).

#### 22.8.4 Production verification

End-to-end verified 2026-05-10 19:53:29 UTC with real `disclaimer_acceptances` row for founder:

```
user_id              = nckoutras@gmail.com's UUID
version_id           = 1
confirmed_age_18     = true
confirmed_non_therapy = true
locale               = 'en'
ip_address           = 94.64.188.99
user_agent           = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
accepted_at          = 2026-05-10 19:53:29.652395+00
```

**Also verified (in incognito 2x):** idempotent re-submit returns 200 success; version-skip routes already-accepted users directly to `/app/dashboard` bypassing `/auth/disclaimer`.

**P1 backlog items created:**
- Integration tests for `/disclaimer/current` + `/disclaimer/accept` (shipped without tests for speed; GDPR audit trail risk — without tests, silent failures in acceptance recording could create legal exposure; ~30 min effort to add 2-3 happy-path + idempotency tests)
- Frontend smoke tests for `/auth/disclaimer`
- Lazy-load monitoring: `acceptance.accepted_at` accessed in router after service `await db.commit()`. If AsyncSession is configured `expire_on_commit=True`, lazy refresh in async context CAN fail. Monitor for `MissingGreenlet` errors in Render logs. If observed, add explicit `await db.refresh(record)` in `disclaimer_service.accept()`. Currently working in production.

### 22.9 Legal Pages Templates — Completion Report (NEW v7)

**PR merged 2026-05-10:** #28 `feat(web): add Terms of Service + Privacy Policy pages`

**Files added:**
- `apps/web/app/legal/terms/page.tsx` (Server component, 123 lines, 16 sections) — Terms of Service v1.0
- `apps/web/app/legal/privacy/page.tsx` (Server component, 121 lines, 13 sections, GDPR-aware) — Privacy Policy v1.0

**Files modified:**
- `apps/web/app/auth/page.tsx` — `'#'` fallback URLs → `/legal/terms` and `/legal/privacy`
- `apps/web/app/auth/verify/page.tsx` — same fallback URL fix

**Env vars:** `NEXT_PUBLIC_TERMS_URL` and `NEXT_PUBLIC_PRIVACY_URL` remain UNSET in Netlify. Setting them later (e.g. for external legal hosting) overrides without code change.

**PR #27 closed without merge.** Earlier failed-push attempt at same content; abandoned after diagnostic. `refs/pull/27/head` persisted as ghost reference — origin of operating principle §19.11 (trust-but-verify CC pushes via `git ls-remote`).

**NEW P0 — Lawyer review of legal templates** before public launch. Greek consumer law specifics, Stripe billing T&Cs, AI-content liability scope all unchecked. Templates are functional placeholders, not legally compliant final copy.

**P4 backlog item:** `target="_blank"` link hardening — auth footers use `target="_blank"` on Terms/Privacy links without `rel="noopener noreferrer"`. Modern browsers default to noopener, but explicit is best practice.

---

## 23. STAKES CONTEXT (NEW v6 — UPDATED v7)

On 2026-05-09 founder shared that Great Minds is being built primarily to support family income. This is documented here so all subsequent mentor sessions inherit the calibration:

- **Long timelines have higher cost than usual.** 12-16 weeks of zero validation has different weight when income depends on outcome.
- **Feature creep is not just a craft concern — it's a runway concern.**
- **Mentor will push back harder on rabbit holes, perfectionism, and "let me also build X while I'm here" patterns.**
- **Mentor will not soften the message.** False politeness costs time the founder does not have.
- **Mentor will respect founder's call.** The 2026-05-06 43-screen decision was reconfirmed 2026-05-10. Mentor still views Plan B (minimum-to-revenue interrupt) as the higher-EV path but will execute Plan A faithfully.
- **Mentor recognizes that founder is non-developer-technical.** This shapes how prompts to Claude Code are structured and how diffs are reviewed.

**2026-05-10 observation (founder energy):** The 2026-05-10 session demonstrated sustained adherence to stakes context — 6 PRs landed cleanly in ~7 hours focused session with monetization-positive outcomes (rate limiter prevents Resend quota burn; A6+A7 generates the legal audit trail required for paid users; legal pages remove a UX friction blocker on the path to monetization). This is exceptional execution for a non-developer-technical solo founder. Discipline is high. **But this also means runway is being consumed at the velocity of Plan A timeline, not Plan B.** Mentor reserves the right to re-raise Plan B at next stakes-relevant moment (UAT signal, runway change, Stripe wiring delay).

If a future session encounters this context for the first time, weight time-to-revenue heavily in trade-off discussions. If circumstances change (founder secures runway from elsewhere, takes contract work, etc.), update this section to reflect new constraints.

---

## 24. BLOCK B PLANNING (NEW v7)

Block A 5/5 closed 2026-05-10. Block B is next in Plan A sequence. **Planning paused awaiting 4 strategic decisions from founder.** Once decisions are confirmed, work resumes immediately.

### 24.1 Block B scope (from `SCREENS_TRACKING_v4`)

| Item | Screen | Notes |
|---|---|---|
| B1 | Welcome | Intro screen, simple |
| B2 | "What brings you here?" | Form (depends on B1) |
| B3 | "What do you need most?" | Form (depends on B2) |
| B4 | Best matches | Persona match output |
| B5 | Persona detail (default) | Data fetch from existing personas table |
| B6 | Persona detail (Pro-locked variant) | **DEFERRED until Stripe lands** |

### 24.2 Four pending strategic decisions

#### Decision 1: B2/B3 answer persistence

- **Options:** (a) frontend-only state (Zustand transient); (b) backend persistence to new `user_preferences` table
- **Mentor recommendation: Backend persistence** + reactive Zustand store
- **Trade-off:** Backend persistence enables retention/segmentation analytics — vital for the monetization signal capture that §23 stakes context demands. Frontend-only is simpler but throws away exactly the data that would tell us why users do/don't convert.

#### Decision 2: Matching algorithm location

- **Options:** (a) frontend-computed (rules in client); (b) backend-computed (POST /matches endpoint)
- **Mentor recommendation: Backend-computed**
- **Trade-off:** Centralized logic, easier iteration without redeploy, can leverage non-exposed persona traits/weights for matching, allows A/B testing matching strategies post-launch. Frontend approach leaks tuning details to anyone reading bundled JS.

#### Decision 3: B6 (Pro-locked variant) timing

- **Options:** (a) build now alongside B5; (b) defer until Stripe block
- **Mentor recommendation: DEFER until Stripe lands**
- **Trade-off:** Building paywall UI before payment infra exists is anti-monetization — if pricing model shifts (it likely will after first UAT signal), the Pro-locked variant gets rebuilt. Avoid wasted work. Aligns with §23 stakes calibration.

#### Decision 4: `user_preferences` schema shape

- **Options:** (a) wide table (1 row per user, columns per question); (b) narrow EAV (1 row per answer)
- **Mentor recommendation: Wide table**
- **Trade-off:** Simpler v1, easier query patterns, fast indexing. Refactor to EAV later if 5+ questions added or schema becomes dynamic. Pre-mature flexibility for hypothetical future needs is a §23 anti-pattern.

### 24.3 Estimated work after decisions confirmed

| Item | Estimate | Notes |
|---|---|---|
| B1 Welcome | ~30 min | Intro screen, simple |
| B2 "What brings you?" | ~45 min | Form, depends on B1 |
| B3 "What do you need?" | ~45 min | Form, depends on B2 |
| Schema migration | ~15 min | `user_preferences` table (alembic 004) |
| Backend endpoint | ~20 min | POST `/api/v1/preferences` (auth required) |
| B4 Best matches | ~75 min | Matching service + UI; backend-computed |
| B5 Persona detail | ~60 min | Data fetch from existing `personas` table |
| B6 Pro-locked variant | DEFERRED | Until Stripe block |
| **Total (excluding B6)** | **~4-5 hours** | Across 4-6 atomic PRs |

### 24.4 Sequencing recommendation

Open the 4 decisions at the start of the next session. Once confirmed, sequence:

1. Schema migration first (alembic 004) — unblocks B2/B3 persistence
2. Backend endpoint — completes data plumbing
3. B1 → B2 → B3 in order (each its own PR; PR cycle discipline per §19.12)
4. B4 (matching) — separate PR with backend service
5. B5 (persona detail) — separate PR

Each step verifies on production before next step. Estimated 2-3 focused sessions to close Block B excluding B6.

---

## 25. CLOSING NOTE FOR NEXT INSTANCE (NEW v7)

**Tone calibration:**

The founder operates with a "ruthless mentor" directive (no flattery, monetization-first, kill bad ideas, recommend alternatives). Match that. The 2026-05-10 session showed the founder can sustain 7+ hours of focused PR work without losing discipline — that is exceptional but it is also the reason Plan A keeps getting confirmed. Watch for energy-driven scope expansion ("while I'm here let me also build X"); §16.A.14 (complete PR cycles before queuing new work) is the active counterweight.

**Documentation hygiene flag (mentor opinion):**

The v6 → v6-addendum → v7 cycle this session produced ~190 KB of merged docs across 3 files. This was warranted because v6 was authoritative for Claude.ai project knowledge upload and Block A 5/5 closure plus legal pages plus Vercel disconnect plus 4 Block B decisions plus 3 new operating principles plus 7 new lessons constituted a significant enough delta. But it also consumed founder time on documentation that did not move revenue.

**Mentor recommendation:** v7 should be the **last full rewrite** until Block B closes. Subsequent sessions append to an addendum file (`*_v7_ADDENDUM_<date>.md`) without rewriting baselines. Only regenerate baseline when (a) Block B closes, (b) Stripe lands, or (c) the addendum file itself exceeds ~30% of baseline length. This is §17.6 / §23 stakes discipline applied to mentor overhead, not just engineering overhead.

**Plan B reconsideration trigger points:**

Mentor will re-raise Plan B (minimum-to-revenue interrupt) if any of:
- Block B Decision 3 (B6 timing) discussion surfaces other "wait for Stripe" deferrals → suggests Stripe should come first
- Block B total time exceeds 6 hours (50% over estimate) → suggests velocity drift
- Stripe wiring 2026-05-11 calendar gate slips by >5 days → ~9-13 week Plan A timeline becomes ~10-14 weeks
- Founder mentions runway pressure or contract-work consideration → Plan B becomes more obviously correct
- UAT signal (when reached) returns <2/5 spontaneous "I'd pay" → 30+ retention screens become provably wrong investment

Document any of these triggers in §21 decision history.

**Next session entry point:**

1. Confirm Plan A still active (default: yes)
2. Resolve 4 Block B strategic decisions (§24.2) — should take 10-15 minutes
3. Open alembic 004 migration for `user_preferences` table (assuming wide-table + backend-computed decisions per mentor recommendations)
4. Sequence B1 → B2 → B3 → backend → B4 → B5 (B6 deferred)
5. Maintain PR cycle discipline per §19.12

---

## END OF v7

**Where v7 conflicts with v6, v7 wins.** v6 conflicts with v5 resolved per v6 §1-14 notes. §1-14 deliberately not duplicated; if needed, retrieve from git history.

**Next session entry point:** confirm Plan A still active, resolve 4 Block B strategic decisions (§24.2), open alembic 004 for `user_preferences`, sequence B1 → B5.

Authoritative as of 2026-05-10 session close. Replaces both `HANDOFF_BRIEF_v6.md` and `HANDOFF_BRIEF_v6_ADDENDUM_2026_05_10.md`.
