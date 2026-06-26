# THE WISE ROOM — Implementation Backlog v21

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v21 = v20 baseline (2026-06-21, through PR #337) + 2026-06-21→2026-06-26 delta (#339–#374):** the **Counterview ritual** shipped end-to-end (last unbuilt ritual now live; migrations 032–033) — backfilled here since it landed after the v20 doc was cut — plus this session's chat **sticky guest mind** (034), **adaptive response length**, **go-deeper depth + free limit + Pro sticky deep mode** (035), **Chat → Council**, **letter write-back** (036), **onboarding profile pills** (037), and the **Home tiles + Explore tab** restructure. Migration head 031 → **037**.
> **v20 = v19 baseline + #317–#337:** Insight engine, Insight → Mirror loop, weekly email (TD-33), monthly season finale; migrations 028–031. Full detail in `IMPLEMENTATION_BACKLOG_v20.md`.
>
> **Generated:** 2026-06-26 (v21 rotation) · **Last updated:** 2026-06-26 (current main `fed8d312`)
>
> **How to read this file:** This v21 file supersedes v20 and all prior backlog files. Where v21 conflicts with v20, v21 wins.
>
> **Companion documents:** `PROJECT_STATE_v21.md`, `HANDOFF_BRIEF_v21.md`, `SCREENS_TRACKING_v9.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## 2026-06-26 Consolidation Summary — Counterview ritual · chat depth/router · letters write-back · onboarding profile · Home/Explore

> Appended as v21. Where this conflicts with earlier sections, this section wins. **Current main SHA `fed8d312`.**

**Code shipped (merged to main; #339–#374):**

| Area | What shipped | PRs |
|---|---|---|
| **Counterview ritual (backend)** | `services/counterview_service.py` — `generate_counterview` (typed/insight anchor, safety-gated both ends, status generated/empty/suppressed, fixed pair Musashi+Machiavelli, ≤10-word verdicts + tighten-retry) + `generate_deeper` (one ≤18-word round-1/persona). `routers/counterview.py` (6 endpoints) + `POST /insights/{id}/counterview`. Migration 032 (`counterviews`+`counterview_responses`). | #342, #343, #346, #348, #353 |
| **Counterview (save/feed/share/recurrence/revisit)** | `counterview_saves` (033) + `reflections_feed_service._counterview_verdicts` (`kind="counterview_verdict"`); `POST /share/counterview` + `image_service` 4:5 card; `counterview_belief_task` recurrence (no migration); revisit list (`GET /counterview`). | #349, #350, #351, #352, #361, #362 |
| **Counterview (frontend)** | `app/app/counterview/page.tsx` — input/insight/result states, staged reveal, large portraits, speaker-toggle frame, go-deeper, Save, Share, start-over; `CounterviewVerdictCard`; SharePreviewModal variant; `RITUAL_INFO['counterview']`. | #343, #344, #345, #347, #354, #360 |
| **Sticky guest mind** | `conversations.active_persona_id` (034); responder = `coalesce(active_persona_id, persona_id)` everywhere incl. quota; `POST`/`DELETE /conversations/{id}/active-mind`; "Return to {origin}". | #366 |
| **Adaptive response length** | `_length_directive_for_input` — ≤15w short (0.34) / 16–49 unchanged / ≥50w long (0.5), within persona band, capped at U; distress-gated, skipped on msg 1. | #367 |
| **Go-deeper depth + limits** | `_deepen_directive` → `reflective_reply_max_words`; `DEEPEN_ESCALATION` neutralized; free `FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA = 3` (`daily_usage.go_deeper_count`, keyed on `conv.persona_id`); Pro sticky `conversations.deep_mode` (Pro-gated endpoint + read site). Migration 035. | #368 |
| **Chat → Council** | Header Scale icon (all users); seed last user msg (≤600) via sessionStorage; Pro → Council / free → upgrade; council `source` gains `'chat'` (`WEEKLY_LIMIT_PER_SOURCE = 1` per bucket). | #369 |
| **Letter write-back** | `weekly_letters.write_back_text`/`write_back_at` (036); `PATCH /weekly-letters/{id}/write-back` (Pro); `WriteBackPanel` in weekly + `SeasonFinaleView`; fed forward as `<reader_wrote_back>` into the next letter. | #370 |
| **Onboarding profile pills** | `user_preferences.profile` JSONB (037); `<what_we_know>` prompt block (turn 1, not recall); `memory_entries` seed (`onboarding_profile`) + `forming_reflection()`; `profile_text.py`; `/app/profile` + `/app/onboarding/profile`; `PATCH /preferences/profile` (+ reflection). | #372 |
| **Home tiles + Insights list** | Today→"Home" (label only, URL `/app/today`); 2×2 `HomeTile` grid + wide Sunday tile; new `/app/insights` minimal list. | #373 |
| **Explore tab** | Rituals tab → Explore (Compass); guide re-parented into `(tabs)/explore`; `/app/guide` + old `/app/explore` redirect deleted; 4 callers → `/app/library?mode=browse`; `/app/rituals` kept, delisted. | #374 |
| **Polish / type / fixes** | insight Today seal (#339), insight mirror host + chrome (#340), discard undo toast (#341), insight title/letter copy/share hero (#355), Library discoverability glow (#356), per-ritual explainer screens (#357), splash priority hero (#358), Sparkle insight marker (#359), saved-line opacity 0.06 (#365), type 15→17px (#364), remove `zoom:1.15` (#363). | #339–#341, #355–#359, #363–#365 |

**Closed this session:**
- **Counterview ritual** (was 🔴 the only unbuilt ritual, stub at `/app/counterview`) → 🟢 LIVE end-to-end. **No remaining unbuilt rituals.**
- **TD-32** (remove `body { zoom: 1.15 }`) → 🟢 DONE (#363).

**New tech debt / parked logged:** TD-37 (dormant brevity post-check) in §3; parked fast-follows in §11.2/§11.3.

**Migrations:** 032 counterviews, 033 counterview_saves, 034 active_persona_id, 035 deep_mode+go_deeper_count, 036 letter write-back, 037 user_preferences.profile. Head → **`037_user_preferences_profile`**.

**Incident:** 035's original revision id (33 chars) overran `version_num VARCHAR(32)`, crashed the deploy, rolled cleanly back to 034; renamed by #371. New rule C-04 (≤32 chars + filename == revision id) in `CLAUDE.md`.

---

## Earlier consolidation summaries (v16 → v20)

Carried forward by reference. See `IMPLEMENTATION_BACKLOG_v20.md` (v20 #317–#337) and `IMPLEMENTATION_BACKLOG_v19.md` (v19/v18 and earlier).

---

## 1. Current Launch Interpretation

**Plan A (active).** Priority order as of 2026-06-26:

1. **PR3a memory bugs — 🔴 not started (highest cold-beta blocker):** fresh-chat missing opening message/thumbnail; home "Continuing" 404s.
2. **Cold beta with 3–5 fresh users** — once memory bugs resolved.
3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
5. **TD-37 — wire or retire the dormant brevity post-check** (post-first-paying-user).
6. **App-icon mark (TD-29).**
7. Counterview / Council / YvY / Mirror fast-follows (post-first-paying-user).

Prior completed items (Mirror, Council, YvY, **Counterview**, TD-11, BETA off, Stripe sandbox, PR3a closed items, Oregon, Sunday Letter reader + email + season finale, Reflections feed, Insight engine, Orwell/Musashi, WebP) — see v20/v19.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt (TD-23)** — add `.env.local`, `.env*.local`. Single-file commit.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### 2.1 Infrastructure P0

- [x] ~~Oregon migration~~ — confirmed.
- [ ] **source_chunks re-ingest** into Oregon (TD-22).
- [ ] **Post-Oregon smoke test** (login, chat, Mirror/Council/YvY, **Counterview**, insight→Mirror reflect, share, library, RAG).
- [ ] **`API_BASE_URL` set to public backend URL** on Render API (else weekly/season emails suppressed — `DEPLOY_NOTES.md`).
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation.**

### 2.2 Code-side P0

- [ ] **PR3a memory bugs** — fresh-chat opening message/thumbnail; home "Continuing" 404s.
- [ ] **bugfixes-3 — auth race fix** (TD-10).
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari) — include **Counterview** result screen (staged reveal, go-deeper, share), the **Chat → Council** icon, the **deep-mode toggle**, and the **Home tile grid + Explore tab** (verify no fixed-tabbar tap desync now that `zoom:1.15` is gone, #363).
- [ ] **Cold beta with 3–5 fresh users.**
- [ ] **Consolidated polish PR** (Block B visual closure).

### 2.3 Legal P0 / 2.4 Infra P0 / 2.5 UAT P0

Unchanged from v20 (lawyer review, GDPR/DPA, runbooks, DNS + Resend domain, UAT ≥2/5 "I'd pay"). See `IMPLEMENTATION_BACKLOG_v20.md §2`.

---

## 3. Tech debt items

### TD-01 through TD-36

Unchanged from v20 except as noted. See `IMPLEMENTATION_BACKLOG_v20.md §3` / v19. Still open highlights: TD-10 (Zustand hydration race), TD-22 (source_chunks re-ingest), TD-23 (.gitignore), TD-24 (render.yaml sync:false), TD-25 (compress mirror.png), TD-26 (Council share redesign), TD-27 (per-verdict saves), TD-28 (live Stripe), TD-29 (app-icon mark), TD-31 (cache YvY forming reflection), TD-34 (cache Reading Revisit), TD-35 (insight threshold tuning), TD-36 (cache/async sync insight-mirror generate). **TD-32 (remove `body { zoom: 1.15 }`) → 🟢 DONE (#363).**

### TD-37 — Dormant brevity post-check (P2, NEW — 🟡 wired but inert)

`services/postprocessing_service.py:check_brevity` is **computed** on the live stream path (`conversation_service.py`) but does **NOT** trigger regeneration — only `forbidden_lexicon` hits enter the `_triggered` regenerate set (see the inline `# brevity no longer forces a regenerate/correction; it stays a prompt-level nudge` comment). The full `regenerate_or_trim` loop runs only in tests / `scripts/voice_test_*`. Net effect: nothing **hard-enforces** reply length in production — length is shaped only by the prompt (adaptive length #367 + `_deepen_directive` #368). Decide post-first-paying-user: **wire** `check_brevity` into the live correction loop, or **retire** it and rely on the prompt nudge. Not a correctness bug; a truth-in-architecture item.

---

## 4. Database schemas

Migration head: **`037_user_preferences_profile`** (chain …031 → 032 → 033 → 034 → 035 → 036 → 037). New since v20:

- **032** `counterviews` + `counterview_responses` (Counterview ritual core).
- **033** `counterview_saves` (soft-delete; feeds Reflections).
- **034** `conversations.active_persona_id` (FK personas ON DELETE SET NULL; sticky guest mind).
- **035** `conversations.deep_mode` (BOOL DEFAULT false) + `daily_usage.go_deeper_count` (INT DEFAULT 0).
- **036** `weekly_letters.write_back_text` + `write_back_at`.
- **037** `user_preferences.profile` JSONB.

All revision ids ≤ 32 chars; filenames == revision ids (C-04). Full table list: `PROJECT_STATE_v21.md §4`.

---

## 5–8.

Config/env (§5 — `API_BASE_URL` operationally required for weekly/season email), Stripe wiring (§6 — sandbox complete, live pending TD-28), persona maintenance (§7 — note all 11 modules now carry `response_length_words`), LLM eval (§8) — unchanged from v20 except as noted. See `IMPLEMENTATION_BACKLOG_v20.md`.

---

## 9. Future blocks reference

### 9.1–9.6

Unchanged from v19/v20.

### 9.7 Rituals (updated v21)

| Ritual | Status | Notes |
|---|---|---|
| Letter to Future Self | 🟡 UI live, ARQ delivery not wired | Distinct from weekly-letter email (wired v20). |
| The Mirror | 🟢 SHIPPED (#166–#173) + insight-seeded (v20) | Unchanged. |
| The Council | 🟢 SHIPPED (#182–#186) **+ Chat → Council source (v21, #369)** | `source` ∈ {direct,mirror,chat}; 1/source/week. |
| You vs You | 🟢 SHIPPED (#193–#202) | Now also sees the onboarding profile (seeded memory). |
| Weekly Reading / Sunday Letter | 🟢 reader (v18) + ARQ email + season finale (v20) **+ write-back (v21, #370)** | Pro write-back fed forward into the next letter. |
| **The Counterview** | 🟢 **SHIPPED (v21, #342–#362)** | Two minds (Musashi+Machiavelli) make the case against a belief; typed or insight-seeded; go-deeper; save→feed; 4:5 share; recurrence from beliefs. **No remaining unbuilt rituals.** |

**Insight engine (v20, polished v21):** discard undo toast (#341), Sparkle marker (#359), Library discoverability glow (#356), standalone `/app/insights` list (#373).

### 9.8–9.11

Unchanged from v19/v20 (YvY / Council / Mirror fast-follows). **Counterview is no longer a "spec exists, not built" item — it is shipped; remaining Counterview work is tuning (voice, thresholds) and a fuller multi-round flow if desired (v2).**

---

## 10. Operating principles

Unchanged from v20. P-01 through P-07 + persona/migration conventions **C-01..C-04** in `CLAUDE.md` (**C-04 NEW this session:** migration revision id ≤ 32 chars + filename == revision id).

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt (TD-23).**
- [ ] **Author smoke-test voice changes** — 6 personas.
- [ ] **PR3a memory bugs** — fresh-chat opening message/thumbnail; home "Continuing" 404s.

### 11.1 P0 (launch blockers)

- [x] ~~Through v20: Mirror, Council, YvY, Insight engine, Insight→Mirror, weekly email (TD-33), season finale, Stripe sandbox, BETA off, TD-11, Oregon, Orwell/Musashi, WebP~~ — DONE.
- [x] ~~**Counterview ritual**~~ ✅ DONE (#342–#362).
- [x] ~~**TD-32 remove `body { zoom: 1.15 }`**~~ ✅ DONE (#363).
- [ ] **PR3a memory bugs** — 🔴.
- [ ] **source_chunks re-ingest** (TD-22); **Post-Oregon smoke test**; **auth race** (TD-10); **mobile nav smoke test**; **TD-28 live Stripe**; **OPS-001 re-sync**; **cold beta**; **consolidated polish PR**; **lawyer review**; **DNS + Resend**; **GDPR/DPA**; **runbooks**; **`PHENOMENOLOGY_BRIDGE_ENABLED`**; **RLS**; **UAT ≥2/5 "I'd pay"**.

### 11.2 P1 (post-revenue)

- [ ] **OPS-001 re-sync.**
- [ ] **TD-29 App-icon mark.**
- [ ] **Letter to Future Self — ARQ email delivery wiring** (still open).
- [ ] **TD-37 — wire/retire dormant brevity post-check.**
- [ ] **`/app/profile` → Explore-tab entry point** (route exists, no nav link).
- [ ] **Per-verdict → reflections save** (TD-27); **Council share redesign** (TD-26); **compress mirror.png** (TD-25).
- [ ] **TD-05 — wire/retire `generate_insight_task`** (separate dormant task).
- [ ] **TD-10**; **I1 Account hub**; **A6+A7 disclaimer integration tests**; **OTP-01 investigation**; **TD-24 render.yaml sync:false**.

### 11.3 P2 (tech debt / tuning)

- [ ] **Home tiles → custom images** (currently typographic; v2).
- [ ] **Adaptive-length thresholds (15/50) + go-deeper free limit (3/day)** — tune on cold-beta volume.
- [ ] **Counterview voice/threshold tuning** — fixed pair, 10-word cut; revisit on volume. Fuller multi-round Counterview flow (v2).
- [ ] **Letter write-back fed-forward truncation** — no max-length cap when injected into the next letter.
- [ ] **Insight-seeding from letter write-back** (explicitly OUT of v1).
- [ ] **TD-35 — insight threshold tuning**; **TD-36 — cache/async sync insight-mirror generate**; **TD-34 — cache Reading Revisit**; **TD-31 — cache YvY forming reflection.**
- [ ] **ChatGPT audit** of persona configs (incl. Orwell + Musashi).
- [ ] TD-12 soft-delete conversations; TD-01 split rate_limit_service; TD-02 PersonaConfig naming; TD-03 ANTHROPIC_MODEL; TD-08 document Render alembic auto-run; rituals-to-chat surfacing; branding resolution; extract Lao Tzu/Wilde/Machiavelli to YAML; TD-20/TD-21.

### 11.4 P3 / 11.5 P4

Unchanged from v20 (modal abstraction, desktop polish, Phase 5 Council premium, eval suite/CI, YvY funnel analytics; TD-04/06/07/14, openapi.json→.gitignore, legal-link rel hardening, stale-branch cleanup). See `IMPLEMENTATION_BACKLOG_v19.md §11.4/11.5`.

---

## 12. Plan A vs Plan B

Unchanged from v20. Plan A active. Timeline note: with **all rituals now shipped (Counterview closed)**, the remaining launch path is dominated by PR3a memory bugs → cold beta → live Stripe wiring. No ritual design/build work remains on the critical path.

---

**End of IMPLEMENTATION_BACKLOG v21.** Authoritative as of 2026-06-26. Supersedes `IMPLEMENTATION_BACKLOG_v20.md` (preserved as historical reference).
</content>
