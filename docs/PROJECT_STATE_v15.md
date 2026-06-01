# PHILOSOPHER — Project State v15

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v15 = v14 baseline (2026-05-30) + 2026-06-01 session delta (Mirror feature shipped end-to-end: PRs #166–#173; migrations 017_create_mirrors + 018_user_mirror_host; 4 new Mirror endpoints; host picker live & verified; eligible-host config locked; Oregon DB confirmed live).**
>
> **Generated:** 2026-06-01 (v15 rotation)
>
> **Last updated:** 2026-06-01

> **v15 conflict resolution rule:** Where v15 conflicts with v14, v15 wins. Production reality always wins over docs.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive — do not write to it. All Render services must point to Oregon.**

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
  - "Take it to the Council" = locked teaser CTA only; Council remains parked premium (Phase 5).

**Supersedes prior facts:**
- `alembic_version` is now **`018_user_mirror_host`** (was `016_message_persona_id`). Two new migrations since v14: `017_create_mirrors` + `018_user_mirror_host`.
- The Mirror: was 🔴 BLOCKED on Brief #4 → now **🟢 SHIPPED**.
- 4 new Mirror endpoints: `GET /mirrors/latest`, `POST /mirrors/{id}/ring-true`, `GET /mirrors/hosts`, `POST /mirrors/host`.
- Live DB confirmed: Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` = legacy, inactive.

**PRE-LAUNCH BLOCKER added:**
- 🔴 `BETA_GRANT_PRO_TO_ALL=true` is ENABLED — must be disabled before any Stripe transaction is accepted. Requires TD-11 (tier resolution refactor) first.

---

## v14 Session Delta (2026-05-29)

> v14 = v13 baseline + 2026-05-29 session. Where v14 conflicts with v13, v14 wins.

**Shipped this session (all squash-merged):**
- **Typography PR-F** (`feat/typography-v1`, `feat/typography-phase2`) — chat reading text → 16px; Cormorant titles → font-medium (500); comprehension prose → 15px. Final scale: chat 16 / titles 500 / comprehension 15 / saved-lines 17 / chrome unchanged.
- **PR-B / C9 "Bring another mind"** (headline Pro feature) — mid-chat second opinion from another persona; the guest reply renders inline; the conversation continues with the home persona. Five PRs: backend engine (`feat/pr-b1-another-mind-backend`, #71ce6e3), picker + streaming UI (`feat/pr-b2-another-mind-ui`, #ff37f36), gate bugfix (`fix/another-mind-gate-backend-authority`, #225a68d), attribution (`feat/pr-b3-brought-in-attribution`) + live attribution (`feat/pr-b3v2-live-attribution`). Live-tested OK.
- **Cross-mind awareness** (`feat/cross-mind-awareness`, #cea8f29) — a persona now recognises a brought-in guest's words instead of mistaking them for its own. LLM history labels turns by another mind as "[Name]: ..."; a `CROSS_MIND_NOTE` is appended only when such turns exist; symmetric; the home path is byte-identical when no brought-in turns exist. No schema/SSE/storage change.

**Supersedes prior facts:**
- `alembic_version` is now **`016_message_persona_id`** (was `015_add_fk_indexes`). Migration 016 = nullable `messages.persona_id` FK → personas.id + index `ix_messages_persona_id`.
- New endpoint **POST /api/v1/conversations/{id}/another-mind** (SSE; Pro-gated → 403 `upgrade_required`; same-persona → 400; rate-limited to target). The single-home-send-endpoint statement still holds for the home path; this is a distinct additive endpoint.
- `conversation_service.py` now has TWO streaming entrypoints: `stream_response` (home) + `stream_another_mind` (guest); both apply cross-mind history labelling.

**File paths (additions/changes):**
- Backend: `db/migrations/versions/016_message_persona_id.py` (NEW), `models/__init__.py` (Message.persona_id + persona rel), `schemas/__init__.py` (MessageOut.persona_slug, AnotherMindCreate), `routers/conversations.py` (persona eager-load + persona_slug; POST /another-mind), `services/conversation_service.py` (stream_another_mind; `_build_lm_messages` / `CROSS_MIND_NOTE`).
- Frontend: `lib/api.ts`, `lib/useStream.tsx`, `lib/store.ts` (streamingBroughtInName), `components/chat/AnotherMindSheet.tsx` (NEW), `StreamingBubble.tsx`, `MessageList.tsx`, `QuickActionsRow.tsx`, both chat pages; typography across MessageBubble/SafetyBubble/ErrorMessage + ~21 titles + 11 comprehension lines.

**Newly logged items:**
- 🔴 **Systemic frontend `plan` reliability bug** — client `plan` getter unreliable on any route outside `(tabs)/layout.tsx` (where `SubscriptionBootstrap` runs); affects all client-side plan gates. Fix before paid launch. Ties to TD-11.
- 🟡 **Another-mind feature gate (post-beta)** — backend gates per-persona, NOT feature-level. Add a feature-level Pro gate before turning off `BETA_GRANT_PRO_TO_ALL`.
- ⏸ **Enhancement — switch to the brought-in mind** (persona switching mid-conversation). Post-validation only.

**Status:** C9 / PR-B COMPLETE; cross-mind awareness COMPLETE; typography PR-F COMPLETE. Critical path to revenue (unchanged, still open): cold-beta validation → live Stripe → TD-11 + another-mind feature gate → paid launch.

---

## v14 Addendum — Voice Overhaul (2026-05-30)

> Appended to v14 baseline. Where this conflicts with earlier v14 content, this addendum wins.

**Shipped this session (all merged to main):**

- **`check_brevity` wired into live post-stream path** — previously dead code; word bands were never enforced at runtime. Now called in the post-stream pipeline; enforcement is live for all 9 personas.
- **Global ending-variation rule in `system_base.jinja2`** — ~40% question / ~40% no-question / ~20% mixed endings enforced globally. Carve-out: personas whose own `ResponseSpec` mandates a question are exempt from the no-question bucket.
- **Socrates elenchus cycle upgraded** — prior spec mandated "exactly one question, no exceptions" (internal contradiction with the elenctic method). Upgraded to the full cycle: ask → synthesise → expose contradiction. Biography now gated under ANTI-FLEXING.
- **All 9 personas voice-tightened** — tighter bands, 2026-voice bullets, ANTI-FLEXING bullets, and `voice_calibration_examples` added across Marcus Aurelius, Socrates, Epictetus, Oscar Wilde, Carl Jung, Sigmund Freud, Simone de Beauvoir, Niccolò Machiavelli, Lao Tzu. Each persona's distinct cognitive signature preserved.

**Critical gap closed — Wilde, Machiavelli, Lao Tzu:**
These three personas previously had **no `ResponseLengthSpec`**, meaning `check_brevity` was skipped entirely for them. This session added a spec to each; brevity enforcement is now active for all 9 personas.

**Per-persona word bands (read from source):**

| Persona | standard (min–max) | first (max) | reflective (max) |
|---|---|---|---|
| Marcus Aurelius | 20–55 | 40 | 75 |
| Socrates | 20–55 | 35 | 70 |
| Epictetus | 20–55 | 35 | 70 |
| Oscar Wilde | 20–55 | 40 | 75 |
| Carl Jung | 25–60 | 40 | 80 |
| Sigmund Freud | 25–60 | 40 | 80 |
| Simone de Beauvoir | 30–65 | 50 | 90 |
| Niccolò Machiavelli | 25–60 | 40 | 80 |
| Lao Tzu | 15–45 | 35 | 70 |

**Personas pending author smoke-test post-deploy (voice changes live):**
Oscar Wilde, Carl Jung, Sigmund Freud, Simone de Beauvoir, Niccolò Machiavelli, Lao Tzu.

**Status:** Voice overhaul COMPLETE. Next major feature: Rituals (user-stated entry condition for beta — **scope not yet designed**; design with Claude chat first).

**INFRA ALREADY PRESENT (verified in live DB, project bvzeuwzqgnqcghvqghtb, 2026-05-30):**
- Tables `rituals` (4 rows) + `user_ritual_completions` (4) exist — rituals skeleton already built.
- `memory_entries` = 56 rows (worker actively producing).
- `insights` table EXISTS but is EMPTY (0 rows) — the progress/insight generator is either not running or not wired.
- The empty `insights` table is the likely leverage point for the "progress" payoff; investigate before building new.

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
- **Rituals tab:** Live (PR4o) — 4 ritual cards shown; **Mirror ✅ SHIPPED** (end-to-end live, PRs #166–#173); Counterview + Weekly Reading are placeholder-locked; Letter to Future Self is functional (ARQ delivery not yet wired).
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
| **016** | **messages.persona_id nullable FK → personas.id + ix_messages_persona_id** | **2026-05-29** | **PR-B / #71ce6e3** |
| **017** | **mirrors table: uq_mirrors_user_period_kind UNIQUE(user_id, period_start, kind); kind ∈ {weekly,preview}; status ∈ {generated,empty,suppressed}; payload JSONB; ring_true fields** | **2026-06-01** | **Mirror / #168** |
| **018** | **users.mirror_host_slug VARCHAR(100) NULL** | **2026-06-01** | **Mirror / #171** |

**alembic_version = `018_user_mirror_host`** (migration 018 added 2026-06-01, Mirror host storage)

### Oregon region migration — CONFIRMED LIVE

**Live DB = Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy, inactive.**

Oregon migration status (confirmed as of 2026-06-01):
- Schema: ✅ COMPLETE
- Reference data: ✅ COMPLETE
- User/app data: ✅ CONFIRMED LIVE (DATABASE_URL pointing to Oregon)
- source_chunks: separate task — re-ingest via existing OpenAI embeddings script (TD-22); status unconfirmed post-switch
- DATABASE_URL switch: ✅ CONFIRMED — pointing to Oregon pooler

⚠️ **Note:** ANTHROPIC_API_KEY disappeared from both services between 2026-05-25 and 2026-05-27 (cause unconfirmed — possibly blueprint sync without sync:false flag). Re-added manually and services redeployed on 2026-05-27/28. See §15 and HANDOFF_BRIEF_v14 §open-issues.

### Live database state (2026-06-01)

```
alembic_version:        018_user_mirror_host ✓
users count:            ~2-3 (founder + test accounts; no organic users yet)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          87+ (testing adds more)
messages:               227+ (testing adds more)
source_chunks:          2476 chunks across 7 personas (C3b, 2026-05-17)
mirrors:                NEW table (017); rows from preview cron
```

See v12 §4 for full table population status and FK ondelete detail. Unchanged.

### RLS state

**RLS DISABLED on all public tables.** Unchanged from v12.

---

## 5. Backend endpoints

Unchanged from v14, plus Mirror endpoints:

**GET /api/v1/mirrors/latest** — Returns the most recent mirror for the authenticated user
- Auth: `Depends(get_current_user)`
- Returns: mirror payload `{thread, moments}` or 204 if no mirror exists yet

**POST /api/v1/mirrors/{id}/ring-true** — Submit ring-true feedback for a mirror
- Auth: `Depends(get_current_user)`
- Stores moment resonance data in `mirrors.ring_true`; used for prompt tuning only

**GET /api/v1/mirrors/hosts** — Returns eligible mirror hosts for the authenticated user
- Auth: `Depends(get_current_user)`
- Returns: list of personas where `config.mirror_capable=true`
- Currently: Jung, Lao Tzu, Marcus Aurelius

**POST /api/v1/mirrors/host** — Set the user's preferred mirror host
- Auth: `Depends(get_current_user)`
- Request: `{host_slug: str}` — validated against eligible hosts list
- Writes to `users.mirror_host_slug`

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

Unchanged from v12 §12. **DATABASE_URL now confirmed pointing to Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2).**

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

### 2026-06-01 session — Mirror feature

| Metric | Value |
|---|---|
| PRs merged | #166 (prompt shape), #167 (voice), #168 (idempotent generator + migration 017), #169 (cron jobs), #170 (verdict-guard), #171 (host storage + endpoints + migration 018), #172 (cron uses user host), #173 (host picker UI) |
| Production regressions | 0 |
| Migrations deployed | 017_create_mirrors, 018_user_mirror_host |
| New tables | `mirrors` |
| New columns | `users.mirror_host_slug VARCHAR(100) NULL` |
| New endpoints | GET /mirrors/latest, POST /mirrors/{id}/ring-true, GET /mirrors/hosts, POST /mirrors/host |
| New backend files | Mirror router, `generate_weekly_mirror_task`, MIRROR_PROMPT template |
| New frontend files | Mirror page (`apps/web/app/app/mirror/page.tsx` updated), api.ts additions |
| Strategic decisions | Mirror eligible-host config locked (Jung/Lao Tzu/Marcus); MIRROR_PROMPT locked; verdict-guard scope clarified (Mirror-only) |

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
DATABASE_URL                  ✅ Supabase Oregon — aws-0-us-west-2.pooler.supabase.com:5432
                               Project: bvzeuwzqgnqcghvqghtb (us-west-2) — CONFIRMED LIVE
                               Ireland project plecolxlzshkfvybszgs (eu-west-1) = LEGACY / INACTIVE

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
                               ⚠️ MUST DISABLE before Stripe checkout smoke test.

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

**render.yaml sync:false for secrets — PENDING.** See HANDOFF_BRIEF_v14 §open-issues. All secrets above are vulnerable to accidental sync overwrite until render.yaml is updated.

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set
```

---

## 16. Key file paths (production codebase)

### Backend (apps/api/)

All v14 paths apply. Additions since v14:

- `routers/mirrors.py` — NEW: Mirror endpoints (GET /latest, POST /{id}/ring-true, GET /hosts, POST /host)
- `workers/tasks/generate_weekly_mirror_task.py` — NEW: ARQ Mirror generation task; idempotent; period_start to midnight UTC
- `db/migrations/versions/017_create_mirrors.py` — NEW
- `db/migrations/versions/018_user_mirror_host.py` — NEW
- `prompts/mirror_prompt.md` (or equivalent) — LOCKED MIRROR_PROMPT template
- `routers/auth.py` — `PATCH /api/v1/auth/me` endpoint added (PR-D2 #130)
- `schemas/__init__.py` — `UpdateMeRequest` schema (PR-D2 #130)
- `services/conversation_service.py` — real-time streaming + correction flow (PR-A #128)

### Frontend (apps/web/)

All v14 paths apply. Additions and changes since v14:

- `app/app/mirror/page.tsx` — Mirror feature page; tappable "Through {host}" header; bottom sheet host picker; ring-true UI (PRs #171–#173)
- `lib/api.ts` — Mirror API methods added: `getMirrorLatest`, `postRingTrue`, `getMirrorHosts`, `setMirrorHost` (PR #171 + #173)
- `app/app/(tabs)/today/page.tsx` — greeting with name (PR-D #129); NamePromptCard render (PR-D2 #130); Bug #1 fix (#127)
- `app/app/(tabs)/reflections/page.tsx` — Bug #1 fix (#127)
- `components/today/NamePromptCard.tsx` — NEW FILE (PR-D2 #130)
- `lib/useTimeGreeting.ts` — `getGreetingWithName` helper (PR-D #129)
- `lib/store.ts` — correction state + `setUser` setter (PR-A + PR-D2)
- `lib/useStream.tsx` — correction event routing (PR-A #128)
- `components/chat/StreamingBubble.tsx` — correction visual (PR-A #128)
- `app/globals.css` — `@keyframes fade-in` (PR-A #128)

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

### 2026-06-01 session (v15)

No new CLAUDE.md violations.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **🔴 TD-11 — Tier resolution unified refactor** (required before disabling BETA flag)
- [ ] **🔴 Disable BETA_GRANT_PRO_TO_ALL** — required before Stripe checkout smoke test
- [ ] **End-to-end Stripe sandbox test** (with BETA flag OFF)
- [ ] **source_chunks re-ingest** into Oregon via OpenAI embeddings script (TD-22); status unconfirmed post-switch
- [ ] **Post-Oregon smoke test** (login, chat, rituals/Mirror, share, library, RAG retrieval)
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

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch) — **escalated to P0 blocker; see above**
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit
- [ ] All v14 TD items not listed above (see IMPLEMENTATION_BACKLOG_v14.md)

### Closed items (2026-06-01) — additions to v14 closed list

- [x] **CLOSED 2026-06-01** — The Mirror shipped end-to-end (PRs #166–#173); migrations 017 + 018 deployed; host picker verified; eligible-host config locked
- [x] **CLOSED 2026-06-01** — Oregon DATABASE_URL confirmed live (`bvzeuwzqgnqcghvqghtb`, us-west-2)

### Closed items (carried from v14)

- [x] **CLOSED 2026-05-30** — Voice overhaul: check_brevity live; ending-variation rule; Socrates elenchus; all 9 personas tightened
- [x] **CLOSED 2026-05-29** — C9 PR-B "Bring another mind" + cross-mind awareness + typography PR-F
- [x] **CLOSED 2026-05-28** — Bug #1 (#127), Bug #4/PR-A (#128), PR-D (#129), PR-D2 (#130)
- [x] **CLOSED 2026-05-27** — Upstash quota incident; ANTHROPIC_API_KEY incident resolved

---

## 20. Pre-Launch Blockers

> These items gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [ ] **`BETA_GRANT_PRO_TO_ALL=true`** — currently all users are granted Pro tier regardless of subscription. Must be set to `false` before any Stripe transaction is processed. Requires TD-11 first.
- [ ] **TD-11 — Tier resolution unified refactor** — consolidate `get_current_user_plan` + `get_user_tier` into a single function. Both used by different endpoints with different semantics. Must precede BETA flag disable.
- [ ] **Another-mind feature gate** — backend gates per-persona, not feature-level. Add a feature-level Pro gate before disabling BETA bypass (otherwise non-subscribers can access the feature).
- [ ] **Systemic frontend `plan` reliability bug** — `plan` getter unreliable outside `(tabs)/layout.tsx`. Affects all client-side paywall gates. Fix before paid launch.
- [ ] **End-to-end Stripe sandbox test** — must be run with BETA flag OFF to verify real tier enforcement, checkout, portal, cancel, and tier downgrade flows.

---

**End of PROJECT_STATE v15.** Authoritative as of 2026-06-01. Supersedes `PROJECT_STATE_v14.md` (preserved as historical reference).
