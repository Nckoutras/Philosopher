# PHILOSOPHER — Project State v11

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v11 = v9 baseline (2026-05-20) + 2026-05-21-24 session delta (PR4j paywall-audit; PR4l alembic hotfix; PR4m FK ondelete hotfix; PR4k Google OAuth dormant; PR4n Share v2 modal; PR4o Rituals tab + page; PR4p hotfix api import + hydration guard (P1 BROKE production); PR4q empty commit; PR4r actual rollback in flight).** *(No v10 was produced — docs jumped v9 → v11 to absorb two full sessions in one rotation.)*
>
> **Generated:** 2026-05-24 (v11 rotation)
>
> **Last updated:** 2026-05-24

> **v11 conflict resolution rule:** Where v11 conflicts with v9, v11 wins. Production reality always wins over docs.

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
| LLM | Anthropic Claude — wired and live for chat |
| Embeddings | OpenAI text-embedding-3-small (2476 chunks live across 7 personas) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage; Google OAuth dormant (PR4k) |
| Billing | Stripe (sandbox — checkout + portal + webhook live; PR1 #77) |
| Email | Resend (free tier, test sender — custom domain in progress) |
| Analytics | PostHog (configured, unused) |

### Hosting

- **Frontend (canonical):** Netlify (project: thinkalike, URL: thinkalike.netlify.app). Auto-deploys from main.
- ~~Frontend (legacy): Vercel~~ — **DISCONNECTED 2026-05-10**
- **Backend:** Render (free tier — `WEB_CONCURRENCY=1`, 15-min idle cold-start, mitigated by external ping bot; upgrade decision pending ~$7/mo)
- **Database:** Supabase project `plecolxlzshkfvybszgs` (eu-west-1, paid). DATABASE_URL points to `aws-0-eu-west-1.pooler.supabase.com:5432`. Direct asyncpg connection — NOT Supabase Data API.
- **Cache (Redis):** Upstash `philosopher-prod` (eu-west-1, free tier). REDIS_URL set; ARQ + APScheduler operational.
- **Email (Resend):** RESEND_API_KEY + FROM_EMAIL set. Currently `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain `thegreatminds.app` DNS setup IN PROGRESS.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-24** — PR4r actual-rollback (reverts hydration guard from PR4p while keeping api import fix) on branch feat/pr4r-actual-rollback-hydration (in flight as of 2026-05-24 docs rotation).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3-5 fresh users still pending)

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v9. See v9/v8 for detail.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v9. Visual closure still pending consolidated polish PR.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

Unchanged from v9. All features live in PATH A SSE streaming endpoint.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; €14.90/mo + €149/yr; PR1 #77)
- **BETA bypass active:** Yes — `BETA_GRANT_PRO_TO_ALL=true` in Render env (PR4j). All users treated as Pro during cold beta.
- **Paywall system wired:** Yes — `/api/v1/subscription` synthetic endpoint live (PR4j); `SubscriptionBootstrap` frontend wiring live (PR4j)
- **Google OAuth:** Dormant — routes live in code but `GOOGLE_OAUTH_ENABLED=false` (PR4k). Not user-visible.
- **Rituals tab:** Live (PR4o) — tab bar swapped Reflections → Rituals; `/app/rituals` page with 4 cards (Letter to my Future Self functional, 3 locked)
- **Share v2:** Live (PR4n) — SharePreviewModal with annotation overlay, dynamic font sizing, emoji strip

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v9.

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001 | initial | Pre-Block-A | — |
| 002 | otp_codes table | 2026-05-09 | #18 |
| 003 | disclaimer_versions + disclaimer_acceptances + v1.0 seed | 2026-05-10 | #24 |
| 004 | user_preferences (wide table) | 2026-05-13 | #33 |
| 005 | personas.bio + personas.portrait_url | 2026-05-13 | #42 |
| 006 | 3 new personas + Jung bio/portrait update | 2026-05-13 | #43 + #44 hotfix |
| 007 | Block C schema: conversations.deleted_at, messages.model_used, daily_usage table | 2026-05-16 | #50 |
| 008 | HNSW vector indexes + source_chunks.chunk_index column | 2026-05-17 | C3a |
| 009 | saved_lines table | 2026-05-17 | #68 |
| 010 | daily_questions table + 30 seed prompts | 2026-05-18 | #76 |
| 011 | conversations.source_saved_line_id + source_persona_slug | 2026-05-20 | #78 |
| **012** | **scheduled_emails table (send-to-future-self ritual)** | **2026-05-21** | **PR4o** |
| **013** | **FK ondelete clauses: memory_entries CASCADE, insights CASCADE, safety_events SET NULL, user_ritual_completions SET NULL** | **2026-05-22** | **PR4m / #99** |
| **014** | **user_oauth_cols: auth_provider varchar(20) + oauth_provider_id text + index** | **2026-05-23** | **PR4k / #101** |

**alembic_version = `014_user_oauth_columns`** (as of 2026-05-24)

### New table added in migration 012

```
scheduled_emails        (NEW 2026-05-21, migration 012)
                        powers "Send to my future self" ritual (Letter to my Future Self)
                        id: UUID PK DEFAULT gen_random_uuid()
                        user_id FK→users ON DELETE CASCADE
                        saved_line_id FK→saved_lines ON DELETE SET NULL (nullable)
                        persona_id FK→personas ON DELETE RESTRICT
                        note: TEXT (nullable — user's optional message to future self)
                        recipient_email: VARCHAR(320) NOT NULL
                        scheduled_for: TIMESTAMP WITH TIME ZONE NOT NULL
                        status: VARCHAR(16) NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','sent','failed','cancelled'))
                        sent_at: TIMESTAMP WITH TIME ZONE (nullable)
                        failure_reason: TEXT (nullable)
                        created_at: TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                        updated_at: TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                        Index ix_scheduled_emails_pending: (scheduled_for) WHERE status = 'pending'
```

### FK ondelete clauses added in migration 013

Migration 013 (`013_add_ondelete_conversation_fks`) adds proper `ON DELETE` cascade semantics
to existing FK constraints that previously had no action (silent orphan risk):

```
memory_entries.*       → ON DELETE CASCADE (when conversation or user deleted)
insights.*             → ON DELETE CASCADE (when conversation or user deleted)
safety_events.*        → ON DELETE SET NULL (preserve audit trail; null out FK)
user_ritual_completions.* → ON DELETE SET NULL (preserve history; null out FK)
```

### New columns added in migration 014

```
users.auth_provider        VARCHAR(20) DEFAULT 'otp'
                            'otp' for existing users, 'google' for OAuth users
                            Populated retroactively for all existing rows (PR4k)

users.oauth_provider_id    TEXT, nullable
                            Google sub claim for OAuth users; NULL for OTP users

Index ix_users_oauth_provider_id:  (auth_provider, oauth_provider_id)
                                    Partial unique enforcement for OAuth dedup
```

### Live database state (2026-05-24)

```
alembic_version:        014_user_oauth_columns ✓
users count:            ~2-3 (founder + test accounts; no organic users yet)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          50+ (from sessions + testing)
messages:               150+ (from sessions + testing)
daily_usage rows:       populated during test runs
safety_events:          populated (safety pipeline active since Phase 4)
memory_entries:         wiring active; 0 organic entries (no real users yet)
source_chunks:          2476 chunks across 7 personas (C3b, 2026-05-17)
scheduled_emails:       empty (ritual not yet exercised by real users)
```

### Table population status

| Table | Status | Notes |
|---|---|---|
| `daily_usage` | ✅ Actively populated | Incremented per successful non-ritual non-admin message |
| `messages.model_used` | ✅ Actively populated | Set on every assistant message |
| `safety_events` | ✅ Actively populated | Safety pipeline live since Phase 4 |
| `memory_entries` | 🟡 Wired but not accumulating | ARQ task queued; no organic users |
| `conversations.deleted_at` | ❌ Not yet used | Soft-delete field exists; endpoint not exposed |
| `scheduled_emails` | ❌ Not yet populated | Ritual live in UI; ARQ delivery not yet wired |
| `users.auth_provider` | ✅ Populated for all rows | Backfill set all to 'otp' in migration |
| `users.oauth_provider_id` | ❌ Always NULL | Google OAuth dormant; no OAuth signups |

### RLS state

**RLS DISABLED on all public tables.** Mitigation: frontend goes exclusively through the FastAPI gateway; no Supabase anon key in the frontend bundle.

---

## 5. Backend endpoints

```
POST /api/v1/auth/register             (legacy — passwordless flow preferred)
POST /api/v1/auth/login                (legacy — passwordless flow preferred)
GET  /api/v1/auth/me                   (auth)
POST /api/v1/auth/otp/request          (public, rate-limited via Redis)
POST /api/v1/auth/otp/verify           (public)
GET  /api/v1/auth/methods              (public — returns list of enabled auth providers; PR4k)
POST /api/v1/auth/google/login         (public — DORMANT; Google OAuth initiation; PR4k)
                                        ⚠️ Only active when GOOGLE_OAUTH_ENABLED=true

GET  /api/v1/disclaimer/current        (public)
POST /api/v1/disclaimer/accept         (auth)

GET  /api/v1/personas                  (public — returns all 9 active personas)

GET  /api/v1/preferences               (auth — returns user's saved preferences or 404)
POST /api/v1/preferences               (auth — save/update themes + need_most)
GET  /api/v1/preferences/matches       (auth — returns top-3 matched personas)

POST /api/v1/conversations             (auth — create conversation)
GET  /api/v1/conversations             (auth — list conversations, max 50)
GET  /api/v1/conversations/{id}/messages   (auth — fetch message history)
POST /api/v1/conversations/{id}/messages   ← CANONICAL SEND-MESSAGE (SSE streaming)
DELETE /api/v1/conversations/{id}          (auth — soft delete)

GET  /api/v1/subscription              (auth — synthetic endpoint; returns plan data from DB)
                                        ⚠️ BETA: returns isPro=true for all users when
                                        BETA_GRANT_PRO_TO_ALL=true (PR4j)

POST /api/v1/billing/checkout          (auth — create Stripe Checkout session; returns {url})
POST /api/v1/billing/portal            (auth — open Stripe Customer Portal; returns {url})
POST /api/v1/billing/webhook           (public — Stripe webhook handler; 6 events)

POST /api/v1/share/{conversation_id}   (auth — create share token; returns {share_url})
GET  /api/v1/share/{token}             (public — returns shareable conversation data)

POST /api/v1/admin/backfill-titles     (admin — backfill auto-generated titles)

GET  /health                           (public)
```

**There is exactly ONE send-message endpoint.** PATH B was deleted in C-RECON-8 (PR #60).

### Google OAuth routes (PR4k — dormant)

`POST /api/v1/auth/google/login` and `GET /api/v1/auth/methods` are live in code but gated by `GOOGLE_OAUTH_ENABLED` environment variable (default `false`). When enabled, the login endpoint initiates the Google OAuth flow. The database schema (migration 014) is fully deployed; only the app-level flag prevents user-facing activation. Requires brand/domain decision before enabling.

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v9. See v9 §6 for full specification and feature list. All 19 features are live.

---

## 7. Persona error messages

All 9 personas have `llm_unavailable` error messages in DB. Unchanged from v9 §7.

---

## 8. LLM provider validation

Unchanged from v9 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 9. Locked decisions (as of 2026-05-16 + PR4j additions)

All 10 from v9 remain locked. Addition from PR4j:

| # | Decision | Detail | Rationale |
|---|---|---|---|
| 11 | **BETA_GRANT_PRO_TO_ALL bypass** | Both `get_current_user_plan` and `get_user_tier` return Pro during cold beta when env var set | Allows founder + testers to access full feature set without Stripe purchase during pre-revenue validation |

---

## 10. Reconciliation history

Unchanged from v9. See v9 §10 for C-RECON-1 through C-RECON-8.

---

## 11. PR4j BETA bypass system

**Added 2026-05-22 (PR4j / PR #100 paywall-audit)**

### What was shipped

1. **`BETA_GRANT_PRO_TO_ALL` env var** — when `true` in Render, both tier-resolution functions return Pro for all users. Zero per-user DB changes required; toggle is atomic.

2. **`auth.get_current_user_plan` modified** — checks `BETA_GRANT_PRO_TO_ALL` before reading `Subscription.plan`; returns `"pro"` if bypass active.

3. **`tier_service.get_user_tier` modified** — same bypass added independently (duplication acknowledged as tech debt TD-11).

4. **`GET /api/v1/subscription` synthetic endpoint** — returns `{isPro, plan, status, interval}` assembled from DB and env vars. Frontend `SubscriptionBootstrap` calls this on mount and hydrates Zustand `useAuthStore` with `isPro` flag.

5. **`SubscriptionBootstrap` component** — layout-level component that fires once on app mount, calls `/api/v1/subscription`, and sets `isPro` in the store. Prevents per-page subscription re-fetching.

### Known tech debt

See TD-11 in IMPLEMENTATION_BACKLOG_v11.md: dual tier resolution functions must be consolidated before disabling the BETA bypass for paid launch.

---

## 12. Frontend architecture: Today page data flow

**Added 2026-05-24 (documenting lesson from PR4n/PR4p regression)**

The Today page (`apps/web/app/app/(tabs)/today/page.tsx`) uses a `load()` async function pattern with a local React state machine. Understanding this is critical for any future modification.

### State variables

```typescript
const [loading, setLoading] = useState(true)
const [isFirstDay, setIsFirstDay] = useState(false)
const [lastConv, setLastConv] = useState<Conversation | null>(null)
const [recentLine, setRecentLine] = useState<SavedLine | null>(null)
```

### Data flow

```
useEffect([], []) → load()
  ├─ api.getConversations()    ← REQUIRES import { api } from '@/lib/api'
  ├─ if conversations.length === 0 → setIsFirstDay(true)  → renders Welcome state
  └─ if conversations.length > 0  → setLastConv(...)      → renders Returning state
                                   → api.getSavedLines()  → setRecentLine(...)
```

### Critical dependency: api import

`import { api } from '@/lib/api'` is **required** for `load()` to function. PR4n accidentally removed this import while extracting `SharePreviewModal` (the `ShareLimitError` import was correctly moved, but `api` was taken with it). Result: `load()` was never called → all users saw first-day Welcome state regardless of conversation history.

**Process rule (P-05 in CLAUDE.md):** When extracting a component, grep the original file for ALL usages of removed imports BEFORE deleting. Each usage must be either re-added or confirmed genuinely removed.

### Hydration guard history

PR4p added a `_hasHydrated` Zustand guard (onRehydrateStorage callback) to prevent auth-check useEffects from firing before store hydration. This guard **never lifted in the production Next.js build** — `onRehydrateStorage` callback timing in the actual build differs from local dev. Result: production-wide regression where all protected pages redirected to /auth on hard refresh.

PR4r (in flight 2026-05-24) reverts the hydration guard while keeping the api import fix.

**Future approach for hydration:** See TD-10 in IMPLEMENTATION_BACKLOG_v11.md.

---

## 13. Session metrics

### 2026-05-21–24 session

| Metric | Value |
|---|---|
| PRs merged | PR4j (#100), PR4l (hotfix), PR4m (#99), PR4k (#101), PR4n (#102), PR4o (#103), PR4p (#104), PR4q (#105) + PR4r in flight |
| Production regressions | 2 (PR4n: api import removed; PR4p: hydration guard broke all protected pages) |
| P0 fire from PR4p | All users redirected to /auth on hard refresh/direct URL — full regression |
| Emergency rollbacks | PR4q (empty commit — branching error); PR4r (proper rollback, in flight) |
| Migrations deployed | 012, 013, 014 |
| New backend endpoints | GET /api/v1/auth/methods, POST /api/v1/auth/google/login (dormant), GET /api/v1/subscription |
| New frontend pages | /app/rituals |
| New frontend components | SharePreviewModal, SubscriptionBootstrap, RitualsCard (simplified), rituals page cards |
| Lessons codified | 5 (P-01 through P-05 in CLAUDE.md) |

---

## 14. Known bugs (active)

### Carried from v9

All v9 bugs carried forward. Auth race (refreshing authenticated route → redirect to /auth) remains P0. BUG-011 (safety_events.message_id always NULL) remains open.

### New from 2026-05-21-24 session

| ID | Description | Severity | Notes |
|---|---|---|---|
| BUG-012 | Zustand hydration race — hard refresh/direct URL on protected routes flashes to /auth | 🔴 P0 | Pre-existing; PR4p attempted fix broke production worse. TD-10 in backlog. |
| BUG-013 | PR4p hydration guard — resolved | 🟢 CLOSED | PR4r reverts guard; api import fix preserved. |
| BUG-014 | Letter to my Future Self — scheduled_emails ARQ delivery not wired | 🟡 P2 | UI exists; DB schema live; email send task not yet implemented. |

---

## 15. Environment variables

### Backend (Render)

```
DATABASE_URL                  (Supabase pooler)
REDIS_URL                     (Upstash)
RESEND_API_KEY                (set)
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>"
JWT_SECRET                    (set)
ANTHROPIC_API_KEY             (set — actively used for chat)
PHENOMENOLOGY_BRIDGE_ENABLED  (state unverified — was true 2026-05-04/05)

FRONTEND_URL                  "https://thinkalike.netlify.app"  ← NEW PR4k
                               Replaces BASE_URL for Stripe success/cancel URLs
                               and ritual reminder email links. 6 call sites migrated.

BETA_GRANT_PRO_TO_ALL         "true"  ← NEW PR4j
                               When true: all users treated as Pro. Toggle to false
                               before disabling for paid launch.

GOOGLE_OAUTH_ENABLED          "false"  ← NEW PR4k (dormant)
GOOGLE_CLIENT_ID              (placeholder — set when brand decision made)
GOOGLE_CLIENT_SECRET          (placeholder — set when brand decision made)

STRIPE_SECRET_KEY             ✅ Set (PR1 #77, 2026-05-19)
STRIPE_WEBHOOK_SECRET         ✅ Set (PR1 #77, 2026-05-19)
STRIPE_PRICE_PRO_MONTHLY      ✅ Set — €14.90/mo price ID
STRIPE_PRICE_PRO_YEARLY       ✅ Set — €149/yr price ID
STRIPE_PRICE_PREMIUM_MONTHLY  ✅ Set — placeholder; Premium deferred

BASE_URL                      ⚠️ DEPRECATED (PR4k)
                               Was "https://philosopher-api.onrender.com" — WRONG URL (404).
                               Canonical backend URL is philosopher-api-z9l9.onrender.com.
                               All 6 call sites migrated to FRONTEND_URL in PR4k.
                               config.py still has the setting but no app code reads it.
                               Remove in next cleanup PR (TD-14).

ANTHROPIC_MODEL (config.py)   ⚠️ ORPHANED — not read by conversation_service.py
```

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set (PR1 #77, 2026-05-19)
```

---

## 16. Key file paths (production codebase)

### Backend (apps/api/)

All v9 paths apply. Additions and changes since v9:

- `routers/auth_oauth.py` — Google OAuth routes (PR4k): `GET /auth/methods`, `POST /auth/google/login`. Gated by `GOOGLE_OAUTH_ENABLED` flag.
- `routers/auth.py` — `get_current_user_plan` dependency modified (PR4j) to check `BETA_GRANT_PRO_TO_ALL` before reading `Subscription.plan`.
- `services/tier_service.py` — `get_user_tier` modified (PR4j) to check `BETA_GRANT_PRO_TO_ALL`; returns `"pro"` for all users during beta.
- `db/migrations/versions/012_scheduled_emails.py` — `scheduled_emails` table (PR4o)
- `db/migrations/versions/013_add_ondelete_conversation_fks.py` — FK ondelete clauses (PR4m)
- `db/migrations/versions/014_user_oauth_columns.py` — `auth_provider` + `oauth_provider_id` columns on `users` (PR4k)
- `requirements.txt` — `emoji==2.12.1` added (PR4n — emoji strip for share preview)

### Frontend (apps/web/)

All v9 paths apply. Additions since v9:

- `app/app/(tabs)/rituals/page.tsx` — Rituals page (PR4o): 4 cards (Letter functional, 3 locked)
- `app/app/(tabs)/today/page.tsx` — RitualsCard simplified to Letter-only + "See all rituals →" affordance; "See all reflections →" affordance added (PR4o)
- `app/app/(tabs)/layout.tsx` — tab swap: Reflections → Rituals (Compass icon) (PR4o)
- `components/share/SharePreviewModal.tsx` — share preview with annotation overlay + dynamic font (64→28px across 15–350 chars) (PR4n)
- `components/layout/SubscriptionBootstrap.tsx` — layout-level subscription hydration (PR4j): calls `/api/v1/subscription`, sets `isPro` in Zustand
- `lib/store.ts` — `_hasHydrated` guard ADDED in PR4p, REMOVED in PR4r (see §12)

---

## 17. Note: KIEN is a SEPARATE project

Unchanged from v8/v9.

---

## 18. CLAUDE.md violations log

### Carried from v9

2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` (408 lines) during C3a. Resolved via Path C recovery commit f78d0f3. See v9 §16b.

### New: 2026-05-23 — PR4p bundled two logical changes

PR4p (#104) bundled:
1. **P0 fix** — restored `import { api }` in `today/page.tsx` (PR4n regression)
2. **P1 experiment** — `_hasHydrated` Zustand hydration guard

The hydration guard broke production (P1 caused a P0 regression). Rollback was complicated because the two changes were tangled in one PR. Rule P-02 in CLAUDE.md now codifies: one logical change per PR.

### New: 2026-05-23 — PR4q empty commit due to stale local main

PR4q (#105) was supposed to revert the PR4p hydration guard. Became an empty commit because the CC agent branched off a stale local `main` that didn't have PR4p's commit yet. Rule P-01 in CLAUDE.md now codifies: always `git fetch origin && git reset --hard origin/main` before any hotfix branch.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **bugfixes-3 — auth race fix** (promoted to P0 2026-05-18; hydration TD-10; approach TBD — see IMPLEMENTATION_BACKLOG_v11.md)
- [ ] **PR4r merge** — actual rollback of hydration guard (in flight 2026-05-24)
- [ ] **End-to-end Stripe sandbox test** — test card → webhook → entitlement → portal → cancel
- [ ] **Backfill-titles admin execution** — run `POST /api/v1/admin/backfill-titles`
- [ ] **Mobile 12-point nav smoke test** — real iOS Safari
- [ ] **Cold beta with 3–5 fresh users** — signup → conversation → Stripe upgrade
- [ ] **Consolidated polish PR** (blocks Block B visual closure)
- [ ] **Lawyer review of legal templates**
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**

### Open items (P1)

- [ ] **Wire generate_insight_task** (TD-05) — when memory_entries accumulating
- [ ] **Render API plan upgrade** (~$7/mo cold-start elimination)
- [ ] **C6c — cold-start screen**
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to my Future Self — ARQ email delivery wiring** (BUG-014)

### Open items (P2 — tech debt)

- [ ] **TD-10** — Zustand hydration race (pre-existing; must smoke test on Netlify preview before any new attempt)
- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch)
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (3 inline modals now)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-20** — safety_events.message_id FK is NO ACTION; should be SET NULL (consistency with PR4m migration 013 pattern). Currently 0 rows trigger the bug. Becomes critical when safety pipeline starts populating message_id. Fix = 1-line migration 015 ALTER.
- [ ] **TD-21** — passive_deletes=True audit needed across remaining parent-child relationships in apps/api/models/__init__.py (User.conversations, User.messages, User.saved_lines, etc). Not user-facing today; becomes P0 when delete-account / GDPR flow is exposed.
- All v9 TD-01 through TD-09 items (see IMPLEMENTATION_BACKLOG_v11.md)

### Closed items (2026-05-21-24)

- [x] **CLOSED 2026-05-22** — PR4j paywall-audit (#100): BETA_GRANT_PRO_TO_ALL bypass + synthetic /subscription + SubscriptionBootstrap
- [x] **CLOSED 2026-05-22** — PR4l alembic hotfix: revision_id VARCHAR(32) length fix
- [x] **CLOSED 2026-05-22** — PR4m hotfix (#99): migration 013 FK ondelete clauses
- [x] **CLOSED 2026-05-23** — PR4k Google OAuth (#101): dormant implementation + migration 014 + FRONTEND_URL + BASE_URL deprecation (6 call sites)
- [x] **CLOSED 2026-05-23** — PR4n Share v2 (#102): SharePreviewModal + dynamic font + emoji strip
- [x] **CLOSED 2026-05-23** — PR4o Rituals (#103): tab swap + /app/rituals page + Today RitualsCard simplified + migration 012 scheduled_emails
- [x] **CLOSED 2026-05-23** — PR4p hotfix (#104): api import fix (P0) + hydration guard (P1 — later reverted)
- [x] **CLOSED 2026-05-23** — PR4q (#105): empty commit (lesson recorded; not a real change)
- [x] **CLOSED 2026-05-24** — PR4s (#108): conversation delete bug fix; passive_deletes=True + cascade="all, delete-orphan" on Conversation.messages relationship. Root cause: SQLAlchemy ORM was nullifying messages.conversation_id before DB-level CASCADE could fire.
- [x] **CLOSED 2026-05-24** — PR4t (#109): RitualsCard removed from Today tab (redundant after PR4o promoted Rituals to its own tab). 1 file, 20 lines deleted.
- [x] **CLOSED 2026-05-24** — PR4v (#110): cleanup bundle (TD-14 BASE_URL removal, TD-15 markdown fence strip in memory extraction, TD-16 INK_COLOR sync to #1F1B14). 3 files, 8/3 insertions/deletions.
- [x] **CLOSED 2026-05-24** — PR4u (#111): edge state pages (not-found.tsx, app/error.tsx, global-error.tsx). Mixed tone: philosophical 404 / philosophical-lite in-app / direct global. 3 new files, 178 lines.

---

**End of PROJECT_STATE v11.** Authoritative as of 2026-05-24. Supersedes `PROJECT_STATE_v9.md` (preserved as historical reference). *(v10 was skipped — two sessions absorbed into one rotation.)*
