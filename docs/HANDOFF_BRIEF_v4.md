# HANDOFF BRIEF v4 — Philosopher / Great Minds

**For:** The next Claude Code (or developer) session
**From:** Nikos Koutras (founder) + mentor instance
**Date updated:** 2026-05-05 (v4 — engine-first launch closure)
**Prior version:** `docs/HANDOFF_BRIEF_v3.md` (2026-05-02, post-Phase-2 merge)
**Status:** Engine-first launch sequence COMPLETE. 7/7 P0 items closed.
Backend stable. Frontend type-safe. All critical safety paths exercised.
Next phase: launch readiness (cold smoke test, marketing, payment
integration verification). Not engineering.

> **Update note for v4:** Sections 1-14 unchanged from v1/v2. §15 updated
> inline for phenomenology bridge completion. §16 updated with Phase 4
> shipped status. §17 substantially rewritten — all P0 launch blockers
> are now CLOSED. §19 adds engine-first session lessons. Where v4
> contradicts v3, v4 wins. v3 preserved verbatim where unchanged.

---

## Changelog v3 → v4

**v4 reflects work shipped 2026-05-05 (engine-first launch sequence):**

- **Bug #33 + Bug #34** — Safety pathway refactor. Deterministic classifier-only path. LLM-side crisis directives removed from system prompt. Medium risk now fully suppresses persona (spec divergence documented as defensible launch fix). Country-neutral crisis copy. Committed on branch `fix/safety-crisis-pathway`.
- **1.7** — `user_name` removal across all callers. Hotfix `0256f97` for missed call site at `conversation_service.py:159` (produced 10-min production crash). Discipline rule established: full diffs required for all parameter/schema changes — no grep summaries trusted as caller audit.
- **1.6** — Nietzsche removed from frontend persona list display (commit `c49c3cd`). Backend YAML preserved. Option A implementation.
- **1.4** — Phenomenology trigger audit (commit `ae58479`). +88 verb-form and gerund triggers across 32 entries.
- **2.1** — Phenomenology map content expansion (commit `54a8be4`). 33 → 78 entries. Adversarial mentor submission, reviewed and accepted.
- **1.3** — Sentence-boundary truncation 3-layer fix (commit `2bf9244`). Budget tweak + strip-time sentence boundary + Layer 3 observability hook. 125→129 tests.
- **1.5** — Empty-conversation dedup + in-flight flag (commit `718a7dd`). Backend dedup + frontend guard. 129→134 tests.

---

## 1-14 — UNCHANGED FROM v1 / v2 / v3

[Sections 1 through 14 preserved as-is. See `docs/HANDOFF_BRIEF_v3.md` for full text.]

---

## 15. SECTION 5.7 FRAMEWORK — STATUS UPDATE (v4 patch)

§15.1 - §15.4 unchanged from v3.

### 15.5 Implementation status (v4 patch)

| Element | v3 status | v4 status |
|---|---|---|
| **Character anchors (schema)** | ✅ Optional field on PersonaConfig | ✅ unchanged |
| **Character anchors (data)** | ⏳ Phase 3 pending | ⏳ Phase 3 pending |
| **Register architecture (schema)** | ✅ RegisterRange + RegisterOverride dataclasses | ✅ unchanged |
| **Register architecture (data + classifier)** | ⏳ Phase 5 pending | ⏳ Phase 5 pending |
| **Brevity discipline (schema)** | ✅ ResponseLengthSpec 4-mode dataclass | ✅ unchanged |
| **Brevity discipline (runtime check)** | ✅ check_brevity() in postprocessing_service | ✅ 3-layer fix shipped (commit 2bf9244): budget multiplier, sentence boundary trim, observability hook |
| **Anti-flexing (schema)** | ✅ AntiFlexingRules dataclass | ✅ unchanged |
| **Anti-flexing (data + enforcement)** | ⏳ Phase 3 pending | ⏳ Phase 3 pending |
| **Modern phenomenology bridge** | ⏳ Phase 4 pending | ✅ ACTIVE in production. 78 entries (was 33 baseline). Phase 4 PR Α infrastructure + 1.4 verb-form audit + 2.1 content expansion + 1.3 truncation fix shipped 2026-05-04 through 2026-05-05. Persona shading content for 45 new entries is mentor follow-up work, post-launch. |
| **Universal forbidden lexicon (runtime)** | ✅ Live via check_universal_forbidden() | ✅ unchanged |
| **Persona-specific forbidden (schema)** | ✅ ForbiddenLexicon dataclass | ✅ unchanged |
| **Persona-specific forbidden (data)** | ⏳ Phase 3 pending | ⏳ Phase 3 pending |
| **Eval suite** | ⏳ Phase 6 pending | ⏳ Phase 6 pending |

---

## 16. MIGRATION PLAN — UPDATED STATUS (v4 patch)

§16.1, §16.3, §16.4, §16.5 unchanged from v3.

### 16.2 Six-phase plan — IMPLEMENTATION STATUS (v4 patch)

**Phase 1** ✅ COMPLETE + MERGED 2026-05-02 (commit `0ade549`). See v3 §16.2 for full detail.

**Phase 2** ✅ COMPLETE + MERGED 2026-05-02 (commit `6e2daad`). See v3 §16.2 for full detail.

**Phase 3** ⏳ NOT STARTED. Post-launch.

**Phase 4 — Modern phenomenology bridge** ✅ **COMPLETE + IN PRODUCTION 2026-05-05**

Infrastructure committed in Phase 4 PR Α (feature-flagged, `PHENOMENOLOGY_BRIDGE_ENABLED` env var). Map expanded from 33 to 78 entries across engine-first session (commits `ae58479` trigger audit, `54a8be4` content expansion). Bridge active in production. Truncation fix (`2bf9244`) resolves bridge-related postprocessing edge case.

Remaining Phase 4 work: **~200 persona shading paragraphs** for 45 new entries. This is content work, not engineering. High-frequency entries first (situationship, FOMO, love bombing, grindset, sunday scaries).

**Phase 5 — Register architecture + UI chips** ⏳ NOT STARTED. Post-launch.

**Phase 6 — Eval suite + CI** ⏳ NOT STARTED. Post-launch.

---

## 17. PHASE QUEUE — REWRITTEN FOR POST-ENGINE-FIRST REALITY (v4)

### 17.1 ENGINE-FIRST LAUNCH SEQUENCE: COMPLETE 2026-05-05

All P0 launch blockers are closed.

| P0 Item | Status | Commit |
|---|---|---|
| Bug #33 — Safety pathway in-persona voice | ✅ CLOSED | fix/safety-crisis-pathway |
| Bug #34 — US-specific crisis copy | ✅ CLOSED | fix/safety-crisis-pathway |
| 1.3 — Sentence-boundary truncation | ✅ CLOSED | `2bf9244` |
| 1.4 — Phenomenology trigger audit | ✅ CLOSED | `ae58479` |
| 1.5 — Empty-conversation dedup + in-flight flag | ✅ CLOSED | `718a7dd` |
| 1.6 — Nietzsche frontend removal | ✅ CLOSED | `c49c3cd` |
| 1.7 — user_name removal + hotfix | ✅ CLOSED | `0256f97` |
| 2.1 — Phenomenology map 33→78 entries | ✅ CLOSED | `54a8be4` |

### 17.2 Next phase: launch readiness (not engineering)

Engineering is stable. Next actions are operational, not code:

1. **Cold smoke test** — Sign up fresh account, chat with Marcus Aurelius (free tier), send 3 messages, verify streaming response, verify no empty-row accumulation in DB, verify safety overlay fires on test phrase.

2. **Phenomenology bridge smoke test** — Send "burnout", "FOMO", "ghosting" to any persona. Verify bridge activates (log `phenomenology_bridge` value non-null). Verify response engages with essence rather than naming the modern term back.

3. **Stripe wiring** — Connect payment flow. Stripe account unpaused as of ~2026-05-11 (per v3 §17.4).

4. **Marketing** — 5-person user validation test: send 3 working persona screenshots, ask "would you pay $7/mo for this?" (per v1 Section 8 Step 6). Decision tree: 3+ yes → Stripe wiring. 0-1 yes → repivot pitch or audience.

5. **Pricing finalization** — $12/mo (per README) or $15/€15 (per spec). Lock for launch, A/B after first 50 paying users.

### 17.3 Post-launch v2 work queue

See `docs/IMPLEMENTATION_BACKLOG_v4.md §8` for prioritized list.
Key items: adversarial classifier test, ~200 phenomneology shading paragraphs, true lazy-create routing refactor, Marcus shading content (Phase 4 PR Β).

### 17.4 "Bring another mind" — preserved from v3

Still deferred until after Phase 5 (register architecture) so multi-persona output is meaningfully distinct.

---

## 18. CLAUDE.AI PROJECT KNOWLEDGE — STATUS (v4 patch)

**Files in Claude.ai Project Knowledge (updated for v4):**
- `PHILOSOPHER.docx` — product spec
- `HANDOFF_BRIEF_v4.md` — this document (NEW)
- `HANDOFF_BRIEF_v3.md` — preserved as historical reference
- `HANDOFF_BRIEF_v2.md` — preserved as historical reference
- `philosopher_brain/` — brain content (ALSO in repo at `apps/api/philosopher_brain/` since PR #5)
- `PROJECT_STATE_v4.md` — v4 patched 2026-05-05 with engine-first closure
- `IMPLEMENTATION_BACKLOG_v4.md` — engine-first closure §8 added 2026-05-05
- `DESIGN_SYSTEM_v4.md`, `SCREENS_TRACKING_v4.md`, `USER_FLOW_v4.md` — UX docs (paused, revisit post-launch)

---

## 19. ENGINE-FIRST SESSION LESSONS (NEW v4)

### 19.1 Full diffs, not grep summaries

The 1.7 hotfix (`0256f97`) was required because grep for `build_system` missed a caller at `conversation_service.py:159`. 10-minute production crash resulted. **Rule established:** for all parameter/schema changes, paste the full diff of every modified file before commit, and grep for every caller, then paste the diff of every caller — even those marked "no change needed." Grep summaries do not substitute for full diff trail.

### 19.2 Defense in depth over single-point fixes

The 1.5 empty-conversation fix used both backend dedup (eliminates duplicate rows even if two requests race) and frontend in-flight flag (eliminates the second request entirely). Either fix alone would have been insufficient: backend dedup doesn't prevent double-network UX; frontend flag doesn't prevent server-side race between concurrent requests from different render frames. **Design principle: layer independent defenses at each boundary.**

### 19.3 Conftest.py must own credential stubs

The first attempt to import `ConversationService` in tests failed because `embedding_client.py` instantiates `AsyncOpenAI` at module load time with an empty key. Fix: `conftest.py` now sets `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` as dummy values before any test module imports run. **Rule: all external client credentials needed for test module load must live in conftest.py, not in individual test files.**

### 19.4 message_count == 0 is the correct empty signal

Opening invocations are written to the `messages` table but do NOT increment `message_count`. Only user-message + assistant-reply pairs (via `stream_response` at line 252-258) increment by +2. Therefore `message_count == 0` is the exact condition for "user has never sent a message in this conversation." This is a non-obvious invariant — it would be easy to check `len(messages) == 0` and get wrong results (opener present → 1 message → non-zero). Document this whenever touching conversation creation logic.

---

## 20. DEPLOYMENT READINESS GAP — STATUS (v4 patch)

§20 from v3 now partially resolved:

- ✅ Backend deployed: Render (philosopher-api-z9l9.onrender.com)
- ✅ Database: Supabase (plecolxlzshkfvybszgs, eu-west-1)
- ✅ Frontend deployed: Vercel (thinkalike.vercel.app)
- ✅ API pointed at live backend (NEXT_PUBLIC_API_URL updated)
- ⏳ Redis: Not configured on Render (non-fatal warning at startup)
- ⏳ Stripe wiring: Paused, planned for ~2026-05-11
- ⏳ Cold smoke test: Not yet run post-engine-first session

§20.1 — §20.5 from v3 preserved for historical reference. Current deployment is live; the gap described in v3 is closed.

---

## END OF v4 ADDITIONS

If v4 conflicts with v3 anywhere, v4 wins. §1-14 unchanged from v1/v2/v3 — see `HANDOFF_BRIEF_v3.md` for full text of those sections.
