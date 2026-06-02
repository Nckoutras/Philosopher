# THE WISE ROOM — Implementation Backlog v16

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v16 = v15 baseline (2026-06-01) + 2026-06-01 Council session delta (The Council shipped end-to-end: C5–C7c, PRs #182–#186; migrations 019 + 020; boardroom screen; save/unsave; share PNG; Mirror animated; shared Pillow renderer).**
>
> **Generated:** 2026-06-01 (v16 rotation)
>
> **How to read this file:**
> - This v16 file supersedes v15 and all prior backlog files.
> - Where v16 conflicts with v15, v16 wins.
> - Status, priority, and launch-readiness calls reflect 2026-06-01 state.
>
> **Companion documents:**
> - `PROJECT_STATE_v16.md` — current project state
> - `HANDOFF_BRIEF_v16.md` — continuity and implementation history
> - `SCREENS_TRACKING_v4.md` — full screen inventory
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

## v16 Consolidation Summary (2026-06-01)

> v16 = v15 baseline + The Council shipped. Where v16 conflicts with v15, v16 wins.

**Shipped this session (PRs #182–#186):**

- **The Council** — 4-member philosophical council (Machiavelli, Epictetus, Freud, de Beauvoir); 4 sequential verdicts + app-voice synthesis; SSE stream end-to-end; save/unsave toggle; share PNG with shared Pillow renderer. Boardroom screen live. Migrations 019 (council_cases / council_sessions / council_responses) + 020 (council_saves).
- **Mirror animated** — `INTRO_HOLD` 1100→2100 in both mirror and council pages; CTA border 1.5px on mirror.
- **`image_service.py` refactored** — `_render_share_canvas` shared Pillow core; reflections path byte-identical; council path added.
- **`SharePreviewModal` generalized** — `kind: 'line' | 'council'` discriminant; existing call sites unaffected.

**New open items added this session:**

- [ ] **Per-verdict → reflections save** — investigation brief required: `saved_lines` is message-centric; `council_responses` are not `messages`. Schema gap must be resolved before build.
- [ ] **Council share card redesign** — current card is a functional placeholder (generic Pillow layout). Full design: boardroom.webp bg, date header, 4 member portrait thumbnails, centered synthesis text. Requires boardroom.webp + 4 persona portrait files under `apps/api/static/personas/`.
- [ ] **Reflection share card redesign** — center the quote text; make thumbnail smaller/lower.
- [ ] **compress mirror.png** — 2.3MB PNG → WebP (page-load improvement).
- [ ] **branding resolution** — "The Wise Room" vs "Great Minds" still unresolved in codebase (FROM_EMAIL, FRONTEND_URL, copy strings); separate thread in progress.
- [ ] **mirror 'said' line-clamp** — removed during polish; watch for layout issues with long user input in the Mirror.

**Status:** The Council ✅ COMPLETE. Critical path to revenue: TD-11 → disable `BETA_GRANT_PRO_TO_ALL` → Stripe checkout smoke test (with BETA flag OFF).

---

## v15 Consolidation Summary (2026-06-01)

The Mirror shipped (PRs #166–#173). See `IMPLEMENTATION_BACKLOG_v15.md §v15 Consolidation Summary` for full detail.

---

## v14 Addendum — Voice Overhaul (2026-05-30)

All 9 personas voice-tightened; check_brevity live; Socrates elenchus upgraded; Wilde/Machiavelli/Lao Tzu got ResponseLengthSpec. See v15 §v14 Addendum for full detail.

---

## 1. Current Launch Interpretation

**Plan A (active).** Current priority order as of 2026-06-01:

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
20. ~~**The Council**~~ ✅ DONE (2026-06-01) — PRs #182–#186; 4 members; verdicts + synthesis; save/share; migrations 019 + 020
21. **TD-11 — Tier resolution refactor** — required before BETA flag can be safely disabled [REVENUE GATE]
22. **Disable BETA_GRANT_PRO_TO_ALL** — then run end-to-end Stripe sandbox test [REVENUE GATE]
23. **End-to-end Stripe sandbox test** (with BETA flag OFF)
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
- [ ] **PR-D2 production smoke test** — verify NamePromptCard save flow end-to-end. Use gmail for OTP delivery. OTP issue investigation pending.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu (live since 2026-05-30, author-testing pending)

### 2.1 Infrastructure P0

- [x] ~~**Oregon migration completion**~~ — DATABASE_URL confirmed pointing to Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2) as of 2026-06-01
- [ ] **source_chunks re-ingest** into Oregon project via OpenAI embeddings script (TD-22); status unconfirmed post-switch
- [x] ~~**Render DATABASE_URL switch**~~ — CONFIRMED DONE (Oregon live)
- [ ] **Post-Oregon smoke test** (login, chat, Mirror, Council, rituals, share, library, RAG retrieval)
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**

### 2.2 Code-side P0

- [ ] **bugfixes-3 — auth race fix** (P0; see TD-10; PR4ai deferred)
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel → tier downgrade)
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari)
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure — 9 mobile walkthrough findings)

### 2.3 Legal P0

- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **GDPR / DPA infrastructure** (Anthropic DPA, processors doc, data subject request fulfillment)
- [ ] **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety escalation)

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

### TD-11 — Tier resolution unified refactor (P0 launch blocker)

Must consolidate `get_current_user_plan` and `get_user_tier` before disabling `BETA_GRANT_PRO_TO_ALL`. Escalated to P0.

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

ANTHROPIC_API_KEY disappeared between May 25-27. Add `sync: false` to all secrets in render.yaml + startup health check + Upstash quota alert.

### TD-25 — compress mirror.png (P1)

`apps/api/static/personas/mirror.png` or equivalent public asset is ~2.3MB. Convert to WebP for page-load performance. No code change beyond asset swap.

### TD-26 — Council share card full design (P1)

Current council share PNG is a functional placeholder. Full design: boardroom.webp background, date header, 4 member portrait thumbnails, centered synthesis text. Requires:
- boardroom.webp copied to `apps/api/static/personas/` (currently only in Next.js public assets as `/personas/boardroom.webp`)
- 4 member portrait files (Machiavelli, Epictetus, Freud, de Beauvoir) confirmed available at the same static path
- New `_draw_council_canvas` or extended `_render_share_canvas` in `image_service.py`

### TD-27 — Per-verdict → reflections save (investigation required, P1)

`saved_lines` requires `message_id` FK. Council verdicts live in `council_responses`, not `messages`. Three options to investigate:
1. Create a parallel `council_saves_line` table that maps to council_responses
2. Insert synthetic `messages` rows for verdict content (mirrors the existing message-centric model)
3. Extend `saved_lines` with a nullable `council_response_id` FK (schema change)

**Do not build without investigation brief first.**

---

## 4. Database schemas

See `PROJECT_STATE_v16.md §4`. Migration head: `020_create_council_saves`. Migrations 019 (council_cases/sessions/responses) and 020 (council_saves) added 2026-06-01.

---

## 5. Config & Environment Variables

See `HANDOFF_BRIEF_v16.md §7` for full env var list. No new env vars added in Council session.

---

## 6. Stripe Wiring (sandbox complete — PR1 #77)

Status: 🟢 **Sandbox complete (PR1 #77, 2026-05-19).** Unchanged from v12.

End-to-end sandbox test still pending (see §2.2 P0 checklist). BETA bypass active.

---

## 7. Persona-specific maintenance backlog

Unchanged from v12. ChatGPT audit, YAML extraction, portrait harmonization still pending.

---

## 8. LLM eval (optional)

Status: ⏸ P3. Unchanged from v12.

---

## 9. Future blocks reference

### 9.1 Block C — complete

Unchanged from v12. Real-time streaming added in PR-A (Bug #4).

### 9.2 Block D — D1 + D2 complete

**PR-D (#129):** D1 greeting now personalizes with first name.
**PR-D2 (#130):** D1 conditionally shows NamePromptCard for OTP users without a name.

### 9.3 Block F — Reflection

F1 ✅. F2 lite ✅ (wiring verification pending PR-G). F3/F4 ✅ spec (Weekly Reading). F6 ✅. F5 ⏸ v2.

### 9.4 Block H — Subscription & Billing

Unchanged from v12.

### 9.5 Block I — Account & Settings

I1 Account hub not yet built. Spec locked. P1.

### 9.6 Block J — Empty/error states

Unchanged from v12.

### 9.7 Rituals (updated v16 — Council SHIPPED)

**Rituals launch scope — Option B (locked 2026-05-28):**

| Ritual | Status | Notes |
|---|---|---|
| Letter to Future Self | 🟡 UI live, ARQ delivery not wired | Remove account card until wired (PR4af done) |
| The Mirror | 🟢 **SHIPPED** (2026-06-01, PRs #166–#173) | Generator + idempotent cron (weekly + preview) + host picker + ring-true live. Eligible hosts: Jung (default), Lao Tzu, Marcus Aurelius. MIRROR_PROMPT locked. |
| The Council | 🟢 **SHIPPED** (2026-06-01, PRs #182–#186) | 4 members (Machiavelli, Epictetus, Freud, de Beauvoir). Verdicts + synthesis SSE. Save/unsave. Share PNG. Migrations 019 + 020. |
| The Counterview | 🔴 NOT DESIGNED | Spec §1.3.2 describes the flow (locked in Option B); implementation not yet designed. Do not dispatch brief until design session complete. Host: Machiavelli (Pro-only). |
| Weekly Reading placeholder | 🔴 pending | "Coming this season" locked card in Rituals tile |

**Common ritual spine (locked):** Unchanged from v15.

**Council Mode (shipped as Council — Phase 5 reinterpreted as direct feature):**

The Council was originally Phase 5 / post-launch Premium. It shipped earlier than planned as a Pro-gated ritual (BETA_GRANT_PRO_TO_ALL makes everyone Pro during cold beta). The "Heraclitus secret host" and Premium-tier mechanics remain parked (⏸ Phase 5).

### 9.8 Council fast-follows (post-first-paying-user; NOT before)

These should NOT block launch or the first Stripe test. Implement after first paying user confirmed.

- [ ] **Per-verdict → reflections save** — investigation brief first (TD-27). P1.
- [ ] **Council share card full redesign** — boardroom bg, date header, 4 thumbnails (TD-26). P1. Needs static assets.
- [ ] **Reflection share card redesign** — center text, smaller/lower thumbnail. P1.
- [ ] **compress mirror.png → WebP** (TD-25). P1.

### 9.9 Mirror fast-follows (post-first-paying-user; NOT before)

Unchanged from v15.

- [ ] **Mirror v2 — branded email postcard** — host's closing words + thumbnail + date; reuse Resend infra. P1.
- [ ] **Host-aware handoff** — reuse `CROSS_MIND_NOTE` pattern. P1.
- [ ] **Smart input cap on Mirror generator** — cost control at scale. P1.

### 9.10 Counterview — spec §1.3.2 exists; implementation NOT DESIGNED

Counterview is locked in Option B (Setup → 2 rounds steelman-the-opposite → 2-line closing "What shifted, what didn't"). Implementation not yet designed.

**Do not dispatch a build brief until a design session is complete.**

- Proposed host: Machiavelli (Pro-only, no free preview)
- Depends on Mirror + Council stable in production
- First step: design session with Claude (chat) to define implementation approach

---

## 10. Operating principles (preserved + extended)

### 10.1–10.24 — Preserved from v15

Full text in prior handoff briefs. Key rules: P-01 through P-06 in CLAUDE.md.

### 10.25 — Council rate-limit counter is shared by design (NEW v16)

`/share/screenshot` and `/council/{id}/share` share the Redis key `share_screenshot:{user.id}`. Free users get 3 combined shares per 90-day window. This is intentional. Any change to give separate counters requires a key-name change only — no schema or migration needed.

### 10.26 — `_render_share_canvas` is the canonical share image entry point (NEW v16)

All share card variants should use `_render_share_canvas` as the Pillow drawing core. Do not duplicate Pillow boilerplate. New share card types: add new callers, not new drawing functions from scratch.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt** (TD-23) — add `.env.local`, `.env*.local` to `.gitignore`. Single commit.
- [ ] **PR-D2 production smoke test** — verify name save flow with gmail workaround
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu

### 11.1 P0 (launch blockers)

- [x] ~~Prior P0 items through 2026-05-28~~ — DONE (see v12–v13 §11.1)
- [x] ~~**Voice overhaul**~~ DONE (2026-05-30)
- [x] ~~**The Mirror**~~ ✅ DONE (2026-06-01) — PRs #166–#173
- [x] ~~**The Council**~~ ✅ DONE (2026-06-01) — PRs #182–#186; 4 members + synthesis + save + share; migrations 019 + 020
- [ ] **🔴 TD-11 — Tier resolution refactor** — REVENUE GATE; required before disabling BETA flag
- [ ] **🔴 Disable BETA_GRANT_PRO_TO_ALL** — set false in Render env after TD-11; then run Stripe test
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel → tier downgrade; MUST run with BETA flag OFF)
- [x] ~~**Oregon region migration completion**~~ — DATABASE_URL confirmed pointing to Oregon
- [ ] **source_chunks re-ingest** into Oregon (TD-22; status unconfirmed post-switch)
- [ ] **Post-Oregon smoke test** (login, chat, Mirror, Council, rituals, share, library, RAG retrieval)
- [ ] **bugfixes-3 — auth race fix** (TD-10; preview smoke test required)
- [ ] **Mobile 12-point nav smoke test**
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Cold validation with external users** (retention + willingness-to-pay)
- [ ] **Consolidated polish PR** (Block B visual closure)
- [ ] **Lawyer review** of Terms / Privacy / Disclaimer
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**
- [ ] **RLS policies** as defense-in-depth
- [ ] **UAT** with 3–5 testers, ≥2/5 spontaneous "I'd pay"

### 11.2 P1 (post-revenue, shortly after first paying user)

- [ ] **Per-verdict → reflections save** (TD-27) — investigation brief first
- [ ] **Council share card redesign** (TD-26) — boardroom bg + 4 thumbnails + date header
- [ ] **Reflection share card redesign** — center text, smaller thumbnail
- [ ] **compress mirror.png** (TD-25) — 2.3MB PNG → WebP
- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to Future Self — ARQ email delivery wiring**
- [ ] **OTP-01 investigation** — Render logs for ote.gr delivery failure
- [ ] **TD-24 — render.yaml sync:false** for all secrets + startup health check + Upstash quota alert
- [ ] **Mirror v2 — branded email postcard** (post-first-paying-user)
- [ ] **Host-aware handoff** — reuse `CROSS_MIND_NOTE` pattern (post-first-paying-user)
- [ ] **Smart input cap on Mirror generator** (post-first-paying-user)
- [x] ~~**Render API plan upgrade**~~ DONE (both services paid tier, 2026-05-25)

### Next brief sequence (P1-P2 feature work)

Suggested execution order post .gitignore fix + smoke test:

**Priority: Revenue gate first (TD-11 + BETA off + Stripe test)**

**Then Council fast-follows (investigation first):**

0. **Investigation brief: per-verdict saves** — map `council_responses` → `saved_lines` schema gap; produce options report.

**Then remaining Brief #1 queue:**

1. **PR-C — Library F6 spec restoration** (1-2 days) — fix duplicate persona name + add last-message snippet
2. **PR-G — F2 verification + Sunday counter** (2-4 days)
3. **PR-E — Press further mode toggle** (3-4 days)

**Then Rituals:**

4. **Design session with Claude (chat)** — Counterview spec + guided program flows; scope NOT YET DESIGNED

### Secondary briefs (parallel-track candidates)

- Brief #3 — About copy integration (depends on branding resolution)
- Brief: Council share card redesign (depends on static asset availability)

### 11.3 P2 (tech debt)

- [ ] **TD-11** — Tier resolution unified refactor — **escalated to P0 blocker; see §11.1**
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

### 11.4 P3

- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **Desktop layout polish**
- [ ] **Phase 5 Council Premium mechanics + Heraclitus secret host** (post-launch, post-feedback)
- [ ] **Phase 6 eval suite + CI**
- [ ] **LLM eval test** for Lao Tzu

### 11.5 P4

- [ ] **TD-04** — Backoff discrepancy
- [ ] **TD-06** — `safety_events.message_id` always NULL
- [ ] **TD-07** — gh CLI install on founder's Windows
- [ ] **TD-14** — BASE_URL legacy cleanup in config.py
- [ ] **openapi.json → .gitignore**
- [ ] **Legal pages `target="_blank"` rel hardening**
- [ ] **Stale branch cleanup**

---

## 12. Plan A vs Plan B (preserved)

Unchanged from v12. Plan A active.

Realistic timeline from end of 2026-06-01 session: 5-8 weeks total.
- Revenue gate (TD-11 + BETA off + Stripe test): ~1-2 weeks
- Council fast-follows + Counterview design: ~1-2 weeks
- Rituals guided programs (Counterview): ~2-4 weeks
- Cold beta + DNS cutover: 1-2 weeks
- **Target: mid-July 2026.**

---

**End of IMPLEMENTATION_BACKLOG v16.** Authoritative as of 2026-06-01. Supersedes `IMPLEMENTATION_BACKLOG_v15.md` (preserved as historical reference).
