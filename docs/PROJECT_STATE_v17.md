# PHILOSOPHER — Project State v17

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v17 = v16 baseline (2026-06-03) + 2026-06-03 session delta (PR #210: ConversationCard title fix, today first-day picker opens PersonaPickerSheet, cross-persona Ask-another-mind fix; rituals micro-polish: half-sphere YvY SVG icon, Letter whole-card tap; app icon landed accidentally + hotfixed, mark deferred; daily_questions: 50 phenomenology themes active, old 30 deactivated; backfill-titles executed queued=0; OTP lockout root cause documented; Pro test account created).**
>
> **Generated:** 2026-06-03 (v17 rotation) · **Last updated:** 2026-06-03

> **v17 conflict resolution rule:** Where v17 conflicts with v16 or earlier, v17 wins. Production reality always wins over docs.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive — scheduled deletion ~2026-06-09; do not write to it. All Render services must point to Oregon.**

---

## 2026-06-03 Session Delta — PR3a micro-polish + daily_questions

> Appended as v17. Where this conflicts with v16 or prior sections, this section wins.

**Code merged to main (current main SHA: `c50779b5`):**

- **PR #210 (squash `eda60f21`) — three production bug fixes:**
  - `apps/web/components/library/ConversationCard.tsx` — card now shows conversation title with `last_message_snippet` as fallback. Fixes BUG-013 and PR3a item #2: title no longer demoted to snippet-first rendering.
  - `apps/web/app/app/(tabs)/today/page.tsx` — first-day "Reflect" no longer hardcodes Marcus Aurelius; opens `PersonaPickerSheet` instead. Opening message skipped only when a topic already exists.
  - `apps/web/components/personas/PersonaPickerSheet.tsx` — cross-persona "Ask another mind" now starts the chat correctly: `onClose()` called before the async conversation create, so `history.back()` no longer reverts `router.push`. Fixes PR3a item A.

- **Rituals micro-polish (merged separately):**
  - `apps/web/app/app/(tabs)/rituals/page.tsx`:
    - You-vs-You card: `<Contrast size={40} strokeWidth={1.2} />` replaced with an inline half-sphere SVG (`<circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1.2" />` + `<path d="M20 1 A19 19 0 0 1 20 39 Z" fill="currentColor" />`). Closes PR3a item #5.
    - Letter-to-Future-Self card: outer `<div>` wrapper changed to `<button onClick={handleBeginLetter}>` making the whole card the tap target; inner "Begin" `<button>` and `<ChevronRight>` removed. Pro-gate and `RitualScheduleSheet` preserved unchanged. Closes PR3a item #8.
    - Import line: `ChevronRight` and `Contrast` removed from `lucide-react` import.

- **App icon — landed accidentally, removed via hotfix:**
  - `apps/web/public/personas/appbutton.png` (1122×1402 px, 8-bit RGB, ~2.1 MB) was copied to `apps/web/app/icon.png` and `apps/web/app/apple-icon.png` in the rituals PR. Both files landed on main (`c9bb3d39`) and were removed in a follow-up hotfix (`c50779b5`).
  - **DECISION: app-icon mark DEFERRED.** The Chesterfield armchair photo stays as brand/hero/OG image only. A purpose-built icon mark is required before wiring Next.js `icon.png` / `apple-icon.png` — design TBD. Closes PR3a item B as deferred (not done).

**Production database (Oregon `bvzeuwzqgnqcghvqghtb`) — data changes, no migrations:**

- **`daily_questions` table updated:** 30 philosophical prompts deactivated (`active=false`, rows preserved, reversible). 50 modern-phenomenology themes inserted (`display_order` 1000–1049, `active=true`). Topics include: loneliness, social-media relationships, doomscrolling, AI threats to work, and related phenomenology themes. Rotation endpoint `GET /api/v1/today/question` selects `WHERE active=true ORDER BY display_order`, picks entry by day-of-year index. Closes PR3a item #6.

- **`backfill-titles` endpoint executed:** `POST /api/v1/admin/backfill-titles` returned `{queued: 0}`. No title debt outstanding — all qualifying conversations (`message_count >= 6 AND title IS NULL`) had already been titled by the ARQ Haiku worker. No further backfill action needed.

**Operational notes (record as facts, not state):**

- **Oregon DB confirmed canonical:** `bvzeuwzqgnqcghvqghtb` (us-west-2) is the only live database. Ireland project `plecolxlzshkfvybszgs` (eu-west-1) = deprecated rollback buffer; scheduled deletion ~2026-06-09; never query.

- **Pro test account:** `nckoutras+pro1@gmail.com` granted Pro tier via `UPDATE subscriptions SET plan='pro', status='active'`. A free subscription row auto-creates at signup — grant is `UPDATE`, not `INSERT`.

- **OTP lockout root cause documented:** Upstash Redis key `otp_request:{email}` rate-limits OTP requests to 5/hour (`auth.py`). This is separate from the DB-side OTP attempt lockout (`OTP_MAX_ATTEMPTS=5`). Workaround for testing: use `+alias` email variants — each alias is a distinct rate-limit bucket.

**Key superseded facts (v17):**

- **BUG-013 — ConversationCard title never renders:** was `last_message_snippet ?? title` → **CLOSED. Fixed in PR #210: `title ?? last_message_snippet`. Title now renders first; snippet is the fallback.**
- **PR3a item A — Ask another mind chat stuck:** was unresolved → **CLOSED. Fixed in PR #210: `onClose()` called before async create in `PersonaPickerSheet.tsx`.**
- **PR3a item #5 — YvY icon unclear:** was `<Contrast>` (lucide) → **CLOSED. Replaced with inline half-sphere SVG (`currentColor`).**
- **PR3a item #8 — Letter card pushbutton:** was inner `<button>Begin</button>` inside `<div>` → **CLOSED. Whole-card `<button onClick={handleBeginLetter}>`.**
- **PR3a item #6 — phenomenology prompts:** was 30 philosophical prompts → **CLOSED. 50 modern-phenomenology themes active in `daily_questions`.**
- **PR3a item B — app icon:** was "in sweep" → **DEFERRED. Photo icon tried and removed. Icon mark design TBD.**
- **Backfill-titles:** was "not yet executed" → **DONE. Executed 2026-06-03; queued=0.**
- **PR3a sweep:** was "not started" → **PARTIALLY COMPLETE.** Remaining: memory bugs (fresh-chat missing opening message/thumbnail; home "Continuing" 404s).
- **`today/page.tsx` first-day picker:** was hardcoded Marcus Aurelius → **FIXED. Opens PersonaPickerSheet (PR #210).**

---

## v16 Session Deltas (2026-06-01 through 2026-06-03)

See `PROJECT_STATE_v16.md` for full v16 session detail: The Council (PRs #182–#186), You vs You (PRs #193–#202), Revenue chain + TD-11 + PR3a triage.

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
| Database | PostgreSQL 17 (Supabase). **Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2) — CONFIRMED LIVE.** Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy / inactive; scheduled deletion ~2026-06-09. |
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
- Last production deploy: **2026-06-03** — PR #210 (ConversationCard title fix, today first-day picker, cross-persona fix); rituals micro-polish (half-sphere YvY SVG, Letter whole-card tap); app icon hotfix removal. Current main: `c50779b5`.
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
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false` confirmed disabled on both API and worker (2026-06-03). Tier enforcement is live via `get_user_tier`.
- **Paywall system wired:** Yes
- **Google OAuth:** Dormant
- **Rituals tab:** Live (PR4o) — ritual cards shown; **Mirror ✅ SHIPPED** (PRs #166–#173); **Council ✅ SHIPPED** (PRs #182–#186); **You vs You ✅ SHIPPED** (PRs #193–#202); Counterview + Weekly Reading are placeholder-locked; Letter to Future Self is functional (ARQ delivery not yet wired). **Rituals micro-polish shipped 2026-06-03:** half-sphere SVG for YvY card; Letter card is whole-card tap.
- **Share v3:** Live (PR4ag1); **Council share:** Live (C7c / #186)
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
| **019** | **council_cases + council_sessions + council_responses tables + indexes** | **2026-06-01** | **Council C5–C7b** |
| **020** | **council_saves (id UUID PK, user_id FK CASCADE, session_id FK CASCADE, saved_at, deleted_at NULL) + UNIQUE(user_id, session_id) + ix_council_saves_user** | **2026-06-01** | **Council C7b** |
| **021** | **self_comparisons (id UUID PK, user_id FK CASCADE, prompt TEXT NOT NULL, then/now window timestamps, payload JSONB, status, ring_true fields, created_at) + ix_self_comparisons_user** | **2026-06-02** | **YvY PR1 #193** |

**alembic_version = `021_create_self_comparisons`** (no new migrations in v17 session)

### Oregon region migration — CONFIRMED LIVE

**Live DB = Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy, inactive; scheduled deletion ~2026-06-09.**

### Live database state (2026-06-03)

```
alembic_version:        021_create_self_comparisons ✓
daily_questions:        50 active (display_order 1000–1049, phenomenology themes)
                        30 inactive (original philosophical prompts, active=false, reversible)
users count:            ~3-4 (founder + test accounts incl. nckoutras+pro1@gmail.com; no organic users)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          87+ (testing adds more)
messages:               227+ (testing adds more)
source_chunks:          2476 chunks across 7 personas
mirrors:                rows from preview cron
council_cases:          table live (019)
council_sessions:       table live (019)
council_responses:      table live (019)
council_saves:          table live (020)
self_comparisons:       table live (021)
```

### RLS state

**RLS DISABLED on all public tables.** Unchanged from v12.

---

## 5. Backend endpoints

All v16 endpoints apply. No new endpoints in v17 session. See `PROJECT_STATE_v16.md §5` for full endpoint list (Council, self-comparison, etc.).

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v15. See v15 §6.

---

## 7. Council architecture

Unchanged from v16. See `PROJECT_STATE_v16.md §7`.

---

## 8. Persona error messages

All 9 personas have `llm_unavailable` error messages in DB. Unchanged from v12 §7.

---

## 9. LLM provider validation

Unchanged from v12 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 10. Locked decisions

All 24 from v16 remain locked. No new locked decisions in v17 session.

---

## 11. Reconciliation history

Unchanged from v12. See v12/v11/v9 §10 for C-RECON-1 through C-RECON-8.

---

## 12. BETA bypass system

**`BETA_GRANT_PRO_TO_ALL` = OFF.** Confirmed disabled on both API and worker services (2026-06-03 revenue chain session). TD-11 canonical tier resolver shipped (#203). `get_user_tier` is the single source of truth; `get_current_user_plan` wraps it. Dual tier resolution tech debt resolved.

---

## 13. Frontend architecture

### Rituals page (`apps/web/app/app/(tabs)/rituals/page.tsx`) — updated v17

- You-vs-You card icon: inline half-sphere SVG (circle + right-semicircle path, `currentColor`). Replaces lucide `<Contrast>`.
- Letter-to-Future-Self card: whole card is `<button onClick={handleBeginLetter}>`. Inner "Begin" button and `<ChevronRight>` removed. Pro-gate and `RitualScheduleSheet` preserved.

### Council screen, SharePreviewModal, You vs You screen, Latency topology

Unchanged from v16. See `PROJECT_STATE_v16.md §13`.

---

## 14. Session metrics

### 2026-06-03 session — PR3a micro-polish + daily_questions

| Metric | Value |
|---|---|
| PRs merged | PR #210 `eda60f21` (3 bug fixes); rituals polish `c9bb3d39` (rituals micro-polish + accidental icon); hotfix `c50779b5` (icon removal) |
| Production regressions | 0 |
| Migrations deployed | None |
| New tables | None |
| New endpoints | None |
| DB data changes | `daily_questions`: 50 phenomenology themes active (display_order 1000–1049); old 30 deactivated. `backfill-titles` executed; queued=0. |
| Files changed | `ConversationCard.tsx`, `today/page.tsx`, `PersonaPickerSheet.tsx` (PR #210); `rituals/page.tsx` (polish) |
| PR3a items closed | A (chat stuck), #2 (title), #5 (YvY icon), #6 (prompts), #8 (Letter tap). Item B (app icon) deferred. Memory bugs still pending. |

### 2026-06-03 session — Revenue chain + PR3a triage

See `PROJECT_STATE_v16.md §14`.

### Earlier sessions

See `PROJECT_STATE_v16.md §14` for Council, You vs You, Mirror, and earlier sessions.

---

## 15. Known bugs (active)

### Carried from v16

- **BUG-012** — Zustand hydration race (hard refresh / direct URL on protected routes flashes to /auth). TD-10. PR4ai deferred. Approach requires Netlify preview smoke test.

### Open issues carried from v16

- **OTP-01** — OTP delivery failure for ote.gr (Greek ISP). Workaround: use gmail. Not related to any PR code changes.
- **OPS-001** — `nkoutr@ote.gr` subscription `current_period_end = NULL` (pre-#205 row). Needs manual re-sync via Stripe dashboard or admin endpoint.

### Closed this session (v17)

- **BUG-013 — ConversationCard title never renders:** CLOSED 2026-06-03. Fixed in PR #210: `title ?? last_message_snippet`. Title now renders first; snippet is fallback.

### New tech debt logged (v17)

None this session.

---

## 16. Environment variables

Unchanged from v16. See `PROJECT_STATE_v16.md §16`.

---

## 17. Key file paths (production codebase)

All v16 paths apply. Changes in v17:

### Frontend (apps/web/)

- `app/app/(tabs)/rituals/page.tsx` — UPDATED: half-sphere SVG for YvY card; Letter card whole-card tap; `Contrast` + `ChevronRight` removed from imports.
- `app/app/(tabs)/today/page.tsx` — UPDATED (PR #210): first-day Reflect opens PersonaPickerSheet; opening message skipped only when topic exists.
- `components/library/ConversationCard.tsx` — UPDATED (PR #210): `title ?? last_message_snippet` (was `last_message_snippet ?? title`).
- `components/personas/PersonaPickerSheet.tsx` — UPDATED (PR #210): `onClose()` called before async create.

---

## 18. CLAUDE.md violations log

### Carried from v16

- 2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` (C3a)
- 2026-05-23 — PR4p bundled two logical changes (P-02 violation)
- 2026-05-23 — PR4q empty commit due to stale local main (P-01 violation)

### 2026-06-03 v17 session

No new CLAUDE.md violations.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **🟡 PR3a cold-beta sweep — partially complete.** Remaining: memory bugs (fresh-chat missing opening message/thumbnail; home "Continuing" 404s). All other PR3a items closed (see below).
- [ ] **OPS-001 — nkoutr@ote.gr current_period_end re-sync** — pre-#205 row has NULL current_period_end; needs manual re-sync.
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

- [ ] **Per-verdict → reflections save** — needs investigation: `saved_lines` is message-centric; council responses live in `council_responses`, not `messages`. Design required before build.
- [ ] **Council share card redesign** — boardroom bg, date header, 4 member portrait thumbnails, centered synthesis text.
- [ ] **Reflection share card redesign** — center text, smaller/lower thumbnail.
- [ ] **compress mirror.png** — 2.3MB PNG → WebP.

### Open items (P1 — general)

- [ ] **OTP-01 — OTP delivery failure for ote.gr** — investigate Render logs
- [ ] **render.yaml sync:false** — add `sync: false` to ALL secrets
- [ ] **Upstash 80% quota alert** — set up in Upstash dashboard
- [ ] **Render env-var-change notification** — set up operational monitoring
- [ ] **Startup health check** — fail loudly on missing critical secrets
- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **App-icon mark design** — deferred from PR3a. Photo icon removed; need purpose-built icon mark before wiring `icon.png` / `apple-icon.png`.

### Open items (P2 — tech debt)

- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit
- [ ] **branding** — "The Wise Room" vs "Great Minds" still unresolved across codebase (FROM_EMAIL, FRONTEND_URL, copy); separate thread in progress

### Closed items (2026-06-03) — PR3a micro-polish session

- [x] **CLOSED 2026-06-03** — PR3a item A: Ask another mind chat stuck. Fixed: `onClose()` before async create in `PersonaPickerSheet.tsx` (PR #210).
- [x] **CLOSED 2026-06-03** — PR3a item #2 / BUG-013: ConversationCard title. Fixed: `title ?? last_message_snippet` in `ConversationCard.tsx` (PR #210).
- [x] **CLOSED 2026-06-03** — Today first-day Reflect hardcoded Marcus. Fixed: opens `PersonaPickerSheet`; opening message skipped only when topic exists (PR #210).
- [x] **CLOSED 2026-06-03** — PR3a item #5: YvY ritual card icon. Replaced `<Contrast>` with inline half-sphere SVG.
- [x] **CLOSED 2026-06-03** — PR3a item #8: Letter to Future Self card. Whole-card `<button>` replacing inner Begin button.
- [x] **CLOSED 2026-06-03** — PR3a item #6: phenomenology prompts. 50 modern-phenomenology themes active in `daily_questions`; old 30 deactivated (reversible).
- [x] **CLOSED 2026-06-03** — Backfill-titles executed. `queued=0` — no title debt outstanding.

### Closed items (2026-06-03) — Revenue chain session

- [x] **CLOSED 2026-06-03** — TD-11 canonical tier resolver shipped (#203)
- [x] **CLOSED 2026-06-03** — BETA_GRANT_PRO_TO_ALL confirmed OFF on both API and worker
- [x] **CLOSED 2026-06-03** — Stripe webhook URL corrected; current_period_end fix (#205); account auth hydration fix (#207)
- [x] **CLOSED 2026-06-03** — Revenue chain verified end-to-end in TEST/sandbox

### Closed items (2026-06-02 and earlier)

See `PROJECT_STATE_v16.md §19` for full history.

---

## 20. Pre-Launch Blockers

> These items gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [x] ~~**`BETA_GRANT_PRO_TO_ALL`**~~ — 🟢 **CONFIRMED OFF** (2026-06-03)
- [x] ~~**TD-11 — Tier resolution unified refactor**~~ — 🟢 **COMPLETE** (#203, 2026-06-03)
- [x] ~~**End-to-end Stripe sandbox test**~~ — 🟢 **COMPLETE** (2026-06-03)
- [ ] **Another-mind feature gate (post-cold-beta)** — add a feature-level Pro gate before disabling BETA bypass for real paying users.
- [ ] **Systemic frontend `plan` reliability bug** — `plan` getter unreliable outside `(tabs)/layout.tsx`. Fix before paid launch.
- [ ] **Live Stripe wiring** — sandbox complete; live wiring requires: live Stripe keys + live price IDs + a separate live-mode webhook + `ENVIRONMENT=production` on Render API.

---

**End of PROJECT_STATE v17.** Authoritative as of 2026-06-03 (PR3a micro-polish + daily_questions session). Supersedes `PROJECT_STATE_v16.md` (preserved as historical reference).
