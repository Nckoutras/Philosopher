# THE WISE ROOM — Implementation Backlog v20

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v20 = v19 baseline (2026-06-16, through PR #316) + 2026-06-21 session delta (#317–#337):** the **Insight engine** shipped end-to-end (recurrence + shift detector wired into the ARQ memory task; in-chat chip; Today insight card + brand seal; provenance line; three-action card), the **Insight → Mirror loop** (`POST /insights/{id}/reflect` + insight-seeded reader), **weekly-letter email delivery** (closes TD-33) synthesized from the insight spine, and the **monthly "season finale"** reusing the weekly engine. Migrations 028–031; head → `031_mirrors_insight_id`.
> **v19 = v18 baseline + #315–#316:** WebP portrait standard (026), Orwell + Musashi (027), roster 9 → 11. Full detail in `IMPLEMENTATION_BACKLOG_v19.md`.
>
> **Generated:** 2026-06-21 (v20 rotation) · **Last updated:** 2026-06-21 (insight engine + insight→Mirror + weekly email + season finale; current main `4c4221c9`)
>
> **How to read this file:**
> - This v20 file supersedes v19 and all prior backlog files. Where v20 conflicts with v19, v20 wins.
>
> **Companion documents:** `PROJECT_STATE_v20.md`, `HANDOFF_BRIEF_v20.md`, `SCREENS_TRACKING_v8.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## 2026-06-21 Consolidation Summary — Insight engine · Insight→Mirror loop · Weekly email · Season finale

> Appended as v20. Where this conflicts with earlier sections, this section wins. **Current main SHA `4c4221c9`.**

**Code shipped (merged to main; #317–#337):**

| Area | What shipped | PRs |
|---|---|---|
| **Insight engine (recurrence + shift)** | `services/memory_service.py:detect_recurrence` — cosine recurrence (`SIM 0.75`, `MIN_PRIOR 1`, `THROTTLE 6h`) + one classify+phrase call deciding `pattern` (default) vs `shift` (hedged). **Wired into the ARQ `extract_memory_task`** (runs after memory extraction commits). In-chat quietly-glowing chip → `InsightCard`. | #323, #324 |
| **Today insight card + seal** | Today surfaces the insight spine as a passive standing card (`variant='today'`, `TODAY_INSIGHT_MAX_AGE_DAYS=14`); brand-seal ornament (`/insight_seal.png`); cleaner primary CTA; "Dismiss" reworked. | #327, #332 |
| **Provenance line** | `insights.source_count` (030); card shows "Noticed across {N} of your conversations" when `source_count >= 2`. | #333 |
| **Three-action card** | Reflect in the Mirror (primary) · Doubt this (→ `/app/counterview` stub; does NOT dismiss) · Discard this (dismiss). | #334 |
| **Insight → Mirror loop** | `POST /insights/{id}/reflect` → `services/insight_mirror_service.py:generate_insight_mirror` (sync; dedup by `insight_id`; `kind="insight"`; safety/empty gates; reuses mirrors serializer). Migration 031 (`mirrors.insight_id` + `ck_mirrors_kind` allows `insight` + partial unique index). `get_latest_mirror` excludes `kind="insight"`. Reader seeds via `?insightId=`. | #335, #336, #337 |
| **Weekly letter email + insight spine** | `generate_weekly_letter_task` synthesizes from the period's non-dismissed insights (`<what_the_room_noticed>` spine); `_maybe_send_weekly_letter_email` sends via Resend + stamps `email_sent_at`; localhost `API_BASE_URL` guard. Opt-out (028) + public HMAC unsubscribe. `DEPLOY_NOTES.md` added. | #325, #326 |
| **Monthly season finale** | `generate_monthly_letter_task` (calendar month, `MONTHLY_MIN_MESSAGES=15`); `weekly_letters.kind` (029); `WeeklyLetterOut.kind` (#329); `SeasonFinaleView` reader on `kind==='monthly'` (#330); branded season share card (#331). | #328–#331 |
| **Guide refresh** | Wise Room copy refresh + ritual rename + minds synced to 11; minds tappable to detail; responsive thumbnails + press effect + taller hero; Sunday-letter links → buttons; iOS share Send gated on prepared image. | #318–#322 |

**Closed this session:**
- **TD-33 (Weekly Reading ARQ email delivery)** → 🟢 DONE (#325). Email sends + `email_sent_at` idempotency + opt-out/unsubscribe + localhost guard.
- **Insight engine** (was F2 "Suggested insights (lite)" placeholder) → 🟢 LIVE: recurrence/shift detector wired; chip + Today card + three-action card + provenance.
- **Insight → Mirror loop** → 🟢 SHIPPED.
- **Monthly season finale** → 🟢 SHIPPED.

**New tech debt / parked items logged:** see §3 (TD-35 insight threshold tuning; TD-36 cache the sync insight-mirror generation) and the parked rituals list in §9.7.

**Migrations:** 028 `user_weekly_email_opt_out`, 029 `weekly_letters_kind`, 030 `insights_source_count`, 031 `mirrors_insight_id`. Head → **`031_mirrors_insight_id`**.

---

## Earlier consolidation summaries (v16 → v19)

Carried forward by reference. See `IMPLEMENTATION_BACKLOG_v19.md` for: v19 (#315–#316 portraits + Orwell/Musashi), v18 (#277–#313 Sunday Letter / Revisit / Reflections feed), v17 (#273–#275 + PR3a), and earlier.

---

## 1. Current Launch Interpretation

**Plan A (active).** Priority order as of 2026-06-21:

1. **PR3a memory bugs — 🔴 not started (highest cold-beta blocker):** fresh-chat missing opening message/thumbnail; home "Continuing" 404s.
2. **Cold beta with 3–5 fresh users** — once memory bugs resolved.
3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment):** live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` + `API_BASE_URL` set.
4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
5. **Counterview ritual** — `/app/counterview` is a stub; design session first, then build.
6. **App-icon mark (TD-29)** — purpose-built mark required.
7. Council / You-vs-You / Mirror fast-follows (post-first-paying-user).

Prior completed items (Mirror, Council, YvY, TD-11, BETA off, Stripe sandbox, PR3a closed items, Oregon migration, Sunday Letter reader, Reflections feed, Orwell/Musashi, WebP) — see `IMPLEMENTATION_BACKLOG_v19.md §1`.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt (TD-23)** — add `.env.local`, `.env*.local`. Single-file commit.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### 2.1 Infrastructure P0

- [x] ~~Oregon migration~~ — DATABASE_URL → Oregon confirmed.
- [ ] **source_chunks re-ingest** into Oregon (TD-22).
- [ ] **Post-Oregon smoke test** (login, chat, Mirror/Council/YvY, **insight→Mirror reflect**, share, library, RAG).
- [ ] **`API_BASE_URL` set to public backend URL** on Render API (else weekly emails suppressed — `DEPLOY_NOTES.md`).
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation.**

### 2.2 Code-side P0

- [ ] **PR3a memory bugs** — fresh-chat opening message/thumbnail; home "Continuing" 404s.
- [ ] **bugfixes-3 — auth race fix** (TD-10).
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari) — include the **three-action insight card** (no awkward wrap) + insight→Mirror flow.
- [ ] **Cold beta with 3–5 fresh users.**
- [ ] **Consolidated polish PR** (Block B visual closure).

### 2.3 Legal P0 / 2.4 Infra P0 / 2.5 UAT P0

Unchanged from v19 (lawyer review, GDPR/DPA, runbooks, DNS + Resend domain, UAT ≥2/5 "I'd pay"). See `IMPLEMENTATION_BACKLOG_v19.md §2`.

---

## 3. Tech debt items

### TD-01 through TD-32

Unchanged from v19 except as noted. See `IMPLEMENTATION_BACKLOG_v19.md §3`. Highlights still open: TD-10 (Zustand hydration race), TD-22 (source_chunks re-ingest), TD-23 (.gitignore), TD-24 (render.yaml sync:false), TD-25 (compress mirror.png), TD-26 (Council share redesign), TD-27 (per-verdict saves), TD-28 (live Stripe), TD-29 (app-icon mark), TD-31 (cache YvY forming reflection), TD-32 (remove `body { zoom: 1.15 }`), TD-34 (cache Reading Revisit). TD-30 superseded.

### TD-05 — Wire `generate_insight_task` (P1, still open — clarified)

The **recurrence/shift detector is live** (`detect_recurrence`, wired into `extract_memory_task`). TD-05 refers to the **separate, older, still-dormant** `generate_insight_task` in `workers/arq_worker.py`. Decide whether to retire it or repurpose it; it is NOT what powers the live insight engine.

### TD-33 — Weekly Reading ARQ email delivery (🟢 DONE — #325, 2026-06-21)

`_maybe_send_weekly_letter_email` (`workers/arq_worker.py`) renders + sends the Sunday/season letter via Resend and stamps `weekly_letters.email_sent_at` (idempotent). Opt-out via `users.weekly_email_opt_out` (028) + public HMAC `GET /unsubscribe/weekly`. Localhost `API_BASE_URL` guard suppresses sending until configured for prod. Resolved.

### TD-35 — Insight detector threshold tuning (P2, NEW)

`RECURRENCE_SIM_THRESHOLD = 0.75`, `RECURRENCE_MIN_PRIOR = 1`, `RECURRENCE_THROTTLE_HOURS = 6` are launch defaults chosen without real-volume data. Tune (precision vs surfacing rate) once cold-beta conversations accumulate. Not a correctness issue.

### TD-36 — Cache / async the sync insight-mirror generation (P2, NEW)

`POST /insights/{id}/reflect` runs `generate_insight_mirror` **synchronously** (the user waits a few seconds for one LLM call). It dedups by `insight_id`, so re-taps are free — but the first reflect is a blocking generate. If latency becomes a problem at volume, consider pre-generating on insight write or moving to an async + poll pattern. Defer until validated live.

---

## 4. Database schemas

Migration head: **`031_mirrors_insight_id`** (chain …027 → 028 → 029 → 030 → 031). New since v19:

- **028** `users.weekly_email_opt_out BOOLEAN NOT NULL DEFAULT false`.
- **029** `weekly_letters.kind` (CHECK {weekly,monthly}) + per-period unique index recreated as `(user_id, period_start, kind)`.
- **030** `insights.source_count INTEGER NULL`.
- **031** `mirrors.insight_id` (FK insights ON DELETE SET NULL) + `ck_mirrors_kind` → {weekly,preview,insight} + partial unique `uq_mirrors_insight`.

Full table list: `PROJECT_STATE_v20.md §4`. `daily_questions` data state unchanged (50 active phenomenology themes; 30 inactive).

---

## 5–8.

Config/env (§5 — `API_BASE_URL` now operationally required for weekly email, see `DEPLOY_NOTES.md`), Stripe wiring (§6 — sandbox complete, live pending TD-28), persona maintenance (§7), LLM eval (§8) — unchanged from v19 except the `API_BASE_URL` note. See `IMPLEMENTATION_BACKLOG_v19.md`.

---

## 9. Future blocks reference

### 9.1–9.6

Unchanged from v19.

### 9.7 Rituals (updated v20)

| Ritual | Status | Notes |
|---|---|---|
| Letter to Future Self | 🟡 UI live, ARQ delivery not wired | Distinct from weekly-letter email (which is now wired). |
| The Mirror | 🟢 **SHIPPED** (#166–#173) **+ insight-seeded mirror (v20, #335–#337)** | Weekly generator + host picker + ring-true + saves; now also `kind="insight"` mirrors reached via `?insightId=`. |
| The Council | 🟢 SHIPPED (#182–#186) | Unchanged. |
| You vs You | 🟢 SHIPPED (#193–#202) | Unchanged. |
| Weekly Reading / Sunday Letter | 🟢 reader SHIPPED (v18) **+ ARQ email delivery (v20, #325)** **+ monthly season finale (v20, #328–#331)** | Synthesizes from the insight spine; opt-out + unsubscribe; `SeasonFinaleView` for `kind='monthly'`. TD-33 closed. |
| The Counterview | 🔴 NOT BUILT (navigation **stub** at `/app/counterview`) | "Doubt this" routes here; the ritual itself is undesigned/unbuilt. Only unbuilt ritual. Design session first. |

**Insight engine (new in v20):** recurrence/shift detector live (`detect_recurrence` → `extract_memory_task`); in-chat chip; Today card (seal, 14-day window); three-action card; provenance line (`source_count`); insight → Mirror loop.

### 9.8–9.11

Unchanged from v19 (YvY / Council / Mirror fast-follows; Counterview spec exists but NOT designed for build).

---

## 10. Operating principles

Unchanged from v19. P-01 through P-07 + persona/migration conventions (C-01..C-03) in `CLAUDE.md`.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt (TD-23).**
- [ ] **Author smoke-test voice changes** — 6 personas.
- [ ] **PR3a memory bugs** — fresh-chat opening message/thumbnail; home "Continuing" 404s.

### 11.1 P0 (launch blockers)

- [x] ~~Through v19: Mirror, Council, YvY, TD-11, BETA off, Stripe sandbox, PR3a closed items, Oregon, Sunday Letter reader, Reflections feed, Orwell/Musashi, WebP~~ — DONE (see v19).
- [x] ~~**Weekly Reading ARQ email delivery (TD-33)**~~ ✅ DONE (#325, 2026-06-21).
- [x] ~~**Insight engine** (recurrence/shift + chip + Today card + three-action card + provenance)~~ ✅ DONE (#323, #324, #327, #332, #333, #334).
- [x] ~~**Insight → Mirror loop**~~ ✅ DONE (#335–#337).
- [x] ~~**Monthly season finale**~~ ✅ DONE (#328–#331).
- [ ] **PR3a memory bugs** — 🔴.
- [ ] **source_chunks re-ingest** (TD-22); **Post-Oregon smoke test**; **auth race** (TD-10); **mobile nav smoke test**; **TD-28 live Stripe**; **OPS-001 re-sync**; **cold beta**; **consolidated polish PR**; **lawyer review**; **DNS + Resend**; **GDPR/DPA**; **runbooks**; **`PHENOMENOLOGY_BRIDGE_ENABLED`**; **RLS**; **UAT ≥2/5 "I'd pay"**.

### 11.2 P1 (post-revenue)

- [ ] **OPS-001 re-sync.**
- [ ] **TD-29 App-icon mark.**
- [ ] **Counterview ritual** — design + build (only unbuilt ritual; stub routed).
- [ ] **Detector → ritual routing** — "Doubt this" → Counterview is a stub target; full routing pending Counterview build.
- [ ] **Letter to Future Self — ARQ email delivery wiring** (still open).
- [ ] **Per-verdict → reflections save** (TD-27); **Council share redesign** (TD-26); **compress mirror.png** (TD-25).
- [ ] **TD-05 — wire/retire `generate_insight_task`** (separate dormant task).
- [ ] **TD-10**; **I1 Account hub**; **A6+A7 disclaimer integration tests**; **OTP-01 investigation**; **TD-24 render.yaml sync:false**.

### 11.3 P2 (tech debt)

- [ ] **TD-35 — Insight detector threshold tuning** (NEW).
- [ ] **TD-36 — Cache/async the sync insight-mirror generation** (NEW).
- [ ] **TD-34 — Cache Reading Revisit completion**; **TD-31 — Cache YvY forming reflection.**
- [ ] **ChatGPT audit** of persona configs (incl. Orwell + Musashi).
- [ ] TD-12 soft-delete conversations; TD-01 split rate_limit_service; TD-02 PersonaConfig naming; TD-03 ANTHROPIC_MODEL; TD-08 document Render alembic auto-run; rituals-to-chat surfacing; branding resolution ("The Wise Room" vs "Great Minds"); extract Lao Tzu/Wilde/Machiavelli to YAML; TD-20/TD-21.

### 11.4 P3 / 11.5 P4

Unchanged from v19 (modal abstraction, desktop polish, Phase 5 Council premium, eval suite/CI, YvY funnel analytics; TD-04/06/07/14, TD-32 remove `zoom:1.15`, openapi.json→.gitignore, legal-link rel hardening, stale-branch cleanup). See `IMPLEMENTATION_BACKLOG_v19.md §11.4/11.5`.

---

## 12. Plan A vs Plan B

Unchanged from v19. Plan A active. Timeline note: with the insight engine + insight→Mirror loop + weekly email + season finale now shipped, the remaining launch path is dominated by PR3a memory bugs → cold beta → live Stripe wiring → Counterview design/build.

---

**End of IMPLEMENTATION_BACKLOG v20.** Authoritative as of 2026-06-21 (Insight engine · Insight→Mirror loop · weekly email · season finale session). Supersedes `IMPLEMENTATION_BACKLOG_v19.md` (preserved as historical reference).
