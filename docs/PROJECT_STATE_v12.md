# PHILOSOPHER — Project State v12

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v12 = v11 baseline (2026-05-24) + 2026-05-25-26 session delta (PR4r merged; PR4w docs v11 rotation; PR4x OTP autofill fix; PR4y auth redirect; PR4z pull-to-refresh; PR4aa title prompt hardening + backfill; PR4ab PersonaPickerSheet fixes; PR4ac/PR4u2 library empty state; PR4ad Today thumbnail uniformity; PR4ae library readability; PR4af account scheduled letters removed; PR4ag1 share card v3 + spacebar fix; PR4ah rituals icons; L1 migration 015 FK indexes; Render paid plan upgrade; latency diagnosis; Oregon region migration in progress).**
>
> **Generated:** 2026-05-26 (v12 rotation)
>
> **Last updated:** 2026-05-26

> **v12 conflict resolution rule:** Where v12 conflicts with v11, v12 wins. Production reality always wins over docs.

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
| Database | PostgreSQL 17 (Supabase). **Two projects active during migration:** Ireland `plecolxlzshkfvybszgs` (eu-west-1, production, intact) + Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2, migration target). Post-migration: Oregon only. |
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
- **Backend:** Render — `philosopher-api` paid Starter tier (upgraded 2026-05-25, eliminates 15-min idle cold-start). `WEB_CONCURRENCY=1`.
- **Worker:** Render — `philosopher-worker` paid Starter tier ($7/mo, srv-d884bomgvqtc73ef2qrg, upgraded 2026-05-25). ARQ + APScheduler. Previously free tier with 15-min idle cold-start.
- **Database:** Supabase project `plecolxlzshkfvybszgs` (eu-west-1, paid). DATABASE_URL points to `aws-0-eu-west-1.pooler.supabase.com:5432`. **Oregon migration project `bvzeuwzqgnqcghvqghtb` is being populated in parallel — switch pending.** Direct asyncpg connection — NOT Supabase Data API.
- **Cache (Redis):** Upstash `philosopher-prod` (eu-west-1, free tier). REDIS_URL set; ARQ + APScheduler operational.
- **Email (Resend):** RESEND_API_KEY + FROM_EMAIL set. Currently `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain `thegreatminds.app` DNS setup IN PROGRESS.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-26** — L1 (#124, 015_add_fk_indexes migration) + PR4ah (#123, rituals icons)
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3-5 fresh users still pending)
- **Render cold-start:** Eliminated — both philosopher-api and philosopher-worker upgraded to paid Starter tier 2026-05-25.

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v11. See v11/v9/v8 for detail.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v11. Visual closure still pending consolidated polish PR.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

Unchanged from v11. All features live in PATH A SSE streaming endpoint.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; €14.90/mo + €149/yr; PR1 #77)
- **BETA bypass active:** Yes — `BETA_GRANT_PRO_TO_ALL=true` in Render env (PR4j). All users treated as Pro during cold beta.
- **Paywall system wired:** Yes — `/api/v1/subscription` synthetic endpoint live (PR4j); `SubscriptionBootstrap` frontend wiring live (PR4j)
- **Google OAuth:** Dormant — routes live in code but `GOOGLE_OAUTH_ENABLED=false` (PR4k). Not user-visible.
- **Rituals tab:** Live (PR4o) — tab bar icon updated to custom symbol (PR4ah); `/app/rituals` page with 4 cards; PersonaPickerSheet stuck-state + error handling fixed (PR4ab)
- **Share v3:** Live (PR4ag1) — portrait 260px, fonts +4pt, bronze opacity bump, spacebar/emoji .trim() bug fixed

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v11.

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
| 012 | scheduled_emails table (send-to-future-self ritual) | 2026-05-21 | PR4o |
| 013 | FK ondelete clauses: memory_entries CASCADE, insights CASCADE, safety_events SET NULL, user_ritual_completions SET NULL | 2026-05-22 | PR4m / #99 |
| 014 | user_oauth_cols: auth_provider varchar(20) + oauth_provider_id text + index | 2026-05-23 | PR4k / #101 |
| **015** | **FK indexes: 20 btree indexes on FK columns across 10 tables** | **2026-05-26** | **L1 / #124** |

**alembic_version = `015_add_fk_indexes`** (as of 2026-05-26)

### Migration 015 — FK indexes (L1, #124)

20 btree indexes added on FK columns. Tables covered:

```
subscriptions          user_id FK → users
conversations          user_id FK → users, persona_id FK → personas
messages               conversation_id FK → conversations, user_id FK → users
memory_entries         conversation_id FK → conversations, user_id FK → users
insights               conversation_id FK → conversations, user_id FK → users
rituals                (FK columns indexed)
user_ritual_completions user_id FK → users, ritual_id FK → rituals
safety_events          conversation_id FK → conversations, message_id FK → messages
saved_lines            user_id FK → users, conversation_id FK → conversations
scheduled_emails       user_id FK → users, saved_line_id FK → saved_lines
```

**Observed result:** Database query time dropped to <5ms post-L1. Real latency bottleneck identified as network RTT between Render Oregon and Supabase Ireland (280ms). See §12 for latency diagnosis.

### New table added in migration 012

See v11 §4 for full scheduled_emails schema. Unchanged.

### FK ondelete clauses (migration 013) and user_oauth_cols (migration 014)

See v11 §4 for full detail. Unchanged.

### Oregon region migration status (in progress as of 2026-05-26)

```
Old project: plecolxlzshkfvybszgs (eu-west-1, Ireland) — UNTOUCHED, production intact
New project: bvzeuwzqgnqcghvqghtb (us-west-2, Oregon)

Schema:             ✅ COMPLETE (20 tables, 31 FKs, 66 indexes, pgvector enabled)
Reference data:     ✅ COMPLETE
  personas          9 rows
  daily_questions   30 rows
  disclaimer_versions 1 row
  rituals           4 rows

User/app data:      🟡 PARTIAL
  users             ✅ 2 rows migrated
  subscriptions     ✅ 2 rows migrated
  user_preferences  ✅ 1 row migrated
  conversations     ✅ 87 rows migrated

Pending (follow-up session):
  messages          ⏳ 227 rows
  saved_lines       ⏳ 13 rows
  safety_events     ⏳ 5 rows
  user_ritual_completions ⏳ 4 rows
  scheduled_emails  ⏳ 2 rows
  memory_entries    ⏳ 8 rows
  disclaimer_acceptances ⏳ 1 row
  alembic_version   ⏳ row (head = 015_add_fk_indexes)
  conversations.source_saved_line_id UPDATE ⏳ (after saved_lines migrated)

source_chunks (2476 rows × 1536-dim vectors):
  Separate task — re-ingest via existing OpenAI embeddings script post-migration.
  NOT migrated via MCP: 2476 × 1536-dim = ~38MB > context window budget.
  Pattern codified: MCP for structured data; re-ingest from source for vector data.

Render DATABASE_URL switch: pending (founder executes after migration verifies clean)
Production impact: NONE — Ireland project intact, app fully functional during migration
```

### Live database state (2026-05-26)

```
alembic_version:        015_add_fk_indexes ✓
users count:            ~2-3 (founder + test accounts; no organic users yet)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          87 (migrated to Oregon count; more from testing)
messages:               227 (pending Oregon migration)
daily_usage rows:       populated during test runs
safety_events:          5 rows (pending Oregon migration)
memory_entries:         8 rows (pending Oregon migration)
source_chunks:          2476 chunks across 7 personas (C3b, 2026-05-17)
scheduled_emails:       2 rows (pending Oregon migration)
```

### Table population status

Unchanged from v11. See v11 §4.

### RLS state

**RLS DISABLED on all public tables.** Mitigation: frontend goes exclusively through the FastAPI gateway; no Supabase anon key in the frontend bundle.

---

## 5. Backend endpoints

Unchanged from v11. See v11 §5 for full list.

**There is exactly ONE send-message endpoint.** PATH B was deleted in C-RECON-8 (PR #60).

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v11. See v11 §6 / v9 §6 for full specification. All 19 features are live.

---

## 7. Persona error messages

All 9 personas have `llm_unavailable` error messages in DB. Unchanged from v11 §7.

---

## 8. LLM provider validation

Unchanged from v11 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 9. Locked decisions (as of 2026-05-26)

All 11 from v11 remain locked. No new locked decisions this session.

---

## 10. Reconciliation history

Unchanged from v11. See v11/v9 §10 for C-RECON-1 through C-RECON-8.

---

## 11. PR4j BETA bypass system

Unchanged from v11 §11. BETA_GRANT_PRO_TO_ALL=true; TD-11 (tier consolidation) required before disabling.

---

## 12. Frontend architecture and performance context

### Today page data flow

See v11 §12 for full specification. PR4r confirmed merged — api import is stable in today/page.tsx. No changes to Today page data flow in this session.

### Latency diagnosis (NEW v12 — 2026-05-26)

Post-L1 baseline established:

```
Database query time:    <5ms (confirmed post-migration 015)
Render ↔ Supabase RTT:  280ms (Render Oregon → Supabase Ireland eu-west-1)
Founder location add:   150-200ms (Greece → Render Oregon)
Total per API call:     ~600-700ms observed

Root cause: Render (Oregon us-west-2) ↔ Supabase Ireland (eu-west-1) cross-region RTT.
L1 indexes eliminated query-side latency. Network RTT is the remaining bottleneck.

Solution: co-locate Render and Supabase in same region (Oregon us-west-2).
Status: Oregon Supabase project provisioned; migration in progress (see §4).
Expected post-migration: <100ms per API call from Render; ~250-350ms for founder in Greece.
```

### Pull-to-refresh fix (PR4z)

`overscroll-behavior-y: contain` added to `apps/web/app/globals.css`. Prevents browser pull-to-refresh gesture from triggering on iOS Safari / mobile Chrome. No data-flow impact.

---

## 13. Session metrics

### 2026-05-21-24 session

See v11 §13.

### 2026-05-25-26 session

| Metric | Value |
|---|---|
| PRs merged | PR4r (was in-flight from v11), PR4w (v11 docs rotation), PR4x (#113), PR4y, PR4z, PR4aa, PR4ab, PR4u2, PR4ad, PR4ae (#120), PR4af (#121), PR4ag1 (#122), PR4ah (#123), L1 (#124) |
| Production regressions | 0 |
| Migrations deployed | 015 (20 FK indexes) |
| New frontend files | RitualIcons.tsx (PR4ah — ReturningPathIcon + MirrorIcon + nav symbol) |
| New backend files | None |
| Infrastructure | Render philosopher-worker + philosopher-api upgraded to paid Starter tier ($7/mo each); cold-start eliminated |
| Latency diagnosis | Ireland↔Oregon 280ms RTT identified as bottleneck; Oregon migration started |
| Lessons codified | P-06 confirmed working (diagnose before code — 3 false alarms correctly resolved without code changes) |
| False diagnostic detours | 3: "share unstuck" = cold-start not bug; "Letter email" = works as intended; "reflections deleted" carried forward from v11 |

---

## 14. Known bugs (active)

### Carried from v11

- **BUG-012** — Zustand hydration race (hard refresh / direct URL on protected routes flashes to /auth). TD-10. PR4ai deferred (too risky). Approach requires Netlify preview smoke test.
- **BUG-014** — Letter to my Future Self ARQ email delivery not wired. DB schema and UI live; actual send task not implemented.

### Closed this session

| ID | Description | Resolution |
|---|---|---|
| BUG-013 | PR4p hydration guard broke production | PR4r merged — guard removed, api import fix kept |

### No new bugs introduced in 2026-05-25-26 session (0 production regressions).

---

## 15. Environment variables

### Backend (Render)

```
DATABASE_URL                  Supabase Ireland pooler (current production)
                               ⚠️ PENDING SWITCH to Oregon after migration completes
                               Current: aws-0-eu-west-1.pooler.supabase.com:5432
                               Target:  aws-0-us-west-2.pooler.supabase.com:5432

REDIS_URL                     (Upstash, set)
RESEND_API_KEY                (set)
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>"
JWT_SECRET                    (set)
ANTHROPIC_API_KEY             (set — actively used for chat)
ANTHROPIC_MEMORY_MODEL        "claude-haiku-4-5-20251001" — used by memory extraction
PHENOMENOLOGY_BRIDGE_ENABLED  (state unverified — was true 2026-05-04/05)

FRONTEND_URL                  "https://thinkalike.netlify.app"
                               Replaces BASE_URL for Stripe redirects + email links (PR4k)

BETA_GRANT_PRO_TO_ALL         "true"
                               All users treated as Pro. Toggle to "false" before paid launch.
                               Requires TD-11 refactor before toggling.

GOOGLE_OAUTH_ENABLED          "false"
GOOGLE_CLIENT_ID              (placeholder)
GOOGLE_CLIENT_SECRET          (placeholder)

STRIPE_SECRET_KEY             ✅ Set (PR1 #77, 2026-05-19)
STRIPE_WEBHOOK_SECRET         ✅ Set (PR1 #77, 2026-05-19)
STRIPE_PRICE_PRO_MONTHLY      ✅ Set — €14.90/mo price ID
STRIPE_PRICE_PRO_YEARLY       ✅ Set — €149/yr price ID
STRIPE_PRICE_PREMIUM_MONTHLY  ✅ Set — placeholder; Premium deferred

BASE_URL                      ⚠️ DEPRECATED (PR4k) — config.py setting remains but no app code reads it.
ANTHROPIC_MODEL (config.py)   ⚠️ ORPHANED — not read by conversation_service.py (TD-03)
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

All v11 paths apply. No new backend files added this session.

Notable changes since v11:
- `workers/arq_worker.py` — `generate_conversation_title` task prompt hardened (PR4aa); avoids generic/meta titles
- `db/migrations/versions/015_add_fk_indexes.py` — 20 btree indexes on FK columns (L1 / #124)

### Frontend (apps/web/)

All v11 paths apply. Additions and changes since v11:

- `app/auth/verify/page.tsx` — OTP input `maxLength` logic fixed for mobile autofill (PR4x / #113)
- `app/app/(tabs)/layout.tsx` — 5 protected tabs now redirect to `/auth?mode=signin` instead of `/auth` (PR4y); tab bar icon for Rituals updated to custom symbol (PR4ah)
- `app/globals.css` — `overscroll-behavior-y: contain` added (PR4z, pull-to-refresh disabled)
- `app/app/(tabs)/today/page.tsx` — "Your reflections" card mirrors "Continuing." flex grammar; hero images migrated to `next/image` (PR4ad)
- `app/app/(tabs)/library/page.tsx` — ConversationCard readability: avatar 56px, font scale up (PR4ae / #120); Library search empty state card added (PR4u2)
- `app/app/(tabs)/account/page.tsx` — ScheduledLettersCard removed (PR4af / #121, 17 lines deleted)
- `components/share/SharePreviewModal.tsx` — portrait height 260px, fonts +4pt, bronze opacity bump (PR4ag1 / #122); `.trim()` on emoji-stripped text removed (spacebar bug fix)
- `components/rituals/PersonaPickerSheet.tsx` (or equivalent) — stuck state fixed, silent errors surfaced, delete feedback toasts added (PR4ab)
- `components/rituals/RitualIcons.tsx` — NEW FILE (PR4ah / #123): `ReturningPathIcon` + `MirrorIcon` SVG components; nav tab uses custom symbol swap

---

## 17. Note: KIEN is a SEPARATE project — DELETED

KIEN sister project was deleted on 2026-05-26. Founder confirmed no precious data; no backup taken. The Philosopher codebase and docs are Philosopher-only. Section preserved as historical note.

---

## 18. CLAUDE.md violations log

### Carried from v11

- 2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` during C3a. Resolved via Path C recovery. See v11/v9 §18.
- 2026-05-23 — PR4p bundled two logical changes (P-02 violation). See v11 §18.
- 2026-05-23 — PR4q empty commit due to stale local main (P-01 violation). See v11 §18.

### 2026-05-25-26 session

No new CLAUDE.md violations. P-06 (diagnose before code change) was applied correctly to three false-alarm reports in this session — no premature code changes were made.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **Region migration Oregon — complete pending tables** (messages 227, saved_lines 13, safety_events 5, user_ritual_completions 4, scheduled_emails 2, memory_entries 8, disclaimer_acceptances 1, alembic_version row, source_saved_line_id UPDATE)
- [ ] **Re-ingest source_chunks into Oregon project** (2476 × 1536-dim vectors via embeddings script)
- [ ] **Render DATABASE_URL switch** to Oregon (founder executes after migration verifies clean)
- [ ] **Post-switch smoke test** (login, chat, rituals, share, library)
- [ ] **bugfixes-3 — auth race fix** (TD-10; PR4ai deferred as too risky; preview smoke test required before any attempt)
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel)
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari)
- [ ] **Cold beta with 3–5 fresh users** (signup → conversation → Stripe upgrade)
- [ ] **Consolidated polish PR** (blocks Block B visual closure)
- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**

### Open items (P1)

- [ ] **TD-05** — Wire generate_insight_task (when memory_entries accumulating)
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory; PR4ai deferred)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to my Future Self — ARQ email delivery wiring** (BUG-014)

### Open items (P2 — tech debt)

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch)
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit across parent-child relationships
- [ ] All v11 TD-01 through TD-09 items (see IMPLEMENTATION_BACKLOG_v12.md)

### Closed items (2026-05-25-26) — additions to v11 closed list

- [x] **CLOSED 2026-05-24** — PR4r: actual rollback of hydration guard (was in-flight at v11 generation)
- [x] **CLOSED 2026-05-25** — PR4w: docs v10→v11 rotation
- [x] **CLOSED 2026-05-25** — Render plan upgrades: philosopher-api + philosopher-worker both to paid Starter tier; cold-start eliminated
- [x] **CLOSED 2026-05-25** — PR4x (#113): OTP autofill mobile fix — maxLength logic in auth/verify/page.tsx
- [x] **CLOSED 2026-05-25** — PR4y: auth redirect destination — 5 protected pages now redirect to /auth?mode=signin
- [x] **CLOSED 2026-05-25** — PR4z: pull-to-refresh disabled via globals.css overscroll-behavior-y: contain
- [x] **CLOSED 2026-05-25** — PR4aa: conversation titles prompt hardening + Render-shell backfill (5/5 clean titles executed)
- [x] **CLOSED 2026-05-25** — Backfill-titles admin execution: 5/5 conversations received clean AI-generated titles
- [x] **CLOSED 2026-05-25** — PR4ab: PersonaPickerSheet stuck state + silent errors + delete feedback toasts
- [x] **CLOSED 2026-05-25** — PR4u2: Library search empty state card
- [x] **CLOSED 2026-05-25** — PR4ad: Today card thumbnail uniformity (flex grammar + next/image migration)
- [x] **CLOSED 2026-05-26** — PR4ae (#120): Library ConversationCard readability (avatar 56px, font scale up)
- [x] **CLOSED 2026-05-26** — PR4af (#121): Account scheduled letters card removed (17 lines deleted)
- [x] **CLOSED 2026-05-26** — PR4ag1 (#122): Share card v3 tweaks + spacebar bug fix (emoji .trim() removed)
- [x] **CLOSED 2026-05-26** — PR4ah (#123): RitualIcons.tsx new file + nav tab symbol swap
- [x] **CLOSED 2026-05-26** — L1 (#124): migration 015 — 20 btree FK indexes; <5ms query time confirmed

---

**End of PROJECT_STATE v12.** Authoritative as of 2026-05-26. Supersedes `PROJECT_STATE_v11.md` (preserved as historical reference).
