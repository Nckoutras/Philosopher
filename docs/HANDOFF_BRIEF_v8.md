# HANDOFF BRIEF v8 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + mentor instance
**Date updated:** 2026-05-13/14
**Prior version:** `docs/HANDOFF_BRIEF_v7.md` (2026-05-10) + `PROJECT_STATE_v7_ADDENDUM_2026_05_11.md`
**Block trigger for v8 baseline regen:** Per v7 §25 mentor advice, baseline regen warranted when Block B closes. Block B functional spine shipped via 11 PRs this session. Block B is **not visually/QA-closed** until the consolidated polish PR ships and is verified on real mobile devices, but spine completion is a sufficient regen trigger.

**Status:** Phase 3 ✅ closed. Phase 4 ✅ closed. Phase 4 stabilization sequence ✅ closed. Setup PR + Greenfield scaffold ✅ closed. **Block A — Authentication ✅ FULLY CLOSED (5/5 line items, 2026-05-10).** Legal pages ✅ shipped as templates (2026-05-10, lawyer review pending P0). Vercel parallel deployment ✅ disconnected (2026-05-10). **Design System v4→v5 migration ✅ shipped (2026-05-11). Block B — Onboarding spine ✅ SHIPPED in production (11 PRs, 2026-05-13).** 9 personas now live in production (was 6). **Consolidated polish PR pending** to visually close Block B. Phase 5 P3 post-feedback. Phase 6 P1 post-revenue. **43-screen UI build remains the P0 work surface; Block A 5/5 done, Block B 6/6 functional spine done, Block C (chat) next. Plan A active. Web/PWA only for v1.**

> **v8 conflict resolution rule:** Where v8 conflicts with v7 or v7 addendum, v8 wins. Production reality always wins over docs.

> **Correction note (2026-05-14):** This copy includes a consistency pass against v7/v7 addendum and the v8 companion docs. Key corrections: Block B wording is now “functional spine shipped / visual QA pending,” Block C is consistently “Chat experience,” existing conversation/message tables are not treated as greenfield, and DNS/Resend dependencies are separated from code-only polish work.

---

## Changelog v7 → v8

### 2026-05-11 session — Design System v4→v5 palette migration (from v7 addendum)

- Warmer palette restored to align with original 1-May editorial vision after silent drift discovered
- 5 files updated in single commit (`d018bcf`); 24 insertions, 17 deletions
- New tokens: `White #FFFFFF`, `shadow-card`, `shadow-card-hover`
- `Rust` renamed to `Safety #7A4030`; dead `gold` token removed
- Block A backfilled with v5 tokens in same commit
- Design System spec committed to repo for first time (was Claude.ai project knowledge only — single-point-of-failure eliminated)
- Branch hygiene lesson: never reuse squash-merged branches; create fresh off main

### 2026-05-13 session — Block B onboarding spine + 4 new personas

**11 production-merged PRs in ~14 hours sustained focus session. 1 hotfix (production deploy incident, recovered cleanly). Zero data corruption.**

#### A. Block B strategic decisions resolved
4 decisions from v7 §24 resolved at session start:
1. **B2/B3 persistence:** Backend persistence to `user_preferences` table (alembic 004, wide-table)
2. **Matching algorithm:** Backend-computed via `matching_service.py`
3. **B6 timing:** Built now as variant of B5 (Pro-locked UI placeholder; paywall enforcement logic in place, no Stripe yet)
4. **`user_preferences` schema shape:** Wide table

#### B. Block B PRs merged

| PR | Title | Notes |
|---|---|---|
| #33 | `feat(api): user_preferences migration 004 + endpoints` | Pre-session foundation |
| #34 | `feat(web): B1 welcome + persona portrait rotation` | Pre-session |
| #36 | `fix(web): B1 portrait positioning v4` | zoom 1.3x + object-top fix; did NOT solve all cases — verified failed on mobile walkthrough |
| #37 | `feat(web): B2 themes selection screen` | Multi-select chips with toggle state |
| #38 | `feat(web): B3 need_most + POST /api/v1/preferences` | One ApiClient pattern violation, fixed via amend + force-push pre-merge |
| #39 | `feat(api): matching service + GET /api/v1/preferences/matches` | `PERSONA_AFFINITIES` dict + `EXCLUDED_SLUGS` set |
| #40 | `feat(web): B4 best matches list` | Top-3 ranked, navigates to B5/B6 |
| #41 | `feat(web): B5+B6 persona detail page` | Free personas show full detail; pro/premium show paywall placeholder via `alert()` |
| #42 | `refactor(api+web): move persona bio + portrait_url to backend` | Extracted `PORTRAIT_PATHS` + `BIOS` dicts; added bio + portrait_url columns via alembic 005 |
| #43 | `feat(api): add 3 new personas + activate Carl Jung` | Lao Tzu (free), Wilde (pro), Machiavelli (pro) via alembic 006 + bio/portrait for Jung |
| #44 | `hotfix(api): migration 006 Machiavelli emoji surrogate encoding` | UTF-16 surrogate pair crashed alembic in Render deploy loop; fixed with literal Unicode codepoint |

**Total:** 11 PRs + 1 hotfix. Block B 6/6 functional spine shipped. 9 personas live.

#### C. New personas — content authored

All 4 new persona configs (Lao Tzu, Wilde, Machiavelli, Jung) authored by Claude assistant in session, founder approved without audit. Each has full Section 5.7-style character config in `personas.config` JSONB:
- system_fragment (~1500 chars character prompt)
- tone, worldview, sentence_structure
- challenge_style, challenge_level (3-4), questioning_pattern
- vocabulary_register, response_length
- forbidden_phrases (AI clichés + persona-specific)
- retrieval_sources (for RAG when Block C ships)
- opening_invocation, tagline, avatar_emoji
- behavior knobs

**Behavioral fields are DORMANT** until Block C (chat) ships. Only visible UI fields (tagline, opening_invocation, bio, portrait) render in current screens.

**Tier assignments:** Lao Tzu = free, Wilde = pro, Machiavelli = pro, Jung activated as pro. Freud remains pro (was originally planned as premium; tier exists in schema, no personas assigned — 1-line UPDATE if desired).

**Affinity weight signatures:**
- **Lao Tzu** → anxiety/acceptance + need=comfort
- **Wilde** → balanced, surfaces for relationships theme
- **Machiavelli** → work/purpose + need=challenge or practical (zero comfort weight, deliberate)
- **Jung** → relationships/purpose + need=interpretation

**Founder action pending:** ChatGPT audit of new persona configs → surgical UPDATE edits via JSONB `jsonb_set` (no rewrites planned).

#### D. Mobile walkthrough findings (founder, 2026-05-14 morning)

Founder did fresh mobile incognito walkthrough after Block B shipping. Found 9 issues:

**Critical (broken functionality):**
1. **Portraits don't load anywhere** (welcome mind-of-the-day, matches thumbnails, persona detail header). DB has correct paths, files exist in `apps/web/public/personas/`, but rendering fails. Suspected: PR #42 refactor broke `persona.portrait_url` flow from backend → frontend Image component
2. **OTP email fails** for `nkoutr@ote.gr` ("we could not send the code"). Corporate domain likely blocks generic Resend sender
3. **Refresh on welcome error page** → redirects to disclaimer instead of retrying same page

**Important (UX issues):**
4. Hero text "Great Minds" + subtitle "Reflect with the greatest thinkers" partially unreadable — sits on persona face, white-on-light contrast issue. v4 zoom fix did not solve underlying problem on tight-composition portraits like Socrates
5. "Explore Minds" secondary button cropped by iOS Safari toolbar (no `safe-area-inset-bottom`)

**Polish:**
6. No iOS rubber-band bounce-back scroll
7. Push buttons lack `:active` press feedback animation
8. OTP input is single field; founder wants 6 separate boxes (modern auth UX)
9. Resend sender display name "Philosopher" — should be "Great Minds" (also requires custom domain)

#### E. Decisions taken on mobile findings

- **Hero text style (Decision A):** Option B style (white text + drop shadow + dark gradient overlay), with **regular weight serif** (V2 variant). Wider text layout (~85-90% frame width). Larger font size.
- **Email domain (Decision B):** `thegreatminds.app` — founder-owned custom domain. DNS + Resend domain verification setup in progress at session end.
- **Polish scope (Decision C):** Full polish (all 9 findings fixed in one consolidated PR). Founder explicit: "θελω να φτιαξουμε ολα τα ευρηματα."

#### F. Production incident + recovery (hotfix PR #44)

PR #43 merged with corrupted emoji encoding in MACHIAVELLI_CONFIG (`\ud83d\udde1\ufe0f` lone surrogate pair). asyncpg JSONB encoder fails on lone surrogates → alembic upgrade crash → Render container restart loop ~20 min. No user impact (no production users). DB transaction rolled back atomically — no data corruption, alembic_version stayed at 005.

Hotfix PR #44: 1-line fix replacing surrogate pair with literal codepoint `🗡\ufe0f`. Founder force-merged (Netlify checks queued, frontend unchanged in this PR). Render rebuilt successfully, alembic ran clean on retry, all 9 personas confirmed in production.

### Inherited pending from v7 (still open)

- Custom domain `thegreatminds.app` DNS setup IN PROGRESS (Resend verification dependent)
- Render API plan upgrade decision (free tier still active)
- Stripe wiring (calendar gate of 2026-05-11 passed; status not verified this session)
- `PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation
- **Lawyer review of legal templates** (P0 launch blocker — templates only)
- RLS audit on Supabase (now 17 tables; all disabled, mitigated by FastAPI gateway)

### New items introduced this session

- **Consolidated polish PR** (P1, blocks Block B visual closure)
- **Block C planning** (P0 once polish PR merges)
- **ChatGPT audit of new persona configs** (P2, founder owns)
- **Portrait style harmonization** (P2) — Aurelius + Socrates painterly outliers vs 7 atmospheric/hybrid others
- **Premium tier reassignment** if desired (P2) — Freud currently `pro`
- **Render alembic auto-run mechanism docs** (P2) — works in production but mechanism undocumented
- **Render `philosopher-db` decommissioning verification** (P4, carry-forward from v6)

---

## 1–14 — UNCHANGED FROM v1/v2/v3

Sections 1 through 14 deliberately not reproduced. Retrieve from git history if needed.

---

## 15. SECTION 5.7 FRAMEWORK — STATUS UNCHANGED FROM v7

§15.1 – §15.4 unchanged.

### 15.5 Implementation status (updated 2026-05-13 — now spans 9 personas, was 6)

| Element | Status |
|---|---|
| Character anchors (schema) | ✅ Optional field on PersonaConfig |
| Character anchors (data) | ✅ Populated for **6 original** (PR #7-12) + **3 new** (PR #43) + **Jung activated** |
| Register architecture (schema) | ✅ RegisterRange + RegisterOverride dataclasses |
| Register architecture (data + classifier) | ⏳ Original 6 populated; new 3 use flat config (no behavioral_parameters_by_register); runtime UI chip selection + classifier deferred to **P3 post-feedback** |
| Brevity discipline (schema) | ✅ ResponseLengthSpec 4-mode dataclass |
| Brevity discipline (runtime check) | ✅ check_brevity() + 3-layer sentence-boundary fix (`2bf9244`) |
| Anti-flexing (schema) | ✅ AntiFlexingRules dataclass |
| Anti-flexing (data + enforcement) | ✅ Populated for all 9 personas; postchecked |
| Modern phenomenology bridge | ✅ Infrastructure shipped + 78 entries + 14-test verification. `PHENOMENOLOGY_BRIDGE_ENABLED` flag to confirm in Render env before launch |
| Universal forbidden lexicon (runtime) | ✅ Live via check_universal_forbidden() |
| Persona-specific forbidden (schema + data) | ✅ Populated for all 9 personas |
| Eval suite | ⏳ Reclassified to **P1 post-revenue** |

**Critical context for next instance:** all Section 5.7 infrastructure is **already live in production** for all 9 personas. It is NOT "future Block C work" — it is running behavior. Block C builds chat-runtime ON TOP OF this existing brain framework.

---

## 16. MIGRATION PLAN — STATUS UNCHANGED FROM v7

§16.1, §16.3, §16.4, §16.5 unchanged from v3.

### 16.2 Six-phase plan — implementation status

**Phases 1-3** ✅ COMPLETE + MERGED 2026-05-02 to 2026-05-04 (PRs #7-12).
**Phase 4 — Modern phenomenology bridge** ✅ COMPLETE + IN PRODUCTION (`PHENOMENOLOGY_BRIDGE_ENABLED` flag state to confirm in Render env)
**Phase 5 — Register architecture + UI chips + classifier** ⏳ P3 post-feedback
**Phase 6 — Eval suite + CI** ⏳ P1 post-revenue

---

## 17. NEXT WORK SURFACE — 43-SCREEN UI BUILD (UPDATED v8)

### 17.1 Phase 4 stabilization sequence — CLOSED 2026-05-05

8 items closed. Do not reopen unless a launch test fails.

### 17.1.5 Setup PR + Greenfield scaffold — CLOSED 2026-05-07

### 17.1.6 Block A — Authentication — ✅ FULLY CLOSED 2026-05-10 (5/5)

| Screen | PR | Status |
|---|---|---|
| A1 — Splash | #15 | ✅ live |
| A2 / A3 — Sign-in (email entry) | #17 | ✅ live |
| A4 — Trouble accessing email | #22, #23, + text-center fix | ✅ live |
| A5 — Verify (OTP entry) | #20 | ✅ live; per-digit boxes polish queued in upcoming polish PR |
| A6+A7 — Combined disclaimer | #24 schema, #25 backend, #26 frontend | ✅ live |

**Auth flow architecture (correcting v7 ambiguity):** Auth is **passwordless OTP-first**. No traditional email+password endpoints exist for users. Flow: email entry → POST `/auth/otp/request` (202) → 6-digit code via Resend → POST `/auth/otp/verify` (200 with JWT) → if `needs_disclaimer` then `/auth/disclaimer` → else `/app/welcome`.

### 17.1.7 Block B — Onboarding spine — ✅ SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

| Screen | PR | Status |
|---|---|---|
| B1 — Welcome (Mind of the day) | #34, #36 | ✅ shipped; portrait positioning issue handled in polish PR |
| B2 — "What brings you here?" | #37 | ✅ shipped |
| B3 — "What do you need most?" | #38 | ✅ shipped |
| B4 — Best matches (top-3) | #40 | ✅ shipped |
| B5 — Persona detail (free) | #41 | ✅ shipped |
| B6 — Persona detail (Pro-locked variant) | #41 | ✅ shipped; paywall via `alert()` until Stripe |

**Status caveat:** Block B functional spine is **shipped**, not visually/QA-closed. Visual closure pending consolidated polish PR (see §27).

### 17.2 Block-by-block remaining work

| Block | Scope | Items | Status |
|---|---|---|---|
| **A** | Authentication | A1, A2/A3, A4, A5, A6+A7 | **✅ 5/5 LIVE** |
| **B** | Onboarding | B1–B6 | **🟡 6/6 spine SHIPPED**; polish PR pending |
| **C** | Chat experience | C1–C9 | ❌ Not started — **NEXT P0** after polish PR |
| **D** | Discovery | D1, D2, D3 | ❌ Not started |
| **F** | Reflection | F1–F6 | ❌ Not started |
| **H** | Subscription & Billing | H1–H6 | ❌ Not started — Stripe wiring depends |
| **I** | Account & Settings | I1–I6 | ❌ Not started |
| **J** | Empty/error states | J1, J2, J3, J5 | ❌ Not started |

**Total: 43 effective screens (45 line items). 11 of 45 closed** (A 5/5 + B 6/6 spine). 34 remaining.

### 17.2.5 Plan A/B Fork — Plan A ACTIVE

**Plan A — 43-screen sequence** (founder's 2026-05-06 decision, reconfirmed 2026-05-10). Active. Next: polish PR → Block C → Block D → ...

**Plan B — Minimum-to-revenue interrupt** (preserved, NOT active). Available as pivot if circumstances change.

**Mentor reserves right to re-raise Plan B if:**
- UAT signal returns <2/5 spontaneous "I'd pay"
- Stripe wiring slips beyond Block C completion
- Block C time exceeds 3x estimate
- Founder explicit pivot trigger

### 17.3 Calendar-gated parallel work

- **Stripe wiring** — calendar gate of 2026-05-11 passed. Verify status before any H block work
- **Legal templates** ✅ shipped. **Lawyer review still REQUIRED** before public launch (P0 — Greek consumer law, Stripe billing T&Cs, AI-content liability)
- **Email infrastructure** — Resend custom domain verification for `thegreatminds.app` IN PROGRESS
- **DNS configuration** for `thegreatminds.app` IN PROGRESS
- **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation. Parallelizable

### 17.4 Pre-launch verification (after UI complete)

- Production smoke test (Phase 4 items + all 43 screens)
- Confirm `PHENOMENOLOGY_BRIDGE_ENABLED` flag state in Render env
- UAT with 3-5 mixed testers
- Decision gate: ≥2/5 spontaneous "I'd pay" → public launch
- **Block A/B specific:** verify auth + onboarding flow on `thegreatminds.app` once DNS live, FROM_EMAIL switched to verified domain sender
- **Block B specific:** verify polish PR fixes on real iOS Safari, not desktop preview

---

## 18. CLAUDE.AI PROJECT KNOWLEDGE — STATUS (UPDATED v8)

### Files currently in Claude.ai Project Knowledge

Top-level state and continuity docs:
- `PHILOSOPHER.docx` — product spec
- **`HANDOFF_BRIEF_v8.md` — THIS document (replaces v7)**
- **`PROJECT_STATE_v8.md` — live state snapshot (replaces v7 + addendum)**
- **`IMPLEMENTATION_BACKLOG_v8.md` — backlog source of truth (replaces v7)**

UX design docs (active):
- `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` (now in repo too)
- `SCREENS_TRACKING_v4.md` — needs v5 update post-polish PR
- `USER_FLOW_v4.md`

Brain content (Section 5.7 design source — also in repo at `apps/api/philosopher_brain/`):
- 6 active original persona YAMLs (Aurelius, Socrates, Beauvoir, Epictetus, Freud, Jung) plus preserved Nietzsche YAML/backend config (Nietzsche removed from frontend)
- `modern_phenomenology.json` (78 entries)
- `persona_specific_forbidden.json`, `universal_forbidden_lexicon.json`
- `master_system_prompt.md`, `eval_suite_spec.md`, `ten_modern_problems.json`

**To consider adding (P2):** YAML extracts for Lao Tzu / Wilde / Machiavelli currently live only as JSONB in `personas.config`. Consider extracting to YAML for source-parity with original 6.

**Removed during v8 cycle:**
- `HANDOFF_BRIEF_v7.md`, `PROJECT_STATE_v7.md` + addendum, `IMPLEMENTATION_BACKLOG_v7.md` — all superseded

---

## 19. SESSION LESSONS

### 19.1–19.13 — Preserved from v7 (summary)

Full text in `HANDOFF_BRIEF_v7.md` if reference needed.

1. **19.1 Full diffs, not grep summaries** — paste full diffs for all callers on parameter/schema changes
2. **19.2 Defense in depth over single fixes** — layer independent defenses
3. **19.3 Conftest.py owns credential stubs** — dummy env vars before test imports
4. **19.4 message_count == 0 is correct empty signal**
5. **19.5 Cross-check HANDOFF status against PROJECT_STATE before publishing**
6. **19.6 Decision reversibility documentation**
7. **19.7 Build-time vs request-time Next.js semantics** — Suspense for `useSearchParams`
8. **19.8 Stamp + code order for alembic plumbing** — stamp AFTER code change
9. **19.9 Disconnect parallel deployments immediately**
10. **19.10 Stakes-aware mentoring requires explicit founder context** — general principle preserved; no specific stakes content carried forward in v8
11. **19.11 Trust-but-verify CC pushes via `git ls-remote`**
12. **19.12 Complete PR cycles before queuing new work**
13. **19.13 "Centered" means both layout-centered AND text-aligned-center**

### 19.14 Unicode encoding in JSONB migrations (NEW v8 — 2026-05-13)

PR #43 broke production because MACHIAVELLI_CONFIG `avatar_emoji` was written as UTF-16 surrogate pair `"\ud83d\udde1\ufe0f"`. Python source-accepts this; asyncpg JSONB encoder calls `str.encode('utf-8')` which fails: `surrogates not allowed`. Alembic upgrade crashed → Render restart loop 20 min.

**Rule:** Any migration that serializes Python dicts to JSONB with non-ASCII characters must pass this pre-merge check:

```python
import json
test_json = json.dumps(YOUR_CONFIG, ensure_ascii=False)
test_json.encode('utf-8')  # Must NOT raise UnicodeEncodeError
```

For user-visible Unicode (emojis): use **literal characters** in source (`"🗡️"`) or **proper escapes for codepoints above BMP** (`"\U0001F5E1"`). Never use surrogate pair representations outside JSON string literals.

### 19.15 Mobile walkthrough is non-substitutable (NEW v8 — 2026-05-13)

PR #36 shipped a "B1 portrait positioning fix" verified via PIL desktop mockups. Mobile walkthrough revealed the fix did not solve the problem in iOS Safari for tight-composition portraits like Socrates. Different viewport, different CSS engine, different `svh` semantics with dynamic toolbar.

**Rule:** Visual fixes targeting mobile Safari must be verified on actual mobile Safari before merge. 2 minutes via Netlify QR code preview. Cost of skipping: PR doesn't actually fix what it claimed.

### 19.16 Read existing docs before writing replacement docs (NEW v8 — 2026-05-13)

This v8 baseline was written in two passes. First pass: drafted from thread memory + intuition, did NOT read v7 content. ChatGPT audit (run by founder) caught multiple critical omissions. Second pass (this version): read v7 + v7 addendum first, then wrote.

**Rule:** When writing a doc marked "supersedes vN", read vN in full first. Working from thread memory is reckless documentation. Thread memory provides illusion of completeness that masks real gaps.

### 19.17 Addendum vs baseline regen (NEW v8 — 2026-05-13)

v7 §25 advised: "v7 should be the last full rewrite until Block B closes. Subsequent sessions append to addendum file without rewriting baselines. Only regenerate baseline when (a) Block B closes, (b) Stripe lands, or (c) addendum exceeds ~30% of baseline length."

v8 baseline regen is warranted because Block B functional spine closed. The addendum pattern (`PROJECT_STATE_v7_ADDENDUM_2026_05_11.md`) was a valid alternative that was almost used instead. Founder explicit instruction overrode §25 advice in favor of full rewrite.

**Rule going forward:** Honor addendum pattern for mid-block deltas. Reserve baseline regen for end-of-block closure (Block A → v6, Block B → v8, Block C → v9, etc.).

---

## 20. DEPLOYMENT READINESS — STATUS (UPDATED v8)

### Live infrastructure

```
✅ Backend                Render web service philosopher-api
                          srv-d7ijct6gvqtc739a0pdg
                          philosopher-api-z9l9.onrender.com
                          ⚠️ Free tier; cold-start 30-60s after idle
                          ⚠️ Upgrade decision pending (~$7/mo)

✅ Database               Supabase project plecolxlzshkfvybszgs (eu-west-1, paid)
                          DATABASE_URL → aws-0-eu-west-1.pooler.supabase.com:5432
                          alembic_version = '006_add_new_personas'
                          17 public tables reported in v8 docs
                          (verify exact table count before RLS work)
                          RLS DISABLED on all
                          ⚠️ Mitigation: frontend goes through FastAPI exclusively
                             (anon key NOT in frontend bundle). If a future change
                             adds Supabase anon key to frontend (e.g., "quick"
                             realtime feature, direct client query from React),
                             RLS becomes a critical vulnerability IMMEDIATELY.
                             Always add explicit RLS policies before that ships.

✅ Cache (Redis)          Upstash philosopher-prod (eu-west-1) free tier
                          feasible-mammal-118733.upstash.io:6379
                          Rate limiter VERIFIED WORKING 2026-05-10

🟡 Email                  Resend free tier
                          FROM_EMAIL = "Great Minds <onboarding@resend.dev>"
                          ⚠️ Test sender — reliable only to founder's email
                          ⚠️ Corporate domains (ote.gr) block delivery
                          🟡 Custom domain thegreatminds.app DNS IN PROGRESS

✅ Frontend (canonical)   Netlify thinkalike.netlify.app
                          Auto-deploys from main

✅ Disclaimer flow        Live since 2026-05-10
✅ Onboarding flow        Live since 2026-05-13
                          GET /api/v1/preferences (auth)
                          POST /api/v1/preferences (auth) — save themes + need_most
                          GET /api/v1/preferences/matches (auth) — top-3 ranked

✅ Personas               9 personas live; all have config + bio + portrait_url
✅ Legal pages            /legal/terms, /legal/privacy — ⚠️ lawyer review REQUIRED before launch

❌ Frontend (legacy)      ~~Vercel thinkalike.vercel.app~~ DISCONNECTED 2026-05-10

🟡 Custom domain          thegreatminds.app registered 2026-05-07
                          DNS + SSL IN PROGRESS this session

❌ Stripe                 Not wired. Calendar gate 2026-05-11 passed; verify status

⏳ PHENOMENOLOGY_BRIDGE_ENABLED flag state in Render env
                          Confirmed true 2026-05-04/05; current state unverified
```

### Auth + onboarding pipeline — VERIFIED LIVE 2026-05-13

```
1.  /auth                                                                 ✓
2.  POST /api/v1/auth/otp/request                  →  202                 ✓
2a. Rate limiter (5/6min)                          →  429 (verified)      ✓
3.  Email delivered (test sender)                                         ✓
4.  /auth/verify?email=<encoded>                                          ✓
5.  POST /api/v1/auth/otp/verify                   →  200 (JWT)           ✓
6.  Response includes user.needs_disclaimer                               ✓
7.  Token persisted (localStorage + cookie, 7-day)                        ✓
8.  Zustand store updated                                                 ✓
9.  IF needs_disclaimer:  /auth/disclaimer                                ✓
10. POST /api/v1/disclaimer/accept                 →  200                 ✓
11. acceptance row written with audit fields                              ✓
12. Redirect to /app/welcome                                              ✓ (NEW 2026-05-13)
13. B1 (Mind of the day) → B2 (themes) → B3 (need) → B4 (matches) → B5/B6 ✓ (NEW 2026-05-13)
14. "Begin conversation" CTA                       →  404                 ❌ EXPECTED until Block C
```

---

## 21. DECISION HISTORY (EXTENDED v8)

### Preserved from v7 (chronological summary)

- 2026-05-04 evening — Engine-first execution decided
- 2026-05-05 — Phase 4 stabilization sequence closed
- 2026-05-06 — UI scope reversal: build all 43 screens before launch
- 2026-05-06 — Infrastructure: DB upgraded to paid tier
- 2026-05-07 — Greenfield UI rebuild + Netlify hosting confirmed
- 2026-05-08 — Block A backend infrastructure shipped
- 2026-05-09 — Block A frontend completion + alembic plumbing fix
- 2026-05-10 — Plan A confirmed; Block A 5/5 closed; Vercel disconnected; legal templates; OTP rate limiter verified
- 2026-05-10 — Block B 4 strategic decisions queued

### 2026-05-11 — Design system v4→v5 palette migration

- Warmer palette restored after silent drift; Block A backfilled
- Design system spec committed to repo for first time

### 2026-05-13 — Block B 4 strategic decisions resolved (NEW v8)

- B2/B3 persistence → backend
- Matching → backend
- B6 timing → built now as variant of B5
- `user_preferences` schema → wide table

### 2026-05-13 — Block B 6/6 functional spine shipped (NEW v8)

- 11 PRs merged + 1 hotfix in ~14 hours
- 9 personas now live (Lao Tzu free, Wilde pro, Machiavelli pro; Jung activated)
- Migrations 004, 005, 006 applied
- Production deploy incident recovered cleanly with no data corruption

### 2026-05-13 — Mobile walkthrough → consolidated polish PR planned (NEW v8)

- 9 findings categorized (3 critical, 2 important, 4 polish)
- Decision A: Hero text V2 style (white + shadow + gradient, regular weight serif)
- Decision B: `thegreatminds.app` for Resend custom domain
- Decision C: Full polish scope (one consolidated PR)

---

## 22. BLOCK A COMPLETION REPORT

Preserved verbatim in `HANDOFF_BRIEF_v7.md` §22. Block A is closed work — no expected modifications.

---

## 23. BLOCK B COMPLETION REPORT (NEW v8)

### 23.1 PRs merged

11 total this session. Key architectural moves:

- **User preferences persistence** (PR #33): wide-table `user_preferences` (alembic 004), columns for `themes` (JSONB array), `need_most` (varchar), timestamps. Idempotent upsert via `INSERT ... ON CONFLICT (user_id) DO UPDATE`.
- **Matching service** (PR #39): pure-Python in `apps/api/services/matching_service.py`. Two data structures:
  - `EXCLUDED_SLUGS: set[str]` — personas hidden from matching (now `set()`; was `{"carl_jung"}` until PR #43)
  - `PERSONA_AFFINITIES: dict[str, dict[str, dict[str, int]]]` — affinity weights per persona, scale 0-3 across themes + needs
  - Algorithm: for each persona, compute `sum(theme_weight * is_selected for theme in user.themes) + need_weight[user.need_most]`. Return top-3 sorted DESC.
- **Refactor PR #42 — backend-owned persona presentation:** `bio` (TEXT) + `portrait_url` (VARCHAR) columns added via alembic 005. Frontend hardcoded `PORTRAIT_PATHS` and `BIOS` dicts removed; UI reads from backend response.
  - **Known regression from mobile walkthrough:** portrait rendering broken on 3 surfaces. Root cause TBD in polish PR investigation.
- **New personas PR #43** + hotfix PR #44 — see §B in changelog.

### 23.2 Database state after Block B

```
alembic_version: 006_add_new_personas
public tables:   17 (was 15 — added user_preferences from 004)
personas count:  9   (was 6 — Lao Tzu, Wilde, Machiavelli added; Jung activated)
all personas:    bio + portrait_url populated
user_preferences: 1 row (test account)
```

### 23.3 Frontend routes added

```
/app/welcome              → B1 (Mind of the day)
/app/onboarding/themes    → B2
/app/onboarding/need      → B3
/app/onboarding/matches   → B4
/app/persona/[slug]       → B5 (free) or B6 (pro/premium with paywall placeholder)
```

### 23.4 Outstanding from Block B — handled by polish PR

- Portrait rendering broken (3 surfaces)
- Hero text contrast issue on B1 (V2 style)
- iOS Safari safe-area-inset-bottom missing
- Rubber-band scroll missing
- Push button press feedback missing
- OTP single field → 6-digit boxes (overlaps Block A backlog)
- Resend sender display name + custom domain switch (depends on DNS)
- Refresh-on-error redirect logic
- OTP email delivery to corporate domains (depends on DNS verification)

### 23.5 Outstanding from Block B — NOT in polish PR scope

- Aurelius + Socrates portrait style harmonization (P2)
- Premium tier reassignment if desired (P2)
- ChatGPT audit of new persona configs → surgical JSONB UPDATE edits (P2, founder-owned)
- B1 hydration flash (P3)
- Desktop layout polish (P3)

---

## 24. BLOCK C PLANNING (NEW v8)

Block C is the next P0 work surface after polish PR closes Block B visually. **Chat is the core product value** — the entire onboarding spine exists to deliver users to this experience.

### 24.1 Block C scope (estimated)

Block C is the largest single block by effort. **Not implementation-ready yet** — requires architectural decisions documented in §24.3 before PRs can start.

Estimated 5-8 PRs, 15-25 hours CC time:

| Item | Description |
|---|---|
| C1 | Verify/reuse existing `conversations` + `messages` tables (50 conversations / 139 messages already exist from prior engine work); add migrations only for gaps needed by current chat UX |
| C2 | LLM provider integration: API client, system prompt assembly from `persona.config.system_fragment` + history |
| C3 | RAG infrastructure: embedding pipeline, retrieval, top-k injection |
| C4 | Message endpoint (start non-streaming for velocity) |
| C5 | Chat UI frontend (chat screen, message list, input box, persona avatar header, opening invocation as first message) |
| C6 | Streaming response upgrade (SSE) |
| C7 | Safety filter integration (forbidden_phrases enforcement, crisis classifier) |
| C8 | Rate limiting (free tier message limits) |

### 24.2 Block C must leverage existing infrastructure

**Critical reminder:** Section 5.7 character framework is **already shipped** for all 9 personas. Block C does NOT rebuild character behavior — it composes runtime chat on top of it:

- `persona.config.system_fragment` → injected as system prompt prefix
- `persona.config.forbidden_phrases` → post-response filter
- `persona.config.retrieval_sources` → RAG corpus identifiers
- `persona.config.opening_invocation` → first message displayed to user
- `persona.config.tone`, `vocabulary_register`, `sentence_structure`, `challenge_style` → already encoded in system_fragment; do not re-parse client-side
- Universal forbidden lexicon + phenomenology bridge → already in `apps/api/philosopher_brain/`

### 24.3 Decisions REQUIRED before Block C PRs start

The next session must surface and resolve these BEFORE writing implementation briefs:

1. **LLM provider:** Claude (Anthropic) vs GPT-4o / GPT-4.1-mini / mixed. Mentor recommendation: Claude for the first paid-quality chat path — character quality is the differentiator for this product. Cost premium is acceptable only if paired with strict message limits and usage monitoring. Reconfirm current API pricing before final choice.
2. **RAG implementation:** pgvector (in current Supabase Postgres) vs Pinecone (separate service). Mentor recommendation: pgvector first (simpler ops, already paying for Supabase).
3. **Conversation memory:** how many messages to keep in context? Mentor recommendation: rolling last 20 messages + persona system_fragment.
4. **Free tier message limits:** Mentor recommendation: 10/day per free persona.
5. **Streaming UX:** SSE vs WebSocket? Mentor recommendation: SSE (simpler, no bidirectional needs).
6. **Multi-turn safety filters:** apply forbidden phrase / crisis / modern-term leakage checks on every assistant response or only first? Mentor recommendation: every assistant response; cheap checks, high brand-risk protection.

### 24.4 Block C is gated by polish PR closure

Do not start Block C until:
- Polish PR is merged
- Founder confirms visual Block B closure on actual mobile devices
- DNS for `thegreatminds.app` complete (OTP email works for non-founder testers)

---

## 25. CLOSING NOTE FOR NEXT INSTANCE

### Tone calibration

Founder uses ruthless mentor directive: no flattery, monetization-first filter on every recommendation, kill bad ideas, recommend alternatives. Match that style. Watch for energy-driven scope expansion. §19.12 (complete PR cycles before queuing new work) remains the active counterweight. Mentor enforces.

### Documentation hygiene

v8 baseline regen was triggered by Block B closure. Next baseline regen should wait for either Block C closure OR Stripe integration. Until then, append `*_v8_ADDENDUM_<date>.md` instead of rewriting v8.

### Plan B reconsideration triggers

Mentor will re-raise Plan B if:
- UAT signal returns <2/5 spontaneous "I'd pay"
- Stripe slips beyond Block C completion
- Block C exceeds 3x estimate
- Founder explicit pivot trigger

Document any trigger in §21 when it fires.

### Next session entry point

1. Confirm Plan A still active (default: yes)
2. **Track 1:** verify DNS + Resend domain setup complete
3. **Track 2:** verify CC investigation of portrait bug returned with root cause
4. **Write consolidated polish PR brief** covering all 9 mobile findings + V2 hero text + safe-area + bounce-back + button feedback + 6-digit OTP + sender name + refresh logic
5. After polish PR merges + visual verification: **Block C planning session** — resolve 6 decisions in §24.3 before any Block C PRs

### Wording precision (ChatGPT audit fix)

Block B is **functionally complete** but **not visually closed** until polish PR ships and is verified on real iOS Safari + reasonable Android. Distinguish in conversation — "Block B spine shipped, polish PR pending" vs "Block B fully closed" (only after polish PR merged + verified).

---

## END OF v8

**Where v8 conflicts with v7 or earlier, v8 wins.** §1-14 deliberately not duplicated.

**Next session entry point:** verify DNS + portrait bug investigation status, write polish PR brief, then Block C planning.

Authoritative as of 2026-05-13/14 session close. Replaces `HANDOFF_BRIEF_v7.md` + `PROJECT_STATE_v7_ADDENDUM_2026_05_11.md`.
