# HANDOFF BRIEF v11 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-05-24
**Prior version:** `docs/HANDOFF_BRIEF_v9.md` (2026-05-20) *(v10 skipped — two sessions absorbed into one rotation)*
**Generated:** 2026-05-24 (v11 rotation)

**Block trigger for v11 baseline regen:** May 21-24 session shipped 8 PRs, 3 migrations, 5 new env vars, 2 new backend endpoints, 3 new frontend components, 1 production regression (PR4p), and 5 new process rules. Volume exceeds addendum threshold; full regen warranted.

**Status:**
- Block A ✅ FULLY CLOSED (5/5)
- Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending)
- Block C ✅ FULLY COMPLETE (backend + frontend + RAG)
- Stripe sandbox ✅ COMPLETE (PR1 #77, 2026-05-19)
- Paywall + BETA bypass ✅ COMPLETE (PR4j #100, 2026-05-22)
- Share v2 ✅ COMPLETE (PR4n #102, 2026-05-23)
- Rituals tab + page ✅ COMPLETE (PR4o #103, 2026-05-23)
- Google OAuth ✅ DORMANT (PR4k #101, 2026-05-23 — GOOGLE_OAUTH_ENABLED=false)
- Migrations: 001–014 all applied; head = `014_user_oauth_columns`
- PR4r rollback 🟡 IN FLIGHT (reverts hydration guard, keeps api import fix; branch: feat/pr4r-actual-rollback-hydration)

> **v11 conflict resolution rule:** Where v11 conflicts with v9 or earlier, v11 wins. Production reality always wins over docs.

---

## Changelog v9 → v11

*(No v10 was produced. Two sessions absorbed into one rotation.)*

### PR4j — Paywall audit + BETA bypass system (PR #100, 2026-05-22)

**Problem:** Paywall enforcement was checking the Stripe subscriptions table, which showed "free" for all users (no one has paid during cold beta). Result: all Pro features were blocked.

**Solution:** `BETA_GRANT_PRO_TO_ALL=true` env var. When set:
- `auth.get_current_user_plan` returns `"pro"` for all users
- `tier_service.get_user_tier` returns `"pro"` for all users
- `GET /api/v1/subscription` synthetic endpoint returns `{isPro: true, plan: "pro"}` for all users

**Frontend:** `SubscriptionBootstrap` layout-level component calls `/api/v1/subscription` on app mount and hydrates Zustand store with `isPro` flag. Prevents per-page re-fetching.

**Tech debt created:** TD-11 — two parallel tier-resolution functions both patched; must consolidate before disabling bypass for paid launch.

### PR4l — Alembic revision_id length hotfix (2026-05-22)

Hotfix to alembic migration infrastructure: `revision_id` column had insufficient VARCHAR length for longer revision strings. Fixed to VARCHAR(32) minimum. No schema data change; affects only alembic_version tracking.

### PR4m — FK ondelete hotfix (PR #99, 2026-05-22)

Migration 013 (`013_add_ondelete_conversation_fks`): adds proper `ON DELETE` semantics to existing FK constraints that previously had no action (silent orphan risk on hard deletes):
- `memory_entries.*` → CASCADE
- `insights.*` → CASCADE
- `safety_events.*` → SET NULL (preserve audit trail)
- `user_ritual_completions.*` → SET NULL (preserve completion history)

### PR4k — Google OAuth dormant implementation (PR #101, 2026-05-23)

**What shipped:**
- `apps/api/routers/auth_oauth.py` — two routes: `GET /api/v1/auth/methods` + `POST /api/v1/auth/google/login`
- Migration 014 (`014_user_oauth_columns`) — `users.auth_provider VARCHAR(20)` (default 'otp') + `users.oauth_provider_id TEXT NULL` + index
- `FRONTEND_URL` env var replaces `BASE_URL` for Stripe success/cancel URLs and ritual reminder email links (6 call sites migrated)
- `GOOGLE_OAUTH_ENABLED` env var (default `false`) gates all OAuth routes
- `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` placeholders in Render

**Critical bug found and fixed:** `BASE_URL` in Render was set to `https://philosopher-api.onrender.com` — a 404 URL. Canonical backend URL is `https://philosopher-api-z9l9.onrender.com`. Stripe success/cancel URLs and ritual reminder email links were silently broken for weeks. PR4k migrated all 6 call sites to `FRONTEND_URL = https://thinkalike.netlify.app`.

**What's NOT active:** Google OAuth user flow. `GOOGLE_OAUTH_ENABLED=false`. Requires brand/domain decision before enabling.

### PR4n — Share v2 (PR #102, 2026-05-23)

- `components/share/SharePreviewModal.tsx` — modal replaces the old inline share UI
- Annotation overlay on share preview image
- Dynamic font sizing: 15–350 chars maps to 64–28px
- Emoji strip: backend (`emoji==2.12.1` in requirements.txt) + frontend both strip emoji before rendering share preview
- Inadvertent regression: `import { api }` removed from `apps/web/app/app/(tabs)/today/page.tsx` while extracting `SharePreviewModal` (the `ShareLimitError` import was correctly moved, but `api` was taken with it). This broke ALL Today data fetching — all users saw first-day Welcome state regardless of conversation history. Fixed in PR4p (api import restored).

### PR4o — Rituals tab + page (PR #103, 2026-05-23)

- Tab bar: "Reflections" tab swapped to "Rituals" (Compass icon)
- `/app/rituals` page with 4 ritual cards:
  - **Letter to my Future Self** — functional: form, persona selector, scheduled date picker, `POST /api/v1/rituals/schedule-letter` (or equivalent), scheduled_emails DB record created
  - **The Mirror** — LOCKED (placeholder)
  - **The Counterview** — LOCKED (placeholder)
  - **The Weekly Reading** — LOCKED (placeholder; full implementation = TD-17)
- Today page `RitualsCard` simplified: shows Letter-only + "See all rituals →" link
- "See all reflections →" affordance added to Today page
- Migration 012 (`012_scheduled_emails`): `scheduled_emails` table for Letter feature

⚠️ **Incomplete:** The `scheduled_emails` ARQ delivery task is NOT yet wired. DB schema exists; UI captures the form data; actual email delivery at the scheduled time is not implemented (BUG-014).

### PR4p — api import hotfix + hydration guard (PR #104, 2026-05-23)

**What was intended:** Two changes bundled in one PR.
1. **P0 fix (correct):** Restored `import { api, ShareLimitError } from '@/lib/api'` in `today/page.tsx`. Fixed the regression introduced by PR4n.
2. **P1 experiment (broke production):** Added `_hasHydrated` Zustand state slice + `onRehydrateStorage` callback + hydration guard in create-conversation effect.

**What happened:** The hydration guard never lifted in the production Next.js build. `onRehydrateStorage` callback timing in production differs from local dev. Result: `_hasHydrated` was always `false`; chat screens showed "Summoning..." stall for all users; all protected pages redirected to `/auth` on hard refresh.

**Process failure:** P0 fix and P1 experiment bundled in one PR (violates P-02). No Netlify preview smoke test before merging (violates P-04). Unit tests passed; production build failed.

### PR4q — Empty commit (PR #105, 2026-05-23)

Supposed to revert the PR4p hydration guard. Became an empty commit because Claude Code branched off stale local `main` without running `git fetch origin` first. The stale local `main` predated PR4p, so the "revert" had nothing to revert.

**Process failure:** Branching from stale local main (violates P-01). Rule codified in CLAUDE.md.

### PR4r — Actual rollback (branch: feat/pr4r-actual-rollback-hydration, in flight 2026-05-24)

Properly reverts the `_hasHydrated` hydration guard (the three HYDRATION hunks from PR4p) while keeping the api import fix from PR4p. Also removes hydration guard from all other page-level `useEffect`s where it was added in PR4p.

Changes on main after PR4r merges:
- `lib/store.ts` — `_hasHydrated` state slice REMOVED
- All page-level auth `useEffect`s — hydration guard condition REMOVED
- `import { api }` in `today/page.tsx` — KEPT (the fix that matters)

### 2026-05-24 evening session — PR4s through PR4u

Session shipped 4 PRs in sequence with strict gated methodology:

- **PR4s (#108)** — Conversation delete P0 fix. Diagnosed via Supabase FK inspection + Render log traceback. Root cause: SQLAlchemy ORM ↔ DB CASCADE mismatch. 1-file, 6-line fix.
- **PR4t (#109)** — RitualsCard removed from Today (PR4o follow-up).
- **PR4v (#110)** — Cleanup bundle: TD-14 + TD-15 + TD-16.
- **PR4u (#111)** — Edge state pages: 404, in-app error boundary, global error. 3 new files, 178 lines.

**Process notes:**
- PR4s smoke test was skipped on preview (only verified on production). Low-risk backend change, no harm done, but P-03 violation logged.
- PR4u correctly went through Netlify preview before merge (P-04 honored).
- One diagnostic detour: founder reported "Reflections deleted" mid-PR4t; investigation revealed Reflections card was hidden because all user's saved_lines had been soft-deleted weeks earlier. Not a bug. Lesson logged.

**Lessons codified in CLAUDE.md:**
- P-06 added (diagnosis-before-action principle).

---

## 1. Pre-Work Investigation Protocol

Unchanged from v9. Defined in `CLAUDE.md` at repo root (PR #54, 2026-05-16). Mandatory for all multi-PR work.

**Extension (2026-05-24):** CLAUDE.md now also contains "Production safety principles" P-01 through P-05. See §13.5 below.

---

## 2. Current architecture

### Chat flow

Unchanged from v9. See v9 §2 for full diagram.

### Subscription / tier resolution (NEW v11)

```
GET /api/v1/subscription (auth)
  └─ auth.get_current_user_plan(user)
       ├─ if BETA_GRANT_PRO_TO_ALL: return "pro"
       └─ else: return Subscription.plan ("free" | "pro" | "premium")
       
  → returns { isPro: bool, plan: str, status: str | null, interval: str | null }

SubscriptionBootstrap (layout-level, apps/web/components/layout/)
  └─ useEffect([], []) → GET /api/v1/subscription
       └─ useAuthStore.setState({ isPro })
            → all components read isPro from Zustand store
```

**Known tech debt:** `tier_service.get_user_tier` is a parallel path used by 5 different endpoints. Must be consolidated with `get_current_user_plan` before paid launch (TD-11).

### Google OAuth routes (dormant)

```
GET /api/v1/auth/methods
  → returns { methods: ["otp"] }  (when GOOGLE_OAUTH_ENABLED=false)
  → returns { methods: ["otp", "google"] }  (when GOOGLE_OAUTH_ENABLED=true)

POST /api/v1/auth/google/login
  → DORMANT when GOOGLE_OAUTH_ENABLED=false
  → When enabled: initiates Google OAuth flow, returns redirect URL
```

---

## 3. Test infrastructure

### Current state (as of v11)

```
~292 backend tests passing (C3a baseline; may have grown with PR4j/PR4k additions)
~43 frontend tests passing (C5d baseline; PR4p/PR4r touched store.ts — tests updated)
```

BottomTabBar tests updated in PR4o to reflect Rituals tab (Reflections → Rituals swap). Tests for `_hasHydrated` guard added in PR4p, removed in PR4r.

---

## 4. Known limitations and not-yet-wired features

All v9 limitations apply. Additions since v9:

### 4.8 Letter to my Future Self — email delivery not wired (BUG-014)

The Rituals UI allows users to compose a letter and schedule delivery. The `scheduled_emails` table (migration 012) records the intent. However, the ARQ task that reads `pending` rows and dispatches emails via Resend is NOT yet implemented. Users who schedule a letter will not receive it until this is wired.

### 4.9 Zustand hydration race (TD-10)

Hard refresh or direct URL navigation to protected routes still flashes to `/auth`. Pre-existing bug. PR4p attempted fix broke production. Safe approach requires Netlify preview smoke test before any new attempt. See TD-10.

### 4.10 Google OAuth dormant

`POST /api/v1/auth/google/login` is live in code but returns 404/disabled when `GOOGLE_OAUTH_ENABLED=false`. DB schema (migration 014) is deployed. Flip the env var to activate — but brand/domain decision needed first (app is currently "Philosopher" codebase; display name in Google OAuth screen matters for user trust).

### 4.11 BASE_URL was broken for weeks (fixed in PR4k)

Historical note for context: `BASE_URL` in Render was `https://philosopher-api.onrender.com` (no `-z9l9` suffix → 404). Stripe success/cancel redirect URLs and ritual reminder email links were using this broken URL. Fixed in PR4k by migrating all 6 call sites to `FRONTEND_URL = https://thinkalike.netlify.app`. Users attempting Stripe checkout during that period would have seen a 404 on redirect back. No confirmed Stripe transactions occurred during this period (no paying users).

---

## Process notes (2026-05-24)

### OTP rate limit observation

During PR4p → PR4q → PR4r debugging cycle, founder hit Upstash Redis
OTP rate limit on nckoutras@gmail.com after 10 OTP requests within
~3.5 hours. Workaround used: verification via existing valid JWT in
normal browser session (no OTP needed), instead of incognito +
re-login.

For future debugging sessions involving auth:
- Use existing logged-in browser when possible (JWT is valid for 7 days)
- Alternative: freetester@gmail.com or other test accounts have
  separate rate limit pools
- Avoid testing the OTP flow itself >5 times per hour from one email

### Ritual icon prompt template (DALL-E 3)

Per TD-19, editorial minimal direction locked. Below is the prompt
template used during May 24 design exploration session, preserved for
when icon generation phase begins:

Style requirements (strict):
- Editorial illustration aesthetic, modernist sensibility
- Single uniform stroke weight throughout (clean monoline)
- Geometric abstraction, not literal depiction
- Generous negative space, breathing composition
- Bronze color (hex #B89968) line work only
- Pure white background, no shading, no gradients
- Maximum 2-3 visual elements per icon
- Inspired by: Aesop packaging, Pentagram design, A24 branding,
  NYT Op-Ed illustration

Absolutely avoid:
- Engraving textures, antique feel, ornamental details
- Wax seals, ribbons, constellations, candles, moons, stars
- Tarot or occult symbolism
- Decorative borders or flourishes
- Photographic realism or shading
- Religious or mystical iconography
- Multiple stroke weights or hand-drawn imperfection
- Background patterns or textures

Subject placeholder: [SUBJECT-PER-ICON]
Output: 1024x1024 PNG, centered composition, suitable for app
thumbnail at 64x64px display size.

Per-icon subjects:
- Mirror (primary): "A simple oval shape, vertically oriented,
  bisected by a single diagonal line from top-right to bottom-left.
  No handle. No frame ornament."
- Mirror (alternative): "Two identical perfect circles, one positioned
  directly above the other, mirrored vertically."
- Counterview (primary): "Two thin lines forming opposing arrows,
  meeting at center. Left arrow points right, right arrow points left.
  Equal length, mirrored composition."
- Counterview (alternative): "A single perfect triangle pointing up,
  with a second identical triangle pointing down directly below it,
  sharing only their tips at the center."
- Letter to Future Self (primary): "A simple rectangle with a
  triangular flap on top (basic envelope outline). No wax seal. No
  decoration."
- Weekly Reading (primary): "Three horizontal parallel lines stacked
  vertically, each of slightly different length. The shortest line
  at the bottom."
- Weekly Reading (alternative): "A simple book outline viewed from
  the side, slightly open at center, showing two angled rectangular
  pages meeting at a vertical spine."

Asset processing pipeline:
1. Generate PNG 1024x1024 via DALL-E 3 (one icon at a time, 2-3
   variants per icon for selection)
2. Background removal: remove.bg (drag-drop, transparent PNG output)
3. Optional vectorization: Vectorizer.AI ($9.95/month or free trial)
4. Output: mirror.png, counterview.png, letter.png, weekly-reading.png
5. Destination: apps/web/public/icons/rituals/

---

## 5. Next session entry point (2026-06-13 onward)

PRIORITY ORDER (monetization-first). Updated 2026-06-13 after PR #282
(UI polish batch) and PR #283 (chat freeze §5 fix) both merged to main.

1. **P0-FREEZE follow-up** — the send_message §5 DB-session fix shipped in
   PR #283 (A1 no-pin auth dep / A2 route drops Depends(get_db) + session
   factory / A3 three-phase generator + frontend AbortController). Apply the
   SAME A1/A2/A3 + abort pattern to `stream_another_mind` and
   `stream_go_deeper`, which still hold `Depends(get_db)` for the full
   stream and can still exhaust the pool. (Frontend abort signal already
   wired for both — backend only.)
2. **Disambiguate the no-chat slowness** (Scenario A vs B): fresh app open,
   navigate tabs WITHOUT chatting — slow or not? Scenario A (post-chat
   pinned sessions) is covered by #283 for send_message; Scenario B (cold
   fresh open, no chat) is a separate cause (likely Render cold start /
   heavy per-tab fetch), NOT covered by the §5 fix. See P0-FREEZE open
   question.
3. **P0-SMOKE-03a Letter submit** — REOPENED. min-h-0 (merged in #282) was
   correct but incomplete; submit still not visible on preview. Fresh
   reproduction-first investigation (P-06), evidence before fix.
4. **P0-SMOKE-01 / 03b — Bottom tab bar position + Letter-screen drag** —
   likely shared root cause (floating-pill tab bar). Still untouched.
5. **Cosmetic batch (P2):** revert the rejected Sunday card X (#282 commit
   85100371; P2-NEW), enlarge all OTHER close-X buttons (16→20-24px),
   re-fix Sunday explainer clipping (localized padding from #282 didn't
   hold — P2-REOPEN), audit ALL list-title font surfaces incl. the 3rd
   "past conversations" surface (#282 covered only Browse + Library —
   P2-REOPEN).

Note (conversation delete): CLOSED earlier via PR4s (#108); re-verify only
if it resurfaces. Note (branch merges): #282 + #283 already merged — no
merge step pending.

Also codified P-06 in CLAUDE.md (reproduce/prove root cause with evidence
before proposing a fix); keep applying it.

---

## 6. PR history (v9 → v11)

| PR | Description | Date | Status |
|---|---|---|---|
| docs/v11-thread-end-updates | 2026-05-24 night | P0 conv delete + TD-19 ritual icons + UI/UX focus | ✅ Merged |
| docs/v11-rotation | 2026-05-24 evening | Docs v9→v11 rotation, CLAUDE.md P-01 through P-05 codified | ✅ Merged |
| PR1 #77 | Stripe checkout/portal + A0/Today/F1 polish + ToS/Privacy v1.1 | 2026-05-19 | ✅ merged |
| PR2 #78 | Auto-titles fix + cross-persona + library dual-mode + 5 nav routes | 2026-05-20 | ✅ merged |
| PR4j #100 | Paywall audit: BETA bypass + synthetic /subscription + SubscriptionBootstrap | 2026-05-22 | ✅ merged |
| PR4l | Alembic revision_id VARCHAR(32) length fix | 2026-05-22 | ✅ merged |
| PR4m #99 | Migration 013 FK ondelete clauses | 2026-05-22 | ✅ merged |
| PR4k #101 | Google OAuth dormant + migration 014 + FRONTEND_URL + BASE_URL deprecation | 2026-05-23 | ✅ merged |
| PR4n #102 | SharePreviewModal + dynamic font + emoji strip | 2026-05-23 | ✅ merged |
| PR4o #103 | Rituals tab swap + /app/rituals page + Today RitualsCard simplified | 2026-05-23 | ✅ merged |
| PR4p #104 | api import fix (TODAY P0 ✅) + hydration guard (P1 ❌ broke prod) | 2026-05-23 | ✅ merged (P1 reverted by PR4r) |
| PR4q #105 | Empty commit (stale local main branching error — lesson only) | 2026-05-23 | ✅ merged (no-op) |
| PR4r | Actual rollback: revert hydration guard, keep api import fix | 2026-05-24 | ✅ Merged 2026-05-24 |

---

## 7. Environmental configuration

### Backend (Render)

```
DATABASE_URL                    ✅ Set (Supabase pooler)
REDIS_URL                       ✅ Set (Upstash)
RESEND_API_KEY                  ✅ Set
FROM_EMAIL                      "Great Minds <onboarding@resend.dev>" — test sender
JWT_SECRET                      ✅ Set
ANTHROPIC_API_KEY               ✅ Set — actively used for chat
PHENOMENOLOGY_BRIDGE_ENABLED    ⚠️ State unverified (was true 2026-05-04/05)

FRONTEND_URL                    "https://thinkalike.netlify.app"  ← NEW PR4k
                                 Replaces BASE_URL for Stripe redirects + email links
                                 6 call sites migrated in PR4k

BETA_GRANT_PRO_TO_ALL           "true"  ← NEW PR4j
                                 All users treated as Pro during cold beta.
                                 Toggle to "false" before disabling for paid launch.
                                 Requires TD-11 refactor before toggling.

GOOGLE_OAUTH_ENABLED            "false"  ← NEW PR4k
GOOGLE_CLIENT_ID                (placeholder — set when brand decision made)
GOOGLE_CLIENT_SECRET            (placeholder — set when brand decision made)

STRIPE_SECRET_KEY               ✅ Set (PR1 #77, 2026-05-19)
STRIPE_WEBHOOK_SECRET           ✅ Set (PR1 #77, 2026-05-19)
STRIPE_PRICE_PRO_MONTHLY        ✅ Set — €14.90/mo price ID
STRIPE_PRICE_PRO_YEARLY         ✅ Set — €149/yr price ID
STRIPE_PRICE_PREMIUM_MONTHLY    ✅ Set — placeholder; Premium deferred

BASE_URL                        ⚠️ DEPRECATED (PR4k)
                                 config.py still has setting but no app code reads it.
                                 Remove in cleanup PR (TD-14). Previous value was WRONG
                                 (https://philosopher-api.onrender.com = 404).

ANTHROPIC_MODEL (config.py)     ⚠️ ORPHANED constant. Not read by conversation_service.py.
ANTHROPIC_MEMORY_MODEL          "claude-haiku-4-5-20251001" — verify which service reads this
```

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set (PR1 #77, 2026-05-19)
```

---

## 8. Key file paths (production codebase)

### Backend (apps/api/)

All v9 paths apply. **Additions since v9:**

- `routers/auth_oauth.py` — Google OAuth routes (PR4k): `GET /auth/methods` + `POST /auth/google/login`. Gated by `GOOGLE_OAUTH_ENABLED`.
- `routers/auth.py` — `get_current_user_plan` dependency (PR4j): checks `BETA_GRANT_PRO_TO_ALL` before DB lookup.
- `services/tier_service.py` — `get_user_tier` (PR4j): checks `BETA_GRANT_PRO_TO_ALL` before Subscription table lookup.
- `db/migrations/versions/012_scheduled_emails.py` — `scheduled_emails` table (PR4o)
- `db/migrations/versions/013_add_ondelete_conversation_fks.py` — FK ondelete clauses (PR4m)
- `db/migrations/versions/014_user_oauth_columns.py` — `auth_provider` + `oauth_provider_id` on `users` (PR4k)
- `requirements.txt` — `emoji==2.12.1` added (PR4n)

### Frontend (apps/web/)

All v9 paths apply. **Additions since v9:**

- `app/app/(tabs)/rituals/page.tsx` — Rituals page (PR4o): 4 cards (Letter functional, 3 locked)
- `app/app/(tabs)/today/page.tsx` — MODIFIED (PR4n regression → PR4p fix → PR4r stable): api import confirmed present; RitualsCard simplified (PR4o)
- `app/app/(tabs)/layout.tsx` — MODIFIED: Reflections → Rituals tab (PR4o)
- `components/share/SharePreviewModal.tsx` — Share v2 modal (PR4n)
- `components/layout/SubscriptionBootstrap.tsx` — layout-level subscription hydration (PR4j)
- `lib/store.ts` — MODIFIED: `_hasHydrated` guard added (PR4p) then REMOVED (PR4r); isPro field added (PR4j)
- `app/app/chat/conv/[id]/__tests__/page.test.tsx` — conv page tests (modified in PR4r)

---

## 9. Decision history (v11 additions)

### 2026-05-22 — BETA bypass system (PR4j)

- BETA_GRANT_PRO_TO_ALL bypass approved as cold-beta shortcut. Named as tech debt (TD-11). Must disable before paid launch.
- Synthetic `/api/v1/subscription` endpoint approved to decouple frontend from Stripe subscription table.
- SubscriptionBootstrap layout pattern approved (not per-page re-fetching).

### 2026-05-23 — Google OAuth brand decision deferred (PR4k)

- Implementation is dormant (`GOOGLE_OAUTH_ENABLED=false`). DB schema deployed (migration 014). Activation requires brand/domain decision (what name appears in Google OAuth consent screen).

### 2026-05-24 — Hydration approach decision deferred (PR4r post-mortem)

- PR4p `_hasHydrated` approach is rejected. Three alternative approaches in TD-10. No approach approved yet; next attempt requires preview smoke test.

### All prior decisions from v9 §9

Unchanged. See v9/v8 for full history.

---

## 10. Section 5.7 framework — status

Unchanged from v9. All 9 personas have full character config. All elements live.

---

## 11. Migration plan — status

All phases through Block C complete. Unchanged from v9.

---

## 12. Deployment readiness

```
✅ Backend                Render web service philosopher-api
                          philosopher-api-z9l9.onrender.com
                          ⚠️ Free tier; cold-start 30-60s after idle
                          Last deploy: PR4p + PR4q (PR4r pending)

✅ Database               Supabase project plecolxlzshkfvybszgs (eu-west-1, paid)
                          alembic_version = '014_user_oauth_columns'
                          23+ public tables
                          RLS DISABLED on all

✅ Cache (Redis)          Upstash philosopher-prod (eu-west-1) free tier

🟡 Email                  Resend free tier (test sender only)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS

✅ Frontend (canonical)   Netlify thinkalike.netlify.app

✅ LLM                    Anthropic API wired (Haiku 4.5 free / Sonnet 4.6 pro)

✅ Stripe                 Sandbox wired. End-to-end test pending.

🟡 Google OAuth           Dormant (GOOGLE_OAUTH_ENABLED=false). Code + DB ready.

🟡 Rituals email delivery Letter scheduled_emails table live; ARQ delivery not wired (BUG-014).
```

---

## 13. Session lessons (v11 additions)

### 13.1–13.4 Preserved from v9

Full text in prior handoff briefs. Key rules: openapi.json is a verification artifact; reconciliation over deletion; test scaffolding for ARQ tasks.

### 13.5 Production safety principles (NEW v11 — 2026-05-24)

Five mandatory rules codified in CLAUDE.md after the PR4n/PR4p/PR4q regression chain. These apply to ALL future sessions:

**P-01 — Hotfix branch protocol**

Before creating any hotfix branch:
```bash
git fetch origin
git checkout main
git reset --hard origin/main
git log -3 --oneline  # verify expected HEAD commit
git checkout -b feat/...
```
Branching from stale local main = empty no-op merge (PR4q lesson). Never skip.

**P-02 — One logical change per PR**

P0 fix + P1 experiment in same PR = anti-pattern. PR4p bundled api import fix (correct) + hydration guard (broke production). Rollback was complicated by their entanglement. Rule: if a fix is found alongside an unrelated improvement, ship the fix alone first.

**P-03 — Mandatory smoke test cadence**

After ANY merge touching user-facing UI or state-management code: 2-minute manual smoke test before the next PR brief is issued. Symptoms requiring stop: empty page, blank tabs, redirect loops, no API calls in Network tab, paywall-when-Pro. ANY of these = stop, debug.

PR4n broke Today on 2026-05-23 evening. Discovered 18 hours later during PR4o smoke test. A single smoke test at PR4n merge would have caught it immediately.

**P-04 — Preview deploy validation for state/auth changes**

Changes touching: Zustand store shape, middleware, or hydration / auth flow / layout-level wrappers or providers / api client (`lib/api.ts`) / per-page auth useEffects — MUST be smoke tested on Netlify preview deploy BEFORE merging to main. Unit tests are necessary but not sufficient.

PR4p had passing unit tests + clean code review. Failed in production Next.js build because onRehydrateStorage callback timing differs from local dev. Preview deploy would have caught this in 5 minutes.

**P-05 — Verify import dependencies when extracting components**

When extracting a component (creating a new file from inline code), grep the original file for ALL usages of removed imports BEFORE deleting the import line. Each usage must be either re-added to the original file or confirmed genuinely no longer needed there.

PR4n moved `ShareLimitError` correctly to `SharePreviewModal.tsx`, but `api` was taken with it accidentally. All Today data fetching silently broke.

### 13.6 BASE_URL was a silent 404 for weeks (NEW v11 — 2026-05-23)

`BASE_URL` in Render was `https://philosopher-api.onrender.com` — missing the `-z9l9` suffix. This URL returns 404. The correct backend URL is `https://philosopher-api-z9l9.onrender.com`. Stripe redirect URLs and ritual reminder email links pointed to this broken URL for the entire period since PR #77.

Lesson: always verify that env vars point to functioning URLs before shipping features that depend on them. A quick `curl -I $BASE_URL` in the Render shell would have caught this immediately.

### 13.7 Regression chain anatomy (NEW v11 — 2026-05-24)

The May 23 regression chain illustrates how compounding failures work:

1. **PR4n** (Share v2, 2026-05-23 evening): Extracts `SharePreviewModal`, accidentally removes `api` import from today/page.tsx. No smoke test after merge.
2. **~18 hours pass** — regression undetected.
3. **PR4o smoke test** (2026-05-23 next day): Founder discovers Today shows first-day state for returning users. Root cause traced to PR4n.
4. **PR4p** (emergency fix): Bundles api import fix + `_hasHydrated` hydration guard in one PR. Hydration guard fails in production build. No Netlify preview deploy.
5. **PR4p breaks production** — all protected pages redirect to /auth on hard refresh for ALL users.
6. **PR4q** (attempted revert): Empty commit due to stale local main. No-op merge.
7. **PR4r** (actual fix): Proper revert of hydration guard, keeping api import fix. Three PRs and ~18 hours to undo one bad import removal.

**Cost:** ~18 hours of degraded UX (first-day state) + production-wide regression for unknown duration. **Prevention:** single smoke test after PR4n merge.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v8/v9. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. Now extended with Production Safety Principles P-01 through P-05.

### The most important lesson from this rotation

**Smoke test on merge. Every merge. No exceptions.**

The entire May 23 regression chain (3 PRs, ~18 hours) was caused by skipping a 2-minute smoke test after PR4n merged. Had the founder opened the Today page on Netlify immediately after PR4n merged, the missing api import would have been obvious (first-day state for a returning user is immediately wrong). Instead, the bug propagated, triggering a worse fix, which triggered an even worse production regression.

P-03 is now a hard rule. It is the cheapest insurance in this codebase.

### Documentation hygiene

v11 baseline regen triggered by volume of changes in May 21-24 sessions. Next baseline regen threshold: Block B consolidated polish PR + cold beta start, OR major architecture change. Until then, append `*_v11_ADDENDUM_<date>.md` instead of rewriting v11.

### Next session entry point

**See §5 "Next session entry point (2026-06-13 onward)" above — it is
authoritative.** The sequence below predates the 2026-06-13 merges
(PR #282, PR #283) and PR4r (long since merged); kept only for the
launch-readiness tail items.

Launch-readiness tail (after the §5 P0 work):
1. End-to-end Stripe sandbox test (test card → webhook → entitlement →
   portal → cancel)
2. Backfill-titles admin execution
3. Mobile 12-point nav smoke test (real iOS Safari)
4. Cold beta with 3–5 fresh users
5. Block B consolidated polish PR

---

**End of HANDOFF_BRIEF v11.** Authoritative as of 2026-05-24. Supersedes `HANDOFF_BRIEF_v9.md` (preserved as historical reference). Where v11 conflicts with v9, v11 wins. *(v10 was skipped — two sessions absorbed into one rotation.)*
