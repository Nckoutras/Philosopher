# PHILOSOPHER — Project State v13

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v13 = v12 baseline (2026-05-26) + 2026-05-28 session delta (Bug #1 BottomSheet history.back race #127; Upstash quota incident resolved + Pay-as-You-Go upgrade; ANTHROPIC_API_KEY incident resolved; Bug #4 / PR-A real-time streaming + inline correction #128; PR-D greeting personalization #129; PR-D2 name capture deferred prompt #130; strategic decisions locked: rituals scope, council mode, press further, typography, weekly reading; docs v13 rotation).**
>
> **Generated:** 2026-05-28 (v13 rotation)
>
> **Last updated:** 2026-05-28

> **v13 conflict resolution rule:** Where v13 conflicts with v12, v13 wins. Production reality always wins over docs.

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
| Database | PostgreSQL 17 (Supabase). Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2) is the migration target; DATABASE_URL switch pending. See §4. |
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
- **Backend:** Render — `philosopher-api` paid Starter tier. `WEB_CONCURRENCY=1`.
- **Worker:** Render — `philosopher-worker` paid Starter tier ($7/mo, srv-d884bomgvqtc73ef2qrg).
- **Database:** Supabase. DATABASE_URL currently unconfirmed — see §4 Oregon migration status.
- **Cache (Redis):** Upstash `philosopher-prod` — **Pay-as-You-Go ($0.2/100k commands)** as of 2026-05-27. Upgraded from free tier after 500k commands/month limit was hit and crashed the worker.
- **Email (Resend):** RESEND_API_KEY + FROM_EMAIL set. `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain `thegreatminds.app` DNS setup IN PROGRESS.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-28** — Bug #1 (#127), PR-A streaming (#128), PR-D greeting (#129), PR-D2 name capture (#130)
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3-5 fresh users still pending)
- **Render cold-start:** Eliminated — both services on paid Starter tier.

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v12. See v12/v11/v9 for detail.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v12. Visual closure still pending consolidated polish PR.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

Updated in v13: real-time streaming architecture shipped (PR-A / Bug #4). See §6.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; €14.90/mo + €149/yr; PR1 #77)
- **BETA bypass active:** Yes — `BETA_GRANT_PRO_TO_ALL=true` in Render env (PR4j). All users treated as Pro during cold beta.
- **Paywall system wired:** Yes — `/api/v1/subscription` synthetic endpoint live (PR4j); `SubscriptionBootstrap` frontend wiring live (PR4j)
- **Google OAuth:** Dormant — routes live in code but `GOOGLE_OAUTH_ENABLED=false` (PR4k). Not user-visible.
- **Rituals tab:** Live (PR4o) — 4 ritual cards shown; Mirror + Counterview + Weekly Reading are placeholder-locked; Letter to Future Self is functional (ARQ delivery not yet wired).
- **Share v3:** Live (PR4ag1)
- **Greeting personalization:** Live (PR-D #129) — Today page greeting includes first name for users with `full_name` set.
- **Name capture prompt:** Live (PR-D2 #130) — NamePromptCard surfaces on Today for OTP users with null/empty `full_name`. PATCH /api/v1/auth/me endpoint live.

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v12.

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001–014 | See v12/v11/v9 for full history | Pre-v12 | — |
| **015** | **FK indexes: 20 btree indexes on FK columns across 10 tables** | **2026-05-26** | **L1 / #124** |

**alembic_version = `015_add_fk_indexes`** (no new migrations in 2026-05-28 session)

### Oregon region migration — IN PROGRESS (not yet complete)

Oregon migration data status carried from v12:
- Schema: ✅ COMPLETE
- Reference data: ✅ COMPLETE
- User/app data: 🟡 PARTIAL (users, subscriptions, conversations done; messages 227, saved_lines 13, safety_events 5, user_ritual_completions 4, scheduled_emails 2, memory_entries 8, disclaimer_acceptances 1 still pending)
- source_chunks: separate task — re-ingest via existing OpenAI embeddings script (TD-22)
- DATABASE_URL switch: **NOT YET CONFIRMED** — not addressed in 2026-05-28 session. Founder to execute in Render env after full migration verifies clean.

⚠️ **Note:** ANTHROPIC_API_KEY disappeared from both services between 2026-05-25 and 2026-05-27 (cause unconfirmed — possibly blueprint sync without sync:false flag). Re-added manually and services redeployed on 2026-05-27/28. See §15 and HANDOFF_BRIEF_v13 §open-issues.

### Live database state (2026-05-28)

```
alembic_version:        015_add_fk_indexes ✓
users count:            ~2-3 (founder + test accounts; no organic users yet)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          87+ (testing adds more)
messages:               227+ (testing adds more)
source_chunks:          2476 chunks across 7 personas (C3b, 2026-05-17)
```

See v12 §4 for full table population status and FK ondelete detail. Unchanged.

### RLS state

**RLS DISABLED on all public tables.** Unchanged from v12.

---

## 5. Backend endpoints

Unchanged from v12, plus one addition:

**PATCH /api/v1/auth/me** — Name update endpoint (PR-D2 #130)
- Auth: `Depends(get_current_user)` — updates own record only
- Request schema: `UpdateMeRequest` — `full_name` with trim + non-empty + max 100 chars validation
- Response: `UserOut` (same shape as GET /auth/me)
- Purpose: OTP users who have no `full_name` set can provide their first name via the NamePromptCard

**There is exactly ONE send-message endpoint.** PATH B was deleted in C-RECON-8 (PR #60). Send-message endpoint now uses real-time streaming architecture (see §6).

---

## 6. Send-message architecture (PATH A — canonical, updated v13)

### Real-time streaming (PR-A / Bug #4, shipped 2026-05-28)

Previous architecture: LLM stream was buffered server-side, then yielded all at once after postprocessing completed (causing 60+ second stalls; 3 regen attempts × 10-15s each).

**New architecture (v13):**
- Chunks yielded to client as LLM generates them — first chunk in 3-7s
- Postprocessing (`check_universal_forbidden`) runs in background AFTER stream completes
- If check fails: new SSE event `'correction'` fires
  - Frontend: fades original content (text-charcoal opacity-55, 300ms transition)
  - Bronze 0.5px divider appears
  - "Let me put that again." renders in font-cormorant italic text-[13px] text-sepia (LOCKED COPY)
  - Regen streams in real-time via `llm_client.stream()`
  - Fade-in animation: opacity 0→1 + translateY 4px→0, 250ms ease-out, both fill mode
- If regen also fails: `_deterministic_strip` on regen text, saved to DB stripped

**New structured log events (5):**
- `postprocessing_correction_triggered` (with `original_response_first_50`)
- `postprocessing_correction_passed`
- `postprocessing_correction_stripped`
- `postprocessing_correction_failed`
- `post_gen_safety_override` (with `exposed_content_first_100`)
- All include `user_id`, `conversation_id`, `persona_slug`

**Trade-offs accepted (documented):**
- Brief Section 5.7 violation exposure during streaming (~17% of messages may briefly show violating content before correction)
- 0.1-2s persona content exposure before post-gen safety override
- Mid-stream errors → partial message + error event, no retry
- Regen-also-fails: user sees streamed content, DB saves stripped

All 19 prior PATH A features remain live. See v12 §6 / v9 §6 for full feature list.

---

## 7. Persona error messages

All 9 personas have `llm_unavailable` error messages in DB. Unchanged from v12 §7.

---

## 8. LLM provider validation

Unchanged from v12 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 9. Locked decisions (as of 2026-05-28)

All 11 from v12 remain locked. New locked decisions from 2026-05-28 session:

**12. Rituals scope for launch (Option B)**
- Launch scope: 3 functional rituals + 1 placeholder
  - The Mirror (Jung Pro / Marcus Aurelius free preview, 3 lifetime)
  - The Counterview (Machiavelli Pro-only, no free preview)
  - Letter to Future Self (existing — keep current implementation)
  - Weekly Reading placeholder ("Coming this season" locked card)
- Common ritual spine: single-purpose, time-boxed, closed-loop; auto-save to F1 with ritual tag; house-persona (not user-chooseable); philosophical heritage positioning; NO gamification; Section 5.7 compliant; editorial layout (NO chat bubbles)
- The Mirror flow: Setup (280-char prompt) → Reflection (≤3 rounds, editorial passages) → Closing ("A line worth keeping" pull-quote) → CTAs: Begin again / Done / Convene the Council
- The Counterview flow: Setup → 2 rounds (≤4 sentences each, steelman-the-opposite) → 2-line closing "What shifted, what didn't"

**13. Weekly Reading = canonical F3/F4 (renamed, single feature)**
- Sunday 8am delivery, 150-250 words
- Rotating most-active-persona author + fallback "The Wise Room" house voice
- Sources: kept F2 insights + Mirror/Counterview closings + F1 saves
- Min 3 items else quiet-week; first-week = introduction letter (≥7 days post-signup)
- Surfaces: Sunday email + F3 inbox + F4 detail + Rituals tile
- Pro-only. "Remove this reading" option.

**14. Council Mode (post-launch Premium / Phase 5)**
- Dual entry: elevated "Convene the Council on this" CTA (after ≥5 user messages) + Today/Rituals tile
- Max 3 personas, sequential turns; optional synthesis card
- Initially Pro-only, may shift to Premium tier
- Heraclitus-secret-host idea PARKED to Phase 5

**15. Press further mode (PR-E)**
- Rename "Ask harder" → "Press further"
- Conversation-scoped MODE TOGGLE
- Header sub-pill state indicator (A-only)
- Chip stays default styling; pill is single source of truth

**16. Typography V1 scope (PR-F)**
- Scoped to labels/headers ONLY
- Body text untouched
- Per-component audit required during implementation

**17. Data collection policy (locked)**
- Name only at deferred prompt (PR-D2 — shipped)
- Optional "intention" question post-launch only if data shows persona matching benefit
- NO demographic data (age, gender, occupation)
- Conversational tone, single field, skippable
- GDPR data-minimization respected

**18. Brand rename: "Great Minds" → "The Wise Room" (in progress, separate thread)**

---

## 10. Reconciliation history

Unchanged from v12. See v12/v11/v9 §10 for C-RECON-1 through C-RECON-8.

---

## 11. PR4j BETA bypass system

Unchanged from v12 §11. BETA_GRANT_PRO_TO_ALL=true; TD-11 (tier consolidation) required before disabling.

---

## 12. Frontend architecture and performance context

### Today page — greeting and name personalization (NEW v13)

**PR-D — Greeting personalization (#129):**
- `apps/web/lib/useTimeGreeting.ts` — `getGreetingWithName(fullName, now?)` helper added
- Today page calls it with `user?.full_name`
- Derives first name via `full_name?.trim().split(/\s+/)[0]`
- Graceful fallback: null/empty/whitespace → "Good morning." (no trailing comma)

**PR-D2 — Name capture deferred prompt (#130):**
- `apps/web/components/today/NamePromptCard.tsx` — NEW FILE
  - Shows for nameless OTP users on Today (full_name null/empty/whitespace)
  - LOCKED COPY: "What should we call you?" / "First name" placeholder / "Save" / "Not now"
  - Animation: fade + maxHeight collapse on dismiss, 250ms/350ms, onTransitionEnd → onDismiss
  - Session-only dismissal (in-memory, not persisted)
  - Save flow: `api.updateMe` → `setUser` → animate out → `onDismiss`
- `apps/web/lib/store.ts` — `setUser: (user) => set({ user })` setter added
- `apps/web/lib/api.ts` — `api.updateMe(fullName: string)` method added
- Today page: conditional render with `namePromptInitialized` ref (one-time snapshot on load)

### Latency topology

Unchanged from v12 §12. Oregon migration DATABASE_URL switch still pending.

### Pull-to-refresh fix (PR4z)

Unchanged from v12.

---

## 13. Session metrics

### 2026-05-21-24 session

See v11 §13.

### 2026-05-25-26 session

See v12 §13.

### 2026-05-28 session

| Metric | Value |
|---|---|
| PRs merged | Bug #1 (#127), PR-A/Bug #4 (#128), PR-D (#129), PR-D2 (#130) |
| Production regressions | 0 |
| Migrations deployed | None |
| New frontend files | `NamePromptCard.tsx` (PR-D2) |
| New backend endpoints | `PATCH /api/v1/auth/me` + `UpdateMeRequest` schema (PR-D2) |
| Production incidents resolved | Upstash free-tier limit hit → upgraded to Pay-as-You-Go; ANTHROPIC_API_KEY missing from both services → re-added, redeployed, smoke tested |
| Strategic decisions locked | Rituals scope (Option B), Weekly Reading canonical spec, Council Mode, PR-E (Press further), PR-F (Typography V1), data collection policy, brand rename in progress |
| PR-D2 smoke test | PARTIALLY BLOCKED — OTP delivery failure to ote.gr; workaround: use gmail for testing |

---

## 14. Known bugs (active)

### Carried from v12

- **BUG-012** — Zustand hydration race (hard refresh / direct URL on protected routes flashes to /auth). TD-10. PR4ai deferred (too risky). Approach requires Netlify preview smoke test.

### Closed this session

| ID | Description | Resolution |
|---|---|---|
| Bug #1 | BottomSheet history.back navigation race — picker → choose persona → navigation killed | PR #127 merged — `router.push` fires first, then state setter triggers cleanup which finds `history.state.modal !== 'bottom-sheet'` and skips `history.back()`. Verified working on mobile Safari. |

### New issues (2026-05-28)

| ID | Description | Status |
|---|---|---|
| OTP-01 | OTP delivery failure for ote.gr (Greek ISP) — send fails before DB insert | Under investigation. Workaround: use gmail for testing. Not related to any PR code changes. |

### No code-introduced regressions in 2026-05-28 session.

---

## 15. Environment variables

### Backend (Render)

```
DATABASE_URL                  Supabase — status unconfirmed post-v12
                               If Ireland: aws-0-eu-west-1.pooler.supabase.com:5432
                               If Oregon: aws-0-us-west-2.pooler.supabase.com:5432
                               Oregon DATABASE_URL switch not confirmed in 2026-05-28 session

REDIS_URL                     ✅ Set (Upstash, Pay-as-You-Go as of 2026-05-27)
                               ⚠️ Was free tier; hit 500k/month limit on 2026-05-27 → worker crashed
                               Upgraded to $0.2/100k commands. Set up 80% quota alert (TODO — see open issues).

RESEND_API_KEY                ✅ Set
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>"
JWT_SECRET                    ✅ Set
ANTHROPIC_API_KEY             ✅ Re-added 2026-05-27/28 (was missing — see §4 note)
                               ⚠️ Disappeared between May 25-27 (cause unconfirmed — possibly blueprint sync).
                               Re-added to philosopher-api AND philosopher-worker. Both redeployed.
                               Production smoke test: chat + title generation confirmed working.

ANTHROPIC_MEMORY_MODEL        "claude-haiku-4-5-20251001"
PHENOMENOLOGY_BRIDGE_ENABLED  (state unverified)

FRONTEND_URL                  "https://thinkalike.netlify.app"

BETA_GRANT_PRO_TO_ALL         "true"
                               All users treated as Pro. Toggle "false" before paid launch.
                               Requires TD-11 refactor before toggling.

GOOGLE_OAUTH_ENABLED          "false"
GOOGLE_CLIENT_ID              (placeholder)
GOOGLE_CLIENT_SECRET          (placeholder)

STRIPE_SECRET_KEY             ✅ Set
STRIPE_WEBHOOK_SECRET         ✅ Set
STRIPE_PRICE_PRO_MONTHLY      ✅ Set — €14.90/mo
STRIPE_PRICE_PRO_YEARLY       ✅ Set — €149/yr
STRIPE_PRICE_PREMIUM_MONTHLY  ✅ Set — placeholder; Premium deferred

BASE_URL                      ⚠️ DEPRECATED (PR4k) — no app code reads it
ANTHROPIC_MODEL (config.py)   ⚠️ ORPHANED — not read by conversation_service.py (TD-03)
```

**render.yaml sync:false for secrets — PENDING.** See HANDOFF_BRIEF_v13 §open-issues. All secrets above are vulnerable to accidental sync overwrite until render.yaml is updated.

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set
```

---

## 16. Key file paths (production codebase)

### Backend (apps/api/)

All v12 paths apply. Additions since v12:

- `routers/auth.py` — `PATCH /api/v1/auth/me` endpoint added (PR-D2 #130)
- `schemas/__init__.py` — `UpdateMeRequest` with `field_validator` (trim + non-empty + max 100 chars) added (PR-D2 #130)
- `services/conversation_service.py` — real-time streaming + correction flow (PR-A #128)

### Frontend (apps/web/)

All v12 paths apply. Additions and changes since v12:

- `app/app/(tabs)/today/page.tsx` — greeting with name (PR-D #129); NamePromptCard conditional render with `namePromptInitialized` ref (PR-D2 #130); Bug #1 fix: `router.push` before `setPickerOpen(false)` (#127)
- `app/app/(tabs)/reflections/page.tsx` — Bug #1 fix applied (#127)
- `components/today/NamePromptCard.tsx` — NEW FILE (PR-D2 #130)
- `lib/useTimeGreeting.ts` — `getGreetingWithName` helper added (PR-D #129)
- `lib/api.ts` — `SSEEventCorrection` type + `api.updateMe` method added (PR-A + PR-D2)
- `lib/store.ts` — `isCorrecting`, `correctionContent`, `setCorrection`, `appendCorrectionContent`, `resetStreaming` updates + `setUser` setter (PR-A + PR-D2)
- `lib/useStream.tsx` — correction event routing, `contentBeforeCorrection` fallback (PR-A #128)
- `components/chat/StreamingBubble.tsx` — correction visual (PR-A #128)
- `app/globals.css` — `@keyframes fade-in` added (PR-A #128)

---

## 17. Note: KIEN is a SEPARATE project — DELETED

Unchanged from v12. Deleted 2026-05-26. Historical note only.

---

## 18. CLAUDE.md violations log

### Carried from v12

- 2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` (C3a)
- 2026-05-23 — PR4p bundled two logical changes (P-02 violation)
- 2026-05-23 — PR4q empty commit due to stale local main (P-01 violation)

### 2026-05-28 session

No new CLAUDE.md violations.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **Oregon migration** — migrate remaining tables + source_chunks re-ingest + DATABASE_URL switch (unconfirmed; not addressed in 2026-05-28 session)
- [ ] **Post-switch smoke test** (login, chat, rituals, share, library)
- [ ] **bugfixes-3 — auth race fix** (TD-10; PR4ai deferred; preview smoke test required)
- [ ] **End-to-end Stripe sandbox test**
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
- [ ] **PR-D2 production smoke test** — PENDING (blocked by OTP delivery failure to ote.gr). Workaround: test with gmail address.

### Open items (P1)

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

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch)
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit
- [ ] All v12 TD items not listed above (see IMPLEMENTATION_BACKLOG_v13.md)

### Closed items (2026-05-28) — additions to v12 closed list

- [x] **CLOSED 2026-05-28** — Bug #1 (#127): BottomSheet history.back race fixed; verified on mobile Safari
- [x] **CLOSED 2026-05-27** — Upstash quota incident: free tier limit hit → Pay-as-You-Go upgrade; worker healthy
- [x] **CLOSED 2026-05-27/28** — ANTHROPIC_API_KEY incident: re-added to both services; production smoke tested
- [x] **CLOSED 2026-05-28** — Bug #4 / PR-A (#128): real-time streaming + inline correction; 4/4 smoke scenarios passed
- [x] **CLOSED 2026-05-28** — PR-D (#129): greeting personalization with first name; live in production
- [x] **CLOSED 2026-05-28** — PR-D2 (#130): name capture deferred prompt; merged to production (smoke test partially blocked by OTP issue)

---

**End of PROJECT_STATE v13.** Authoritative as of 2026-05-28. Supersedes `PROJECT_STATE_v12.md` (preserved as historical reference).
