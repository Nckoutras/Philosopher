# IMPLEMENTATION BACKLOG v4 — Philosopher / Great Minds

> **What this file is:** Ordered list of implementation work by priority tier.
> Lives in Claude.ai Project Knowledge. Updated manually at session close.
> Sections §1-§7 cover UX, design system, screens tracking, and component
> backlog (paused during engine-first launch sequence — see §8 for status).

---

## §8. ENGINE-FIRST LAUNCH SEQUENCE — STATUS

**Updated: 2026-05-05. ENGINE-FIRST LAUNCH SEQUENCE: 7/7 P0 COMPLETE.**

### CLOSED (all shipped to main + production)

| Item | Commit | Notes |
|---|---|---|
| **Bug #33** — Safety pathway in-persona voice | fix/safety-crisis-pathway | Deterministic classifier-only path. LLM-side crisis directives removed. Medium risk now fully suppresses persona (spec divergence, defensible launch fix). |
| **Bug #34** — US-specific crisis copy → generic | fix/safety-crisis-pathway | Country-neutral copy. No hotline numbers. Generic language covering all regions. |
| **1.7** — user_name removal + hotfix | `0256f97` | Removed deprecated `user_name` kwarg. Hotfix for missed call site at conversation_service.py:159 that caused 10-min production crash. Discipline rule established: full diffs required, grep summaries do not substitute for caller audit. |
| **1.6** — Nietzsche removal from frontend landing | `c49c3cd` | Option A: removed from persona list display only. Backend YAML preserved for v2. |
| **1.4** — Phenomenology trigger audit | `ae58479` | +88 verb-form and gerund triggers across 32 entries. All high-frequency modern terms now have natural-language surface form coverage. |
| **2.1** — Phenomenology map content expansion | `54a8be4` | 33 → 78 entries. Adversarial submission reviewed by mentor. 45 new entries cover situationship, FOMO, love bombing, grindset, sunday scaries, hustle culture, burnout (expanded), and others. |
| **1.3** — Sentence-boundary truncation 3-layer fix | `2bf9244` | Layer 1: attempt-2 budget multiplier 1.0→1.15. Layer 2: strip-time sentence boundary trim with `hard_cut_no_sentence_boundary` fallback. Layer 3: `brevity_passed_but_mid_sentence` observability hook. 125→129 tests. |
| **1.5** — Empty-conversation dedup + in-flight flag | `718a7dd` | Backend: POST /conversations returns existing empty conv for (user, persona, ritual) tuple if message_count==0. Frontend: useState in-flight flag + disabled HTML attribute + animate-pulse visual. Defense in depth: backend dedup catches any frontend race window. 129→134 tests. |

### POST-LAUNCH BACKLOG (P3 — v2 work queue)

Prioritized order. None are launch blockers.

1. **~10 missing triggers** — `dating_apps` and `caregiving_burden` entries noted in 2.1 review as incomplete. Low ROI vs other entries; deferred.

2. **1.7 production smoke test** — Verify `user_name` removal in production. Already verified incidentally during burnout test session; formal smoke test deferred.

3. **Layer 3 observability follow-up** — If `brevity_passed_but_mid_sentence` fires >5% of qualifying replies in production, revisit with Option γ (track best full-sentence reply across regen attempts). Monitor via structured logs post-launch.

4. **~200 persona shading paragraphs** — 45 new phenomenology entries need per-persona shading content (how Marcus, Socrates, etc. would specifically address that concept). High-frequency entries first: situationship, FOMO, love bombing, grindset, sunday scaries.

5. **True lazy-create routing refactor** — Eliminates ALL empty conversation rows (including the 1-per-persona residual from the 1.5 fix). Requires routing refactor since URL is keyed by conversation UUID. v2 design, not launch scope.

6. **Adversarial classifier coverage test** — 30-50 novel crisis phrases → verify medium-or-higher escalation. Addresses residual risk from Bug #33 fix removing LLM-side crisis directives from prompt. P1 post-launch safety audit.

7. **Frontend race in same render frame** — Currently caught by backend dedup. True synchronous prevention would require `useRef` approach (flag set before re-render, not after). Theoretical edge case; backend defense makes it non-urgent.

8. **Marcus shading content (Phase 4 PR Β)** — Original founder spec. Deferred to post-launch.

---

> §1-§7 (UX, design system, screens, component backlog) paused during
> engine-first launch sequence. Will be revisited when launch-readiness
> tasks (cold smoke test, marketing, payment integration verification)
> are complete.
