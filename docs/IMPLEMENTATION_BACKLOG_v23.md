# THE WISE ROOM — Implementation Backlog v23

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v23 = v22 baseline (2026-07-09, through PR #447) + 2026-07-09→2026-07-12 delta (#449–#491):** the **Quotes system ("The Wise Room" authenticated-quote corpus)** shipped end-to-end (data layer → 5th bottom tab + screen → interactive discuss/story layer → Pro themed/persona-ranked suggestion + Home nudge → QR-stamped share PNG → save → Reflections feed; migrations 045–049), plus the **Future-Self prediction loop** (043), **Counterview share-title** (044), **insight `theme` capture** (047) + seen-state, **Self-Portrait polish**, and a **prompt/persona-voice pass** (tiered emotional-acknowledgment, cross-turn ADVANCEMENT block, ~1.65× deep-mode ceilings). Migration head 042 → **049**.
> **v22 = v21 baseline + #376–#447:** the Self-Portrait feature end-to-end (039), Counterview rebuttal turns (038) + still-stands (041), Explore guides, Council decision-architecture (042), insight doorways, Home image tiles, letters/YvY beats; migrations 038–042. Full detail in `IMPLEMENTATION_BACKLOG_v22.md`.
>
> **Generated:** 2026-07-12 (v23 rotation) · **Last updated:** 2026-07-12 (current main `8a79ca3c`)
>
> **How to read this file:** This v23 file supersedes v22 and all prior backlog files. Where v23 conflicts with v22, v23 wins.
>
> **⚠️ Provenance (three-way split by PR range):** **#469–#491 session-reviewed** (2026-07-12 session, full diffs); **#459–#468 session-reviewed** (prior founder+Claude sessions, full diffs + byte-verification); **#449–#458 code-derived** (reconstructed from merged code at `8a79ca3c` — re-read the source before building on it); **#448** was the v22 doc PR.
>
> **Companion documents:** `PROJECT_STATE_v23.md`, `HANDOFF_BRIEF_v23.md`, `SCREENS_TRACKING_v11.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## 2026-07-12 Consolidation Summary — Quotes / Wise Room corpus · Future-Self prediction loop · Counterview title · insight seen-state · persona-voice pass

> Appended as v23. Where this conflicts with earlier sections, this section wins. **Current main SHA `8a79ca3c`.**

**Code shipped (merged to main; #449–#491):**

| Area | What shipped | PRs |
|---|---|---|
| **Quotes — data layer** | `quotes` table (045; persona_slug, text_en, text_original, source_locator, translation_note, confidence, context, discuss/story counts, is_active); `themes TEXT[]` + GIN idx (046); corpus expansion 88 → 198 (049, rewrote 88 contexts + 110 new). Seed `data/quotes_seed.json` / `db/seed_quotes.py` / frozen `db/migrations/data/quotes_049_data.json`. `GET /quotes`. | #459, #464, #487 |
| **Quotes — tab + screen** | 5th **Quotes** bottom tab (`/app/quotes`, 4th slot before Account); full-bleed portrait cards; peek carousel + gentle auto-advance + no-repeat rotation; read-only cards; detail sheet. Tab-order fix. | #460, #461, #469, #470 |
| **Quotes — interactive** | Atomic `discuss_count`/`story_count` increment endpoints; in-card Discuss (prefill, `lib/quotePrefill.ts`) + "The story"; per-card analytics; persona-locked paywall; larger story text. | #462, #463, #484 |
| **Quotes — suggestion + nudge (Pro)** | `GET /quotes/suggested` (themed, persona-ranked, Pro-gated; 14-day live signal-theme window, `services/quote_suggest.py`); Home "A line for you" nudge (`QuoteNudgeCard`, Pro, daily-capped `lib/quoteNudgeFrequency.ts`, seen-state `lib/quoteNudgeSeen.ts`); `insights.theme` (047). | #465, #466, #467, #468 |
| **Quotes — share** | `POST /share/quote` → 1080×1350 QR-stamped PNG (`image_service.generate_quote_share_image`, `QUOTE_GRADE_*` grade); share button + `SharePreviewModal` quote variant; `source_short` (35-char word-boundary) + tappable full-source popover; native phrase only in story; full-bleed A1 card; filled-bronze actions; preview mirrors sent card. | #471, #472, #473, #474, #480, #481, #482, #483 |
| **Quotes — save → Reflections** | `saved_quotes` table (048; soft-delete, unique (user_id, quote_id), partial idx); `POST`/`DELETE /quotes/{id}/save`, `GET /quotes/saved`; `SavedQuoteCard` in the feed (`reflections_feed_service._quotes`). | #475, #476 |
| **Future-Self — prediction loop** | `scheduled_emails` +prediction/+review_text/+review_at (043); in-app arrived-letter screen (`/app/scheduled-letters/[id]`) + email link; review on open → Reflections. | #449, #450 |
| **Counterview** | `counterviews.title` (044, share-card heading); past-list collapse to 3 + show-earlier expander. | #453, #477 |
| **Insights — seen-state** | "The room noticed" shows only unseen insights (client seen state); Home tile star for unseen insight / waiting letter; Insights-visit clears the seen set. | #454, #490 |
| **Self-Portrait — polish** | Succinct entry copy (no artwork overlap); share-card title personalised with first name; map drops X marker for larger/warmer labels. | #455, #478, #479 |
| **Persona voice** | EMOTIONAL WEIGHT tiered acknowledgment block (plain/present/warm + calibration, `emotional_acknowledgment` config, #488); ADVANCEMENT (cross-turn discipline) block + deep-mode new-layers rule (#491); `reflective_reply_max_words` ~1.65× across 11 personas + warm-trio extra (#486); YvY two-selves brevity band (#457); reflection skip-profile once answered (#485). | #457, #485, #486, #488, #491 |
| **Tab bar / auth / assets** | Liquid-glass active-tab lens + icon magnify (#458); 5th tab + lens 20% + shortened Portrait label (#460); expired-session redirect → `/auth` (#489, `middleware.ts`); transparent insight-seal/Sunday-envelope + WebP re-encode + Home LCP priority (#451, #452, #456). | #458, #460, #489, #451, #452, #456 |

**Migrations:** 043 future_self_prediction, 044 counterview_title, 045 quotes, 046 quotes_themes, 047 insight_theme, 048 saved_quotes, 049 quotes_expand. Head → **`049_quotes_expand`**. All ids ≤ 32 chars; filenames == revision ids (C-04, verified).

**Corrections applied this rotation (see §3.CORR):**
- **CORR-01** — the bottom tab bar is **5 tabs** (Home · Explore · Portrait · Quotes · Account), not the 4 the v22 docs record; "Self Portrait" is labelled "Portrait"; lens width 20%.
- **CORR-02** — `system_base.jinja2` gained the EMOTIONAL WEIGHT (#488) and ADVANCEMENT (#491) blocks mid-template; the recorded block order is stale.

**Closed / corrected this session:**
- **Quotes / "The Wise Room"** → was a backlog concept → 🟢 **LIVE end-to-end** (#459–#487). Remaining work is tuning (see 11.3).
- **Future-Self prediction loop** → 🟢 **LIVE** (#449/#450). (Delivery was already live via APScheduler — v22 CORR-01.)

---

## Earlier consolidation summaries (v16 → v22)

Carried forward by reference. See `IMPLEMENTATION_BACKLOG_v22.md` (v22 #376–#447) and `IMPLEMENTATION_BACKLOG_v21.md` (v21 and earlier).

---

## 1. Current Launch Interpretation

**Plan A (active).** Priority order as of 2026-07-12:

1. **PR3a memory bugs — 🟡 partially addressed (#435).** Verify on smoke test whether the fresh-chat symptoms are fully closed; if not, remaining work stays the highest cold-beta blocker.
2. **Pending verification set (v23) — run before cold beta** (see §2.6). Dimitris repetition retest, empathy mini-eval, quote-share device check.
3. **Cold beta with 3–5 fresh users** — once memory bugs + the verification set clear.
4. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
5. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
6. **TD-37 — wire or retire the dormant brevity post-check** (post-first-paying-user).
7. Quotes / Self-Portrait / Counterview / Council / YvY / Mirror fast-follows (post-first-paying-user).

Prior completed items (Mirror, Council, YvY, Counterview, Self-Portrait, **Quotes / Wise Room**, TD-11, BETA off, Stripe sandbox, Oregon, Sunday Letter + email + season finale + future-self delivery + **prediction loop**, Reflections feed, Insight engine, Orwell/Musashi, WebP) — see above / v22 / v21.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt (TD-23)** — add `.env.local`, `.env*.local`. Single-file commit.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu — **now including the v23 emotional-acknowledgment tier (#488), ADVANCEMENT block (#491), and raised deep-mode ceilings (#486).**

### 2.1 Infrastructure P0

- [x] ~~Oregon migration~~ — confirmed.
- [ ] **source_chunks re-ingest** into Oregon (TD-22).
- [ ] **Post-Oregon smoke test** — now also **Quotes** (tab, carousel, discuss/paywall, share PNG, save→Reflections, Pro nudge), **Future-Self prediction loop** (arrived-letter screen + review), **Counterview title/collapse**, **insight seen-state**.
- [ ] **`API_BASE_URL` set to public backend URL** on Render API (else weekly/season **and future-self** emails suppressed — `DEPLOY_NOTES.md`).
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation.**

### 2.2 Code-side P0

- [ ] **PR3a memory bugs** — verify #435 fully closed the fresh-chat symptoms.
- [ ] **bugfixes-3 — auth race fix** (TD-10).
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari) — include the **Quotes tab** (carousel, share, save), the **Future-Self arrived-letter screen**, and the **5-tab liquid-glass bar** (lens slides under all 5; reduced-motion disables the spring).
- [ ] **Cold beta with 3–5 fresh users.**
- [ ] **Consolidated polish PR** (Block B visual closure).

### 2.3 Legal P0 / 2.4 Infra P0 / 2.5 UAT P0

Unchanged from v20/v21/v22 (lawyer review, GDPR/DPA, runbooks, DNS + Resend domain, UAT ≥2/5 "I'd pay"). See `IMPLEMENTATION_BACKLOG_v22.md §2`.

### 2.6 Pending verification set (v23 — NEW, run before cold beta)

- [ ] **Dimitris repetition retest** — Freud, deep mode, dream scenario. Confirm the new **ADVANCEMENT block (#491)** stops the observed cross-turn repetition. **If it does NOT, open the conditional retrieval-dedup item (TD-40, §3).**
- [ ] **Empathy mini-eval** — 6 personas, heavy emotional input. Confirm the **emotional-acknowledgment tiers (#488)** land in-character (plain/present/warm) without therapy-speak.
- [ ] **A1 `QUOTE_GRADE_*` tuning on a real-device share** — confirm the portrait-background grade (`QUOTE_GRADE_COLOR=0.65` / `CONTRAST=1.02` / `BRIGHTNESS=0.97`, `image_service.py`) reads well on an actual phone before the corpus goes to cold beta.

---

## 3. Tech debt items

### TD-01 through TD-39

Unchanged from v22 except as noted. See `IMPLEMENTATION_BACKLOG_v22.md §3`. Still-open highlights: TD-10 (Zustand hydration race), TD-22 (source_chunks re-ingest), TD-23 (.gitignore), TD-24 (render.yaml sync:false), TD-26 (Council share redesign), TD-27 (per-verdict saves), TD-28 (live Stripe), TD-29 (app-icon mark), **TD-37 (dormant brevity post-check — still 🟡; wire or retire post-first-paying-user)**, **TD-38 (`rituals.ts` future-self copy — founder call)**, **TD-39 (`insights.source_count` recurrence-vs-signal split — confirm intended)**.

### CORR — Corrections to prior docs (v23)

> Verified against merged code at `8a79ca3c`. These correct claims in v22 docs that no longer match reality.

- **CORR-01 — the bottom tab bar is 5 tabs, not 4.** `PROJECT_STATE_v22 §17`, `HANDOFF_BRIEF_v22`, and `SCREENS_TRACKING_v10` record **Home · Explore · Self Portrait · Account** (4 tabs). The live `apps/web/components/layout/BottomTabBar.tsx` has **5 tabs: Home · Explore · Portrait · Quotes · Account** — the **Quotes** tab was added 4th (#460, `/app/quotes`), the Self-Portrait tab **label** shortened to "Portrait" (#460, route `/app/self-portrait` unchanged), and the liquid-glass lens is `calc(20% - 3px)` wide (was ~25% at 4 tabs; lens introduced #458, set to 20% in #460).
- **CORR-02 — `system_base.jinja2` gained two blocks mid-template.** v22-era docs predate the EMOTIONAL WEIGHT (#488) and ADVANCEMENT (#491) blocks. Current order: intro → date → **PERSONA** → **EMOTIONAL WEIGHT** [new] → CONVERSATIONAL MOVES → **ADVANCEMENT (cross-turn discipline)** [new] → VOICE CALIBRATION → PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES. See `HANDOFF_BRIEF_v23.md` lesson 13.42.

### TD-40 — Retrieval dedup (P2, NEW — 🟡 CONDITIONAL, do NOT start yet)

`retrieval_ids` persist per message, but `retrieve()` never consults them, so **same-topic turns can re-serve identical chunks** — a plausible contributor to the Dimitris deep-mode repetition. **This item is gated:** open it **only if the Dimitris repetition retest (§2.6) shows the ADVANCEMENT block (#491) is insufficient** on its own. If the prompt-level discipline fixes the observed repetition, retrieval-dedup is unnecessary complexity for cold beta and stays parked. Not a confirmed bug — a conditional lever.

### TD-41 — Quote-corpus provenance discipline (P1, NEW — confirm before public launch)

The `quotes` table renders **verbatim, source-located** text with a `confidence` field and `translation_note`/`text_original` for non-English originals, on shareable QR-stamped cards. The persona prompt's HARD RULES forbid fabricated quotes; the Quotes feature is the only surface shipping verbatim attributed text to users. **Confirm** the authentication process (who verifies `source_locator` + sets `confidence`, and what `confidence` levels gate display) is documented. No code change implied — a process/verification gap to close before the corpus is public.

### TD-42 — Greek/CJK original-phrase font gap on the quote share card (P2, NEW)

Non-Latin `text_original` values are **omitted from the quote share PNG by design** pending a bundled Greek/CJK-capable font (Pillow renders with the currently-bundled Latin fonts, which lack the glyphs). Same class as the existing quote-card font-coverage debt (the share card omits original phrases for Greek + CJK personas). **Fix:** bundle a Greek-capable (and, ideally, CJK-capable) font for `image_service` and stop omitting `text_original` on the card. Deferred; named, not buried.

---

## 4. Database schemas

Migration head: **`049_quotes_expand`** (chain …042 → 043 → 044 → 045 → 046 → 047 → 048 → 049). New since v22:

- **043** `scheduled_emails` +`prediction`/+`review_text`/+`review_at` (Future-Self prediction+review loop; nullable no-ops).
- **044** `counterviews.title` TEXT (share-card heading; nullable).
- **045** `quotes` table (authenticated corpus; verbatim source-located quotes + counts + is_active).
- **046** `quotes.themes` TEXT[] NOT NULL (server-default) + GIN `idx_quotes_themes`.
- **047** `insights.theme` TEXT (optional life-theme for quote-nudge ranking; nullable).
- **048** `saved_quotes` (soft-delete; feeds Reflections; mirrors `saved_lines`/`counterview_saves` shape).
- **049** quotes corpus expansion (data migration; 88 → 198; frozen payload `db/migrations/data/quotes_049_data.json`, self-contained per C-01).

All revision ids ≤ 32 chars; filenames == revision ids (C-04). Full table list: `PROJECT_STATE_v23.md §4`.

---

## 5–8.

Config/env (§5 — `API_BASE_URL` operationally required for weekly/season **and future-self** email), Stripe wiring (§6 — sandbox complete, live pending TD-28), persona maintenance (§7 — **+ `emotional_acknowledgment` tier + raised `reflective_reply_max_words` on all 11 personas, v23**), LLM eval (§8 — **+ the v23 pending verification set §2.6**) — unchanged from v21/v22 except as noted. See `IMPLEMENTATION_BACKLOG_v22.md`.

---

## 9. Future blocks reference

### 9.1–9.6

Unchanged from v19–v22.

### 9.7 Rituals (updated v23)

| Ritual | Status | Notes |
|---|---|---|
| **Letter to Future Self** | 🟢 **LIVE — delivery wired (APScheduler) + prediction/review loop (v23)** | `send_pending_future_self_emails` cron sends every 5 min (v22 CORR-01). **v23: `prediction`/`review_text`/`review_at` (043); in-app arrived-letter screen (`/app/scheduled-letters/[id]`); review on open → Reflections (#449/#450).** See TD-38 for the rituals.ts copy question. |
| The Mirror | 🟢 SHIPPED + insight-seeded | Unchanged. |
| The Council | 🟢 SHIPPED + decision-architecture synthesis (v22) | Unchanged in v23. |
| You vs You | 🟢 SHIPPED + sentence-owed save (v22) **+ two-selves brevity band (v23, #457)** | Unchanged otherwise. |
| Weekly Reading / Sunday Letter | 🟢 reader + email + season finale + write-back + takeaway/continuity (v22) | Unchanged delivery in v23. |
| The Counterview | 🟢 SHIPPED + rebuttal turns + still-stands (v22) **+ share title (044) + collapsed history (v23, #453/#477)** | `counterviews.title` (044). |
| The Self-Portrait | 🟢 SHIPPED (v22) **+ entry/share/map polish (v23, #455/#478/#479)** | Unchanged core. |

### 9.8 Quotes / "The Wise Room" (NEW — shipped v23)

| Surface | Status | Notes |
|---|---|---|
| **The Wise Room — quote corpus** | 🟢 **NEW — SHIPPED (v23, #459–#487)** | 198 authenticated source-located quotes, 12-theme tagged (045/046/049). Free browse; Pro suggestion + nudge + in-card Discuss. New **Quotes** 5th tab. |
| Quote share card | 🟢 SHIPPED | `POST /share/quote` → 1080×1350 QR-stamped PNG. **Non-Latin originals omitted pending font (TD-42).** |
| Save → Reflections | 🟢 SHIPPED | `saved_quotes` (048) → `SavedQuoteCard`. |
| Corpus provenance process | 🟡 **confirm (TD-41)** | Authentication of `source_locator`/`confidence` to be documented before public launch. |

### 9.9–9.11

Unchanged from v19–v22 (fast-follows).

---

## 10. Operating principles

Unchanged from v22. P-01 through P-07 + persona/migration conventions **C-01..C-04** in `CLAUDE.md`.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt (TD-23).**
- [ ] **Author smoke-test voice changes** — 6 personas (now incl. v23 emotional-acknowledgment / ADVANCEMENT / deep-mode ceilings).
- [ ] **PR3a memory bugs** — verify #435 fully closed them.
- [ ] **v23 pending verification set (§2.6)** — Dimitris retest, empathy mini-eval, quote-share device check.

### 11.1 P0 (launch blockers)

- [x] ~~Through v22: Mirror, Council, YvY, Counterview, Self-Portrait, Insight engine, weekly email, season finale, Stripe sandbox, BETA off, TD-11, Oregon, Home tiles + Explore tab, Explore guides~~ — DONE.
- [x] ~~**Quotes / "The Wise Room" corpus**~~ ✅ DONE (#459–#487).
- [x] ~~**Future-Self prediction loop**~~ ✅ DONE (#449/#450).
- [ ] **PR3a memory bugs** — verify.
- [ ] **v23 pending verification set** (§2.6).
- [ ] **source_chunks re-ingest** (TD-22); **Post-Oregon smoke test**; **auth race** (TD-10); **mobile nav smoke test**; **TD-28 live Stripe**; **OPS-001 re-sync**; **cold beta**; **consolidated polish PR**; **lawyer review**; **DNS + Resend**; **GDPR/DPA**; **runbooks**; **`PHENOMENOLOGY_BRIDGE_ENABLED`**; **RLS**; **UAT ≥2/5 "I'd pay"**.

### 11.2 P1 (post-revenue)

- [ ] **OPS-001 re-sync.**
- [ ] **TD-29 App-icon mark.**
- [ ] **TD-37 — wire/retire dormant brevity post-check.**
- [ ] **TD-38 — `rituals.ts` future-self copy** (founder call: reword vs leave).
- [ ] **TD-39 — confirm `insights.source_count` recurrence-vs-signal split is intended.**
- [ ] **TD-41 — quote-corpus provenance process documented** (before public launch).
- [ ] **`/app/profile` → Explore-tab entry point** (route exists, no nav link).
- [ ] **Per-verdict → reflections save** (TD-27); **Council share redesign** (TD-26).
- [ ] **TD-05 — wire/retire `generate_insight_task`.**
- [ ] **TD-10**; **I1 Account hub**; **A6+A7 disclaimer integration tests**; **OTP-01 investigation**; **TD-24 render.yaml sync:false**.

### 11.3 P2 (tech debt / tuning)

- [ ] **Quotes tuning (NEW)** — 14-day signal-theme window (`quote_suggest.py`), Home nudge daily cap (1/day/device, `quoteNudgeFrequency.ts`), persona-ranking weights, `QUOTE_GRADE_*` share-card grade constants; tune on cold-beta volume + a real-device share.
- [ ] **TD-40 — retrieval dedup (CONDITIONAL)** — open only if the Dimitris retest shows the ADVANCEMENT block is insufficient.
- [ ] **TD-42 — Greek/CJK share-card font** — bundle a Greek-capable (and ideally CJK) font for `image_service`; stop omitting non-Latin `text_original` on the quote card.
- [ ] **Self-Portrait tuning** — breadth-gate thresholds, `PORTRAIT_REGEN_DELTA=8`, `FREE_QUESTION_LIMIT=15`, best-fit bridge-map weights.
- [ ] **Deep-mode reflective-ceiling calibration** — the ~1.65× raise (#486) is a launch default; confirm replies don't run long on cold-beta volume.
- [ ] **Emotional-acknowledgment tier assignment** — per-persona tier (plain/present/warm) is authored; revisit if the empathy mini-eval flags a mismatch.
- [ ] **Adaptive-length thresholds (15/50) + go-deeper free limit (3/day)** — tune on volume.
- [ ] **Counterview voice/threshold tuning**; **Letter write-back fed-forward truncation**; **Insight-seeding from letter write-back** (OUT of v1).
- [ ] **TD-35/36/34/31 caching/tuning**; **ChatGPT audit** of persona configs; TD-12/01/02/03/08; branding; extract Lao Tzu/Wilde/Machiavelli to YAML; TD-20/21.

### 11.4 P3 / 11.5 P4

Unchanged from v22 (modal abstraction, desktop polish, Phase 5 Council premium, eval suite/CI, YvY funnel analytics; TD-04/06/07/14, openapi.json→.gitignore, legal-link rel hardening, stale-branch cleanup). See `IMPLEMENTATION_BACKLOG_v22.md §11.4/11.5`.

---

## 12. Plan A vs Plan B

Unchanged from v22. Plan A active. With **all rituals shipped and the Quotes / Wise Room corpus now live**, the remaining launch path is dominated by PR3a memory-bug verification + the v23 verification set (§2.6) → cold beta → live Stripe wiring. No ritual or feature design/build work remains on the critical path — the tail is tuning + verification + go-to-market plumbing.

---

**End of IMPLEMENTATION_BACKLOG v23.** Authoritative as of 2026-07-12. Supersedes `IMPLEMENTATION_BACKLOG_v22.md` (preserved as historical reference).
