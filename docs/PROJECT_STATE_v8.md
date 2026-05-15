# PHILOSOPHER — Project State v8

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v8 = v7 baseline (2026-05-10) + 2026-05-11 addendum (design system v4→v5) + 2026-05-13 session deltas (Block B onboarding spine, 9 personas, mobile walkthrough findings).**
>
> **Last updated:** 2026-05-14 (v8 consolidation — Block B 6/6 functional spine SHIPPED; 9 personas live; polish PR pending for visual/QA closure)

> **Correction note (2026-05-14):** This copy includes a consistency pass against v7/v7 addendum and companion v8 docs. It fixes closure wording, clarifies code-vs-DNS dependencies, softens unverified table-count assumptions, and preserves launch-risk items from v7.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 async · asyncpg |
| Database | PostgreSQL 17 (Supabase, eu-west-1, paid) |
| Queue/Cache | Redis (Upstash) + ARQ + APScheduler |
| LLM | Anthropic Claude (not yet wired for chat — Block C work) |
| Embeddings | OpenAI text-embedding-3-small (not yet wired) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage |
| Billing | Stripe (scaffolded, NOT wired) |
| Email | Resend (free tier, test sender — custom domain in progress) |
| Analytics | PostHog (configured, unused) |

### Hosting

- **Frontend (canonical):** Netlify (project: thinkalike, URL: thinkalike.netlify.app). Auto-deploys from main.
- ~~Frontend (legacy): Vercel~~ — **DISCONNECTED 2026-05-10**
- **Backend:** Render (free tier — `WEB_CONCURRENCY=1`, 15-min idle cold-start, mitigated by external ping bot; upgrade decision pending ~$7/mo)
- **Database:** Supabase project `plecolxlzshkfvybszgs` (eu-west-1, paid). DATABASE_URL points to `aws-0-eu-west-1.pooler.supabase.com:5432`. Direct asyncpg connection — NOT Supabase Data API (so the May 30 2026 Data API default change does NOT affect this project).
- **Cache (Redis):** Upstash `philosopher-prod` (eu-west-1, free tier). REDIS_URL set; ARQ + APScheduler operational. Rate limiter verified working 2026-05-10 (5 req / 6 min ceiling → 429).
- **Email (Resend):** RESEND_API_KEY + FROM_EMAIL set. Currently `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain `thegreatminds.app` DNS setup IN PROGRESS at session end.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-13 (hotfix PR #44 — migration 006 surrogate emoji fix, commit `cd76999`)**
- **Has paying users:** No
- **Has free trial users:** No

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Flow: passwordless OTP-first.

| Step | Status |
|---|---|
| `/auth` (email entry) | ✅ |
| POST `/api/v1/auth/otp/request` → 202 | ✅ |
| Rate limiter (5/6min → 429) | ✅ verified |
| Email delivery (test sender) | ✅ |
| `/auth/verify` (6-digit code) | ✅ |
| POST `/api/v1/auth/otp/verify` → 200 (JWT) | ✅ |
| Token persistence (localStorage + cookie 7d) | ✅ |
| Conditional disclaimer routing | ✅ |
| POST `/api/v1/disclaimer/accept` → 200 | ✅ |
| Acceptance row written with audit fields | ✅ |
| Redirect to `/app/welcome` | ✅ NEW 2026-05-13 |

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional)

| Screen | Route | Status |
|---|---|---|
| B1 — Welcome (Mind of the day) | `/app/welcome` | 🟡 shipped; portrait + hero text issues in polish PR |
| B2 — Themes selection | `/app/onboarding/themes` | ✅ |
| B3 — Need most | `/app/onboarding/need` | ✅ |
| B4 — Best matches (top-3) | `/app/onboarding/matches` | 🟡 shipped; portrait thumbnails not loading |
| B5 — Persona detail (free) | `/app/persona/[slug]` | 🟡 shipped; header portrait not loading |
| B6 — Persona detail (Pro-locked) | `/app/persona/[slug]` | 🟡 shipped; paywall via `alert()` until Stripe |

**"Begin conversation" CTA from B5/B6** → 404 by design until Block C ships.

### Block B visual closure status

**NOT closed.** Consolidated polish PR pending to fix 9 mobile walkthrough findings (3 critical, 2 important, 4 polish). Block B is **functionally complete, visually pending verification on real mobile devices.**

### Other systems

- **Stripe wired:** No (calendar gate of 2026-05-11 passed; verify status before Block H work)
- **User validation done:** No (UAT planned with ≥2/5 spontaneous "I'd pay" criterion after 43-screen build — Plan A path active)
- **`PHENOMENOLOGY_BRIDGE_ENABLED` flag:** Verified active 2026-05-04/05; current state in Render env to confirm before launch
- **API plan upgrade:** Free tier still. Decision pending.
- **Database:** Paid tier. RLS disabled on all 17 public tables. **Mitigation: frontend exclusively goes through FastAPI; anon key NOT in frontend bundle. If a future change ever adds Supabase anon key to frontend, RLS becomes critical vulnerability immediately.**

### 2026-05-13 production verification snapshot

```
alembic_version:        006_add_new_personas ✓
public tables:          17 (was 15; added user_preferences from migration 004,
                            plus disclaimer_versions + disclaimer_acceptances from 003)
users count:            2 (founder, freetester)
personas count:         9 (was 6; Lao Tzu, Wilde, Machiavelli added; Jung activated)
disclaimer_versions:    1 (v1.0 seed)
disclaimer_acceptances: 1 (founder's, 2026-05-10)
user_preferences rows:  1 (test account)
conversations:          50 (from prior engine sessions)
messages:               139 (from prior engine sessions)
```

### Auth + onboarding pipeline — end-to-end verified

```
1.  /auth                                          ✓
2.  POST /api/v1/auth/otp/request   →  202         ✓
2a. Rate limiter (5/6min)          →  429          ✓
3.  Email delivered (test sender)                  ✓
4.  /auth/verify?email=<encoded>                   ✓
5.  POST /api/v1/auth/otp/verify    →  200 + JWT   ✓
6.  Token persisted                                ✓
7.  Conditional → /auth/disclaimer (if needed)     ✓
8.  POST /api/v1/disclaimer/accept  →  200         ✓
9.  Redirect to /app/welcome                       ✓
10. B1 → B2 → B3 → B4 → B5/B6                      ✓
11. "Begin conversation" CTA       →  404          ❌ EXPECTED until Block C
```

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.**

| Slug | Tier | YAML in `philosopher_brain/` | DB `config` JSONB | `is_active` | Notes |
|---|---|---|---|---|---|
| marcus_aurelius | free | ✅ | ✅ | ✅ | Phases 1-3 + Phase 4 essence-only (Marcus shading PR Β P3 post-launch) |
| socrates | free | ✅ | ✅ | ✅ | Phases 1-4 |
| simone_de_beauvoir | pro | ✅ | ✅ | ✅ | Phases 1-4 |
| epictetus | pro | ✅ | ✅ | ✅ | Phases 1-4 |
| sigmund_freud | pro | ✅ | ✅ | ✅ | Phases 1-4. Originally planned as premium; tier currently `pro`. Schema supports premium, no personas assigned. 1-line UPDATE if reassignment desired. |
| carl_jung | pro | ✅ | ✅ | ✅ | Was in DB pre-session but excluded from matching (no bio + portrait). Activated PR #43. |
| **lao_tzu** | **free** | ❌ (in JSONB only) | ✅ | ✅ | NEW 2026-05-13 PR #43. Config authored by Claude assistant in session. |
| **oscar_wilde** | **pro** | ❌ (in JSONB only) | ✅ | ✅ | NEW 2026-05-13 PR #43. |
| **niccolo_machiavelli** | **pro** | ❌ (in JSONB only) | ✅ | ✅ | NEW 2026-05-13 PR #43. Hotfix PR #44 fixed UTF-16 surrogate emoji encoding. |

**Removed from frontend (preserved backend):**
- nietzsche — backend YAML kept; not in `is_active` rotation

### Persona content gaps

- **3 new personas not in `philosopher_brain/` YAML repo path** — currently live only as JSONB in `personas.config`. Consider extracting to YAML (`lao_tzu.yaml`, `oscar_wilde.yaml`, `niccolo_machiavelli.yaml`) for source-parity with original 6. P2.
- **ChatGPT audit of new persona configs pending** — founder will run audit and request surgical UPDATE edits via JSONB `jsonb_set`. P2.
- **Portrait style harmonization** — Aurelius + Socrates are painterly outliers vs the 7 atmospheric/hybrid others. Re-generate Aurelius + Socrates in matching style. P2.

### Affinity weight signatures (apps/api/services/matching_service.py)

`PERSONA_AFFINITIES` dict, scale 0-3 across themes + needs dimensions:

- **Lao Tzu** → anxiety/acceptance + need=comfort (sage of yielding)
- **Wilde** → balanced, surfaces for relationships theme or undifferentiated needs
- **Machiavelli** → work/purpose + need=challenge or practical_steadiness (zero comfort weight — deliberate)
- **Jung** → relationships/purpose + need=interpretation
- **Aurelius, Socrates, Beauvoir, Epictetus, Freud** — affinity weights documented in matching_service.py

`EXCLUDED_SLUGS: set[str] = set()` (Carl Jung removed from exclusion in PR #43; no current exclusions)

---

## 4. Database schema

### Tables (17 public reported — verify exact count before RLS work)

```
users
sessions
otp_codes               (NEW 2026-05-08, migration 002)
disclaimer_versions     (NEW 2026-05-10, migration 003)
disclaimer_acceptances  (NEW 2026-05-10, migration 003)
user_preferences        (NEW 2026-05-13, migration 004)
personas                (existing — now has bio + portrait_url via migration 005)
conversations           (existing from prior engine work)
messages                (existing from prior engine work)
... plus other engine tables (memories, insights, themes, summaries, etc.). v8 documents report 17 public tables; verify exact table list/count via Supabase before RLS implementation because migrations 005/006 did not add tables.
```

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001 | initial | Pre-Block-A | — |
| 002 | otp_codes table | 2026-05-09 | #18 |
| 003 | disclaimer_versions + disclaimer_acceptances + v1.0 seed | 2026-05-10 | #24 |
| 004 | user_preferences (wide table) | 2026-05-13 | #33 |
| 005 | personas.bio + personas.portrait_url | 2026-05-13 | #42 |
| 006 | 3 new personas + Jung bio/portrait update | 2026-05-13 | #43 + #44 hotfix |

**alembic auto-runs `upgrade head` on Render container startup.** Mechanism is undocumented (worth finding — Procfile? Dockerfile CMD? render.yaml?). P2 backlog item.

### RLS state

**RLS DISABLED on public tables.** v8 documents report 17 public tables; verify exact list/count via Supabase before implementing RLS policies. Current mitigation: frontend goes exclusively through the FastAPI gateway and no Supabase anon key is present in the frontend bundle.

⚠️ **Forward-looking warning:** if a future change ever introduces Supabase anon key on the frontend (e.g., for a "quick" Supabase realtime feature, or direct client query from React), RLS becomes a critical vulnerability the moment that ships. Always add explicit RLS policies BEFORE that change is merged.

---

## 5. Backend endpoints (selected — see `apps/api/routers/`)

```
POST /api/v1/auth/register             (legacy — passwordless flow preferred)
POST /api/v1/auth/login                (legacy — passwordless flow preferred)
GET  /api/v1/auth/me                   (auth)
POST /api/v1/auth/otp/request          (public, rate-limited)
POST /api/v1/auth/otp/verify           (public)

GET  /api/v1/disclaimer/current        (public)
POST /api/v1/disclaimer/accept         (auth)

GET  /api/v1/personas                  (public — returns all 9 active personas)

GET  /api/v1/preferences               (auth — returns user's saved preferences or 404)
POST /api/v1/preferences               (auth — save/update themes + need_most)
GET  /api/v1/preferences/matches       (auth — returns top-3 matched personas)

GET  /health                           (public)
```

---

## 6. Known bugs (active P0/P1 — from 2026-05-13 mobile walkthrough)

| ID | Description | Severity | Owner | Notes |
|---|---|---|---|---|
| BUG-001 | Portraits not loading anywhere (welcome, matches, persona detail) | 🔴 Critical | Polish PR | Suspected PR #42 refactor broke portrait_url flow from backend |
| BUG-002 | OTP email fails for `@ote.gr` domain | 🔴 Critical | Polish PR + DNS | Resolves when DNS done + Resend custom domain active |
| BUG-003 | Refresh on welcome error page → redirect to disclaimer | 🟡 Important | Polish PR | Should retry instead of redirect |
| BUG-004 | Hero text on B1 partially unreadable, sits on persona face | 🟡 Important | Polish PR | V2 style: white + shadow + dark gradient, regular weight serif, wider layout |
| BUG-005 | "Explore Minds" button cropped by iOS Safari toolbar | 🟡 Important | Polish PR | `safe-area-inset-bottom` |
| BUG-006 | No bounce-back scroll on iOS | 🟢 Polish | Polish PR | `overscroll-behavior` + native rubber-band |
| BUG-007 | Push buttons lack press feedback | 🟢 Polish | Polish PR | CSS `:active` scale-down 0.97x |
| BUG-008 | OTP input is single field, should be 6 separate boxes | 🟢 Polish | Polish PR | Carries Block A backlog item (A5 polish) |
| BUG-009 | Email sender display name "Philosopher" → "Great Minds" | 🟢 Polish | Polish PR + Resend dashboard | Depends on custom domain + Resend settings |

**Polish PR should address the code/UI parts of all 9 findings.** BUG-002 + BUG-009 also depend on DNS/Resend domain verification and dashboard/env configuration, so they are not code-only fixes.

---

## 7. Test credentials

- **Email:** `freetester@gmail.com`
- **Password:** none for current UX — actual flow uses OTP. Legacy password endpoints exist but are not the preferred user-facing flow.
- **Saved preferences:** Yes, from test session
- **For fresh-user testing:** create new account

---

## 8. Environment variables (Render backend)

```
DATABASE_URL                  (Supabase pooler)
REDIS_URL                     (Upstash)
RESEND_API_KEY                (set)
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>"
                              (test sender — switch to thegreatminds.app post-DNS)
JWT_SECRET                    (set)
PHENOMENOLOGY_BRIDGE_ENABLED  (was true 2026-05-04/05; current state unverified)
```

### Environment variables (Netlify frontend)

```
NEXT_PUBLIC_API_URL                (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL          nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_TERMS_URL              (unset; hardcoded fallback to /legal/terms)
NEXT_PUBLIC_PRIVACY_URL            (unset; hardcoded fallback to /legal/privacy)
```

---

## 9. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **Consolidated polish PR** (blocks Block B visual closure) — 9 mobile walkthrough findings
- [ ] **Lawyer review of legal templates** — Terms v1.0, Privacy v1.0, disclaimer v1.0 — Greek consumer law, Stripe billing T&Cs, AI-content liability
- [ ] **Resend domain verification** for `thegreatminds.app` — IN PROGRESS (depends on DNS)
- [ ] **DNS configuration** for `thegreatminds.app` — IN PROGRESS this session
- [ ] **Stripe wiring** (calendar gate 2026-05-11 passed; verify status)
- [ ] **GDPR/DPA infrastructure** — LLM provider DPA review when Block C lands, processors table, data subject request fulfillment workflow
- [ ] **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** in Render env vars before launch

### Open items (P1)

- [ ] **Block C planning** — 6 architectural decisions to resolve (LLM provider, RAG, memory, limits, streaming, safety filter cadence) — see HANDOFF_BRIEF_v8.md §24.3
- [ ] **A6+A7 disclaimer endpoint integration tests** (shipped without tests for speed)
- [ ] **A6+A7 lazy-load monitoring** (watch for `MissingGreenlet` in Render logs)
- [ ] **A4 mailto visible support email fallback** (when real mailbox exists)

### Open items (P2)

- [ ] **ChatGPT audit of new persona configs** → surgical JSONB UPDATE edits (founder-owned)
- [ ] **Portrait style harmonization** — Aurelius + Socrates re-generate to match the 7 others
- [ ] **Extract Lao Tzu / Wilde / Machiavelli configs to YAML** in `apps/api/philosopher_brain/` for source-parity
- [ ] **Premium tier reassignment** — Freud → premium if desired (1-line UPDATE)
- [ ] **B1 hydration polish** — 0.5s flash before auth-guard redirect
- [ ] **Document Render alembic auto-run mechanism** — currently undocumented
- [ ] **Local Python venv for founder** — would prevent another emoji surrogate disaster

### Open items (P3)

- [ ] **Desktop layout polish** — mobile-first design looks broken on wide screens
- [ ] **Phase 5 register architecture + UI chips + classifier** — post-feedback
- [ ] **A5 polish** (per-digit OTP boxes — overlaps with polish PR scope)

### Open items (P4)

- [ ] **Render `philosopher-db` decommissioning verification** — carry-forward from v6. Old Render PostgreSQL was upgraded to paid tier 2026-05-06 per v5 §2 but reality has Supabase as the live DB. Verify whether old Render DB is dormant/deleted/stale. If still costing money, decommission.
- [ ] **`apps/api/scripts/` decision** — gitignore, commit, or delete
- [ ] **Stale branch cleanup** — periodic batch every 1-2 weeks
- [ ] **gh CLI install on founder's Windows** — `winget install --id GitHub.cli`
- [ ] **Legal pages `target="_blank"` rel hardening** — explicit noopener noreferrer
- [ ] **Untracked v6 docs cleanup** — `docs/HANDOFF_BRIEF_v6.md`, etc. on disk (commit as historical or delete since superseded by v7→v8)

### Closed items (recent — through 2026-05-13)

- [x] **CLOSED 2026-05-13** — **Block B 6/6 functional spine shipped.** 11 PRs + 1 hotfix in single session. 9 personas live.
- [x] **CLOSED 2026-05-13** — **4 Block B strategic decisions** resolved (backend persistence + matching, B6 built now, wide-table schema)
- [x] **CLOSED 2026-05-13** — **Migration 004 (user_preferences)**, migration 005 (personas bio+portrait), migration 006 (3 new personas + Jung activation) all applied successfully
- [x] **CLOSED 2026-05-13** — **Production deploy incident (PR #44 hotfix)** recovered cleanly with zero data corruption
- [x] **CLOSED 2026-05-11** — **Design System v4→v5 palette migration** + Block A token backfill + spec docs committed to repo
- [x] **CLOSED 2026-05-10** — Block A 5/5 (A1, A2/A3, A4, A5, A6+A7) end-to-end verified with real production acceptance row
- [x] **CLOSED 2026-05-10** — Vercel project disconnect; Plan A confirmation; Legal pages templates live; A4 status verification; A6/A7 boundary clarification
- [x] **CLOSED 2026-05-10** — OTP rate limiter VERIFIED working in production (5/6min → 429)
- [x] **CLOSED 2026-05-09** — Block A frontend (A5); alembic plumbing (versions/ subdirectory)
- [x] **CLOSED 2026-05-08** — Backend OTP infrastructure; Resend; Upstash Redis; ARQ background tasks unsilenced
- [x] **CLOSED 2026-05-07** — Greenfield rewrite; Netlify hosting confirmed
- [x] **CLOSED 2026-05-05** — Phase 4 stabilization sequence (8 items)

---

## 10. Manual — Live URLs

- Repo: https://github.com/Nckoutras/Philosopher
- **Frontend live (canonical):** https://thinkalike.netlify.app
- Frontend planned domain: https://thegreatminds.app (DNS + SSL IN PROGRESS — registered 2026-05-07)
- Backend live: https://philosopher-api-z9l9.onrender.com
- Backend health: https://philosopher-api-z9l9.onrender.com/health
- **Netlify project:** https://app.netlify.com/sites/thinkalike
- Render API service: https://dashboard.render.com (philosopher-api, Service ID `srv-d7ijct6gvqtc739a0pdg`)
- **Production database:** Supabase https://supabase.com/dashboard/project/plecolxlzshkfvybszgs (eu-west-1, paid)
- ~~Render PostgreSQL `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`)~~ — **STATUS UNCERTAIN** (carry-forward from v6/v7). v5 listed as production DB. Reality has Supabase live. Verify decommissioning. If still costing money, retire.
- **Upstash Redis:** https://console.upstash.com/redis (database `philosopher-prod`)
- **Resend:** https://resend.com (account `nckoutras@gmail.com`; domain verification for `thegreatminds.app` IN PROGRESS)

---

## 11. Key file paths (production codebase)

### Backend (apps/api/)
- `main.py` — FastAPI app + router mounting
- `models/__init__.py` — all SQLAlchemy ORM models (flat, single file)
- `schemas/__init__.py` — all Pydantic schemas (flat, single file)
- `routers/` — `auth.py`, `disclaimer.py`, `personas.py`, `preferences.py`
- `services/` — `otp_service.py`, `disclaimer_service.py`, `matching_service.py`, `rate_limit_service.py`, `email_service.py`
- `db/migrations/versions/` — alembic migrations (001-006)
- `db/session.py:22-31` — `get_db()` dependency
- `auth.py:41-50` — `get_current_user` dependency
- `philosopher_brain/` — Section 5.7 brain content (6 persona YAMLs + phenomenology + forbidden lexicons + prompts)
- `scripts/` — manual test scripts (currently untracked, decision pending)

### Frontend (apps/web/)
- `lib/api.ts` — ApiClient singleton + Persona/Match/Preference interfaces
- `lib/store.ts` — Zustand auth store
- `app/auth/` — login, OTP, disclaimer flow
- `app/app/welcome/page.tsx` — B1
- `app/app/onboarding/themes/page.tsx` — B2
- `app/app/onboarding/need/page.tsx` — B3
- `app/app/onboarding/matches/page.tsx` — B4
- `app/app/persona/[slug]/page.tsx` — B5/B6
- `components/ui/BronzeDivider.tsx` — reusable divider
- `public/personas/` — 9 portrait files (5 jpg/webp + 4 png)
- `tailwind.config.js` — Design System v5 palette

### Docs (founder's local `docs/` folder + Claude.ai project knowledge)
- `HANDOFF_BRIEF_v8.md` — handoff (NEW — supersedes v7)
- `PROJECT_STATE_v8.md` — THIS file (NEW — supersedes v7 + addendum)
- `IMPLEMENTATION_BACKLOG_v8.md` — backlog (NEW — supersedes v7)
- `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` — design spec (in repo since 2026-05-11)
- `SCREENS_TRACKING_v4.md` — needs v5 update post-polish PR
- `USER_FLOW_v4.md`

---

## 12. Note: KIEN is a SEPARATE project

Founder also runs **KIEN** — an AI companion SaaS — as a separate codebase and product. Not to be confused with Philosopher / Great Minds.

For KIEN context (Supabase Data API May 30 deadline, n8n workflow updates, Stripe pricing tiers, narrative endings for personas Amber/Rei), see KIEN-specific session memories.

This v8 doc is **Philosopher-only**. Any references to "the project" mean Philosopher.

---

**End of PROJECT_STATE v8.** Authoritative as of 2026-05-13/14 session close. Supersedes `PROJECT_STATE_v7.md` + `PROJECT_STATE_v7_ADDENDUM_2026_05_11.md`.
