# PHILOSOPHER — Project State v16

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v16 = v15 baseline (2026-06-01) + 2026-06-01 session delta (The Council shipped end-to-end: C5–C7c; migrations 019_create_council + 020_create_council_saves; 3 Council endpoints; boardroom screen live; Mirror INTRO_HOLD updated; share renderer shared).**
>
> **Generated:** 2026-06-01 (v16 rotation)
>
> **Last updated:** 2026-06-01

> **v16 conflict resolution rule:** Where v16 conflicts with v15, v16 wins. Production reality always wins over docs.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive — do not write to it. All Render services must point to Oregon.**

## v16 Session Delta (2026-06-01)

> v16 = v15 baseline + The Council shipped end-to-end (C5–C7c). Where v16 conflicts with v15, v16 wins.

**Shipped (all merged to main or PR open, C5–C7c):**

- **The Council** — 4-member philosophical council (Machiavelli, Epictetus, Freud, de Beauvoir); 4 sequential verdicts + app-voice synthesis; SSE stream end-to-end live & verified.
  - `council_cases` + `council_sessions` + `council_responses` tables (migration 019).
  - `council_saves` table (migration 020): id, user_id FK CASCADE, session_id FK CASCADE, saved_at, deleted_at, UNIQUE(user_id, session_id), index `ix_council_saves_user`.
  - **3 new endpoints:** `POST /council` (SSE stream; Pro-gated; weekly rate-limit per source), `POST+DELETE /council/{session_id}/save` (optimistic save toggle), `POST /council/{session_id}/share` (PNG image; shared counter with line shares, 3/90 days free tier).
  - `done` SSE event carries `case_id` + `session_id`.
  - Council screen `apps/web/app/app/council/page.tsx`: boardroom.webp full-bg + vellum veil (`VEIL_OPACITY=0.75`) + readability scrim; full bench (4 from start: faint→sequential light; 66px circle, flex-nowrap); rAF word-reveal (`INTRO_HOLD=2100`, `WORD_STAGGER=105`, `SENTENCE_PAUSE=480`, `SEAT_LIGHT=950`, `MEMBER_GAP=1500`); auto-scroll (pause-on-scroll guard); idle title "Bring your matter before them"; mirror-entry prefill label; synthesis card with Save/Share buttons; `ROSTER` const; `council.module.css` `.word` keyframe; lit bench names `text-ink`; verdict + synthesis body `font-medium`.
  - Council Save: `saveCouncil`/`unsaveCouncil` in `api.ts`; optimistic toggle in page state.
  - Council Share: `services/image_service.py` refactored — shared Pillow core `_render_share_canvas`; `generate_council_share_image` (synthesis text, no portrait, `attribution="— THE COUNCIL"`); reflections path byte-identical (no output change); `SharePreviewModal` generalized with `kind: 'line' | 'council'` discriminant; `shareCouncil` in `api.ts`.
- **Mirror animated** — `apps/web/app/app/mirror/page.tsx`: `INTRO_HOLD` updated to 2100 (was 1100); CTA border 1.5px.

**Supersedes prior facts:**
- `alembic_version` is now **`020_create_council_saves`** (was `018_user_mirror_host`). Two new migrations since v15: `019_create_council` + `020_create_council_saves`.
- The Council: was Phase 5 / parked → now **🟢 SHIPPED end-to-end**.
- "Take it to the Council" CTA on Mirror page now navigates to live `/app/council`.
- `SharePreviewModal` now accepts `kind` prop; existing `kind='line'` call sites unaffected.
- `image_service.py` refactored: `_compose_canvas` → `_render_share_canvas` (keyword-only params; `attribution`, `portrait_path`, `intro_text`, `persona_initial`); reflections output byte-identical.

**Locked decisions (v16):**
- Council roster is fixed at 4: Machiavelli, Epictetus, Freud, de Beauvoir. `ROSTER` const in page.tsx.
- Council is Pro-gated (`plan not in ("pro", "premium")` → 403 upgrade_required).
- Council weekly rate-limit: 1 session per source per week (admins bypass for testing).
- Share rate-limit counter is SHARED between line shares and Council shares (`share_screenshot:{user.id}`, 3/90-day window).

---

## v15 Session Delta (2026-06-01)

> v15 = v14 baseline + Mirror feature shipped. Where v15 conflicts with v14, v15 wins.

**Shipped (all squash-merged to main, PRs #166–#173):**

- **The Mirror** — weekly "said → meant" reflection artifact, end-to-end live & verified.
  - `mirrors` table (migration 017): `uq_mirrors_user_period_kind` UNIQUE(user_id, period_start, kind); `kind` ∈ {weekly, preview}; `status` ∈ {generated, empty, suppressed}; `payload` JSONB; `ring_true` fields.
  - `users.mirror_host_slug VARCHAR(100) NULL` (migration 018).
  - `generate_weekly_mirror_task` in worker — idempotent; `period_start` normalised to midnight UTC; skip-if-exists.
  - Payload shape: `{thread, moments}`. MIRROR_PROMPT LOCKED: `said` = charged kernel (one line); `thread` = second-person closing reflection; ≥1 moment must honour; universal verdict-guard (lens not verdict; never diagnose). Tuning via ring-true data only.
  - **MIRROR_PROMPT is a separate path from `prompt_builder.py` (chat).** The verdict-guard affects the Mirror only — normal persona chats are unaffected.
  - 6 APScheduler cron jobs (was 4): `dispatch_weekly_mirrors` (Mon 06:00 UTC, ≥5 user messages / 7 days, per-user host) + `dispatch_preview_mirrors` (hourly, ≥3 active convos / 72 h AND no existing mirror, host = carl_jung).
  - Eligible hosts (locked): Jung (default), Lao Tzu, Marcus Aurelius — via `config.mirror_capable=true` (additive JSONB flag). Extensible: new host = one `UPDATE`. Excluded: Machiavelli, Wilde, Socrates, Epictetus, Freud, de Beauvoir.
  - Host picker live — tappable "Through {host}" header → bottom sheet. Verified end-to-end.

**PRE-LAUNCH BLOCKER added:**
- 🔴 `BETA_GRANT_PRO_TO_ALL=true` is ENABLED — must be disabled before any Stripe transaction is accepted. Requires TD-11 (tier resolution refactor) first.

---

## v14 Session Delta (2026-05-29)

See `PROJECT_STATE_v15.md §v14 Session Delta` for full detail (C9 PR-B "Bring another mind", cross-mind awareness, typography PR-F).

---

## v14 Addendum — Voice Overhaul (2026-05-30)

See `PROJECT_STATE_v15.md §v14 Addendum — Voice Overhaul` for full detail. All 9 personas voice-tightened; check_brevity live; ending-variation rule; Socrates elenchus cycle upgraded.

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
| Database | PostgreSQL 17 (Supabase). **Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2) — CONFIRMED LIVE.** Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy / inactive. |
| Queue/Cache | Redis (Upstash) + ARQ + APScheduler |
| LLM | Anthropic Claude — wired and live for chat + Council synthesis |
| Embeddings | OpenAI text-embedding-3-small (2476 chunks live across 7 personas) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage; Google OAuth dormant (PR4k) |
| Billing | Stripe (sandbox — checkout + portal + webhook live; PR1 #77) |
| Email | Resend (free tier, test sender — custom domain in progress) |
| Analytics | PostHog (configured, unused) |
| Image rendering | Pillow (PIL) — server-side PNG generation for share cards (reflections + council) |

### Hosting

Unchanged from v15. Netlify (canonical), Render (API + worker, paid tier), Supabase Oregon.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-06-01** — The Council C5–C7c
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3-5 fresh users still pending)

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v12.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v12.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

Real-time streaming architecture shipped (PR-A / Bug #4). See §6.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; €14.90/mo + €149/yr; PR1 #77)
- **BETA bypass active:** Yes — `BETA_GRANT_PRO_TO_ALL=true` in Render env (PR4j). All users treated as Pro during cold beta.
- **Paywall system wired:** Yes
- **Google OAuth:** Dormant
- **Rituals tab:** Live (PR4o) — 4 ritual cards shown; **Mirror ✅ SHIPPED** (PRs #166–#173); **Council ✅ SHIPPED** (C5–C7c); Counterview + Weekly Reading are placeholder-locked; Letter to Future Self is functional (ARQ delivery not yet wired).
- **Share v3:** Live (PR4ag1); **Council share:** Live (C7c)
- **Greeting personalization:** Live (PR-D #129)
- **Name capture prompt:** Live (PR-D2 #130)

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v12.

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli

**Council roster (fixed):** Machiavelli, Epictetus, Freud, de Beauvoir — all Pro-tier personas.

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001–014 | See v12/v11/v9 for full history | Pre-v12 | — |
| **015** | **FK indexes: 20 btree indexes on FK columns across 10 tables** | **2026-05-26** | **L1 / #124** |
| **016** | **messages.persona_id nullable FK → personas.id + ix_messages_persona_id** | **2026-05-29** | **PR-B / 71ce6e3** |
| **017** | **mirrors table: uq_mirrors_user_period_kind UNIQUE(user_id, period_start, kind); kind ∈ {weekly,preview}; status ∈ {generated,empty,suppressed}; payload JSONB; ring_true fields** | **2026-06-01** | **Mirror / #168** |
| **018** | **users.mirror_host_slug VARCHAR(100) NULL** | **2026-06-01** | **Mirror / #171** |
| **019** | **council_cases (id, user_id FK CASCADE, mirror_id FK SET NULL, status, session_count, created_at, closed_at) + council_sessions (id, case_id FK CASCADE, session_number, input_text, synthesis TEXT NULL, status, created_at) + council_responses (id, session_id FK CASCADE, persona_slug VARCHAR(100) NULL, position, verdict TEXT, quote TEXT NULL, quote_source, created_at) + UNIQUE(case_id, session_number) + indexes** | **2026-06-01** | **Council C5–C7b** |
| **020** | **council_saves (id UUID PK, user_id FK CASCADE, session_id FK CASCADE, saved_at, deleted_at NULL) + UNIQUE(user_id, session_id) + ix_council_saves_user** | **2026-06-01** | **Council C7b** |

**alembic_version = `020_create_council_saves`** (migration 020 added 2026-06-01, Council save storage)

### Oregon region migration — CONFIRMED LIVE

**Live DB = Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy, inactive.**

Oregon migration status (confirmed as of 2026-06-01):
- Schema: ✅ COMPLETE (through migration 020)
- Reference data: ✅ COMPLETE
- User/app data: ✅ CONFIRMED LIVE
- source_chunks: separate task — re-ingest via existing OpenAI embeddings script (TD-22); status unconfirmed post-switch
- DATABASE_URL switch: ✅ CONFIRMED — pointing to Oregon pooler

### Live database state (2026-06-01)

```
alembic_version:        020_create_council_saves ✓
users count:            ~2-3 (founder + test accounts; no organic users yet)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          87+ (testing adds more)
messages:               227+ (testing adds more)
source_chunks:          2476 chunks across 7 personas
mirrors:                rows from preview cron
council_cases:          NEW table (019)
council_sessions:       NEW table (019)
council_responses:      NEW table (019)
council_saves:          NEW table (020)
```

### RLS state

**RLS DISABLED on all public tables.** Unchanged from v12.

---

## 5. Backend endpoints

All v15 endpoints apply. Additions since v15:

**POST /api/v1/council** — Convene the council (SSE stream)
- Auth: `Depends(get_current_user_plan)`
- Pro-gate: plan not in (pro, premium) → 403 `upgrade_required`
- Rate-limit: 1 session per source per week; admins bypass
- Request: `CouncilCreate` — `{matter: str (max 600), source: str (direct|mirror), mirror_id: UUID | null}`
- SSE events: `convening`, `member` (slug, name, position), `chunk` (verdict text), `synthesis_start`, `chunk` (synthesis text), `synthesis_error`, `done` (carries `case_id` + `session_id`), `safety`, `safety_override`, `error`
- `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers on response

**POST /api/v1/council/{session_id}/save** — Save a council session
- Auth: `Depends(get_current_user_plan)`
- Verifies session belongs to a case owned by the user
- Upsert: re-activates soft-deleted save; no-op if already saved
- Returns: `{"saved": true}`

**DELETE /api/v1/council/{session_id}/save** — Unsave a council session
- Auth: `Depends(get_current_user_plan)`
- Soft-delete: sets `council_saves.deleted_at`
- Returns: `{"saved": false}`

**POST /api/v1/council/{session_id}/share** — Generate council share PNG
- Auth: `Depends(get_current_user_plan)`
- Free tier: max 3/90-day rolling window (shared counter with `/share/screenshot`)
- Returns: `image/png` bytes; synthesis text + "— THE COUNCIL" attribution; no portrait circle
- On 429: `{"error_code": "share_limit_reached"}`

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v15. See v15 §6.

---

## 7. Council architecture

### SSE stream (`services/council_service.py`)

- 4-member roster: Machiavelli, Epictetus, Freud, de Beauvoir (Pro-tier personas)
- Sequential: each member's verdict streams as chunks between `member` and implicit close events
- `synthesis_start` event marks transition to app-voice synthesis
- `done` event carries `case_id` + `session_id` for client-side save/share wiring
- DB writes: `council_cases`, `council_sessions`, `council_responses` rows committed on completion

### Share image (`services/image_service.py` — refactored)

`_render_share_canvas(*, quote, attribution, portrait_path, persona_initial, intro_text, annotation, saved_at)` is the shared Pillow drawing core. Two callers:
- `generate_share_image` — reflections path; output byte-identical to pre-refactor
- `generate_council_share_image` — council path; `portrait_path=None`, `persona_initial=None`, `intro_text=None`, `attribution="— THE COUNCIL"`

---

## 8. Persona error messages

All 9 personas have `llm_unavailable` error messages in DB. Unchanged from v12 §7.

---

## 9. LLM provider validation

Unchanged from v12 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 10. Locked decisions

All 18 from v15 remain locked. New locked decisions from 2026-06-01 Council session:

**19. Council roster fixed at 4 (locked)**
- Members: Machiavelli, Epictetus, Freud, de Beauvoir. Encoded as `ROSTER` const in `council/page.tsx`.
- All Pro-tier personas — council is Pro-only during beta (BETA_GRANT_PRO_TO_ALL bypasses for all users).
- Expanding the roster requires `ROSTER` const update + LLM prompt change; no schema change needed.

**20. Share rate-limit counter is shared (locked)**
- `/share/screenshot` (reflections) and `/council/{id}/share` both use key `share_screenshot:{user.id}`.
- Intent: 3 total shares per 90-day window for free users, counting both types.
- If separate counters are desired later: key change only (no schema change).

**21. Council weekly rate-limit per source (locked)**
- 1 council session per source (`direct` or `mirror`) per week.
- Source is stored on `council_cases.source`; used to enforce the weekly cap.
- Admins bypass the rate limit for testing.

---

## 11. Reconciliation history

Unchanged from v12. See v12/v11/v9 §10 for C-RECON-1 through C-RECON-8.

---

## 12. PR4j BETA bypass system

Unchanged from v12 §11. BETA_GRANT_PRO_TO_ALL=true; TD-11 (tier consolidation) required before disabling.

---

## 13. Frontend architecture

### Council screen (`apps/web/app/app/council/page.tsx`)

State machine: `idle` → `intro` (INTRO_HOLD) → `convening` (bench shown) → `session` (verdicts + synthesis) → `done` (Save/Share CTAs). Separate `anim.current` ref drives the rAF loop; `setPhase` only called for React state that triggers renders.

Key constants: `INTRO_HOLD=2100`, `WORD_STAGGER=105`, `SENTENCE_PAUSE=480`, `SEAT_LIGHT=950`, `MEMBER_GAP=1500`, `VEIL_OPACITY=0.75`.

Bench: always 4 portraits; state transitions `pending → lighting → speaking → done` with opacity + ring styling. Name labels: `font-medium text-[11px]`, lit = `text-ink` full opacity.

### SharePreviewModal (`apps/web/components/share/SharePreviewModal.tsx`)

`kind='line'` (default): portrait + persona intro header, download as `reflection.png`.
`kind='council'`: "THE COUNCIL'S READING" eyebrow label, no portrait, download as `council-reading.png`.
All existing call sites pass no `kind` prop → `kind='line'` by default → unaffected.

### Latency topology

Unchanged from v12 §12. DATABASE_URL confirmed Oregon.

---

## 14. Session metrics

### 2026-06-01 session — The Council

| Metric | Value |
|---|---|
| PRs merged | C5 87a9c32 (#182), C6 3149764 (#183), C7a adc2592 (#184), C7b 76340ef (#185), C7c c7d181f (#186) |
| Production regressions | 0 |
| Migrations deployed | 019_create_council, 020_create_council_saves |
| New tables | `council_cases`, `council_sessions`, `council_responses`, `council_saves` |
| New endpoints | POST /council, POST+DELETE /council/{id}/save, POST /council/{id}/share |
| New backend files | `routers/council.py`, `services/council_service.py`, `services/image_service.py` (refactored) |
| New frontend files | `app/app/council/page.tsx` (new), `app/app/council/council.module.css` (new) |
| Modified frontend files | `SharePreviewModal.tsx` (kind discriminant), `api.ts` (shareCouncil, saveCouncil, unsaveCouncil), `mirror/page.tsx` (INTRO_HOLD) |

### Earlier sessions

See v15 §13 for 2026-06-01 Mirror session, 2026-05-28, 2026-05-25-26, 2026-05-21-24 sessions.

---

## 15. Known bugs (active)

### Carried from v15

- **BUG-012** — Zustand hydration race (hard refresh / direct URL on protected routes flashes to /auth). TD-10. PR4ai deferred. Approach requires Netlify preview smoke test.

### Open issues carried from v15

- **OTP-01** — OTP delivery failure for ote.gr (Greek ISP). Workaround: use gmail. Not related to any PR code changes.

### New tech debt logged (v16)

- **mirror.png** — 2.3MB uncompressed PNG in `apps/api/static/personas/` (or static assets). Should be converted to WebP for page load performance.
- **mirror 'said' line-clamp removed** — Mirror page previously clamped long "said" quotes; clamp was removed during polish. Watch for layout issues with unusually long user inputs.
- **Council share card** — currently uses generic Pillow layout (no boardroom bg, no 4-portrait row, no header). Full redesign needed: boardroom background, date header, 4 member thumbnails, centered synthesis text. Requires boardroom.webp + 4 persona portraits copied to `apps/api/static/personas/`.

### No code-introduced regressions in 2026-06-01 Council session.

---

## 16. Environment variables

### Backend (Render)

All v15 vars apply. No new env vars added for Council (uses existing `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`).

See v15 §15 for full list.

### Frontend (Netlify)

Unchanged from v15.

---

## 17. Key file paths (production codebase)

### Backend (apps/api/)

All v15 paths apply. Additions since v15:

- `routers/council.py` — NEW: POST /council, POST+DELETE /council/{id}/save, POST /council/{id}/share
- `services/council_service.py` — NEW: `council_service.stream_council` (SSE stream, verdict + synthesis); `weekly_remaining` rate-limit check
- `services/image_service.py` — REFACTORED: `_render_share_canvas` shared core; `generate_council_share_image` added; `generate_share_image` output byte-identical
- `db/migrations/versions/019_create_council.py` — NEW
- `db/migrations/versions/020_create_council_saves.py` — NEW

### Frontend (apps/web/)

All v15 paths apply. Additions and changes since v15:

- `app/app/council/page.tsx` — NEW: full council screen with rAF animation, bench, verdicts, synthesis, save/share
- `app/app/council/council.module.css` — NEW: `.word` keyframe fade-in animation
- `app/app/mirror/page.tsx` — UPDATED: `INTRO_HOLD` 1100→2100; CTA border 1.5px
- `components/share/SharePreviewModal.tsx` — UPDATED: `kind` discriminant; council variant
- `lib/api.ts` — UPDATED: `saveCouncil`, `unsaveCouncil`, `shareCouncil`, `streamCouncil`; `SSEEventConvening`, `SSEEventMember`, `SSEEventSynthesisStart`, `SSEEventSynthesisError` types

---

## 18. CLAUDE.md violations log

### Carried from v15

- 2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` (C3a)
- 2026-05-23 — PR4p bundled two logical changes (P-02 violation)
- 2026-05-23 — PR4q empty commit due to stale local main (P-01 violation)

### 2026-06-01 Council session (v16)

No new CLAUDE.md violations.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **🔴 TD-11 — Tier resolution unified refactor** (required before disabling BETA flag)
- [ ] **🔴 Disable BETA_GRANT_PRO_TO_ALL** — required before Stripe checkout smoke test
- [ ] **End-to-end Stripe sandbox test** (with BETA flag OFF)
- [ ] **source_chunks re-ingest** into Oregon via OpenAI embeddings script (TD-22); status unconfirmed post-switch
- [ ] **Post-Oregon smoke test** (login, chat, rituals/Mirror/Council, share, library, RAG retrieval)
- [ ] **bugfixes-3 — auth race fix** (TD-10; PR4ai deferred; preview smoke test required)
- [ ] **Mobile 12-point nav smoke test**
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure)
- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**
- [ ] **RLS policies** as defense-in-depth
- [ ] **UAT** with 3–5 testers, ≥2/5 spontaneous "I'd pay"

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. Must fix before any further PR work. Branch: `chore/gitignore-env-local`.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu (live since 2026-05-30, author-testing pending)
- [ ] **PR-D2 production smoke test** — PENDING (blocked by OTP delivery failure to ote.gr). Workaround: test with gmail address.

### Open items (P1 — Council fast-follows)

- [ ] **Per-verdict → reflections save** — needs investigation: `saved_lines` is message-centric (requires `message_id`); council responses live in `council_responses`, not `messages`. Design required before build.
- [ ] **Council share card redesign** — boardroom bg, date header, 4 member portrait thumbnails, centered synthesis text. Requires boardroom.webp + 4 portraits copied to `apps/api/static/personas/`. Current card is generic Pillow layout.
- [ ] **Reflection share card redesign** — center text, smaller/lower thumbnail.
- [ ] **compress mirror.png** — 2.3MB PNG → WebP. Page-load perf improvement.

### Open items (P1 — general)

- [ ] **OTP-01 — OTP delivery failure for ote.gr** — investigate Render logs; likely Resend deliverability or rate-limiting
- [ ] **render.yaml sync:false** — add `sync: false` to ALL secrets to prevent accidental env-var overwrite
- [ ] **Upstash 80% quota alert** — set up in Upstash dashboard
- [ ] **Render env-var-change notification** — set up operational monitoring
- [ ] **Startup health check** — fail loudly on missing critical secrets
- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**

### Open items (P2 — tech debt)

- [ ] **TD-11** — Tier resolution unified refactor — **escalated to P0 blocker; see above**
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit
- [ ] **branding** — "The Wise Room" vs "Great Minds" still unresolved across codebase (FROM_EMAIL, FRONTEND_URL, copy); separate thread in progress

### Closed items (2026-06-01) — Council session additions

- [x] **CLOSED 2026-06-01** — The Council shipped end-to-end (C5–C7c); migrations 019 + 020 deployed; boardroom screen live; save/unsave toggle wired; share PNG live; Mirror animated (INTRO_HOLD=2100)
- [x] **CLOSED 2026-06-01** — `image_service.py` refactored to shared Pillow core; reflections output byte-identical; council path added

### Closed items (carried from v15)

- [x] **CLOSED 2026-06-01** — The Mirror shipped end-to-end (PRs #166–#173); migrations 017 + 018 deployed; host picker verified; eligible-host config locked
- [x] **CLOSED 2026-06-01** — Oregon DATABASE_URL confirmed live (`bvzeuwzqgnqcghvqghtb`, us-west-2)
- [x] **CLOSED 2026-05-30** — Voice overhaul: check_brevity live; ending-variation rule; Socrates elenchus; all 9 personas tightened
- [x] **CLOSED 2026-05-29** — C9 PR-B "Bring another mind" + cross-mind awareness + typography PR-F
- [x] **CLOSED 2026-05-28** — Bug #1 (#127), Bug #4/PR-A (#128), PR-D (#129), PR-D2 (#130)
- [x] **CLOSED 2026-05-27** — Upstash quota incident; ANTHROPIC_API_KEY incident resolved

---

## 20. Pre-Launch Blockers

> These items gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [ ] **`BETA_GRANT_PRO_TO_ALL=true`** — currently all users are granted Pro tier regardless of subscription. Must be set to `false` before any Stripe transaction is processed. Requires TD-11 first.
- [ ] **TD-11 — Tier resolution unified refactor** — consolidate `get_current_user_plan` + `get_user_tier` into a single function. Both used by different endpoints with different semantics. Must precede BETA flag disable.
- [ ] **Another-mind feature gate (post-beta)** — backend gates per-persona, not feature-level. Add a feature-level Pro gate before disabling BETA bypass.
- [ ] **Systemic frontend `plan` reliability bug** — `plan` getter unreliable outside `(tabs)/layout.tsx`. Affects all client-side paywall gates. Fix before paid launch.
- [ ] **End-to-end Stripe sandbox test** — must be run with BETA flag OFF to verify real tier enforcement, checkout, portal, cancel, and tier downgrade flows.

---

**End of PROJECT_STATE v16.** Authoritative as of 2026-06-01. Supersedes `PROJECT_STATE_v15.md` (preserved as historical reference).
