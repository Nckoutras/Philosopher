# GREAT MINDS — Implementation Backlog v12

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v12 = v11 baseline (2026-05-24) + 2026-05-25-26 session delta (PR4r merged; PR4x–PR4ah; L1 migration 015 FK indexes; Render paid plan upgrade; latency diagnosis; Ireland→Oregon region migration in progress; KIEN deleted; TD-22 source_chunks re-ingest added).**
>
> **Generated:** 2026-05-26 (v12 rotation)
>
> **How to read this file:**
> - This v12 file supersedes v11 and all prior backlog files.
> - Where v12 conflicts with v11, v12 wins.
> - Status, priority, and launch-readiness calls reflect 2026-05-26 state.
>
> **Companion documents:**
> - `PROJECT_STATE_v12.md` — current project state
> - `HANDOFF_BRIEF_v12.md` — continuity and implementation history
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

## v12 Consolidation Summary

### What shipped (2026-05-25-26) — items to mark DONE

| Item | PR | Status |
|---|---|---|
| PR4r — Actual rollback of hydration guard (was in-flight) | — | ✅ DONE |
| PR4w — Docs v11 rotation | — | ✅ DONE |
| Render paid plan upgrade (philosopher-api + philosopher-worker) | — | ✅ DONE |
| PR4x — OTP autofill mobile fix | #113 | ✅ DONE |
| PR4y — Auth redirect to /auth?mode=signin | — | ✅ DONE |
| PR4z — Pull-to-refresh disabled (overscroll) | — | ✅ DONE |
| PR4aa — Conversation titles prompt hardening | — | ✅ DONE |
| Backfill-titles admin execution (5/5 clean titles) | — | ✅ DONE |
| PR4ab — PersonaPickerSheet stuck state + errors + toasts | — | ✅ DONE |
| PR4u2 — Library search empty state card | — | ✅ DONE |
| PR4ad — Today card thumbnail uniformity (flex + next/image) | — | ✅ DONE |
| PR4ae — Library ConversationCard readability | #120 | ✅ DONE |
| PR4af — Account scheduled letters card removed | #121 | ✅ DONE |
| PR4ag1 — Share card v3 tweaks + spacebar bug fix | #122 | ✅ DONE |
| PR4ah — RitualIcons.tsx new file + nav symbol swap | #123 | ✅ DONE |
| L1 — Migration 015: 20 btree FK indexes | #124 | ✅ DONE |

### Infra actions completed

| Action | Status |
|---|---|
| Render philosopher-worker upgraded to paid Starter tier | ✅ DONE |
| Render philosopher-api on paid plan | ✅ DONE |
| Cold-start eliminated on both services | ✅ DONE |
| Latency root cause diagnosed (280ms Ireland↔Oregon RTT) | ✅ DONE |
| Oregon Supabase project provisioned + schema + ref data migrated | ✅ DONE (partial) |
| KIEN project deleted | ✅ DONE |

### Items previously in P1 that shipped

| Old ID | Description | PR |
|---|---|---|
| Render API plan upgrade | Both services now paid; cold-start eliminated | — |
| C6c cold-start screen | **Deprioritized** (paid plan eliminates the problem; C6c moved to ⏸) | — |
| Backfill-titles admin execution | Executed via Render shell; 5/5 titles clean | PR4aa |

---

## 1. Current Launch Interpretation

**Plan A (active).** Current priority order as of 2026-05-26:

1. ~~**C5 — Chat UI frontend**~~ DONE (2026-05-17)
2. ~~**C3b — Corpus ingestion**~~ DONE (2026-05-17)
3. ~~**Stripe sandbox wiring**~~ SANDBOX COMPLETE (PR1 #77, 2026-05-19)
4. ~~**D1 Home/Today**~~ DONE (PR #76, 2026-05-18)
5. ~~**A0 Public Landing**~~ DONE (PR #76 + PR1 #77)
6. ~~**Paywall + subscription bootstrap (PR4j)**~~ DONE (#100)
7. ~~**Share v2/v3 (PR4n + PR4ag1)**~~ DONE (#102, #122)
8. ~~**Rituals tab + page (PR4o + PR4ah)**~~ DONE (#103, #123)
9. ~~**Render cold-start elimination**~~ DONE (paid plan upgrade 2026-05-25)
10. ~~**Backfill-titles admin execution**~~ DONE (PR4aa + Render shell, 5/5)
11. **Oregon region migration completion** — migrate remaining tables + re-ingest source_chunks + DATABASE_URL switch
12. **Post-switch smoke test** — full app verification on Oregon
13. **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel)
14. **Mobile 12-point nav smoke test** (real iOS Safari)
15. **Cold beta with 3–5 fresh users**
16. **Block B consolidated polish PR**
17. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)
18. **UAT** (≥2/5 spontaneous "I'd pay")
19. **Public launch**

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.1 Infrastructure P0

- [ ] **Oregon migration completion** (messages 227, saved_lines 13, safety_events 5, user_ritual_completions 4, scheduled_emails 2, memory_entries 8, disclaimer_acceptances 1, alembic_version row, conversations.source_saved_line_id UPDATE)
- [ ] **source_chunks re-ingest** into Oregon project via existing OpenAI embeddings script
- [ ] **Render DATABASE_URL switch** to Oregon pooler (founder action, post-verification)
- [ ] **Post-switch smoke test** (login, chat, rituals, share, library, RAG retrieval)
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** in Render env

### 2.2 Code-side P0

- [ ] **bugfixes-3 — auth race fix** (P0; see TD-10 for approach options; PR4ai deferred)
- [ ] **End-to-end Stripe sandbox test** (test card → webhook → entitlement → portal → cancel → tier downgrade)
- [ ] **Mobile 12-point nav smoke test** (5 fixed routes + tab bar including Rituals + chat + upgrade on real iOS Safari)
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

Unchanged from v11. See v11 §3 for full text.

### TD-10 — Zustand hydration race condition (P1, preview smoke test mandatory)

Unchanged from v11. PR4ai (new attempt) was deferred — too risky given the PR4p production regression history. Any new attempt requires:
1. Three-path smoke test on Netlify preview: hard refresh, direct URL, normal nav
2. All three pass before merging to main

Approaches to investigate (in order of preference):
1. `skipHydration: true` + manual `useStore.persist.rehydrate()` in SSR-safe wrapper
2. Move auth check to Next.js middleware (server-side cookie check)
3. Cookie-based auth check entirely server-side

### TD-11 — Tier resolution unified refactor (P2, pre-paid-launch)

Unchanged from v11. Must consolidate `get_current_user_plan` and `get_user_tier` before disabling `BETA_GRANT_PRO_TO_ALL`.

### TD-12 — Soft-delete pattern for conversations (P2, pre-paid-launch)

Unchanged from v11.

### TD-13 — Modal abstraction (P3)

Unchanged from v11. Three modals exist; refactor when 4th is needed.

### TD-14 — BASE_URL legacy cleanup (P4)

Unchanged from v11. `config.py` setting remains; no app code reads it. Remove in next cleanup PR.

### TD-15 — Memory extraction JSON parse fix (P3)

Unchanged from v11.

### TD-16 — INK_COLOR mismatch

**CLOSED** — Fixed in PR4v (#110). `image_service.py` now uses `#1F1B14` to match Tailwind config.

### TD-17 — Weekly Reading full implementation (post cold-beta, multi-week)

Unchanged from v11. Not before cold-beta validation.

### TD-18 — Hydration guard process lesson (process)

Unchanged from v11. Codified as P-01 through P-05 in CLAUDE.md.

### TD-20 — safety_events.message_id FK ondelete (P2)

Unchanged from v11. `safety_events.message_id` uses `ON DELETE NO ACTION` — inconsistent with migration 013 pattern. Fix = 1-line ALTER in a new migration (016). Currently 0 rows populate message_id; becomes critical when safety pipeline starts using it.

### TD-21 — passive_deletes audit (P2, pre-paid-launch)

Unchanged from v11. PR4s fixed `Conversation.messages`. Remaining parent-child relationships (User.conversations, User.messages, User.saved_lines, etc.) should be audited for the same SQLAlchemy ↔ DB CASCADE mismatch. Becomes P0 when delete-account / GDPR flow is exposed.

### TD-22 — source_chunks re-ingest post-Oregon migration (P0 operational, not code)

**New v12.**

After DATABASE_URL is switched to Oregon, the `source_chunks` table in Oregon will be empty (2476 rows × 1536-dim vectors were not migrated via MCP — ~38MB exceeds context budget). RAG retrieval will fail until re-ingest runs.

**Fix:** Run the existing OpenAI embeddings ingestion script against the Oregon project. Not a code change — an operational step.

**Timing:** Immediately after DATABASE_URL switch; before smoke-testing RAG / before cold beta.

**Lesson codified:** MCP is for structured/relational data. Large vector payloads must be re-ingested from source. See HANDOFF_BRIEF_v12.md §13.9.

---

## 4. Database schemas

See `PROJECT_STATE_v12.md` §4 for current state. Migration head: `015_add_fk_indexes`. Migration 015 (20 FK indexes) applied since v11.

---

## 5. Config & Environment Variables

See `HANDOFF_BRIEF_v12.md` §7 for full env var list and status.

**Key change since v11:**
- `DATABASE_URL` pending switch to Oregon pooler after migration completes

---

## 6. Stripe Wiring (sandbox complete — PR1 #77)

Status: 🟢 **Sandbox complete (PR1 #77, 2026-05-19).** Unchanged from v11.

End-to-end sandbox test still pending (see §2.2 P0 checklist). BETA bypass active.

---

## 7. Persona-specific maintenance backlog

Unchanged from v11. ChatGPT audit, YAML extraction, portrait harmonization all still pending.

---

## 8. LLM eval (optional)

Status: ⏸ P3. Unchanged from v11.

---

## 9. Future blocks reference

### 9.1 Block C — complete

Unchanged from v11.

### 9.2 Block D — D1 complete, D2/D3 not planned

Unchanged from v11.

### 9.3 Block F — Reflection

Unchanged from v11. F1 ✅. F2/F3/F4 P2. F6 ✅.

### 9.4 Block H — Subscription & Billing

Stripe sandbox ✅ (PR1 #77). `/api/v1/subscription` ✅ (PR4j). End-to-end sandbox test pending.

### 9.5 Block I — Account & Settings

I1 Account hub not yet built. Spec locked. P1.

Account page: Scheduled letters card removed (PR4af) — cleaner until ARQ delivery is wired.

### 9.6 Block J — Empty/error states

Edge state pages shipped (PR4u #111 — 404, in-app error, global-error). Library empty state card shipped (PR4u2).

### 9.7 Rituals (updated v12)

- **Letter to my Future Self:** UI live (PR4o). PersonaPickerSheet fixed (PR4ab). Scheduled email ARQ delivery NOT YET WIRED (BUG-014). DB schema live (migration 012). Account card removed until ARQ is wired (PR4af).
- **The Mirror:** LOCKED (placeholder card). MirrorIcon component added (PR4ah).
- **The Counterview:** LOCKED (placeholder card).
- **The Weekly Reading:** LOCKED (placeholder card; full implementation = TD-17, post cold-beta).
- **Nav tab:** Custom icon symbol live (PR4ah).

---

## 10. Operating principles (preserved + extended)

### 10.1–10.21 — Preserved from v11

Full text in prior handoff briefs. Key rules include P-01 through P-05 in CLAUDE.md.

### 10.22 — P-06 confirmed working (NEW v12 — 2026-05-26)

P-06 (diagnose before code change) was applied correctly three times in this session. Each time a "bug" was reported, investigation-first revealed a non-bug (cold-start delay, intended behavior, prior user action). Zero premature code changes were made. See HANDOFF_BRIEF_v12.md §13.8.

The discipline: when user reports "X is broken," ALWAYS verify the reported state in actual data / logs before writing any code. Premature code responses to perceived bugs cost time and risk real regressions.

### 10.23 — MCP migration pattern for large vector data (NEW v12 — 2026-05-26)

MCP-based SQL migration is efficient for structured/relational rows. It has a hard context window limit that makes it unsuitable for large binary/vector payloads. Pattern codified:
- Structured data (users, conversations, messages, metadata): migrate via MCP SQL execution
- Vector embeddings (source_chunks, any future embedding table): re-ingest from source

See HANDOFF_BRIEF_v12.md §13.9.

---

## 11. Backlog by priority (consolidated)

## 11.1 P0 (launch blockers)

- [x] **C5 — Chat UI frontend** — DONE (2026-05-17)
- [x] **C3 — RAG + corpus ingestion** — DONE (2026-05-17)
- [x] **D1 Home/Today** — DONE (PR #76, 2026-05-18)
- [x] **A0 Public Landing** — DONE (PR #76 + PR1 #77, 2026-05-19)
- [x] **Stripe sandbox wiring** — SANDBOX DONE (PR1 #77, 2026-05-19)
- [x] **PR4j paywall-audit + BETA bypass** — DONE (#100, 2026-05-22)
- [x] **PR4n/PR4ag1 Share v2/v3** — DONE (#102, #122)
- [x] **PR4o/PR4ah Rituals tab + page** — DONE (#103, #123)
- [x] **Render cold-start elimination** — DONE (paid plan upgrade, 2026-05-25)
- [x] **Backfill-titles admin execution** — DONE (PR4aa + Render shell, 5/5, 2026-05-25)
- [ ] **Oregon region migration completion** (messages, saved_lines, safety_events, etc.)
- [ ] **source_chunks re-ingest** into Oregon via embeddings script (TD-22)
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

## 11.2 P1

- [ ] **TD-05** — Wire generate_insight_task (when memory_entries accumulating)
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory; PR4ai deferred)
- [ ] **I1 Account hub build** (spec locked)
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **Letter to my Future Self — ARQ email delivery wiring** (BUG-014)
- [x] ~~**Render API plan upgrade**~~ — DONE (both services on paid tier, 2026-05-25)
- [x] ~~**Google OAuth implementation**~~ — DONE (PR4k #101; dormant)
- [x] ~~**Share v2/v3 polish**~~ — DONE (PR4n #102 + PR4ag1 #122)
- [x] ~~**Rituals tab + page**~~ — DONE (PR4o #103 + PR4ah #123)

## 11.3 P2 (tech debt)

- [ ] **TD-11** — Tier resolution unified refactor (pre-paid-launch)
- [ ] **TD-12** — Soft-delete pattern for conversations (pre-paid-launch)
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
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
- [ ] **F3/F4 Weekly letter inbox + detail** (post-revenue; TD-17)
- [ ] **TD-17** — Weekly Reading full implementation
- [ ] **B1 hydration polish** (0.5s flash before auth-guard redirect)
- [ ] **TD-20** — safety_events.message_id FK ondelete (pre-cold-beta)
- [ ] **TD-21** — passive_deletes audit across remaining parent-child relationships
- [x] ~~**C6c — cold-start screen**~~ — ⏸ DEPRIORITIZED (Render paid plan eliminates cold-start; no longer needed before launch)

## 11.4 P3

- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **Desktop layout polish** — mobile-first looks broken >768px
- [ ] **Phase 5 register architecture + UI chips** — post-feedback
- [ ] **Phase 6 eval suite + CI** — post-revenue
- [ ] **LLM eval test** for Lao Tzu
- [ ] **LLM classifier** (safety layer 3)

## 11.5 P4

- [ ] **TD-04** — Backoff discrepancy (document or harmonize)
- [ ] **TD-06** — `safety_events.message_id` always NULL
- [ ] **TD-07** — `gh CLI install on founder's Windows`
- [ ] **TD-14** — BASE_URL legacy cleanup in config.py
- [ ] **TD-18** — Process lesson (already codified in CLAUDE.md)
- [ ] **Stale branch cleanup**
- [ ] **openapi.json → .gitignore**
- [ ] **Legal pages `target="_blank"` rel hardening**

---

## 12. Plan A vs Plan B (preserved)

### 12.1 Plan A — 43-screen build before launch (ACTIVE)

Unchanged from v11. Remaining work: Oregon migration → cold beta → consolidated polish PR → lawyer review + GDPR → UAT → launch.

### 12.2 Plan B — Minimum-to-revenue interrupt (preserved, not active)

Available as pivot if UAT signal < 2/5 "I'd pay" or timeline slips.

---

## 13. KIEN — deleted

KIEN project deleted 2026-05-26. No backup taken. This backlog is **Philosopher-only**.

---

**End of IMPLEMENTATION_BACKLOG v12.** Authoritative as of 2026-05-26. Supersedes `IMPLEMENTATION_BACKLOG_v11.md` (preserved as historical reference). *(v10 was skipped in the previous rotation — v12 is a normal single-session rotation.)*
