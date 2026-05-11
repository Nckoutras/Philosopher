# GREAT MINDS — Implementation Backlog v7

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch. v7 = v6 baseline (2026-05-09) + delta from 2026-05-10 session (Block A 5/5 closure: A4 trouble screen, A6+A7 disclaimer schema/backend/frontend, legal Terms+Privacy templates, Vercel disconnect, rate limiter live verification).
>
> **How to read this file:**
> - This v7 file supersedes v6 and all prior backlog files.
> - Where v7 conflicts with v6, v7 wins.
> - Historical detail from v6 retained where still useful.
> - Status, priority, and launch-readiness calls reflect 2026-05-10 state.
>
> **Last updated:** 2026-05-10. **Block A — Authentication 5/5 line items CLOSED in production.** Block B onboarding paused awaiting 4 strategic decisions (§17.7). Founder confirmed Plan A path is active (Plan B preserved as alternative). Stakes context (§17.6) still authoritative.
>
> **Companion documents:**
> - `SCREENS_TRACKING_v4.md` — full screen inventory and per-screen specs (43 screens)
> - `DESIGN_SYSTEM_v4.md` — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect across user journeys
> - `HANDOFF_BRIEF_v7.md` — continuity and implementation history (replaces v6)
> - `PROJECT_STATE_v7.md` — current project state and session continuity (replaces v6)
>
> **Priority key:**
> - **P0** = launch blocker / must be done before public launch
> - **P1** = post-revenue cleanup / fix shortly after first paying user
> - **P2** = v2 / post-MVP refinement
> - **P3** = post-launch / post-feedback backlog
> - **P4** = technical debt / infrastructure cleanup
>
> **Status key:**
> - 🔴 not started
> - 🟡 in progress
> - 🟢 done
> - ⏸ deferred with reason
>
> **Authoritative rule:** If this file conflicts with any earlier backlog file, this v7 file wins.

---

## v7 Consolidation Summary

### What changed from v6 (2026-05-10 session)

- **Block A — Authentication FULLY CLOSED.** 5 of 5 line items live in production. Beyond v6 baseline (A1, A2/A3, A5), this session shipped: **A4 trouble-accessing-email** (PRs #22, #23, text-center fix), **A6+A7 combined disclaimer screen** (PRs #24 schema, #25 backend, #26 frontend). End-to-end verified with real `disclaimer_acceptances` row for founder's user (2026-05-10 19:53:29 UTC).
- **Legal Terms + Privacy template pages live** (PR #28). Server Components at `/legal/terms` (16 sections) and `/legal/privacy` (13 sections, GDPR-aware). Fixed `'#'` fallback bug in auth footers. ⚠️ Templates only — lawyer review re-opened as P0 launch blocker.
- **Vercel parallel deployment DISCONNECTED.** Founder deleted `thinkalike.vercel.app` project via Vercel dashboard. Production canonical is exclusively `thinkalike.netlify.app`.
- **Schema delta.** `alembic_version` advanced `002_otp_codes` → `003_disclaimer_acceptances` cleanly via container start. Two new tables: `disclaimer_versions` (1 row seeded v1.0), `disclaimer_acceptances` (UNIQUE(user_id, version_id), idempotent INSERT via IntegrityError catch). 15 public tables total now (was 13). RLS still disabled on all; mitigated by FastAPI gateway.
- **Backend additions.** `apps/api/routers/disclaimer.py` (GET /current public + POST /accept auth-required), `apps/api/services/disclaimer_service.py` (module-level functions matching otp_service.py convention), ORM + Pydantic schemas + `needs_disclaimer: bool = False` field on UserOut. All 4 auth response paths (register, login, /me, otp/verify) extended with `needs_disclaimer` computation — prevents bypass via legacy paths.
- **Frontend additions.** 4 new routes: `/auth/trouble`, `/auth/disclaimer`, `/legal/terms`, `/legal/privacy`. `lib/api.ts` extended with 3 types + 2 methods. `app/auth/verify/page.tsx` extended with conditional routing.
- **OTP rate limiter confirmed working in production.** Founder hit `429 Too Many Requests` after 5 requests in 6 minutes — working as designed.
- **Founder confirmed Plan A path is active.** Plan B (minimum-to-revenue interrupt) preserved as alternative but not active. Continue 43-screen sequential build, Block B next.
- **Two new operating principles** added to §16.A: #13 (spec word "centered" means BOTH layout-centered AND text-aligned-center) and #14 (complete PR cycles before queuing new work — compound-risk avoidance).
- **One new mentor pattern flag** logged: trust-but-verify Claude Code push outputs via `git ls-remote origin <branch>` for high-stakes branches.

### Key decisions logged in v7

- **2026-05-10** — Block A 5/5 closed in one focused ~7-hour session, 6 production-merged PRs, zero rollbacks. Sustained STOP-gate discipline throughout. Vercel disconnect resolved.
- **2026-05-10** — Founder confirmed Plan A (43-screen sequence) is active path. Plan B preserved.
- **2026-05-10** — Block B planning surfaced 4 strategic decisions pending founder confirmation (§17.7).
- **2026-05-09** — Block A frontend (A5 verify UI) shipped; alembic plumbing fixed; end-to-end auth verified live.
- **2026-05-08** — Block A backend infrastructure shipped; Resend; Upstash Redis; ARQ background tasks unsilenced.

### Current source-of-truth status

- ✅ Phase 4 stabilization sequence: 8/8 ship items closed
- ✅ Setup PR + Greenfield scaffold (2026-05-07)
- ✅ **Block A — Authentication: 5 of 5 line-items live** (A1, A2/A3, A4, A5, A6+A7)
- ✅ Backend OTP infrastructure (PR #18)
- ✅ Backend disclaimer infrastructure (PRs #24, #25)
- ✅ Alembic plumbing fixed; migrations executing on container start
- ✅ Legal pages templates live (PR #28) — ⚠️ lawyer review pending
- ✅ Vercel parallel deployment disconnected
- ⏳ 40 of 45 line-items remain in 43-screen UI build (5 closed in Block A)
- ⏸ Block B onboarding paused — 4 strategic decisions pending
- ⏳ `/app/dashboard` placeholder page (still 404 by design until Block H+I)
- ⏳ Stripe wiring (calendar-gated, available from 2026-05-11)
- ⏳ Resend domain verification (blocks public launch)
- ⏳ DNS configuration for `thegreatminds.app`
- ⏳ Lawyer review of legal templates
- ⏳ Founder runbooks
- ⏳ UAT with mixed testers
- ⏳ Web/PWA public launch

---

## Quick Reference Table

| Section | What's in it |
|---|---|
| 1. Current launch status | Phase 4 + Block A closed; Phase 5/6 reclassified; Plan A/B fork |
| 2. Remaining launch-readiness checklist | What still matters before public launch |
| 3. Database schemas | Tables and columns required for v1 (now includes `otp_codes`) |
| 4. Config & environment variables | Required launch env vars (now includes RESEND_API_KEY, FROM_EMAIL, REDIS_URL as mandatory) |
| 5. Stripe integration | Portal, webhooks, entitlement, cancellation, pricing (calendar-gated 2026-05-11) |
| 6. API endpoints | Backend routes (OTP endpoints now live in production) |
| 7. Background jobs | Scheduled / async jobs |
| 8. Prompt-level rules & AI engine | Persona behavior, safety, phenomenology, postprocessing |
| 9. Auth & account | OAuth, OTP, deletion, logout, disclaimer (OTP partially live) |
| 10. Privacy & compliance | GDPR, deletion, export, policy requirements |
| 11. Notifications | Email channel, push deferred |
| 12. Frontend behavior | State preservation, validation, sheets, loading/errors |
| 13. Post-launch backlog | P1–P4 work queue (extended with v6 items) |
| 14. v2 / post-MVP backlog | Deliberately deferred product features |
| 15. Block 9 frontend behavior | Empty/error state implementation rules |
| 16. Implementation rules | 16.A operating discipline (12 principles) + 16.B coding/scope rules |
| 17. Immediate recommended next sequence | 43-screen UI build status + Plan A/B fork + stakes context |

---

# 1. Current Launch Status

## 1.1 Status Snapshot

**Updated: 2026-05-10.**

- Phase 4 stabilization sequence closed (8 ship items).
- Setup PR + Greenfield scaffold closed (2026-05-07).
- **Block A — Authentication FULLY CLOSED (2026-05-10)**: A1 splash, A2/A3 sign-in, A4 trouble screen, A5 verify UI, A6+A7 disclaimer all live. End-to-end auth pipeline verified in production with real disclaimer acceptance row.
- Legal Terms + Privacy template pages live (PR #28). ⚠️ Lawyer review pending.
- Vercel parallel deployment DISCONNECTED (2026-05-10).
- Phase 5 (Register architecture + UI chips + classifier) reclassified to P3 post-feedback (2026-05-06).
- Phase 6 (Eval suite + CI) reclassified to P1 post-revenue safety/quality audit (2026-05-06).

**Next P0 work surface — Plan A confirmed active (2026-05-10):**

- **Plan A** — Continue 43-screen sequence with Block B onboarding per `SCREENS_TRACKING_v4`. **PAUSED awaiting confirmation of 4 strategic decisions** (see §17.7).
- **Plan B** — Minimum-to-revenue interrupt path preserved as alternative but **not active**. See §17.5 if circumstances change.

See §17 for full sequence detail.

The previous v5 §1.1 framing of "43-screen UI build is now the next P0 work surface" remains the default if founder confirms Plan A. v6 introduces Plan B as an explicit alternative for founder consideration.

## 1.2 Closed Work — Shipped to Main + Production

| Item | Commit / branch | Status | Notes |
|---|---|---|---|
| **Bug #33 — Safety pathway in-persona voice** | `fix/safety-crisis-pathway` | 🟢 done | Deterministic classifier-only path. LLM-side crisis directives removed. Medium risk now fully suppresses persona. |
| **Bug #34 — US-specific crisis copy → generic** | `fix/safety-crisis-pathway` | 🟢 done | Country-neutral copy. No hotline numbers. |
| **1.7 — `user_name` removal + hotfix** | `0256f97` | 🟢 done | Discipline rule established: full diffs required; grep summaries do not replace caller audit. |
| **1.6 — Nietzsche removal from frontend landing** | `c49c3cd` | 🟢 done | Option A: removed from persona list display only. Backend YAML preserved for v2. |
| **1.4 — Phenomenology trigger audit** | `ae58479` | 🟢 done | +88 verb-form and gerund triggers across 32 entries. |
| **2.1 — Phenomenology map content expansion** | `54a8be4` | 🟢 done | Map expanded 33 → 78 entries. |
| **1.3 — Sentence-boundary truncation 3-layer fix** | `2bf9244` | 🟢 done | Tests 125 → 129. |
| **1.5 — Empty-conversation dedup + in-flight flag** | `718a7dd` | 🟢 done | Tests 129 → 134. |
| **Setup PR — Design tokens, fonts, BronzeDivider/Spinner primitives** | `ad24d15` (PR #13) | 🟢 done | 11 spec colors + Cormorant Garamond/Lora fonts wired into Tailwind + dark mode dropped (forced light). |
| **Greenfield scaffold** | `474f081` (PR #14) | 🟢 done | 19 legacy frontend files deleted (2183 deletions). Backend integration glue preserved. |
| **A1 — Splash screen** (NEW v6) | PR #15 | 🟢 done | Apps/web/app/page.tsx. Live on Netlify. |
| **A2/A3 — Sign-in (email entry)** (NEW v6) | PR #17 | 🟢 done | Email-only path. POST `/auth/otp/request` → 202. Routes to `/auth/verify?email=<encoded>`. |
| **Backend — Passwordless OTP endpoints + Dockerfile alembic-on-boot** (NEW v6) | PR #18 | 🟢 done | `POST /auth/otp/request` (202), `POST /auth/otp/verify` (200 with JWT). 6-digit hashed+salted code, 10-min expiry, max 5 attempts, lockout. Dockerfile CMD updated to `sh -c "alembic upgrade head && exec uvicorn ..."`. |
| **Alembic plumbing fix** (NEW v6) | `fix/alembic-versions-layout` | 🟢 done | Migration files moved into `apps/api/db/migrations/versions/` subdirectory. Alembic was looking in default `versions/` subdir but files were flat. Combined with `alembic_version` stamp at `'002_otp_codes'` via Supabase MCP, restores normal alembic flow for future schema work. |
| **A5 — Verify UI** (NEW v6) | PR #20 | 🟢 done | OTP code entry screen. 6-digit numeric input + autoComplete="one-time-code". Two prerender hotfixes during PR cycle: `dynamic = 'force-dynamic'` insufficient → wrapped useSearchParams in `<Suspense>`. End-to-end auth pipeline verified live. |
| **A4 — Trouble accessing email** (NEW v7) | PR #22 + PR #23 + text-center fix | 🟢 done 2026-05-10 | `apps/web/app/auth/trouble/page.tsx` + link insertion in `/auth/verify`. Iterated 3 PRs: initial Option card with mailto CTA → fix Chrome incognito mailto edge case (button → `<a href="mailto:">`) + reframed card to muted future-state placeholder → fix text-center alignment after orphaned commit lost in squash. Lesson codified as operating principle #13. New env var `NEXT_PUBLIC_SUPPORT_EMAIL` (placeholder `nckoutras@gmail.com`). |
| **A6+A7 — Combined disclaimer schema migration** (NEW v7) | PR #24, commit `acb910c` | 🟢 done 2026-05-10 | alembic `003_disclaimer_acceptances` (55 lines): creates `disclaimer_versions` + `disclaimer_acceptances` tables, seeds v1.0 disclaimer copy. Verified live via Supabase MCP. `alembic_version` advanced `002_otp_codes` → `003_disclaimer_acceptances`. |
| **A6+A7 — Combined disclaimer backend** (NEW v7) | PR #25, commit `4941296` (squashed `8667778`) | 🟢 done 2026-05-10 | New `apps/api/services/disclaimer_service.py` (module-level functions, idempotent `IntegrityError` catch on UNIQUE(user_id, version_id)). New `apps/api/routers/disclaimer.py` (`GET /current` public + `POST /accept` auth-required, `x-forwarded-for` IP extraction). ORM models, Pydantic schemas, `needs_disclaimer: bool = False` on UserOut. All 4 auth response paths (register, login, /me, otp_verify) extended with `needs_disclaimer` computation. |
| **A6+A7 — Combined disclaimer frontend** (NEW v7) | PR #26, commit `614dc51` (squashed `17c48a6`) | 🟢 done 2026-05-10 | New `apps/web/app/auth/disclaimer/page.tsx` (172 lines): BronzeDivider ornament, centered hero, 2 stacked checkbox cards, auth guard, fetch via `getDisclaimerCurrent()`, submit via `acceptDisclaimer()`, inline retry on fetch error. `lib/api.ts` extended with 3 types + 2 methods. `/auth/verify/page.tsx` extended with 4-line conditional routing. End-to-end verified live with real acceptance row. |
| **Legal Terms + Privacy template pages** (NEW v7) | PR #28 | 🟢 done 2026-05-10 | New `apps/web/app/legal/terms/page.tsx` (Server Component, 16 sections, vellum theme, Effective 10 May 2026 v1.0) + `apps/web/app/legal/privacy/page.tsx` (13 sections, GDPR-aware — Article 6 basis, processors table w/ SCC ref, full rights enumeration). Fixed `'#'` fallback bug in `/auth` and `/auth/verify` footers. ⚠️ TEMPLATE only — lawyer review tracked as P0 in §2.1.C. |
| **Vercel parallel deployment disconnect** (NEW v7) | manual via Vercel dashboard | 🟢 done 2026-05-10 | Founder deleted `thinkalike.vercel.app` project. GitHub integration cleanup confirmed. Production canonical exclusively `thinkalike.netlify.app`. |

## 1.3 Current Launch Interpretation

The engine is no longer the main blocker. Phase 5 and Phase 6 are deferred to post-launch. **Block A is FULLY closed (5/5 line items, end-to-end verified).** Block B (Onboarding) is the next P0, **paused awaiting 4 strategic decisions** (§17.7).

The remaining work surfaces, in priority order under Plan A (confirmed active 2026-05-10):

1. **40 of 45 remaining UI line-items** per `SCREENS_TRACKING_v4` — see §17 for ordering.
2. **Stripe wiring** — calendar-gated, available from 2026-05-11.
3. **Lawyer review of legal templates** (NEW v7 P0 launch blocker) — Greek consumer law, Stripe billing T&Cs, AI-content liability scope all unchecked.
4. **Email infrastructure verification** — Resend domain verification for `thegreatminds.app` (current setup uses test sender `onboarding@resend.dev`, only sends reliably to founder email).
5. **DNS configuration for `thegreatminds.app`** — domain registered 2026-05-07.
6. **Operational founder runbooks** — refund, account recovery, GDPR, cancellation, safety escalation.
7. **Production smoke test** of the closed Phase 4 + Block A items.
8. **UAT** with mixed testers (≥2/5 spontaneous "I'd pay" criterion).
9. **Public launch (web/PWA)**.

Under Plan B (preserved but not active), the order shifts dramatically — see §17.5.

Avoid reopening Phase 4 stabilization or Block A work unless:
- production smoke test fails,
- safety classifier shows material false negatives,
- payment entitlement breaks,
- responses show repeated modern-term leakage or severe persona failure,
- auth flow breaks (validate cookie persistence, JWT issuance, disclaimer flow, redirect targets).

---

# 2. Remaining Launch-Readiness Checklist

This section is the practical pre-launch checklist after the 2026-05-09 state.

## 2.1 Must Verify Before Public Launch — P0

### A. Production Smoke Test

- [ ] Incognito / fresh browser sign-up
- [x] Auth flow live and working end-to-end (verified 2026-05-09)
- [ ] All active personas visible and selectable (5 of 6 — Nietzsche removed from frontend)
- [ ] Start a conversation with each persona
- [ ] Chat response latency acceptable
- [ ] No duplicate empty conversation creation
- [ ] Persona responses do not cut mid-sentence in normal use
- [ ] Safety crisis path suppresses persona voice and shows app-voice safety copy
- [ ] Country-neutral safety copy appears where expected
- [ ] No Nietzsche on frontend landing unless intentionally restored
- [ ] Phenomenology map triggers fire naturally for high-frequency terms
- [ ] No catastrophic frontend navigation issue across implemented screens
- [ ] **Sign out works correctly** (cookie + localStorage cleared, redirect to /auth) — pending /app/dashboard placeholder build

### B. Stripe / Payment Verification (calendar-gated 2026-05-11)

- [ ] Production Stripe account live
- [ ] Products + prices created for monthly and annual plans (EUR)
- [ ] Stripe Checkout works with real test card
- [ ] Webhook endpoint configured with signature verification
- [ ] Subscription created → user entitlement updates correctly
- [ ] Subscription updated → cached user fields update correctly
- [ ] Cancellation at period end works
- [ ] Past-due / failed payment path tested or explicitly accepted as Stripe-managed for v1
- [ ] Customer Portal configured and reachable from H5
- [ ] Refund process documented for founder/admin manual operation
- [ ] No frontend code path calls Stripe directly (must use backend `/api/subscription`)

### C. Legal / Privacy

- [x] **Terms of Use written and live at `/legal/terms`** (PR #28, 2026-05-10) — ⚠️ TEMPLATE v1.0, lawyer review still pending below
- [x] **Privacy Policy written and live at `/legal/privacy`** (PR #28, 2026-05-10) — ⚠️ TEMPLATE v1.0, lawyer review still pending below
- [x] **Disclaimer copy v1.0 finalized and stored in `disclaimer_versions`** (PR #24, 2026-05-10) — `age_copy` + `positioning_copy` seeded; current effective version
- [x] **Disclaimer re-acceptance flow forced on sign-in if version changed** (PR #26, 2026-05-10) — `needs_disclaimer` computation in all 4 auth response paths; redirect to `/auth/disclaimer` if true; verified working
- [ ] **NEW P0 v7: Lawyer review of legal templates** — Greek consumer law specifics, Stripe billing T&Cs, AI-content liability scope all unchecked. **Pre-public-launch blocker.**
- [ ] About Great Minds copy written for in-app sheet
- [ ] DPO/contact info or founder privacy contact in Privacy Policy (currently template placeholder)
- [ ] LLM provider data-processing terms reviewed at practical founder level
- [ ] Stripe agreement / account requirements completed
- [ ] Cookie posture verified: strictly necessary cookies only → no consent banner needed; if analytics/marketing cookies added, consent handling required

### D. Database / Backend

- [x] **Required tables migrated:** `disclaimer_versions`, `disclaimer_acceptances` (PR #24, 2026-05-10). Still pending: `cancellation_reasons`, `data_requests`, `notification_preferences` (Block H/I work)
- [x] **`otp_codes` table created (PR #18, applied via direct SQL 2026-05-09)** with `(email, created_at DESC)` index
- [x] **`disclaimer_versions` + `disclaimer_acceptances` tables created (PR #24, 2026-05-10)** — `UNIQUE(user_id, version_id)` enforces idempotency; INET ip_address column; v1.0 seeded
- [ ] Required user columns exist: `subscription_status`, `current_period_end`, `cancel_at_period_end`, `stripe_customer_id`, `stripe_subscription_id`, `account_deleted_at`
- [ ] Indices created where specified
- [ ] Personal data column flags applied (per §10.3)
- [ ] Account deletion guard checks Stripe before deletion
- [ ] Data request creation and expiry path works
- [x] Logout clears user-specific cached data (Block A `clearAuth` + `setToken(null)` cleans cookie + localStorage + Zustand store) — verify implementation in `/app/dashboard` page when built
- [ ] Backup/restore procedure understood at minimum practical level
- [ ] **RLS audit** — all 15 public Supabase tables currently have RLS DISABLED (was 13; +2 new disclaimer tables 2026-05-10 follow same convention). Mitigated by frontend going through FastAPI exclusively, but anon key exposure in client code (none currently, but flag if added) would be a serious vulnerability. Pre-launch blocker for any scenario where direct Supabase access from frontend is added.
- [ ] **Database reality verification** — confirm whether Render `philosopher-db` is decommissioned (v5 stated it was live; reality 2026-05-08/09 shows Supabase is live).
- [x] **`alembic_version` table state aligned** with deployed code (stamped at `'003_disclaimer_acceptances'` 2026-05-10)
- [x] **Future schema migrations will execute on container start** (Dockerfile fix + versions/ subdirectory layout) — verified working 2026-05-10 with `003_disclaimer_acceptances` deploying cleanly

### E. Email / Operations

- [ ] Support email configured via `SUPPORT_EMAIL`
- [x] **Email provider configured: Resend (2026-05-08)**
- [x] **`RESEND_API_KEY` set in Render env vars**
- [x] **`FROM_EMAIL` set to "Great Minds <onboarding@resend.dev>" in Render env vars**
- [ ] **Sender domain authenticated (SPF / DKIM / DMARC) for `thegreatminds.app`** — Resend free tier currently uses test sender `onboarding@resend.dev`; only reliable for sends to founder's email. **Public launch blocker.**
- [ ] Weekly letter template tested (only if weekly letters ship in v1; otherwise skip)
- [ ] Account deletion confirmation email template tested
- [ ] Data export ready email template tested
- [ ] Unsubscribe link in any marketing emails (none planned for v1, but required if any go out)
- [ ] Founder receives / admin monitors data request notifications
- [ ] Support inbox monitored
- [ ] Stripe webhook failures alert founder or are visible in Stripe dashboard
- [ ] Founder runbook exists for: refund, account recovery, GDPR fulfillment, cancellation override, safety escalation review

### F. UAT / Market Validation

- [ ] Run UAT with 3–5 mixed testers
- [ ] Tester mix: 1–2 close friends, 1–2 acquaintances, 1–2 strangers
- [ ] Avoid using only supportive friends as validation
- [ ] Launch criterion: at least 2 of 5 testers spontaneously indicate they would pay
- [ ] If fewer than 2 of 5 say they would pay, iterate before public launch

### G. Auth — Block A Production Verification

- [ ] Google Sign In OAuth client configured for production (deferred per founder; OTP-only is launch path)
- [x] **Email OTP working with chosen provider** (Resend, verified live 2026-05-09)
- [x] **OTP endpoint live** (POST `/auth/otp/request` → 202)
- [x] **OTP verify endpoint live** (POST `/auth/otp/verify` → 200 with JWT)
- [x] **JWT cookie + localStorage persistence working** (verified live)
- [x] **Zustand store auth state synchronized** (verified live)
- [x] **Rate limiting active in production** (`OTP_RATE_LIMIT_PER_HOUR`, `OTP_LOCKOUT_AFTER_ATTEMPTS`, `OTP_LOCKOUT_DURATION_MINUTES`) — **VERIFIED WORKING 2026-05-10:** founder hit `429 Too Many Requests` on `/auth/otp/request` after 5 requests in 6 min. Document actual env-var values in next regenerated PROJECT_STATE for visibility.
- [ ] Account linking tested with verified-email auto-link path
- [ ] OTP state machine tested end-to-end (5-attempt lockout, 10-min expiry, resend cooldown — resend cooldown UI deferred per A5 MVP scope, lockout/expiry validated in backend tests only)
- [x] **A4 — "Trouble accessing email" screen** (PRs #22, #23, text-center fix, 2026-05-10) — `apps/web/app/auth/trouble/page.tsx`, currently muted future-state placeholder with mailto fallback
- [x] **A6+A7 — Combined age + positioning disclaimer screen** (PRs #24, #25, #26, 2026-05-10) — schema + backend + frontend chain live, end-to-end verified with real acceptance row
- [x] **Disclaimer re-acceptance flow forced on sign-in if version changed** — `needs_disclaimer` computation in all 4 auth response paths; conditional routing in `/auth/verify`
- [ ] Apple Sign In **explicitly deferred** to native app submission (v2)

### H. Web Deployment

- [x] **Production deployment URL live: https://thinkalike.netlify.app** (canonical)
- [x] **Vercel parallel deployment DISCONNECTED 2026-05-10** — founder deleted `thinkalike.vercel.app` project via Vercel dashboard; GitHub integration cleanup confirmed
- [ ] SSL/TLS verified (presumably yes since site is serving)
- [ ] HTTPS-only enforcement
- [ ] PWA manifest validated (if installable PWA targeted for v1)
- [ ] Production env vars hardened (no committed secrets, no hardcoded URLs in components — `api.ts` falls back to hardcoded Render URL if `NEXT_PUBLIC_API_URL` not set)
- [ ] **Custom domain `thegreatminds.app` DNS + SSL configured** (registered 2026-05-07)
- [ ] **Brand consolidation pass** (currently displays "Philosopher — Your Reflective Companion"; brand is "Great Minds")

## 2.2 No Longer Launch Blockers Unless Newly Broken

These were either dropped, reclassified, or never v1-critical:

- Marcus shading content (33 strings) — post-launch
- ~200 persona shading paragraphs for expanded phenomenology entries — post-launch
- True lazy-create routing refactor for empty conversations — v2
- Frontend race in same render frame — backend dedup already catches it; theoretical
- Full observability optimization for sentence-boundary truncation — post-launch monitor
- PostHog event polish — post-revenue unless already wired
- App store submission (iOS / Google Play) — v2 only; v1 launch is web/PWA only
- **A5 polish items (resend cooldown timer, edit-email back button, per-digit boxes with auto-advance)** — deferred per Block A MVP scope; current single-input + autoComplete="one-time-code" works on all platforms

---

# 3. Database Schemas

Schemas are illustrative; final migrations should reference Supabase types and be reviewed before applying.

## 3.1 `cancellation_reasons`

**Priority:** P0 if cancellation flow ships at or before payment launch.

```sql
cancellation_reasons (
    id uuid primary key,
    user_id uuid references users(id),
    reason_code enum (
        'not_using_enough',
        'too_expensive',
        'not_useful_enough',
        'expected_more_from_personas',
        'temporary_need',
        'technical_issue',
        'other'
    ) not null,
    free_text varchar(300) nullable,
    created_at timestamp default now(),
    outcome enum (
        'canceled_confirmed',
        'not_canceled_after_24h',
        'superseded',
        'unknown'
    ) default 'unknown',
    expires_at timestamp default (now() + interval '24 hours'),
    status enum (
        'sent_to_stripe',
        'resolved'
    ) default 'sent_to_stripe'
)
```

Notes:
- `free_text` is personal data.
- Index for duplicate prevention lookup, e.g. on `(user_id, status, expires_at)`.
- Prefer extending this table rather than creating a separate `cancel_intents` table.
- When `outcome` is set, flip `status` to `resolved`.

## 3.2 `data_requests`

**Priority:** P0 — GDPR Article 17 / 20 operational support.

```sql
data_requests (
    id uuid primary key,
    user_id uuid references users(id),
    request_type enum ('export', 'deletion', 'correction') not null,
    status enum (
        'requested',
        'processing',
        'completed',
        'rejected',
        'expired'
    ) default 'requested',
    requested_at timestamp default now(),
    completed_at timestamp nullable,
    user_email varchar not null,
    notes text nullable
)
```

Notes:
- `notes` is internal admin-only field.
- Auto-expire stale `requested` rows after `DATA_REQUEST_EXPIRY_DAYS`.

## 3.3 `disclaimer_versions` + `disclaimer_acceptances` (STATUS: 🟢 LIVE IN PRODUCTION — PR #24, 2026-05-10)

**Priority:** P0 — legal update re-prompt mechanism. **STATUS UPDATED v7:** Tables created and seeded in production. alembic_version advanced from `002_otp_codes` → `003_disclaimer_acceptances` cleanly via container start.

**Actual production schema** (slightly extended from v5/v6 spec to capture per-flag audit + audit fields):

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

**Differences from v5/v6 spec:**
- v5 spec had single `copy` field on versions; v7 production splits into `age_copy` + `positioning_copy` for distinct rendering (mirrors A6+A7 combined screen's two checkbox cards).
- v5 spec had no audit fields; v7 production includes `locale`, `confirmed_age_18`, `confirmed_non_therapy`, `ip_address` (INET), `user_agent` to satisfy GDPR audit trail expectations.
- `version` renamed `version_string` for clarity (avoids SQL keyword collision).

**Seed data (v1.0, PR #24):**
- `age_copy`: "I am 18 years or older."
- `positioning_copy`: "I understand Great Minds is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional."

**Behavior (verified live 2026-05-10):**
- A6+A7 acceptance writes a row with both confirmation flags = true, IP + UA captured, accepted_at = now().
- On every auth response path (register, login, /me, otp/verify), backend calls `user_needs_acceptance(user_id, db)` → if user has no row for current version, returns true; frontend `/auth/verify` then routes to `/auth/disclaimer`.
- If user already accepted current version, returns false; frontend routes to `/app/dashboard` (still 404 until Block H+I).
- `UNIQUE (user_id, version_id)` enforces idempotency; service catches `IntegrityError` on duplicate INSERT, queries existing row and returns it as success.

## 3.4 `notification_preferences`

**Priority:** P0 if weekly letters / notification settings are exposed in v1.

```sql
notification_preferences (
    user_id uuid primary key references users(id),
    weekly_letters boolean default null,
    reflection_reminders boolean default false,
    product_updates boolean default false,
    updated_at timestamp default now()
)
```

Defaults at read-time:
- Pro user + `weekly_letters = null` → treat as ON.
- Free user weekly letters are ignored / not controllable; show Pro pill if surfaced.
- `reflection_reminders` and `product_updates` default OFF.

## 3.5 `users` Table Additions

**Priority:** P0 for payment launch.

Required columns:
- `subscription_status` — cached from Stripe webhook; never fully authoritative
- `current_period_end` — cached
- `cancel_at_period_end` — cached boolean
- `stripe_customer_id`
- `stripe_subscription_id`
- `account_deleted_at` — soft-delete timestamp

Rules:
- Cached columns are updated by webhook handlers.
- For billing-critical UI, query backend entitlement function; do not trust frontend cache.
- Before destructive account deletion, re-query Stripe.

## 3.6 `otp_codes` (NEW v6 — shipped 2026-05-08 via PR #18)

**Priority:** P0 — Block A authentication. **STATUS: 🟢 LIVE IN PRODUCTION (Supabase, applied via direct SQL 2026-05-09 due to alembic plumbing being broken at go-live).**

```sql
otp_codes (
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
```

Notes:
- `code_hash` is bcrypt or similar hash of the 6-digit code + `salt`.
- 10-minute expiry from `created_at`.
- Max 5 attempts before lockout.
- Index `(email, created_at DESC)` supports efficient "latest unused code for this email" lookup.
- `used_at` set when code is verified successfully.
- Expired/used rows can be swept by a background job (see §7.6).

---

# 4. Config & Environment Variables

## 4.1 Required at v1 Launch

| Variable | Purpose | Source | Status |
|---|---|---|---|
| `SUPPORT_EMAIL` | Destination for support / I4 mailto routes | Founder mailbox | ⏳ |
| `STRIPE_SECRET_KEY` | Stripe API access | Stripe dashboard | ⏳ |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification | Stripe webhook config | ⏳ |
| `STRIPE_CUSTOMER_PORTAL_URL` | H5 manage subscription target | Stripe Portal config | ⏳ |
| `STRIPE_CHECKOUT_PRICE_ID_MONTHLY` | Monthly checkout price | Stripe Products | ⏳ |
| `STRIPE_CHECKOUT_PRICE_ID_ANNUAL` | Annual checkout price | Stripe Products | ⏳ |
| `TERMS_URL` | External Terms link | Website | ⏳ |
| `PRIVACY_POLICY_URL` | External Privacy Policy link | Website | ⏳ |
| `OPENAI_API_KEY` or equivalent | LLM provider | Provider dashboard | ✅ |
| `ANTHROPIC_API_KEY` | LLM provider | Provider dashboard | ✅ |
| `OTP_RATE_LIMIT_PER_HOUR` | OTP rate limit; default 5 | App config | ⏳ verify |
| `OTP_LOCKOUT_AFTER_ATTEMPTS` | OTP lockout threshold; default 5 | App config | ⏳ verify |
| `OTP_LOCKOUT_DURATION_MINUTES` | OTP lockout duration; default 15 | App config | ⏳ verify |
| `DATA_REQUEST_EXPIRY_DAYS` | Data request expiry; default 30 | App config | ⏳ |
| `ACCOUNT_DELETION_GRACE_PERIOD_DAYS` | Soft-delete grace; default 30 | App config | ⏳ |
| `CANCEL_INTENT_WINDOW_HOURS` | Cancel intent reconciliation window; default 24 | App config | ⏳ |
| `PHENOMENOLOGY_BRIDGE_ENABLED` | Phenomenology bridge flag; should reflect post-smoke-test decision | App config | ⏳ verify state |
| `DATABASE_URL` | Postgres connection string (Supabase) | Supabase dashboard | ✅ |
| `RESEND_API_KEY` (NEW v6 — promoted from optional) | Email provider auth | Resend dashboard | ✅ set 2026-05-08 |
| `FROM_EMAIL` (NEW v6 — promoted from optional) | OTP/notification sender | App config | ✅ set 2026-05-08 to `Great Minds <onboarding@resend.dev>`; **switch to verified domain before public launch** |
| `REDIS_URL` (NEW v6 — promoted from optional) | Upstash Redis for ARQ + APScheduler + rate limiting | Upstash dashboard | ✅ set 2026-05-08 |
| `JWT_SECRET` | JWT signing | App config | ✅ |
| `POSTPROCESSING_ENABLED` | Phase 2 postprocessing toggle | App config | ✅ explicitly set |
| `NEXT_PUBLIC_SUPPORT_EMAIL` (NEW v7 — A4 trouble screen) | Support mailto target on /auth/trouble | Frontend env | ✅ set 2026-05-10 to `nckoutras@gmail.com` (placeholder until real `support@thegreatminds.app` mailbox) |

## 4.2 Optional / Future

- `POSTMARK_API_KEY` or equivalent backup email provider key
- `PUSH_NOTIFICATION_KEY` for v2 push notifications
- `SENTRY_DSN` for error monitoring
- `ANALYTICS_KEY` for product analytics
- `NEXT_PUBLIC_API_URL` (frontend) — currently relies on api.ts hardcoded fallback to `https://philosopher-api-z9l9.onrender.com/api/v1`; explicit set recommended
- `NEXT_PUBLIC_TERMS_URL`, `NEXT_PUBLIC_PRIVACY_URL` (frontend) — **UPDATED v7 2026-05-10:** PR #28 changed fallbacks from `#` to hardcoded `/legal/terms` and `/legal/privacy` (the in-app legal template pages). Env vars remain UNSET in Netlify; setting them later (e.g. for external legal hosting) overrides the fallbacks without code change. No longer a launch blocker.

## 4.3 Forbidden Patterns

- Never hardcode `SUPPORT_EMAIL` in UI components.
- Never hardcode Stripe URLs in components.
- Never call Stripe directly from frontend UI.
- Never commit secrets to repo.
- Move hardcoded production URLs from `.env.production` to hosting env vars.
- Avoid partial dependency pinning long-term; move toward full pinning after launch.
- **Never paste production API keys, Stripe secrets, JWT secrets, or RESEND/REDIS connection strings into chat or commit messages.** Rotate immediately if leaked.

---

# 5. Stripe Integration

> **Calendar gate:** Stripe wiring is available from **2026-05-11**. Until then, payment infrastructure work is blocked. All §5 verification items are P0 but cannot start before that date.

[§5.1–§5.6 unchanged from v5 — see v5 for full content. Pricing baseline: EUR €9.99/mo + €119.99/yr, 14-day money-back guarantee, manual refunds via Stripe dashboard for v1.]

## 5.1 Customer Portal Setup

**Priority:** P0 for paid launch.

Enable: update payment method, view invoices/billing history, update billing address, cancel subscription (end-of-period for v1), reactivate canceled subscription within grace period if supported.

Disable for v1: plan changes via portal if monthly/annual switching is not implemented cleanly; multiple subscription management.

## 5.2 Webhook Events

**Endpoint:** `POST /api/webhooks/stripe`

| Event | Action |
|---|---|
| `customer.subscription.created` | Update `users.subscription_status`, `stripe_subscription_id`, customer reference |
| `customer.subscription.updated` | Update cached status, `cancel_at_period_end`, `current_period_end` |
| `customer.subscription.deleted` | Set `subscription_status = canceled`; retain access if period end remains in future |
| `invoice.payment_failed` | Set `subscription_status = past_due`; optional email path |
| `invoice.payment_succeeded` | Set `subscription_status = active`; clear past-due state |
| `customer.deleted` | Mark user as Stripe-orphaned edge case |

Rules: verify signature with `STRIPE_WEBHOOK_SECRET`; idempotent handler; respond within 20 seconds; queue heavy work.

## 5.3 Effective Entitlement Function

Backend function `get_effective_entitlement(user_id)` returns: `free`, `pro_active`, `past_due` (access still allowed unless decided otherwise), `canceling_at_period_end` (access until date), `canceled_no_access`.

Rules: billing-gated UI must use this function; frontend never calls Stripe directly; cached user columns are convenience state, not final truth.

## 5.4 Cancel Intent Reconciliation

Hourly or webhook-triggered job. For each `cancellation_reasons` row where `status = 'sent_to_stripe'`: if Stripe shows cancellation within `[created_at, expires_at]` → `outcome = 'canceled_confirmed'`, `status = 'resolved'`. If `expires_at` passed → `outcome = 'not_canceled_after_24h'`, `status = 'resolved'`. Otherwise leave unchanged. New cancel intent supersedes previous.

## 5.5 Account Deletion Subscription Guard

Before deletion: query Stripe for active subscription; if present, return `active_subscription_exists` and block deletion in UI.

## 5.6 Pricing Configuration

Baseline v4 pricing decision (preserved): EUR, €9.99/mo, €119.99/yr, no trial, 14-day money-back, manual refunds via Stripe dashboard for v1. **Decision pending in `PROJECT_STATE_v6.md` §10:** confirm pricing before H1 pricing page implementation OR Plan B paywall trigger.

---

# 6. API Endpoints

## 6.1 Block 6 / Account / Subscription Routes

| Method | Route | Purpose | Status |
|---|---|---|---|
| POST | `/api/cancel_intents` | Save cancellation reason and create intent row | ⏳ |
| GET | `/api/subscription` | Fetch effective entitlement | ⏳ |
| POST | `/api/data_requests` | Create export / deletion / correction request | ⏳ |
| GET | `/api/data_requests/active` | Check pending request state | ⏳ |
| POST | `/api/account/delete` | Trigger account deletion with Stripe guard | ⏳ |
| GET | `/api/notification_preferences` | Fetch notification toggles | ⏳ |
| PATCH | `/api/notification_preferences` | Update notification toggles | ⏳ |
| POST | `/api/auth/logout` | Clear session and cached user data | ⏳ verify |

## 6.2 Existing Routes — Status Updated

| Route | Status |
|---|---|
| `/api/auth/oauth/{provider}` — OAuth flow | ⏳ scaffolded; deferred to P1 post-revenue per founder |
| `/api/v1/auth/otp/request` — send OTP | ✅ **LIVE 2026-05-08 (PR #18)** — returns 202 Accepted |
| `/api/v1/auth/otp/verify` — verify OTP | ✅ **LIVE 2026-05-08 (PR #18)** — returns 200 with AuthResponse `{access_token, token_type, user}`. **Extended 2026-05-10 (PR #25):** `user.needs_disclaimer: bool` field added (true for fresh users / users who haven't accepted current version). |
| `/api/v1/disclaimer/current` — fetch active disclaimer version | ✅ **LIVE 2026-05-10 (PR #25)** — public (no auth), returns `DisclaimerCurrentOut { version_string, age_copy, positioning_copy }`. 503 if no version seeded. |
| `/api/v1/disclaimer/accept` — record disclaimer acceptance | ✅ **LIVE 2026-05-10 (PR #25)** — auth required via `get_current_user`, body `{ confirmed_age_18, confirmed_non_therapy, locale? }`. Returns `DisclaimerAcceptOut { accepted_at, version_string }`. 400 if either flag is false. Idempotent on UNIQUE(user_id, version_id) — catches IntegrityError, queries existing row, returns 200 success. IP via x-forwarded-for header, UA from request headers. |
| `/api/messages` — chat send and history | ✅ verified live |
| `/api/saved_lines` — save/retrieve reflections | ⏳ verify |
| `/api/conversations` — conversation creation; empty-conversation dedup behavior | ✅ verified live |

## 6.3 Webhook Route

- `POST /api/webhooks/stripe` — all Stripe events (P0, calendar-gated 2026-05-11)

---

# 7. Background Jobs

[§7.1–§7.6 unchanged from v5 with one v6 update: §7.6 OTP cleanup is now operationally relevant since `otp_codes` table is live.]

## 7.1 Weekly Letter Generation

**Priority:** P0 only if weekly letters are included in v1 paid promise; otherwise P1/P2.

Rules: Sundays at user-local adjusted time (e.g. 7am); only Pro users with weekly letters ON or default ON; skip if insufficient material; do not send thin letters; track token usage per generated letter.

## 7.2 Cancel Intent Reconciliation

**Priority:** P0 if cancellation reason capture is live. See §5.4.

## 7.3 Subscription State Cache Refresh

**Priority:** P1. Daily job; for each Pro user, re-query Stripe and refresh cached fields; catches missed webhooks.

## 7.4 Data Request Expiry Sweeper

**Priority:** P0 for GDPR operational hygiene. Daily job; rows where `status = requested` and older than `DATA_REQUEST_EXPIRY_DAYS` → `expired`.

## 7.5 Soft-Deleted Account Hard-Delete Sweeper

**Priority:** P0 if account deletion is live. Daily job; after `ACCOUNT_DELETION_GRACE_PERIOD_DAYS`, cascade-delete user data; preserve aggregate analytics only if user reference removed.

## 7.6 OTP Cleanup (NEW relevance v6)

**Priority:** P1.

- Hourly job.
- Delete expired OTP records older than configured window (e.g. 10 minutes unused).
- **Now operationally relevant** since `otp_codes` table is live (PR #18, 2026-05-08). Without cleanup, table grows linearly with every auth attempt. Not blocking launch (table size will be small for some time), but should be running before significant traffic.

---

# 8. Prompt-Level Rules & AI Engine

[§8.1–§8.7 unchanged from v5. Engine work is closed; postprocessing pipeline active in production; modern phenomenology bridge active; map at 78 entries; safety pathway deterministic; sentence-boundary fix shipped.]

---

# 9. Auth & Account

## 9.1 Platform-Aware OAuth Provider Order

For v1 web/PWA launch:
- Web/PWA: ~~Google,~~ email (passwordless OTP only — Google deferred)
- Apple Sign In deferred to native app submission (v2)
- Google OAuth deferred to P1 post-revenue per founder (Block A MVP scope)

## 9.2 Account Linking Security

[Unchanged from v5.] Auto-link two providers only when both report `email_verified: true`; if unverified, require OTP confirmation; never link based on email string alone. **Currently moot for v1 since only OTP path is active.**

## 9.3 OTP State Machine — STATUS UPDATE v6

States:
- Wrong code attempts 1–4 → inline error, retry — **🟢 backend logic live (PR #18); UI error toasts wired in A5 (PR #20)**
- Wrong code attempt 5 → lockout 15 minutes — **🟢 backend logic live; UI displays appropriate error message via A5 toast**
- Expired code >10 minutes → prompt to send new code — **🟢 backend returns 410; A5 toast says "Code expired. Request a new one."**
- Resend cooldown → disabled resend link with countdown — **🔴 NOT BUILT in A5 MVP** (deferred per scope; user must navigate back to /auth manually for new code)
- >5 OTP requests/hour → rate-limit message — **🟡 backend logic exists in `rate_limit_service.py` (uses Redis); UI message wired; verify rate limit values match `OTP_RATE_LIMIT_PER_HOUR` env var**
- Different email → back to sign-in with field cleared — **🔴 NOT BUILT in A5 MVP** (no edit-email back button; refresh works as workaround)

**Polish items from §13.2 P2 candidates:**
1. Resend cooldown timer UI on /auth/verify
2. Edit-email back button on /auth/verify
3. Per-digit boxes with auto-advance instead of single 6-digit input

## 9.4 Account Deletion

[§9.4 unchanged from v5.] Two-stage soft + hard delete with grace period.

## 9.5 Logout Behavior

On sign out:
- Clear access token, refresh token, session cookie. **🟢 PR #20 implemented `clearAuth()` + `setToken(null)` for /app/dashboard sign out button** (placeholder dashboard page not yet built)
- Clear user-specific cached conversations, saved reflections, profile, subscription state, last active session context, persona preferences, last-viewed letters.
- Keep only non-identifying device preferences.

[Allowed/not-allowed lists unchanged from v5.]

## 9.6 Disclaimer Re-Acceptance

[Unchanged from v5.] On sign-in, check current effective version; force re-prompt if missing.

## 9.7 Block A — Status Reconciliation (UPDATED v7)

| Screen | Spec status (`SCREENS_TRACKING_v4`) | Implementation status (2026-05-10) | Notes |
|---|---|---|---|
| A1 — Splash | Specced | 🟢 live (PR #15, `ad24d15`) | `apps/web/app/page.tsx` |
| A2/A3 — Sign up + Sign in (merged) | Specced as merged | 🟢 live (PR #17, `e2dcf9f`) | `apps/web/app/auth/page.tsx` — email-only path |
| A4 — Trouble accessing email | Specced | 🟢 live (PRs #22, #23, text-center fix, 2026-05-10) | `apps/web/app/auth/trouble/page.tsx` — muted future-state placeholder with mailto fallback. Apple/Google sign-in messaging deferred until OAuth lands. |
| A5 — OTP / Email verification | Specced | 🟢 live (PR #20) | `apps/web/app/auth/verify/page.tsx` — single-input 6-digit + autoComplete="one-time-code". Polish (per-digit boxes, resend cooldown, edit-email back) deferred to P3. |
| A6+A7 — Combined age + positioning disclaimer | Specced as combined | 🟢 live (PRs #24, #25, #26, 2026-05-10) | `apps/web/app/auth/disclaimer/page.tsx` (172 lines) — BronzeDivider ornament, 2 checkbox cards, end-to-end verified with real acceptance row. Disclaimer rendered as Block A (not Block B) per founder decision 2026-05-10. |

**Block A: 5 of 5 line items closed in production.**

---

# 10. Privacy & Compliance

[§10.1–§10.6 unchanged from v5. GDPR Article 17, 20, 16 handling; personal data classification; cookie posture; Privacy Policy requirements.]

---

# 11. Notifications

[§11.1–§11.3 unchanged from v5. Email-only in v1; push deferred to v2; in-app banners deferred.]

---

# 12. Frontend Behavior

[§12.1–§12.5 unchanged from v5 with one v6 update.]

## 12.1 State Preservation

[List unchanged from v5 plus:]
- **OTP attempt count server-side** — backed by `otp_codes.attempts` column (PR #18) ✅
- **Auth state across session** — Zustand `philosopher-store` persists `user`, `token`, `subscription` to localStorage (PR #20 setAuth integration) ✅

## 12.2 Validation Patterns

[Unchanged from v5 plus:]
- **OTP: 6 digits, single input field with `inputMode="numeric"` and `autoComplete="one-time-code"`** (Block A MVP); auto-advance per-digit boxes deferred to polish

## 12.3 Loading & Error States

[Unchanged from v5 plus:]
- **A5 verify loading state**: button text changes to "Verifying…" while POST in flight; input disabled during request; `setIsLoading(false)` only on error path (success navigates away)

## 12.4 Sheet Behavior

[Unchanged from v5.]

## 12.5 Empty Conversation Dedup Behavior

[Unchanged from v5.]

---

# 13. Post-Launch Backlog — P1 to P4

## 13.1 P1 — Early Post-Revenue Cleanup / Safety & Quality Audit

[v5 entries 1–3 unchanged.]

1. **Phase 6 — Eval suite + CI** (4 tests + adversarial classifier coverage 30-50 novel crisis phrases; time-boxed)
2. **Formal production smoke test documentation for `user_name` removal**
3. **Monitor sentence-boundary observability** (if `brevity_passed_but_mid_sentence` >5%, revisit)

**NEW v6 entries:**

4. **Google OAuth re-enablement** — Block A MVP shipped passwordless OTP only. Re-evaluate Google OAuth post-revenue based on user feedback (signup friction).
5. **Auth flow integration tests with mocked Resend + TestClient** — currently relies on live verification. Pre-existing v5 backlog item, escalated post-Block-A live since the flow is now critical revenue path.
6. **A5 polish: resend cooldown timer + edit-email back button + per-digit boxes** — UI polish deferred from MVP. Add only if user feedback signals friction.

**NEW v7 entries (2026-05-10 session):**

7. **A6+A7 disclaimer endpoint integration tests** — Currently shipped without tests for speed (founder decision). GDPR audit trail risk — without tests, silent failures in acceptance recording could create legal exposure. ~30 min effort to add 2-3 happy-path + idempotency tests. Test cases: (a) happy path POST accept → row created + correct response, (b) duplicate POST accept → 200 + same row (idempotency), (c) one flag false → 400.
8. **A6+A7 frontend page tests (smoke level)** — Same speed-vs-coverage trade-off. Frontend is visually verifiable, lower priority than backend.
9. **A6+A7 lazy-load monitoring** — `acceptance.accepted_at` accessed in router after service `await db.commit()`. If AsyncSession is configured `expire_on_commit=True`, lazy refresh in async context CAN fail. Monitor for `MissingGreenlet` errors in Render logs. If observed, add explicit `await db.refresh(record)` in `disclaimer_service.accept()`. Currently working in production.
10. **A4 mailto: visible support email fallback** — When real `support@thegreatminds.app` mailbox exists, swap placeholder `nckoutras@gmail.com` from `NEXT_PUBLIC_SUPPORT_EMAIL`.

## 13.2 P2 — Product / AI Refinements

[Unchanged from v5.]

1. **Modern-term-leak post-check**
2. **Adversarial truncation strip UX smoothing**
3. **Context-aware safety variants**

## 13.3 P3 — Post-Launch / Post-Feedback Queue

[Unchanged from v5.]

1. **Phase 5 — Register architecture + UI chips + classifier**
2. **~10 missing triggers**
3. **~200 persona shading paragraphs**
4. **Marcus shading content** (Phase 4 PR Β, 33 strings)
5. **Real persona avatar artwork**
6. **Frontend race in same render frame**

**NEW v7 entries (2026-05-10 session):**

7. **A5 polish** — Per-digit OTP boxes (currently single 6-digit input), expiry countdown, resend cooldown indicator. Founder explicitly mentioned wanting per-digit boxes "eventually". MVP form is functional but utilitarian. Recommendation: trickle in as time permits, do not block Block B for cosmetic A5 improvements.

## 13.4 P4 — Technical Debt / Infrastructure (EXTENDED v6)

[v5 entries 1–10 retained.]

1. **`make state` infrastructure repair** — workaround: manual state entries.
2. **Local test environment repair** — `pip install`, `requirements-dev.txt`, or Docker-only.
3. **`seed.py` UPDATE branch bug** — does not set `is_active=True`.
4. **Decision E logging visibility in Render UI**
5. **Production env vars hardening** — move hardcoded URLs out of committed `.env.production`; full dependency pinning post-launch.
6. **Greek source text editions for RAG corpus**
7. **Nietzsche persona decision** — frontend removed; backend YAML retained for v2.
8. **Runtime template structured-field rendering** — Phase 1-3 fields not in Jinja template; postprocessing catches violations.
9. **Priority hints for overlapping phenomenology mappings**
10. **Render API web service `WEB_CONCURRENCY=1` bottleneck** — upgrade to ~$7/mo recommended.

**NEW v6 entries:**

11. ~~**Vercel parallel deployment disconnect** (URGENT — escalated 2026-05-09)~~ — ✅ **RESOLVED 2026-05-10.** Founder deleted `thinkalike.vercel.app` project via Vercel dashboard.
12. **`/app/dashboard` placeholder page** — auth flow successfully completes but redirects to 404. Plan B path priority #2; under Plan A still blocks UX completion but not launch (built as part of Block H+I work). ~30-60 min.
13. ~~**A4 status verification against `SCREENS_TRACKING_v4`**~~ — ✅ **RESOLVED 2026-05-10.** A4 confirmed as genuinely separate screen; shipped this session.
14. ~~**A6/A7 boundary clarification**~~ — ✅ **RESOLVED 2026-05-10.** Decided as Block A item (combined disclaimer screen); shipped this session.
15. **Database reality verification** — confirm whether Render `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`) is decommissioned, demoted to staging, or still has some role. v5 §1 stated it was the live production DB; reality 2026-05-08/09 shows DATABASE_URL points to Supabase. Either v5 was wrong or undocumented migration occurred.
16. **RLS audit on Supabase tables** (escalated from "consider eventually" to pre-launch blocker) — all 15 public tables currently have RLS DISABLED (was 13; +2 disclaimer tables 2026-05-10 follow same convention). Mitigated by frontend going through FastAPI exclusively, but vulnerable if direct Supabase access from frontend is ever added. Per-table policies needed: users read/write own rows; service-role bypass for backend operations. Test thoroughly — wrong policies break everything.
17. **Brand consolidation pass** (cleanup PR after DNS lands) — replace stale `philosopher.app` strings in code with `thegreatminds.app` or remove FROM_EMAIL hardcoded default; update tab titles, page metadata, OG tags from "Philosopher — Your Reflective Companion" to "Great Minds" branding; align repo name vs domain name vs display name. Do NOT rename repo (too many URLs/CI configs would break).
18. **Migration of `FROM_EMAIL` default in `apps/api/config.py:44`** from `noreply@philosopher.app` to `noreply@thegreatminds.app` once domain is verified. Currently overridden by env var so functionally fine; cleanup only.
19. **Resend domain verification** for `thegreatminds.app` — blocks any production send to non-founder recipient. Dependent on DNS configuration completing first.
20. **DNS configuration for `thegreatminds.app`** — domain registered 2026-05-07; needs A/CNAME records pointing to Netlify, SSL activation, Resend SPF/DKIM/DMARC records. Founder action, ~10-30 min in Netlify dashboard + DNS provider.
21. **Backend GitHub Actions test workflow** — parallel to existing frontend Web build workflow. Run pytest on push/PR.
22. **Endpoint integration tests with mocked Stripe + TestClient** — pre-existing v5 backlog; promotes to higher priority once Stripe is wired post-2026-05-11.
23. **Async email send via arq worker** — currently synchronous in OTP request endpoint; works fine for current load. Move to async if email send latency becomes user-visible. Requires Render Worker (~$7/mo).
24. **Redis race condition in `rate_limit_service.py`** — INCR + EXPIRE not atomic; microsecond window. Very low priority; would only manifest under sustained brute-force attempts.
25. **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** — was true during 14-test session 2026-05-04/05; current state unverified.
26. **Pre-existing untracked files cleanup decision** — `apps/api/scripts/` and `docs/PERSONA_EXPANSION_ROADMAP_v1.md` have been "untracked" through multiple sessions. Decide: gitignore vs commit vs delete.

**NEW v7 entries (2026-05-10 session):**

27. **Stale branch cleanup** — 6 merged branches from 2026-05-10 session, mostly auto-deleted on merge. `fix/a4-mailto-and-card-reframe` from yesterday still lingering. Periodic batch cleanup (every 1-2 weeks) recommended.
28. **gh CLI installation on founder's Windows machine** — `winget install --id GitHub.cli` would eliminate manual GitHub PR opening flow (currently founder copy-pastes title + body into compare URL each time). One-time install reduces friction across all future PRs.
29. **Legal pages `target="_blank"` link hardening** — Auth footers use `target="_blank"` on Terms/Privacy links without `rel="noopener noreferrer"`. Modern browsers default to noopener, but explicit is best practice.
30. **Verify Render `philosopher-db` decommissioning** — carry-forward from v6 reality check. Founder action: check Render dashboard for `philosopher-db` service status.

---

# 14. v2 / Post-MVP Backlog

[§14.1–§14.8 unchanged from v5. Multi-mind features, full insight engine, F5 themes, F4 PDF export, automated data export, push notifications, custom avatars, native app submission.]

---

# 15. Block 9 Frontend Behavior

[§15.1–§15.6 unchanged from v5. J1, J2, J3, J5 routing, retry, state derivation, status bar treatment, forbidden patterns, optional tracking.]

---

# 16. Implementation Rules

## 16.A Operating Discipline (engineering principles)

These principles emerged from Section 5.7 work cycles, Phase 4 stabilization, Block A implementation, and are codified to prevent regression on future work.

1. **Quality-first execution + 3-day soft cap.** Engine-first ≠ engine-forever. UI-forever is the same enemy in different clothes. Each phase has a 3-day soft cap; if work stretches beyond, ship as-is and move on.

2. **Mentor cross-check on design-critical content.** Adversarial review by a different model where stakes warrant. Apply to persona-data work, lexical patterns, prompt content, schema design.

3. **STOP-gate methodology.** INVESTIGATE → PROPOSE → APPROVE → IMPLEMENT → DIFF → APPROVE → COMMIT for any persona-data, schema, or refactor work. No skipping STOP-gates even when in a hurry.

4. **Brain YAML supplements legacy fields, never replaces.** Two-layer defense: prompt-level soft + runtime-level hard.

5. **Production slug authoritative; brain YAML slug descriptive.** Use slug normalization map when slug mismatch exists.

6. **Distinctiveness test for content matching.** When authoring lexical patterns that fire on user input substring (triggers, classifier patterns, regex, forbidden phrases), test: "can I think of 2-3 plausible alternative meanings outside the intended context?". If yes, the pattern fails.

7. **UAT mix mandatory.** Close friends + acquaintances + strangers. Friends-only ≠ market validation.

8. **≥2/5 spontaneous "I'd pay" launch criterion.** Below threshold → iterate before public launch.

**NEW v6 principles (from May 8-9 session):**

9. **Build-time vs request-time Next.js semantics.** When Next.js complains about hooks needing Suspense, do not assume `dynamic = 'force-dynamic'` will suppress the build-time error. Either move forward with Suspense (idiomatic) or refactor the param-reading into a deferred chunk. Trust the error message; do not fight it. Origin: PR #20 deploy preview failed twice before passing — first attempt used `useSearchParams()` directly and failed; second added `dynamic = 'force-dynamic'` and still failed; final fix wrapped in `<Suspense>`.

10. **Stamp + code-change order for alembic plumbing.** When fixing alembic discovery (e.g., moving migration files into `versions/` subdirectory), the order matters: (1) Code change committed and ready to deploy → (2) Stamp `alembic_version` to current head via direct DB tool BEFORE merge → (3) Merge, deploy. Wrong order: stamp first while old code is live → next container restart tries to upgrade from stamped-head to head, fails with `Can't locate revision`, deploy crashes. Origin: hit this exact failure 2026-05-09; recovered by `DELETE FROM alembic_version` + manual redeploy.

11. **Always disconnect parallel deployments before they cause confusion.** When two deployments of the same app exist for any reason (migration, accidentally-attached CI, leftover staging), disconnect the non-canonical one immediately. Cost is ~5 minutes; cost of leaving it is cumulative cognitive friction every PR plus risk of debugging the wrong environment. Origin: Vercel parallel deployment caused live testing confusion 2026-05-09; founder accidentally tested production auth on `thinkalike.vercel.app` instead of `thinkalike.netlify.app` due to browser autocomplete picking the more recently visited domain.

12. **Stakes-aware mentoring requires explicit founder context.** Mentor relationship benefits from explicit stakes signal. If a founder shares their financial/personal stakes context, document it in HANDOFF/STATE so subsequent sessions inherit the right calibration. Mentor recommendations rebalance based on stakes: harder pushback against rabbit holes, more aggressive against feature creep, more willingness to interrupt sequence-following with revenue-blocking concerns. Origin: 2026-05-09 founder revealed Great Minds is built primarily for family income support, not side project. See §17.6.

**NEW v7 principles (from May 10 session):**

13. **Spec word "centered" means BOTH layout-centered AND text-aligned-center.** When a screen spec says "centered" without further qualification, default interpretation is `text-center` class on the inner content container PLUS `mx-auto` for block-level centering. Demonstrated by A4 trouble screen iteration: initial implementation centered the block via `mx-auto` but left text inside left-aligned; founder noted visual still felt off; single-line fix added `text-center`. Pattern: layout centering ≠ text alignment; both are usually expected. Origin: A4 trouble screen iteration 2026-05-10.

14. **Complete PR cycles before queuing new work.** When energy is high and there's a temptation to start the next PR before the current one is open/tested/merged, mentor pushes back. Compound-risk avoidance: 2 PRs in flight without verification means 3× harder debugging if something breaks because we don't know which PR introduced the issue. Discipline cost (~5-10 minutes to close a PR cycle) ≪ debug cost when this fails. Held twice in 2026-05-10 session (post-A6+A7 frontend, post-legal-pages push), prevented messy state both times.

15. **Trust-but-verify CC push outputs via `git ls-remote`.** Failure mode discovered 2026-05-10: Claude Code reported "Branch live on remote" but GitHub UI showed no branch (PR #27 / refs/pull/27/head ghost-branch incident). The cheap (~5 sec) verification step is `git ls-remote origin <branch>` before opening the compare URL. Apply selectively to high-stakes PRs (production blockers, schema migrations, anything where a re-push would be costly). Cross-listed with `HANDOFF_BRIEF` Pattern §C.1.

## 16.B Coding & Scope Rules

1. **This v6 file is the source of truth.** Do not use older backlog files (v4, v5) for priority decisions.
2. **Do not reopen Phase 4 stabilization or Block A work unless a launch test fails.** Closed lists are closed.
3. **Use full diffs, not grep summaries, before claiming a refactor is complete.**
4. **DB migrations require approval before applying.** Schemas in this file are implementation guidance, not automatic migration permission. **Manual SQL through Supabase MCP requires founder approval before each apply** (precedent: 2026-05-09 manual `otp_codes` table creation was approved beforehand).
5. **Test cancellation and payment flows end-to-end.** Highest-risk commercial surface.
6. **Never call Stripe from UI.** Use backend entitlement/state routes.
7. **Founder approval required for:** new env vars, new third-party services, new background jobs, schema changes to existing tables, new paid-plan behavior.
8. **Do not expand scope.** No retention mechanics, billing experiments, notification types, or extra personas unless explicitly approved.
9. **Safety beats persona style.** The deterministic crisis pathway may suppress persona voice; that is acceptable for launch.
10. **Launch validation must include strangers.** Close friends alone are not market validation.
11. **Keep post-launch backlog visible but do not let it block launch.** UI-forever is the same trap as engine-forever.
12. **Greenfield, not refactor (NEW 2026-05-07).** Old screens are deleted, not refactored. Each new screen built fresh on the spec-compliant foundation. Backend integration glue preserved through deletion.
13. **Auth flow is now in production (NEW v6, EXTENDED v7).** Any change to auth-related code (`apps/web/lib/api.ts`, `apps/web/app/auth/*`, `apps/api/services/otp_service.py`, `apps/api/services/email_service.py`, `apps/api/services/rate_limit_service.py`, `apps/api/services/disclaimer_service.py` **(NEW v7)**, `apps/api/routers/disclaimer.py` **(NEW v7)**, `apps/api/db/migrations/versions/*`) must be approved before merge. Auth breakage = zero new users = zero revenue. Disclaimer flow specifically gates first-login UX; breakage there blocks all new-user activation.

---

# 17. Immediate Recommended Next Sequence

**Per founder decision 2026-05-06:** build all 43 specced screens before public launch (Plan A). **2026-05-09 update:** Plan B (minimum-to-revenue interrupt) introduced as alternative for founder consideration given stakes context disclosure (§17.6). Founder decides path at start of next session.

## 17.1 UI Implementation Order — 43 Screens (Plan A path)

**Block A — Authentication (5 screen items) — ✅ 5/5 CLOSED IN PRODUCTION 2026-05-10**
1. ✅ A1 — Splash / loading (PR #15, `ad24d15`)
2. ✅ A2/A3 — Sign up + Sign in (merged single screen) (PR #17, `e2dcf9f`)
3. ✅ A4 — Trouble accessing email (PRs #22, #23, + text-center fix 2026-05-10)
4. ✅ A5 — OTP / Email verification (PR #20; per-digit polish queued P3)
5. ✅ A6+A7 — Combined age + positioning disclaimer (PRs #24 schema, #25 backend, #26 frontend, all 2026-05-10)

**Block B — Onboarding (6 screens) — ⏸ PAUSED awaiting 4 strategic decisions (see §17.7)**
6. 🔴 B1 — Welcome
7. 🔴 B2 — What brings you here?
8. 🔴 B3 — What do you need most?
9. 🔴 B4 — Best matches
10. 🔴 B5 — Persona detail (unlocked / default)
11. 🔴 B6 — Persona detail (Pro-locked variant) — **DEFERRED until Stripe lands**

**Block C — Chat experience (9 screens)**
12. 🔴 C1 — Chat live conversation (some backend live; verify against spec)
13. 🔴 C2 — Chat initial loading
14. 🔴 C3 — Save line confirmation
15. 🔴 C4 — Failed message + retry
16. 🔴 C5 — Daily limit reached (free user)
17. 🔴 C6 — Weak connection / offline (3 sub-states)
18. 🔴 C7 — Safety mode activation
19. 🔴 C8 — First persona greeting
20. 🔴 C9 — Bring another mind flow (2 sub-states)

**Block D — Discovery (3 screens)**
21. 🔴 D1 — Home / Today (2 states)
22. 🔴 D2 — Explore Minds, Carousel/list view
23. 🔴 D3 — Explore Minds, Grid view

**Block F — Reflection (5 screens)**
24. 🔴 F1 — Saved reflections
25. 🔴 F2 — Suggested insights (lite, in-chat)
26. 🔴 F3 — Weekly letter inbox
27. 🔴 F4 — Weekly letter detail
28. 🔴 F6 — Reflection history (UI: "Past conversations")

**Block H — Subscription & Billing (7 screens)**
29. 🔴 H1 — Upgrade / pricing
30. 🔴 H2 — Checkout loading bridge
31. 🔴 H3 — Payment success
32. 🔴 H4 — Payment failed
33. 🔴 H4b — Payment canceled (gentle variant)
34. 🔴 H5 — Subscription management
35. 🔴 H6 — Cancel subscription flow (bottom sheet)

**Block I — Account & Settings (6 screens)**
36. 🔴 I1 — Account hub
37. 🔴 I2 — Notifications
38. 🔴 I3 — Privacy & data
39. 🔴 I4 — Help & support
40. 🔴 I5 — About & legal
41. 🔴 I6 — Logout (bottom sheet)

**Block J — Empty / error states (4 screens)**
42. 🔴 J1 — App-wide server error / 5xx
43. 🔴 J2 — App-wide offline (non-chat shell)
44. 🔴 J3 — Empty saved reflections
45. 🔴 J5 — Empty conversation history

> Note on count: `SCREENS_TRACKING_v4` reports 43 effective specced screens because A2/A3 and A6/A7 are merged screens. The 45 line items above expand the merges for tracking. **8 of 45 line-items closed (A1, A2/A3, A4, A5, A6+A7); 37 remaining if Plan A.** Block A: 5/5 ✅. Next: Block B (paused pending 4 decisions — see §17.7).

## 17.2 Parallel and Post-UI Sequence

While UI is in progress, run in parallel where possible:
- ~~**Vercel disconnect** (NEW v6 priority — urgent ~5 min) — should happen first regardless of plan~~ ✅ **RESOLVED 2026-05-10:** Vercel project deleted, GitHub integration cleanup confirmed. Production canonical is exclusively `thinkalike.netlify.app`.
- **Stripe wiring** (available from 2026-05-11) — can start as soon as Block H screens exist, even in placeholder form.
- **Stripe entitlement + cancellation end-to-end testing** — after Block H + Stripe.
- ~~**Legal copy** — Terms, Privacy Policy, disclaimer copy. Can be drafted during early UI work and finalized before launch.~~ ✅ **TEMPLATES SHIPPED 2026-05-10** via PR #28 (`/legal/terms` v1.0, `/legal/privacy` v1.0) + disclaimer v1.0 seeded in `disclaimer_versions` via PR #24. **Lawyer review still P0** before public launch (Greek consumer law, Stripe billing T&Cs, AI-content liability scope).
- **Email infrastructure verification** — Resend domain verification for `thegreatminds.app` (blocks public launch).
- **DNS configuration for `thegreatminds.app`** — registered 2026-05-07; needs setup.
- **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation review.
- **Brand consolidation pass** — stale `philosopher.app` strings, tab titles, page metadata.

After all UI complete:
- **Production smoke test** per §2.1.A.
- **UAT** with 3-5 mixed testers (close + acquaintances + strangers).
- **Decision gate:** ≥2/5 spontaneous "I'd pay" → public launch (web/PWA only).
- If <2/5 → iterate before public launch.

## 17.3 Estimated Timeline (Plan A)

Per founder decision 2026-05-06, updated 2026-05-09, refined 2026-05-10:

| Phase | Estimate | Status |
|---|---|---|
| Setup PR + Greenfield scaffold | 1 day actual | ✅ DONE 2026-05-07 |
| Block A — Authentication (initial 3/5) | 1.5 days actual (May 8 evening + May 9 overnight) | ✅ DONE 2026-05-09 |
| Block A — A4 + A6/A7 + legal pages closure | ~7 hours sustained session 2026-05-10 | ✅ DONE 2026-05-10 (6 PRs landed) |
| Remaining 37-of-45-screen UI build | 5-9 weeks (revised down — Block A fully closed; legal pages in place; clean foundation) | ⏳ Plan A path |
| Stripe wiring + testing (calendar-gated start 2026-05-11) | 1-2 weeks (parallelizable with UI) | ⏳ |
| Legal review + email + DNS + runbook prep | 1 week (parallelizable with UI; legal templates already shipped) | ⏳ |
| UAT + iteration | 1-2 weeks | ⏳ |
| **Total realistic to first paying user (web/PWA only) under Plan A** | **~9-13 weeks from 2026-05-10** | |

The 2026-05-04 "~6-7 weeks" estimate is superseded. The 2026-05-06 "~12-16 weeks" estimate is revised down by ~3 weeks since Block A is now fully closed and legal templates are live.

**2026-05-10 update:** Plan A confirmed by founder. Plan B remains documented but not actively considered. §17.5 retained for reference.

## 17.4 Sequence Trade-offs (preserved for reference)

The founder explicitly chose Plan A (all 43 before launch) on 2026-05-06 over two alternatives:

- **Plan B** — hybrid: critical subset (16-20 screens) + Stripe + UAT → launch with payment → remaining screens as P1. Estimated ~5-7 weeks to first revenue.
- **Plan C** — 43 screens with parallel UAT prep on partial cohorts during UI work. Estimated ~10-13 weeks.

These alternatives are documented so that if circumstances change (timeline pressure, runway concerns, signal from early testers), the founder can pivot without re-litigating the decision from scratch.

**2026-05-09 stakes context disclosure (§17.6) re-introduces Plan B for founder consideration** — see §17.5 for current Plan A vs Plan B fork.

## 17.5 Plan A vs Plan B Fork (NEW v6)

Founder must decide path at start of next session. Both legitimate; mentor stated preference but founder calls.

### Plan A — Continue 43-screen sequence (founder's 2026-05-06 decision)

Next item: Block B — Onboarding (B1–B6). Build screens in spec order. ~10-14 weeks to first paying user.

### Plan B — Minimum-to-revenue interrupt (mentor recommended given §17.6)

Pause 43-screen sequence to ship the minimum viable monetization path:

1. **Vercel disconnect** (urgent prerequisite, ~5 min)
2. **`/app/dashboard` placeholder page** (~30-60 min) — unblocks the post-auth redirect that currently 404s. Implementation: 'use client' page reading user from store, displaying "Hello, {name}" + Sign Out button calling `clearAuth()` + `setToken(null)` + redirect to `/auth`.
3. **One persona conversation experience (existing engine + minimal C-block screen)** — proves product. Backend chat is already live (50 conversations + 139 messages in DB from earlier testing); needs minimal UI.
4. **Free-tier limit + paywall trigger** — backend logic + minimal H1/H4 UI.
5. **Stripe Checkout + webhook handler** — calendar-gated to 2026-05-11.
6. **Soft launch** — 5-10 users from founder's network. Can they pay? Do they want to? Iterate from real signal.
7. **Return to remaining Block B/D/F/H/I/J screens** armed with paying-user feedback.

Estimated total: ~4-6 weeks to first paid user under Plan B.

### Why mentor recommends Plan B given §17.6

- Family income context raises cost of long timelines
- 43 screens before any paying user = 12-16 weeks of zero validation
- Building 30+ retention screens (memory inspector, ritual library, settings tabs, multi-persona switcher, analytics) before knowing if anyone pays is anti-pattern: many of those screens may be wrong for what real users want
- Plan A is defensible for hobby project; harder to defend with financial stakes
- Trade-off alternatives explicitly preserved per §16.A.12 reversibility — pivoting to Plan B does not invalidate prior decision, just reframes timing

**Founder's call. Mentor will support either.** Update `HANDOFF_BRIEF_v6.md` §21 and `PROJECT_STATE_v6.md` §10 with the chosen path before starting work.

## 17.6 Stakes Context (NEW v6)

On 2026-05-09 founder shared that Great Minds is being built primarily to support family income. This is documented here so all subsequent sessions inherit the calibration:

- **Long timelines have higher cost than usual.** 12-16 weeks of zero validation has different weight when income depends on outcome.
- **Feature creep is not just a craft concern — it's a runway concern.**
- **Mentor will push back harder on rabbit holes, perfectionism, and "let me also build X while I'm here" patterns.**
- **Mentor will not soften the message.** False politeness costs time the founder does not have.
- **Mentor will respect founder's call.** The 2026-05-06 43-screen decision stands until founder reverses it. Mentor recommends Plan B but will execute Plan A faithfully if founder confirms.
- **Mentor recognizes that founder is non-developer-technical.** This shapes how prompts to Claude Code are structured and how diffs are reviewed.

If a future session encounters this context for the first time, weight time-to-revenue heavily in trade-off discussions. If circumstances change (founder secures runway from elsewhere, takes contract work, etc.), update this section to reflect new constraints.

## 17.7 Block B Onboarding Planning (NEW v7 — 2026-05-10)

Block A 5/5 closed. Block B is next in Plan A sequence. **Planning paused awaiting 4 strategic decisions from founder.** Once decisions are confirmed, work resumes immediately.

### 17.7.1 Block B scope (from `SCREENS_TRACKING_v4`)

| Item | Screen | Notes |
|---|---|---|
| B1 | Welcome | Intro screen, simple |
| B2 | "What brings you here?" | Form (depends on B1) |
| B3 | "What do you need most?" | Form (depends on B2) |
| B4 | Best matches | Persona match output |
| B5 | Persona detail (default) | Data fetch from existing personas table |
| B6 | Persona detail (Pro-locked variant) | **DEFERRED until Stripe lands** |

### 17.7.2 Four pending strategic decisions

**Decision 1: B2/B3 answer persistence**
- *Options:* (a) frontend-only state (Zustand transient); (b) backend persistence to new `user_preferences` table
- *Mentor recommendation:* **Backend persistence** + reactive Zustand store
- *Trade-off:* Backend persistence enables retention/segmentation analytics — vital for the monetization signal capture that §17.6 stakes context demands. Frontend-only is simpler but throws away exactly the data that would tell us why users do/don't convert.

**Decision 2: Matching algorithm location**
- *Options:* (a) frontend-computed (rules in client); (b) backend-computed (POST /matches endpoint)
- *Mentor recommendation:* **Backend-computed**
- *Trade-off:* Centralized logic, easier iteration without redeploy, can leverage non-exposed persona traits/weights for matching, allows A/B testing matching strategies post-launch. Frontend approach leaks tuning details to anyone reading bundled JS.

**Decision 3: B6 (Pro-locked variant) timing**
- *Options:* (a) build now alongside B5; (b) defer until Stripe block
- *Mentor recommendation:* **DEFER until Stripe lands**
- *Trade-off:* Building paywall UI before payment infra exists is anti-monetization — if pricing model shifts (it likely will after first UAT signal), the Pro-locked variant gets rebuilt. Avoid wasted work. Aligns with §17.6 stakes calibration.

**Decision 4: `user_preferences` schema shape**
- *Options:* (a) wide table (1 row per user, columns per question); (b) narrow EAV (1 row per answer)
- *Mentor recommendation:* **Wide table**
- *Trade-off:* Simpler v1, easier query patterns, fast indexing. Refactor to EAV later if 5+ questions added or schema becomes dynamic. Pre-mature flexibility for hypothetical future needs is a §17.6 anti-pattern.

### 17.7.3 Estimated work after decisions confirmed

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

### 17.7.4 Sequencing recommendation

Open the 4 decisions at the start of the next session. Once confirmed, sequence:
1. Schema migration first (alembic 004) — unblocks B2/B3 persistence
2. Backend endpoint — completes data plumbing
3. B1 → B2 → B3 in order (each its own PR; PR cycle discipline per §16.A.14)
4. B4 (matching) — separate PR with backend service
5. B5 (persona detail) — separate PR

Each step verifies on production before next step. Estimated 2-3 focused sessions to close Block B excluding B6.

---

**End of Implementation Backlog v7.** Authoritative as of 2026-05-10 session close. Replaces both `IMPLEMENTATION_BACKLOG_v6.md` and `IMPLEMENTATION_BACKLOG_v6_ADDENDUM_2026_05_10.md`.
