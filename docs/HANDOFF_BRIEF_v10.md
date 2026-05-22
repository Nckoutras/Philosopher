# HANDOFF BRIEF v10 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-05-22
**Prior version:** `docs/HANDOFF_BRIEF_v9.md` (2026-05-20)
**Generated:** 2026-05-22

**Block trigger for v10 regen:** PR3a–PR4h wave (12 PRs), Render Background Worker deployment, migration 012, 5 new endpoints. Per §19.17 (addendum vs baseline regen rule): background worker deployment + new infrastructure layer is a sufficient regen trigger.

**Status:** Block A ✅ FULLY CLOSED. Block B ✅ SPINE + POLISH COMPLETE (PR3a). Block C ✅ FULLY COMPLETE (backend + frontend + RAG). Stripe sandbox ✅ COMPLETE (live mode migration pending). D1 ✅ COMPLETE. Share screenshot ✅ COMPLETE (PR3b). Scheduled emails backend ✅ COMPLETE (PR3c). Render Background Worker ✅ DEPLOYED. Migration 012 ✅ APPLIED. PR4a–PR4h ✅ ALL MERGED. **alembic_version = `012_scheduled_emails`.**

> **v10 conflict resolution rule:** Where v10 conflicts with v9 or earlier, v10 wins. Production reality always wins over docs.

---

## Changelog v9 → v10

### 2026-05-20 to 2026-05-22 — PR3a–PR4h wave

**12 PRs merged + 1 hotfix + background worker deployed.**

| Commit | PR | Description |
|---|---|---|
| `3c6d48e` | PR3a #80 | B1/B3/B6 mobile bug fixes + polish + share button (consolidated polish PR) |
| `cf5a756` | PR3b #81 | Share screenshot generation + `image_service.py` + `POST /api/v1/share` |
| `5acda61` | PR3c #82 | Rituals card + send-to-future-self + BottomSheet + scheduled emails (migration 012) |
| `7083f16` | PR4a #83 | Conv-not-found fix (`GET /conversations/{id}`) + 422 formatting + mobile safe-area |
| `efd5b94` | PR4b #84 | TodaysTopicCard + `skip_opening` flag + `PersonaPickerSheet` `onSelect` prop |
| `5a95f1c` | PR4c #85 | UX polish: AppHeader, 'Letter to future self', 5yr scheduling, auth back-button, Home routing |
| `c0b716a` | Hotfix #86 | `cron.py` `enqueue_job()` fix for `daily_rituals` job |
| `f2e90b4` | PR4d #87 | Share card 1080×1350 + bottom-anchored footer + BRONZE_60/BRONZE_50 |
| `09a779c` | PR4e #88 | Sign Up / Sign In distinction + mode-aware email copy |
| `947c3d1` | PR4f #89 | Swipe-to-delete Reflections + Library + undo toast + `SwipeableRow` |
| `c33af4b` | PR4g #90 | `SavedLinePicker` with thumbnails + custom highlight in `RitualScheduleSheet` |
| `675f00a` | PR4h | Splash redesign — full-bleed chesterfield hero |
| — | Operational | Render Background Worker deployed (`philosopher-worker`, Starter, Oregon, $7/mo) |
| — | Operational | Web service upgraded to Render Starter ($7/mo) |

---

## 1. Pre-Work Investigation Protocol

**This protocol is mandatory for all future multi-PR work on this project.**

Defined in `CLAUDE.md` at the repository root (PR #54, 2026-05-16). Every new code session must:

1. Enumerate all existing functionality in the same domain before writing any code
2. Read the actual source files — not rely on session memory or doc summaries
3. Report findings and stop for founder review if overlaps are found
4. Check cross-system dependencies (ARQ tasks, webhooks, admin endpoints, tests, frontend)

See `HANDOFF_BRIEF_v9.md` §1 for the full list of what this protocol caught during C-RECON reconciliation (4 real bugs avoided).

---

## 2. System architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 · TypeScript · Tailwind)              │
│  Netlify · thinkalike.netlify.app · auto-deploy from main   │
│  43 frontend tests (vitest)                                  │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTPS / REST + SSE
┌───────────────────────▼─────────────────────────────────────┐
│  Backend Web Service (FastAPI · Python 3.12)                 │
│  Render Starter · philosopher-api-z9l9.onrender.com         │
│  srv-d7ijct6gvqtc739a0pdg · Oregon (us-west-2) · $7/mo     │
│  362 backend tests (pytest)                                  │
│                                                              │
│  Routers: auth, conversations, personas, preferences,        │
│           billing, share, scheduled-emails, admin            │
│  Services: conversation, rate_limit, persona_voice, tier,    │
│            llm_client, safety, retrieval, memory,            │
│            image, template, stripe, prompt_builder           │
└──────┬──────────────────────┬───────────────────────────────┘
       │ ARQ enqueue (Redis)  │ asyncpg (PostgreSQL)
┌──────▼─────────────┐  ┌────▼──────────────────────────────┐
│  Background Worker  │  │  Database                          │
│  philosopher-worker │  │  Supabase PostgreSQL 17            │
│  Render Starter     │  │  project: plecolxlzshkfvybszgs    │
│  Oregon · $7/mo     │  │  eu-west-1 (paid)                  │
│  [srv-XXXX —        │  │  alembic_version:                  │
│   founder to fill]  │  │    012_scheduled_emails            │
│                     │  │                                    │
│  ARQ tasks (4):     │  │  Key tables:                       │
│  · generate_conv_   │  │  users, personas,                  │
│    ersion_title     │  │  conversations, messages,          │
│  · extract_memory_  │  │  saved_lines, scheduled_emails,    │
│    task             │  │  daily_questions, source_chunks,   │
│  · generate_        │  │  memory_entries, daily_usage,      │
│    insight_task     │  │  safety_events, subscriptions      │
│  · send_ritual_     │  └────────────────────────────────────┘
│    reminder_task    │
│                     │  ┌────────────────────────────────────┐
│  APScheduler (4):   │  │  Cache                             │
│  · daily_rituals    │  │  Upstash Redis · eu-west-1 · free  │
│    08:00 UTC        │  │  philosopher-prod                  │
│  · stale_memory     │  │  ARQ job queue + OTP rate limiter  │
│    Sun 03:00 UTC    │  └────────────────────────────────────┘
│  · stripe_reconcile │
│    every 6h         │  ┌────────────────────────────────────┐
│  · future_self_     │  │  LLM / Embeddings                  │
│    emails           │  │  Anthropic API — Haiku (free tier) │
│    every 5 min      │  │  Sonnet (pro tier)                 │
└─────────────────────┘  │  OpenAI text-embedding-3-small     │
                         │  (corpus ingested — one-time done) │
                         └────────────────────────────────────┘
```

### The canonical chat flow (unchanged from v9)

```
Frontend
  ├─ POST /api/v1/conversations             → create conversation (returns conv_id)
  └─ POST /api/v1/conversations/{id}/messages  → SSE stream
       │
       ├─ Ownership check
       ├─ Admin bypass / Ritual exemption
       ├─ rate_limit_service.check_rate_limit()
       ├─ SSE headers (X-RateLimit-*)
       └─ StreamingResponse(conversation_service.stream_response())
             ├─ safety_service.check_input()
             ├─ retrieval_service.retrieve()      → pgvector RAG
             ├─ memory_service.retrieve()         → memory recall
             ├─ phenomenology_bridge_service      → enrichment (if flag=true)
             ├─ prompt_builder.build_system()
             ├─ SELECT messages LIMIT MEMORY_WINDOW
             ├─ _save_message(user)
             ├─ yield "start" SSE
             ├─ llm_client.stream()               → Anthropic SSE
             ├─ safety_service.check_output()
             ├─ _save_message(assistant, model_used=...)
             ├─ UPDATE conversations SET message_count+=2
             ├─ UPDATE daily_usage SET message_count+=1  (free users)
             ├─ arq_queue.enqueue_job("generate_conversation_title", ...)
             └─ arq_queue.enqueue_job("extract_memory_task", ...)
```

---

## 3. Service URLs and IDs

```
Web service:
  Name:    philosopher-api-z9l9
  URL:     https://philosopher-api-z9l9.onrender.com
  ID:      srv-d7ijct6gvqtc739a0pdg
  Region:  Oregon (us-west-2)
  Tier:    Starter ($7/mo)

Background Worker:
  Name:    philosopher-worker
  ID:      [srv-XXXX — founder to fill in]
  Region:  Oregon (us-west-2)
  Tier:    Starter ($7/mo)

Database:
  Project: plecolxlzshkfvybszgs
  URL:     aws-0-eu-west-1.pooler.supabase.com:5432
  Region:  eu-west-1 (paid)
  alembic_version: 012_scheduled_emails

Cache (Redis):
  Provider: Upstash
  Name:     philosopher-prod
  Region:   eu-west-1
  Tier:     Free

Frontend:
  Provider: Netlify
  Project:  thinkalike
  URL:      https://thinkalike.netlify.app
  Domain:   https://thegreatminds.app (DNS: verify status)

Email:
  Provider: Resend
  Sender:   Great Minds <onboarding@resend.dev> (test sender — ⚠️ domain unverified)

Billing:
  Provider: Stripe
  Mode:     TEST — ⚠️ live mode migration required

Total Render cost: $14/mo (web Starter $7 + worker Starter $7)
```

---

## 4. Worker tasks reference

### ARQ tasks (registered in `WorkerSettings.functions`, `apps/api/workers/arq_worker.py`)

| Function | Enqueued by | What it does | Status |
|---|---|---|---|
| `generate_conversation_title` | `stream_response()` when `message_count == 0` (first message in conv) | Fetches first 4 messages; generates 4–7 word title via Haiku `llm_client.complete()`; updates `conversations.title` | ✅ live |
| `extract_memory_task` | `stream_response()` after every assistant response | Calls `memory_service.extract_and_store()` with 7 args: `ctx, user_id, conversation_id, persona_id, user_text, assistant_text, turn` | ✅ live (no organic entries yet) |
| `generate_insight_task` | **Not enqueued anywhere** | Synthesizes insight from ≥4 recent memory entries; writes `Insight` DB row | ⏸ orphan |
| `send_ritual_reminder_task` | APScheduler `dispatch_ritual_reminders` cron | Sends ritual reminder email via Resend to a specific `(user_id, ritual_id)` pair | ✅ live |

**Worker config (`WorkerSettings`):**
```python
max_jobs = 10
job_timeout = 90  # seconds
keep_result = 300  # seconds
redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
```

### APScheduler cron jobs (4 total, wired in `setup_cron()`, `apps/api/workers/cron.py`)

| Job ID | Schedule | Function | What it does |
|---|---|---|---|
| `daily_rituals` | `CronTrigger(hour=8, minute=0)` — 08:00 UTC daily | `dispatch_ritual_reminders` | Queries Pro+ users with ritual completions in last 36h; enqueues `send_ritual_reminder_task` per `(user_id, ritual_id)` |
| `stale_memory` | `CronTrigger(day_of_week="sun", hour=3, minute=0)` — Sunday 03:00 UTC | `deactivate_stale_memories` | Sets `is_active = False` on memory entries older than 90 days with `confidence < 0.6` |
| `stripe_reconcile` | `IntervalTrigger(hours=6)` — every 6 hours | `reconcile_stripe_subscriptions` | Fetches live Stripe status for active/trialing/past_due subscriptions; corrects drift from missed webhooks |
| `future_self_emails` | `IntervalTrigger(minutes=5)` — every 5 minutes | `send_pending_future_self_emails` | Queries `scheduled_emails` WHERE `status = 'pending'` AND `scheduled_for <= NOW()`; sends up to 50 per run via `send_email()` directly (NOT via ARQ) |

**Important:** `send_pending_future_self_emails` calls `send_email()` inline — it does NOT enqueue an ARQ task. This is direct execution inside the APScheduler job.

**Cron hotfix (applied commit `c0b716a`):** The `daily_rituals` job originally called `arq_queue.enqueue()` which does not exist on `ArqRedis`. Fixed to `arq_queue.enqueue_job()`. Applied before worker went live. All other cron jobs already used the correct method.

---

## 5. Critical operating principles

- **Test in incognito.** A fresh authenticated session catches auth/hydration issues invisible to the logged-in developer. Required for all auth and chat smoke tests.
- **Full diff audit before merge.** Never approve a PR from its description alone. Read every changed line.
- **No secrets in chat.** API keys, JWT secrets, Stripe keys, Supabase credentials never appear in Claude conversations.
- **Brand-agnostic work until rebrand decision lands.** UI copy referencing "Great Minds" as product name is provisional. See DEF-01 in backlog.
- **Mobile-first smoke test.** Every frontend PR requires real iOS Safari verification — desktop Chrome is not a substitute (BUG-001–009 were mobile-only findings).
- **One logical fix per PR.** Auth/hydration changes require isolated PR + mobile smoke test on preview URL before merge. (TD-09 lesson from 2h production fire.)
- **CLAUDE.md pre-work protocol.** Enumerate existing code in the domain before writing any new code. Never guess or trust briefs blindly — read source files.
- **Post-migration verification.** After every Render deploy: check `SELECT version FROM alembic_version`, confirm columns, verify indexes via Supabase MCP.
- **ARQ API — `enqueue_job()` not `enqueue()`.** ARQ's `ArqRedis` uses `enqueue_job()`. Verify method name against the `arq` library docs before wiring any new cron or route enqueue call.
- **Reconciliation over deletion.** When parallel implementations are discovered: investigation PR first → founder approves strategy → port → delete last. Never silently delete pre-existing code.

---

## 6. Cold beta launch checklist

All P0 gates. Presented in logical dependency order:

```
[ ] Brand rebrand decision (DEF-01) — resolves Resend domain + DNS + copy choices
[ ] Greek ΚΑΔ addition via TAXISnet form Μ2 (P0-09) — prerequisite for Stripe live mode
[ ] DNS thegreatminds.app verified (P0-07)
[ ] Resend domain verified — OTP delivery working for non-Gmail (P0-01)
[ ] Stripe live mode activated (P0-02): swap keys, re-register webhook, smoke test
[ ] End-to-end Stripe sandbox test (P0-03): test card → checkout → entitlement → portal → cancel
[ ] PHENOMENOLOGY_BRIDGE_ENABLED confirmed true in Render env (P0-11)
[ ] Backfill-titles admin execution: POST /api/v1/admin/backfill-titles (P0-05)
[ ] Lawyer review of ToS / Privacy / Disclaimer (P0-06)
[ ] GDPR / DPA infrastructure: Anthropic DPA, processors doc, data subject workflow (P0-08)
[ ] Founder runbooks: refund, GDPR, cancellation, safety escalation (P0-10)
[ ] Cold smoke test with 5–7 fresh users: signup → OTP → onboarding → conversation (P0-04)
```

---

## 7. Known issues

### [OPEN] Memory extraction JSON parse

`extract_memory_task` → `memory_service.extract_and_store()` parses LLM output as JSON. If the LLM wraps its response in markdown fences (` ```json ... ``` `), `json.loads()` fails. Defensive strip not yet applied. **Verify with fresh worker task logs first. Only implement if confirmed in production.**

### [OPEN] `safety_events.message_id` always NULL

`safety_events` table: `message_id` FK is never set. Safety events are still queryable by `user_id`, `conversation_id`, and timestamp. Minor cleanup; not a launch blocker. (TD-06)

### [OPEN] `generate_insight_task` not enqueued

Task is defined and registered in `WorkerSettings.functions` but never enqueued from any route or cron job. Intentional until organic memory entries accumulate. (TD-05)

### [OPEN] `ANTHROPIC_MODEL` constant orphaned

`config.py` has `ANTHROPIC_MODEL = "claude-sonnet-4-20250514"` (stale Sonnet 4). Not read by `conversation_service.py`, which uses `MODEL_FREE`/`MODEL_PRO` literals. Remove or update before it misleads future work. (TD-03)

### [OPEN] Brand copy provisional

All UI copy referencing "Great Minds" (AppHeader, email templates, share card wordmark, splash) is provisional pending DEF-01 brand rebrand decision.

---

## 8. Test infrastructure

### Current state (2026-05-22)

```
362 backend tests passing (pytest) — up from 292 in v9
 43 frontend tests passing (vitest) — unchanged from v9
  0 failures
```

Test count evolution (backend):
- v9 baseline (2026-05-20): 292
- PR3b (#81): +70 (share router + image service + conversation service additions)
- PR3c (#82): +? (16 new tests: scheduled_emails router + cron pending emails)
- PR4a (#83): +90 (conversations router additions)
- PR4b (#84): +3 (skip_opening cases in test_conversation_service.py)
- PR4c (#85): +1 (test_validator_accepts_4_years)
- **v10 total: 362**

### New test files added in PR3/PR4 wave

```
apps/api/tests/routers/test_share.py              (PR3b — 136 lines)
apps/api/tests/services/test_image_service.py     (PR3b — 110 lines)
apps/api/tests/routers/test_scheduled_emails.py   (PR3c — 281 lines)
apps/api/tests/services/test_cron_pending_emails.py  (PR3c — 294 lines)
```

Extended in PR3b:
```
apps/api/tests/services/test_conversation_service.py  (+77 lines)
```

Extended in PR4a:
```
apps/api/tests/routers/test_conversations.py  (+90 lines)
```

---

## 9. Environmental configuration

### Backend (Render)

```
DATABASE_URL                    ✅ Set (Supabase pooler — aws-0-eu-west-1.pooler.supabase.com:5432)
REDIS_URL                       ✅ Set (Upstash eu-west-1)
RESEND_API_KEY                  ✅ Set
FROM_EMAIL                      "Great Minds <onboarding@resend.dev>" — ⚠️ test sender
JWT_SECRET                      ✅ Set
ANTHROPIC_API_KEY               ✅ Set
ANTHROPIC_MEMORY_MODEL          "claude-haiku-4-5-20251001" (used by memory service)
PHENOMENOLOGY_BRIDGE_ENABLED    ⚠️ State unverified (was true 2026-05-04/05)
PUBLIC_ASSET_BASE_URL           ✅ Set (added PR3c — used by cron email template for portrait URLs)

STRIPE_SECRET_KEY               ✅ Set (test mode — ⚠️ swap to live before launch)
STRIPE_WEBHOOK_SECRET           ✅ Set (test mode — ⚠️ re-register on live mode switch)
STRIPE_PRICE_PRO_MONTHLY        ✅ Set — €14.90/mo price ID
STRIPE_PRICE_PRO_YEARLY         ✅ Set — €149/yr price ID
STRIPE_PRICE_PREMIUM_MONTHLY    ✅ Set — placeholder (Premium pricing deferred)

ANTHROPIC_MODEL (config.py)     ⚠️ ORPHANED constant — "claude-sonnet-4-20250514" (stale)
                                 Not read by conversation_service.py. Update or remove (TD-03).
```

**Pending env var changes (before launch):**
- `FROM_EMAIL` → `noreply@thegreatminds.app` (after Resend domain verifies + brand decision)
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` → live values (P0-02)
- `PHENOMENOLOGY_BRIDGE_ENABLED` → set explicitly to `true` (confirm current state)

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL                (unset; falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL          nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ✅ Set (test mode — ⚠️ swap to live before launch)
```

---

## 10. Key file paths (full production codebase)

### Backend (apps/api/)

**Core application:**
- `main.py` — FastAPI app + all router mounts
- `config.py` — Settings class (note: `ANTHROPIC_MODEL` orphan, `PUBLIC_ASSET_BASE_URL` added PR3c)
- `auth.py` — `get_current_user` + `get_current_user_plan` deps
- `models/__init__.py` — all ORM models (adds `ScheduledEmail` in PR3c)
- `schemas/__init__.py` — all Pydantic schemas (adds `ScheduledEmail*`, `skip_opening` in PR3c/4b)

**Routers:**
- `routers/conversations.py` — all conversation endpoints incl. `GET /conversations/{id}` (PR4a)
- `routers/billing.py` — Stripe checkout + portal + webhook
- `routers/share.py` — `POST /api/v1/share` (NEW — PR3b)
- `routers/scheduled_emails.py` — `POST/GET/DELETE /api/v1/scheduled-emails` (NEW — PR3c)
- `routers/admin.py` — `/backfill-titles`

**Services:**
- `services/conversation_service.py` — `stream_response()` + `create()`; `MODEL_FREE`, `MODEL_PRO`, `MEMORY_WINDOW_FREE`, `MEMORY_WINDOW_PRO` constants
- `services/image_service.py` — share card PNG generation; 1080×1350 canvas (NEW — PR3b, updated PR4d)
- `services/template_service.py` — `render_future_self_email()` Jinja2 renderer (NEW — PR3c)
- `services/rate_limit_service.py` — OTP rate limit (Redis) + message rate limit (DB)
- `services/llm_client.py` — streaming Anthropic client
- `services/retrieval_service.py` — pgvector RAG retrieval
- `services/memory_service.py` — memory extraction + recall
- `services/safety_service.py` — 2-layer safety
- `services/tier_service.py` — `get_user_tier()`
- `services/persona_voice.py` — `get_error_voice(persona_orm, error_code)`
- `services/stripe_service.py` — Stripe integration
- `services/prompt_builder.py` — system prompt assembly

**Workers:**
- `workers/arq_worker.py` — ARQ task definitions + `WorkerSettings`
- `workers/cron.py` — APScheduler `setup_cron()` with 4 scheduled jobs

**Database:**
- `db/migrations/versions/` — 012 migrations, HEAD: `012_scheduled_emails`
- `db/session.py` — `AsyncSessionLocal`

**Static assets:**
- `static/fonts/` — CormorantGaramond-Italic.ttf, CormorantGaramond-Medium.ttf, Lora-Regular.ttf
- `static/personas/` — 9 persona portrait images

**Templates:**
- `templates/future_self_email.html` — Jinja2 future-self email template (NEW — PR3c)

**Scripts:**
- `scripts/chunking.py`, `corpus_sources.py`, `curated_chunks.py`, `ingest_corpus.py` — corpus ingestion (C3a; C3b complete)

### Frontend (apps/web/)

**Pages:**
- `app/page.tsx` — Splash / A0 Landing (full-bleed dark, PR4h; mode-aware CTAs, PR4e)
- `app/auth/page.tsx` — Auth entry (mode-aware copy, PR4e)
- `app/app/(tabs)/today/page.tsx` — D1 Today (TodaysTopicCard, RitualsCard, AppHeader)
- `app/app/(tabs)/reflections/page.tsx` — F1 Reflections (SwipeableRow, AppHeader)
- `app/app/(tabs)/library/page.tsx` — F6 Library (SwipeableRow in PastConversationsView, AppHeader)
- `app/app/(tabs)/account/page.tsx` — Account hub (Scheduled letters card, AppHeader)
- `app/app/scheduled-letters/page.tsx` — Scheduled letters list (NEW — PR3c)
- `app/app/chat/conv/[id]/page.tsx` — Chat (auto-send from localStorage draft, 'Home' routing)
- `app/app/upgrade/page.tsx` — Stripe Checkout

**Components (layout):**
- `components/layout/AppHeader.tsx` — 'Great Minds · Day, Mon DD' header (NEW — PR4c)
- `components/layout/BottomTabBar.tsx`

**Components (today):**
- `components/today/TodaysTopicCard.tsx` — editable topic card (NEW — PR4b)
- `components/today/RitualsCard.tsx` — 3-row rituals card (NEW — PR3c)

**Components (rituals):**
- `components/rituals/RitualScheduleSheet.tsx` — letter scheduling form (NEW — PR3c)
- `components/rituals/SavedLinePicker.tsx` — inline thumbnail picker (NEW — PR4g)

**Components (UI):**
- `components/ui/SwipeableRow.tsx` — framer-motion swipe-to-delete (NEW — PR4f)
- `components/ui/BottomSheet.tsx` — AnimatePresence slide-up sheet (NEW — PR3c)

**Components (chat, reflections, library, personas):**
- Unchanged from v9. See `HANDOFF_BRIEF_v9.md` §8 for full list.

**Lib:**
- `lib/api.ts` — all API types + fetch helpers (updated PR3b/3c/4a/4b)
- `lib/store.ts` — Zustand state
- `lib/useStream.tsx` — SSE parser
- `lib/initials.ts` — `deriveInitials()` helper (NEW — PR4b)

---

## 11. Decision history (v10 additions)

No new locked decisions in PR3/PR4 wave. All 10 locked decisions from v9 §9 remain unchanged.

### Preserved from v9

See `HANDOFF_BRIEF_v9.md` §9 and `PROJECT_STATE_v9.md` §9 for the 10 locked decisions (LLM routing, RAG architecture, streaming protocol, memory window, free tier limits, safety architecture, copyright, pricing, ritual exemption, admin bypass placement).

---

## 12. Section 5.7 framework — status

Unchanged from v9. All infrastructure live. See `HANDOFF_BRIEF_v9.md` §10.

---

## 13. Migration plan — status

- **Phases 1-3:** ✅ COMPLETE
- **Phase 4 — Modern phenomenology bridge:** ✅ COMPLETE (PHENOMENOLOGY_BRIDGE_ENABLED flag to confirm in Render)
- **Block A — Authentication:** ✅ FULLY CLOSED 5/5
- **Block B — Onboarding:** ✅ SPINE + POLISH COMPLETE (PR3a)
- **Block C — Chat backend:** ✅ COMPLETE (PATH A canonical)
- **Block C frontend:** ✅ COMPLETE (C5a/b/c/d, C3a, C3b)
- **Block D — D1 Today:** ✅ COMPLETE (PR #76 + PR4b)
- **Block H — Stripe:** ✅ SANDBOX COMPLETE; live mode migration pending (P0-02 + P0-09)
- **Phase 5 — Register architecture + UI chips:** ⏳ P3 post-feedback
- **Phase 6 — Eval suite + CI:** ⏳ P1 post-revenue

---

## 14. Session lessons (v10 additions)

### 14.1 — Preserved from v9 (§13.1–13.4)

All prior lessons retained. Full text in `HANDOFF_BRIEF_v9.md` §13.

### 14.2 — ARQ `enqueue_job()` vs `enqueue()` (NEW v10 — 2026-05-21)

ARQ's `ArqRedis` class uses `enqueue_job()` to add jobs to the queue. There is no `enqueue()` method. The `daily_rituals` cron job was written with `enqueue()` (cron hotfix commit `c0b716a`), which would have caused `AttributeError` on every execution. This was a 1-line fix but would have silently broken all ritual reminder delivery.

**Rule:** Before wiring any new cron job or route that enqueues ARQ work, verify the exact method name against the `arq` library docs or an existing confirmed-working call site (e.g. `stream_response()` uses `arq_queue.enqueue_job("generate_conversation_title", ...)`).

### 14.3 — APScheduler cron jobs run inline in the worker process (NEW v10 — 2026-05-21)

`send_pending_future_self_emails` is an APScheduler job that calls `send_email()` directly — it does NOT dispatch to an ARQ queue. This is intentional: future-self emails require DB reads, Jinja2 rendering, and Resend API calls in a single transactional sweep. The per-row `try/except` ensures one failure does not block the rest of the batch.

When writing new cron jobs: decide upfront whether the work should be (a) done inline in the scheduler job, or (b) delegated to ARQ for concurrency/retry. Inline is simpler for small batches with per-row error isolation; ARQ is better for large fan-out (e.g. `dispatch_ritual_reminders` fans out to N `send_ritual_reminder_task` jobs).

---

## 15. Next session entry point

Priority order as of 2026-05-22:

1. **Brand rebrand decision** (DEF-01) — resolve before Resend domain + DNS choices
2. **Greek ΚΑΔ addition** (P0-09) — TAXISnet form Μ2; unblocks Stripe live mode
3. **Resend domain verification** (P0-01) — unblocks cold beta OTP delivery
4. **Stripe live mode activation** (P0-02) — after ΚΑΔ + Resend verified
5. **End-to-end Stripe sandbox test** (P0-03) — confidence gate before live mode
6. **Backfill-titles admin execution** (P0-05) — one-time founder action
7. **Cold smoke test with 5–7 fresh users** (P0-04) — requires Resend domain live
8. **Lawyer review + GDPR + runbooks** (P0-06/08/10) — parallel to above

---

**End of HANDOFF_BRIEF v10.** Authoritative as of 2026-05-22. Supersedes `HANDOFF_BRIEF_v9.md` (preserved as historical reference). Where v10 conflicts with v9, v10 wins.
