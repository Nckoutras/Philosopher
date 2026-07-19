# THE WISE ROOM — Implementation Backlog v24

> **Purpose:** Source of truth for implementation work for The Wise Room / Philosopher v1 launch.
> **v24 = v23 baseline (2026-07-12, through PR #491) + 2026-07-12→2026-07-19 delta (#493–#520):** a **Memory arc** (user-authored text → confidence-1.0 memory across 4 ritual surfaces), a **Reflections feed schema fix** (a systemic 500 closed), an **Explore hub copy rewrite + portrait section**, and an **Efficiency trip** (anthropic GA bump, prompt caching, free counterview cap, ritual_id validation, embed dedup, letter-suppression logging), plus **deep-mode free metering** (050), **ritual/insight door chips**, **Council edited-matter deliberation** (051), and an **auth/polish** batch. Migration head 049 → **051**.
> **v23 = v22 baseline + #449–#491:** the Quotes / Wise Room corpus end-to-end (045–049), Future-Self prediction loop (043), Counterview title (044), insight theme (047) + seen-state, Self-Portrait polish, persona-voice pass. Full detail in `IMPLEMENTATION_BACKLOG_v23.md`.
>
> **Generated:** 2026-07-19 (v24 rotation) · **Last updated:** 2026-07-19 (current main `faa18600`)
>
> **How to read this file:** This v24 file supersedes v23 and all prior backlog files. Where v24 conflicts with v23, v24 wins. **Production reality always wins over docs.**
>
> **⚠️ Provenance:** **#493–#520 session-reviewed** (2026-07-12→2026-07-19 sessions, full diffs) **and re-verified against merged code at `faa18600`** this rotation (migration chain, `anthropic==0.99.0`, cache sentinel, the Reflections union, the distill helper/task, the two rate-limit constants). #492 was the v23 doc PR.
>
> **Companion documents:** `PROJECT_STATE_v24.md`, `HANDOFF_BRIEF_v24.md`, `SCREENS_TRACKING_v12.md`, `DESIGN_SYSTEM_v4.md` (+ v5 addendum), `USER_FLOW_v4.md`, `DEPLOY_NOTES.md`.
>
> **Priority key:** P0 launch blocker · P1 post-revenue · P2 v2/post-MVP · P3 post-launch · P4 tech debt/infra
> **Status key:** 🔴 not started · 🟡 in progress / partial · 🟢 done · ⏸ deferred

---

## 2026-07-19 Consolidation Summary — Memory arc · Reflections feed fix · Explore copy · Efficiency trip · deep-mode metering · ritual doors · Council edited matter

> Appended as v24. Where this conflicts with earlier sections, this section wins. **Current main SHA `faa18600`.**

**Code shipped (merged to main; #493–#520):**

| Area | What shipped | PRs |
|---|---|---|
| **Memory arc** | `distill_to_memory(text)` (Haiku, max_tokens=160, `MIN_DISTILL_WORDS=6` pre-filter → no LLM on trivial text; `services/memory_service.py`) + `distill_user_text_to_memory_task` (safety-gated in-task; `entry_type="stated"`, `confidence=1.0`, stale-cron-exempt; `workers/arq_worker.py`). Wired to **Council edited matter** (#510), **Future-Self note** + **Mirror ring-true note** (#511), **Counterview rebuttal** (#512, rollback-safe count guard). Bounded insight recheck after a reply (#509). | #509, #510, #511, #512 |
| **Reflections feed fix** | `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` added to the `ReflectionFeedItem` union (`schemas/__init__.py`) — feed previously **500'd** for users with a saved quote / future-self review. Regression test `tests/routers/test_reflections_feed.py`. **CORR-03.** | #513 |
| **Explore copy + portrait** | Hub copy corrected (memories-vs-noticings two-store distinction; saved quotes don't feed the room; rituals mostly write not read; Sunday Letter arrives on its own) + new plain "The portrait" section. Driven by an interconnection-map audit (letters read `insights`, not `memories`). | #514 |
| **Efficiency — SDK bump** | `anthropic` 0.34.2 → **0.99.0** (GA prompt-caching prerequisite; `requirements.txt`). | #515 |
| **Efficiency — prompt caching** | `{{ cache_sentinel }}` in `system_base.jinja2` after VOICE CALIBRATION (**CORR-02**); `prompt_builder.CACHE_SPLIT_SENTINEL` / `split_system_for_cache` / `cache_whole_system`; chat 4 paths + Council members only (synthesis/one-shots excluded); `llm_client` logs `cache_write`/`cache_read`. FREE/Haiku below cache minimum → PRO-only (accepted). | #516 |
| **Efficiency — counterview cap** | `FREE_DAILY_COUNTERVIEW_LIMIT = 2` (`rate_limit_service.py`), `source='direct'` count-based; router 429 + upgrade wall (429 convention shared with `self_comparison`). | #517 |
| **Efficiency — ritual_id validation** | `conversation_service.create` validates a provided `ritual_id` (active + tier-accessible); closed a free rate-limit bypass exploit. **FK deferred (P4, orphan check first).** | #518 |
| **Efficiency — embed dedup** | `recall()`/`retrieve()` optional `query_embedding`; one embed per turn across the 3 chat paths (main/another-mind/go-deeper). Zero behavior change. | #519 |
| **Efficiency — letter log** | Weekly/monthly letter-email suppression log warning → error, actionable message; **guard NOT moved** (letter has in-app value); shared helper covers weekly + monthly. | #520 |
| **Deep mode** | Free daily metering `FREE_DAILY_DEEP_MODE_LIMIT = 5` global (migration **050** `daily_usage.deep_mode_count`); toggle ungated (metered); moved to chip row, go-deeper chip removed; Pro toggle wired (persona-first path) + filled-bronze ON state. | #497, #498, #503, #504 |
| **Ritual / insight doors** | Named one-tap ritual door chips (#501) + global cross-conversation door surfacing (#502) in chat; Sunday Letter suggest-a-ritual (in-voice proposal payload keys, #505) → ritual door card + route (#506); aspiration signal → Future Self door chip (#507). | #501, #502, #505, #506, #507 |
| **Council** | Display-summary prefill for chat-sourced councils (#500); deliberate the user's **edited** matter + persist `matter_edited` (migration **051**, #508) — edited matter feeds the Memory arc distill (#510). | #500, #508 |
| **Auth / polish** | Sign-out clears `ph_token` cookie + localStorage (#493); 401 self-heal + shared `signOut()` (#494); polish batch 1 (#495); OTP email header (#496); stronger insight star + larger today-card mark (#499). | #493, #494, #495, #496, #499 |

**Migrations:** 050 deep_mode_count (`daily_usage.deep_mode_count` INT default 0), 051 council_matter_edited (`council_sessions.matter_edited` BOOL default false). Head → **`051_council_matter_edited`**. Both ids ≤ 32 chars; filenames == revision ids (C-04, verified).

**Corrections applied this rotation (see §3.CORR):**
- **CORR-02 (UPDATED)** — `system_base.jinja2` gained a `{{ cache_sentinel }}` slot between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE (#516); it is the cache split point.
- **CORR-03 (NEW)** — the `ReflectionFeedItem` schema union was missing `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview`; the feed 500'd for affected users (#513).

**Closed / corrected this session:**
- **PR-OPT-4a chat double-embed** → 🟢 closed (#519).
- **PR-OPT-4b silent letter-email suppression** → 🟢 closed (#520; loud error, guard intentionally kept).
- **Reflections feed 500** (saved-quote / future-self-review users) → 🟢 closed (#513).
- **Free counterview / deep-mode uncapped** → 🟢 closed (#517 / #503).
- **ritual_id free rate-limit bypass** → 🟢 closed (#518; FK still deferred → TD-43).

---

## Earlier consolidation summaries (v16 → v23)

Carried forward by reference. See `IMPLEMENTATION_BACKLOG_v23.md` (v23 #449–#491) and `IMPLEMENTATION_BACKLOG_v22.md` (v22 and earlier).

---

## 1. Current Launch Interpretation

**Plan A (active).** Priority order as of 2026-07-19:

1. **Cache-read verification (#516)** — confirm `cache_read > 0` in prod `llm_usage`; underwriting check on the cost model (§2.6).
2. **PR3a memory bugs — 🟡 partially addressed (#435).** Verify on smoke test.
3. **v23 pending verification set — STILL NEVER RUN** (Dimitris repetition retest, empathy mini-eval, quote-share device check; §2.6).
4. **UAT protocol v2 — READY, tester pending.** Produces the willingness-to-pay data the pricing decision waits on.
5. **Cold beta with 3–5 fresh users** — once memory bugs + verification set clear.
6. **Live Stripe wiring (TD-28) + pricing decision — 🔴 (P0 before any real payment).** €11.99/mo / €99.99/yr single Pro tier recommended, founder sign-off pending UAT WTP.
7. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**

Prior completed items (Mirror, Council, YvY, Counterview, Self-Portrait, Quotes / Wise Room, Future-Self prediction loop, **Memory arc**, **deep-mode metering**, TD-11, BETA off, Stripe sandbox, Oregon, Reflections feed + fix, Insight engine, WebP) — see above / v23 / v22.

---

## 2. Remaining Launch-Readiness Checklist (P0)

### 2.0 Immediate blockers (before next PR)

- [ ] **.gitignore security debt (TD-23)** — add `.env.local`, `.env*.local`. Single-file commit.
- [ ] **Author smoke-test voice changes** — 6 personas — incl. the v23 emotional-acknowledgment tier (#488), ADVANCEMENT block (#491), raised deep-mode ceilings (#486).

### 2.1 Infrastructure P0

- [x] ~~Oregon migration~~ — confirmed.
- [ ] **source_chunks re-ingest** into Oregon (TD-22).
- [ ] **Post-Oregon smoke test** — now also the **Memory arc** (4 distill surfaces land confidence-1 memories), the **Reflections feed fix** (#513), **deep-mode metering** (050), **prompt-caching cache-read** (#516), **counterview 429 cap** (#517), **ritual_id validation** (#518).
- [ ] **`API_BASE_URL` set to public backend URL** on Render API (else weekly/season **and future-self** emails suppressed — **now ERROR-logged, #520**; `DEPLOY_NOTES.md`).
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation.**
- [ ] **Confirm alembic head `051_council_matter_edited` (050–051) applied on Render deploy.**

### 2.2 Code-side P0

- [ ] **PR3a memory bugs** — verify #435 fully closed the fresh-chat symptoms.
- [ ] **bugfixes-3 — auth race fix** (TD-10).
- [ ] **Mobile 12-point nav smoke test** (real iOS Safari) — include the **deep-mode chip-row metering**, **ritual door chips**, **Council edited-matter** flow.
- [ ] **Cold beta with 3–5 fresh users.**
- [ ] **Consolidated polish PR** (Block B visual closure).

### 2.3 Legal P0 / 2.4 Infra P0 / 2.5 UAT P0

Unchanged from v20–v23 (lawyer review, GDPR/DPA, runbooks, DNS + Resend domain, UAT ≥2/5 "I'd pay"). **v24: UAT protocol v2 is READY — tester pending.** See `IMPLEMENTATION_BACKLOG_v23.md §2`.

### 2.6 Pending verification set (run before cold beta)

- [ ] **Cache-read verification (NEW, v24)** — confirm `cache_read > 0` in prod `llm_usage` logs for a Pro chat turn / Council call (#516). Prompt caching can silently write-only (pure overhead); this proves hits. **Gates the cost model.**
- [ ] **Dimitris repetition retest (STILL NEVER RUN)** — Freud, deep mode, dream scenario. Confirm the ADVANCEMENT block (#491) stops the observed cross-turn repetition. **If not, open TD-40 (retrieval dedup).** Carried unchanged from v23.
- [ ] **Empathy mini-eval (carried)** — 6 personas, heavy emotional input; confirm the emotional-acknowledgment tiers (#488) land in-character.
- [ ] **A1 `QUOTE_GRADE_*` real-device share check (carried)** — portrait-background grade reads well on an actual phone.

---

## 3. Tech debt items

### TD-01 through TD-42

Unchanged from v23 except as noted. See `IMPLEMENTATION_BACKLOG_v23.md §3`. Still-open highlights: TD-10 (Zustand hydration race), TD-22 (source_chunks re-ingest), TD-23 (.gitignore), TD-24 (render.yaml sync:false), TD-26 (Council share redesign), TD-27 (per-verdict saves), TD-28 (live Stripe), TD-29 (app-icon mark), TD-37 (dormant brevity post-check), TD-38 (`rituals.ts` future-self copy), TD-39 (`insights.source_count` split), **TD-40 (retrieval dedup — CONDITIONAL, gated on the Dimitris retest)**, TD-41 (quote-corpus provenance), TD-42 (Greek/CJK share-card font). Plus the **dual tier-resolution debt** (`auth.get_current_user_plan` vs `tier_service.get_user_tier`, `CLAUDE.md`).

### CORR — Corrections to prior docs (v24)

> Verified against merged code at `faa18600`.

- **CORR-02 (UPDATED) — `system_base.jinja2` carries the cache-split sentinel.** The v23 order (PERSONA → EMOTIONAL WEIGHT → CONVERSATIONAL MOVES → ADVANCEMENT → VOICE CALIBRATION → PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES) now has a **`{{ cache_sentinel }}` slot between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE** (`system_base.jinja2:112`, #516) — the cache split point (prefix cached, suffix volatile). Template-insertion instructions must be written against the live file (lesson 13.42).
- **CORR-03 (NEW) — the Reflections feed schema union was incomplete.** `SavedQuoteCard` (v23 #475/#476) and the Future-Self review (v23 #450) shipped in service+frontend without the matching `ReflectionFeedItem` union member; the feed 500'd for affected users. #513 added `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` + a regression test (`tests/routers/test_reflections_feed.py`). See `HANDOFF_BRIEF_v24.md` lesson 13.46.

### TD-43 — ritual_id foreign key (P4, NEW — deferred)

`conversation.ritual_id` is validated at creation (#518: active + tier-accessible, orphan check) but has **no FK constraint**. The validation is the cold-beta stopgap that closed the free rate-limit bypass; the FK is the durable fix. **Add before public launch.** Named, not buried.

### TD-44 — Cache-read unverified in prod (P1, NEW — verify)

Prompt caching (#516) is merged and logs `cache_write`/`cache_read`, but no prod log has yet confirmed `cache_read > 0`. Caching has a silent write-only failure mode (pure overhead, no savings). **Confirm hits in `llm_usage` before the cost model relies on the savings.** No code change implied — a verification gap. See §2.6.

---

## 4. Database schemas

Migration head: **`051_council_matter_edited`** (chain …049 → 050 → 051). New since v23:

- **050** `daily_usage.deep_mode_count` INTEGER NOT NULL default 0 (free deep-mode daily metering; no-op for existing rows).
- **051** `council_sessions.matter_edited` BOOLEAN NOT NULL default false (Council edited-matter flag; no-op for existing rows).

Both additive columns with server-defaults. All revision ids ≤ 32 chars; filenames == revision ids (C-04). Full table list: `PROJECT_STATE_v24.md §4`.

---

## 5–8.

Config/env (§5 — `API_BASE_URL` operationally required, **now ERROR-logged on suppression #520**; **`anthropic==0.99.0`**), Stripe wiring (§6 — sandbox complete, live pending TD-28; **pricing €11.99/€99.99 recommended, founder sign-off pending UAT**), persona maintenance (§7 — unchanged in v24), LLM eval (§8 — **+ the v24 cache-read verification §2.6**) — unchanged from v22/v23 except as noted. See `IMPLEMENTATION_BACKLOG_v23.md`.

---

## 9. Future blocks reference

### 9.1–9.6

Unchanged from v19–v23.

### 9.7 Rituals (updated v24)

| Ritual | Status | Notes |
|---|---|---|
| **Letter to Future Self** | 🟢 LIVE (delivery + prediction/review loop v23) | **v24: the arrived note distills → confidence-1 memory (#511).** |
| The Mirror | 🟢 SHIPPED + insight-seeded | **v24: the ring-true note distills → confidence-1 memory (#511).** |
| The Council | 🟢 SHIPPED + decision-architecture synthesis (v22) | **v24: deliberate the user's edited matter + persist `matter_edited` (051, #508); edited matter → memory (#510); display-summary prefill (#500).** |
| You vs You | 🟢 SHIPPED + sentence-owed save (v22) + brevity band (v23) | Unchanged in v24. |
| Weekly Reading / Sunday Letter | 🟢 reader + email + season finale + write-back (v22) | **v24: suggest-a-ritual door card + route (#505/#506); suppression now ERROR-logged (#520).** |
| The Counterview | 🟢 SHIPPED + rebuttal turns + title (v22/v23) | **v24: free daily cap 2/day + 429 wall (#517); rebuttal → memory (#512).** |
| The Self-Portrait | 🟢 SHIPPED + polish (v22/v23) | Unchanged in v24. |

### 9.8 Quotes / "The Wise Room"

Unchanged from v23 except the Reflections feed fix (#513) restored the feed for users with a saved quote. See `IMPLEMENTATION_BACKLOG_v23.md §9.8`.

### 9.9 Deep mode (updated v24)

| Surface | Status | Notes |
|---|---|---|
| Deep-mode toggle | 🟢 LIVE | Chip-row toggle, filled-bronze ON, Pro-wired on persona-first path (#497/#498/#504). |
| Free daily metering | 🟢 LIVE | `FREE_DAILY_DEEP_MODE_LIMIT = 5` global (migration 050); Pro/premium unlimited (#503). |

### 9.10–9.12

Unchanged from v19–v23 (fast-follows).

---

## 10. Operating principles

Unchanged from v22/v23. P-01 through P-07 + persona/migration conventions **C-01..C-04** in `CLAUDE.md`.

---

## 11. Backlog by priority (consolidated)

### 11.0 Pre-work blockers (do before any PR)

- [ ] **.gitignore security debt (TD-23).**
- [ ] **Author smoke-test voice changes** — 6 personas.
- [ ] **PR3a memory bugs** — verify #435 fully closed them.
- [ ] **v24 pending verification set (§2.6)** — cache-read, Dimitris retest, empathy mini-eval, quote-share device check.

### 11.1 P0 (launch blockers)

- [x] ~~Through v23: Mirror, Council, YvY, Counterview, Self-Portrait, Quotes / Wise Room, Future-Self prediction loop, Insight engine, weekly email, Stripe sandbox, BETA off, TD-11, Oregon~~ — DONE.
- [x] ~~**Memory arc** (user-authored → confidence-1 memory)~~ ✅ DONE (#510/#511/#512).
- [x] ~~**Reflections feed 500 fix**~~ ✅ DONE (#513).
- [x] ~~**Deep-mode free metering**~~ ✅ DONE (#503, migration 050).
- [ ] **Cache-read verification** (TD-44 / §2.6).
- [ ] **PR3a memory bugs** — verify.
- [ ] **v24 pending verification set** (§2.6).
- [ ] **source_chunks re-ingest** (TD-22); **Post-Oregon smoke test**; **auth race** (TD-10); **mobile nav smoke test**; **TD-28 live Stripe + pricing decision**; **OPS-001 re-sync**; **cold beta**; **consolidated polish PR**; **lawyer review**; **DNS + Resend**; **GDPR/DPA**; **runbooks**; **`PHENOMENOLOGY_BRIDGE_ENABLED`**; **RLS**; **UAT ≥2/5 "I'd pay" (protocol v2 ready, tester pending)**.

### 11.2 P1 (post-revenue)

- [ ] **TD-44 — cache-read verification** (before the cost model relies on caching savings).
- [ ] **OPS-001 re-sync.**
- [ ] **TD-29 App-icon mark.**
- [ ] **TD-37 / TD-38 / TD-39** (carried).
- [ ] **TD-41 — quote-corpus provenance process documented** (before public launch).
- [ ] **Dual tier-resolution consolidation** (before paid launch).
- [ ] **`/app/profile` → Explore-tab entry point**; **Per-verdict → reflections save** (TD-27); **Council share redesign** (TD-26); **TD-05**; **TD-10**; **I1 Account hub**; **A6+A7 disclaimer integration tests**; **OTP-01 investigation**; **TD-24**.

### 11.3 P2 (tech debt / tuning)

- [ ] **Deep-mode metering calibration (NEW)** — `FREE_DAILY_DEEP_MODE_LIMIT = 5/day` is a launch default; tune on cold-beta volume.
- [ ] **Counterview cap calibration (NEW)** — `FREE_DAILY_COUNTERVIEW_LIMIT = 2/day` launch default; tune on volume + conversion signal.
- [ ] **Prompt-cache tuning (NEW)** — confirm the split point (VOICE CALIBRATION | PHENOMENOLOGY BRIDGE) maximizes prefix stability; revisit if per-persona prefixes churn.
- [ ] **TD-40 — retrieval dedup (CONDITIONAL)** — open only if the Dimitris retest shows the ADVANCEMENT block is insufficient.
- [ ] **TD-42 — Greek/CJK share-card font** (carried).
- [ ] **Self-Portrait / Quotes / adaptive-length / Counterview-voice tuning** (carried from v23).
- [ ] **TD-43 — ritual_id FK** (deferred; add before public launch).

### 11.4 P3 / 11.5 P4

Unchanged from v22/v23 (modal abstraction, desktop polish, Phase 5 Council premium, eval suite/CI, YvY funnel analytics; TD-04/06/07/14, openapi.json→.gitignore, legal-link rel hardening, stale-branch cleanup) **+ TD-43 (ritual_id FK)**. See `IMPLEMENTATION_BACKLOG_v23.md §11.4/11.5`.

---

## 12. Plan A vs Plan B

Unchanged from v22/v23. Plan A active. With all rituals shipped, the Quotes corpus live, and now the **Memory arc + Efficiency trip** landed, the remaining launch path is dominated by **verification** (cache-read, PR3a memory bugs, the v23/v24 verification set incl. the never-run Dimitris retest) + **UAT** (protocol v2 ready) → cold beta → **live Stripe wiring + pricing decision**. No ritual or feature design/build work remains on the critical path — the tail is verification + tuning + go-to-market plumbing.

---

**End of IMPLEMENTATION_BACKLOG v24.** Authoritative as of 2026-07-19. Supersedes `IMPLEMENTATION_BACKLOG_v23.md` (preserved as historical reference).
