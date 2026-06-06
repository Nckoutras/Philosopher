# GREAT MINDS — Implementation Backlog v11

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v11 = v9 baseline (2026-05-20) + 2026-05-21-24 session delta (PR4j paywall-audit #100; PR4l alembic hotfix; PR4m FK ondelete hotfix #99; PR4k Google OAuth #101; PR4n Share v2 #102; PR4o Rituals #103; PR4p hotfix #104; PR4q empty commit #105; PR4r rollback in flight). TD-10 through TD-18 added. P0-04/08, P0-09, P1-01, P1-04 marked DONE.** *(No v10 was produced — docs jumped v9 → v11 to absorb two sessions.)*
>
> **Generated:** 2026-05-24 (v11 rotation)
>
> **How to read this file:**
> - This v11 file supersedes v9 and all prior backlog files.
> - Where v11 conflicts with v9, v11 wins.
> - Status, priority, and launch-readiness calls reflect 2026-05-24 state.
>
> **Companion documents:**
> - `PROJECT_STATE_v11.md` — current project state
> - `HANDOFF_BRIEF_v11.md` — continuity and implementation history
> - `SCREENS_TRACKING_v4.md` — full screen inventory (43 screens)
> - `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` — visual spec
> - `USER_FLOW_v4.md` — how screens connect
>
> **Priority key:**
> - **P0** = launch blocker / must be done before public launch
> - **P1** = post-revenue cleanup / fix shortly after first paying user
> - **P2** = v2 / post-MVP refinement
> - **P3** = post-launch / post-feedback backlog
> - **P4** = technical debt / infrastructure cleanup
>
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## v11 Consolidation Summary

### What shipped (2026-05-21-24) — items to mark DONE

| Item | PR | Status |
|---|---|---|
| PR4j — BETA_GRANT_PRO_TO_ALL bypass + synthetic /subscription + SubscriptionBootstrap | #100 | ✅ DONE |
| PR4l — alembic revision_id VARCHAR(32) length hotfix | hotfix | ✅ DONE |
| PR4m — migration 013 FK ondelete clauses | #99 | ✅ DONE |
| PR4k — Google OAuth dormant + migration 014 + FRONTEND_URL + BASE_URL deprecation | #101 | ✅ DONE |
| PR4n — SharePreviewModal + dynamic font + emoji strip | #102 | ✅ DONE |
| PR4o — Rituals tab swap + /app/rituals page + Today RitualsCard simplified + migration 012 | #103 | ✅ DONE |
| PR4p — api import fix in Today (P0 kept) + hydration guard (P1 reverted via PR4r) | #104 | ✅ DONE (partial) |

### Items previously in P0/P1 that shipped

These v9 backlog items are now closed. They appear as DONE in §11 below and are NOT carried forward as open work:

| Old ID | Description | PR |
|---|---|---|
| P0-04 / P0-08 | Paywall + subscription bootstrap (PR4j) | #100 |
| P0-09 | Google OAuth implementation (PR4k, dormant) | #101 |
| P1-01 | Share v2 modal polish (PR4n) | #102 |
| P1-04 | Rituals tab + page (PR4o) | #103 |

### New tech debt captured (TD-10 through TD-18)

Ten new items added since v9. See §3 below.

---

## 1. Current Launch Interpretation

**Plan A (active).** Current priority order as of 2026-05-24:

1. ~~**C5 — Chat UI frontend**~~ DONE (2026-05-17)
2. ~~**C3b — Corpus ingestion**~~ DONE (2026-05-17)
3. ~~**Stripe sandbox wiring**~~ SANDBOX COMPLETE (PR1 #77, 2026-05-19)
4. ~~**D1 Home/Today**~~ DONE (PR #76, 2026-05-18)
5. ~~**A0 Public Landing**~~ DONE (PR #76 + PR1 #77)
6. ~~**Paywall + subscription bootstrap (PR4j)**~~ DONE (#100)
7. ~~**Share v2 (PR4n)**~~ DONE (#102)
8. ~~**Rituals tab + page (PR4o)**~~ DONE (#103)
9. **PR4r merge** — complete actual rollback of hydration guard (in flight 2026-05-24)
10. **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel)
11. **Backfill-titles admin execution** (`POST /api/v1/admin/backfill-titles`)
12. **Mobile 12-point nav smoke test** (real iOS Safari — includes Rituals tab)
13. **Cold beta with 3–5 fresh users**
14. **Block B consolidated polish PR**
15. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)
16. **UAT** (≥2/5 spontaneous "I'd pay")
17. **Public launch**

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.1 Code-side P0

### P0-NEW — Conversation deletion failing (2026-05-24, found in post-restore smoke test)

User reports DELETE conversation throws error. Reproducible.
Suspected causes (investigate in order):

1. PR4m migration 013 FK CASCADE ondelete clauses may have changed
   the deletion path semantics. Specifically: memory_entries CASCADE,
   insights CASCADE, safety_events SET NULL, user_ritual_completions
   SET NULL — verify these don't conflict with the soft-delete logic
   in conversations.deleted_at
2. DELETE /api/v1/conversations/{id} endpoint may return non-2xx
   status. Check Render logs after a failed delete attempt
3. Frontend SwipeableRow handler may call wrong endpoint or fail
   to refresh state after delete

Investigation approach for next session:
- Reproduce in user's normal browser (logged-in session)
- Capture exact error from Network tab + Console
- Check Render logs for the specific request
- If backend error: check delete_conversation service logic
- If frontend issue: check Library or chat conv page delete handler

Priority: P0 — affects every paid user who wants to clean up history.
Pre-paid-launch blocker.

- [ ] **bugfixes-3 — auth race fix** (P0; see TD-10 for approach options)
- [ ] **PR4r merge** (in flight — reverts hydration guard, keeps api import fix)
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel → tier downgrade)
- [ ] **Backfill-titles admin execution** (`POST /api/v1/admin/backfill-titles`)
- [ ] **Mobile 12-point nav smoke test** (5 fixed routes + tab bar including Rituals + chat + upgrade on real iOS Safari)
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure — 9 mobile walkthrough findings)

### 2.2 Legal P0

- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **GDPR / DPA infrastructure** (Anthropic DPA, processors doc, data subject request fulfillment)
- [ ] **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety escalation)

### 2.3 Infrastructure P0

- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** in Render env
- [ ] **RLS policies** as defense-in-depth (even with FastAPI gateway)

### 2.4 UAT P0

- [ ] **UAT** with 3–5 mixed testers (≥2/5 spontaneous "I'd pay")

---

## 3. Tech debt items

### TD-01 — Split rate_limit_service.py

**Priority:** P2
**File:** `apps/api/services/rate_limit_service.py`

Two unrelated rate limiters coexist in one file. Split into `services/auth_rate_limit.py` (Redis/OTP) + `services/message_rate_limit.py` (DB/daily messages). See v9 for full detail.

### TD-02 — PersonaConfig / Persona ORM naming confusion

**Priority:** P2
**Files:** `apps/api/personas/_base.py`, `apps/api/models/__init__.py`, `apps/api/services/persona_voice.py`

`PersonaConfig` dataclass has no `.config` attribute; ORM `Persona` has `.config` JSONB dict. `get_error_voice()` must receive ORM object. Current streaming path is correct but naming is a latent maintenance risk. See v9 for full detail.

### TD-03 — Update or remove ANTHROPIC_MODEL constant

**Priority:** P2
**File:** `apps/api/config.py`

`ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"` — stale orphan. Not read by `conversation_service.py`. Remove or update before it misleads someone.

### TD-04 — C-RECON-6 backoff discrepancy

**Priority:** P4
**File:** `apps/api/services/conversation_service.py`

PATH A retry: 0s/2s/4s (attempt starts at 0). Document as intentional or harmonize to 2s/4s/8s.

### TD-05 — Wire generate_insight_task

**Priority:** P1
**File:** `apps/api/workers/arq_worker.py`

`generate_insight_task` is defined but never enqueued. Wire when memory_entries accumulates real data (≥10 entries for a user).

### TD-06 — safety_events.message_id always NULL

**Priority:** P4
**File:** `apps/api/services/conversation_service.py`

Safety events log correctly; `message_id` FK not threaded through. Minor cleanup.

### TD-07 — gh CLI on founder's Windows

**Priority:** P4

`winget install --id GitHub.cli`

### TD-08 — Document Render alembic auto-run mechanism

**Priority:** P2

Alembic runs `upgrade head` on container startup. Mechanism (Procfile? Dockerfile CMD?) undocumented. Document before next engineer touches deployment pipeline.

### TD-09 — One-fix-per-PR rule (process — from PR #72 post-mortem)

**Priority:** P4 (process discipline)

PR #72 bundled auth hydration guard + savedLines sync fix. Hydration guard broke production; sync fix was sound. Surgical revert required. Rule: one logical change per PR. Auth/hydration changes require isolated PR + mandatory preview smoke test. See v9 for full detail.

---

### TD-10 — Zustand hydration race condition (P1, must smoke test before any new attempt)

**Priority:** P1 (pre-paid-launch; do not attempt without Netlify preview smoke test)

**Background:** `persist` middleware hydrates asynchronously in Next.js. Per-page auth `useEffect`s fire before hydration completes → flash redirect to `/auth` on hard refresh or direct URL access to protected routes (Reflections, Library, Rituals, chat pages).

**Failed attempt (PR4p):** Added `_hasHydrated` state slice + `onRehydrateStorage` callback. The callback never fired in the production Next.js build (timing differs from local dev). Result: `_hasHydrated` was always `false`; the create-conversation effect was permanently blocked; all chat screens showed "Summoning..." stall for all users. PR4r reverts this.

**Future approaches to investigate (in order of preference):**
1. `skipHydration: true` + manual `useStore.persist.rehydrate()` in a SSR-safe wrapper component
2. Move auth check to Next.js middleware level (server-side cookie check) instead of per-page `useEffect`
3. Use Next.js cookie-based auth check on the server side entirely

**CRITICAL process requirement:** Any new attempt MUST be smoke tested on Netlify preview deploy with:
- Hard refresh on protected route (e.g., `/app/rituals`)
- Direct URL navigation (paste URL into new tab)
- Normal navigation from auth → app
- All three must work correctly before merging to main. Unit tests are NOT sufficient.

**Why:** PR4p had passing unit tests + clean code review. Failed in production build. Preview deploy would have caught in 5 minutes. PR4p did not have a preview smoke test.

### TD-11 — Tier resolution unified refactor (P2, pre-paid-launch)

**Priority:** P2 (refactor before disabling BETA_GRANT_PRO_TO_ALL)

**Background:** Two parallel tier-resolution functions exist with different semantics:
- `apps/api/auth.py:get_current_user_plan` — returns `"free" | "pro" | "premium"` from `Subscription.plan` directly (no expiry check)
- `apps/api/services/tier_service.py:get_user_tier` — returns `"free" | "pro"` with expiry/status validation + BETA bypass

PR4j added BETA bypass to both as a workaround. 8 endpoints use `get_current_user_plan`; 5 use `get_user_tier`. Frontend `isPro` depends on whichever the called endpoint returns.

**Required before paid launch:** Consolidate to a single tier-resolution function used by all enforcement points. Decision needed: keep `"premium"` tier semantics or collapse to `free | pro`. Affects all paywall gates and frontend `Subscription` type.

**References:** CLAUDE.md "Known tech debt — Dual tier resolution".

### TD-12 — Soft-delete pattern for conversations (P2, pre-paid-launch)

**Priority:** P2

`conversations.deleted_at` column exists (migration 007) but is never set. Currently using hard DELETE with CASCADE FK. Before paid launch:
- Expose soft-delete in DELETE endpoint (set `deleted_at = now()` instead of hard delete)
- Filter all queries to `WHERE deleted_at IS NULL`
- Implement undo window (30 days?)
- Periodic cleanup cron for old soft-deletes
- GDPR compliance path: true hard delete on explicit user data request

### TD-13 — Modal abstraction (P3)

**Priority:** P3

Three inline modals now exist:
- `DeleteConversationModal` (v9)
- `PaywallModal` (v9 — C5)
- `SharePreviewModal` (PR4n)

When a 4th modal is needed, refactor to a shared `Modal` primitive with consistent backdrop + dismiss behavior (Escape key, click-outside, animation). Defer until 4th modal is required.

### TD-14 — BASE_URL legacy cleanup (P4)

**Priority:** P4
**File:** `apps/api/config.py`

`BASE_URL` setting remains in config.py but no app code reads it post-PR4k (all 6 call sites migrated to `FRONTEND_URL`). Remove the setting in the next cleanup PR. Verify no orphan imports first via grep.

Note: Original value was `https://philosopher-api.onrender.com` which 404s — the correct backend URL is `https://philosopher-api-z9l9.onrender.com`. The misconfiguration meant Stripe success/cancel URLs and ritual reminder email links were broken for weeks before PR4k fixed it.

### TD-15 — Memory extraction JSON parse fix (P3)

**Priority:** P3
**File:** `apps/api/services/memory_service.py`

~5-line markdown fence strip needed when LLM wraps JSON in ``` fences. Background task; no UX impact until memory extraction is actively accumulating. Low priority until organic users exist.

### TD-16 — INK_COLOR mismatch (P4)

**Priority:** P4
**Files:** `apps/api/services/image_service.py`, `apps/web/tailwind.config.ts`

`image_service.py` uses `#1A1A1A` as ink color. Tailwind config uses `#1F1B14`. 1-line fix. No user-visible impact until image generation is prominent.

### TD-17 — Weekly Reading full implementation (post cold-beta, multi-week)

**Priority:** Post cold-beta validation (P2 after cold beta passes)

Multi-source aggregator (chat sessions + Letter entries + Mirror + Counterview sessions). LLM-driven weekly synthesis. Email delivery via Resend with phased rollout:
- **Phase A:** "Your reading awaits" — purely positive notification; no re-engagement pressure
- **Phase B:** Re-engagement nudge ("come feed your reading") — opt-in only

Engineering scope: ~3–5 days. Not before cold beta validation (no point if product doesn't resonate).

### TD-18 — Hydration guard process lesson (process)

**Priority:** P4 (process — codified in CLAUDE.md P-01 through P-05)

The sequence of failures in May 21-24 sessions (PR4n regression → PR4p bundled fix → PR4q empty commit → PR4r rollback) established 5 mandatory process rules now in CLAUDE.md:

- **P-01:** Always `git fetch origin && git reset --hard origin/main` before any hotfix branch. Branching from stale local main = empty merge (PR4q lesson).
- **P-02:** One logical change per PR. P0 fix + P1 experiment in same PR = anti-pattern (PR4p lesson).
- **P-03:** Smoke test on merge. After any UI/state-management merge, 2-minute manual check before next PR brief.
- **P-04:** Preview deploy validation for any Zustand/auth/layout/api-client change (PR4p lesson).
- **P-05:** Grep original file for ALL usages of removed imports before deleting (PR4n lesson).

### TD-19 — Ritual icon set (P2, post-cold-beta)

**Priority:** P2

Aesthetic direction LOCKED 2026-05-24: editorial minimalism, NOT tarot/antique engraving.

Reference brands for visual language:
- Aesop packaging (refined, restrained)
- Pentagram design (Linear, Mailchimp redesign)
- A24 film posters (classical typography, minimal)
- NYT Op-Ed illustration style
- Iconoir / Phosphor Icons (modern monoline)

Style requirements (strict):
- Single uniform stroke weight (clean monoline)
- Geometric abstraction, not literal depiction
- Bronze (#B89968) line on transparent background
- Generous negative space
- Maximum 2-3 visual elements per icon
- No engraving texture, no antique feel, no ornament
- No tarot/occult symbolism (no constellations, candles, moons, wax seals)

4 icons needed for launch MVP:
- The Mirror — oval with diagonal stroke OR two stacked circles
- The Counterview — opposing arrows OR mirrored triangles
- Letter to my Future Self — simple envelope outline, no decoration
- The Weekly Reading — three stacked horizontal lines OR open book

4 additional concepts parked for future rituals (Daily Question, Examined Day, Unanswered Questions, Thought Card) — visual exploration only, NOT roadmap commitment.

Asset generation: DALL-E 3 with prompt template documented in May 24 chat session. PNG 1024x1024 with transparent background, background-removed via remove.bg post-processing. Optional SVG conversion via Vectorizer.AI for vector format.

Implementation: ~30-40 lines code change (icon assets in apps/web/public/icons/rituals/ + rituals page component update + Today RitualsCard letter icon). Estimated 1 hour implementation after source files ready.

Trigger: post cold-beta validation + brand decision locked.

### TD-20 — safety_events.message_id FK ondelete (P2, pre-cold-beta)

**Priority:** P2  
**File:** new migration `apps/api/db/migrations/versions/015_*.py`

`safety_events.message_id` currently uses `ON DELETE NO ACTION`. Inconsistent with PR4m migration 013 pattern which set `safety_events.conversation_id` to `SET NULL`. Latent bug: when safety pipeline starts populating message_id (currently 0 rows), any message hard-delete will fail FK constraint check.

Fix: 1-line ALTER in new migration 015.

### TD-21 — passive_deletes audit (P2, pre-paid-launch)

**Priority:** P2  
**File:** `apps/api/models/__init__.py`

PR4s fixed `Conversation.messages` relationship. Other parent-child relationships likely have the same latent bug (SQLAlchemy will try to nullify children's FK before DB-level CASCADE fires). Candidates to audit:

- User.conversations
- User.messages (if defined)
- User.saved_lines (if defined)
- Any other parent → child relationship where DB has ON DELETE CASCADE

Not user-visible today because these parents are never deleted in production flows. Becomes P0 when delete-account / GDPR data-deletion flow is exposed.

Fix pattern (apply per relationship):
```python
cascade="all, delete-orphan",
passive_deletes=True,
```

---

## 4. Database schemas

See `PROJECT_STATE_v11.md` §4 for current state. Migration head: `014_user_oauth_columns`. Migrations 012 (scheduled_emails), 013 (FK ondelete), and 014 (user oauth cols) applied since v9.

---

## 5. Config & Environment Variables

See `HANDOFF_BRIEF_v11.md` §7 for full env var list and status.

**New since v9:**
- `FRONTEND_URL` — set to `https://thinkalike.netlify.app` (replaces BASE_URL for Stripe + ritual emails)
- `BETA_GRANT_PRO_TO_ALL` — set to `"true"` in Render
- `GOOGLE_OAUTH_ENABLED` — set to `"false"` in Render
- `GOOGLE_CLIENT_ID` — placeholder (set when brand decision made)
- `GOOGLE_CLIENT_SECRET` — placeholder (set when brand decision made)
- `BASE_URL` — deprecated; remove in cleanup PR (TD-14)

---

## 6. Stripe Wiring (sandbox complete — PR1 #77)

Status: 🟢 **Sandbox complete (PR1 #77, 2026-05-19).** Unchanged from v9. End-to-end sandbox test still pending (see §2.1 P0 checklist).

**BETA bypass:** During cold beta, all users receive Pro entitlement via `BETA_GRANT_PRO_TO_ALL=true`. Stripe checkout/portal remain functional for testing purposes. Disable bypass before paid launch.

---

## 7. Persona-specific maintenance backlog

### P2 — ChatGPT audit of new persona configs

Status: 🔴 not started (founder-owned). Lao Tzu, Wilde, Machiavelli, Jung. Surgical JSONB UPDATE edits.

### P2 — Extract new personas to YAML

Status: 🔴 not started. `apps/api/philosopher_brain/lao_tzu.yaml`, `oscar_wilde.yaml`, `niccolo_machiavelli.yaml`.

### P2 — Portrait style harmonization

Status: 🔴 not started. Aurelius + Socrates are painterly outliers vs 7 atmospheric/hybrid others.

---

## 8. LLM eval (optional)

Status: ⏸ P3. Workbench A/B test (2026-05-15) provides sufficient confidence. Optional additional eval for Lao Tzu post-revenue.

---

## 9. Future blocks reference

### 9.1 Block C — complete

C5 frontend ✅, C3a RAG infrastructure ✅, C3b corpus ingestion ✅. All closed.

### 9.2 Block D — D1 complete, D2/D3 not planned

D1 ✅ (PR #76, 2026-05-18). D2, D3 not yet planned.

### 9.3 Block F — Reflection

F1 ✅ (basic reflections page). F2/F3/F4 demoted to P2. F6 (library) ✅.

### 9.4 Block H — Subscription & Billing

Stripe sandbox ✅ (PR1 #77). `/api/v1/subscription` synthetic endpoint ✅ (PR4j). End-to-end sandbox test pending.

### 9.5 Block I — Account & Settings

I1 Account hub not yet built. Spec locked. P1 (after D1 tab bar live).

### 9.6 Block J — Empty/error states

Not yet planned. Often handled inline with other blocks.

### 9.7 Rituals (new block, post PR4o)

- **Letter to my Future Self:** UI live (PR4o). Scheduled email ARQ delivery NOT YET WIRED (BUG-014). DB schema live (migration 012).
- **The Mirror:** LOCKED (placeholder card)
- **The Counterview:** LOCKED (placeholder card)
- **The Weekly Reading:** LOCKED (placeholder card; full implementation = TD-17)

---

## 10. Operating principles (preserved + extended)

### 10.1–10.20 — Preserved from v9

Full text in prior handoff briefs. Key rules:
- §19.14: Unicode JSONB encoding pre-merge check
- §19.15: Mobile walkthrough is non-substitutable
- §19.16: Read existing docs before writing replacement docs
- §19.17: Addendum vs baseline regen discipline

### 10.21 — Production safety principles (NEW v11 — 2026-05-24)

Codified in `CLAUDE.md` as P-01 through P-05. Summary:

- **P-01:** `git fetch origin && git reset --hard origin/main` before every hotfix branch
- **P-02:** One logical change per PR
- **P-03:** Smoke test on merge (2 minutes, before next PR brief)
- **P-04:** Preview deploy required for any Zustand/auth/layout/api-client change
- **P-05:** Grep original file for all import usages before extracting a component

These rules exist because of the May 21-24 regression chain:
1. PR4n removed `api` import accidentally (missed by code review)
2. PR4p bundled fix + experiment; experiment broke production
3. PR4q was empty due to stale local main
4. PR4r correctly reverts — but 3 PRs and ~18 hours lost

---

## 11. Backlog by priority (consolidated)

## 11.1 P0 (launch blockers)

- [x] **C5 — Chat UI frontend** — DONE (2026-05-17)
- [x] **C3 — RAG + corpus ingestion** — DONE (2026-05-17)
- [x] **D1 Home/Today** — DONE (PR #76, 2026-05-18)
- [x] **A0 Public Landing** — DONE (PR #76 + PR1 #77, 2026-05-19)
- [x] **Stripe sandbox wiring** — SANDBOX DONE (PR1 #77, 2026-05-19)
- [x] **PR4j paywall-audit + BETA bypass** — DONE (#100, 2026-05-22)
- [x] **PR4n Share v2** — DONE (#102, 2026-05-23)
- [x] **PR4o Rituals tab + page** — DONE (#103, 2026-05-23)
- [x] ~~**Landing page waitlist test**~~ — superseded (Stripe wired directly)
- [ ] **P0-NEW — Conversation deletion failing** (post-restore smoke test 2026-05-24; see §2.1 for investigation approach)
- [ ] **PR4r merge** (in flight — revert hydration guard, keep api import fix)
- [ ] **bugfixes-3 — auth race fix** (TD-10; P1, preview smoke test required before any attempt)
- [ ] **End-to-end Stripe sandbox test**
- [ ] **Backfill-titles admin execution**
- [ ] **Mobile 12-point nav smoke test**
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure)
- [ ] **Lawyer review** of Terms / Privacy / Disclaimer
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**
- [ ] **RLS policies** as defense-in-depth
- [ ] **UAT** with 3–5 testers, ≥2/5 spontaneous "I'd pay"

## 11.2 P1

- [ ] **TD-05** — Wire generate_insight_task (when memory_entries accumulating)
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **Render API plan upgrade** (~$7/mo cold-start elimination; before UAT)
- [ ] **C6c — cold-start screen** (UX for Render free-tier idle; before UAT)
- [ ] **I1 Account hub build** (spec locked; tab bar via D1 first)
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to my Future Self — ARQ email delivery wiring** (BUG-014)
- [x] ~~**Google OAuth implementation**~~ — DONE (PR4k #101; dormant — GOOGLE_OAUTH_ENABLED=false)
- [x] ~~**Share v2 polish**~~ — DONE (PR4n #102)
- [x] ~~**Rituals tab + page**~~ — DONE (PR4o #103)

## 11.3 P2 (tech debt)

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch — must do before disabling BETA bypass)
- [ ] **TD-12** — Soft-delete pattern for conversations (pre-paid-launch)
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-01** — Split `rate_limit_service.py`
- [ ] **TD-02** — PersonaConfig / Persona ORM naming confusion
- [ ] **TD-03** — Update or remove `ANTHROPIC_MODEL` constant
- [ ] **TD-08** — Document Render alembic auto-run mechanism
- [ ] **ChatGPT audit** of new persona configs
- [ ] **Portrait style harmonization**
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML**
- [ ] **Premium tier reassignment** (Freud → premium if desired; 1-line UPDATE)
- [ ] **C9 real implementation** (C9b inline second-opinion; post-revenue)
- [ ] **F2 Suggested insights (lite)** (post-revenue; requires memory accumulation)
- [ ] **F3/F4 Weekly letter inbox + detail** (post-revenue; see TD-17)
- [ ] **TD-17** — Weekly Reading full implementation
- [ ] **B1 hydration polish** — 0.5s flash before auth-guard redirect
- [ ] **TD-20** — safety_events.message_id FK ondelete (pre-cold-beta)
- [ ] **TD-21** — passive_deletes audit across remaining parent-child relationships in apps/api/models/__init__.py (pre-paid-launch)

## 11.4 P3

- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **Desktop layout polish** — mobile-first looks broken >768px
- [ ] **Phase 5 register architecture + UI chips** — post-feedback
- [ ] **Phase 6 eval suite + CI** — post-revenue
- [ ] **LLM eval test** for Lao Tzu (optional confidence check)
- [ ] **LLM classifier** (safety layer 3) — from Decision #6

## 11.5 P4

- [ ] **TD-04** — Backoff discrepancy (0s/2s/4s; document or harmonize)
- [ ] **TD-06** — `safety_events.message_id` always NULL
- [ ] **TD-07** — `gh CLI install on founder's Windows`
- [ ] **TD-18** — Process lesson (already codified in CLAUDE.md; keep for audit trail)
- [ ] **Stale branch cleanup**
- [ ] **openapi.json → .gitignore** (separate cleanup PR)
- [ ] **Legal pages `target="_blank"` rel hardening**

---

## 12. Plan A vs Plan B (preserved)

### 12.1 Plan A — 43-screen build before launch (ACTIVE)

Unchanged from v9. Remaining work: Cold beta → consolidated polish PR → lawyer review + GDPR → UAT → launch.

### 12.2 Plan B — Minimum-to-revenue interrupt (preserved, not active)

Available as pivot if UAT signal < 2/5 "I'd pay" or timeline slips beyond cold beta.

---

## 13. KIEN — separate project note

Unchanged from v9. This v11 backlog is **Philosopher-only**.

---

**End of IMPLEMENTATION_BACKLOG v11.** Authoritative as of 2026-05-24. Supersedes `IMPLEMENTATION_BACKLOG_v9.md` (preserved as historical reference). *(v10 was skipped — two sessions absorbed into one rotation.)*
