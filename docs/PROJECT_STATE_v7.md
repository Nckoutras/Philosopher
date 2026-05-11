# PHILOSOPHER — Project State v7

> **What this file is:** Live snapshot of the project's current implementation status.
> Regenerated via `make state` (which calls Claude Code to read the repo and rewrite this file).
> Re-upload to Claude.ai Project Knowledge after each regeneration.
>
> **Sections marked "MANUAL — preserved across regenerations":** these are not auto-updated.
> Edit by hand for decisions, blockers, and qualitative notes.
>
> **v7 = v6 baseline (2026-05-09) + 2026-05-10 session deltas (Block A 5/5 closure, disclaimer flow live, legal pages, Vercel disconnected). Authoritative.**

---

**Last updated:** 2026-05-10 (v7 consolidation — Block A 5/5 closed in production; disclaimer flow live end-to-end; legal pages shipped; Vercel disconnected)
**Last `make state` run:** 2026-04-29 (stale — `make state` infrastructure broken per §10 housekeeping #4; manual updates by mentor instance)
**Current phase:** Phase 4 stabilization sequence CLOSED 2026-05-05 (8 ship items). Setup PR + Greenfield scaffold CLOSED 2026-05-07. **Block A — Authentication CLOSED 2026-05-10 (5/5 line items live in production: A1, A2/A3, A4, A5, A6+A7).** End-to-end verified with real `disclaimer_acceptances` row for founder's user. 2026-05-06 founder decision still authoritative: build all 43 specced screens before public launch. **2026-05-10 update: Founder confirmed Plan A path is active (Block B sequential build), Plan B preserved as alternative.** Phase 5 → P3 post-feedback. Phase 6 → P1 post-revenue. Web/PWA only for v1. Native app submission → v2. **Next P0 work surface:** Block B — Onboarding (B1–B6), PAUSED awaiting confirmation of 4 strategic decisions (B2/B3 persistence, matching algorithm location, B6 timing, user_preferences schema shape). See `HANDOFF_BRIEF_v7.md` §17.2.5 and §B.3.
**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment:** https://thinkalike.netlify.app (canonical; **Vercel project DISCONNECTED 2026-05-10** — `thinkalike.vercel.app` no longer auto-deploys)

> **v7 note:** This file consolidates `PROJECT_STATE_v6.md` (2026-05-09) + `PROJECT_STATE_v6_ADDENDUM_2026_05_10.md`. All factual state changes from the 2026-05-10 session are integrated inline. Where v6 conflicts with addendum, addendum wins.

---

## 1. Stack (locked)

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 |
| Database | PostgreSQL 17 (Supabase, eu-west-1) |
| Queue/Cache | Redis (Upstash) + ARQ + APScheduler |
| LLM | Anthropic Claude (streaming) |
| Embeddings | OpenAI text-embedding-3-small |
| Auth | Custom JWT + passwordless OTP (FastAPI-issued; Resend for code delivery) |
| Billing | Stripe (scaffolded, NOT wired) |
| Email | Resend (active for OTP delivery as of 2026-05-08) |
| Analytics | PostHog (configured, unused) |

**Hosting:**
- Frontend (canonical): Netlify (project: thinkalike, URL: thinkalike.netlify.app)
- ~~Frontend (legacy, must disconnect): Vercel~~ — **DISCONNECTED 2026-05-10.** Founder deleted `thinkalike.vercel.app` project via Vercel dashboard; GitHub integration cleanup confirmed. Production canonical is exclusively Netlify.
- Backend: Render (free tier — `WEB_CONCURRENCY=1`, 15-min idle cold-start, mitigated by external ping bot; upgrade decision pending)
- Database: **Supabase project `plecolxlzshkfvybszgs` (eu-west-1)** — VERIFIED LIVE 2026-05-08/09 via DATABASE_URL inspection + Supabase MCP queries returning production data. ⚠️ v5 §1 + §12 stated Render PostgreSQL `philosopher-db` is the production DB. Reality differs. Either an undocumented migration occurred between 2026-05-06 and 2026-05-08, or v5 was incorrect. **Render `philosopher-db` status to be verified** — was it decommissioned, demoted to staging, or just stale info in v5?
- Cache (Redis): **Upstash `philosopher-prod` (eu-west-1)**, free tier — provisioned 2026-05-08; `REDIS_URL` set in Render env vars; ARQ + APScheduler operational. Resolves the silent breakage of background tasks (memory extraction, insight generation, ritual reminders) that had been broken in production for unknown duration prior to 2026-05-08. **Rate limiter confirmed working 2026-05-10** (founder hit 5-requests-in-6-minutes ceiling, received 429 Too Many Requests as designed).
- Email (Resend): RESEND_API_KEY + FROM_EMAIL set in Render env vars; sender = `Great Minds <onboarding@resend.dev>`. ⚠️ Free tier without verified domain — sends reliably only to founder's email; switch to verified domain required before public launch.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- ~~Legacy URL still serving: https://thinkalike.vercel.app~~ — **disconnected 2026-05-10**
- Last production deploy: 2026-05-10 (PR #28 — legal Terms + Privacy pages)
- Has paying users: **No**
- Has free trial users: **No**
- Auth flow status: **end-to-end live in production as of 2026-05-10 ~23:00 (Block A 5/5 closed)**
  - POST `/auth/otp/request` → 202 Accepted
  - Email delivery via Resend confirmed (~5 second SLA)
  - POST `/auth/otp/verify` → 200 OK with JWT, user object (now includes `needs_disclaimer: bool`)
  - Token persistence: localStorage `ph_token` + cookie `ph_token` (7-day, SameSite=Lax)
  - Zustand store (`philosopher-store`) updated with user data
  - If `needs_disclaimer=true` → redirect to `/auth/disclaimer`; user accepts age + non-therapy positioning → row inserted in `disclaimer_acceptances` with audit fields (locale, IP, user agent, accepted_at, both confirmation flags)
  - If `needs_disclaimer=false` → redirect to `/app/dashboard` (still 404 by design until Block H+I)
  - Subsequent OTP logins correctly skip `/auth/disclaimer` for already-accepted users (idempotency + version check verified working 2x in incognito)
- Stripe wired: **No** (calendar-gated until 2026-05-11; see `IMPLEMENTATION_BACKLOG_v7.md` §5)
- User validation done: **No** (founder's plan: UAT mixed-group with ≥2/5 spontaneous "I'd pay" criterion before public launch, after 43-screen UI build — Plan A path confirmed 2026-05-10)
- Phase 4 feature flag (`PHENOMENOLOGY_BRIDGE_ENABLED`): verified active during 14-test session 2026-05-04/05. **Current state should be confirmed in Render env vars before public launch.**
- Render API web service `philosopher-api`: **free tier** as of 2026-05-10. Upgrade decision pending. Free-tier limits: `WEB_CONCURRENCY=1`, 15-min idle cold-start. Mentor recommendation: upgrade now (~$7/month) to avoid friction during dev cycle and prevent first-impression damage with UAT testers.
- Database (Supabase): **paid tier — verified 2026-05-08/09.** No 30-day expiry risk. RLS disabled on all 15 public tables (security flag — must be addressed before public launch with real users; currently mitigated by frontend going through FastAPI exclusively, but anon key exposure remains a theoretical risk). **Note 2026-05-10:** new `disclaimer_versions` and `disclaimer_acceptances` tables follow the same RLS-disabled convention.
- Render PostgreSQL `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`): **status uncertain.** Was upgraded to paid tier 2026-05-06 per v5 §2. Whether still active, decommissioned, or migrated to Supabase between 2026-05-06 and 2026-05-08 is unverified. Founder action: confirm and update §10/§12 with reality.

### 2026-05-10 production verification snapshot

Captured ~23:00 UTC at session end:

```
alembic_version:        003_disclaimer_acceptances ✓
users count:            2 (nckoutras@gmail.com, freetester@gmail.com)
personas count:         6 (Marcus, Jung, Socrates, Epictetus, Freud, de Beauvoir)
disclaimer_versions:    1 (v1.0 seed)
disclaimer_acceptances: 1 (founder's acceptance, 2026-05-10 19:53:29 UTC)
conversations count:    50 (from prior sessions)
messages count:         139 (from prior sessions)
```

Disclaimer acceptance row audit fields verified populated: `user_id`, `version_id=1`, `confirmed_age_18=true`, `confirmed_non_therapy=true`, `locale='en'`, `ip_address=94.64.188.99`, `user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."`, `accepted_at=2026-05-10 19:53:29.652395+00`.

---

## 3. Personas registered (`apps/api/personas/__init__.py`)

| Slug | Tier | Python config | DB `is_active` | Tested by founder | Section 5.7-compliant |
|---|---|---|---|---|---|
| marcus_aurelius | free | ✅ | ✅ | ✅ excellent | ✅ Phases 1-3; Phase 4 essence-only (shading PR Β pending) |
| socrates | free | ✅ | ✅ (fixed via direct SQL 2026-05-03) | ✅ smoke-tested 2026-05-03 | ✅ Phases 1-4 |
| carl_jung | pro | ✅ | ✅ | ✅ excellent | ✅ Phases 1-4 |
| simone_de_beauvoir | pro | ✅ | ✅ | ✅ excellent | ✅ Phases 1-4 |
| epictetus | pro | ✅ (verified Epictetus, not Jung) | ✅ (fixed via direct SQL 2026-05-03) | ⚠️ untested by founder | ✅ Phases 1-4 |
| sigmund_freud | pro | ✅ | ✅ (fixed via direct SQL 2026-05-03) | ⚠️ untested by founder | ✅ Phases 1-4 |

**Notes:**
- All 6 imported and registered in `__init__.py` as of commit `12a6e1d` (2026-04-27).
- All 6 active in production DB as of 2026-05-03 (direct SQL fix from Render Shell — `seed.py` UPDATE branch bug deferred to backlog #21).
- Phase 4 PR Α covers all 6 personas via shared `modern_phenomenology.json` map. 5/6 personas have populated shading data; Marcus has none (33 strings to be authored in PR Β); falls back to generic essence rendering.
- Live persona data verified 2026-05-08/09 via Supabase MCP: 6 rows in `personas` table; data unchanged from v5 state.

---

## 4. PersonaConfig schema (`apps/api/personas/_base.py`)

Unchanged from v5. Current dataclass fields (22 base + 8 Phase 1 optional = 30 total). See v5 §4 for the full Python class definition.

**Section 5.7 fields populated for all 6 personas as of 2026-05-04** (Phase 3 closure):
- All 8 Phase 1 optional fields: `character_anchors`, `register_range`, `anti_flexing`, `response_length_words`, `forbidden_lexicon_persona_specific`, `behavioral_parameters`, `behavioral_parameters_by_register`, `safety`

**Section 5.7 fields lifecycle (Phase 4 update):**
- `modern_phenomenology_shading` was DROPPED from `PersonaConfig` schema in Phase 1 (commit `0ade549`) — lives in shared map at `apps/api/philosopher_brain/maps/modern_phenomenology.json`, not per-persona.
- Runtime per-request dataclass `PhenomenologyBridge` added to `apps/api/personas/_models.py` 2026-05-04 (Phase 4 PR Α). Not part of `PersonaConfig`; produced by `phenomenology_bridge_service.lookup()` per request.

---

## 5. System prompt template (`apps/api/prompts/system_base.jinja2`)

Unchanged from v5. Existing template structure (verified post-Phase-4):
1. Application identity + non-clinical disclaimer
2. Current date + user_name (optional)
3. PERSONA section with persona.system_fragment + tone/structure/register/challenge/questioning + forbidden phrases
4. **MODERN PHENOMENOLOGY BRIDGE** (Phase 4 PR Α — conditional on `phenomenology_bridge` argument; inner conditional for `persona_shading` to handle Marcus case)
5. WHAT YOU KNOW ABOUT THIS PERSON (memories — conditional)
6. GROUNDING PASSAGES (RAG retrieval — conditional)
7. HARD RULES (7 numbered non-negotiables)

**Section 5.7 sections still NOT in template** (Phase 5+ work):
- Character anchors structured rendering
- Anti-flexing structured rendering
- Brevity directive (numerical) — currently enforced via runtime postprocessing only
- Register directive

---

## 6. What's been built (production-verified)

Routers (`apps/api/routers/`):
- `auth.py` — register/login via custom JWT ✅. **Extended 2026-05-08 with passwordless OTP endpoints** (`POST /auth/otp/request`, `POST /auth/otp/verify`) ✅. **Extended 2026-05-10: all 4 auth response paths (register, login, /me, otp/verify) compute `needs_disclaimer` via `user_needs_acceptance()` and propagate it on `UserOut` (prevents disclaimer bypass via legacy paths).** ✅
- `personas.py` — list/get with tier filtering ✅
- `conversations.py` — chat endpoint with Anthropic streaming ✅
- `memory.py` — long-term recall (UNTESTED end-to-end) ⚠️
- `billing.py` — Stripe scaffolding only, NOT wired ❌
- `rituals.py` — endpoint exists, "Begin" button broken in UI ❌
- `admin.py` — review safety events ✅
- `disclaimer.py` — **NEW 2026-05-10, PR #25.** `GET /api/v1/disclaimer/current` (public) returns active disclaimer version; `POST /api/v1/disclaimer/accept` (auth required) records acceptance with audit fields. IP extraction via `x-forwarded-for` header (Render proxy aware). Both confirmation flags must be `true` else returns 400. ✅

Services (`apps/api/services/`):
- `analytics_service.py` — usage/event analytics
- `conversation_service.py` — conversation orchestration (extended 2026-05-04 with Step 3.5 phenomenology bridge lookup + `PHENOMENOLOGY_BRIDGE_ENABLED` feature flag)
- `email_service.py` — Resend integration. **Active in production for OTP delivery as of 2026-05-08** (was "configured, unused" through v5).
- `embedding_client.py` — OpenAI embedding wrapper
- `llm_client.py` — Anthropic Claude client
- `memory_service.py` — long-term memory retrieval
- `otp_service.py` — **NEW 2026-05-08, PR #18.** Generates 6-digit OTP, hashes + salts, stores in `otp_codes` with 10-min expiry, max 5 attempts then locks. Calls `email_service.send_email()` for delivery. Verifies code on `/auth/otp/verify`, issues JWT on success.
- `disclaimer_service.py` — **NEW 2026-05-10, PR #25.** Module-level async functions (matches `otp_service.py` convention, no class wrapper). Public API: `get_current_version(db)` → latest disclaimer version by `effective_at DESC`; `user_needs_acceptance(user_id, db)` → bool, catches `NoVersionAvailable` internally and returns False (don't block login on misconfigured DB); `accept(user_id, flags, locale, ip, ua, db)` → INSERT with idempotent `IntegrityError` catch on `UNIQUE(user_id, version_id)` → query existing row and return as success. Exception hierarchy: `DisclaimerError` → `NoVersionAvailable`.
- `phenomenology_bridge_service.py` — **NEW 2026-05-04, Phase 4 PR Α.** Loads shared phenomenology map at startup, performs substring-match classifier with specificity resolution + slug normalization + fail-open exception handling
- `postprocessing_service.py` — Phase 2 brevity + forbidden lexicon enforcement
- `prompt_builder.py` — system prompt assembly (extended 2026-05-04 with `phenomenology_bridge` argument)
- `rate_limit_service.py` — Redis-backed counter per `(email, action)`. **NO try/except wrapper; raises if Redis unavailable.** Used by OTP request endpoint. **Confirmed working in production 2026-05-10** — founder hit 5-requests-in-6-minutes ceiling, received 429 Too Many Requests as designed.
- `retrieval_service.py` — pgvector similarity search
- `safety_service.py` — 3-tier safety classification

Database migrations (`apps/api/db/migrations/versions/`):
- `001_initial.py` — initial schema
- `002_otp_codes.py` — **NEW 2026-05-08, PR #18.** Creates `otp_codes` table + `(email, created_at DESC)` index.
- `003_disclaimer_acceptances.py` — **NEW 2026-05-10, PR #24, commit `acb910c`** (55 lines). Creates `disclaimer_versions` + `disclaimer_acceptances` tables, seeds v1.0 disclaimer copy. `alembic_version` advanced from `002_otp_codes` → `003_disclaimer_acceptances` cleanly via container start (alembic plumbing fix from 2026-05-09 working as designed).
- **Layout fix 2026-05-09:** files moved into `versions/` subdirectory after discovery that flat layout was preventing alembic from finding migrations. `alembic_version` stamped to `'002_otp_codes'` to align state.

Systems:
- pgvector similarity search ✅
- Memory feature: implemented, untested end-to-end ⚠️
- Safety system: 3-tier (high/medium/low) per README, code path unverified ⚠️
- Rate limiting per plan: code merged commit `3ba572f`, NOT browser-tested ⚠️
- Streaming SSE ✅
- Persona registry pattern ✅
- **Postprocessing pipeline (Phase 2):** active in production, smoke-tested 2026-05-03 ✅
- **Modern phenomenology bridge (Phase 4 PR Α):** infrastructure deployed; map expanded 33→78 entries; flag verified active during 14-test session 2026-05-04/05 ✅
- **Passwordless auth pipeline (Block A):** end-to-end live as of 2026-05-09 ✅
- **Disclaimer acceptance flow (A6+A7, Block A):** end-to-end live as of 2026-05-10. Schema → backend → frontend → routing chain verified with real production acceptance row. Idempotency + version-skip for already-accepted users confirmed working. ✅
- **Legal pages (Terms + Privacy):** template versions live at `/legal/terms` and `/legal/privacy` as of 2026-05-10. ⚠️ Templates — pre-public-launch lawyer review required. ✅ (templates), ⚠️ (lawyer review pending)
- **Alembic migrations on container start:** Dockerfile CMD includes `alembic upgrade head &&` prefix; ensures schema sync on every deploy from 2026-05-08 forward ✅
- **ARQ + APScheduler (Redis-backed):** operational as of 2026-05-08 (was silently broken before due to missing REDIS_URL) ✅

Frontend (`apps/web/`):
- `lib/api.ts` — extended 2026-05-09 with `api.verifyOtp(email, code)` method (PR #20); **extended 2026-05-10 (PR #25/#26): `User` interface adds `needs_disclaimer?: boolean`; 3 new types (`DisclaimerCurrent`, `DisclaimerAcceptRequest`, `DisclaimerAcceptResponse`); 2 new methods (`getDisclaimerCurrent()`, `acceptDisclaimer(body)`).**
- `lib/store.ts` — Zustand store with `setAuth(user, token)` / `clearAuth()` ✅. **No changes 2026-05-10:** `User` imported from `./api` so `needs_disclaimer` extension propagates automatically.
- `app/page.tsx` — A1 splash (PR #15) ✅
- `app/auth/page.tsx` — A2/A3 sign-in email entry (PR #17) ✅. **Modified 2026-05-10 (PR #28):** `process.env.NEXT_PUBLIC_TERMS_URL ?? '/legal/terms'` (was `'#'`), same for privacy.
- `app/auth/verify/page.tsx` — A5 verify OTP code entry (PR #20, with Suspense boundary) ✅. **Extended 2026-05-10 (PR #26):** conditional routing — `if (data.user.needs_disclaimer) router.push('/auth/disclaimer') else router.push('/app/dashboard')`. **Also modified 2026-05-10 (PR #28):** env-var-with-fallback URLs for Terms/Privacy.
- `app/auth/trouble/page.tsx` — **NEW 2026-05-10 (PR #22 + #23 + text-center fix).** A4 trouble accessing email screen. ~95 lines, client component. Currently a muted `bg-linen` future-state placeholder with copy "Try a different sign-in method — Apple and Google sign-in coming soon" + mailto: link via `<a href>` (Chrome incognito incompatibility with `window.location.href` discovered + worked around). Uses `NEXT_PUBLIC_SUPPORT_EMAIL` env var (placeholder `nckoutras@gmail.com` until real `support@thegreatminds.app` exists). ✅
- `app/auth/disclaimer/page.tsx` — **NEW 2026-05-10 (PR #26, commit `614dc51`, squashed `17c48a6`).** A6+A7 combined disclaimer page. 172 lines, client component. BronzeDivider ornament at top, centered hero, 2 stacked clickable checkbox cards (left-aligned for readability per spec), inline 20×20 SVG checkmark with literal `stroke="#FAF4E6"` (avoids currentColor inheritance bug against bg-ink), auth guard via `store.token` check (redirects to /auth if missing), fetches via `getDisclaimerCurrent()`, submits via `acceptDisclaimer()`, inline retry link on fetch error. ✅
- `app/legal/terms/page.tsx` — **NEW 2026-05-10 (PR #28).** Server component, 123 lines. 16 sections, vellum theme, max-w-[680px] reading width, Cormorant headers / Lora body. Effective 10 May 2026 v1.0. ⚠️ TEMPLATE, lawyer review pending.
- `app/legal/privacy/page.tsx` — **NEW 2026-05-10 (PR #28).** Server component, 121 lines. 13 sections, GDPR-aware (Article 6 legal basis mapping, processors table with SCC reference, full GDPR rights enumeration, retention table, EU/US data flow disclosure). ⚠️ TEMPLATE, lawyer review pending.
- `app/app/dashboard/page.tsx` — **DOES NOT EXIST** — currently 404s after auth (when user has accepted disclaimer), blocks UX completion. Plan B path priority #2 if reconsidered.
- `middleware.ts` — protects `/app/*`, `/admin/*`, redirects `/login`, `/register` (legacy refs to deleted routes — flag #2)
- `components/ui/BronzeDivider.tsx` — first production consumer landed 2026-05-10 at `/auth/disclaimer`. API: `width?: number` (default 80), `className?: string`. Next earmarked consumers per source comment: B1 Welcome, F4 Weekly Letter.

---

## 6.1 Schema delta 2026-05-10 (disclaimer tables — additive only)

`alembic_version` advanced from `002_otp_codes` → `003_disclaimer_acceptances`. Two new tables added to `public` schema:

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

**Seed data applied** in `003_disclaimer_acceptances.py` migration:
- `version_string = '1.0'`
- `age_copy = "I am 18 years or older."`
- `positioning_copy = "I understand Great Minds is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional."`

**RLS state:** both new tables created with RLS DISABLED matching existing 13-table convention. Mitigated by FastAPI gateway. Pre-launch RLS audit remains P0 (§10 below).

**Production data state (2026-05-10 verification):** `disclaimer_versions = 1 row` (v1.0 seed), `disclaimer_acceptances = 1 row` (founder's acceptance from preview testing).

### ORM models (`apps/api/models/__init__.py`)

Appended after existing models in single-file flat layout:

```python
class DisclaimerVersion(Base):
    __tablename__ = "disclaimer_versions"
    # id, version_string (unique), age_copy, positioning_copy, effective_at
    acceptances: relationship("DisclaimerAcceptance", back_populates="version")

class DisclaimerAcceptance(Base):
    __tablename__ = "disclaimer_acceptances"
    # id (UUID), user_id (FK → users, CASCADE), version_id (FK → disclaimer_versions),
    # accepted_at, locale, confirmed_age_18, confirmed_non_therapy,
    # ip_address (INET), user_agent (Text)
    version: relationship("DisclaimerVersion", back_populates="acceptances")
    __table_args__ = (UniqueConstraint(...), Index(...))
```

Imports added: `INET` from `sqlalchemy.dialects.postgresql`; `UniqueConstraint`, `Index` from `sqlalchemy`.

### Pydantic schemas (`apps/api/schemas/__init__.py`)

Appended after `Subscription`:

```python
class DisclaimerAcceptRequest(BaseModel):
    confirmed_age_18: bool
    confirmed_non_therapy: bool
    locale: Optional[str] = "en"

class DisclaimerAcceptOut(BaseModel):
    accepted_at: datetime
    version_string: str

class DisclaimerCurrentOut(BaseModel):
    version_string: str
    age_copy: str
    positioning_copy: str
```

`UserOut` extended with `needs_disclaimer: bool = False`. Default `False` propagates safely through `TokenResponse`. Computed-true value applied in auth router endpoints (`model_copy(update={"needs_disclaimer": ...})`).

---

## 7. Section 5.7 brain (`apps/api/philosopher_brain/`)

Unchanged from v5. ✅ Directory exists in repo as of 2026-05-02 commit `3832ec4` (PR #5).

| File | Status |
|---|---|
| `personas/socrates.yaml` | ✅ Phase 3 source PR #7 |
| `personas/nietzsche.yaml` | ✅ Present (NOT in production registry — see §10) |
| `personas/freud.yaml` | ✅ Phase 3 source PR #9 |
| `personas/jung.yaml` | ✅ Phase 3 source PR #10 |
| `personas/epictetus.yaml` | ✅ Phase 3 source PR #8 |
| `personas/de_beauvoir.yaml` | ✅ Phase 3 source PR #11 |
| `personas/marcus_aurelius.yaml` | ✅ Authored 2026-05-03; Phase 3 source PR #12 |
| `prompts/master_system_prompt.md` | ✅ Design source — runtime uses `apps/api/prompts/system_base.jinja2` |
| `maps/modern_phenomenology.json` | ✅ 78 entries × triggers schema, used by Phase 4 PR Α |
| `maps/universal_forbidden_lexicon.json` | ✅ Used by Phase 2 postprocessing |
| `maps/persona_specific_forbidden.json` | ✅ Phase 3 source for `forbidden_lexicon_persona_specific` field |
| `evals/eval_suite_spec.md` | ✅ Design source for Phase 6 |
| `evals/ten_modern_problems.json` | ✅ Present |

---

## 8. What's pending — priority order

> **AUTHORITATIVE source for current priorities:** `IMPLEMENTATION_BACKLOG_v5.md` §17 (or v6 once written). Snapshot below; if conflicts emerge with backlog, backlog wins.

### P0 — 43-screen UI build (per founder decision 2026-05-06, Plan A confirmed 2026-05-10)

Order follows `SCREENS_TRACKING_v4.md` block sequence:

1. **Block A — Authentication** (5 items) — ✅ **CLOSED 2026-05-10: A1 ✅, A2/A3 ✅, A4 ✅, A5 ✅, A6+A7 ✅**
2. **Block B — Onboarding** (6 items: B1–B6) — ❌ NOT STARTED — **next P0, PAUSED awaiting 4 strategic decisions** (see §10 open questions)
3. **Block C — Chat experience** (9 items: C1–C9; some partially live, verify against spec)
4. **Block D — Discovery** (3 items: D1, D2, D3)
5. **Block F — Reflection** (5 items: F1, F2, F3, F4, F6)
6. **Block H — Subscription & Billing** (7 items: H1, H2, H3, H4, H4b, H5, H6)
7. **Block I — Account & Settings** (6 items: I1, I2, I3, I4, I5, I6)
8. **Block J — Empty/error states** (4 items: J1, J2, J3, J5)

Total: 43 effective specced screens (45 line items because A2/A3 and A6/A7 are merged screens). **5 of 5 Block A items live; 40 line items remaining.**

### P0 — Plan B alternative path (mentor-recommended interrupt)

Per `HANDOFF_BRIEF_v6.md` §17.2.5 — pending founder decision:

1. **Vercel disconnect** (~5 min) — removes CI noise + autocomplete confusion
2. **`/app/dashboard` placeholder page** (~30-60 min) — completes auth UX loop, unblocks the post-verify 404
3. **Minimal C-block conversation experience** — proves product to first user
4. **Free tier limit + Stripe paywall trigger**
5. **Soft launch** — 5-10 testers, validate willingness-to-pay
6. **Return to remaining Block B/D/F/H/I/J screens armed with paying-user feedback**

### P0 — Parallel & post-UI work

9. **Stripe wiring** — calendar-gated until 2026-05-11; can start in parallel once Block H exists in placeholder form
10. **Legal copy** — Terms, Privacy Policy, disclaimer (parallelizable with UI)
11. **Email infrastructure verification** — Resend domain verification for `thegreatminds.app` blocks public launch (current setup only sends reliably to founder email)
12. **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation
13. **DNS configuration for `thegreatminds.app`** — domain registered 2026-05-07; not configured
14. **Production smoke test** — after UI complete (or after soft launch if Plan B), verify 8 closed Phase 4 stabilization items + auth pipeline + flag state
15. **UAT mixed-group** — 3-5 testers (close + acquaintances + strangers); ≥2/5 spontaneous "I'd pay" criterion
16. **Public launch** — web/PWA only

### Reclassified post-launch (per 2026-05-06 founder decision)

- **Phase 5** (Register architecture + UI chips + classifier) → **P3 post-feedback**
- **Phase 6** (Eval suite + CI) → **P1 post-revenue**
- **Phase 4 PR Β** (Marcus shading content, 33 strings) → **P3 post-launch**
- **Native app submission** (iOS App Store, Google Play) → **v2**

### P1+ — Continuity, refinements, post-launch UX, technical debt

See `IMPLEMENTATION_BACKLOG_v5.md` §13 (P1–P4 backlog).

---

## 9. MANUAL — Recent decisions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

- **2026-05-10 — Block A completion session (5/5 line items closed).** 6 production-merged PRs across ~7 hours of focused work with rigorous STOP-gate discipline, zero rollbacks:

  - **PR #22** — Initial A4 trouble-accessing-email page (`apps/web/app/auth/trouble/page.tsx`) + link insertion in `/auth/verify`. Single Option card with "Contact support" CTA, mailto: handler. New env var `NEXT_PUBLIC_SUPPORT_EMAIL` set in Netlify (placeholder `nckoutras@gmail.com` until real `support@` mailbox).
  - **PR #23** — Two follow-up A4 fixes squashed: (1) `<button>+window.location.href` → `<a href="mailto:...">` anchor (Chrome incognito redirected programmatic mailto to Google search; founder verified mailto unreliable on Windows machine due to no default mail handler — accepted as Chrome-config edge case); (2) Reframed Option card from active CTA to muted `bg-linen` future-state placeholder ("Try a different sign-in method — Apple and Google sign-in coming soon"). A small follow-up PR re-applied `text-center` on inner `max-w-[380px]` container after orphaned commit was lost in squash. Lesson codified as operating principle #13 (`IMPLEMENTATION_BACKLOG_v7.md` §16.A): spec word "centered" means BOTH layout-centered AND text-aligned-center.
  - **PR #24 (commit `acb910c`)** — alembic migration `003_disclaimer_acceptances` creating `disclaimer_versions` + `disclaimer_acceptances` tables. Seeded `disclaimer_versions` with v1.0 copy. Verified live via Supabase MCP. `alembic_version` advanced `002_otp_codes` → `003_disclaimer_acceptances` cleanly on container start.
  - **PR #25 (commit `4941296`, squashed `8667778`)** — backend endpoint chain: new `apps/api/services/disclaimer_service.py` (module-level functions matching `otp_service.py` convention), new `apps/api/routers/disclaimer.py` (`GET /disclaimer/current` public + `POST /disclaimer/accept` auth-required), ORM models in `models/__init__.py`, Pydantic schemas in `schemas/__init__.py` (+`needs_disclaimer` on `UserOut`), all 4 auth response paths in `auth.py` extended with `needs_disclaimer` computation, router registered in `main.py`.
  - **PR #26 (commit `614dc51`, squashed `17c48a6`)** — frontend page + routing: new `app/auth/disclaimer/page.tsx` (172 lines) with BronzeDivider ornament, centered hero, 2 stacked checkbox cards, auth guard, fetch/submit logic. `lib/api.ts` extended with 3 types + 2 methods. `/auth/verify/page.tsx` extended with 4-line conditional routing.
  - **End-to-end verified live in production:** founder accepted disclaimer, row inserted in `disclaimer_acceptances` for user `nckoutras@gmail.com` with all audit fields populated (locale='en', both flags true, IP 94.64.188.99, Chrome on Windows UA, accepted_at 2026-05-10 19:53:29 UTC). Subsequent OTP logins correctly skip disclaimer (idempotency + version check working as designed, verified 2x in incognito).
  - **PR #28** — Template Terms of Service + Privacy Policy at `/legal/terms` and `/legal/privacy` (Server Components, 16 + 13 sections, GDPR-aware). Fixed `'#'` fallback bug where clicking Terms/Privacy in auth footers caused page refresh back to OTP screen. ⚠️ Template only — lawyer review tracked as P0 in `IMPLEMENTATION_BACKLOG_v7.md` §2.1.C launch readiness.
  - **PR #27 closed without merge** — earlier failed-push attempt at legal pages; refs/pull/27/head ref persisted server-side after branch was auto-deleted. Final PR for legal pages landed as #28 after re-push.
  - **Vercel disconnect — RESOLVED.** Founder deleted `thinkalike.vercel.app` project via Vercel dashboard; GitHub integration cleanup confirmed. Production canonical exclusively Netlify.
  - **OTP rate limiter — CONFIRMED WORKING** (informational). Founder hit `429 Too Many Requests` on `/auth/otp/request` after 5 requests in 6 minutes. Document the actual limits (per-email, per-IP, per-day) in §C of next regenerated PROJECT_STATE for visibility.
  - **Founder confirmed Plan A path is active** (43-screen sequential build, A→B→C→D→F→H→I→J). Plan B (minimum-to-revenue interrupt) preserved as alternative but not active. Mentor pushback held twice during session against starting Block B before legal pages PR was open/tested/merged — discipline pattern codified as operating principle #14 (`IMPLEMENTATION_BACKLOG_v7.md` §16.A): complete PR cycles before queuing new work. Compound-risk avoidance.

- **2026-05-09 evening / overnight** — **Block A frontend completion + alembic plumbing fix.** Three PRs landed in sequence over a single ~7-hour session (with 3-hour sleep break in middle):

  - **`fix/alembic-versions-layout`** (squash merge): root cause of alembic discovery failure was that `001_initial.py` and `002_otp_codes.py` lived flat in `apps/api/db/migrations/`. Alembic looks in `<script_location>/versions/` by default. Files moved into `versions/` subdirectory; alembic_version stamped to `'002_otp_codes'` via direct SQL through Supabase MCP to align DB state with code state. Mid-flight deployment failure caught: stamp had been applied before code was deployed, causing next container restart to crash with "Can't locate revision". Recovered by `DELETE FROM alembic_version` + manual redeploy. Lesson codified in `HANDOFF_BRIEF_v6.md` §19.8.

  - **PR #20 `feat(web): A5 verify UI`** + 2 prerender hotfixes: A5 implementation mirrored A2/A3 verbatim for layout/fonts/colors. Two failed Netlify deploys before passing: (1) `useSearchParams()` triggered Next.js prerender failure; added `dynamic = 'force-dynamic'` — still failed; (2) wrapped inner component in `<Suspense fallback={null}>` — passed. Lesson codified in `HANDOFF_BRIEF_v6.md` §19.7.

  - **End-to-end auth pipeline verified live in production**: POST `/auth/otp/request` → 202; email delivered ~5s; POST `/auth/otp/verify` → 200 with JWT; cookie + localStorage + Zustand store all populated correctly. Founder accidentally tested on `thinkalike.vercel.app` instead of `thinkalike.netlify.app` due to browser autocomplete picking the more recently visited domain — both deployments serve identical code so test passed but only by luck. Lesson codified in `HANDOFF_BRIEF_v6.md` §19.9; Vercel disconnect promoted to urgent priority.

  - **Mentor stakes context elevated:** founder shared during this session that Great Minds is being built primarily to support family financial needs, not as a side project. Calibration adjustment recorded in `HANDOFF_BRIEF_v6.md` §23. Mentor recommendation introduced for Plan B (minimum-to-revenue interrupt) as alternative to 2026-05-06 Plan A (43-screen sequence). Founder's call on which path to take in next session.

  - **Discrepancy flagged:** v5 §1, §2, §12 stated Render PostgreSQL `philosopher-db` is the live production DB and Supabase is dormant. Reality on 2026-05-08/09: DATABASE_URL points to Supabase (`aws-0-eu-west-1.pooler.supabase.com:5432/postgres`), Supabase MCP queries return live production data (2 users, 50 conversations, 139 messages, 6 personas, 12 tables). Either an undocumented migration occurred between 2026-05-06 and 2026-05-08, or v5 was incorrect. Founder action: verify and update.

- **2026-05-08** — **Block A backend infrastructure shipped.** PR #18 `feat(api): passwordless OTP endpoints` + Dockerfile alembic-on-boot fix merged. `/auth/otp/request` (202) + `/auth/otp/verify` (200) endpoints with 6-digit hashed+salted code, 10-min expiry, max 5 attempts then locked. Dockerfile CMD updated to `sh -c "alembic upgrade head && exec uvicorn ..."` solving migration deployment for all current and future schema PRs.

  Three external services configured during this session:
  - **Upstash Redis (`philosopher-prod`, eu-west-1, free tier)** provisioned. `REDIS_URL` set in Render env. **Discovery:** existing ARQ background tasks (`extract_memory_task`, `generate_insight_task`, `send_ritual_reminder_task`) had been silently broken in production for unknown duration before this session due to missing REDIS_URL — confirmed fixed when ARQ + APScheduler started cleanly post-deploy.
  - **Resend account** created. RESEND_API_KEY set in Render env. FROM_EMAIL set to `Great Minds <onboarding@resend.dev>` — Resend's test sender, works without verified domain. Acceptable for dev/test where founder is the only intended recipient; **switch to verified domain required before sending to any other recipient**.
  - **Supabase confirmed as live DB** (DATABASE_URL hostname analysis), conflicting with v5 §1/§2/§12 which stated Render PostgreSQL `philosopher-db` is live. Conflict flagged for verification.

  Mentor wavered on Dockerfile vs Web Shell migration approach during planning; final decision was Dockerfile (νοικοκυρεμένη path that fixes migrations forever, vs Web Shell saving 5 minutes today but requiring manual intervention for future schema PRs). Lesson preserved.

- **2026-05-07** — **Setup PR (#13) + Greenfield scaffold (#14) MERGED.** Setup PR (commit `ad24d15`): 11 spec colors + Cormorant Garamond/Lora fonts wired into Tailwind + dark mode dropped (forced light) + BronzeDivider/Spinner primitives + `.glass` utility removed per spec §1.7. Greenfield scaffold (commit `474f081`): 19 legacy frontend files deleted (auth/, admin/, billing/, app/app/, components/billing|chat|persona, AppSidebar) — 2183 deletions. Replaced `apps/web/app/page.tsx` with minimal spec-aware placeholder. Backend integration glue (`apps/web/lib/`: api.ts, apiExt.ts, store.ts, useStream.tsx) and `middleware.ts` kept untouched. Hosting clarified as Netlify (`thinkalike.netlify.app`) — earlier PROJECT_STATE drafts incorrectly stated Vercel. Custom domain `thegreatminds.app` registered by founder same session; DNS + SSL setup deferred to pre-launch.

- **2026-05-06** — **Documentation v5 cycle delivered.** `IMPLEMENTATION_BACKLOG_v5.md` and `HANDOFF_BRIEF_v5.md` produced as full rewrites. Reorganized around 2026-05-06 reality: Phase 4 stabilization closed, 43-screen UI build as next P0, Phase 5 → P3 post-feedback, Phase 6 → P1 post-revenue, web/PWA only for v1.

- **2026-05-06** — **Render PostgreSQL upgraded to paid tier.** `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`) moved from free tier to paid tier. **Status as of 2026-05-09: uncertain** — see 2026-05-09 entry above.

- **2026-05-06** — **UI scope decision REVERSED. Founder elected to build all 43 specced screens before public launch.** Reverses 2026-05-04 "critical UX subset only" compromise. All 43 screens per `SCREENS_TRACKING_v4.md` will ship before launch, in block order A→B→C→D→F→H→I→J. Phase 5 → P3 post-feedback. Phase 6 → P1 post-revenue. Native app submission → v2. v1 launch is web/PWA only. Estimated timeline: ~12-16 weeks to first paying user (vs ~6-7 weeks under prior compromise). Trade-off alternatives preserved in `IMPLEMENTATION_BACKLOG_v5.md` §17.4. **2026-05-09 update:** Plan B alternative (minimum-to-revenue interrupt) re-introduced for founder consideration given stakes context disclosure.

- **2026-05-05 evening** — **Engine-first launch sequence COMPLETE: 7/7 P0 closed in single ~7h session.** 8 ship items closed (Bug #33, Bug #34, items 1.3-1.7, 2.1). New discipline rule: full diffs required for all parameter/schema changes, no grep summaries trusted as caller audit (origin: 1.7 hotfix incident).

- **2026-05-04 evening** — **Section 5.7 Phase 4 PR Α (Modern phenomenology bridge infrastructure) SHIPPED to main.** 5 commits across 6 files. Mid-flight pivot at Step 1: original 6-PR-per-persona plan was wrong because shading data already lives in shared map. Re-planned to 4-PR functional shape. Adversarial cross-model review of triggers (ChatGPT) flagged 81 distinctiveness issues; mentor accepted 71 (88%), rejected 10 with rationale. Time-box honored within ~3 days end-to-end.

- **2026-05-04** — **Engine-first strategy decision.** Founder pushed back on mentor's distribution-first proposal. Engine-first execution chosen. Mentor concession: legitimate when engine is differentiator, founder has demonstrated 2-3 day per phase pace, and Stripe is calendar-blocked anyway. **NOTE 2026-05-06:** Strategy revised — see 2026-05-06 entries above.

- **2026-05-04** — **Phase 3 of Section 5.7 framework SHIPPED in full.** All 6 production personas now have populated 8 Section 5.7 structured fields.

- **2026-05-04** — **Site state verified by founder.** Loads, all 6 personas visible on dashboard (post-is_active fix), navigation works, streaming chat functional, auth flow works (legacy email/password path at this point — passwordless OTP came 2026-05-08), Free/Pro tier filtering works.

- **2026-05-03** — **Marcus Aurelius brain YAML authored from scratch.** Mentor instance authored v1.0, ChatGPT performed adversarial review, mentor accepted ~85% of feedback, produced v1.1, founder approved. Committed as `1c67d22` before Phase 3 PR.

- **2026-05-03** — **Critical hallucination event caught mid-PR-12.** First Step 2 mapping proposal from Claude Code returned values completely unrelated to the Marcus YAML. Cause: long-session context drift; pattern memory of prior 5 PRs instead of reading the actual file. Caught by mentor cross-check. Lessons codified in HANDOFF_BRIEF §19.6.

- **2026-05-03** — **Phase 3 Sub-session 3.2 fully shipped.** PRs #8 (Επίκτητος, `6c55086`), #9 (Σιγμ. Φρόυντ, `491e06f`), #10 (Καρλ Γιουνγκ, `d46d37b`), #11 (Σιμόν ντε Μποβουάρ, `b213838`). Combined with PR #7 Σωκράτη from 3.1, 5 of 6 personas brought into the framework.

- **2026-05-03** — **Three personas were inactive in production DB.** Σωκράτης, Επίκτητος, Σιγμ. Φρόυντ had `is_active=False`. Fixed via direct SQL `UPDATE personas SET is_active=TRUE` from Render Shell. Bug fix in `seed.py` deferred until post-first-payment.

- **2026-05-03** — **HANDOFF_BRIEF_v3 §20 deployment-gap statement was INCORRECT.** Backend has been deployed to Render at `philosopher-api-z9l9.onrender.com` for ~10 days (Service ID `srv-d7ijct6gvqtc739a0pdg`). v3 stated live database was Supabase; v4 corrected to Render PostgreSQL `philosopher-db`. **2026-05-09 reality check:** v4/v5 stated Render PostgreSQL is live; live verification 2026-05-08/09 shows DATABASE_URL points to Supabase. Either v3 was right and v4/v5 were wrong, OR v3 was wrong, v4/v5 right at the time, and a migration to Supabase occurred between 2026-05-06 and 2026-05-08. Founder verification needed.

- **2026-05-03** — **`POSTPROCESSING_ENABLED=true` added explicitly to Render Environment** (philosopher-api Web Service). Prevents silent regression if implicit default changes.

- **2026-05-03** — **Production smoke test of Phase 2/3 pipeline PASSED.** Verified live for socrates after PR #7 merge.

- **2026-05-02** — **Phase 2 (Section 5.7 brevity + forbidden lexicon) COMPLETE + MERGED.** Branch `feat/section-5.7-phase-2`, PR #6, commit `6e2daad`. Buffer-then-stream architecture with feature flag.

- **2026-05-02** — **Brain folder committed to repo (commit `3832ec4` via PR #5).** `philosopher_brain/` (12 files) committed at `apps/api/philosopher_brain/`.

- **2026-05-02** — **Phase 1.5 housekeeping items 1 + 2 COMPLETE (PR #4, commit `1581c76`).** `forbidden_phrases` gap closed; `.gitignore` added.

- **2026-05-02** — **Phase 1 schema extension COMPLETE + MERGED (PR #2, commit `0ade549`).** 8 optional fields + 7 supporting dataclasses. 4 schema corrections vs original v2 spec.

- **2026-04-28** — Verified Section 5.7 framework against existing codebase. Hybrid migration (Option A) chosen.

- **2026-04-28** — Confirmed all 6 personas Python files correct in repo.

- **2026-04-28** — Stripe wiring elevated to P0 ahead of any Section 5.7 work. **NOTE 2026-05-04:** Engine-first strategy decision later supplanted this.

- **2026-04-27** — Section 5.7 framework added to PHILOSOPHER spec.

- **2026-04-26** — `HANDOFF_BRIEF_v1` written.

---

## 10. MANUAL — Current blockers / open questions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

**Open questions:**

- [ ] **Block B onboarding — 4 strategic decisions PENDING founder confirmation** (NEW 2026-05-10). Mentor proposed; founder did not explicitly confirm before session ended. Block B work paused until these are settled:
  1. **B2/B3 answer persistence** — Mentor recommends: persist to backend (new `user_preferences` table) + reactive Zustand state. Trade-off: backend persistence enables retention/segmentation analytics (vital for monetization signal capture per §17.6 stakes context).
  2. **Matching algorithm location** — Mentor recommends: backend-computed (POST `/matches`). Trade-off: centralized logic, easier iteration, can leverage non-exposed persona traits/weights.
  3. **B6 (Pro-locked variant) timing** — Mentor recommends: DEFER until Stripe lands. Trade-off: avoid building paywall UI before payment infra exists; reduces wasted work risk if monetization model changes.
  4. **`user_preferences` schema shape** — Mentor recommends: wide table (1 row per user, columns per question). Trade-off: YAGNI for 2 questions; normalize later if 5+ questions added.
- [ ] **Legal pages lawyer review** (NEW 2026-05-10) — Templates shipped (Terms v1.0 + Privacy v1.0). Greek consumer law specifics, Stripe billing T&Cs, AI-content liability scope all unchecked. **Pre-public-launch P0 blocker.**
- [ ] **A6+A7 disclaimer endpoint integration tests** (NEW 2026-05-10) — currently shipped without tests for speed (founder decision). GDPR audit trail risk — without tests, silent failures in acceptance recording could create legal exposure. ~30 min effort to add 2-3 happy-path + idempotency tests. P1.
- [ ] **A6+A7 lazy-load monitoring** (NEW 2026-05-10) — `acceptance.accepted_at` accessed in router after service `await db.commit()`. If AsyncSession is configured `expire_on_commit=True`, lazy refresh in async context CAN fail. Monitor for `MissingGreenlet` errors in Render logs. If observed, add explicit `await db.refresh(record)` in `disclaimer_service.accept()`. Currently working in production. P1.
- [ ] **Database reality check** (NEW 2026-05-09) — v5 §1/§2/§12 stated Render PostgreSQL `philosopher-db` is live and Supabase is dormant. Verification 2026-05-08/09 shows reverse: DATABASE_URL points to Supabase, Supabase contains all production data. Founder action: confirm whether (a) undocumented migration to Supabase occurred between 2026-05-06 and 2026-05-08, (b) v5 was incorrect about which DB was live, or (c) Render `philosopher-db` is still active in some capacity. Update §1, §2, §12 with reality.
- [ ] **gh CLI installation on founder's Windows machine** (NEW 2026-05-10) — `winget install --id GitHub.cli` would eliminate manual GitHub PR opening flow (currently founder copy-pastes title + body into compare URL each time). One-time install reduces friction across all future PRs. P4.
- [ ] **API web service plan upgrade** — paid (~$7/month) for production-ready performance, or stay on free tier? Mentor recommendation: upgrade now. DB question pending (see Database reality check above).
- [ ] **Resend domain verification for `thegreatminds.app`** — currently using `onboarding@resend.dev` test sender; works only for sends to founder's email. Required before sending OTP to any other user. Dependent on DNS setup (below). P0 launch blocker.
- [ ] **DNS setup for `thegreatminds.app`** — domain registered 2026-05-07; needs DNS records pointing to Netlify + SSL activation + Resend verification records. Founder action, ~10 min in Netlify dashboard + DNS provider. Not launch blocker but blocks both branding consistency AND Resend verification.
- [ ] **RLS audit** — all 15 public tables in Supabase have RLS DISABLED (was 13, +2 new disclaimer tables 2026-05-10 follow same convention). Currently mitigated by frontend going through FastAPI exclusively (Supabase anon key not used in client). Pre-launch blocker for any scenario where direct Supabase access from frontend is added. Should be addressed before public launch with real users.
- [ ] **A4 mailto: visible support email fallback** (NEW 2026-05-10) — when real `support@thegreatminds.app` mailbox exists, swap placeholder `nckoutras@gmail.com` from `NEXT_PUBLIC_SUPPORT_EMAIL`. P1.
- [ ] **A5 polish** — per-digit OTP boxes (currently single 6-digit input), expiry countdown, resend cooldown indicator. Founder explicitly mentioned wanting per-digit boxes "eventually". MVP form is functional. P3.
- [ ] **Stale branch cleanup** (NEW 2026-05-10) — 6 merged branches from this session, mostly auto-deleted on merge. `fix/a4-mailto-and-card-reframe` from yesterday still lingering. Periodic batch cleanup (every 1-2 weeks) recommended. P4.
- [ ] **Legal pages `target="_blank"` link hardening** (NEW 2026-05-10) — Auth footers use `target="_blank"` on Terms/Privacy links without `rel="noopener noreferrer"`. Modern browsers default to noopener, but explicit is best practice. P4.
- [ ] User validation test: send working persona experience to 5 humans (UAT mixed-group), ≥2/5 spontaneous "I'd pay" criterion before public launch. Per `IMPLEMENTATION_BACKLOG_v7.md` §17.2.
- [ ] Decide whether Nietzsche becomes a 7th persona, OR whether the brain YAML is permanently retired. Frontend landing display already removed via `c49c3cd` (Option A). Backend YAML retained for v2.
- [ ] Decide pricing for launch: €9.99/mo + €119.99/yr per `IMPLEMENTATION_BACKLOG_v7.md` §5.6 baseline, or different number? **NEEDED before H1 pricing page implementation in Block H of UI build.**
- [ ] Greek source text editions: which translations are legally clear for ingestion in RAG corpus?
- [ ] **Brand consolidation** — currently fragmented across: repo name `Philosopher`, code identifiers `philosopher.app` / `philosopher-api`, frontend domain `thinkalike.netlify.app`, target domain `thegreatminds.app`, page titles "Philosopher — Your Reflective Companion", email FROM "Great Minds". To resolve once DNS lands and Resend verification completes. Blocks paid launch (trust signal); not blocking dev work.
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** — was true during 14-test session 2026-05-04/05; current state in Render env vars unverified.
- [ ] **Untracked files decision** (NEW 2026-05-10) — `apps/api/scripts/` still untracked across many sessions. Decide: gitignore, commit, or delete.

**Closed:**

- [x] **CLOSED 2026-05-10** — **Block A complete: A1 ✅ (PR #15), A2/A3 ✅ (PR #17), A4 ✅ (PRs #22, #23, text-center fix), A5 ✅ (PR #20), A6+A7 ✅ (PRs #24, #25, #26).** End-to-end verified with real production acceptance row.
- [x] **CLOSED 2026-05-10** — **Vercel project disconnect.** Founder deleted `thinkalike.vercel.app` project via Vercel dashboard.
- [x] **CLOSED 2026-05-10** — **Plan A vs Plan B path decision.** Founder confirmed Plan A path (43-screen sequential build) is active. Plan B preserved as alternative but not active.
- [x] **CLOSED 2026-05-10** — **Legal pages live** at `/legal/terms` and `/legal/privacy` (PR #28). Fixed `'#'` fallback bug in auth footers. ⚠️ Templates only — lawyer review still pending (re-opened as separate P0 above).
- [x] **CLOSED 2026-05-10** — **A4 status verification.** A4 was a genuinely separate screen; built and closed this session.
- [x] **CLOSED 2026-05-10** — **A6/A7 boundary.** Decided to ship as Block A item (combined disclaimer screen) rather than punt to Block B.
- [x] **CLOSED 2026-05-09** — Block A authentication: A1 ✅ (PR #15), A2/A3 ✅ (PR #17), A5 ✅ (PR #20). End-to-end auth pipeline verified live. (A4 + A6/A7 still pending at v6 baseline — closed 2026-05-10.)
- [x] **CLOSED 2026-05-09** — Alembic plumbing: migration files moved to `versions/` subdirectory, alembic_version stamped at `'002_otp_codes'`. Future schema migrations will execute correctly on container start.
- [x] **CLOSED 2026-05-08** — Backend OTP infrastructure: Resend integration, Upstash Redis, FROM_EMAIL configured.
- [x] **CLOSED 2026-05-08** — Silent breakage of ARQ background tasks (memory extraction, insights, ritual reminders) due to missing REDIS_URL. Fixed by Upstash provisioning + REDIS_URL env var.
- [x] **CLOSED 2026-05-07** — Frontend hosting clarified: Netlify (`thinkalike.netlify.app`), not Vercel.
- [x] **CLOSED 2026-05-07** — Greenfield rewrite vs in-place refactor: greenfield chosen.
- [x] **CLOSED 2026-05-06** — Phase 4 PR Β (Marcus shading) timing: deferred to P3 post-launch.
- [x] **CLOSED 2026-05-05** — Phase 4 production smoke test timing: 14-test session verified bridge active. Formal post-engine-first smoke test deferred to post-43-screen-UI-build.

**Blockers:**

- **Stripe account paused** (cooldown ~10 days as of 2026-05-01). Resolves itself ~2026-05-11. Calendar blocker, not code.
- All other blockers are decision-pending, not technical.

**Phase 1.5 housekeeping list — STATUS:**

✅ **Item 1: DONE 2026-05-02** — `forbidden_phrases` gap fixed across 3 personas.

✅ **Item 2: DONE 2026-05-02** — `.gitignore` created.

⏳ **Item 3: pending — needs decision.** Local test environment broken: `test_billing.py`, `test_prompts.py`, `test_safety.py` un-runnable due to missing packages (`stripe`, `jinja2`, `pydantic_settings`).

⏳ **Item 4: pending — needs decision.** `make state` infrastructure mismatch. Workaround: manual §9 entries written by mentor instance per session.

⏳ **Item 5: pending.** Two unzipped `Philosopher` folders on Desktop (legacy from earlier setup). Cleanup when convenient.

**Phase 4 follow-up items (NEW 2026-05-04 evening) — tracked in IMPLEMENTATION_BACKLOG §8.2:**

⏳ **#26 Runtime template doesn't render Phase 1-3 structured fields** (P3) — not a launch blocker.

⏳ **#27 Explicit priority hints for overlapping phenomenology mappings** (P3) — edge case in classifier.

⏳ **#28 Modern-term-leak post-check** (P2/P3) — defer to Phase 6 eval suite.

⏳ **#29 Local Python env missing API dependencies** (P4) — overlaps with housekeeping #3.

**Pre-existing untracked files (status: gitignore vs commit decision pending):**

- `apps/api/scripts/`
- `docs/PERSONA_EXPANSION_ROADMAP_v1.md`

---

## 11. MANUAL — How to refresh this file (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

1. From repo root: `make state`
2. Claude Code reads the repo and rewrites this file
3. Manual sections (9, 10, 11) are preserved — only auto-sections are updated
4. Review the diff: `git diff docs/PROJECT_STATE.md`
5. Commit: `git add docs/PROJECT_STATE.md && git commit -m "chore: update state"`
6. Push: `git push`
7. Re-upload to Claude.ai Project Knowledge:
   - Open Claude.ai → Philosopher Project → Project Knowledge
   - Delete old `PROJECT_STATE_v6.md` (now `PROJECT_STATE_v7.md`)
   - Upload `docs/PROJECT_STATE.md` (the just-regenerated one)

**Frequency:** Before opening a new technical thread on Claude.ai. 2-3 times per week is typical.

**When NOT to run `make state`:** Right before a commit (it'll create extra noise in git log). Run after the commit, then commit the state update separately.

**STATUS NOTE 2026-05-04:** `make state` infrastructure currently broken (uses `claude` CLI; founder uses VS Code extension). Manual §9 entries written by mentor instance per session as workaround. See §10 housekeeping item #4. Fix deferred until post-first-payment.

---

## 12. MANUAL — Live URLs (preserved across regenerations)

- Repo: https://github.com/Nckoutras/Philosopher
- **Frontend live (canonical):** https://thinkalike.netlify.app
- Frontend planned domain: https://thegreatminds.app (DNS + SSL setup pending — registered 2026-05-07)
- ~~Frontend legacy still serving: https://thinkalike.vercel.app~~ — **DISCONNECTED 2026-05-10**
- Backend live: https://philosopher-api-z9l9.onrender.com
- Backend health: https://philosopher-api-z9l9.onrender.com/health
- **Netlify project:** https://app.netlify.com/sites/thinkalike
- Render API service: https://dashboard.render.com (philosopher-api, Service ID `srv-d7ijct6gvqtc739a0pdg`)
- **Production database (verified live 2026-05-08/09):** Supabase project https://supabase.com/dashboard/project/plecolxlzshkfvybszgs (eu-west-1)
- Render PostgreSQL `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`) — **STATUS UNCERTAIN as of 2026-05-10:** v5 listed this as production DB (paid tier as of 2026-05-06), but reality check shows DATABASE_URL points to Supabase. Verify whether decommissioned, demoted to staging, or stale info in v5.
- **Upstash Redis (NEW 2026-05-08):** https://console.upstash.com/redis (database: `philosopher-prod`, eu-west-1, free tier, endpoint `feasible-mammal-118733.upstash.io:6379`)
- **Resend (NEW 2026-05-08):** https://resend.com (API key `philosopher-prod`; account email `nckoutras@gmail.com`; FROM_EMAIL = `Great Minds <onboarding@resend.dev>`; **domain verification for `thegreatminds.app` pending** — required before sending to non-founder recipients)

---

**End of PROJECT_STATE v7.** Authoritative as of 2026-05-10 session close.
