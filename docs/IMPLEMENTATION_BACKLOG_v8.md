# GREAT MINDS — Implementation Backlog v8

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v8 = v7 baseline (2026-05-10) + 2026-05-11 addendum (design system v4→v5) + 2026-05-13 session delta (Block B 6/6 functional spine shipped, 9 personas live, mobile walkthrough findings, polish PR pending).**
>
> **How to read this file:**
> - This v8 file supersedes v7 and all prior backlog files.
> - Where v8 conflicts with v7, v8 wins.
> - Historical detail retained where still useful.
> - Status, priority, and launch-readiness calls reflect 2026-05-13/14 state.
>
> **Last updated:** 2026-05-14. **Block B 6/6 functional spine SHIPPED.** Consolidated polish PR pending for visual/QA closure. Founder confirmed Plan A path is active (Plan B preserved as alternative).

**Correction note (2026-05-14):** This version includes a consistency pass against v7/v7 addendum and the v8 companion docs. It fixes wording around Block B closure, Block C scope, Stripe pricing baseline, Pro persona count, existing chat tables, and code-vs-DNS dependencies.
>
> **Companion documents:**
> - `SCREENS_TRACKING_v4.md` — full screen inventory and per-screen specs (43 screens)
> - `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect
> - `HANDOFF_BRIEF_v8.md` — continuity and implementation history (replaces v7)
> - `PROJECT_STATE_v8.md` — current project state (replaces v7 + addendum)
>
> **Priority key:**
> - **P0** = launch blocker / must be done before public launch
> - **P1** = post-revenue cleanup / fix shortly after first paying user
> - **P2** = v2 / post-MVP refinement
> - **P3** = post-launch / post-feedback backlog
> - **P4** = technical debt / infrastructure cleanup
>
> **Status key:** 🔴 not started · 🟡 in progress · 🟢 done · ⏸ deferred
>
> **Authoritative rule:** If this file conflicts with any earlier backlog file, this v8 file wins.

---

## v8 Consolidation Summary

### What changed from v7 (2026-05-11 + 2026-05-13 sessions)

**2026-05-11 (Design System v4→v5 palette migration):**
- Warmer palette restored after silent drift discovered (1 commit, 5 files)
- New tokens: `White #FFFFFF`, `shadow-card`, `shadow-card-hover`; `Rust` → `Safety #7A4030`
- Design System spec committed to repo (was Claude.ai project knowledge only)
- Branch hygiene lesson: never reuse squash-merged branches

**2026-05-13 (Block B onboarding spine + 4 new personas):**
- 11 PRs + 1 hotfix merged in ~14 hours sustained session
- Block B 6/6 functional spine SHIPPED (B1-B6 all live)
- 9 personas now in production (was 6): Lao Tzu (free), Wilde (pro), Machiavelli (pro) added; Jung activated; Freud remains pro
- 3 migrations applied: 004 (user_preferences), 005 (personas bio+portrait), 006 (3 new personas + Jung activation)
- Production deploy incident (PR #43 emoji surrogate) recovered via hotfix PR #44 with zero data corruption
- Mobile walkthrough revealed 9 issues (3 critical, 2 important, 4 polish) — all to be fixed in consolidated polish PR
- 4 Block B strategic decisions resolved (backend persistence + backend matching, B6 built now, wide-table schema)
- Two new operating principles added: §19.14 (Unicode encoding pre-merge check for JSONB migrations), §19.15 (mobile walkthrough is non-substitutable)
- Two new mentor lessons logged: §19.16 (read existing docs before replacement), §19.17 (addendum vs baseline regen discipline)

### Key decisions logged in v8

- **2026-05-13** — Block B 4 strategic decisions resolved (backend everything; B6 built now as variant of B5; wide-table preferences)
- **2026-05-13** — Hero text style: V2 (Option B — white text + drop shadow + dark gradient, regular weight serif, wider layout)
- **2026-05-13** — Email domain: `thegreatminds.app` for Resend custom domain (DNS setup in progress)
- **2026-05-13** — Polish scope: ALL 11 findings in one consolidated polish PR
- **2026-05-11** — Design System v4→v5 palette migration shipped

### Current source-of-truth status

- ✅ Phase 4 stabilization sequence: 8/8 ship items closed
- ✅ Setup PR + Greenfield scaffold (2026-05-07)
- ✅ Design System v4→v5 migration (2026-05-11)
- ✅ **Block A — Authentication: 5/5 line-items live**
- ✅ **Block B — Onboarding: 6/6 functional spine shipped** (visual closure pending polish PR)
- ✅ Backend OTP infrastructure
- ✅ Backend disclaimer infrastructure
- ✅ Backend user_preferences + matching service
- ✅ 9 personas live with full Section 5.7 character config + bio + portrait
- ✅ Alembic plumbing; migrations 001-006 applied
- ✅ Legal pages templates live — ⚠️ lawyer review pending
- ✅ Vercel parallel deployment disconnected
- ⏳ **Consolidated polish PR** (11 findings — blocks Block B visual closure)
- ⏳ 34 of 45 line-items remain in 43-screen UI build (11 closed: A 5/5 + B 6/6 spine)
- ⏳ Stripe wiring (calendar gate passed; status unverified)
- ⏳ Resend domain verification for `thegreatminds.app`
- ⏳ DNS configuration for `thegreatminds.app` (in progress)
- ⏳ Lawyer review of legal templates
- ⏳ Founder runbooks
- ⏳ UAT with mixed testers
- ⏳ Web/PWA public launch

---

# 1. Current Launch Interpretation

The engine is no longer the main blocker. Phase 5 and Phase 6 are deferred to post-launch. **Block A is FULLY closed (5/5). Block B is FUNCTIONALLY closed (6/6 spine shipped), but visual/QA closure is still pending the consolidated polish PR.** Block C (**Chat experience**, not onboarding) is the next P0 work surface AFTER the polish PR is merged and verified on real mobile devices.

The remaining work surfaces, in priority order under Plan A (confirmed active 2026-05-10):

1. **Consolidated polish PR** (P0 immediate) — visually/QA-close Block B (11 findings, ~6-8 hours CC time; DNS/Resend items are partly manual/config, not code-only)
2. **Block C — Chat experience** (P0 once polish merged) — chat infrastructure + RAG + LLM provider + streaming UI + safety filters (~5-8 PRs, 15-25 hours)
3. **34 remaining UI line-items** per `SCREENS_TRACKING_v4` — Block D Discovery → F Reflection → H Billing → I Settings → J Empty states
4. **Stripe wiring** — calendar-gated; available from 2026-05-11
5. **Lawyer review of legal templates** (P0 launch blocker) — Greek consumer law, Stripe billing T&Cs, AI-content liability scope
6. **Email infrastructure verification** — Resend domain verification for `thegreatminds.app` (depends on DNS)
7. **DNS configuration for `thegreatminds.app`** — IN PROGRESS this session
8. **GDPR / DPA infrastructure** — LLM provider DPA review (when Block C lands), processors documentation, data subject request fulfillment workflow
9. **Operational founder runbooks** — refund, account recovery, GDPR, cancellation override, safety escalation
10. **Production smoke test** of Phase 4 + Block A + Block B
11. **UAT** with mixed testers (≥2/5 spontaneous "I'd pay" criterion)
12. **Public launch (web/PWA)**

Under Plan B (preserved but not active), the order shifts dramatically — see §17.5.

Avoid reopening Phase 4 stabilization or Block A or shipped Block B work unless:
- Production smoke test fails
- Safety classifier shows material false negatives
- Payment entitlement breaks
- Responses show repeated modern-term leakage or persona failure
- Auth flow breaks (cookie persistence, JWT issuance, disclaimer flow, redirect targets)
- Block B onboarding flow breaks (preferences save, matching, persona detail render)

---

# 2. Remaining Launch-Readiness Checklist (P0)

This section is the practical pre-launch checklist. **These items block public launch.**

## 2.1 Code-side P0

### A. Block B visual closure — Consolidated Polish PR

Status: 🟡 in progress (DNS + portrait investigation prerequisites being established)

Covers 11 mobile walkthrough findings:

**Critical:**
- [ ] Portrait loading bug (3 surfaces — welcome, matches thumbnails, persona detail header). Root cause investigation pending. Suspected PR #42 refactor broke flow from backend `persona.portrait_url` → frontend Image component
- [ ] OTP email delivery to corporate domains (currently fails for `@ote.gr`). Depends on DNS + Resend domain verification
- [ ] Refresh on welcome error page redirects to disclaimer instead of retrying
- [x] Tagline missing for personas without Python registry config (Machiavelli, Lao Tzu, Wilde). Fixed via JSONB fallback in apps/api/routers/personas.py for tagline + avatar_emoji + opening_invocation.

**Important:**
- [ ] Hero text B1 — V2 style: white text + drop shadow + dark gradient overlay, regular weight serif, wider layout (~85-90% frame width)
- [ ] iOS Safari `safe-area-inset-bottom` padding for bottom buttons

**Polish:**
- [ ] iOS rubber-band scroll behavior (`overscroll-behavior` + native touch scrolling)
- [ ] Push-button press feedback (CSS `:active` scale-down 0.97x + slight darker)
- [ ] OTP 6-digit input boxes (refactor from single field; autofocus next, paste handling, backspace navigation)
- [ ] Resend sender display name "Great Minds" (Resend dashboard + custom domain)
- [x] B5/B6 persona detail: opening_invocation preview block visually dominated cream content area, pulling focus from portrait. Block removed; opening_invocation remains in API response, reserved for Block C C8 first greeting per spec.

**Estimated effort:** ~6-8 hours CC time. Likely 10-15 files touched.

**Blocked by:**
- DNS + Resend domain verification (manual setup, founder action)
- Portrait bug investigation (CC discovery)

### B. Block C — Chat experience

Status: 🔴 not started

5-8 PRs, 15-25 hours CC time. Cannot start until:
- Polish PR merged + verified on mobile
- DNS complete
- 6 architectural decisions resolved (see §7.1 and `HANDOFF_BRIEF_v8.md` §24.3)

### C. Remaining 34 UI line-items (Blocks D, F, H, I, J)

Status: 🔴 not started. Sequenced after Block C.

## 2.2 Legal P0

### A. Lawyer review of legal templates

Status: 🔴 not started

**Required scope:**
- Terms of Service v1.0 (16 sections) — `apps/web/app/legal/terms/page.tsx`
- Privacy Policy v1.0 (13 sections, GDPR-aware) — `apps/web/app/legal/privacy/page.tsx`
- Disclaimer v1.0 (in `disclaimer_versions` table seed) — `age_copy` + `positioning_copy`

**Lawyer review must cover:**
- Greek consumer law specifics (founder is in Greece; users will likely include EU citizens)
- Stripe billing terms — subscription cancellation, refund policy, recurring billing disclosures
- AI-content liability scope — user expectations, hallucination risk, non-therapeutic positioning, age requirements
- GDPR Article 6 lawful bases per processing activity
- Processors table (Resend, Supabase, OpenAI/Anthropic, Stripe, etc.) — Standard Contractual Clauses where applicable
- DPO/privacy contact information

**Blocker for public launch.** Templates are functional placeholders, NOT legally compliant final copy.

### B. GDPR / DPA infrastructure

Status: 🔴 not started

Required artifacts:
- [ ] DPA with LLM provider (Anthropic Claude or OpenAI GPT-4) — must be reviewed/signed when Block C lands
- [ ] Processors documentation page or appendix
- [ ] Data subject request fulfillment workflow (export, deletion, rectification)
- [ ] Cookie posture documentation
- [ ] Privacy contact / DPO email (placeholder currently)

### C. Operational founder runbooks

Status: 🔴 not started

- [ ] Refund handling runbook
- [ ] Account recovery runbook (user can't access email, lost OTP, etc.)
- [ ] GDPR data subject request fulfillment runbook
- [ ] Subscription cancellation override runbook
- [ ] Safety escalation runbook (crisis classifier fires, user reports concerning content)

## 2.3 Infrastructure P0

### A. DNS configuration for `thegreatminds.app`

Status: 🟡 IN PROGRESS this session

- [ ] DNS records configured at registrar (A/AAAA, MX, SPF/DKIM/DMARC TXT, CNAME)
- [ ] SSL provisioning (probably automatic via Netlify/registrar)
- [ ] Netlify domain attachment

### B. Resend domain verification

Status: 🟡 IN PROGRESS (depends on DNS)

- [ ] Add `thegreatminds.app` to Resend dashboard
- [ ] Add DNS records Resend provides
- [ ] Wait propagation (5-30 min)
- [ ] Click "Verify DNS Records" in Resend dashboard
- [ ] Switch `FROM_EMAIL` env var on Render to `noreply@thegreatminds.app` or `hello@thegreatminds.app`
- [ ] Set sender display name "Great Minds" in Resend dashboard

### C. Stripe verification

Status: 🟡 calendar gate passed (2026-05-11), status unverified

- [ ] Verify Stripe account status (cooldown period was ~10 days from 2026-05-01)
- [ ] If still paused, contact Stripe support
- [ ] If active, plan products/prices structure before Block H work
- [ ] Test mode integration verification

### D. Render API plan upgrade

Status: 🔴 not started
Priority: **P1 / pre-UAT recommended**, not a strict launch blocker unless cold starts harm tester experience.

- [ ] Decide on plan tier (recommendation: $7/mo Starter to eliminate cold-start)
- [ ] Apply upgrade
- [ ] Verify `WEB_CONCURRENCY` setting (currently 1; may bump to 2 with paid tier)

### E. Production smoke test

Status: 🔴 not started (must run after polish PR closes Block B)

- [ ] Incognito / fresh browser sign-up
- [ ] All 9 personas visible and selectable
- [ ] Full Block A flow (signup → OTP → disclaimer)
- [ ] Full Block B flow (welcome → themes → need → matches → persona detail)
- [ ] Block C flow (when shipped) — start conversation with each tier of persona
- [ ] Chat response latency acceptable
- [ ] Safety crisis path suppresses persona voice
- [ ] No duplicate conversation creation
- [ ] No persona response truncation
- [ ] OTP rate limiter still working
- [ ] PHENOMENOLOGY_BRIDGE_ENABLED verified true

### F. `PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation

Status: 🔴 not done

Was verified true during 14-test session 2026-05-04/05. Current state in Render env vars unverified. Confirm before public launch.

## 2.4 RLS Audit P0 (forward-looking)

Status: 🔴 not started

All 17 public Supabase tables: RLS disabled. Mitigated by frontend going exclusively through FastAPI gateway (no Supabase anon key in frontend bundle).

⚠️ **Critical forward-looking warning:** If a future change ever introduces Supabase anon key on the frontend (e.g., for a "quick" Supabase realtime feature, direct client query from React, Supabase Auth replacement), RLS becomes a critical vulnerability the moment that ships. **Always add explicit RLS policies BEFORE any such change merges.**

Action item for pre-launch:
- [ ] Add explicit RLS policies to all 17 tables as a defense-in-depth measure (even with FastAPI gateway in place, RLS provides protection if gateway is bypassed or misconfigured)
- [ ] Document the RLS state for each table in a single source-of-truth doc

## 2.5 UAT P0

Status: 🔴 not started

- [ ] Identify 3-5 mixed testers (close + acquaintances + strangers)
- [ ] Distribute access (when DNS is live)
- [ ] Collect spontaneous "I'd pay" signal
- [ ] Decision gate: ≥2/5 → public launch; <2/5 → iterate before launch

---

# 3. Database schemas

See `PROJECT_STATE_v8.md` §4 for current state. Current docs report **17 public tables** and alembic_version `006_add_new_personas`; exact table count should be verified via Supabase before RLS implementation because v7→v8 arithmetic only clearly explains +1 table (`user_preferences`) after the v7 15-table state.

---

# 4. Config & Environment Variables

See `PROJECT_STATE_v8.md` §8 for current Render + Netlify env vars.

**Pending env var changes:**
- Render: `FROM_EMAIL` → `noreply@thegreatminds.app` (after DNS + Resend verification)
- Render: `PHENOMENOLOGY_BRIDGE_ENABLED` → verify state, set explicitly to `true`
- Netlify: `NEXT_PUBLIC_SUPPORT_EMAIL` → `support@thegreatminds.app` (when mailbox exists)

---

# 5. Stripe Wiring (P0)

Status: 🔴 not wired. Calendar gate of 2026-05-11 passed.

### 5.1 Required before Block H work
- [ ] Verify Stripe account active (not paused)
- [ ] Set up products + prices for tiers:
  - Free: 0€ — limited to free personas (currently Aurelius, Socrates, Lao Tzu)
  - Pro: **baseline preserved from v7/v5: €9.99/month and €119.99/year**, to be explicitly reconfirmed before H1 pricing implementation; currently unlocks **6** pro personas (Beauvoir, Epictetus, Jung, Wilde, Machiavelli, Freud)
  - Premium: schema-supported but no personas currently assigned; pricing/use case deferred until there is a concrete premium feature or persona reason
- [ ] Webhook endpoint URL: `https://philosopher-api-z9l9.onrender.com/api/v1/stripe/webhook` (TBD)
- [ ] Webhook events to handle: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
- [ ] Test mode integration verification

### 5.2 Backend work
- [ ] `apps/api/services/stripe_service.py` (create)
- [ ] `apps/api/routers/stripe.py` (create) — webhook handler + checkout session creation
- [ ] DB: `subscriptions` table (or extend `users` with subscription state)
- [ ] Entitlement check: `is_persona_accessible(user, persona)` — leverage existing tier matching from B6 paywall logic

### 5.3 Frontend work (Block H)
- [ ] H1-H6 screens per `SCREENS_TRACKING_v4`
- [ ] Stripe Checkout redirect or embedded form
- [ ] Upgrade CTAs in B6 paywall placeholder (currently `alert()`)
- [ ] Subscription management in account settings (Block I)

---

# 6. Persona-specific maintenance backlog (Section 5.7 framework)

### P2 — ChatGPT audit of new persona configs

Status: 🔴 not started (founder-owned)

- [ ] Run ChatGPT audit on Lao Tzu config
- [ ] Run ChatGPT audit on Oscar Wilde config
- [ ] Run ChatGPT audit on Niccolò Machiavelli config
- [ ] Run ChatGPT audit on Jung config (existed pre-session, now active — re-audit reasonable)
- [ ] Apply surgical UPDATE edits via JSONB `jsonb_set` for any findings (not full rewrites)

### P2 — Extract new personas to YAML

Status: 🔴 not started

Currently Lao Tzu, Wilde, Machiavelli live only as JSONB in `personas.config`. Original 6 have parallel YAML files in `apps/api/philosopher_brain/`. Source-parity gap.

- [ ] `apps/api/philosopher_brain/lao_tzu.yaml`
- [ ] `apps/api/philosopher_brain/oscar_wilde.yaml`
- [ ] `apps/api/philosopher_brain/niccolo_machiavelli.yaml`

### P2 — Portrait style harmonization

Status: 🔴 not started

Aurelius + Socrates are painterly outliers vs the 7 atmospheric/hybrid others. Re-generate Aurelius + Socrates in matching style.

### P2 — Premium tier reassignment (if desired)

Status: 🔴 not decided

Freud currently `pro`, but originally planned as `premium`. Tier exists in schema (used in `tier` column with check constraint), 0 personas assigned. Founder decision needed: leave as-is, or reassign Freud → premium (1-line SQL UPDATE)?

---

# 7. Future blocks reference

## 7.1 Block C (Chat experience) — next P0 after polish PR

5-8 PRs, 15-25 hours CC time. See HANDOFF_BRIEF_v8.md §24 for full scope.

**Architectural decisions required before C1 PR starts** (see HANDOFF_BRIEF_v8.md §24.3):
1. LLM provider — Claude vs GPT-4o vs mixed (mentor: Claude)
2. RAG — pgvector vs Pinecone (mentor: pgvector first)
3. Conversation memory window (mentor: rolling 20 + system_fragment)
4. Free tier message limits (mentor: 10/day per free persona)
5. Streaming — SSE vs WebSocket (mentor: SSE)
6. Safety filter cadence (mentor: every message)

## 7.2 Block D — Discovery (D1, D2, D3)

Not yet planned. After Block C.

## 7.3 Block F — Reflection (F1, F2, F3, F4, F6)

Not yet planned.

## 7.4 Block H — Subscription & Billing (H1-H6)

Depends on Stripe wiring. Likely runs parallel with Block C or immediately after.

## 7.5 Block I — Account & Settings (I1-I6)

Not yet planned.

## 7.6 Block J — Empty/error states (J1, J2, J3, J5)

Not yet planned. Often handled inline with other blocks.

---

# 8. Operating principles (preserved + extended)

### 8.1–8.13 — Preserved from v7 (summary; full text in HANDOFF_BRIEF_v8.md §19)

1. Full diffs, not grep summaries
2. Defense in depth over single fixes
3. Conftest.py owns credential stubs
4. message_count == 0 is correct empty signal
5. Cross-check HANDOFF status against PROJECT_STATE before publishing
6. Decision reversibility documentation
7. Build-time vs request-time Next.js semantics — Suspense for `useSearchParams`
8. Stamp + code order for alembic plumbing
9. Disconnect parallel deployments immediately
10. Stakes-aware mentoring requires explicit founder context (general principle preserved)
11. Trust-but-verify CC pushes via `git ls-remote`
12. Complete PR cycles before queuing new work
13. "Centered" means both layout-centered AND text-aligned-center

### 8.14 — Unicode encoding in JSONB migrations (NEW v8 — 2026-05-13)

Any migration that serializes Python dicts to JSONB with non-ASCII characters must pass this pre-merge check:

```python
import json
test_json = json.dumps(YOUR_CONFIG, ensure_ascii=False)
test_json.encode('utf-8')  # Must NOT raise UnicodeEncodeError
```

For user-visible Unicode (emojis): use **literal characters** in source (`"🗡️"`) or **proper escapes for codepoints above BMP** (`"\U0001F5E1"`). Never use surrogate pair representations (`"\ud83d\udde1"`) outside JSON string literals.

### 8.15 — Mobile walkthrough is non-substitutable (NEW v8)

Visual fixes targeting mobile Safari must be verified on actual mobile Safari before merge. Desktop browser DevTools or static rendered mockups are insufficient. 2 minutes via Netlify QR code preview. Cost of skipping: PR doesn't actually fix what it claimed.

### 8.16 — Read existing docs before writing replacement docs (NEW v8)

When writing a doc marked "supersedes vN", read vN in full first. Working from thread memory is reckless documentation. Thread memory provides illusion of completeness that masks real gaps.

### 8.17 — Addendum vs baseline regen (NEW v8)

Honor the addendum pattern for mid-block deltas. Reserve baseline regen for end-of-block closure (Block A → v6, Block B → v8, Block C → v9, etc.). Addendum file naming: `*_vN_ADDENDUM_<date>.md`.

---

# 9. Backlog by priority (consolidated)

## 9.1 P0 (launch blockers)

- [ ] **Consolidated polish PR** (visually closes Block B)
- [ ] **Lawyer review** of Terms / Privacy / disclaimer
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure** (LLM provider DPA, processors doc, request fulfillment workflow)
- [ ] **Stripe wiring** (Block H + backend service)
- [ ] **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety escalation)
- [ ] **Production smoke test** post-polish-PR
- [ ] **PHENOMENOLOGY_BRIDGE_ENABLED flag state confirmation**
- [ ] **RLS policies** added defense-in-depth (even with FastAPI gateway)
- [ ] **UAT** with 3-5 testers, ≥2/5 spontaneous "I'd pay"
- [ ] **Block C — Chat** (next P0 after polish PR; 5-8 PRs, 15-25 hours)
- [ ] **Blocks D, F, H, I, J** — 34 remaining UI line-items

## 9.2 P1

- [ ] **A6+A7 disclaimer endpoint integration tests** (shipped without tests for speed)
- [ ] **A6+A7 lazy-load monitoring** — watch for `MissingGreenlet` in Render logs
- [ ] **A4 mailto visible support email fallback** — when real `support@thegreatminds.app` mailbox exists
- [ ] **Block C architectural decisions surfacing** (6 decisions in §7.1 / `HANDOFF_BRIEF_v8.md` §24.3)
- [ ] **Render API plan upgrade** (~$7/mo to eliminate cold-start)
- [ ] **API plan upgrade decision** confirmed before UAT (founder hit on first user testing impression)

## 9.3 P2

- [ ] **ChatGPT audit of new persona configs** → surgical JSONB UPDATE edits (founder-owned)
- [ ] **Portrait style harmonization** — Aurelius + Socrates re-generate
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML** in `apps/api/philosopher_brain/`
- [ ] **Premium tier reassignment** if desired (Freud → premium; 1-line UPDATE)
- [ ] **B1 hydration polish** — 0.5s flash before auth-guard redirect
- [ ] **Document Render alembic auto-run mechanism** — find where it's wired
- [ ] **Local Python venv for founder** (Windows-friendly) — would prevent another #43 emoji disaster
- [ ] **B5/B6 spec drift correction** — current implementation diverges from SCREENS_TRACKING § B5: (1) name + tagline render below portrait instead of above; (2) portrait is full-bleed hero (62vh) instead of 4:3 card with Edge border + 6px radius; (3) cream section shows bio + CTA instead of About / Best for / Why this mind may help blocks. Working state; not a launch blocker. Defer until UAT signals whether the drift hurts conversion.

## 9.4 P3

- [ ] **Desktop layout polish** — mobile-first looks broken >768px
- [ ] **Phase 5 register architecture + UI chips + classifier** — post-feedback
- [ ] **Phase 6 eval suite + CI** — post-revenue
- [ ] **A5 polish** — close/remove after consolidated polish PR if 6-digit OTP boxes ship there
- [ ] **Phase 4 PR Β** (Marcus shading content, 33 strings) — post-launch
- [ ] **Phase 4 follow-up items**: #26 runtime template rendering, #27 phenomenology priority hints, #28 modern-term-leak post-check

## 9.5 P4

- [ ] **Render `philosopher-db` decommissioning verification** — carry-forward from v6/v7. Old DB possibly still costing money.
- [ ] **`apps/api/scripts/` decision** — gitignore, commit, or delete
- [ ] **Stale branch cleanup** — periodic batch
- [ ] **gh CLI install on founder's Windows**
- [ ] **Legal pages `target="_blank"` rel hardening** — explicit noopener noreferrer
- [ ] **Untracked v6/v7 docs cleanup** — commit as historical archive or delete
- [ ] **`make state` infrastructure broken** — `claude` CLI mismatch with founder's VS Code workflow. Fix deferred until post-first-payment.
- [ ] **HANDOFF_BRIEF_v7.md deletion** — pending in local working tree (stashed during polish PR session to avoid scope creep). Intentional per v8 baseline regen ("Removed during v8 cycle"). Commit separately on main when convenient.

---

# 10. Plan A vs Plan B (preserved)

### 10.1 Plan A — 43-screen build before launch (ACTIVE)

Founder's 2026-05-06 decision, reconfirmed 2026-05-10. Build all 43 specced screens, then UAT, then public launch.

**Remaining work surfaces** in priority order:
1. Polish PR (closes Block B visually)
2. Block C (chat)
3. Block D (Discovery)
4. Block F (Reflection)
5. Stripe wiring + Block H (Billing)
6. Block I (Settings)
7. Block J (Empty states)
8. Lawyer review + GDPR/DPA + Founder runbooks (in parallel)
9. UAT
10. Public launch

### 10.2 Plan B — Minimum-to-revenue interrupt (PRESERVED, NOT ACTIVE)

Alternative path. Available as pivot if circumstances change. Sequence:
1. Polish PR (still needed)
2. Block C subset (chat only, no Discovery/Reflection)
3. Stripe wiring + Block H subset (paywall enforcement, single tier)
4. Lawyer review (still needed)
5. Limited UAT
6. Launch with minimum viable product
7. Iterate on signal

**Plan B triggers (when mentor will re-raise):**
- UAT signal returns <2/5 spontaneous "I'd pay"
- Stripe wiring slips beyond Block C completion
- Block C time exceeds 3x estimate
- Founder explicit pivot trigger

---

# 11. KIEN — separate project note

Founder also runs **KIEN** — AI companion SaaS — as separate codebase + product. Not to be confused with Philosopher / Great Minds.

**KIEN-specific concerns NOT in this backlog:**
- Supabase Data API default change (May 30 2026) — affects KIEN (uses supabase-js), NOT Philosopher (uses asyncpg direct)
- n8n workflow updates
- Stripe pricing tier decisions for KIEN
- Narrative endings for KIEN personas (Amber, Rei)

This v8 file is **Philosopher-only**. Cross-references to KIEN should remain only as separation reminders.

---

**End of IMPLEMENTATION_BACKLOG v8.** Authoritative as of 2026-05-13/14 session close. Replaces `IMPLEMENTATION_BACKLOG_v7.md`.
