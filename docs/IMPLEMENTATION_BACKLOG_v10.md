# GREAT MINDS — Implementation Backlog v10

> **Purpose:** Source of truth for implementation work for Great Minds / Philosopher v1 launch.
> **v10 = v9 baseline (2026-05-20) + 2026-05-21/22 session delta (PR3a–PR4h shipped; cron hotfix; Render Background Worker deployed; migration 012; new P0 items: ΚΑΔ addition, Resend domain, Stripe live mode; corrections A + B applied).**
>
> **Generated:** 2026-05-22
>
> **Last updated:** 2026-05-22. PR3a–PR4h wave completed (16 items closed). New P0 items added: ΚΑΔ addition (P0-09), Resend domain (P0-01), Stripe live mode (P0-02). Brand rebrand decision captured as deferred blocker. Web service upgrade to Starter confirmed complete (Correction A).
>
> **Companion documents:**
> - `PROJECT_STATE_v10.md` — current project state
> - `HANDOFF_BRIEF_v10.md` — continuity and implementation history
> - `SCREENS_TRACKING_v4.md` — full screen inventory (v4.2 update)
> - `DESIGN_SYSTEM_v4.md` + addenda — visual spec
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

# 1. Completed since v9 (PR3a–PR4h wave)

All items below closed between 2026-05-20 and 2026-05-22.

| # | Item | Closed by | Date |
|---|---|---|---|
| 1 | PR3a — B1/B3/B6 mobile bug fixes + polish (consolidated polish PR closure) | PR3a #80 | 2026-05-20 |
| 2 | PR3b — Share screenshot generation (`POST /api/v1/share`, `image_service.py`) | PR3b #81 | 2026-05-20 |
| 3 | PR3c — Scheduled emails backend (migration 012, router, template, cron jobs) | PR3c #82 | 2026-05-21 |
| 4 | PR3c — Rituals card + BottomSheet + RitualScheduleSheet frontend | PR3c #82 | 2026-05-21 |
| 5 | PR4a — Conv-not-found fix (`GET /conversations/{id}`) | PR4a #83 | 2026-05-21 |
| 6 | PR4a — 422 Pydantic error formatting in `api.ts` | PR4a #83 | 2026-05-21 |
| 7 | PR4a — Mobile safe-area (BottomSheet `svh`, safe-area-inset-bottom) | PR4a #83 | 2026-05-21 |
| 8 | PR4b — Today's topic card (`TodaysTopicCard`, `skip_opening` flag) | PR4b #84 | 2026-05-21 |
| 9 | PR4c — 'Letter to future self' rename | PR4c #85 | 2026-05-21 |
| 10 | PR4c — 5-year scheduling max | PR4c #85 | 2026-05-21 |
| 11 | PR4c — `AppHeader` on all 4 tab pages | PR4c #85 | 2026-05-21 |
| 12 | PR4c — Auth back-button fix (`router.push` → `router.replace`) | PR4c #85 | 2026-05-21 |
| 13 | PR4c — Chat error link → 'Home' → `/app/today` | PR4c #85 | 2026-05-21 |
| 14 | Cron hotfix — `enqueue()` → `enqueue_job()` in `cron.py` | Hotfix #86 | 2026-05-21 |
| 15 | PR4d — Share card 1080×1350 + bottom-anchored footer + Bronze opacity | PR4d #87 | 2026-05-21 |
| 16 | PR4e — Sign Up / Sign In distinction + mode-aware email copy | PR4e #88 | 2026-05-21 |
| 17 | PR4f — Swipe-to-delete Reflections + Library with undo toast | PR4f #89 | 2026-05-21 |
| 18 | PR4g — Saved-line picker with thumbnails + custom highlight | PR4g #90 | 2026-05-21 |
| 19 | PR4h — Splash redesign, full-bleed chesterfield hero | PR4h | 2026-05-21/22 |
| 20 | Render Background Worker deployed (`philosopher-worker`, Starter, Oregon, $7/mo) | Operational | 2026-05-21/22 |
| 21 | Web service upgrade to Render Starter ($7/mo, eliminates cold-start) | Operational | 2026-05-21/22 |

---

# 2. Current launch sequence

Priority order as of 2026-05-22:

1. **Resend domain verification** (P0 — blocks cold beta OTP)
2. **Greek ΚΑΔ addition** (P0 — hard prerequisite for Stripe live mode)
3. **Brand rebrand decision** (soft-blocks Resend domain choice)
4. **Stripe live mode migration** (P0 — after ΚΑΔ + Resend)
5. **End-to-end Stripe sandbox test** (P0 — before cold beta)
6. **Backfill-titles admin execution** (P0 — one-time founder action)
7. **Cold smoke test with 5–7 fresh users** (P0 — requires Resend domain live)
8. **Lawyer review** (P0 — parallel)
9. **DNS / thegreatminds.app** (P0 — parallel)
10. **GDPR / DPA infrastructure** (P0 — parallel)
11. **Founder runbooks** (P0 — parallel)

---

# 3. P0 — Launch blockers (open)

### P0-01 — Resend domain verification

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Cold beta OTP delivery fails for non-Gmail addresses on the test sender (`onboarding@resend.dev`). Corporate domains (e.g. `@ote.gr`) confirmed blocked. Must verify either a utility domain (fastest path for testing) or `thegreatminds.app` / new branded domain. Resend domain choice is soft-blocked by the brand rebrand decision (DEF-01). Unblocks P0-04 (cold smoke test).

---

### P0-02 — Stripe live mode migration

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Currently in Stripe test mode. Live mode requires: (1) ΚΑΔ addition complete (P0-09 — hard prerequisite), (2) Stripe account identity verification and business activation, (3) swap `STRIPE_SECRET_KEY` and `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` from test to live values in Render + Netlify, (4) delete and re-register webhook endpoint with live secret → update `STRIPE_WEBHOOK_SECRET` in Render, (5) smoke test checkout → webhook → entitlement → portal → cancel with real card. No real payments can be taken until this is complete.

---

### P0-03 — End-to-end Stripe sandbox test

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Carried from v9. Before switching to live mode, verify the full sandbox flow end-to-end: Stripe test card → checkout session → webhook delivers → subscription entitlement updates → Customer Portal opens → cancel → verify tier downgrade. Required confidence gate before P0-02 (live mode).

---

### P0-04 — Cold smoke test with 5–7 fresh users

**Priority:** P0 | **Status:** 🔴 not started
**Context:** End-to-end signup → OTP → onboarding → conversation → (optional) Stripe upgrade, using users who have never touched the app. Requires P0-01 (Resend domain) so OTP delivery works. Target: 5–7 users, at least some from non-Gmail domains. Validates the full funnel before public launch.

---

### P0-05 — Backfill-titles admin endpoint execution

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Run `POST /api/v1/admin/backfill-titles` on production to generate titles for existing untitled conversations. One-time founder action via API call or Render shell. Not a code change.

---

### P0-06 — Lawyer review of legal templates

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Carried from v9. ToS v1.1, Privacy v1.1, Disclaimer v1.0 need review for: Greek consumer law, Stripe billing T&Cs, AI-content liability, GDPR Article 6 lawful bases, processors table, DPO contact. Not a coding task.

---

### P0-07 — DNS configuration for `thegreatminds.app`

**Priority:** P0 | **Status:** 🟡 uncertain
**Context:** Was "IN PROGRESS" in v9; current status unknown. DNS records + SSL provisioning for `thegreatminds.app`. Soft-blocked by brand rebrand decision (DEF-01). Verify current state before cold beta.

---

### P0-08 — GDPR / DPA infrastructure

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Carried from v9. Required: DPA with Anthropic (for chat data), processors documentation, data subject request fulfillment workflow, cookie posture, privacy contact email.

---

### P0-09 — Greek ΚΑΔ addition to ΕΕ company

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Founder's existing ΕΕ company is registered with real estate ΚΑΔ only. Stripe live mode activation requires business activity to match the registered ΚΑΔ. Must add a software/digital ΚΑΔ via TAXISnet form Μ2 before attempting Stripe live mode. Candidate ΚΑΔ codes:
- `62.01.21.06` — Έκδοση λογισμικού ψυχαγωγίας
- `62.01.29.04` — Άλλες υπηρεσίες ανάπτυξης λογισμικού
- `63.12.10` — Υπηρεσίες διαδικτυακών πυλών

**Hard prerequisite for P0-02 (Stripe live mode).** Not a coding task.

---

### P0-10 — Founder runbooks

**Priority:** P0 | **Status:** 🔴 not started
**Context:** Carried from v9. Required runbooks: refund, account recovery, GDPR fulfillment, cancellation override, safety escalation.

---

### P0-11 — PHENOMENOLOGY_BRIDGE_ENABLED flag confirmation

**Priority:** P0 | **Status:** 🔴 not verified
**Context:** Was `true` on 2026-05-04/05; current Render env state unknown. Confirm before cold smoke test.

---

# 4. P1 — Post-launch, pre-first-paying-user

### P1-01 — Memory extraction JSON parse fix

**Priority:** P1 | **Status:** 🟡 pending verification
**Context:** `extract_memory_task` calls `memory_service.extract_and_store()`, which parses LLM output as JSON. If the LLM wraps its response in markdown fences (` ```json ... ``` `), `json.loads()` will fail. A defensive strip (strip the fence wrapper before parse) is not yet applied. **Verify with fresh task logs from the deployed worker first. Only implement if issue persists in production.**

---

### P1-02 — Marketing copy + landing page

**Priority:** P1 | **Status:** 🔴 not started
**Context:** A0 landing page exists at `/` but has minimal copy. Pre-launch marketing surface needs value prop, social proof structure, CTA hierarchy. Soft-blocked by brand rebrand decision (DEF-01) — copy referencing "Great Minds" may need revision.

---

### P1-03 — Wire `generate_insight_task`

**Priority:** P1 | **Status:** 🔴 not started (see TD-05)
**Context:** `generate_insight_task` is defined in `arq_worker.py` and registered in `WorkerSettings.functions` but is never enqueued by any router or cron job. Requires ≥4 organic memory entries to produce a meaningful signal. Defer until real users accumulate sufficient memory via `extract_memory_task`.

---

### P1-04 — C6c cold-start screen

**Priority:** P1 | **Status:** 🔴 not started
**Context:** Demoted from P0 on 2026-05-18. Web service is now Render Starter (no idle cold-start). Cold-start screen would still improve UX during any transient slow response. Not a launch blocker.

---

### P1-05 — I1 Account hub build

**Priority:** P1 | **Status:** 🔴 not started
**Context:** Spec locked in `SCREENS_TRACKING_v4.md`. Tab bar reachable via D1 (done). Functional value (subscription management, sign-out, plan changes) requires Block H wiring (Stripe live mode). Becomes co-requisite once live mode lands.

---

### P1-06 — A4 mailto visible support email fallback

**Priority:** P1 | **Status:** 🔴 not started
**Context:** When `support@thegreatminds.app` mailbox exists, surface it in Help & support screen (A4). Soft-blocked by DNS + brand decision.

---

### P1-07 — A6+A7 disclaimer endpoint integration tests

**Priority:** P1 | **Status:** 🔴 not started
**Context:** Carried from v9. Shipped without tests for speed. Add before first paying user.

---

# 5. Deferred / Blocked

### DEF-01 — Brand rebrand decision (Great Minds saturation concern)

**Status:** ⏸ blocked on founder decision
**Context:** Concern that "Great Minds" is too common a phrase for effective brand differentiation. This decision blocks: Resend domain choice, `AppHeader` copy, email template branding, share card wordmark, splash copy. No implementation of brand-dependent items until decision lands. Soft-blocks P0-01 (Resend domain), P0-07 (DNS), P1-02 (marketing copy).

---

### DEF-02 — PR4d.1 share card vertical centering

**Priority:** P3 | **Status:** ⏸ deferred
**Context:** Only if the quote/portrait block appears skeletal or off-center on real Instagram share. Verify in production before implementing. Do not implement speculatively.

---

# 6. P3 — Post-launch

### P3-01 — Region migration Oregon → Frankfurt

**Context:** Both Render services (web + worker) are in Oregon (us-west-2). Supabase is in eu-west-1. For EU-majority user base, migrating Render to Frankfurt would reduce latency ~370ms per request. Low urgency until user base has meaningful EU concentration. Requires: new Render services in Frankfurt, env var migration, DATABASE_URL routing verification, Oregon service decommission.

---

### P3-02 — Render Environment Groups migration

**Context:** Web service + worker share ~15 env vars. Environment Groups would deduplicate and reduce drift risk when env vars change. Low urgency.

---

### P3-03 — Desktop layout polish

**Context:** Mobile-first build looks broken above 768px. Post-feedback priority once mobile UX is validated.

---

### P3-04 — Phase 5 register architecture + UI chips + LLM classifier

**Context:** Deferred from Decision #6. Post-feedback; revisit after sufficient safety event data accumulates.

---

# 7. P2 — Tech debt (TD-01 through TD-09, carried from v9)

No new tech debt items added in PR3/PR4 wave (clean build).

### TD-01 — Split `rate_limit_service.py`

**Priority:** P2 | **File:** `apps/api/services/rate_limit_service.py`

Two unrelated rate limiters in one file: `check_and_increment()` (Redis/OTP) + `check_rate_limit()` (DB/daily messages). Split into `services/auth_rate_limit.py` + `services/message_rate_limit.py`. Not a launch blocker.

---

### TD-02 — PersonaConfig / Persona ORM naming confusion

**Priority:** P2 | **Files:** `apps/api/personas/_base.py`, `models/__init__.py`, `services/persona_voice.py`

`PersonaConfig` (in-memory dataclass) ≠ `Persona` (ORM model). `get_error_voice()` reads `getattr(persona, "config", None)` — works on ORM object, silently falls back on `PersonaConfig`. Current streaming path is correct (passes ORM object). Rename `PersonaConfig` to `PersonaBrainConfig` or add a `NotImplementedError` guard.

---

### TD-03 — Update or remove `ANTHROPIC_MODEL` constant

**Priority:** P2 | **File:** `apps/api/config.py`

`ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"` — stale Sonnet 4 default. Not read by `conversation_service.py`, which uses `MODEL_FREE`/`MODEL_PRO` literals. Remove or update before it misleads future engineers.

---

### TD-04 — C-RECON-6 backoff discrepancy

**Priority:** P4 | **File:** `apps/api/services/conversation_service.py`

PATH A retry loop: `asyncio.sleep(2**attempt)` with `attempt` starting at 0 → 0s, 2s, 4s. Document as intentional or change to start at 1 (2s, 4s, 8s).

---

### TD-05 — Wire `generate_insight_task`

**Priority:** P1 | **File:** `apps/api/workers/arq_worker.py`

`generate_insight_task` defined and registered in `WorkerSettings.functions` but never enqueued. Defer until ≥4 organic memory entries accumulate. See P1-03 above.

---

### TD-06 — `safety_events.message_id` always NULL

**Priority:** P4 | **File:** `apps/api/services/conversation_service.py`

Safety events log correctly by user_id/conversation_id/timestamp; message FK not wired. Minor cleanup; not a launch blocker.

---

### TD-07 — `gh` CLI installation on founder's Windows

**Priority:** P4

`winget install --id GitHub.cli` — currently PR creation requires GitHub web UI link from `git push`. Minor inconvenience.

---

### TD-08 — Document Render alembic auto-run mechanism

**Priority:** P2

Alembic runs `upgrade head` on Render container startup. The exact mechanism (Procfile? Dockerfile CMD? render.yaml?) is undocumented. Document before the next engineer touches the deployment pipeline or before a migration fails on startup. Has worked reliably through 012 migrations.

---

### TD-09 — One-fix-per-PR rule (process discipline)

**Priority:** P4

Post-mortem from bugfixes-2 (PR #72) production fire: auth hydration guard bundled with unrelated store fix caused 2h outage. Rule: one logical fix per PR. Auth/hydration changes require isolated PR + mandatory mobile smoke test on preview URL before merge. Process rule only — no code change.

---

# 8. Future blocks reference

### 8.1 Block C — COMPLETE

C5 (Chat UI), C3a (RAG infrastructure), C3b (corpus ingestion), C9a (PersonaPickerSheet) all complete. C9b (inline second-opinion response) demoted to P2 post-revenue.

### 8.2 Block D — D1 COMPLETE

D1 Home/Today: complete (PR #76 + PR4b). D2/D3: not planned. D4: deferred v2.

### 8.3 Block F — Reflection (F1-F6)

F1 (Saved reflections): live. F6 (Past conversations): live. F2 lite, F3, F4 demoted to P2 post-revenue. F5: deferred v2.

### 8.4 Block H — Stripe sandbox COMPLETE

Checkout + portal + webhook live. Live mode migration pending (P0-02 + P0-09).

### 8.5 Block I — Account & Settings

I1 Account hub: P1 (spec locked). I2–I6: not yet planned.

### 8.6 Block J — Empty states

J1–J3, J5 specced. Not yet built.

---

# 9. Operating principles (preserved)

Full text in `HANDOFF_BRIEF_v9.md` §19 and `HANDOFF_BRIEF_v10.md` §5. Key additions since v9:

### 9.1 ARQ API — `enqueue_job()` not `enqueue()` (NEW v10 — 2026-05-21)

ARQ's `ArqRedis` class uses `enqueue_job()`, not `enqueue()`. The cron hotfix was a 1-line change that prevented `AttributeError` on every cron fire. Rule: verify ARQ method name against the `arq` library docs before wiring any new cron job.

### 9.2 Cron job verification before worker goes live

Apply and verify all APScheduler job fixes before bringing the worker online. Test cron logic in isolation (unit tests for each scheduler job function) before relying on production execution.

---

**End of IMPLEMENTATION_BACKLOG v10.** Authoritative as of 2026-05-22. Supersedes `IMPLEMENTATION_BACKLOG_v9.md` (preserved as historical reference).
