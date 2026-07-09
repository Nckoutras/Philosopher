# THE WISE ROOM — Implementation Backlog v22

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v22 = v21 baseline (2026-06-26, through PR #374) + 2026-06-26→2026-07-09 delta (#376–#447):** the **Self-Portrait** feature shipped end-to-end (Pro-gated quiz → forming/ready portrait → radar + territorial map → shareable card → best-fit-to-chat; migration 039), plus **Counterview user-rebuttal turns** (038) + **still-stands** (041), the **Explore guides** build-out, **Council decision-architecture** (042), **dilemma/belief insight doorways** + Home room-noticed card, a **Home image-tile** redesign, and letters/YvY continuity beats. Migration head 037 → **042**.
> **v21 = v20 baseline + #339–#374:** Counterview ritual backfill, chat depth/router, letter write-back, onboarding profile, Home tiles + Explore tab; migrations 032–037. Full detail in `IMPLEMENTATION_BACKLOG_v21.md`.
>
> **Generated:** 2026-07-09 (v22 rotation) · **Last updated:** 2026-07-09 (current main `aa3ecafd`)
>
> **How to read this file:** This v22 file supersedes v21 and all prior backlog files. Where v22 conflicts with v21, v22 wins.
>
> **⚠️ Provenance:** the entire v22 delta (#376–#447) was built outside the v21→v22 working sessions and **reconstructed by reading merged code at `aa3ecafd`** — code-derived, not session-verified. Re-read the source before building on it.
>
> **Companion documents:** `PROJECT_STATE_v22.md`, `HANDOFF_BRIEF_v22.md`, `SCREENS_TRACKING_v10.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## 2026-07-09 Consolidation Summary — Self-Portrait · Counterview turns · Explore guides · Council decision architecture · insight doorways

> Appended as v22. Where this conflicts with earlier sections, this section wins. **Current main SHA `aa3ecafd`.**

**Code shipped (merged to main; #376–#447):**

| Area | What shipped | PRs |
|---|---|---|
| **Self-Portrait — quiz + backend** | 360-question bank / 12 categories (`data/question_bank.json`); `services/self_portrait.py` (tier gate `FREE_QUESTION_LIMIT=15`, breadth gate, forming/ready, cache); `GET /preferences/self-portrait`, `GET /preferences/self-portrait/portrait`, `PATCH /preferences/self-portrait`; answers stored in `user_preferences.profile["answers"]`; ARQ seed to memory + Sunday letters + YvY reinject. Migration 039 (`portrait_cache`). | #387, #388, #389, #390, #394 |
| **Self-Portrait — payoff** | Payoff 5a breadth gate + forming endpoint + cache column (039); 5b Sonnet summary + persona best-fit (bridge map, cached, regen + failure-cooldown, `self_portrait_summary.py`/`_prompts.py`); 5c view toggle + render + YvY cross-link. | #395, #396, #397 |
| **Self-Portrait — viz** | `PortraitRadar.tsx` (top-5 pentagon, compass rose, frame, denser fill); `PortraitMap.tsx` (Shape/Map toggle, static hand-drawn territories, rank names, dominant highlight, needle); Artwork/observation cards; deterministic summary line. | #400–#404, #407–#409, #411, #418–#427, #447 |
| **Self-Portrait — share + entry** | Client-canvas share card (`portraitShareCard.ts`, ungated, preview-first, recomposed to radar aesthetic); entry hero + wordmark + pill CTAs; category-coverage progress bar; best-fit → chat (prefilled first sentence). | #405, #410, #412, #416, #417, #423, #425, #437 |
| **Self-Portrait — tab + assets** | New **Self Portrait** tab (Easel icon, replaced Library in the bar); theme/card WebP set; rose/mirror compression; appbutton asset. | #388, #406, #413, #414, #415, #433 |
| **Counterview — rebuttal turns** | `counterview_turns` (038); `POST /counterview/{id}/respond` (bounded `MAX_REBUTTALS=3`, current speaker replies ≤18w, 409 on cap); rebut-in-place UI; `respond_to_rebuttal` + tests. | #376, #377 |
| **Counterview — still stands** | `counterviews.still_stands` (041) — one closing line naming what survives, same LLM call as verdicts (grounded-or-null). | #443 |
| **Explore guides** | "The Conversations" guide (+Council/Deep-mode blocks, sticky-guest fix); "Reflections & portraits" guide; "The room remembers" memory explainer; Explore index rewrite + pushable heroes + text-first. | #382, #428–#432, #434, #446 |
| **Council — decision architecture** | Essence brief distilled from chat (`council_prompts.py`); `council_sessions.synthesis_structured` (042) — real_question/tension/verdict/next_move; flat `synthesis` retained for feed/share. | #386, #444 |
| **Insight doorways** | Dilemma/belief signal detection via memory extraction (`memory_service.py`); chat doorway chips (`InsightCard.tsx`); Home "The room noticed" card (`RoomNoticedCard.tsx`, `useInsightDoors.ts`). | #438, #439, #440 |
| **Home redesign** | Image-card 2×2 tiles + Discuss route (`discuss/page.tsx`, `useTopicConversation.ts`); relocate Continuing/Reflections; centered tile words; priority images; LQIP blur (`mint-image-lqip.py`). | #378, #379, #384, #393 |
| **Letters** | Sunday next-reading line + UTC fix; sign-off + Frame icon; persona thumbnails; practical takeaway + continuity; "something new" star for unread letters (`LettersBootstrap.tsx`); prefill on suggested-persona tap; "What went unspoken" avoidance line. | #380, #391, #392, #398, #399, #436, #445 |
| **You vs You** | YvY reinject + edit-as-change signal; hidden continuity + sentence-owed beats; save "sentence you owe yourself" → Reflections (`self_comparison_saves` 040, `YvYSentenceCard.tsx`). | #389, #441, #442 |
| **Chat / store / polish** | "Take to Council" → quick-action chip; conv/[id] resilience (opening fallback, 404, Continuing sync); reflections per-kind type marker; `store.ts` `plan` as real state (persist-freeze fix). | #385, #435, #381, #383 |

**Migrations:** 038 counterview_turns, 039 portrait_cache, 040 self_comparison_saves, 041 counterview_still_stands, 042 council_synthesis_json. Head → **`042_council_synthesis_json`**. All ids ≤ 32 chars; filenames == revision ids (C-04).

**Corrections applied this rotation (see §3.CORR):**
- **REMOVED** the false "Letter to Future Self — ARQ delivery not wired / still open" item — **delivery is LIVE** via APScheduler (`workers/cron.py:133–204`).
- **ADDED** `rituals.ts:42` copy item (OPEN — founder call) and the `insights.source_count` design-confirmation item.

**Closed / corrected this session:**
- **Letter to Future Self delivery** → was 🟡 "ARQ delivery not wired" → 🟢 **LIVE (APScheduler)**. Item removed from the backlog (not deferred).

---

## Earlier consolidation summaries (v16 → v21)

Carried forward by reference. See `IMPLEMENTATION_BACKLOG_v21.md` (v21 #339–#374) and `IMPLEMENTATION_BACKLOG_v20.md` (v20 and earlier).

---

## 1. Current Launch Interpretation

**Plan A (active).** Priority order as of 2026-07-09:

1. **PR3a memory bugs — 🟡 partially addressed (#435 conv/[id] resilience: opening fallback, graceful 404, Continuing-card sync).** Verify on smoke test whether the fresh-chat missing-opening-message/thumbnail + "Continuing" 404 symptoms are fully closed; if not, remaining work stays the highest cold-beta blocker.
2. **Cold beta with 3–5 fresh users** — once memory bugs confirmed resolved.
3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
5. **TD-37 — wire or retire the dormant brevity post-check** (post-first-paying-user).
6. **App-icon mark (TD-29).**
7. Self-Portrait / Counterview / Council / YvY / Mirror fast-follows (post-first-paying-user).

Prior completed items (Mirror, Council, YvY, Counterview, **Self-Portrait**, TD-11, BETA off, Stripe sandbox, Oregon, Sunday Letter reader + email + season finale + **future-self delivery**, Reflections feed, Insight engine, Orwell/Musashi, WebP) — see above / v21 / v20.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt (TD-23)** — add `.env.local`, `.env*.local`. Single-file commit.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### 2.1 Infrastructure P0

- [x] ~~Oregon migration~~ — confirmed.
- [ ] **source_chunks re-ingest** into Oregon (TD-22).
- [ ] **Post-Oregon smoke test** — now also **Self-Portrait** (quiz gate, forming→ready, radar/map toggle, share card, best-fit→chat), **Counterview rebuttal turns**, **Explore guides**, **Council decision-architecture synthesis**, **insight doorways / Home room-noticed**.
- [ ] **`API_BASE_URL` set to public backend URL** on Render API (else weekly/season **and future-self** emails suppressed — `DEPLOY_NOTES.md`).
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation.**

### 2.2 Code-side P0

- [ ] **PR3a memory bugs** — verify #435 fully closed the fresh-chat opening/thumbnail + "Continuing" 404 symptoms.
- [ ] **bugfixes-3 — auth race fix** (TD-10).
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari) — include the **Self-Portrait** tab (quiz, radar/map, share), **Counterview rebuttal exchange**, the **Home image tiles + Discuss route**, and the **Explore guides**.
- [ ] **Cold beta with 3–5 fresh users.**
- [ ] **Consolidated polish PR** (Block B visual closure).

### 2.3 Legal P0 / 2.4 Infra P0 / 2.5 UAT P0

Unchanged from v20/v21 (lawyer review, GDPR/DPA, runbooks, DNS + Resend domain, UAT ≥2/5 "I'd pay"). See `IMPLEMENTATION_BACKLOG_v21.md §2`.

---

## 3. Tech debt items

### TD-01 through TD-37

Unchanged from v21 except as noted. See `IMPLEMENTATION_BACKLOG_v21.md §3`. Still-open highlights: TD-10 (Zustand hydration race), TD-22 (source_chunks re-ingest), TD-23 (.gitignore), TD-24 (render.yaml sync:false), TD-26 (Council share redesign), TD-27 (per-verdict saves), TD-28 (live Stripe), TD-29 (app-icon mark), TD-31/34/35/36 (caching/tuning), **TD-37 (dormant brevity post-check — still 🟡 wired but inert; wire or retire post-first-paying-user).** **TD-25 (compress mirror.png) → 🟢 DONE (#414, mirror.png → mirror.webp).**

### CORR — Corrections to prior docs (v22)

> Verified against merged code at `aa3ecafd`. These correct claims in v21 that no longer (or never) matched reality.

- **CORR-01 — Future-Self delivery is LIVE (removes the v21 open item).** v21 backlog (§9.7 line 145, §11.2 line 186) listed *"Letter to Future Self — ARQ email delivery wiring (still open)."* **FALSE.** Delivery ships via **APScheduler**, not ARQ: `send_pending_future_self_emails` (`apps/api/workers/cron.py:133–204`, `AsyncIOScheduler` + `IntervalTrigger(minutes=5)`) delivers pending `ScheduledEmail` rows via `send_email`. The item is **removed**, not deferred. (Operational dependency: `API_BASE_URL`/asset base must be set — same as weekly/season email.)

### TD-38 — `rituals.ts:42` stale copy (P2, NEW — 🟡 OPEN, founder call)

`apps/web/lib/rituals.ts:42` — the `'future-self'` ritual body reads *"It isn't sent anywhere; the room keeps it as your stated direction."* This describes the future-self **direction declaration** (feeds Sunday/monthly readings; genuinely not emailed). BUT the same-named **scheduled "Letter to Future Self"** (`ScheduledEmail`, `routers/scheduled_emails.py`) DOES email the user via the live cron (CORR-01). The copy is arguably correct for the declaration yet misleading given the emailing feature exists. **Decide:** reword, or leave (two distinct features sharing a name). Not asserted as a confirmed bug — flagged for judgment. Frontend-only change if reworded.

### TD-39 — `insights.source_count` split (P3, NEW — confirm intended)

NOT "never populated." `services/memory_service.py:363,421` (`detect_recurrence`) sets `source_count = len(distinct prior conversations)+1`; the dilemma/belief **signal** path (`memory_service.py:181–187`, #438) deliberately sets `source_count=None` ("not a cross-conversation recurrence"). The provenance line renders only when `source_count >= 2`, so signal-path insights omit it by design. **Confirm the split is intended** (recurrence carries provenance; signals don't). No code change unless the product wants signals to carry a count.

---

## 4. Database schemas

Migration head: **`042_council_synthesis_json`** (chain …037 → 038 → 039 → 040 → 041 → 042). New since v21:

- **038** `counterview_turns` (bounded user rebuttal exchange; own table, verdict/round axis untouched).
- **039** `user_preferences.portrait_cache` JSONB (Self-Portrait summary/best-fit cache; nullable no-op).
- **040** `self_comparison_saves` (soft-delete; feeds Reflections; mirrors `counterview_saves`).
- **041** `counterviews.still_stands` TEXT (closing "what still stands" line; nullable).
- **042** `council_sessions.synthesis_structured` JSONB (decision-instrument close; flat `synthesis` retained).

All revision ids ≤ 32 chars; filenames == revision ids (C-04). Full table list: `PROJECT_STATE_v22.md §4`.

---

## 5–8.

Config/env (§5 — `API_BASE_URL` operationally required for weekly/season **and future-self** email), Stripe wiring (§6 — sandbox complete, live pending TD-28), persona maintenance (§7 — Self-Portrait best-fit ranks the 11 personas), LLM eval (§8) — unchanged from v20/v21 except as noted. See `IMPLEMENTATION_BACKLOG_v21.md`.

---

## 9. Future blocks reference

### 9.1–9.6

Unchanged from v19–v21.

### 9.7 Rituals (updated v22)

| Ritual | Status | Notes |
|---|---|---|
| **Letter to Future Self** | 🟢 **LIVE — delivery wired (APScheduler)** | `send_pending_future_self_emails` cron (`workers/cron.py:133–204`) sends `ScheduledEmail` rows every 5 min. **Corrects the v21 "delivery not wired" claim (CORR-01).** See TD-38 for the rituals.ts copy question. |
| The Mirror | 🟢 SHIPPED + insight-seeded | Unchanged. |
| The Council | 🟢 SHIPPED + Chat → Council (v21) **+ decision-architecture synthesis (v22, #444)** | `synthesis_structured` real_question/tension/verdict/next_move; flat synthesis retained. |
| You vs You | 🟢 SHIPPED **+ sentence-owed save → Reflections (v22, #442)** | Also sees onboarding profile + Self-Portrait answers. |
| Weekly Reading / Sunday Letter | 🟢 reader + email + season finale + write-back **+ takeaway/continuity/avoidance-line (v22)** | Unchanged delivery. |
| The Counterview | 🟢 SHIPPED (v21) **+ bounded user rebuttal turns + still-stands closing (v22, #376/#377/#443)** | `MAX_REBUTTALS=3`; `counterview_turns` (038); `still_stands` (041). |
| **The Self-Portrait** | 🟢 **NEW — SHIPPED (v22, #387–#427, #437, #447)** | Pro-gated quiz (360 Qs / 12 cats; free 15); forming→ready portrait (breadth gate); Sonnet summary + persona best-fit (cached, 039); radar + territorial map (Shape/Map toggle); client-canvas share card; best-fit→chat. New **Self Portrait** tab. |

### 9.8–9.11

Unchanged from v19–v21 (fast-follows). **Self-Portrait is now shipped; remaining Self-Portrait work is tuning (breadth gate, regen delta, free-question count, best-fit weights) and any v2 depth.**

---

## 10. Operating principles

Unchanged from v21. P-01 through P-07 + persona/migration conventions **C-01..C-04** in `CLAUDE.md`.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt (TD-23).**
- [ ] **Author smoke-test voice changes** — 6 personas.
- [ ] **PR3a memory bugs** — verify #435 fully closed them.

### 11.1 P0 (launch blockers)

- [x] ~~Through v21: Mirror, Council, YvY, Counterview, Insight engine, weekly email, season finale, Stripe sandbox, BETA off, TD-11, Oregon, Orwell/Musashi, WebP, Home tiles + Explore tab~~ — DONE.
- [x] ~~**Self-Portrait feature**~~ ✅ DONE (#387–#427, #437, #447).
- [x] ~~**Counterview rebuttal turns + still-stands**~~ ✅ DONE (#376, #377, #443).
- [x] ~~**Letter to Future Self delivery**~~ ✅ **LIVE (APScheduler)** — CORR-01.
- [ ] **PR3a memory bugs** — verify.
- [ ] **source_chunks re-ingest** (TD-22); **Post-Oregon smoke test**; **auth race** (TD-10); **mobile nav smoke test**; **TD-28 live Stripe**; **OPS-001 re-sync**; **cold beta**; **consolidated polish PR**; **lawyer review**; **DNS + Resend**; **GDPR/DPA**; **runbooks**; **`PHENOMENOLOGY_BRIDGE_ENABLED`**; **RLS**; **UAT ≥2/5 "I'd pay"**.

### 11.2 P1 (post-revenue)

- [ ] **OPS-001 re-sync.**
- [ ] **TD-29 App-icon mark.**
- [ ] **TD-37 — wire/retire dormant brevity post-check.**
- [ ] **TD-38 — `rituals.ts:42` future-self copy** (founder call: reword vs leave).
- [ ] **TD-39 — confirm `insights.source_count` recurrence-vs-signal split is intended.**
- [ ] **`/app/profile` → Explore-tab entry point** (route exists, no nav link).
- [ ] **Per-verdict → reflections save** (TD-27); **Council share redesign** (TD-26).
- [ ] **TD-05 — wire/retire `generate_insight_task`.**
- [ ] **TD-10**; **I1 Account hub**; **A6+A7 disclaimer integration tests**; **OTP-01 investigation**; **TD-24 render.yaml sync:false**.

### 11.3 P2 (tech debt / tuning)

- [ ] **Self-Portrait tuning** — breadth-gate thresholds, `PORTRAIT_REGEN_DELTA=8`, `FREE_QUESTION_LIMIT=15`, best-fit bridge-map weights; tune on cold-beta volume.
- [ ] **Adaptive-length thresholds (15/50) + go-deeper free limit (3/day)** — tune on volume.
- [ ] **Counterview voice/threshold tuning** — fixed pair, 10-word cut, `MAX_REBUTTALS=3`. Fuller multi-round flow (v2).
- [ ] **Letter write-back fed-forward truncation** — no max-length cap.
- [ ] **Insight-seeding from letter write-back** (OUT of v1).
- [ ] **TD-35 insight threshold tuning**; **TD-36 cache/async sync insight-mirror generate**; **TD-34 cache Reading Revisit**; **TD-31 cache YvY forming reflection.**
- [ ] **ChatGPT audit** of persona configs (incl. Orwell + Musashi).
- [ ] TD-12 soft-delete conversations; TD-01 split rate_limit_service; TD-02 PersonaConfig naming; TD-03 ANTHROPIC_MODEL; TD-08 document Render alembic auto-run; branding resolution; extract Lao Tzu/Wilde/Machiavelli to YAML; TD-20/TD-21.
- [ ] **~~Home tiles → custom images~~** — 🟢 addressed (#378 image-card tiles); verify this closes the v21 parked item.

### 11.4 P3 / 11.5 P4

Unchanged from v21 (modal abstraction, desktop polish, Phase 5 Council premium, eval suite/CI, YvY funnel analytics; TD-04/06/07/14, openapi.json→.gitignore, legal-link rel hardening, stale-branch cleanup). Plus **TD-39** (source_count split). See `IMPLEMENTATION_BACKLOG_v19.md §11.4/11.5`.

---

## 12. Plan A vs Plan B

Unchanged from v21. Plan A active. With **all rituals shipped (Self-Portrait added; Counterview extended; future-self delivery confirmed live)**, the remaining launch path is dominated by PR3a memory-bug verification → cold beta → live Stripe wiring. No ritual design/build work remains on the critical path.

---

**End of IMPLEMENTATION_BACKLOG v22.** Authoritative as of 2026-07-09. Supersedes `IMPLEMENTATION_BACKLOG_v21.md` (preserved as historical reference).
