# HANDOFF BRIEF v16 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-03
**Prior version:** `docs/HANDOFF_BRIEF_v15.md` (2026-06-01)
**Generated:** 2026-06-01 (v16 rotation) · **Last appended:** 2026-06-03 (revenue chain + PR3a triage)

**Block trigger for v16 baseline regen:** The Council shipped end-to-end (C5–C7c, PRs #182–#186, 2026-06-01). 4-member council, sequential verdicts, app-voice synthesis, save/unsave toggle, share PNG. Migrations 019 + 020. Session volume sufficient for rotation.

**v16 baseline (2026-06-01):** Council ✅ COMPLETE. Mirror ✅ COMPLETE. BETA_GRANT_PRO_TO_ALL still enabled — top revenue-gate blocker. Next: revenue gate (TD-11 + BETA off + Stripe test), then share card redesigns and Counterview.

**2026-06-02 append:** You vs You ✅ COMPLETE (PRs #193–#202, migration 021). WiseMark shipped (#191). TD-11 🔴 not started; BETA flip 🟡 in progress / verify (flip initiated on Render, redeploy pending); Stripe smoke test 🔴 pending.

**2026-06-03 append:** TD-11 ✅ DONE (#203). BETA_GRANT_PRO_TO_ALL ✅ OFF (both services). Stripe webhook URL corrected. current_period_end fix (#205). Account auth hydration fix (#207, dfbfd81). **Revenue chain CLOSED in TEST/sandbox.** PR3a sweep triage agreed. Brand name "The Wise Room" locked (rename audit pending).

**Status:**
- Block A ✅ FULLY CLOSED (5/5)
- Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending)
- Block C ✅ FULLY COMPLETE — real-time streaming added PR-A (#128)
- Stripe sandbox ✅ COMPLETE (PR1 #77, 2026-05-19)
- Paywall + BETA bypass ✅ COMPLETE (PR4j #100)
- Share v3 ✅ COMPLETE (PR4ag1 #122)
- Rituals tab + page ✅ COMPLETE (PR4o + PR4ah) — Mirror/Council live; Counterview/Weekly Reading placeholder-locked
- Greeting personalization ✅ COMPLETE (PR-D #129)
- Name capture prompt ✅ MERGED (PR-D2 #130) — smoke test partially blocked by OTP issue
- Bug #1 ✅ FIXED (#127 — BottomSheet history.back race)
- Bug #4 ✅ FIXED (PR-A #128 — real-time streaming)
- Typography PR-F ✅ COMPLETE (2026-05-29)
- C9 "Bring another mind" / PR-B ✅ COMPLETE (2026-05-29) — Pro-gated; cross-mind awareness shipped
- Voice overhaul ✅ COMPLETE (2026-05-30)
- **The Mirror ✅ COMPLETE (2026-06-01)** — PRs #166–#173; generator + cron + host picker + ring-true; migrations 017 + 018
- **The Council ✅ COMPLETE (2026-06-01)** — PRs #182–#186; 4 members; verdicts + synthesis SSE; save/unsave; share PNG; migrations 019 + 020; boardroom screen live
- **WiseMark ✅ SHIPPED (#191)** — standalone icon component; placed on Council synthesis card
- **You vs You ✅ COMPLETE (2026-06-02)** — PRs #193–#202; self_comparisons table (migration 021); dual-self SSE; closing card with evidence quotes + ring-true; weekly limit pro=5/wk, premium=30/wk; usage meter + premium nudge; faded bg
- **TD-11 ✅ DONE (#203, 2026-06-03)** — canonical tier resolver: `get_user_tier` is single source; `get_current_user_plan` wraps it; dual tier resolution tech debt resolved
- **BETA_GRANT_PRO_TO_ALL ✅ OFF (2026-06-03)** — confirmed disabled on both API and worker
- **Stripe webhook URL ✅ corrected (2026-06-03)** — `/api/v1/billing/webhook` (sandbox)
- **current_period_end fix ✅ (#205, 2026-06-03)** — reads from `subscription.items.data[0]`; regression tests added
- **Account auth hydration fix ✅ (#207, dfbfd81, 2026-06-03)** — `useHydrated()` via Zustand; supersedes #204 and #206
- **🟢 REVENUE CHAIN CLOSED IN TEST/SANDBOX (2026-06-03)** — signup → checkout → 4242 → webhook 200 → tier = pro → account renders → "Welcome to Pro"
- Oregon region migration ✅ CONFIRMED LIVE — bvzeuwzqgnqcghvqghtb (us-west-2)
- Upstash ✅ Pay-as-You-Go (upgraded 2026-05-27)
- ANTHROPIC_API_KEY ✅ Re-added to both services (2026-05-27/28)

> **v16 conflict resolution rule:** Where v16 conflicts with v15 or earlier, v16 wins. Production reality always wins over docs.

## v16 Session Delta (2026-06-01)

> v16 = v15 baseline + The Council shipped end-to-end. Where v16 conflicts with v15, v16 wins.

**Shipped (PRs #182–#186):**

- **The Council** — full Council feature live. Full technical detail in `PROJECT_STATE_v16.md §v16 Session Delta`.
  - 4 members: Machiavelli, Epictetus, Freud, de Beauvoir. All Pro-tier.
  - Sequential SSE stream: `convening` → per-member `member`/`chunk` events → `synthesis_start`/`chunk` → `done` (carries `case_id` + `session_id`).
  - Boardroom screen: `INTRO_HOLD=2100`, word-reveal rAF loop, bench animation (pending→lighting→speaking→done), auto-scroll, synthesis card, Save/Share buttons.
  - Save: `council_saves` table; `POST+DELETE /council/{id}/save`; optimistic toggle.
  - Share: shared Pillow `_render_share_canvas`; `POST /council/{id}/share`; `kind='council'` in `SharePreviewModal`; downloads as `council-reading.png`.
- **Mirror animated** — `INTRO_HOLD` updated 1100→2100 in both mirror and council pages.

**Key superseded facts:**
- `alembic_version` = **`020_create_council_saves`** (was `018_user_mirror_host`). Two new migrations: `019_create_council` + `020_create_council_saves`.
- The Council: was Phase 5 parked → **🟢 SHIPPED**.
- `image_service.py`: `_compose_canvas` → `_render_share_canvas` (shared core); reflections output byte-identical.
- Share counter is **shared** between reflections and council: key `share_screenshot:{user.id}`, 3/90-day free-tier limit.

---

## v15 Session Delta (2026-06-01)

The Mirror shipped (PRs #166–#173). Full detail in `HANDOFF_BRIEF_v15.md §v15 Session Delta`.

---

## 2026-06-02 Session Delta — You vs You + polish PRs

> Appended to v16. Where this conflicts with the v16 baseline, this section wins.

**Polish / brand (PRs #190–#192, between Council and You vs You):**

- **#190** — Mirror reveal frameless + center Council idle heading
- **#191** — WiseMark icon component added; placed on Council synthesis card
- **#192** — Ritual hub descriptor copy sharpened

**You vs You — full ritual shipped (PRs #193–#202):**

- **DB:** `self_comparisons` table (migration 021). Columns: `id UUID PK`, `user_id FK CASCADE`, `prompt TEXT NOT NULL`, `then_start / then_end / now_start / now_end TIMESTAMPTZ` (window boundaries), `payload JSONB` (carries dual-self answers + closing), `status VARCHAR(20) DEFAULT 'pending'`, `ring_true VARCHAR(10)`, `ring_true_note TEXT`, `ring_true_at TIMESTAMPTZ`, `created_at TIMESTAMPTZ`. Index: `ix_self_comparisons_user`.
- **Model:** `SelfComparison` ORM in `models/__init__.py`.
- **Services:** `self_model_service` (pure-read; splits active `memory_entries` into then/now windows: earliest 12 = then, latest 12 = now; unlock gate: ≥20 total active signals AND ≥14 day span; forming state below threshold); `self_comparison_service` (SSE stream: two safety gates → dual first-person LLM generation [then / now] → app-voice closing with VERBATIM evidence quotes selected by `message_id` + anti-hallucination guard + degradation ladder → `done` with `comparison_id`); `self_comparison_prompts` (SELF_SYSTEM_PROMPT, CLOSING_PROMPT). Model: `MODEL_PRO = claude-sonnet-4-6`.
- **API:**
  - `GET /self-comparison/status` — unlock/forming state + `weekly_remaining` / `weekly_limit` / `plan` (when unlocked)
  - `POST /self-comparison` — Pro-gated (plan ∉ {pro, premium} → 403); weekly rate-limit tier-aware (pro=5, premium=30; admins bypass); SSE stream
  - `PATCH /self-comparison/{id}/ring-true` — 204; sets `ring_true`, `ring_true_note`, `ring_true_at`
- **SSE events:** `safety` → `chunk[safety]` → `done` (suppressed path); `error[not_unlocked]`; `self` (which, start, end) → `chunk` (which, data); `closing` (observation, question, then_quote, now_quote); `done` (comparison_id)
- **Tiers/limits:** Pro+ only; free → 403. Weekly limits tier-aware: pro=5, premium=30.
- **Frontend:** `/app/you-vs-you` screen — locked/forming guard → input (textarea + saved-lines accordion) → dual-self streaming reveal THEN/NOW (date spans) → "The Wise Room says" closing card (WiseMark + observation + question + verbatim evidence quotes + ring-true pills + humility line); weekly usage meter + pro→premium upgrade nudge (→ `/app/upgrade`); faded room background (`/personas/youvsyou.webp`); hub card on `/app/rituals`.
- **`lib/api.ts`:** `getSelfComparisonStatus`, `streamSelfComparison`, `setSelfComparisonRingTrue` added.

**Key superseded facts:**
- `alembic_version` = **`021_create_self_comparisons`** (was `020_create_council_saves`)
- You vs You: was planned/backlog → **🟢 SHIPPED end-to-end**
- Rituals hub: Mirror ✅ Council ✅ You vs You ✅ (Counterview + Weekly Reading still placeholder-locked)

---

## 2026-06-03 Session Delta — Revenue chain + PR3a triage

> Appended to v16. Where this conflicts with the v16 baseline or 2026-06-02 section, this section wins.

**Shipped (merged to main, TEST/sandbox):**

- **TD-11 (#203):** `services/tier_service.py:get_user_tier` is the single source of truth. `auth.py:get_current_user_plan` is a thin wrapper. `rate_limit_service` enforces `plan in ("pro","premium")`. Resolves the dual tier resolution tech debt.
- **BETA_GRANT_PRO_TO_ALL = OFF:** Disabled on both API and worker services.
- **Stripe webhook URL corrected (sandbox):** `/api/v1/billing/webhook`.
- **current_period_end fix (#205):** Reads from `subscription.items.data[0]`. Stripe moved this field off the top-level Subscription object in their API version 2026-04-22. Regression tests added.
- **Account auth hydration fix (#207, dfbfd81):** `useHydrated()` hook via Zustand `onFinishHydration` / `hasHydrated` / `rehydrate`. Supersedes and removes the `mounted`-state approach from failed #204 and #206.
- **Revenue chain verified end-to-end in TEST/sandbox ✅**

**PRs that failed and were superseded:**
- #204: `_hasHydrated` guard approach — failed in production Next.js build; removed.
- #206: `mounted` state approach — also failed; removed.

**Key superseded facts:**
- TD-11: was "unresolved known tech debt" → **RESOLVED.**
- BETA_GRANT_PRO_TO_ALL: was "🟡 in progress" → **🟢 OFF.**
- Stripe sandbox test: was "🔴 pending" → **🟢 COMPLETE.**

**Investigation findings:**
- **Title generation:** ARQ worker (Haiku) auto-generates titles; backfill endpoint `POST /api/v1/admin/backfill-titles` targets `message_count >= 6 AND title IS NULL` → `{queued: N}`. Not yet run (not a cold-beta blocker).
- **ConversationCard title bug:** `apps/web/components/library/ConversationCard.tsx:49` renders `last_message_snippet ?? title`; title never shows when snippet exists. Fix in PR3a sweep.
- **OAuth scaffolding:** `auth_oauth_router` (partial implementation) exists in backend — relevant to deferred item #3.

**PR3a sweep plan:**

| Category | Items |
|---|---|
| Cold-beta blockers | PR3a memory bugs (fresh-chat missing message/thumbnail; home 404s); item A (Ask another mind chat stuck); item #2 (ConversationCard title) |
| Micro-polish | Item B (app icon: `apps/web/public/personas/appbutton.png`); item #5 (You-vs-You card icon); item #8 (Letter to Future Self: tap-the-card — NOTE: only functional ritual) |
| Content (needs founder copy) | Item #6: replace 30 "What's on your mind?" prompts with phenomenology themes (loneliness, social-media, doomscrolling, AI threats to work) |
| Deferred post-cold-beta | Item #3 (OAuth — scaffolding exists); item #4 (Council in Rituals); item #7 (intent/mode selection screen) |

**Pending (NOT done this session):**
- Backfill-titles not executed (data hygiene, not blocker).
- `nkoutr@ote.gr` `current_period_end = NULL` — needs manual re-sync.
- ~19 frontend pages lack hydration guard. Deferred.
- Block H live Stripe wiring: live keys + live price IDs + live-mode webhook (URL fix + live signing secret) + `ENVIRONMENT=production` on Render API.
- Cold beta date: to be locked.

**Brand:** "The Wise Room" is the locked product brand name. Rename audit PENDING — docs/code/Stripe may still say "Great Minds".

---

## Top of mind / Next (2026-06-03)

### Revenue gate is CLOSED in TEST. Next: PR3a cold-beta sweep, then live Stripe wiring, then cold beta.

**Priority order as of 2026-06-03:**

1. **PR3a cold-beta sweep — 🔴 not started (highest priority):**
   - Memory bugs: fresh-chat missing opening message/thumbnail; home "Continuing" / "Mind-of-the-Day" 404s
   - Item A: Today → Your reflections → "Ask another mind" → choose a mind: chat does not start / stuck
   - Item #2: `ConversationCard.tsx:49` title demoted to snippet fallback — fix required
   - Micro-polish: item B (app icon from `apps/web/public/personas/appbutton.png`), item #5 (You-vs-You card icon), item #8 (Letter to Future Self tap-to-card — NOTE: only functional ritual)
   - Content item #6: replace 30 "What's on your mind?" prompts with phenomenology themes — **needs founder-supplied copy first**

2. **Live Stripe wiring (TD-28) — 🔴 not started (P0 before any real payment):**
   - Live Stripe keys + live price IDs
   - A separate live-mode webhook registered in Stripe dashboard (same path `/api/v1/billing/webhook`, different signing secret)
   - `ENVIRONMENT=development` → `production` on Render API service

3. **OPS-001 — nkoutr@ote.gr current_period_end re-sync** — NULL pre-#205 row needs manual re-sync.

4. **Cold beta with 3–5 fresh users** — date to be locked.

5. **You vs You fast-follows** (post-first-paying-user, NOT before launch):
   - Funnel analytics: limit-hit → premium-nudge click tracking.
   - Rolling-both window anchor (v2, user-selectable).

6. **Council fast-follows** (post-first-paying-user, NOT before launch):
   - Per-verdict → reflections save: needs design (saved_lines is message-centric; council_responses are not messages).
   - Council share card redesign: boardroom bg, date header, 4 portrait thumbnails, centered synthesis.
   - Reflection share card redesign: center text, smaller/lower thumbnail.

7. **Rituals guided programs** — Counterview spec §1.3.2 ready; implementation not yet designed. Design with Claude (chat) before brief dispatch.

8. **Mirror fast-follows** (post-first-paying-user, NOT before): branded email postcard; host-aware handoff; smart input cap.

### Still-pending from prior sessions

- `.gitignore` security debt — **must fix before any code PR** (branch `chore/gitignore-env-local`)
- Author smoke-test voice changes — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu
- PR-D2 production smoke test — use gmail workaround
- OTP-01 (ote.gr delivery failure) — investigate Render logs
- compress mirror.png (2.3MB → WebP)
- OPS-001 — nkoutr@ote.gr subscription `current_period_end = NULL`; needs re-sync (pre-#205 row)

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

These must be addressed before the next PR brief is dispatched. Do NOT skip to feature work.

### 1. .gitignore security debt (CRITICAL — do first)

`.env.local` is **NOT** in `.gitignore`. Production secrets are one accidental `git add -A` away from being committed to the public GitHub repo.

**Action required:** Single dedicated commit before any other PR:
- Branch: `chore/gitignore-env-local`
- File changed: `.gitignore` only
- Patterns to add: `.env.local`, `.env*.local`

**Do this first. No other PR work until this is done.**

### 2. PR-D2 production smoke test PENDING

The NamePromptCard save flow has NOT been fully smoke tested in production. Blocked by OTP delivery failure to the founder's ote.gr address.

**Workaround:** Use a Gmail address for OTP testing.

### 3. OTP delivery failure for ote.gr (investigation pending)

OTP to nkoutr@ote.gr fails before DB insert. Render logs investigation pending.

### 4. Render env var protection (operational debt)

ANTHROPIC_API_KEY disappeared from both services between May 25-27. `render.yaml` needs `sync: false` on all secrets.

---

## Changelog v15 → v16

### The Council — C5 (#182, 87a9c32)

**Council screen scaffold + boardroom bg + rAF word-reveal + bench + synthesis card**

- `apps/web/app/app/council/page.tsx` — NEW: full council screen
- `apps/web/app/app/council/council.module.css` — NEW: `.word` keyframe
- Backend: `routers/council.py` + `services/council_service.py` + `db/migrations/versions/019_create_council.py` — NEW

### The Council — C6 (#183, 3149764)

**Polish: input framing, full bench + sequential light, veil 0.75, auto-scroll**

- `council/page.tsx` — `VEIL_OPACITY` 0.75; flex-nowrap bench; auto-scroll sentinel + pause-on-scroll; `scrollPendingRef` pattern

### The Council — C7a (#184, adc2592)

**Mirror session animation, council lit-name polish, stronger CTA border**

- `mirror/page.tsx` — `INTRO_HOLD` 1100→2100; CTA border 1.5px
- `council/page.tsx` — lit bench names `text-ink`; synthesis card label styling

### The Council — C7b (#185, 76340ef)

**Save synthesis: council_saves table, save/unsave endpoints, button wiring**

- `routers/council.py` — `POST+DELETE /council/{id}/save`
- `db/migrations/versions/020_create_council_saves.py` — NEW
- `lib/api.ts` — `saveCouncil`, `unsaveCouncil`
- `council/page.tsx` — `saved` state, `handleSave`, Bookmark button wired

### The Council — C7c (#186, c7d181f)

**Share synthesis: shared Pillow renderer, council share endpoint, modal generalization, intro/prominence tweaks**

- `services/image_service.py` — `_compose_canvas` → `_render_share_canvas` (shared core); `generate_council_share_image` added; reflections output byte-identical
- `routers/council.py` — `POST /council/{id}/share`; free-tier guard (shared `share_screenshot:{user.id}` counter)
- `lib/api.ts` — `shareCouncil`
- `components/share/SharePreviewModal.tsx` — `kind: 'line' | 'council'` discriminant; existing call sites unaffected
- `council/page.tsx` — `INTRO_HOLD` 1100→2100; bench name `font-medium text-[11px]`; verdict + synthesis body `font-medium`; Share button wired; `SharePreviewModal` mounted

---

## 1. Pre-Work Investigation Protocol

Unchanged from v12. Defined in `CLAUDE.md` at repo root. Mandatory for all multi-PR work. P-01 through P-06 apply to ALL sessions.

---

## 2. Current architecture

### Chat flow

PATH A SSE streaming endpoint. Real-time streaming added in PR-A (v13). Unchanged from v15.

### Council flow

`POST /council` → SSE stream → `council_service.stream_council` → 4-verdict loop → synthesis → `done` event (case_id + session_id). Client state machine: idle → intro → convening → session (bench + verdicts + synthesis) → allDone. Save via `POST /council/{id}/save`. Share via `POST /council/{id}/share` → PNG bytes.

### Subscription / tier resolution

Unchanged from v12. TD-11 (tier consolidation) remains pre-paid-launch requirement.

### Latency topology

Unchanged from v12. DATABASE_URL confirmed Oregon.

---

## 3. Test infrastructure

```
~292+ backend tests (v12 baseline; no new tests added in Council session)
~43+ frontend tests (v12 baseline)
```

No test changes in Council session.

---

## 4. Known limitations and not-yet-wired features

All v15 limitations apply. Additions and updates since v15:

### 4.16 Council per-verdict saves not wired (NEW v16)

Individual verdict saves require a `saved_lines` entry but `saved_lines` is message-centric (`message_id` FK required). Council verdicts live in `council_responses`, not `messages`. Wiring per-verdict saves needs an investigation brief to determine approach (extend `saved_lines` schema, create a parallel table, or something else).

### 4.18 ConversationCard title never renders (NEW 2026-06-03)

`apps/web/components/library/ConversationCard.tsx:49` evaluates `last_message_snippet ?? title`. Because virtually all conversations have a snippet, the title is never displayed — the snippet renders in its place. Fix: change to `title ?? last_message_snippet` or render title independently. **PR3a sweep item #2.**

### 4.19 nkoutr@ote.gr subscription current_period_end = NULL (NEW 2026-06-03)

The founder's ote.gr account created its subscription row before the #205 fix. `current_period_end` is NULL. Tier resolver will not return "pro" for this account until the row is re-synced via Stripe dashboard webhook re-send or admin endpoint.

### 4.17 Council share card is generic Pillow layout (NEW v16)

Current council share PNG uses the same centered text + footer layout as reflections, with `"— THE COUNCIL"` attribution and no portrait. The intended final design is: boardroom.webp background, date header, 4 member portrait thumbnails at top, centered synthesis text. This requires boardroom.webp + 4 member portrait files under `apps/api/static/personas/` (currently only available as Next.js public assets). Not a blocker for launch.

---

## 5. Next session entry point

**Priority order as of 2026-06-03:**

### Phase 0 — Operational cleanup (do before any code PR)

1. **Fix .gitignore** — add `.env.local`, `.env*.local`. Branch `chore/gitignore-env-local`. Single commit. Squash merge.
2. **Smoke test PR-D2** — sign in with gmail, verify NamePromptCard save flow end-to-end.
3. **Investigate OTP-01** — check Render logs for ote.gr delivery failure root cause.
4. **Author smoke-test voice changes** — test Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu in production.

### Phase 1 — Revenue gate [COMPLETE ✅]

- ~~TD-11~~ ✅ DONE (#203)
- ~~Disable BETA_GRANT_PRO_TO_ALL~~ ✅ DONE (both services)
- ~~End-to-end Stripe sandbox test~~ ✅ DONE (revenue chain verified)

### Phase 1b — PR3a cold-beta sweep [NEXT PRIORITY]

5. **Get founder copy for item #6** — 30 phenomenology prompts (loneliness, social-media relationships, doomscrolling, AI threats to work). Content must arrive from founder before sweep can complete.
6. **PR3a memory bugs** — fresh-chat missing opening message/thumbnail; home "Continuing" / "Mind-of-the-Day" 404s.
7. **PR3a item A** — "Ask another mind" chat doesn't start / stuck.
8. **PR3a item #2** — fix `ConversationCard.tsx:49` title demoted to snippet.
9. **PR3a micro-polish** — item B (app icon), item #5 (You-vs-You card icon), item #8 (Letter to Future Self tap-to-card entry).

### Phase 1c — Live Stripe wiring (before any real payment)

10. **TD-28 — Live Stripe wiring** — live keys + live price IDs + live-mode webhook (URL fix + live signing secret) + `ENVIRONMENT=production` on Render API.

### Phase 1d — OPS cleanup

11. **OPS-001 — nkoutr@ote.gr re-sync** — re-sync subscription row via Stripe dashboard or admin endpoint.

### Phase 2 — Council fast-follows (post-first-paying-user, NOT before)

8. **Per-verdict → reflections save** — investigation brief first (saved_lines is message-centric).
9. **Council share card redesign** — boardroom bg, date header, 4 portrait thumbnails, centered text. Needs static asset copies.
10. **Reflection share card redesign** — center text, smaller/lower thumbnail.
11. **compress mirror.png** — 2.3MB PNG → WebP.

### Phase 3 — Rituals guided programs [retention]

12. **Design session with Claude (chat)** — Counterview spec + guided program flows. Scope NOT YET DESIGNED. Do not dispatch a build brief until design is complete.
13. **Investigate `insights` table** — exists in live DB (0 rows); likely leverage point for progress payoff.

### Phase 4 — Mirror fast-follows (post-first-paying-user)

14. Branded email postcard — reuse Resend infra.
15. Host-aware handoff — reuse `CROSS_MIND_NOTE` pattern.
16. Smart input cap on Mirror generator.

### Phase 5 — Remaining Brief #1 queue

17. **PR-C** — Library F6 spec restoration (1-2 days)
18. **PR-G** — F2 verification + Sunday counter (2-4 days)
19. **PR-E** — Press further mode toggle (3-4 days)

### Phase 6 — Infrastructure hardening

20. **TD-24** — render.yaml `sync: false` for all secrets + startup health check + alerts

### Phase 7 — Launch track

21. Block B consolidated polish PR
22. Pre-launch items (lawyer review, DNS, GDPR/DPA, runbooks)
23. UAT (≥2/5 spontaneous "I'd pay")
24. Cold validation with external users (retention + willingness-to-pay)

---

## 6. PR history (v15 → v16)

| PR | Description | Date | Status |
|---|---|---|---|
| C5 #182 87a9c32 | Council: screen scaffold, boardroom bg, rAF reveal, bench, synthesis | 2026-06-01 | ✅ merged |
| C6 #183 3149764 | Council: input framing, full bench + sequential light, veil 0.75, auto-scroll | 2026-06-01 | ✅ merged |
| C7a #184 adc2592 | Council: Mirror animation (INTRO_HOLD 2100), lit-name polish, CTA border | 2026-06-01 | ✅ merged |
| C7b #185 76340ef | Council: save synthesis (council_saves, save/unsave endpoints, button) | 2026-06-01 | ✅ merged |
| C7c #186 c7d181f | Council: share synthesis (shared Pillow renderer, modal generalization, polish) | 2026-06-01 | ✅ merged |
| #190 46dac9e4 | polish(rituals): frameless Mirror reveal + center Council idle heading | 2026-06-02 | ✅ merged |
| #191 804af4ad | feat(brand): add WiseMark, place on Council synthesis | 2026-06-02 | ✅ merged |
| #192 4e5ceba1 | copy(rituals): sharpen ritual hub descriptors | 2026-06-02 | ✅ merged |
| YvY PR1 #193 e8a5c4de | feat(self-comparisons): add table and migration (021) | 2026-06-02 | ✅ merged |
| YvY PR2 #194 4d66f401 | feat(self-comparison): self-model read service and status endpoint | 2026-06-02 | ✅ merged |
| YvY PR3 #195 a5ce9ff1 | feat(you-vs-you): hub card and forming screen | 2026-06-02 | ✅ merged |
| YvY PR4 #196 cf813210 | feat(self-comparison): ask endpoint and dual generation | 2026-06-02 | ✅ merged |
| YvY PR5 #197 1001e6d8 | feat(self-comparison): app-voice closing, evidence quotes, ring-true | 2026-06-02 | ✅ merged |
| YvY PR6 #198 7d4390ca | feat(you-vs-you): input reveal | 2026-06-02 | ✅ merged |
| YvY PR6b #199 fd88625a | feat(you-vs-you): closing card with evidence and ring-true | 2026-06-02 | ✅ merged |
| YvY PR7 #200 54ebd4a3 | feat(you-vs-you): tier-aware weekly rate limit | 2026-06-02 | ✅ merged |
| YvY PR7.5 #201 5a859bbb | feat(you-vs-you): weekly usage meter and premium nudge | 2026-06-02 | ✅ merged |
| YvY bg #202 9ca95e65 | feat(you-vs-you): faded room background | 2026-06-02 | ✅ merged |

| #203 (TD-11) | feat(billing): canonical tier resolver — get_user_tier is single source | 2026-06-03 | ✅ merged |
| #204 | fix(auth): _hasHydrated guard — FAILED, superseded by #207 | 2026-06-03 | ❌ removed |
| #205 04709a80 | fix(billing): read current_period_end from subscription items | 2026-06-03 | ✅ merged |
| #206 c22c18d6 | fix(account): mounted state approach — FAILED, superseded by #207 | 2026-06-03 | ❌ removed |
| #207 dfbfd81d | fix(account): useHydrated() via Zustand onFinishHydration | 2026-06-03 | ✅ merged |

Earlier PR history (v12–v15): see `HANDOFF_BRIEF_v15.md §6`.

---

## 7. Environmental configuration

### Backend (Render)

Unchanged from v15. No new env vars required for Council. See v15 §7 for full list.

### Frontend (Netlify)

Unchanged from v15.

---

## 8. Key file paths (production codebase)

### Backend (apps/api/)

All v15 paths apply. Additions since v15:

- `routers/council.py` — NEW: POST /council, POST+DELETE /council/{id}/save, POST /council/{id}/share; `CouncilShareRequest`, `CouncilShareRequest` models; rate-limit guard
- `services/council_service.py` — NEW: `CouncilService.stream_council` (SSE generator); `weekly_remaining`
- `services/image_service.py` — REFACTORED: `_render_share_canvas` shared core; `generate_council_share_image`
- `db/migrations/versions/019_create_council.py` — NEW
- `db/migrations/versions/020_create_council_saves.py` — NEW
- `routers/self_comparison.py` — NEW: GET /self-comparison/status, POST /self-comparison (SSE), PATCH /self-comparison/{id}/ring-true
- `services/self_model_service.py` — NEW: `SelfModelService.build` (pure read; then/now window split from memory_entries; unlock gates)
- `services/self_comparison_service.py` — NEW: `SelfComparisonService.stream` (SSE dual-gen + closing + evidence); `weekly_remaining`
- `services/self_comparison_prompts.py` — NEW: `SELF_SYSTEM_PROMPT`, `CLOSING_PROMPT`
- `db/migrations/versions/021_create_self_comparisons.py` — NEW

### Frontend (apps/web/)

All v15 paths apply. Additions and changes since v15:

- `app/app/council/page.tsx` — NEW: full council screen
- `app/app/council/council.module.css` — NEW: `.word` keyframe
- `app/app/mirror/page.tsx` — UPDATED: `INTRO_HOLD` 1100→2100; CTA border; frameless reveal (#190)
- `components/share/SharePreviewModal.tsx` — UPDATED: `kind` discriminant; council preview
- `components/ui/WiseMark.tsx` — NEW: WiseMark icon component (#191)
- `app/app/you-vs-you/page.tsx` — NEW: full You vs You screen (forming/locked guard → input → dual-self reveal → closing card + ring-true + usage meter)
- `lib/api.ts` — UPDATED: `streamCouncil`, `saveCouncil`, `unsaveCouncil`, `shareCouncil`; council SSE event types; `getSelfComparisonStatus`, `streamSelfComparison`, `setSelfComparisonRingTrue`; `SelfComparisonStatus` type

---

## 9. Decision history (v16 additions)

### 2026-06-01 — Council roster and Pro-gate locked

The Council is Pro-only and permanently fixed at 4 members (Machiavelli, Epictetus, Freud, de Beauvoir). The BETA flag makes everyone Pro during cold beta. Roster is a `ROSTER` const in `council/page.tsx`; expanding requires const + prompt change, no schema change.

### 2026-06-01 — Shared share counter by design

Line shares and Council shares share the `share_screenshot:{user.id}` Redis counter. Free-tier users get 3 shares total (both types combined) per 90-day rolling window. If the product needs separate limits later, it's a key-name change only.

### 2026-06-01 — image_service.py refactored for reuse

`_compose_canvas` extracted to `_render_share_canvas` with keyword-only params. This is the canonical approach for any future share card variant. The reflections path is byte-identical; the council path passes `portrait_path=None`, `intro_text=None`, `attribution="— THE COUNCIL"`.

### 2026-06-02 — You vs You design stance locked (mirror-not-oracle)

You vs You observes and asks — it never asserts. No numeric scores, no clinical labels, no verdicts. The two selves reflect back the user's own words; the closing asks a question rather than concluding. User is always the judge. Encoded in `SELF_SYSTEM_PROMPT` and `CLOSING_PROMPT` in `self_comparison_prompts.py`.

### 2026-06-02 — You vs You weekly limits are tier-aware (not unlimited)

pro=5/week, premium=30/week. Premium is capped (not unlimited) as a cost-safety measure. Constants in `self_comparison_service.py`: `WEEKLY_LIMIT_BY_TIER = {"pro": 5, "premium": 30}`. Admins bypass for testing.

### 2026-06-02 — Self-model windows: then = earliest 12 signals, now = latest 12 signals

The "then" and "now" windows are fixed slices of the user's active `memory_entries` ordered by `created_at`. Unlock gate: ≥20 total active signals AND ≥14 day span between oldest and newest. This is not user-configurable in v1. Rolling-both window anchor (user-selectable) is deferred to v2.

### 2026-06-03 — TD-11 tier resolution architecture locked

`get_user_tier` in `services/tier_service.py` is the canonical tier resolution function. `get_current_user_plan` in `auth.py` is a thin wrapper — it calls `get_user_tier` and returns its result. All enforcement points should prefer `get_current_user_plan` (the FastAPI dependency) for new endpoints, understanding it now delegates to `get_user_tier`. `rate_limit_service` enforces `plan in ("pro","premium")` directly. The previous semantic divergence between the two functions (premium handling, expiry validation) is resolved.

### 2026-06-03 — Account auth hydration approach locked

`useHydrated()` is the canonical pattern for guarding auth redirects in account-related pages. Implemented via Zustand `onFinishHydration` / `hasHydrated` / `rehydrate`. The simpler `mounted` + `useEffect` approach was tried twice (#204, #206) and failed in production Next.js builds due to timing differences. Do not revert to the `mounted` pattern.

### All prior decisions from v15 §9

Unchanged.

---

## 10. Section 5.7 framework — status

Unchanged from v12. All 9 personas have full character config.

**Council synthesis** uses the app voice ("The Wise Room"), not any individual persona voice. It is not Section 5.7 governed in the same way as persona chat.

---

## 11. Migration plan — status

All phases through Block C complete. Oregon complete. alembic_version = `021_create_self_comparisons`.

---

## 12. Deployment readiness

```
✅ Backend                Render web service philosopher-api
                          philosopher-api-z9l9.onrender.com
                          ✅ Paid Starter tier — no cold-start
                          ✅ ANTHROPIC_API_KEY confirmed (re-added 2026-05-27/28)

✅ Worker                 Render worker philosopher-worker
                          ✅ Paid Starter tier — no cold-start
                          ✅ Upstash Pay-as-You-Go

✅ Database               alembic_version = '021_create_self_comparisons'
                          Oregon data migration confirmed.
                          DATABASE_URL pointing to Oregon bvzeuwzqgnqcghvqghtb.

🟡 Redis (Upstash)        ✅ Pay-as-You-Go ($0.2/100k commands)
                          ⚠️ 80% quota alert not yet set up

🟡 Email                  Resend free tier (test sender)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS
                          ⚠️ OTP delivery failing to ote.gr (investigation pending)

✅ Frontend (canonical)   Netlify thinkalike.netlify.app

✅ LLM                    Anthropic API wired — chat + Council synthesis live

✅ Stripe                 Sandbox: end-to-end verified (2026-06-03). Revenue chain CLOSED in TEST.
                          ⚠️ LIVE wiring pending: live keys + live price IDs + live-mode webhook + ENVIRONMENT=production

🟡 Google OAuth           Dormant (GOOGLE_OAUTH_ENABLED=false).

🟡 Rituals email delivery Letter DB schema live; ARQ delivery not wired.
```

---

## 13. Session lessons (v16 additions)

### 13.1–13.17 Preserved from v15

See v15 §13 for full text. Key rules: P-01 through P-06 in CLAUDE.md.

### 13.18 Council synthesis `quote` prop at `allDone=true` is complete (NEW v16)

`phase.synthesisWords.join(' ')` at `allDone=true` yields the full synthesis text because the rAF loop only sets `allDone=true` after all synthesis words are revealed. This is safe to pass as the `quote` prop to `SharePreviewModal` without a separate state variable.

### 13.19 `SharePreviewModal` kind discriminant preserves existing call sites (NEW v16)

All existing `kind='line'` call sites pass NO `kind` prop. TypeScript default `kind = 'line'` ensures zero behaviour change. Any new council use must explicitly pass `kind='council'`. This pattern is the right one for future share variants.

### 13.20 rate-limit key sharing is a product decision, not a bug (NEW v16)

The decision to share `share_screenshot:{user.id}` between line shares and council shares is intentional. Free users get 3 total shares per 90-day window. Document this in every share endpoint so future engineers don't "fix" it accidentally.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v12. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. P-01 through P-06 apply to ALL sessions.

### The most important context for the next session

**Five things in order:**

1. **Fix .gitignore first.** Production secrets are one `git add -A` away from the public repo. This is the highest-priority item — above all feature work.

2. **Revenue chain is CLOSED in TEST/sandbox.** TD-11 done, BETA off, Stripe verified. The next gate is live Stripe wiring (TD-28) — different from sandbox: live keys, live price IDs, a *separate* live-mode webhook with its own signing secret, and `ENVIRONMENT=production` on Render.

3. **PR3a sweep needs founder copy for item #6 before it can ship.** Items B, #5, #8, memory bugs, item A, and item #2 (ConversationCard title) can proceed without founder input. Item #6 (phenomenology prompts) is blocked on founder-supplied copy.

4. **Brand name is "The Wise Room" (locked).** A rename audit is pending across docs, code, and Stripe product names. Do not rename anything until the audit is complete and the founder approves.

5. **ConversationCard.tsx:49 is the root cause of item #2.** `last_message_snippet ?? title` means the title never renders when a snippet exists. Fix: invert the fallback or render title independently. Backend already generates and stores titles correctly via the ARQ Haiku worker.

### Documentation hygiene

v16 rotation triggered by The Council shipping end-to-end (5 PRs, 2 migrations, major new feature complete). Next baseline regen threshold: revenue gate shipped OR major new feature block complete. Until then, append `*_v16_ADDENDUM_<date>.md` instead of rewriting v16.

### Launch timeline from here

Realistic from end of 2026-06-03 session: 3-6 weeks.
- Revenue gate: ✅ CLOSED (TEST). Live Stripe wiring (TD-28): ~1 week (env vars + dashboard config, no code changes).
- PR3a cold-beta sweep: ~1-2 weeks.
- Counterview design + build: ~2-3 weeks.
- Cold beta + DNS cutover: 1-2 weeks.
- **Target: mid-July 2026.**

---

**End of HANDOFF_BRIEF v16.** Authoritative as of 2026-06-03 (revenue chain + PR3a triage appended). Supersedes `HANDOFF_BRIEF_v15.md` (preserved as historical reference). Where this file conflicts with v15, v16 wins.
