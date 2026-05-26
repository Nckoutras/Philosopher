# HANDOFF BRIEF v12 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-05-26
**Prior version:** `docs/HANDOFF_BRIEF_v11.md` (2026-05-24)
**Generated:** 2026-05-26 (v12 rotation)

**Block trigger for v12 baseline regen:** 2026-05-25-26 session shipped 11 PRs, 1 migration (015 FK indexes), Render paid plan upgrade (both services), latency root-cause diagnosis, and started the Ireland→Oregon region migration. Region migration is in progress with a partially migrated target project — next session must complete it before any other P0 work.

**Status:**
- Block A ✅ FULLY CLOSED (5/5)
- Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending)
- Block C ✅ FULLY COMPLETE (backend + frontend + RAG)
- Stripe sandbox ✅ COMPLETE (PR1 #77, 2026-05-19)
- Paywall + BETA bypass ✅ COMPLETE (PR4j #100, 2026-05-22)
- Share v3 ✅ COMPLETE (PR4ag1 #122, 2026-05-26)
- Rituals tab + page ✅ COMPLETE (PR4o #103 + PR4ah #123 + PR4ab, 2026-05-26)
- Google OAuth ✅ DORMANT (PR4k #101 — GOOGLE_OAUTH_ENABLED=false)
- Migrations: 001–015 all applied; head = `015_add_fk_indexes`
- PR4r ✅ MERGED (hydration guard reverted; api import fix kept)
- **Oregon region migration 🟡 IN PROGRESS** (schema + ref data + partial user data done; messages/saved_lines/etc. pending)
- Render cold-start ✅ ELIMINATED (both philosopher-api + philosopher-worker on paid Starter tier)

> **v12 conflict resolution rule:** Where v12 conflicts with v11 or earlier, v12 wins. Production reality always wins over docs.

---

## Changelog v11 → v12

### PR4r — Actual rollback of hydration guard (merged early 2026-05-25)

Was in-flight at v11 generation date (2026-05-24). Confirmed merged before Day 1 PR4s sequence. Changes on main:
- `lib/store.ts` — `_hasHydrated` state slice REMOVED
- All page-level auth `useEffect`s — hydration guard condition REMOVED
- `import { api }` in `today/page.tsx` — KEPT (the critical fix from PR4n/PR4p)

Production confirmed stable after merge.

### PR4w — Docs v11 rotation (2026-05-25)

Created `docs/PROJECT_STATE_v11.md`, `docs/HANDOFF_BRIEF_v11.md`, `docs/IMPLEMENTATION_BACKLOG_v11.md`. Prior v9 docs preserved as historical reference.

### Render paid plan upgrade (2026-05-25)

- `philosopher-worker` upgraded to paid Starter tier ($7/mo, srv-d884bomgvqtc73ef2qrg). Was free tier with 15-min idle cold-start.
- `philosopher-api` also on paid plan.
- **Eliminates the 15-min idle cold-start on both services.** C6c cold-start screen is now lower-urgency.

### PR4x (#113) — OTP autofill mobile fix (2026-05-25)

**File:** `apps/web/app/auth/verify/page.tsx`

Mobile browsers (iOS Safari, Android Chrome) were failing to autofill the OTP code from the SMS/email prompt because the input `maxLength` attribute was missing or misconfigured. Fix: correct `maxLength` on each OTP digit input to enable OS-level autofill popover.

### PR4y — Auth redirect destination (2026-05-25)

5 protected pages now redirect to `/auth?mode=signin` instead of bare `/auth`. This ensures that users landing on a protected route while unauthenticated see the sign-in form immediately (not the default state of the auth page, which may show sign-up). Affects: Reflections, Library, Rituals, Account, and one additional protected route.

### PR4z — Pull-to-refresh disabled (2026-05-25)

**File:** `apps/web/app/globals.css`

Added `overscroll-behavior-y: contain` globally. Prevents the browser's native pull-to-refresh gesture from triggering when users scroll to the top of any page on mobile. This was causing accidental full-page reloads during normal scrolling on iOS Safari.

### PR4aa — Conversation titles prompt hardening (2026-05-25)

**File:** `apps/api/workers/arq_worker.py` — `generate_conversation_title` function

Previous title generation prompt was producing generic or meta titles ("Philosophical Conversation", "Discussion with Marcus Aurelius"). Prompt hardened to extract the actual topic/theme from the first exchange rather than describe the conversation format.

**Manual backfill:** After deploying, founder executed the `POST /api/v1/admin/backfill-titles` endpoint via Render shell. **5/5 conversations received clean, topically accurate AI-generated titles.** Backfill-titles P0 item is now closed.

### PR4ab — PersonaPickerSheet fixes (2026-05-25)

**Stuck state fixed:** The PersonaPickerSheet (bottom sheet on Rituals page for selecting which persona to address a letter to) was getting stuck open after certain interactions. Root cause: state not reset on selection confirmation. Fixed.

**Silent errors surfaced:** API errors during ritual submission were being swallowed. Now surfaced to the user via error states.

**Delete feedback toasts:** Ritual deletion (cancel scheduled letter) now shows a dismissal toast confirming the action completed.

### PR4u2 — Library search empty state card (2026-05-25)

**File:** `apps/web/app/app/(tabs)/library/page.tsx`

When a library search query returns no results, an empty state card is now shown ("No conversations found for…") instead of a blank list. Matches the empty state pattern used in other list views.

### PR4ad — Today card thumbnail uniformity (2026-05-25)

**File:** `apps/web/app/app/(tabs)/today/page.tsx`

Two changes:
1. **Flex grammar:** "Your reflections" card now mirrors the "Continuing." card's flex layout grammar (row alignment, icon sizing, spacing). Visual consistency across Today page cards.
2. **`next/image` migration:** Hero/thumbnail images in Today cards migrated from `<img>` to `next/image` for correct lazy loading and LCP optimization.

### PR4ae (#120) — Library readability (2026-05-26)

**File:** `apps/web/app/app/(tabs)/library/page.tsx` (ConversationCard component)

- Persona avatar enlarged from 40px to 56px
- Font sizes scaled up on conversation title and subtitle
- Matches Explore Minds readability standard (which was already using the larger scale)

### PR4af (#121) — Account scheduled letters card removed (2026-05-26)

**File:** `apps/web/app/app/(tabs)/account/page.tsx`

The "Scheduled letters" card in the Account tab was removed (17 lines deleted). This section was premature — the Letter to my Future Self ARQ delivery is not yet wired (BUG-014), making the list always empty. Removed to avoid confusing users with a blank section. Card can be restored once ARQ delivery is wired and letters are actually being sent.

### PR4ag1 (#122) — Share card v3 tweaks + spacebar bug fix (2026-05-26)

**File:** `apps/web/components/share/SharePreviewModal.tsx`

Visual tweaks:
- Portrait card height increased to 260px
- Font sizes increased by 4pt across all breakpoints
- Bronze overlay opacity bumped (more visible branding)

**Bug fix:** The spacebar key was being stripped from the share preview text alongside emoji. Root cause: `stripEmoji(text).trim()` — `.trim()` after emoji stripping was collapsing internal spaces (including intentional spaces around stripped emoji). Fixed by removing the `.trim()` call.

### PR4ah (#123) — Rituals icons (2026-05-26)

**New file:** `components/rituals/RitualIcons.tsx` (or equivalent path within apps/web/)

Contains two custom SVG icon components:
- `ReturningPathIcon` — used for the "Returning" ritual path indicator
- `MirrorIcon` — used for "The Mirror" ritual card

**Nav tab:** The Rituals tab bar icon was swapped from the generic Compass icon (used since PR4o) to the custom `ReturningPathIcon` symbol. Provides distinct visual identity for the Rituals tab.

### L1 (#124) — Migration 015: FK indexes (2026-05-26)

20 btree indexes added on FK columns across 10 tables (subscriptions, conversations, messages, memory_entries, insights, rituals, user_ritual_completions, safety_events, saved_lines, scheduled_emails). See `PROJECT_STATE_v12.md` §4 for full table.

**Latency diagnosis triggered by this migration:** After L1 confirmed <5ms database queries, profiling showed the real bottleneck is the 280ms network RTT between Render Oregon and Supabase Ireland. Total observed latency ~600-700ms per API call. Solution: co-locate in Oregon. Migration started same session.

### Ireland → Oregon region migration (in progress, 2026-05-26)

**Decision:** Move Supabase database from eu-west-1 (Ireland) to us-west-2 (Oregon) to co-locate with Render backend. Expected post-migration improvement: <100ms API latency from Render; ~250-350ms for founder in Greece.

**Two-project topology during migration:**
- Ireland `plecolxlzshkfvybszgs` — production, intact, app running against it
- Oregon `bvzeuwzqgnqcghvqghtb` — migration target, partially populated

**Progress:**
- Schema: ✅ COMPLETE (20 tables, 31 FKs, 66 indexes, pgvector enabled)
- Reference data: ✅ COMPLETE (personas 9, daily_questions 30, disclaimer_versions 1, rituals 4)
- User/app data: 🟡 PARTIAL (users 2, subscriptions 2, user_preferences 1, conversations 87 done)
- Pending: messages 227, saved_lines 13, safety_events 5, user_ritual_completions 4, scheduled_emails 2, memory_entries 8, disclaimer_acceptances 1, alembic_version row, conversations.source_saved_line_id UPDATE
- source_chunks: separate task — re-ingest via existing OpenAI embeddings script (too large for MCP, ~38MB)
- DATABASE_URL switch: founder executes in Render env after migration verifies clean

**Lesson codified:** MCP context window has a hard limit for large vector payloads. 2476 × 1536-dim embeddings ≈ 38MB. Pattern for future migrations: MCP for structured/relational data; re-ingest from source for vector data.

### KIEN project deleted (2026-05-26)

Founder deleted the KIEN sister project on 2026-05-26. Confirmed no precious data; no backup taken. Workspace cleanup complete.

---

## 1. Pre-Work Investigation Protocol

Unchanged from v11. Defined in `CLAUDE.md` at repo root. Mandatory for all multi-PR work. Now includes P-01 through P-06.

---

## 2. Current architecture

### Chat flow

Unchanged from v11. See v11 §2 / v9 §2 for full diagram.

### Subscription / tier resolution

Unchanged from v11 §2. See v11 §2 for flow diagram.

### Latency topology (NEW v12)

```
User (Greece) → Netlify CDN (edge, ~fast) → Render Oregon us-west-2
                                              → Supabase Ireland eu-west-1 (280ms RTT)

Post-migration topology:
User (Greece) → Netlify CDN → Render Oregon → Supabase Oregon (same-region, ~5ms)

Expected latency improvement: ~600-700ms → ~250-350ms per API call
```

### Region migration topology (NEW v12)

Two Supabase projects exist simultaneously during migration:
- Ireland (`plecolxlzshkfvybszgs`) — current production target for DATABASE_URL
- Oregon (`bvzeuwzqgnqcghvqghtb`) — migration target; not yet receiving production traffic

Switch happens atomically when founder changes DATABASE_URL in Render env.

---

## 3. Test infrastructure

### Current state (as of v12)

```
~292+ backend tests (v11 baseline; no new tests added this session)
~43+ frontend tests (v11 baseline; PR4r removed _hasHydrated tests)
```

No test changes in 2026-05-25-26 session beyond what was already captured in v11.

---

## 4. Known limitations and not-yet-wired features

All v11 limitations apply. Additions and updates since v11:

### 4.8 Letter to my Future Self — email delivery not wired (BUG-014)

Unchanged from v11. Account scheduled letters card removed from UI (PR4af) to avoid showing empty list. Underlying BUG-014 remains open.

### 4.9 Zustand hydration race (TD-10)

PR4ai (attempt at TD-10 fix) was explicitly deferred — too risky given PR4p/PR4r history. Any new attempt MUST be smoke tested on Netlify preview deploy. See TD-10 in IMPLEMENTATION_BACKLOG_v12.md.

### 4.10 Google OAuth dormant

Unchanged from v11. GOOGLE_OAUTH_ENABLED=false. DB schema deployed. Activation requires brand/domain decision.

### 4.11 DATABASE_URL latency (NEW v12)

DATABASE_URL currently points to Supabase Ireland. This adds ~280ms RTT to every API call that touches the database. Render and Supabase being in different regions is the identified root cause of ~600-700ms observed API latency. Fix: Oregon migration (§ changelog above). Until DATABASE_URL switch happens, all API calls are slow-by-infrastructure.

### 4.12 source_chunks not yet migrated to Oregon (NEW v12)

The 2476 source_chunks rows (1536-dim vectors, ~38MB) are not migrated. After Oregon switch, RAG retrieval will work on the Ireland project's data until re-ingest is run. Re-ingest via existing OpenAI embeddings script — not a code change, just an operational step.

---

## 5. Next session entry point

**Priority order as of 2026-05-26:**

### Phase 1 — Complete Oregon migration (P0, do first)

1. **Migrate remaining tables to Oregon** (MCP SQL execution):
   - messages (227 rows)
   - saved_lines (13 rows)
   - safety_events (5 rows)
   - user_ritual_completions (4 rows)
   - scheduled_emails (2 rows)
   - memory_entries (8 rows)
   - disclaimer_acceptances (1 row)
   - alembic_version row (head = `015_add_fk_indexes`)
   - UPDATE conversations.source_saved_line_id (FK references to saved_lines)
2. **Verify Oregon data integrity** (row counts match, FK constraints satisfied, alembic_version correct)
3. **Founder: switch DATABASE_URL** in Render env to Oregon pooler
4. **Smoke test post-switch:** login → Today → chat → rituals → library → share
5. **Re-ingest source_chunks** via existing OpenAI embeddings script (against Oregon project)
6. **Verify RAG** (send a message, confirm persona context retrieval working)

### Phase 2 — Post-migration cleanup

7. **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel)
8. **Mobile 12-point nav smoke test** (real iOS Safari)
9. **Cold beta with 3–5 fresh users**

### Phase 3 — Launch track

10. **Block B consolidated polish PR**
11. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)
12. **UAT** (≥2/5 spontaneous "I'd pay")

---

## 6. PR history (v9 → v12)

| PR | Description | Date | Status |
|---|---|---|---|
| PR1 #77 | Stripe checkout/portal + A0/Today/F1 polish + ToS/Privacy v1.1 | 2026-05-19 | ✅ merged |
| PR2 #78 | Auto-titles fix + cross-persona + library dual-mode + 5 nav routes | 2026-05-20 | ✅ merged |
| PR4j #100 | Paywall audit: BETA bypass + synthetic /subscription + SubscriptionBootstrap | 2026-05-22 | ✅ merged |
| PR4l | Alembic revision_id VARCHAR(32) length fix | 2026-05-22 | ✅ merged |
| PR4m #99 | Migration 013 FK ondelete clauses | 2026-05-22 | ✅ merged |
| PR4k #101 | Google OAuth dormant + migration 014 + FRONTEND_URL + BASE_URL deprecation | 2026-05-23 | ✅ merged |
| PR4n #102 | SharePreviewModal + dynamic font + emoji strip | 2026-05-23 | ✅ merged |
| PR4o #103 | Rituals tab swap + /app/rituals page + Today RitualsCard simplified | 2026-05-23 | ✅ merged |
| PR4p #104 | api import fix (P0 ✅) + hydration guard (P1 ❌ reverted by PR4r) | 2026-05-23 | ✅ merged |
| PR4q #105 | Empty commit (stale local main — lesson only) | 2026-05-23 | ✅ merged (no-op) |
| PR4r | Actual rollback: revert hydration guard, keep api import fix | 2026-05-24/25 | ✅ merged |
| PR4s #108 | Conversation delete P0 fix: passive_deletes=True + cascade on Conversation.messages | 2026-05-24 | ✅ merged |
| PR4t #109 | RitualsCard removed from Today (PR4o follow-up) | 2026-05-24 | ✅ merged |
| PR4v #110 | Cleanup: TD-14 BASE_URL removal + TD-15 markdown fence strip + TD-16 INK_COLOR sync | 2026-05-24 | ✅ merged |
| PR4u #111 | Edge state pages: 404, in-app error boundary, global-error | 2026-05-24 | ✅ merged |
| PR4w | Docs v11 rotation | 2026-05-25 | ✅ merged |
| PR4x #113 | OTP autofill mobile fix — maxLength in auth/verify/page.tsx | 2026-05-25 | ✅ merged |
| PR4y | Auth redirect destination — 5 protected pages → /auth?mode=signin | 2026-05-25 | ✅ merged |
| PR4z | Pull-to-refresh disabled — globals.css overscroll-behavior-y: contain | 2026-05-25 | ✅ merged |
| PR4aa | Conversation titles prompt hardening + Render-shell backfill (5/5 ✅) | 2026-05-25 | ✅ merged |
| PR4ab | PersonaPickerSheet: stuck state + silent errors + delete feedback toasts | 2026-05-25 | ✅ merged |
| PR4u2 | Library search empty state card | 2026-05-25 | ✅ merged |
| PR4ad | Today card thumbnail uniformity: flex grammar + next/image migration | 2026-05-25 | ✅ merged |
| PR4ae #120 | Library ConversationCard readability: avatar 56px + font scale up | 2026-05-26 | ✅ merged |
| PR4af #121 | Account: scheduled letters card removed (17 lines) | 2026-05-26 | ✅ merged |
| PR4ag1 #122 | Share card v3: portrait 260px + fonts +4pt + bronze opacity + spacebar fix | 2026-05-26 | ✅ merged |
| PR4ah #123 | RitualIcons.tsx (new file) + nav tab symbol swap | 2026-05-26 | ✅ merged |
| L1 #124 | Migration 015: 20 btree FK indexes across 10 tables | 2026-05-26 | ✅ merged |

---

## 7. Environmental configuration

### Backend (Render)

```
DATABASE_URL                    ⚠️ Currently Supabase Ireland pooler
                                 PENDING SWITCH to Oregon after migration verifies clean
                                 Current: aws-0-eu-west-1.pooler.supabase.com:5432
                                 Target:  aws-0-us-west-2.pooler.supabase.com:5432

REDIS_URL                       ✅ Set (Upstash, eu-west-1)
RESEND_API_KEY                  ✅ Set
FROM_EMAIL                      "Great Minds <onboarding@resend.dev>" — test sender
JWT_SECRET                      ✅ Set
ANTHROPIC_API_KEY               ✅ Set — actively used for chat
ANTHROPIC_MEMORY_MODEL          "claude-haiku-4-5-20251001"
PHENOMENOLOGY_BRIDGE_ENABLED    ⚠️ State unverified (was true 2026-05-04/05)

FRONTEND_URL                    "https://thinkalike.netlify.app"
BETA_GRANT_PRO_TO_ALL           "true" — all users treated as Pro; toggle false before paid launch
GOOGLE_OAUTH_ENABLED            "false"
GOOGLE_CLIENT_ID                (placeholder)
GOOGLE_CLIENT_SECRET            (placeholder)

STRIPE_SECRET_KEY               ✅ Set
STRIPE_WEBHOOK_SECRET           ✅ Set
STRIPE_PRICE_PRO_MONTHLY        ✅ Set — €14.90/mo
STRIPE_PRICE_PRO_YEARLY         ✅ Set — €149/yr
STRIPE_PRICE_PREMIUM_MONTHLY    ✅ Set — placeholder

BASE_URL                        ⚠️ DEPRECATED (PR4k) — no app code reads it; safe to remove (TD-14)
ANTHROPIC_MODEL (config.py)     ⚠️ ORPHANED — not read by conversation_service.py (TD-03)
```

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set
```

---

## 8. Key file paths (production codebase)

### Backend (apps/api/)

All v11 paths apply. Additions since v11:

- `workers/arq_worker.py` — `generate_conversation_title` prompt hardened (PR4aa)
- `db/migrations/versions/015_add_fk_indexes.py` — 20 btree indexes on FK columns (L1 / #124)

### Frontend (apps/web/)

All v11 paths apply. Additions since v11:

- `app/auth/verify/page.tsx` — OTP maxLength fix for mobile autofill (PR4x / #113)
- `app/app/(tabs)/layout.tsx` — auth redirect to `/auth?mode=signin` (PR4y) + Rituals custom tab icon (PR4ah)
- `app/globals.css` — overscroll-behavior-y: contain (PR4z)
- `app/app/(tabs)/today/page.tsx` — flex grammar uniformity + next/image (PR4ad)
- `app/app/(tabs)/library/page.tsx` — ConversationCard readability (PR4ae) + empty state card (PR4u2)
- `app/app/(tabs)/account/page.tsx` — ScheduledLettersCard removed (PR4af)
- `components/share/SharePreviewModal.tsx` — share card v3 visual tweaks + .trim() removal (PR4ag1)
- `components/rituals/PersonaPickerSheet.tsx` — stuck state + errors + toasts (PR4ab)
- `components/rituals/RitualIcons.tsx` — NEW FILE: ReturningPathIcon + MirrorIcon SVGs (PR4ah)

---

## 9. Decision history (v12 additions)

### 2026-05-25 — Render paid plan upgrade

Philosopher-worker and philosopher-api both upgraded to paid Starter tier ($7/mo each). Cold-start eliminated on both services. C6c cold-start screen deprioritized as a result.

### 2026-05-26 — Oregon region migration (L1 → latency diagnosis → decision)

After L1 confirmed <5ms database queries, profiling identified 280ms Render Oregon ↔ Supabase Ireland RTT as the actual bottleneck. Decision: migrate Supabase to Oregon (us-west-2) to co-locate with Render. Non-disruptive: Ireland project stays intact and production-active until switch.

### 2026-05-26 — MCP migration pattern for vector data

Established: MCP is suitable for structured/relational data (row-by-row SQL). Not suitable for large vector payloads (2476 × 1536-dim ≈ 38MB exceeds context window). Pattern: re-ingest vector data from source (OpenAI embeddings script) rather than migrating rows.

### All prior decisions from v11 §9

Unchanged. See v11/v9/v8 for full history.

---

## 10. Section 5.7 framework — status

Unchanged from v11. All 9 personas have full character config. All elements live.

---

## 11. Migration plan — status

All phases through Block C complete. Unchanged from v11.

---

## 12. Deployment readiness

```
✅ Backend                Render web service philosopher-api
                          philosopher-api-z9l9.onrender.com
                          ✅ Paid Starter tier — no cold-start

✅ Worker                 Render worker philosopher-worker
                          ✅ Paid Starter tier — no cold-start
                          srv-d884bomgvqtc73ef2qrg

⚠️ Database               Supabase Ireland plecolxlzshkfvybszgs (eu-west-1)
                          alembic_version = '015_add_fk_indexes'
                          ⚠️ 280ms RTT to Render Oregon — DATABASE_URL switch PENDING
                          after Oregon migration completes

🟡 Oregon migration       bvzeuwzqgnqcghvqghtb (us-west-2)
                          Schema + ref data + partial user data done
                          messages/saved_lines/etc. pending next session

✅ Cache (Redis)          Upstash philosopher-prod (eu-west-1) free tier

🟡 Email                  Resend free tier (test sender only)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS

✅ Frontend (canonical)   Netlify thinkalike.netlify.app

✅ LLM                    Anthropic API wired (Haiku 4.5 free / Sonnet 4.6 pro)

✅ Stripe                 Sandbox wired. End-to-end test still pending.

🟡 Google OAuth           Dormant (GOOGLE_OAUTH_ENABLED=false). Code + DB ready.

🟡 Rituals email delivery Letter DB schema live; ARQ delivery not wired (BUG-014).
```

---

## 13. Session lessons (v12 additions)

### 13.1–13.5 Preserved from v11

Full text in v11. Key rules: P-01 through P-05 in CLAUDE.md. Most important: smoke test on merge.

### 13.6–13.7 Preserved from v11

BASE_URL silent 404 history (§13.6) and regression chain anatomy (§13.7). See v11 §13.

### 13.8 P-06 — Diagnose before code change (confirmed v12 — 2026-05-25-26)

P-06 was applied correctly three times in this session, each time correctly identifying a non-bug:

1. **"Share stuck" report:** Investigation showed it was Render cold-start delay on the free tier (now resolved by paid plan upgrade), not a code bug.
2. **"Letter to Future Self email" report:** Investigation confirmed the email sends as intended. No bug.
3. **"Reflections deleted" (carried from v11 post-mortem):** Already diagnosed in v11 as a user's own prior soft-delete action. Not a regression.

Zero premature code changes were made in response to these reports. P-06 is working.

### 13.9 MCP migration context window limit (NEW v12 — 2026-05-26)

MCP-based database migration has a hard limit: large binary/vector payloads exceed the context window budget. Discovered: 2476 × 1536-dim vectors ≈ 38MB. Schema DDL and relational rows migrate fine through MCP. Vector embeddings must be re-ingested from source.

**Pattern for future migrations:** Use MCP for structured data. Use existing ingestion scripts for vector data. Plan the migration sequence accordingly (structured data first, vectors last via separate operational step).

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v11. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. P-01 through P-06 apply to ALL sessions.

### The most important context for the next session

**The Oregon region migration is in progress.** The next session should begin by completing it — not by shipping new features. The migration state is documented precisely in `PROJECT_STATE_v12.md` §4. Do not switch DATABASE_URL until all tables are migrated and row counts verified.

After the Oregon switch, the 280ms per-call RTT tax goes away. Every user-facing interaction becomes ~600ms faster. That is the highest-leverage infrastructure change remaining before cold beta.

### Documentation hygiene

v12 baseline regen triggered by volume of session (11 PRs, infra upgrade, region migration). Next baseline regen threshold: major architecture change OR volume of a similar two-day session. Until then, append `*_v12_ADDENDUM_<date>.md` instead of rewriting v12.

---

**End of HANDOFF_BRIEF v12.** Authoritative as of 2026-05-26. Supersedes `HANDOFF_BRIEF_v11.md` (preserved as historical reference). Where v12 conflicts with v11, v12 wins.
