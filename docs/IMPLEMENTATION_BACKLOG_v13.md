# GREAT MINDS — Implementation Backlog v13

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v13 = v12 baseline (2026-05-26) + 2026-05-28 session delta (Bug #1 BottomSheet race #127; Upstash Pay-as-You-Go upgrade; ANTHROPIC_API_KEY incident resolved; Bug #4 / PR-A real-time streaming #128; PR-D greeting personalization #129; PR-D2 name capture #130; rituals scope locked; council mode locked; PR-E/PR-F/Weekly Reading decisions; .gitignore + render.yaml security debt added).**
>
> **Generated:** 2026-05-28 (v13 rotation)
>
> **How to read this file:**
> - This v13 file supersedes v12 and all prior backlog files.
> - Where v13 conflicts with v12, v13 wins.
> - Status, priority, and launch-readiness calls reflect 2026-05-28 state.
>
> **Companion documents:**
> - `PROJECT_STATE_v13.md` — current project state
> - `HANDOFF_BRIEF_v13.md` — continuity and implementation history
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

## v13 Consolidation Summary

### What shipped (2026-05-28) — items to mark DONE

| Item | PR | Status |
|---|---|---|
| Bug #1 — BottomSheet history.back navigation race | #127 | ✅ DONE |
| Upstash Pay-as-You-Go upgrade (free tier 500k limit hit → worker crashed) | — | ✅ DONE |
| ANTHROPIC_API_KEY re-added to philosopher-api + philosopher-worker | — | ✅ DONE |
| Bug #4 / PR-A — Real-time streaming + inline correction | #128 | ✅ DONE |
| PR-D — Greeting personalization with first name | #129 | ✅ DONE |
| PR-D2 — Name capture deferred prompt + PATCH /me | #130 | ✅ DONE |

### Strategic decisions locked this session

| Decision | Status |
|---|---|
| Rituals launch scope — Option B (Mirror, Counterview, Letter, Weekly Reading placeholder) | ✅ LOCKED |
| Weekly Reading = canonical F3/F4 (renamed, single feature) | ✅ LOCKED |
| Council Mode (post-launch Premium / Phase 5) | ✅ LOCKED |
| Press further mode (PR-E) — rename + conversation-scoped toggle | ✅ LOCKED |
| Typography V1 scope (PR-F) — labels/headers only, body text untouched | ✅ LOCKED |
| Data collection policy — name-only deferred prompt; no demographics | ✅ LOCKED |
| Brand rename "Great Minds" → "The Wise Room" — in separate thread | 🟡 IN PROGRESS |

### Items still open (carried from v12)

Oregon migration partial data + DATABASE_URL switch + source_chunks re-ingest — not addressed in this session; still pending.

---

## 1. Current Launch Interpretation

**Plan A (active).** Current priority order as of 2026-05-28:

1–10. ~~Prior items through 2026-05-26~~ — DONE (see v12 §1)
11. ~~**Bug #1 — BottomSheet race**~~ DONE (#127, 2026-05-28)
12. ~~**Bug #4 / PR-A — Real-time streaming**~~ DONE (#128, 2026-05-28)
13. ~~**PR-D — Greeting personalization**~~ DONE (#129, 2026-05-28)
14. ~~**PR-D2 — Name capture prompt**~~ DONE (#130, 2026-05-28)
15. **Fix .gitignore security debt** — `.env.local` not protected. Must be done before any further PR work.
16. **PR-D2 production smoke test** (blocked by OTP issue; use gmail workaround)
17. **Oregon region migration completion** — remaining tables + source_chunks re-ingest + DATABASE_URL switch
18. **Post-switch smoke test** — full app verification on Oregon
19. **End-to-end Stripe sandbox test**
20. **Mobile 12-point nav smoke test**
21. **Cold beta with 3–5 fresh users**
22. **PR-C — Library F6 spec restoration** (fix duplicate persona name + add last-message snippet)
23. **PR-F — Typography V1** (labels/headers scope)
24. **PR-G — F2 verification + Sunday counter**
25. **PR-E — Press further mode toggle**
26. **PR-B — C9 Bring another mind end-to-end** (biggest, Pro-gated)
27. **Block B consolidated polish PR**
28. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)
29. **UAT** (≥2/5 spontaneous "I'd pay")
30. **Public launch**

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt** — add `.env.local` and `.env*.local` to `.gitignore`. Single-file commit. Branch: `chore/gitignore-env-local`. MUST be done before any other PR.
- [ ] **PR-D2 production smoke test** — verify NamePromptCard save flow end-to-end. Use gmail for OTP delivery (ote.gr delivery failing). OTP issue investigation pending.

### 2.1 Infrastructure P0

- [ ] **Oregon migration completion** (messages, saved_lines, safety_events, user_ritual_completions, scheduled_emails, memory_entries, disclaimer_acceptances, alembic_version, conversations.source_saved_line_id UPDATE)
- [ ] **source_chunks re-ingest** into Oregon project via OpenAI embeddings script (TD-22)
- [ ] **Render DATABASE_URL switch** to Oregon pooler (founder action, post-verification)
- [ ] **Post-switch smoke test** (login, chat, rituals, share, library, RAG retrieval)
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

### TD-11 — Tier resolution unified refactor (P2, pre-paid-launch)

Unchanged from v12. Must consolidate `get_current_user_plan` and `get_user_tier` before disabling `BETA_GRANT_PRO_TO_ALL`.

### TD-12 through TD-15

Unchanged from v12.

### TD-17 — Weekly Reading full implementation (post cold-beta, multi-week)

Scope now locked (see §9.7). Not before cold-beta validation. Canonical feature = F3/F4 Weekly Letter (renamed Weekly Reading). See §9.7 for full spec.

### TD-18 through TD-21

Unchanged from v12.

### TD-22 — source_chunks re-ingest post-Oregon migration (P0 operational)

Unchanged from v12. After DATABASE_URL switch, re-ingest 2476 × 1536-dim vectors via existing OpenAI embeddings script. Not a code change — operational step.

### TD-23 — .gitignore security debt (P0 operational — new v13)

`.env.local` is NOT in `.gitignore`. Production secrets are one careless `git add -A` away from being committed to the public repo.

**Fix:** Add `.env.local` and `.env*.local` patterns to `.gitignore`. Single-file commit. Branch: `chore/gitignore-env-local`.

**Must be done before any further PR work.**

### TD-24 — render.yaml sync:false for all secrets (P1 operational — new v13)

ANTHROPIC_API_KEY disappeared from both Render services between May 25-27 (cause unconfirmed — possibly blueprint sync without sync:false flag). Upstash also vulnerable to accidental sync reset.

**Fix:** Add `sync: false` to render.yaml for ALL secrets:
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `JWT_SECRET`, `SECRET_KEY`, `REDIS_URL`, `DATABASE_URL`, `RESEND_API_KEY`

**Additionally:**
- Implement startup health check that fails loudly on missing critical secrets
- Set up Upstash 80% quota alert
- Set up Render env-var-change notification

---

## 4. Database schemas

See `PROJECT_STATE_v13.md` §4. Migration head: `015_add_fk_indexes`. No new migrations in 2026-05-28 session.

---

## 5. Config & Environment Variables

See `HANDOFF_BRIEF_v13.md` §7 for full env var list.

**Key changes since v12:**
- `REDIS_URL` — Upstash now Pay-as-You-Go ($0.2/100k commands); was free tier
- `ANTHROPIC_API_KEY` — re-added to both services after disappearing between May 25-27

---

## 6. Stripe Wiring (sandbox complete — PR1 #77)

Status: 🟢 **Sandbox complete (PR1 #77, 2026-05-19).** Unchanged from v12.

End-to-end sandbox test still pending (see §2.2 P0 checklist). BETA bypass active.

---

## 7. Persona-specific maintenance backlog

Unchanged from v12. ChatGPT audit, YAML extraction, portrait harmonization all still pending.

---

## 8. LLM eval (optional)

Status: ⏸ P3. Unchanged from v12.

---

## 9. Future blocks reference

### 9.1 Block C — complete

Unchanged from v12. Real-time streaming added in PR-A (Bug #4).

### 9.2 Block D — D1 + D2 complete

**PR-D (#129):** D1 greeting now personalizes with first name via `getGreetingWithName`.
**PR-D2 (#130):** D1 conditionally shows NamePromptCard for OTP users without a name.

D2/D3 unchanged.

### 9.3 Block F — Reflection

F1 ✅. F2 lite ✅ (wiring verification pending PR-G). F3/F4 ✅ spec (implementation = Weekly Reading, see §9.7). F6 ✅. F5 ⏸ v2.

### 9.4 Block H — Subscription & Billing

Unchanged from v12.

### 9.5 Block I — Account & Settings

I1 Account hub not yet built. Spec locked. P1.

### 9.6 Block J — Empty/error states

Unchanged from v12.

### 9.7 Rituals (updated v13 — SCOPE LOCKED)

**Rituals launch scope — Option B (locked 2026-05-28):**

| Ritual | Status | Notes |
|---|---|---|
| Letter to Future Self | 🟡 UI live, ARQ delivery not wired | Remove account card until wired (PR4af done) |
| The Mirror | 🔴 BLOCKED on Brief #4 | Needs `mirror_ritual_prompt.md` for Jung + Marcus Aurelius; 3 lifetime for free, Jung = Pro |
| The Counterview | 🔴 BLOCKED on Brief #5 | Needs Mirror done + `counterview_ritual_prompt.md` for Machiavelli; Pro-only, no free preview |
| Weekly Reading placeholder | 🔴 pending | "Coming this season" locked card in Rituals tile; can be added any time as Brief #2 |

**Common ritual spine (locked):**
- Single-purpose, time-boxed, closed-loop
- Auto-save to F1 with ritual tag
- House-persona (not user-chooseable)
- Philosophical heritage positioning
- NO gamification
- Section 5.7 compliant (anti-flexing, brevity, register, forbidden lexicon)
- Editorial layout (NO chat bubbles)

**The Mirror flow (locked):**
- Setup: 280-char prompt entry
- Reflection: ≤3 rounds, editorial passages
- Closing: "A line worth keeping" pull-quote
- CTAs: Begin again / Done / Convene the Council
- Counterview safety: pre-ritual gate detects vulnerability → soft redirect; crisis → C7 safety screen

**The Counterview flow (locked):**
- Setup → 2 rounds (≤4 sentences each, steelman-the-opposite)
- 2-line closing "What shifted, what didn't"

**Weekly Reading (canonical spec, locked):**
- = renamed F3/F4 Weekly Letter — single canonical feature, not a separate system
- Sunday 8am delivery, 150-250 words
- Rotating most-active-persona author + fallback "The Wise Room" house voice
- Sources: kept F2 insights + Mirror/Counterview closings + F1 saves
- Min 3 items else quiet-week
- First-week = introduction letter (≥7 days post-signup trigger)
- Surfaces: Sunday email + F3 inbox + F4 detail + Rituals tile
- Pro-only. "Remove this reading" option.

**Council Mode (Phase 5 / post-launch Premium):**
- Dual entry: "Convene the Council on this" CTA (after ≥5 user messages) + Today/Rituals tile
- Max 3 personas, sequential turns; optional synthesis card
- Initially Pro-only, may shift to Premium tier

---

## 10. Operating principles (preserved + extended)

### 10.1–10.22 — Preserved from v12

Full text in prior handoff briefs. Key rules: P-01 through P-06 in CLAUDE.md.

### 10.23 — MCP migration pattern for large vector data (NEW v12)

Unchanged from v12.

### 10.24 — Operational incident response (NEW v13)

When a production service becomes unhealthy (worker crash, missing env vars):
1. Check Render logs first — confirm the actual error before touching code or config
2. Check Upstash dashboard for quota/rate metrics if Redis-related
3. Verify env vars in Render dashboard for both `philosopher-api` AND `philosopher-worker` — they must be in sync
4. After any env var change: redeploy both services; smoke test chat + title generation
5. Add `sync: false` to `render.yaml` for all secrets to prevent recurrence (TD-24)

Lesson: ANTHROPIC_API_KEY disappeared silently from both services between May 25-27. Cause unconfirmed. Production was broken for ~2 days before discovery. Startup health check (TD-24) would have surfaced this immediately.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt** (TD-23) — add `.env.local`, `.env*.local` to `.gitignore`. Single commit.
- [ ] **PR-D2 production smoke test** — verify name save flow with gmail workaround

### 11.1 P0 (launch blockers)

- [x] ~~Prior P0 items through 2026-05-26~~ — DONE (see v12 §11.1)
- [x] ~~**Bug #1 — BottomSheet race**~~ DONE (#127, 2026-05-28)
- [x] ~~**Bug #4 / PR-A — Real-time streaming**~~ DONE (#128, 2026-05-28)
- [x] ~~**PR-D — Greeting personalization**~~ DONE (#129, 2026-05-28)
- [x] ~~**PR-D2 — Name capture prompt**~~ DONE (#130, 2026-05-28)
- [ ] **Oregon region migration completion** (remaining tables + source_chunks re-ingest)
- [ ] **Render DATABASE_URL switch** to Oregon (founder action post-verification)
- [ ] **Post-switch smoke test**
- [ ] **bugfixes-3 — auth race fix** (TD-10; preview smoke test required)
- [ ] **End-to-end Stripe sandbox test**
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

### 11.2 P1

- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to Future Self — ARQ email delivery wiring**
- [ ] **OTP-01 investigation** — Render logs for ote.gr delivery failure
- [ ] **TD-24 — render.yaml sync:false** for all secrets + startup health check + Upstash quota alert
- [x] ~~**Render API plan upgrade**~~ DONE (both services paid tier, 2026-05-25)

### Next brief sequence (P1-P2 feature work)

Suggested execution order post .gitignore fix + smoke test:

1. **PR-C — Library F6 spec restoration** (1-2 days)
   - Fix duplicate persona name on conversation cards
   - Add last-message snippet preview (~70 chars + ellipsis)
   - Likely requires backend extension to conversation list endpoint
   - Brief drafted, awaiting dispatch

2. **PR-F — Typography V1** (2-3 days)
   - Scoped audit of labels/headers only
   - DO NOT touch body text

3. **PR-G — F2 verification + Sunday counter** (2-4 days)
   - Verify F2 lite Insights wired correctly
   - Add "Saved. This will return in your Sunday reading." toast
   - D1 Today counter row "Reflections gathering for Sunday" (Pro only, ≥1 kept this week)

4. **PR-E — Press further mode toggle** (3-4 days)
   - "Ask harder" → "Press further" rename
   - Mode toggle with header sub-pill state indicator
   - May need migration for existing conversations

5. **PR-B — C9 Bring another mind end-to-end** (4-6 days, biggest)
   - Inline second-opinion from another persona mid-chat
   - C9a picker + C9b inline rendering
   - Pro-gated

### Secondary briefs (parallel-track candidates)

- Brief #2 — Weekly Reading placeholder card (drop-in any time, low effort)
- Brief #3 — About copy integration (depends on brand rename merged)
- Brief #4 — The Mirror implementation (BLOCKED on `mirror_ritual_prompt.md` for Jung + Marcus)
- Brief #5 — The Counterview implementation (BLOCKED on Mirror done + `counterview_ritual_prompt.md` for Machiavelli)

### 11.3 P2 (tech debt)

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch)
- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-01** — Split `rate_limit_service.py`
- [ ] **TD-02** — PersonaConfig / Persona ORM naming confusion
- [ ] **TD-03** — Update or remove `ANTHROPIC_MODEL` constant
- [ ] **TD-08** — Document Render alembic auto-run mechanism
- [ ] **ChatGPT audit** of new persona configs
- [ ] **Portrait style harmonization**
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML**
- [ ] **Premium tier reassignment** (Freud → premium if desired)
- [ ] **C9 real implementation** (post-revenue)
- [ ] **F2 Suggested insights (lite)** (post-revenue)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-20** — safety_events.message_id FK ondelete
- [ ] **TD-21** — passive_deletes audit

### 11.4 P3

- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **Desktop layout polish**
- [ ] **Phase 5 Council Mode architecture + UI chips**
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

Realistic timeline from end of 2026-05-28 session: 8-12 weeks total.
- Brief #1 complete (PR-C, PR-F, PR-G, PR-E, PR-B): ~3 weeks
- Brand rename merged: ~1-2 weeks parallel
- Briefs #2-#5 complete: 6-9 weeks
- Cold beta + Stripe live + DNS cutover: 2-3 weeks
- **Target: early-to-mid August 2026.**

---

**End of IMPLEMENTATION_BACKLOG v13.** Authoritative as of 2026-05-28. Supersedes `IMPLEMENTATION_BACKLOG_v12.md` (preserved as historical reference).
