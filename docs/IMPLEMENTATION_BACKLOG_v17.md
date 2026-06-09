# THE WISE ROOM — Implementation Backlog v17

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v17 = v16 baseline (2026-06-03) + 2026-06-03 session delta (PR #210: 3 bug fixes; rituals micro-polish: half-sphere YvY SVG, Letter whole-card tap; app icon deferred; daily_questions: 50 phenomenology themes active, old 30 deactivated; backfill-titles executed queued=0; OTP lockout root cause documented; Pro test account created).**
>
> **Generated:** 2026-06-03 (v17 rotation) · **Last updated:** 2026-06-09 (TD-30, TD-31 added)
>
> **How to read this file:**
> - This v17 file supersedes v16 and all prior backlog files.
> - Where v17 conflicts with v16, v17 wins.
>
> **Companion documents:**
> - `PROJECT_STATE_v17.md` — current project state
> - `HANDOFF_BRIEF_v17.md` — continuity and implementation history
> - `SCREENS_TRACKING_v5.md` — full screen inventory
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

## 2026-06-03 Consolidation Summary — PR3a micro-polish + daily_questions

> Appended as v17. Where this conflicts with v16 or prior sections, this section wins.

**Code shipped (merged to main):**

- **PR #210 (`eda60f21`) — three production bug fixes:**
  - `ConversationCard.tsx`: `title ?? last_message_snippet` (was snippet-first). BUG-013 + PR3a item #2 closed.
  - `today/page.tsx`: first-day Reflect opens PersonaPickerSheet; opening message skipped only when topic exists.
  - `PersonaPickerSheet.tsx`: `onClose()` before async create. PR3a item A (chat stuck) closed.
- **Rituals micro-polish:** `rituals/page.tsx` — half-sphere inline SVG for YvY card (item #5 closed); Letter card whole-card `<button>` (item #8 closed). `Contrast` + `ChevronRight` removed from imports.
- **App icon:** photo icon (`appbutton.png`, 1122×1402 px, ~2.1 MB) tried as `icon.png`/`apple-icon.png`, landed on main accidentally, removed via hotfix. **Item B DEFERRED.** Icon mark design required before next attempt.

**Database (data changes, no migrations):**
- `daily_questions`: 50 modern-phenomenology themes inserted (display_order 1000–1049, active=true); old 30 deactivated (active=false, reversible). Item #6 closed.
- `backfill-titles` executed: `{queued: 0}`. No title debt. Done.

**Operational facts recorded:**
- Oregon DB confirmed canonical: `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland deprecated; deletion ~2026-06-09.
- Pro test account `nckoutras+pro1@gmail.com` granted via `UPDATE subscriptions`.
- OTP lockout root cause: Upstash Redis `otp_request:{email}` 5/hour. Workaround: `+alias` email.

**PR3a sweep status after this session:**

| Item | Status |
|---|---|
| Memory bugs (fresh-chat thumbnail; home Continuing 404s) | 🔴 still pending |
| Item A — Ask another mind chat stuck | 🟢 CLOSED (PR #210) |
| Item #2 — ConversationCard title | 🟢 CLOSED (PR #210) |
| Item B — app icon | ⏸ DEFERRED (icon mark TBD) |
| Item #5 — YvY ritual card icon | 🟢 CLOSED (half-sphere SVG) |
| Item #6 — phenomenology prompts | 🟢 CLOSED (daily_questions updated) |
| Item #8 — Letter card whole-card tap | 🟢 CLOSED (whole-card button) |

**Still-deferred (no action this session):**
- App-icon mark (design required)
- Item #3: Google/Apple OAuth (backend scaffolding exists; post-cold-beta)
- Item #4: Surface The Council in Rituals (post-cold-beta)
- Item #7: Intent/mode selection screen (post-cold-beta)
- Block H live Stripe wiring (TD-28; env vars + dashboard config when ready)

**Status:** PR3a largely complete. Remaining cold-beta blocker: memory bugs. Next: fix memory bugs → cold beta.

---

## v16 Consolidation Summaries (2026-06-01 through 2026-06-03)

See `IMPLEMENTATION_BACKLOG_v16.md` for full v16 detail: Council (PRs #182–#186), You vs You (PRs #193–#202), Revenue chain + TD-11 + original PR3a triage.

---

## v15 Consolidation Summary (2026-06-01)

The Mirror shipped (PRs #166–#173). See `IMPLEMENTATION_BACKLOG_v15.md §v15 Consolidation Summary` for full detail.

---

## v14 Addendum — Voice Overhaul (2026-05-30)

All 9 personas voice-tightened; check_brevity live; Socrates elenchus upgraded. See v15 §v14 Addendum for full detail.

---

## 1. Current Launch Interpretation

**Plan A (active).** Current priority order as of 2026-06-03 (v17):

1–10. ~~Prior items through 2026-05-26~~ — DONE (see v12 §1)
11. ~~**Bug #1 — BottomSheet race**~~ DONE (#127, 2026-05-28)
12. ~~**Bug #4 / PR-A — Real-time streaming**~~ DONE (#128, 2026-05-28)
13. ~~**PR-D — Greeting personalization**~~ DONE (#129, 2026-05-28)
14. ~~**PR-D2 — Name capture prompt**~~ DONE (#130, 2026-05-28)
15. **Fix .gitignore security debt** — `.env.local` not protected. Must be done before any further PR work.
16. **PR-D2 production smoke test** (blocked by OTP issue; use gmail workaround)
17. ~~**Voice overhaul**~~ ✅ DONE (2026-05-30)
18. **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu (live, pending author test)
19. ~~**The Mirror**~~ ✅ DONE (2026-06-01) — PRs #166–#173
20. ~~**The Council**~~ ✅ DONE (2026-06-01) — PRs #182–#186
20.5. ~~**You vs You**~~ ✅ DONE (2026-06-02) — PRs #193–#202
21. ~~**TD-11 — Tier resolution refactor**~~ ✅ DONE (#203, 2026-06-03)
22. ~~**Disable BETA_GRANT_PRO_TO_ALL**~~ ✅ DONE (2026-06-03)
23. ~~**End-to-end Stripe sandbox test**~~ ✅ DONE (2026-06-03)
23.5. ~~**PR3a item A — Ask another mind chat stuck**~~ ✅ DONE (PR #210, 2026-06-03)
23.6. ~~**PR3a item #2 — ConversationCard title**~~ ✅ DONE (PR #210, 2026-06-03)
23.7. ~~**Today first-day Reflect hardcodes Marcus**~~ ✅ DONE (PR #210, 2026-06-03)
23.8. ~~**PR3a item #5 — YvY ritual card icon**~~ ✅ DONE (half-sphere SVG, 2026-06-03)
23.9. ~~**PR3a item #8 — Letter card whole-card tap**~~ ✅ DONE (2026-06-03)
23.10. ~~**PR3a item #6 — phenomenology prompts**~~ ✅ DONE (daily_questions updated, 2026-06-03)
23.11. ~~**backfill-titles executed**~~ ✅ DONE (queued=0, 2026-06-03)
23.12. **PR3a memory bugs** — 🔴 not started. Fresh-chat missing opening message/thumbnail; home "Continuing" 404s.
23.13. **PR3a item B — app-icon mark** — ⏸ DEFERRED. Photo icon removed. Icon mark design TBD.
24. **source_chunks re-ingest** into Oregon (TD-22; status unconfirmed post-switch)
25. **Post-Oregon smoke test** — login, chat, Mirror, Council, share, library, RAG retrieval
26. **Mobile 12-point nav smoke test**
27. **Cold beta with 3–5 fresh users**
28. **Cold validation with external users** (retention + willingness-to-pay)
29. **Rituals guided programs** — Counterview + guided programs; scope NOT YET DESIGNED; design session first
30. **Per-verdict → reflections save** — investigation brief first
31. **Council share card redesign** — boardroom bg + 4 thumbnails + date header
32. **Reflection share card redesign** — center text, smaller thumbnail
33. **PR-C — Library F6 spec restoration** (1-2 days)
34. ~~**PR-F — Typography V1**~~ ✅ DONE (2026-05-29)
35. **PR-G — F2 verification + Sunday counter**
36. **PR-E — Press further mode toggle**
37. ~~**PR-B — C9 Bring another mind end-to-end**~~ ✅ DONE (2026-05-29)
38. **Block B consolidated polish PR**
39. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)
40. **UAT** (≥2/5 spontaneous "I'd pay")
41. **Public launch**

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt** — add `.env.local` and `.env*.local` to `.gitignore`. Single-file commit. Branch: `chore/gitignore-env-local`. MUST be done before any other PR.
- [ ] **PR-D2 production smoke test** — verify NamePromptCard save flow end-to-end. Use gmail for OTP delivery.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu (live since 2026-05-30, author-testing pending)

### 2.1 Infrastructure P0

- [x] ~~**Oregon migration completion**~~ — DATABASE_URL confirmed pointing to Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2)
- [ ] **source_chunks re-ingest** into Oregon project via OpenAI embeddings script (TD-22); status unconfirmed post-switch
- [x] ~~**Render DATABASE_URL switch**~~ — CONFIRMED DONE (Oregon live)
- [ ] **Post-Oregon smoke test** (login, chat, Mirror, Council, rituals, share, library, RAG retrieval)
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**

### 2.2 Code-side P0

- [x] ~~**End-to-end Stripe sandbox test**~~ — DONE (2026-06-03)
- [ ] **PR3a memory bugs** — fresh-chat missing opening message/thumbnail; home "Continuing" 404s. All other PR3a items closed.
- [ ] **bugfixes-3 — auth race fix** (P0; see TD-10; PR4ai deferred)
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari)
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure)

### 2.3 Legal P0

- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**

### 2.4 Infrastructure P0 (continued)

- [ ] **DNS + Resend domain verification** for `thegreatminds.app`

### 2.5 UAT P0

- [ ] **UAT** with 3–5 mixed testers (≥2/5 spontaneous "I'd pay")

---

## 3. Tech debt items

### TD-01 through TD-09

Unchanged from v12. See v11 §3 for full text.

### TD-10 — Zustand hydration race condition (P1, preview smoke test mandatory)

Unchanged from v12. PR4ai deferred.

### TD-11 — Tier resolution unified refactor (🟢 DONE — #203, 2026-06-03)

`get_user_tier` (`services/tier_service.py`) is the single source of truth. `get_current_user_plan` (`auth.py`) is a thin wrapper. Resolved.

### TD-12 through TD-15

Unchanged from v12.

### TD-17 — Weekly Reading full implementation (post cold-beta)

Scope locked (§9.7). Not before cold-beta validation.

### TD-18 through TD-21

Unchanged from v12.

### TD-22 — source_chunks re-ingest post-Oregon migration (P0 operational)

After DATABASE_URL switch confirmed, re-ingest 2476 × 1536-dim vectors. Not a code change — operational step.

### TD-23 — .gitignore security debt (P0 operational)

`.env.local` NOT in `.gitignore`. Fix before any further PR work.

### TD-24 — render.yaml sync:false for all secrets (P1 operational)

Add `sync: false` to all secrets in render.yaml + startup health check + Upstash quota alert.

### TD-25 — compress mirror.png (P1)

`apps/api/static/personas/mirror.png` or equivalent ~2.3MB. Convert to WebP.

### TD-26 — Council share card full design (P1)

Current council share PNG is a functional placeholder. Full design: boardroom.webp background, date header, 4 member portrait thumbnails, centered synthesis text.

### TD-27 — Per-verdict → reflections save (investigation required, P1)

`saved_lines` requires `message_id` FK. Council verdicts live in `council_responses`, not `messages`. Investigation brief required before build.

### TD-28 — Live Stripe wiring (P0 before any live payment)

Sandbox complete. Live wiring: live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` on Render API.

### TD-29 — App-icon mark design (P1, deferred from PR3a)

Photo icon (`appbutton.png`) tried and removed. A purpose-built icon mark is required. Design TBD. Next attempt: wire `apps/web/app/icon.png` and `apps/web/app/apple-icon.png` once mark is ready.

### TD-30 — `zoom: 1.15` / `100svh/1.15` compensation coupled across three sites (P4)

`apps/web/app/globals.css` sets `body { zoom: 1.15 }`. CSS `zoom` magnifies `position: fixed` descendants and their viewport-unit sizing, so any full-viewport or bottom-anchored fixed overlay must divide its height by 1.15 or it renders ~15% below the visible viewport (bottom content / submit buttons cut off). Three sites now carry this divisor:

1. `app/app/(tabs)/layout.tsx` — tabs shell `h-[calc(100svh/1.15)]`
2. `components/ui/BottomSheet.tsx` — container `h-[calc(100svh/1.15)]` + `maxHeight: calc(<prop> / 1.15)` (#263, 2026-06-09)
3. `app/app/mirror/page.tsx` — "Whose eyes?" host picker container `h-[calc(100svh/1.15)]` (2026-06-09)

These are coupled: when `zoom: 1.15` is eventually removed (durable fix = drop the global zoom hack and size the app shell responsively), **all three `/1.15` divisors and BottomSheet's `maxHeight` calc must be removed together**, or those overlays become 15% too short. Until then, any new full-viewport/bottom-anchored fixed overlay must apply the same `/1.15` compensation.

### TD-31 — Cache You-vs-You "taking shape" forming reflection (P2)

`self_comparison_service.forming_reflection()` synthesizes the warm second-person reflection on **every forming-state `/status` load** (one `llm_client.complete` call + latency each time the locked You-vs-You screen opens). Introduced 2026-06-09 with the block-scoped synthesis (`feat/yvy-forming-reflection`). The recent signals only change when new `MemoryEntry` rows are added, so the reflection is recomputed needlessly on repeat views.

Optimization: cache the synthesized reflection and regenerate only when new signals arrive — e.g. key the cache on user_id + latest signal `created_at` (or count of the last-N signals), or persist it on a column and invalidate when memory extraction writes new entries. Removes the per-view LLM call/latency. Not a correctness issue; defer until after the wording is validated live.

---

## 4. Database schemas

See `PROJECT_STATE_v17.md §4`. Migration head: `021_create_self_comparisons`. No new migrations in v17 session.

`daily_questions` data state: 50 active (phenomenology themes, display_order 1000–1049); 30 inactive (original philosophical prompts, reversible).

---

## 5. Config & Environment Variables

See `HANDOFF_BRIEF_v17.md §7` for full env var list. No new env vars added in v17 session.

---

## 6. Stripe Wiring (sandbox complete — PR1 #77)

Status: 🟢 **Sandbox complete; end-to-end verified (2026-06-03).** Unchanged from v16.

---

## 7. Persona-specific maintenance backlog

Unchanged from v12.

---

## 8. LLM eval (optional)

Status: ⏸ P3. Unchanged from v12.

---

## 9. Future blocks reference

### 9.1 Block C — complete

Unchanged from v12.

### 9.2 Block D — D1 + D2 complete

**PR-D (#129):** D1 greeting personalizes with first name.
**PR-D2 (#130):** D1 conditionally shows NamePromptCard for OTP users without a name.

### 9.3 Block F — Reflection

F1 ✅. F2 lite ✅. F3/F4 ✅ spec (Weekly Reading). F6 ✅ (title bug fixed PR #210). F5 ⏸ v2.

### 9.4 Block H — Subscription & Billing

Unchanged from v12.

### 9.5 Block I — Account & Settings

I1 Account hub not yet built. Spec locked. P1.

### 9.6 Block J — Empty/error states

Unchanged from v12.

### 9.7 Rituals (updated v17)

**Rituals launch scope — Option B (locked 2026-05-28):**

| Ritual | Status | Notes |
|---|---|---|
| Letter to Future Self | 🟡 UI live, ARQ delivery not wired | Whole-card tap shipped (v17). Remove account card until wired (PR4af done). |
| The Mirror | 🟢 **SHIPPED** (2026-06-01, PRs #166–#173) | Generator + idempotent cron + host picker + ring-true live. MIRROR_PROMPT locked. |
| The Council | 🟢 **SHIPPED** (2026-06-01, PRs #182–#186) | 4 members. Verdicts + synthesis SSE. Save/unsave. Share PNG. |
| You vs You | 🟢 **SHIPPED** (2026-06-02, PRs #193–#202) | Pro-gated SSE. Half-sphere SVG icon on hub card (v17). Dual-self reveal. Weekly limits. |
| The Counterview | 🔴 NOT DESIGNED | Spec §1.3.2 locked (Option B); implementation not designed. Design session first. |
| Weekly Reading placeholder | 🔴 pending | "Coming this season" locked card in Rituals tile. |

**Content (v17):** `daily_questions` "What's on your mind?" prompts updated to 50 modern-phenomenology themes (display_order 1000–1049, active=true). Old 30 deactivated (reversible).

### 9.8 You vs You fast-follows (post-first-paying-user)

Unchanged from v16. See `IMPLEMENTATION_BACKLOG_v16.md §9.8`.

### 9.9 Council fast-follows (post-first-paying-user)

Unchanged from v16. See `IMPLEMENTATION_BACKLOG_v16.md §9.9`.

### 9.10 Mirror fast-follows (post-first-paying-user)

Unchanged from v16. See `IMPLEMENTATION_BACKLOG_v16.md §9.10`.

### 9.11 Counterview — spec §1.3.2 exists; implementation NOT DESIGNED

Unchanged from v16. Do not dispatch a build brief until a design session is complete.

---

## 10. Operating principles (preserved + extended)

### 10.1–10.27 — Preserved from v16

Full text in prior backlog files. Key rules: P-01 through P-06 in CLAUDE.md.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt** (TD-23) — add `.env.local`, `.env*.local` to `.gitignore`. Single commit.
- [ ] **PR-D2 production smoke test** — verify name save flow with gmail workaround
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu
- [ ] **PR3a memory bugs** — fresh-chat missing opening message/thumbnail; home "Continuing" 404s. (All other PR3a items closed.)

### 11.1 P0 (launch blockers)

- [x] ~~Prior P0 items through 2026-05-28~~ — DONE
- [x] ~~**Voice overhaul**~~ DONE (2026-05-30)
- [x] ~~**The Mirror**~~ ✅ DONE (2026-06-01)
- [x] ~~**The Council**~~ ✅ DONE (2026-06-01)
- [x] ~~**You vs You**~~ ✅ DONE (2026-06-02)
- [x] ~~**TD-11 — Tier resolution refactor**~~ ✅ DONE (#203, 2026-06-03)
- [x] ~~**Disable BETA_GRANT_PRO_TO_ALL**~~ ✅ DONE (2026-06-03)
- [x] ~~**End-to-end Stripe sandbox test**~~ ✅ DONE (2026-06-03)
- [x] ~~**PR3a item A — Ask another mind chat stuck**~~ ✅ DONE (PR #210, 2026-06-03)
- [x] ~~**PR3a item #2 / BUG-013 — ConversationCard title**~~ ✅ DONE (PR #210, 2026-06-03)
- [x] ~~**PR3a item #5 — YvY ritual card icon**~~ ✅ DONE (half-sphere SVG, 2026-06-03)
- [x] ~~**PR3a item #6 — phenomenology prompts**~~ ✅ DONE (daily_questions updated, 2026-06-03)
- [x] ~~**PR3a item #8 — Letter card whole-card tap**~~ ✅ DONE (2026-06-03)
- [x] ~~**backfill-titles executed**~~ ✅ DONE (queued=0, 2026-06-03)
- [ ] **🔴 PR3a memory bugs** — fresh-chat missing opening message/thumbnail; home "Continuing" 404s
- [x] ~~**Oregon region migration completion**~~ — DATABASE_URL confirmed pointing to Oregon
- [ ] **source_chunks re-ingest** into Oregon (TD-22)
- [ ] **Post-Oregon smoke test**
- [ ] **bugfixes-3 — auth race fix** (TD-10)
- [ ] **Mobile 12-point nav smoke test**
- [ ] **TD-28 — Live Stripe wiring** — live keys + live price IDs + live-mode webhook + `ENVIRONMENT=production`
- [ ] **OPS-001 — nkoutr@ote.gr current_period_end re-sync**
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Cold validation with external users**
- [ ] **Consolidated polish PR** (Block B visual closure)
- [ ] **Lawyer review** of Terms / Privacy / Disclaimer
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**
- [ ] **RLS policies** as defense-in-depth
- [ ] **UAT** with 3–5 testers, ≥2/5 spontaneous "I'd pay"

### 11.2 P1 (post-revenue, shortly after first paying user)

- [ ] **OPS-001 — nkoutr@ote.gr current_period_end re-sync**
- [ ] **TD-29 — App-icon mark design** — purpose-built icon mark required before wiring `icon.png`/`apple-icon.png`
- [ ] **Per-verdict → reflections save** (TD-27) — investigation brief first
- [ ] **Council share card redesign** (TD-26)
- [ ] **Reflection share card redesign**
- [ ] **compress mirror.png** (TD-25)
- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to Future Self — ARQ email delivery wiring**
- [ ] **OTP-01 investigation** — Render logs for ote.gr delivery failure
- [ ] **TD-24 — render.yaml sync:false** for all secrets + startup health check + Upstash quota alert
- [ ] **Mirror v2 — branded email postcard**
- [ ] **Host-aware handoff** — reuse `CROSS_MIND_NOTE` pattern
- [ ] **Smart input cap on Mirror generator**

### Next brief sequence (P1-P2 feature work)

**Priority: PR3a memory bugs → cold beta → live Stripe wiring**

**Then Council fast-follows (investigation first):**
0. **Investigation brief: per-verdict saves** — map `council_responses` → `saved_lines` schema gap.

**Then remaining Brief #1 queue:**
1. **PR-C — Library F6 spec restoration** (1-2 days)
2. **PR-G — F2 verification + Sunday counter** (2-4 days)
3. **PR-E — Press further mode toggle** (3-4 days)

**Then Rituals:**
4. **Design session with Claude (chat)** — Counterview spec + guided program flows.

### Deferred — post-cold-beta

- [ ] **PR3a item #3 — Google/Apple OAuth** (backend scaffolding `auth_oauth_router` exists)
- [ ] **PR3a item #4 — Surface The Council in Rituals** (currently accessible only via Mirror)
- [ ] **PR3a item #7 — Intent/mode selection screen** (grief/anxiety/free-text + challenge/comfort → persona routing)
- [ ] **Doc-2 relationship track** (deferred per 2026-06-03 session)
- [ ] **Block H live Stripe wiring** (TD-28; after cold beta validated)

### Secondary briefs (parallel-track candidates)

- Brief #3 — About copy integration (depends on branding resolution)
- Brief: Council share card redesign (depends on static asset availability)

### 11.3 P2 (tech debt)

- [x] ~~**TD-11**~~ — DONE (#203, 2026-06-03)
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-01** — Split `rate_limit_service.py`
- [ ] **TD-02** — PersonaConfig / Persona ORM naming confusion
- [ ] **TD-03** — Update or remove `ANTHROPIC_MODEL` constant
- [ ] **TD-08** — Document Render alembic auto-run mechanism
- [ ] **ChatGPT audit** of new persona configs
- [ ] **Portrait style harmonization**
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML**
- [ ] **Premium tier reassignment** (Freud → premium if desired)
- [ ] **branding resolution** — "The Wise Room" vs "Great Minds" in FROM_EMAIL, FRONTEND_URL, copy strings
- [ ] **C9 real implementation** (post-revenue) — Another-mind feature gate
- [ ] **F2 Suggested insights (lite)** (post-revenue)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-20** — safety_events.message_id FK ondelete
- [ ] **TD-21** — passive_deletes audit
- [ ] **TD-31 — Cache You-vs-You forming reflection** — `forming_reflection()` runs an LLM call on every forming-state `/status` load; cache + invalidate on new signals (introduced `feat/yvy-forming-reflection`, 2026-06-09)

### 11.4 P3

- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **Desktop layout polish**
- [ ] **Phase 5 Council Premium mechanics + Heraclitus secret host** (post-launch, post-feedback)
- [ ] **Phase 6 eval suite + CI**
- [ ] **LLM eval test** for Lao Tzu
- [ ] **You vs You funnel analytics** (deferred from YvY session)
- [ ] **Rolling-both window anchor (v2)** (deferred from YvY session)

### 11.5 P4

- [ ] **TD-04** — Backoff discrepancy
- [ ] **TD-06** — `safety_events.message_id` always NULL
- [ ] **TD-07** — gh CLI install on founder's Windows
- [ ] **TD-14** — BASE_URL legacy cleanup in config.py
- [ ] **TD-30 — `zoom:1.15` / `100svh/1.15` coupling** across tabs shell, BottomSheet (#263), Mirror picker; remove all divisors + BottomSheet maxHeight calc together when the global zoom hack is dropped
- [ ] **openapi.json → .gitignore**
- [ ] **Legal pages `target="_blank"` rel hardening**
- [ ] **Stale branch cleanup**

---

## 12. Plan A vs Plan B (preserved)

Unchanged from v12. Plan A active.

Realistic timeline from end of 2026-06-03 v17 session: 3-5 weeks total.
- PR3a memory bugs: ~1 week
- Cold beta + DNS cutover: 1-2 weeks
- Counterview design + build: ~2-3 weeks
- Live Stripe wiring: ~1 week (env vars + dashboard, no code)
- **Target: mid-July 2026.**

---

**End of IMPLEMENTATION_BACKLOG v17.** Authoritative as of 2026-06-03 (PR3a micro-polish session). Supersedes `IMPLEMENTATION_BACKLOG_v16.md` (preserved as historical reference).
