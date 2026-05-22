# PHILOSOPHER — Project State v10

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v10 = v9 baseline (2026-05-20) + 2026-05-21/22 session delta (PR3a–PR4h shipped; cron hotfix; Render Background Worker deployed; migration 012 applied; 5 new backend endpoints; 7 new frontend components; cost shift to $14/mo Render).**
>
> **Generated:** 2026-05-22
>
> **Last updated:** 2026-05-22 (v10 sync — PR3a #80 through PR4h + cron hotfix + Render Background Worker deployment; see §11 for worker details, §2a for per-PR summary)

> **v10 conflict resolution rule:** Where v10 conflicts with v9, v10 wins. Production reality always wins over docs.

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
| LLM | Anthropic Claude — wired and live for chat + title generation + memory extraction |
| Embeddings | OpenAI text-embedding-3-small (corpus ingested 2026-05-17 — 2476 chunks) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage |
| Billing | Stripe (sandbox — checkout + portal + webhook live; live mode migration pending) |
| Email | Resend (free tier, test sender — custom domain pending) |
| Analytics | PostHog (configured, unused) |

### Hosting

| Service | Detail |
|---|---|
| **Frontend (canonical)** | Netlify (project: thinkalike, URL: thinkalike.netlify.app). Auto-deploys from main. |
| ~~Frontend (legacy): Vercel~~ | **DISCONNECTED 2026-05-10** |
| **Backend (web service)** | Render Starter — `philosopher-api-z9l9.onrender.com` · `srv-d7ijct6gvqtc739a0pdg` · Oregon · $7/mo |
| **Background Worker** | Render Starter — `philosopher-worker` · Oregon · $7/mo · ARQ + APScheduler |
| **Database** | Supabase project `plecolxlzshkfvybszgs` (eu-west-1, paid). Direct asyncpg — NOT Supabase Data API. |
| **Cache (Redis)** | Upstash `philosopher-prod` (eu-west-1, free tier). OTP rate limiter + ARQ job queue. |
| **Email (Resend)** | RESEND_API_KEY + FROM_EMAIL set. Currently `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain pending. |

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-21/22** — PR4h (splash redesign, full-bleed chesterfield hero). Prior: PR4g #90 (saved-line picker), PR4f #89 (swipe-to-delete), PR4e #88 (Sign Up/In distinction), PR4d #87 (share card 1080×1350), cron hotfix #86, PR4c #85 (UX polish bundle), PR4b #84 (Today's topic card), PR4a #83 (conv-not-found fix + 422 + safe-area), PR3c #82 (rituals + scheduled emails), PR3b #81 (share screenshot), PR3a #80 (mobile polish wave).
- **Has paying users:** No
- **Has free trial users:** No

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v9. See v9 §2 / v8 §2 Block A table for detail. Mode-aware copy update in PR4e: splash CTAs pass `?mode=signup` / `?mode=signin`; auth page renders "Create your account." vs "Welcome back." accordingly.

### Block B — Onboarding spine: SHIPPED + POLISH COMPLETE

6/6 functional, mobile polish wave complete (PR3a). Visual closure achieved.

### Block C — Chat backend: COMPLETE (8/8 backend items)

All Block C backend items live. Block C frontend complete (C5a/b/c/d merged 2026-05-16/17). RAG infrastructure live (migration 008). C3b corpus ingestion complete (2476 chunks).

See v9 §2 Block C table for full item-by-item status.

---

## 2a. Shipped since v9 (PR3a through PR4h)

This section captures all work merged after the v9 docs sync (commit `92fb821`, 2026-05-20).

### PR3a — #80 — B1/B3/B6 mobile bug fixes + polish + share button

**Commit:** `3c6d48e` · **Date:** 2026-05-20

Pre-PR3b foundation wave. Addressed mobile walkthrough findings from v9 backlog:
- Today page (`today/page.tsx`): layout and copy polish
- Welcome page (`welcome/page.tsx`): minor cleanup
- Auth page (`auth/page.tsx`): minor fix
- `SavedLineCard.tsx`: share button and layout polish

This PR represents closure of the v9 "consolidated polish PR" (Block B visual closure).

---

### PR3b — #81 — Share screenshot generation + cross-persona refactor + free tier limit

**Commit:** `cf5a756` · **Date:** 2026-05-20

**Backend:**
- New `POST /api/v1/share` endpoint (`routers/share.py`)
- New `services/image_service.py` — generates 1080×1080 PNG share card (Cormorant Garamond Italic for persona name/intro, Lora Regular for quote body, persona portrait circle, Bronze divider, wordmark, URL, date)
- Static assets committed to backend: `apps/api/static/fonts/` (CormorantGaramond-Italic.ttf, CormorantGaramond-Medium.ttf, Lora-Regular.ttf), `apps/api/static/personas/` (9 persona portraits)
- New tests: `tests/routers/test_share.py` (136 lines), `tests/services/test_image_service.py` (110 lines); `test_conversation_service.py` +77 lines

**Frontend:**
- `SourceLineModal.tsx` refactored out of chat — now a standalone component
- `SavedLineCard.tsx` share button wired to new API
- `PersonaPickerSheet.tsx` extended
- Free tier conversation limit enforcement (today/page.tsx)

---

### PR3c — #82 — Rituals card + send-to-future-self + BottomSheet + scheduled emails

**Commit:** `5acda61` · **Date:** 2026-05-21

**Backend:**
- **Migration 012** (`012_scheduled_emails`) — new `scheduled_emails` table (see §4)
- `routers/scheduled_emails.py` — `POST`, `GET`, `DELETE /api/v1/scheduled-emails` (Pro gate on POST, soft-cancel on DELETE)
- `services/template_service.py` — `render_future_self_email()` Jinja2 renderer
- `apps/api/templates/future_self_email.html` — Jinja2 email template (table-layout for Outlook compat, autoescape, parametrized footer via PUBLIC_ASSET_BASE_URL)
- `workers/cron.py` — gains two new APScheduler jobs: `dispatch_ritual_reminders` (08:00 UTC daily) + `send_pending_future_self_emails` (every 5 min); plus `deactivate_stale_memories` (Sunday 03:00 UTC) + `reconcile_stripe_subscriptions` (every 6h) were also wired in this PR
- `config.py` — `PUBLIC_ASSET_BASE_URL` env var added
- 16 new tests: `tests/routers/test_scheduled_emails.py` (281 lines) + `tests/services/test_cron_pending_emails.py` (294 lines)

**Frontend:**
- `components/ui/BottomSheet.tsx` — reusable framer-motion AnimatePresence slide-up bottom sheet
- `components/personas/PersonaPickerSheet.tsx` — refactored to use BottomSheet
- `components/rituals/RitualScheduleSheet.tsx` — schedule letter form (lazy-load saved lines, datetime, toast on success, 90vh maxHeight)
- `components/today/RitualsCard.tsx` — 3-row card: "Send to future self" (functional, Pro gate → /app/upgrade), "Emerging Patterns" (locked shell), "Weekly Letter" (locked shell)
- `today/page.tsx` — renders RitualsCard 4th (after "Your Reflections")
- `account/page.tsx` — "Scheduled letters" card between Subscription and Sign Out
- `app/app/scheduled-letters/page.tsx` — list view with pending/sent sections + cancel action
- `lib/api.ts` — `ScheduledEmailCreate/Out/ListItem` interfaces + `createScheduledEmail/listScheduledEmails/cancelScheduledEmail` methods

---

### PR4a — #83 — Conv-not-found fix + 422 error formatting + mobile safe-area

**Commit:** `7083f16` · **Date:** 2026-05-21

Three bug fixes:

1. **Conv-not-found fix** — New `GET /api/v1/conversations/{id}` endpoint. Chat init now fetches a single conversation directly instead of searching the top-50 `GET /conversations` list. Fixes "Conversation not found" for users with 50+ conversations (new conv has NULL `last_message_at` and lands outside the ordered LIMIT 50 window). 90 new backend tests.

2. **422 Pydantic error formatting** — `api.ts request()` now formats FastAPI 422 validation errors (detail is array, not string) into readable `field: msg` strings instead of `"[object Object]"`.

3. **Mobile safe-area** — `BottomSheet.tsx` `maxHeight` switched from `vh` to `svh` so `90svh` does not overflow the visible viewport on iOS Safari/Chrome Android when the address bar is visible. `env(safe-area-inset-bottom)` padding added to `RitualScheduleSheet` submit footer for devices with a home indicator.

---

### PR4b — #84 — Today's topic card + persona picker + skip_opening flag

**Commit:** `efd5b94` · **Date:** 2026-05-21

- **`TodaysTopicCard`** component (`components/today/TodaysTopicCard.tsx`) — replaces static "Today's question" display. User's initials in a 40×40 Bronze circle, expanding textarea, faded day-deterministic placeholder, "Reflect" button → `PersonaPickerSheet`
- **`skip_opening: bool`** added to `ConversationCreate` schema and `conversation_service.create()`. When `True`: bypasses dedup check (always fresh row) and suppresses the opening_invocation assistant bootstrap message
- **`PersonaPickerSheet`** extended with optional `onSelect` prop: when provided, delegates conversation creation to parent instead of calling `createCrossPersonaConversation` directly
- **`initials.ts`** helper (`lib/initials.ts`) — `deriveInitials(displayName)` for user avatar
- Auto-send from localStorage draft: `chat/conv/[id]/page.tsx` reads `today_topic_draft_{id}` from localStorage and fires it once after `isReady`
- 3 new backend pytest cases: `skip_opening` with no message, with message, and dedup bypass (Section H in `test_conversation_service.py`)

---

### PR4c — #85 — UX polish bundle (7 items)

**Commit:** `5a95f1c` · **Date:** 2026-05-21

1. **Rename:** 'Send to future self' → 'Letter to future self' in `RitualsCard` + `RitualScheduleSheet`
2. **5-year scheduling max:** Backend validator + frontend `maxDate` + helper text (was 1 year)
3. **`AppHeader` component** (`components/layout/AppHeader.tsx`) — 'Great Minds · Day, Mon DD' header added to all 4 tab pages (Today, Library, Reflections, Account)
4. **Note placeholder simplified:** 'What do you want to remember?' + `placeholder:text-charcoal/40`
5. **Reflections card buttons** (Revisit / Ask another mind / Share) normalized to same Charcoal token
6. **Auth back-button fix:** `router.push` → `router.replace` in verify + disclaimer flows
7. **Chat error link:** 'Back to conversations' → 'Home' routing to `/app/today`

Backend: schema validator `_TOO_FAR` updated to 6 years; `test_validator_accepts_4_years` added.

---

### Cron hotfix — #86 — cron.py `enqueue_job()` fix

**Commit:** `c0b716a` · **Date:** 2026-05-21

Single-line fix: `enqueue()` → `enqueue_job()` on the `daily_rituals` APScheduler job. ARQ's `ArqRedis` class uses `enqueue_job()`, not `enqueue()`. Without this fix, the daily ritual reminder cron would crash with `AttributeError` on every execution. Applied immediately before the Render Background Worker was brought online.

**Changed:** `apps/api/workers/cron.py` — 1 line

---

### PR4d — #87 — Share card 1080×1350 portrait

**Commit:** `f2e90b4` · **Date:** 2026-05-21

- Canvas 1080×1080 → **1080×1350** (4:5 aspect ratio, IG-optimal)
- Portrait: 240px @ y=80 → 200px @ y=120 (lighter visual weight)
- Footer block **bottom-anchored** 170px from bottom: divider y=1180, attribution y=1208, wordmark y=1248, URL y=1280, date y=1300
- URL/date colors: `INK_60/INK_50` → **`BRONZE_60/BRONZE_50`** (on-brand opacity)
- `CANVAS_WIDTH` / `CANVAS_HEIGHT` constants added; `FOOTER_TOP_Y` derivation refactored
- Tests: 1080×1350 dimension assertion + 15–300KB byte range test added; `sample_share.png` fixture regenerated

---

### PR4e — #88 — Sign Up / Sign In distinction

**Commit:** `09a779c` · **Date:** 2026-05-21

- Splash CTAs now pass `?mode=signup` and `?mode=signin` to `/auth`
- `/auth` page reads `mode` query param and renders:
  - `signup` → "Create your account."
  - `signin` → "Welcome back."
- `AuthForm` wrapped in `Suspense` for Next.js `useSearchParams` compatibility
- `apps/web/app/page.tsx` CTA hrefs updated

---

### PR4f — #89 — Swipe-to-delete on Reflections + Library with undo toast

**Commit:** `947c3d1` · **Date:** 2026-05-21

- **`SwipeableRow`** component (`components/ui/SwipeableRow.tsx`) — framer-motion x-drag, bg-safety color reveal behind row, Trash2 icon, spring-back below threshold, slide-off above −80px
- **Reflections:** each `SavedLineCard` wrapped in `SwipeableRow`; optimistic remove via `pendingDeletes` set, 5s deferred API call, undo toast restores item and cancels `setTimeout`; uses `store.removeAfterDelete` for sync
- **Library `PastConversationsView`:** same pattern for `ConversationCard`; uses `store.setConversations` after confirmed delete
- **Discoverability hint:** first-row wiggle animation on first session render, gated by `sessionStorage` (`swipe_hint_seen_reflections` / `swipe_hint_seen_library`)
- Timer cleanup on unmount; error toast if API call fails after undo window

---

### PR4g — #90 — Saved-line picker with thumbnails + custom highlight

**Commit:** `c33af4b` · **Date:** 2026-05-21

- **`SavedLinePicker`** component (`components/rituals/SavedLinePicker.tsx`) — replaces native `<select>` in `RitualScheduleSheet`
- Inline expand/collapse picker: each row shows 28px persona portrait circle + truncated quote (single line collapsed, 2-line clamped expanded)
- **Selected row:** `bg-linen` tint (not checkmark) for visual indication
- Falls back to Bronze initial circle if portrait image fails to load
- Loads persona list via parallel `api.getPersonas()` call

---

### PR4h — Splash redesign with full-bleed chesterfield hero

**Commit:** `675f00a` · **Date:** 2026-05-21/22

- Drops 3-zone split (cream / image / dark) for single **full-bleed dark image background** with `chesterfield-hero.jpg`
- Minimal title overlay at top (white, Cormorant italic); outlined CTA + sign-in link at bottom
- Subtle gradient overlays at top and bottom for text legibility
- Mode-aware routing (`?mode=signup`, `?mode=signin`) preserved from PR4e
- a11y intact — all text is rendered HTML, not baked into the image
- **Changed:** `apps/web/app/page.tsx` only (33 insertions, 34 deletions)

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v9.

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli

See v9 §3 for full table and affinity weight signatures.

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
| **012** | **scheduled_emails table** | **2026-05-21** | **#82 (PR3c)** |

**alembic_version = `012_scheduled_emails`** (current HEAD as of 2026-05-21/22)

### New table added in migration 012

```
scheduled_emails        (NEW 2026-05-21, migration 012)
                        Per-user future-self letter scheduling record.
                        Powers the "Letter to future self" feature in RitualsCard.

  id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
  saved_line_id    UUID REFERENCES saved_lines(id) ON DELETE SET NULL
  persona_id       UUID NOT NULL REFERENCES personas(id) ON DELETE RESTRICT
  note             TEXT  (optional personal note from user)
  recipient_email  VARCHAR(320) NOT NULL
  scheduled_for    TIMESTAMP WITH TIME ZONE NOT NULL
  status           VARCHAR(16) NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','sent','failed','cancelled'))
  sent_at          TIMESTAMP WITH TIME ZONE
  failure_reason   TEXT
  created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
  updated_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()

  Index: ix_scheduled_emails_pending
         ON scheduled_emails (scheduled_for) WHERE status = 'pending'
         Partial index — covers only pending rows for efficient sweep query
```

### Prior migrations (001–011)

See `PROJECT_STATE_v9.md` §4 for full schema detail on migrations 001–011. All unchanged.

### Live database state (2026-05-22 session end)

```
alembic_version:        012_scheduled_emails ✓ (applied 2026-05-21, PR3c)
users count:            2 (founder, freetester)
personas count:         9 (all active)
conversations:          50+ (from testing sessions)
messages:               139+ (from testing sessions)
source_chunks:          2476 chunks across 7 personas (C3b complete 2026-05-17)
scheduled_emails:       0 (new table; no production users yet)
memory_entries:         wiring active; 0 organic entries
```

### RLS state

**RLS DISABLED on all public tables.** Mitigation: frontend goes exclusively through the FastAPI gateway; no Supabase anon key is present in the frontend bundle. See v9 §4 for the forward-looking warning.

---

## 5. Backend endpoints

```
POST /api/v1/auth/register             (legacy — passwordless flow preferred)
POST /api/v1/auth/login                (legacy — passwordless flow preferred)
GET  /api/v1/auth/me                   (auth)
POST /api/v1/auth/otp/request          (public, rate-limited via Redis)
POST /api/v1/auth/otp/verify           (public)

GET  /api/v1/disclaimer/current        (public)
POST /api/v1/disclaimer/accept         (auth)

GET  /api/v1/personas                  (public — returns all 9 active personas)

GET  /api/v1/preferences               (auth)
POST /api/v1/preferences               (auth)
GET  /api/v1/preferences/matches       (auth)

POST /api/v1/conversations             (auth — create conversation; accepts skip_opening: bool [PR4b])
GET  /api/v1/conversations             (auth — list conversations, max 50)
GET  /api/v1/conversations/{id}        (auth — fetch single conversation by ID [NEW — PR4a])
GET  /api/v1/conversations/{id}/messages   (auth — fetch message history)
POST /api/v1/conversations/{id}/messages   ← CANONICAL SEND-MESSAGE (SSE streaming)
DELETE /api/v1/conversations/{id}          (auth — soft delete)

POST /api/v1/billing/checkout          (auth — create Stripe Checkout session)
POST /api/v1/billing/portal            (auth — open Stripe Customer Portal)
POST /api/v1/billing/webhook           (public — Stripe webhook handler; 6 events)

POST /api/v1/share                     (auth — generate share card PNG [NEW — PR3b])

POST /api/v1/scheduled-emails          (auth, Pro gate — schedule future-self email [NEW — PR3c])
GET  /api/v1/scheduled-emails          (auth — list user's scheduled emails [NEW — PR3c])
DELETE /api/v1/scheduled-emails/{id}   (auth — soft-cancel a scheduled email [NEW — PR3c])

POST /api/v1/admin/backfill-titles     (admin — backfill auto-generated titles)

GET  /health                           (public)
```

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v9 §6. See v9 for full architecture diagram and feature list.

One addition: `skip_opening: bool` on `POST /api/v1/conversations` (the *create* endpoint, not send-message). When `True`, `conversation_service.create()` bypasses dedup check and suppresses the opening invocation assistant message.

---

## 7. Persona error messages

Unchanged from v9 §7. All 9 persona-voiced `llm_unavailable` messages stored in DB.

---

## 8. LLM provider validation

Unchanged from v9 §8. Workbench A/B test 2026-05-15: Haiku 23/24, Sonnet 24/24.

---

## 9. Locked decisions (as of 2026-05-22)

Unchanged from v9 §9. All 10 decisions still locked. No new locked decisions in PR3/PR4 wave.

---

## 10. Reconciliation history

Unchanged from v9 §10. C-RECON series complete; no new reconciliation events.

---

## 11. Worker deployment (NEW — 2026-05-21/22)

### Render Background Worker

A Render Background Worker was deployed alongside the main web service to handle async task processing via ARQ and APScheduler cron jobs.

| Property | Value |
|---|---|
| Service name | `philosopher-worker` |
| Render service ID | [srv-XXXX — founder to fill in] |
| Region | Oregon (us-west-2) |
| Tier | Starter ($7/mo) |
| Runtime | Python 3.12, ARQ + APScheduler |
| Entry point | `apps/api/workers/arq_worker.py` — `WorkerSettings` class |

### ARQ tasks registered in `WorkerSettings.functions`

| Task function | Trigger | Description |
|---|---|---|
| `generate_conversation_title` | Enqueued from `stream_response()` when `message_count == 0` | Generates 4–7 word title from first 4 messages via `llm_client.complete()` (Haiku) |
| `extract_memory_task` | Enqueued from `stream_response()` after every response | Extracts and stores memory entries from user/assistant exchange via `memory_service.extract_and_store()` |
| `generate_insight_task` | **Not yet enqueued anywhere** | Synthesizes insight from ≥4 recent memory entries; orphan task pending organic accumulation |
| `send_ritual_reminder_task` | Enqueued by APScheduler `dispatch_ritual_reminders` cron | Sends ritual reminder email via Resend to a specific user/ritual pair |

### APScheduler cron jobs (4 total, wired in `cron.py`)

| Job ID | Schedule | Function | What it does |
|---|---|---|---|
| `daily_rituals` | 08:00 UTC daily | `dispatch_ritual_reminders` | Finds Pro+ users with recent ritual activity (36h window); enqueues `send_ritual_reminder_task` per user/ritual pair |
| `stale_memory` | Sunday 03:00 UTC | `deactivate_stale_memories` | Sets `is_active = False` on memory entries older than 90 days with `confidence < 0.6` |
| `stripe_reconcile` | Every 6 hours | `reconcile_stripe_subscriptions` | Fetches live Stripe subscription status for all active/trialing/past_due subscriptions; corrects drift from missed webhook events |
| `future_self_emails` | Every 5 minutes | `send_pending_future_self_emails` | Delivers `scheduled_emails` WHERE `scheduled_for <= NOW()` AND `status = 'pending'`; processes up to 50 per run, oldest-first; calls `send_email()` directly (not via ARQ) |

**Cron hotfix applied:** `cron.py` `enqueue()` → `enqueue_job()` for `daily_rituals` (commit `c0b716a`). This was applied immediately before the worker was brought online — without it, every `dispatch_ritual_reminders` execution would crash with `AttributeError`.

---

## 12. Known issues (active)

### Memory extraction JSON parse (pending verification)

`extract_memory_task` calls `memory_service.extract_and_store()`, which parses LLM output as JSON. If the LLM wraps its response in markdown fences (` ```json ... ``` `), the `json.loads()` call will fail. A defensive strip is not yet applied. **Status:** pending verification with fresh task logs from the deployed worker. Only implement the fix if logs confirm the issue persists.

### BUG-011 — `safety_events.message_id` always NULL

Carried from v9. Minor cleanup. Safety events log correctly by user_id, conversation_id, and timestamp; FK not wired.

### Tech debt (TD-01 through TD-09)

Carried from v9. See `IMPLEMENTATION_BACKLOG_v10.md` §6 for full list.

---

## 13. Session metrics

### PR3a–PR4h wave (2026-05-20 to 2026-05-22)

| Metric | Value |
|---|---|
| PRs merged | 12 (PR3a, PR3b, PR3c, PR4a, PR4b, PR4c, cron hotfix, PR4d, PR4e, PR4f, PR4g, PR4h) |
| Backend test count | 292 (v9) → **362** (+70; PR3b/3c/4a/4b/4c additions) |
| Frontend test count | 43 → **43** (unchanged; no frontend test files in PR3/PR4 wave) |
| New backend endpoints | 5 (GET /conversations/{id}, POST /share, POST/GET/DELETE /api/v1/scheduled-emails) |
| New migrations | 1 (012_scheduled_emails) |
| New frontend components | 7 (AppHeader, TodaysTopicCard, SwipeableRow, SavedLinePicker, BottomSheet, RitualScheduleSheet, RitualsCard) |
| New backend services | 2 (image_service.py, template_service.py) |
| Render infrastructure | Background Worker deployed (Starter, Oregon, $7/mo) |

---

## 14. Cost overview

| Service | Tier | Monthly cost |
|---|---|---|
| Render Web Service (`philosopher-api-z9l9`) | Starter | $7/mo |
| Render Background Worker (`philosopher-worker`) | Starter | $7/mo |
| Supabase | Paid (eu-west-1) | As per Supabase pricing |
| Upstash Redis | Free | $0 |
| Anthropic API | Pay-per-use | Variable (Haiku + Sonnet) |
| OpenAI Embeddings | Pay-per-use | ~$0.025 one-time (corpus ingested 2026-05-17) |
| Resend | Free tier | $0 (test sender) |
| **Total fixed (Render only)** | | **$14/mo** |

---

## 15. Environment variables

### Backend (Render)

```
DATABASE_URL                  ✅ Set (Supabase pooler)
REDIS_URL                     ✅ Set (Upstash)
RESEND_API_KEY                ✅ Set
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>" — test sender
JWT_SECRET                    ✅ Set
ANTHROPIC_API_KEY             ✅ Set
ANTHROPIC_MEMORY_MODEL        "claude-haiku-4-5-20251001"
PHENOMENOLOGY_BRIDGE_ENABLED  ⚠️ State unverified (was true 2026-05-04/05)
STRIPE_SECRET_KEY             ✅ Set (test mode)
STRIPE_WEBHOOK_SECRET         ✅ Set (test mode)
STRIPE_PRICE_PRO_MONTHLY      ✅ Set — €14.90/mo price ID
STRIPE_PRICE_PRO_YEARLY       ✅ Set — €149/yr price ID
STRIPE_PRICE_PREMIUM_MONTHLY  ✅ Set — placeholder
PUBLIC_ASSET_BASE_URL         ✅ Set (added PR3c — used by email template for portrait URLs)

ANTHROPIC_MODEL (config.py)   ⚠️ ORPHANED — not read by conversation_service.py
                               Default: "claude-sonnet-4-20250514" (stale Sonnet 4)
                               conversation_service.py uses MODEL_FREE/MODEL_PRO literals.
                               Update or remove before it misleads anyone (TD-03).
```

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set (test mode)
```

---

## 16. Key file paths (production codebase)

### Backend (apps/api/) — additions since v9

**New services:**
- `services/image_service.py` — share card PNG generation (PR3b); updated to 1080×1350 in PR4d
- `services/template_service.py` — `render_future_self_email()` Jinja2 renderer (PR3c)

**New routers:**
- `routers/share.py` — `POST /api/v1/share` (PR3b)
- `routers/scheduled_emails.py` — `POST/GET/DELETE /api/v1/scheduled-emails` (PR3c)

**New templates:**
- `templates/future_self_email.html` — Jinja2 email template (PR3c)

**New static assets:**
- `static/fonts/CormorantGaramond-Italic.ttf`
- `static/fonts/CormorantGaramond-Medium.ttf`
- `static/fonts/Lora-Regular.ttf`
- `static/personas/` — 9 persona portrait images

**Updated workers:**
- `workers/arq_worker.py` — `send_ritual_reminder_task` added; `WorkerSettings.functions` updated
- `workers/cron.py` — 4 APScheduler jobs wired (`dispatch_ritual_reminders`, `deactivate_stale_memories`, `reconcile_stripe_subscriptions`, `send_pending_future_self_emails`); enqueue_job hotfix applied

**Updated migrations:**
- `db/migrations/versions/012_scheduled_emails.py`

**Updated config:**
- `config.py` — `PUBLIC_ASSET_BASE_URL` added

### Frontend (apps/web/) — additions since v9

**New layout components:**
- `components/layout/AppHeader.tsx` — 'Great Minds · Day, Mon DD' header (PR4c)

**New Today components:**
- `components/today/TodaysTopicCard.tsx` — editable topic card with Bronze initials + persona picker (PR4b)
- `components/today/RitualsCard.tsx` — 3-row rituals card (PR3c)

**New UI components:**
- `components/ui/SwipeableRow.tsx` — framer-motion swipe-to-delete wrapper (PR4f)
- `components/ui/BottomSheet.tsx` — AnimatePresence slide-up sheet (PR3c)

**New ritual components:**
- `components/rituals/RitualScheduleSheet.tsx` — letter scheduling form (PR3c)
- `components/rituals/SavedLinePicker.tsx` — inline thumbnail picker (PR4g)

**New pages:**
- `app/app/scheduled-letters/page.tsx` — scheduled letters list view (PR3c)

**New lib:**
- `lib/initials.ts` — `deriveInitials()` helper (PR4b)

**Updated pages (key changes):**
- `app/page.tsx` — splash redesign (PR4h); mode-aware CTAs (PR4e)
- `app/auth/page.tsx` — mode-aware copy, Suspense wrapper (PR4e)
- `app/app/(tabs)/today/page.tsx` — TodaysTopicCard, RitualsCard (PR4b, PR3c, PR4c)
- `app/app/(tabs)/reflections/page.tsx` — SwipeableRow wrapping (PR4f); AppHeader (PR4c)
- `app/app/(tabs)/library/page.tsx` — SwipeableRow in PastConversationsView (PR4f); AppHeader (PR4c)
- `app/app/(tabs)/account/page.tsx` — Scheduled letters card (PR3c); AppHeader (PR4c)
- `app/app/chat/conv/[id]/page.tsx` — auto-send from localStorage draft (PR4b); 'Home' routing fix (PR4c)

### Files unchanged since v9 (carry forward)

All backend service files from v9 §15 (`conversation_service.py`, `rate_limit_service.py`, `persona_voice.py`, `tier_service.py`, `llm_client.py`, `safety_service.py`, `retrieval_service.py`, `memory_service.py`, `prompt_builder.py`) — unchanged in PR3/PR4 wave.

---

## 17. Note: KIEN is a SEPARATE project

Unchanged from v9 §16. Not to be confused with Philosopher / Great Minds.

---

## 18. CLAUDE.md violations log

No new violations in PR3/PR4 wave. Prior violation (2026-05-17 C3a silent deletion of `ingest_sources.py`) documented in v9 §16b and reconciled.

---

## 19. Open / Closed items

### Closed items (PR3a–PR4h wave, 2026-05-20 to 2026-05-22)

- [x] **CLOSED 2026-05-20** — PR3a: B1/B3/B6 mobile bug fixes + polish (consolidated polish PR)
- [x] **CLOSED 2026-05-20** — PR3b: Share screenshot generation endpoint live
- [x] **CLOSED 2026-05-21** — PR3c: Rituals card + scheduled emails backend + BottomSheet frontend
- [x] **CLOSED 2026-05-21** — Migration 012 (scheduled_emails) applied
- [x] **CLOSED 2026-05-21** — PR4a: Conv-not-found fix, 422 formatting, mobile safe-area
- [x] **CLOSED 2026-05-21** — PR4b: TodaysTopicCard + skip_opening flag
- [x] **CLOSED 2026-05-21** — PR4c: AppHeader on all 4 tabs; 'Letter to future self' rename; 5-year scheduling; auth back-button fix; chat 'Home' routing fix
- [x] **CLOSED 2026-05-21** — Cron hotfix: enqueue_job() fix applied
- [x] **CLOSED 2026-05-21** — PR4d: Share card 1080×1350, bottom-anchored footer, Bronze opacity
- [x] **CLOSED 2026-05-21** — PR4e: Sign Up / Sign In distinction + mode-aware email copy
- [x] **CLOSED 2026-05-21** — PR4f: Swipe-to-delete Reflections + Library with undo toast
- [x] **CLOSED 2026-05-21** — PR4g: Saved-line picker with thumbnails
- [x] **CLOSED 2026-05-21/22** — PR4h: Splash redesign, full-bleed chesterfield hero
- [x] **CLOSED 2026-05-21/22** — Render Background Worker deployed (philosopher-worker, Starter, Oregon)
- [x] **CLOSED 2026-05-21/22** — Web service upgraded to Render Starter ($7/mo)

### Open items (P0 — launch blockers)

- [ ] **Resend domain verification** — blocks cold beta OTP delivery for non-Gmail
- [ ] **Greek ΚΑΔ addition to ΕΕ company** — hard prerequisite for Stripe live mode (add software/digital ΚΑΔ via TAXISnet form Μ2)
- [ ] **Stripe live mode migration** — swap keys, re-register webhook, smoke test
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel)
- [ ] **Backfill-titles admin execution** — `POST /api/v1/admin/backfill-titles`
- [ ] **Cold smoke test with 5–7 fresh users**
- [ ] **Lawyer review** of ToS / Privacy / Disclaimer
- [ ] **DNS configuration** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety)
- [ ] **PHENOMENOLOGY_BRIDGE_ENABLED** flag state confirmation in Render env

### Open items (P1)

- [ ] **Memory extraction JSON parse fix** (defensive markdown fence strip — verify first)
- [ ] **Marketing copy + landing page** (A0 has minimal copy)
- [ ] **Wire `generate_insight_task`** (when ≥4 organic memory entries accumulate)
- [ ] **C6c cold-start screen** (demoted from P0 2026-05-18)
- [ ] **I1 Account hub build** (spec locked; tab bar reachable via D1)

### Open items (deferred)

- [ ] **Brand rebrand decision** (Great Minds saturation concern) — soft-blocks Resend domain choice, email template, share card wordmark
- [ ] **PR4d.1 share card vertical centering** (only if skeletal in production)

### Prior closed items (through v9)

See `PROJECT_STATE_v9.md` §17 for all closed items through 2026-05-20.

---

**End of PROJECT_STATE v10.** Authoritative as of 2026-05-22. Supersedes `PROJECT_STATE_v9.md` (preserved as historical reference).
