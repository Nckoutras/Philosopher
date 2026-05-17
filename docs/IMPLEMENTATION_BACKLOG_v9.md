# GREAT MINDS — Implementation Backlog v9

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v9 = v8 baseline (2026-05-13/14) + 2026-05-16 session delta (Block C backend complete; C-RECON reconciliation series complete; PATH B deleted; 10 architectural decisions locked; 8 tech debt items captured) + 2026-05-16/17 session delta (Block C frontend complete; C5a/b/c/d all merged; C3a RAG infrastructure merged; migration 008 deployed).**
>
> **Generated:** 2026-05-16 (post-reconciliation)
>
> **How to read this file:**
> - This v9 file supersedes v8 and all prior backlog files.
> - Where v9 conflicts with v8, v9 wins.
> - Historical Block C detail removed (complete); replaced with remaining C3 + C5 items.
> - Status, priority, and launch-readiness calls reflect 2026-05-17 state.
>
> **Last updated:** 2026-05-17. **Block C frontend 4/4 complete (C5a/b/c/d merged). C3a RAG infrastructure live (migration 008). C3b corpus ingestion READY (operational run pending).**
>
> **Companion documents:**
> - `PROJECT_STATE_v9.md` — current project state (replaces v8)
> - `HANDOFF_BRIEF_v9.md` — continuity and implementation history (replaces v8)
> - `SCREENS_TRACKING_v4.md` — full screen inventory and per-screen specs (43 screens)
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

## v9 Consolidation Summary

### What changed from v8 (2026-05-16 session)

**Block C backend — 8/8 items complete (C1, C2, C4, C8 + C-RECON-3 through C-RECON-8):**
- Migration 007 applied: `conversations.deleted_at`, `messages.model_used`, `daily_usage` table
- Single canonical send-message endpoint: `POST /api/v1/conversations/{id}/messages` (SSE streaming)
- PATH B deleted: `routers/messages.py`, `services/llm_service.py`, 4 test files, 4 schema classes
- All features ported into PATH A: tier routing, rate limit, auto-title, LLM retry, error voice, memory extraction
- 10 architectural decisions locked (LLM routing, RAG, streaming, memory window, rate limits, safety, copyright, pricing, ritual exemption, admin bypass)
- Pre-Work Investigation Protocol added to repo (`CLAUDE.md`)

**New tech debt items captured (8 items):**
- Split rate_limit_service.py into two focused files
- Resolve PersonaConfig / Persona ORM naming confusion
- Update orphaned ANTHROPIC_MODEL constant
- Fix C-RECON-6 backoff discrepancy
- Wire generate_insight_task (currently orphaned)
- Fix safety_events.message_id always NULL
- gh CLI installation on founder's Windows machine
- Document Render alembic auto-run mechanism

### What changed from v9 baseline (2026-05-16/17 session)

**Block C frontend — 4/4 complete (C5a, C5b, C5c, C5d all merged):**
- C5b (#63): Chat screen v1 with polished error rendering
- C5c (#64): 429 paywall modal + safety mode UI per C7 spec
- C5d (#65): Conversation list (F6) + existing conv route + tab bar — 1128 lines, 13 files, 13 new frontend tests (43 total frontend tests)

**C3a — RAG infrastructure (merged to main, 2026-05-17):**
- Migration 008 (`008_hnsw_vector_indexes`): HNSW indexes on `source_chunks.embedding` + `memory_entries.embedding`; `chunk_index INTEGER nullable` added to `source_chunks`
- New scripts: `chunking.py`, `corpus_sources.py`, `curated_chunks.py`, `ingest_corpus.py` (one-shot CLI with `--dry-run` and `--persona` flags; not an ARQ task)
- UNIQUE PARTIAL index `uq_source_chunks_persona_title_chunk` on `(persona_id, source_title, chunk_index) WHERE chunk_index IS NOT NULL`
- 14 files, 1615 insertions, 409 deletions, 63 new backend tests (292 total backend tests)
- CLAUDE.md Rule 5 violation discovered and reconciled: `apps/api/db/ingest_sources.py` (408 lines) silently deleted during C3a; 19 Marcus Aurelius curated chunks recovered as `apps/api/scripts/curated_chunks.py` in commit `f78d0f3`. See PROJECT_STATE_v9.md §"CLAUDE.md violations log".

### Current source-of-truth status

- ✅ Phase 4 stabilization sequence: 8/8 ship items closed
- ✅ Setup PR + Greenfield scaffold (2026-05-07)
- ✅ Design System v4→v5 migration (2026-05-11)
- ✅ **Block A — Authentication: 5/5 line-items live**
- ✅ **Block B — Onboarding: 6/6 functional spine shipped** (visual closure pending polish PR)
- ✅ **Block C backend — 8/8 complete** (PATH A canonical, PATH B deleted)
- ✅ 9 personas live with full Section 5.7 character config + bio + portrait + error messages
- ✅ Alembic plumbing; migrations 001-008 applied
- ✅ Legal pages templates live — ⚠️ lawyer review pending
- ✅ Pre-Work Investigation Protocol (CLAUDE.md) in repo
- ✅ **Block C frontend — 4/4 complete** (C5a/b/c/d all merged, 2026-05-16/17)
- ✅ **C3a — RAG infrastructure** (migration 008 applied, HNSW indexes live, 2026-05-17)
- ⏳ **C3b — Corpus ingestion operational run** (READY; operational, not coding; see HANDOFF_BRIEF runbook)
- ⏳ **Consolidated polish PR** (blocks Block B visual closure)
- ⏳ Stripe wiring (calendar gate passed; paused pending $14.99 landing page validation)
- ⏳ DNS + Resend domain verification for `thegreatminds.app`
- ⏳ Lawyer review of legal templates
- ⏳ Founder runbooks
- ⏳ Landing page waitlist test ($14.99 pricing validation)
- ⏳ UAT with mixed testers
- ⏳ Web/PWA public launch

---

# 1. Current Launch Interpretation

**Block C backend is complete and Block C frontend is complete.** The Chat UI (C5a/b/c/d) is live and the RAG infrastructure (C3a, migration 008) is deployed. The next immediate steps are C3b (corpus ingestion operational run) and the consolidated polish PR.

Priority order under Plan A (confirmed active 2026-05-10):

1. ~~**C5 — Chat UI frontend**~~ **DONE** (C5a/b/c/d merged 2026-05-16/17)
2. **C3b — Corpus ingestion operational run** (P0, immediate) — run `python -m apps.api.scripts.ingest_corpus` via Render shell; <$0.02 OpenAI cost. See HANDOFF_BRIEF runbook.
3. **Block B consolidated polish PR** (P0 — blocked on DNS/Resend confirmation)
4. **Landing page waitlist test** (founder-owned, ~2 hours build, 10-day data window) — validates $14.99 price before Stripe wiring
5. **Stripe wiring + Block H** (P0, paused pending landing page signal)
6. **Remaining 28 UI line-items** (Blocks D, F, H, I, J — after polish PR)
7. **Lawyer review of legal templates** (P0 launch blocker — parallel with UI work)
8. **DNS + Resend domain verification** (IN PROGRESS — manual/config)
9. **GDPR / DPA infrastructure** (when Block C UI ships publicly)
10. **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety escalation)
11. **Production smoke test** (after polish PR merged + verified on mobile)
12. **UAT** with mixed testers (≥2/5 spontaneous "I'd pay")
13. **Public launch (web/PWA)**

Avoid reopening Phase 4, Block A, Block B spine, Block C backend, or Block C frontend unless production smoke test reveals a regression.

---

# 2. Remaining Launch-Readiness Checklist (P0)

## 2.1 Code-side P0

### A. Block C remaining — C5 (Chat UI)

Status: 🟢 done — C5a/b/c/d all merged to main (2026-05-16/17). Block C frontend complete. 43 total frontend tests.

**API endpoint:** `POST /api/v1/conversations/{id}/messages` — SSE streaming. This is the ONLY canonical send-message endpoint.

**New conversation flow (2 API calls):**
```
1. POST /api/v1/conversations  { persona_slug: "socrates" }  → { id, persona, title, ... }
2. POST /api/v1/conversations/{id}/messages  { content: "..." }  → SSE stream
```
On subsequent messages in the same conversation: only call step 2.

**SSE event types to handle:** `start`, `chunk`, `done`, `safety`, `safety_override`, `error`

**Error message rendering requirements:**
- Display `data.persona_voice` text when `data.type === "error"` and `data.error_code === "llm_unavailable"`
- Style: italic + muted color (Bronze `#B89968` at ~60% opacity)
- Include a visible retry affordance ("Try again" button or tap-to-retry)
- Do NOT persist the error to message history — it is a transient UI state only

**Rate limit (429) rendering:**
- When API returns HTTP 429 before the SSE stream opens: show paywall UI with upgrade CTA
- Include: limit context from `X-RateLimit-Limit` header, reset time from `X-RateLimit-Reset` header

**Opening invocation:**
- Each persona's `opening_invocation` field (returned by `GET /api/v1/conversations`) is displayed as the first "message" in the chat UI before the user types
- It is NOT a DB-persisted `messages` row — purely a UI affordance from persona config
- Do not send it to the API

**Error message availability note:** All 9 persona error messages are stored in DB and will be returned by the API in the `persona_voice` field of error events. Until tech debt TD-02 is resolved, these ARE being served correctly (the ORM path works). The frontend can safely rely on `persona_voice` being non-null when `error_code === "llm_unavailable"`.

### B. Block C remaining — C3 (RAG corpus ingestion)

Status: 🟡 in progress — C3a complete (RAG infrastructure live, migration 008 deployed, 2026-05-17); C3b READY (operational run pending, founder action)

**C3a — done (2026-05-17):** Migration 008 deployed HNSW indexes on `source_chunks.embedding` + `memory_entries.embedding`. Ingestion pipeline scripts live (`chunking.py`, `corpus_sources.py`, `curated_chunks.py`, `ingest_corpus.py`). pgvector version verified: 0.8.0 (HNSW supported from 0.5.0+). 19 Marcus Aurelius curated chunks in `curated_chunks.py`.

**C3b — operational run (next immediate step):** Run `python -m apps.api.scripts.ingest_corpus` via Render shell. Requires `OPENAI_API_KEY` set in Render env. Cost: <$0.02. See HANDOFF_BRIEF runbook section. `retrieval_service.py` remains fail-open until corpus is populated.

The pgvector infrastructure is live (`source_chunks` table, `vector(1536)`, `retrieval_service.py`). No auto-ingested corpus has been loaded yet. `retrieval_service.retrieve()` returns empty results on every call (fail-open).

**Copyright allowlist (approved sources):**

| Persona | Sources approved for RAG |
|---|---|
| Socrates / Plato | Jowett 1871 translation (public domain) |
| Marcus Aurelius | Long 1862 translation (public domain) |
| Lao Tzu | Legge 1891 translation (public domain) |
| Niccolò Machiavelli | Marriott 1908 translation (public domain) |
| Oscar Wilde | All major works (died 1900, public domain) |
| Epictetus | Long 1890 translation (public domain) |
| Sigmund Freud | Works >95 years old (verify per jurisdiction; most major texts pre-1931 qualify) |

**Excluded from RAG corpus (copyright risk):**

| Persona | Excluded | Reason |
|---|---|---|
| Carl Jung | ALL primary works | Copyrighted until 2031 (died 1961) |
| Simone de Beauvoir | ALL primary works | Copyrighted until 2056 (died 1986) |
| Any persona | Stanford Encyclopedia of Philosophy entries | Not public domain |
| Marcus Aurelius | Hays translation | Modern translation, copyrighted |
| Lao Tzu | Mitchell translation | Modern translation, copyrighted |

Jung and Beauvoir ship with `system_fragment` only (Decision #7). Quality documented as a known limitation for Pro users. Pricing implication deferred.

**Infrastructure requirements in C3 PR:**
- Ingestion script to parse, chunk, and embed approved sources
- `HNSW` vector index on `source_chunks.embedding` (include in same PR as ingestion)
- `HNSW` vector index on `memory_entries.embedding` (same PR — convenient and already schema-ready)

### C. Block B visual closure — Consolidated Polish PR

Status: 🟡 in progress (prerequisites being established)

9 mobile walkthrough findings still open. See v8 §6 BUG-001 through BUG-009 + v8 §2.1A for full scope.

**Blocked by:** DNS + Resend domain verification (manual/config, founder action)

### D. Remaining 28 UI line-items (Blocks D, F, H, I, J)

Status: 🔴 not started. After Block C UI + polish PR verified on mobile.

## 2.2 Legal P0

### A. Lawyer review of legal templates

Status: 🔴 not started

Scope: Terms v1.0, Privacy v1.0, Disclaimer v1.0. Greek consumer law, Stripe billing T&Cs, AI-content liability, GDPR Article 6 lawful bases, processors table, DPO contact.

### B. GDPR / DPA infrastructure

Status: 🔴 not started

Required: DPA with Anthropic (for chat data), processors documentation, data subject request fulfillment workflow, cookie posture, privacy contact email.

### C. Operational founder runbooks

Status: 🔴 not started

Required: Refund, account recovery, GDPR fulfillment, cancellation override, safety escalation.

## 2.3 Infrastructure P0

### A. DNS configuration for `thegreatminds.app`

Status: 🟡 IN PROGRESS (manual DNS records + SSL provisioning)

### B. Resend domain verification

Status: 🟡 IN PROGRESS (depends on DNS). Flip FROM_EMAIL to `noreply@thegreatminds.app` + set display name "Great Minds" after DNS verifies.

### C. Stripe verification

Status: 🟡 Calendar gate passed (2026-05-11). **Paused pending landing page $14.99 validation.** Do not wire until waitlist data (10-day window) signals demand. If signal positive, proceed with Block H work.

### D. Landing page waitlist test

Status: 🔴 not started (founder-owned, ~2 hours build)

Build a minimal landing page for `thegreatminds.app` with:
- Product description + persona teaser
- Email waitlist signup
- Pricing prominently displayed: **$14.99/month · $129/year**
- Goal: validate that $14.99 price point generates meaningful waitlist signup intent

Run for ~10 days before wiring Stripe. Decision gate: if strong waitlist interest → wire Stripe at $14.99; if weak → iterate pricing/messaging before launch.

### E. Render API plan upgrade

Status: 🔴 not started
Priority: P1 / pre-UAT recommended.

~$7/mo Starter plan eliminates 30-60s cold-start. Affects tester experience significantly. Upgrade before UAT.

### F. Production smoke test

Status: 🔴 not started (run after C5 + polish PR merged + verified on mobile)

Include:
- Fresh signup → OTP → disclaimer → onboarding → conversation creation → send message (free persona)
- SSE stream received and rendered correctly
- Rate limit 429 triggers paywall UI after 5 messages
- Pro persona paywalled for free user
- Auto-title appears after first message (may be async — check after ~5s)
- Safety crisis path tested
- `PHENOMENOLOGY_BRIDGE_ENABLED` confirmed true in Render env

### G. `PHENOMENOLOGY_BRIDGE_ENABLED` flag confirmation

Status: 🔴 not verified. Was true 2026-05-04/05; current Render env state unknown. Confirm before smoke test.

## 2.4 RLS Audit P0 (forward-looking)

Status: 🔴 not started

All public Supabase tables: RLS disabled. Mitigation: FastAPI gateway exclusive path.

⚠️ **If any future change adds Supabase anon key to the frontend, RLS becomes a critical vulnerability immediately.** Add explicit RLS policies BEFORE any such change merges.

## 2.5 UAT P0

Status: 🔴 not started

- 3-5 mixed testers (close + acquaintances + strangers)
- Decision gate: ≥2/5 spontaneous "I'd pay" → proceed to public launch
- Requires DNS live and OTP email delivery working for non-Gmail addresses

---

# 3. Tech debt items captured 2026-05-16

These were discovered during the reconciliation session. Each is a real gap in the current codebase that should be addressed before or shortly after the first paying user.

## TD-01 — Split rate_limit_service.py

**Priority:** P2
**File:** `apps/api/services/rate_limit_service.py`

Two unrelated rate limiters coexist in one file:
- `check_and_increment()` — Redis-backed, for OTP/auth flows (sliding window)
- `check_rate_limit()` — DB-backed, for daily message limits (daily_usage table)

These have different backing stores, different semantics, and different callers. Split into:
- `services/auth_rate_limit.py` (Redis/OTP section)
- `services/message_rate_limit.py` (DB/daily section)

Update all callers. Not a launch blocker but creates confusion for any engineer working on either rate limiter in isolation.

## TD-02 — PersonaConfig / Persona ORM naming confusion

**Priority:** P2
**Files:** `apps/api/personas/_base.py`, `apps/api/models/__init__.py`, `apps/api/services/persona_voice.py`

`PersonaConfig` (in-memory Python dataclass from `personas/_base.py`) and `Persona` (SQLAlchemy ORM model from `models/__init__.py`) share the name "persona" in conversation but are different objects.

`get_error_voice(persona, error_code)` reads `getattr(persona, "config", None)`. This works when passed the ORM `Persona` (which has a `.config` JSONB dict attribute) but silently falls back to generic messages when passed a `PersonaConfig` dataclass (which has no `.config` attribute).

Current streaming path correctly passes the ORM object. However, this is a latent confusion risk for future engineers. Resolution options:
- Rename `PersonaConfig` to `PersonaBrainConfig` or `PersonaCharacterSpec` to make the distinction explicit
- Or add a `.config` property to `PersonaConfig` that raises `NotImplementedError` with a clear message

**Consequence if unresolved:** 9 persona-voiced error messages stored in DB will not reach users if any future code path passes `PersonaConfig` to `get_error_voice()`.

## TD-03 — Update or remove ANTHROPIC_MODEL constant

**Priority:** P2
**File:** `apps/api/config.py`

`ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"` is a stale default pointing to old Sonnet 4. `conversation_service.py` does NOT read this constant — it uses `MODEL_FREE`/`MODEL_PRO` literals defined directly in the service file.

The constant is an orphan that will mislead future engineers who look at config.py to understand which model is being used.

Options:
- Remove the constant entirely (cleanest)
- Update to current model IDs and wire it up as the actual source of truth (more work but more consistent)

## TD-04 — C-RECON-6 backoff discrepancy

**Priority:** P4
**File:** `apps/api/services/conversation_service.py`

PATH A's retry loop uses `asyncio.sleep(2**attempt)` with `attempt` starting at 0. This produces delays of 0s, 2s, 4s on attempts 0, 1, 2.

PATH B (now deleted) had a different pattern (1s, 2s, 4s). The current PATH A behavior (0s first retry) may be unintentional. Consider changing to `asyncio.sleep(2**attempt)` with `attempt` starting at 1 (giving 2s, 4s, 8s for a more conservative retry cadence) or document the 0s first-retry as intentional.

## TD-05 — Wire generate_insight_task

**Priority:** P1
**File:** `apps/api/workers/arq_worker.py`

`generate_insight_task` is defined in `arq_worker.py` but is never enqueued. `extract_memory_task` IS wired (dispatched from `stream_response` after each message). Insights are a downstream step that synthesizes accumulated memory entries.

This gap only matters once real users accumulate memory entries. Wire the trigger when `memory_entries` starts growing organically (after C5 ships and users begin conversing). The trigger logic should fire periodically (e.g., every N memory entries for a user), not after every message.

## TD-06 — safety_events.message_id always NULL

**Priority:** P4
**File:** `apps/api/services/conversation_service.py`, safety event logging

Safety events are logged correctly to the `safety_events` table, but the `message_id` FK field is always NULL — the message ID is not threaded through the safety logging call.

Minor cleanup. The events are queryable by user_id, conversation_id, and timestamp. Not a launch blocker.

## TD-07 — gh CLI installation on founder's Windows

**Priority:** P4

`winget install --id GitHub.cli`

Currently `gh pr create` is not available in bash from the Windows environment. PR creation requires using the GitHub web UI link printed by `git push`. Minor inconvenience, not a blocker.

## TD-08 — Document Render alembic auto-run mechanism

**Priority:** P2

Alembic runs `upgrade head` on Render container startup. It has worked through 7 migrations. The mechanism (Procfile? render.yaml CMD? startup script?) is undocumented. Find and document before the next engineer touches the deployment pipeline or before a migration fails on startup.

---

# 4. Database schemas

See `PROJECT_STATE_v9.md` §4 for current state. Migration 008 (`008_hnsw_vector_indexes`) is the latest, applied 2026-05-17. No further migrations are expected until a new feature requires schema changes.

---

# 5. Config & Environment Variables

See `HANDOFF_BRIEF_v9.md` §7 for full env var list and status.

**Pending env var changes:**
- Render: `FROM_EMAIL` → `noreply@thegreatminds.app` (after DNS + Resend verification)
- Render: `PHENOMENOLOGY_BRIDGE_ENABLED` → verify state; set explicitly to `true`
- Render: `ANTHROPIC_MODEL` → update or remove (TD-03)
- Netlify: `NEXT_PUBLIC_SUPPORT_EMAIL` → `support@thegreatminds.app` (when mailbox exists)

---

# 6. Stripe Wiring (P0 — paused)

Status: 🔴 Paused pending landing page $14.99 validation.

**Pricing locked (Decision #8):** $14.99/month · $129/year (~$10.75/month effective)

When landing page waitlist data is positive, proceed with:

### 6.1 Required before Block H work
- [ ] Verify Stripe account active (cooldown from ~2026-05-01 — verify status)
- [ ] Set up products + prices:
  - Free: $0 — 3 free personas (Aurelius, Socrates, Lao Tzu); 5 messages/persona/day
  - Pro: **$14.99/month · $129/year** — unlocks all 6 pro personas; unlimited messages
  - Premium: schema-supported; 0 personas assigned; pricing deferred (no concrete premium feature defined)
- [ ] Webhook endpoint: `https://philosopher-api-z9l9.onrender.com/api/v1/stripe/webhook`
- [ ] Webhook events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
- [ ] Test mode integration verification

### 6.2 Backend work
- [ ] `apps/api/services/stripe_service.py` (create)
- [ ] `apps/api/routers/stripe.py` (create) — webhook handler + checkout session endpoint
- [ ] Entitlement check integration with existing `tier_service.get_user_tier()`

### 6.3 Frontend work (Block H)
- [ ] H1-H6 screens per `SCREENS_TRACKING_v4`
- [ ] Stripe Checkout redirect or embedded form
- [ ] Upgrade CTAs in B6 paywall placeholder (currently `alert()`) → real paywall flow
- [ ] Subscription management in Block I (account settings)

---

# 7. Persona-specific maintenance backlog

### P2 — ChatGPT audit of new persona configs

Status: 🔴 not started (founder-owned)

Run ChatGPT audit on Lao Tzu, Wilde, Machiavelli, Jung configs. Apply surgical UPDATE edits via JSONB `jsonb_set`. Not full rewrites.

### P2 — Extract new personas to YAML

Status: 🔴 not started

Lao Tzu, Wilde, Machiavelli currently live only as JSONB in `personas.config`. Original 6 have parallel YAML in `apps/api/philosopher_brain/`. Create:
- `apps/api/philosopher_brain/lao_tzu.yaml`
- `apps/api/philosopher_brain/oscar_wilde.yaml`
- `apps/api/philosopher_brain/niccolo_machiavelli.yaml`

### P2 — Portrait style harmonization

Status: 🔴 not started

Aurelius + Socrates are painterly outliers vs the 7 atmospheric/hybrid others. Re-generate in matching style.

### P2 — Premium tier reassignment (if desired)

Status: 🔴 not decided

Freud currently `pro`, was originally planned as `premium`. Tier exists in schema. If reassigned: 1-line SQL UPDATE + update persona table row. Pricing/UX implications deferred.

---

# 8. LLM eval (optional confidence check)

Status: ⏸ optional, P3

v8 §24.3 Decision 6 recommended an eval suite as P1 post-revenue. The 2026-05-15 Workbench A/B test (23/24 Haiku, 24/24 Sonnet) provided sufficient confidence to proceed to production.

An optional additional eval test for Lao Tzu or a third persona would give coverage across a wider range of character voices (current validation covered primarily Western philosophical voices). Not a launch blocker.

---

# 9. Future blocks reference

## 9.1 Block C — remaining items

### C5 — Chat UI frontend

Status: 🟢 done (C5a/b/c/d merged 2026-05-16/17). See §2.1A for spec reference.

### C3 — RAG corpus ingestion

- **C3a** — 🟢 done (2026-05-17). HNSW indexes live, ingestion pipeline deployed. See §2.1B.
- **C3b** — READY (operational run). Run `python -m apps.api.scripts.ingest_corpus` via Render shell. Copyright allowlist defined. See HANDOFF_BRIEF runbook.

## 9.2 Block D — Discovery (D1, D2, D3)

Not yet planned. After C5 + polish PR.

## 9.3 Block F — Reflection (F1-F6)

Not yet planned.

## 9.4 Block H — Subscription & Billing (H1-H6)

Paused pending landing page validation. See §6.

## 9.5 Block I — Account & Settings (I1-I6)

Not yet planned.

## 9.6 Block J — Empty/error states (J1, J2, J3, J5)

Not yet planned. Often handled inline with other blocks.

---

# 10. Operating principles (preserved + extended)

### 10.1–10.17 — Preserved from v7/v8

Full text in `HANDOFF_BRIEF_v8.md` §19. Key rules:

- §19.14: Unicode JSONB encoding pre-merge check (relevant for any future migration with emoji/non-ASCII)
- §19.15: Mobile walkthrough is non-substitutable
- §19.16: Read existing docs before writing replacement docs
- §19.17: Addendum vs baseline regen discipline

### 10.18 — Pre-Work Investigation Protocol (NEW v9 — 2026-05-16)

Codified in `CLAUDE.md`. Mandatory for all multi-PR work. Caught 4 real bugs during reconciliation. See `HANDOFF_BRIEF_v9.md` §1 for the full list of what was caught.

**The rule:** Before writing any brief or any code that adds, modifies, or extends a feature, enumerate what already exists in the same domain. "Look at existing patterns" is NOT sufficient — explicit enumeration is required.

### 10.19 — openapi.json is a verification artifact, not source (NEW v9 — 2026-05-16)

Do not commit `openapi.json`. Generate it locally for verification after deletions/additions; discard after use. If needed persistently, add to `.gitignore` in a dedicated cleanup PR.

### 10.20 — Reconciliation over deletion (NEW v9 — 2026-05-16)

When parallel implementations of the same feature are discovered, the default sequence is:
1. Investigation-only PR → comparison report
2. Founder approves reconciliation strategy
3. Feature ports in order of risk (security + billing holes first)
4. Deletion last, after all ports verified

See `HANDOFF_BRIEF_v9.md` §13.3 for full rationale.

---

# 11. Backlog by priority (consolidated)

## 11.1 P0 (launch blockers)

- [x] **C5 — Chat UI frontend** — COMPLETE (C5a/b/c/d merged 2026-05-16/17)
- [x] **C3a — RAG infrastructure** — COMPLETE (migration 008, HNSW indexes, ingestion scripts, 2026-05-17)
- [ ] **C3b — Corpus ingestion operational run** — READY; founder runs `python -m apps.api.scripts.ingest_corpus` via Render shell; <$0.02 OpenAI cost
- [ ] **Consolidated polish PR** — visually closes Block B
- [ ] **Landing page waitlist test** — $14.99 validation (founder builds, ~2h, 10-day data window)
- [ ] **Lawyer review** of Terms / Privacy / disclaimer
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure** (Anthropic DPA, processors doc, request fulfillment workflow)
- [ ] **Stripe wiring** (paused pending landing page signal; Block H + backend service)
- [ ] **Founder runbooks** (refund, account recovery, GDPR, cancellation, safety escalation)
- [ ] **Production smoke test** post-C5+polish-PR
- [ ] **PHENOMENOLOGY_BRIDGE_ENABLED flag state confirmation**
- [ ] **RLS policies** added as defense-in-depth (even with FastAPI gateway)
- [ ] **UAT** with 3-5 testers, ≥2/5 spontaneous "I'd pay"
- [ ] **Blocks D, F, H, I, J** — 28 remaining UI line-items (after C5)

## 11.2 P1

- [ ] **Wire generate_insight_task** (TD-05) — when memory_entries starts accumulating
- [x] **HNSW vector indexes** on `source_chunks.embedding` + `memory_entries.embedding` — DONE in C3a (migration 008, 2026-05-17)
- [ ] **Render API plan upgrade** (~$7/mo to eliminate cold-start; do before UAT)
- [ ] **A6+A7 disclaimer endpoint integration tests** (shipped without tests for speed)
- [ ] **A6+A7 lazy-load monitoring** — watch Render logs for `MissingGreenlet`
- [ ] **A4 mailto visible support email fallback** — when `support@thegreatminds.app` mailbox exists

## 11.3 P2 (tech debt)

- [ ] **TD-01** — Split `rate_limit_service.py` into `auth_rate_limit.py` + `message_rate_limit.py`
- [ ] **TD-02** — Resolve PersonaConfig / Persona ORM naming confusion (rename or add guard)
- [ ] **TD-03** — Update or remove `ANTHROPIC_MODEL` constant in `config.py`
- [ ] **TD-08** — Document Render alembic auto-run mechanism
- [ ] **ChatGPT audit** of new persona configs → surgical JSONB UPDATE edits (founder-owned)
- [ ] **Portrait style harmonization** — Aurelius + Socrates re-generate
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML** in `apps/api/philosopher_brain/`
- [ ] **Premium tier reassignment** (Freud → premium if desired; 1-line UPDATE)
- [ ] **B1 hydration polish** — 0.5s flash before auth-guard redirect
- [ ] **Local Python venv for founder** (Windows) — prevents another surrogate emoji disaster

## 11.4 P3

- [ ] **Desktop layout polish** — mobile-first looks broken >768px
- [ ] **Phase 5 register architecture + UI chips + classifier** — post-feedback
- [ ] **Phase 6 eval suite + CI** — post-revenue
- [ ] **LLM eval test** for Lao Tzu or third persona (optional confidence check)
- [ ] **LLM classifier** (safety layer 3) — deferred from Decision #6; revisit post-launch
- [ ] **A5 polish** — 6-digit OTP boxes (if not handled in polish PR)
- [ ] **Phase 4 PR Β** (Marcus shading content, 33 strings) — post-launch

## 11.5 P4

- [ ] **TD-04** — C-RECON-6 backoff discrepancy (PATH A 0s/2s/4s; document as intentional or harmonize)
- [ ] **TD-06** — `safety_events.message_id` always NULL — wire message FK
- [ ] **TD-07** — `gh CLI install on founder's Windows**: `winget install --id GitHub.cli`
- [ ] **Render `philosopher-db` decommissioning verification** — carry-forward from v6/v7
- [x] **`apps/api/scripts/` decision** — RESOLVED: committed as C3a ingestion pipeline home (`chunking.py`, `corpus_sources.py`, `curated_chunks.py`, `ingest_corpus.py`, `README.md`)
- [ ] **Stale branch cleanup** — periodic batch
- [ ] **Legal pages `target="_blank"` rel hardening** — explicit `noopener noreferrer`
- [ ] **openapi.json cleanup** — add to `.gitignore` in a separate cleanup PR

---

# 12. Plan A vs Plan B (preserved)

### 12.1 Plan A — 43-screen build before launch (ACTIVE)

Founder's 2026-05-06 decision, reconfirmed 2026-05-10. Build all 43 specced screens, then UAT, then public launch.

**Remaining work surfaces in priority order:**
1. C5 (chat UI)
2. Polish PR (closes Block B visually)
3. C3 (RAG corpus)
4. Block D (Discovery)
5. Block F (Reflection)
6. Stripe wiring + Block H (Billing)
7. Block I (Settings)
8. Block J (Empty states)
9. Lawyer review + GDPR/DPA + Founder runbooks (parallel)
10. UAT
11. Public launch

### 12.2 Plan B — Minimum-to-revenue interrupt (PRESERVED, NOT ACTIVE)

Available as pivot. Sequence: polish PR → Block C (C5 only) → Stripe wiring → limited UAT → launch → iterate.

**Plan B triggers (when mentor will re-raise):**
- UAT signal returns <2/5 spontaneous "I'd pay"
- Stripe wiring slips beyond C5 completion
- Block C UI exceeds 3x estimate
- Founder explicit pivot trigger

---

# 13. KIEN — separate project note

Founder also runs **KIEN** — AI companion SaaS — as a separate codebase. Not to be confused with Philosopher / Great Minds. This v9 backlog is **Philosopher-only**.

---

**End of IMPLEMENTATION_BACKLOG v9.** Authoritative as of 2026-05-17. Supersedes `IMPLEMENTATION_BACKLOG_v8.md` (preserved as historical reference).
