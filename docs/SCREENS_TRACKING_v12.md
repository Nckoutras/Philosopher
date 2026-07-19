# GREAT MINDS — Screens Tracking v12

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 79 screens** (v12 adds **0 new screens** — the #493–#520 delta is states/components on existing screens plus backend/service work). New states/components on existing screens: the **deep-mode chip-row toggle + free 5/day metering**, **named ritual door chips** in chat + a **Sunday-Letter ritual door card**, the **Council edited-matter** flow, the **Explore hub copy rewrite + "The portrait" section**, the **Future-Self / Mirror / Council / Counterview → confidence-1 memory** distill (invisible but behaviour-changing), the **Reflections feed 500 fix**, and the **counterview 429 free cap**.
>
> **⚠️ Provenance:** the v12 delta spans **#493–#520** — all **session-reviewed** (2026-07-12→2026-07-19, full diffs) and **re-verified against merged code at `faa18600`** this rotation. **#492** was the v23 doc PR.
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`)
> - `USER_FLOW_v4.md`
> - `IMPLEMENTATION_BACKLOG_v24.md`
>
> **Last updated:** 2026-07-19 (v12). Current main `faa18600`.
>
> **Changelog v11 → v12 (2026-07-12→2026-07-19):**
> - **Deep mode — chip-row toggle + free metering (C1, #497/#498/#503/#504).** The deep-mode toggle moved to the chip row with a free-quota UX; the separate go-deeper chip was removed; ON reads as filled bronze; the Pro toggle is wired on the persona-first chat path. Free tier is **metered 5/day global** (migration 050 `daily_usage.deep_mode_count`), not walled; Pro/premium unlimited.
> - **Ritual / insight door chips (C1 / D1 / F-letters, #501/#502/#505/#506/#507).** Named one-tap **ritual door chips** in chat (#501) + **global cross-conversation door surfacing** (#502); the **Sunday Letter** suggests a ritual (in-voice proposal) rendered as a **ritual door card that routes into the ritual** (#505/#506); an **aspiration** insight signal surfaces a **Future Self** door chip (#507).
> - **Council edited-matter flow (Council, #500/#508).** Chat-sourced councils get a display-summary prefill (#500); the Council now deliberates the user's **edited** matter and persists `matter_edited` (migration 051, #508). The edited matter also distils into a confidence-1 memory (#510).
> - **Explore hub copy rewrite + "The portrait" section (D2, #514).** Hub copy corrected (memories-vs-noticings two-store distinction; saved quotes don't feed the room; rituals mostly write not read; Sunday Letter arrives on its own) + a new plain **"The portrait"** section.
> - **Memory arc — invisible behaviour change (C/F/G, #510/#511/#512).** Editing a Council matter, writing a Future-Self note, a Mirror ring-true note, or generating a Counterview rebuttal now distils the user's own words into a **confidence-1.0 memory** (safety-gated), feeding chat recall / letters / insights. No new screen; changes what the room "knows".
> - **Reflections feed 500 fix (F1, #513, CORR-03).** The feed 500'd for any user with a saved corpus quote or a future-self review; `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` added to the schema union restore it.
> - **Counterview free cap (G17, #517).** Free tier capped at **2 direct counterviews/day** → 429 + upgrade wall.
> - **Auth (A-guard, #493/#494/#496).** Sign-out clears the `ph_token` cookie + localStorage (#493); a 401 self-heals via a shared `signOut()` helper (#494); OTP email header (#496).
> - **Prompt caching behind chat (C1, #516).** Every Pro chat + Council-member call now runs against a cache-split system prompt (`{{ cache_sentinel }}` between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE — CORR-02). Invisible to the UI; PRO-only (FREE/Haiku below the cache minimum).
> - Screen count: 79 → 79 (no new screens).
>
> **Changelog v10 → v11 (2026-07-09→2026-07-12):** Quotes / Wise Room screen; Future-Self arrived-letter screen; 5-tab liquid-glass bar; Home quote nudge + insight seen-state; Counterview title; persona-prompt EMOTIONAL WEIGHT + ADVANCEMENT blocks. Full text in `SCREENS_TRACKING_v11.md`.
> **Changelog history v1 → v10:** see `SCREENS_TRACKING_v11.md` / `_v10.md`.

---

## Inventory

### A — Authentication & First-time user

Unchanged from v11 (A0 pending spec; A1–A7 covered; expired-session guard → `/auth`, v11 #489). **v12: sign-out clears the `ph_token` cookie + localStorage (#493); a 401 self-heals via a shared `signOut()` helper (#494); OTP email header (#496).** See `SCREENS_TRACKING_v7.md`.

### B — Onboarding

Unchanged from v11 (B1–B7 covered; reflection profile step skipped once answered, v11 #485). See `SCREENS_TRACKING_v9.md`.

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v12: deep-mode toggle moved to the chip row (#504); ON reads as filled bronze (#498); Pro toggle wired on the persona-first path (#497); free tier metered 5/day global (migration 050, #503), not walled. Named one-tap ritual door chips (#501) + global cross-conversation door surfacing (#502). Prompt caching behind the call (#516, invisible; PRO-only).** Carries v11 EMOTIONAL WEIGHT (#488) + ADVANCEMENT (#491) blocks (see CORR-02, now with the cache sentinel), v10 doorway chips, "Take to Council" chip. |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered. **v12: the deep-mode free-limit path surfaces a metered-quota UX (not a hard wall) at 5/day (#503).** Carries v11 fixes. |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today | ✅ covered. **v12: an aspiration insight signal surfaces a Future Self door chip (#507); stronger "something new" star + larger today-card mark (#499).** Carries v11 quote nudge + insight seen-state. |
| D2 | Explore (hub) | ✅ covered. **v12: hub copy rewritten (memories-vs-noticings two-store distinction; saved quotes don't feed the room; rituals mostly write not read; Sunday Letter arrives on its own) + a new plain "The portrait" section (#514).** |
| D12 | Quotes / "The Wise Room" (`/app/quotes`) | ✅ covered (v11 #459–#487). Unchanged in v12. |
| D7 | Insights list (`/app/insights`) | ✅ covered. **v12: a bounded insight recheck runs after a reply (#509).** Carries v11 seen-set clearing. |
| D8 / D6 / D9 / D10 / D11 | Discuss launcher + Explore guide sub-pages | ✅ shipped (v10). Unchanged in v12. |
| D3 / D4 | search (deferred v2) / (folded) | ✅ covered. Unchanged. |

### E — Multi-mind features (post-MVP)

Unchanged from v7 (E1–E5 pending, Phase 5).

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / Reflections feed | ✅ covered. **v12: the feed 500'd for any user with a saved corpus quote or a future-self review; `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` added to the `ReflectionFeedItem` union restore it (#513, CORR-03, regression test `tests/routers/test_reflections_feed.py`).** Carries v11 `SavedQuoteCard`. |
| F2 | Suggested insights (in-chat) | ✅ covered. Unchanged in v12. |
| F3 / F4 | Weekly letter inbox / detail | ✅ covered. **v12: the Sunday Letter can suggest a ritual (in-voice proposal, payload keys) rendered as a ritual door card that routes into the ritual (#505/#506); the arrived Future-Self note distils into a confidence-1 memory (#511); email suppression now ERROR-logged (#520).** |
| F7 | Future-Self arrived-letter (`/app/scheduled-letters/[id]`) | ✅ covered (v11 #449/#450). **v12: the note distils into a confidence-1.0 memory on write (#511, safety-gated).** |
| F5 / F6 | Recurring-themes dashboard (deferred) / Past conversations | ✅/⏸ (unchanged). |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G1–G11 | Rituals library / detail / flow | ⚠️/✅ as in v11. **v12:** ritual door chips route here from chat / the Sunday Letter (#501/#502/#506). `rituals.ts` future-self copy still flagged (TD-38). |
| G12 | You vs You | ✅ shipped (v10 + v11 brevity band). Unchanged in v12. |
| G13–G16 | Sunday Letter — library / detail / revisit / share | ✅ shipped. **v12: suggest-a-ritual door card (#505/#506).** |
| G17 | The Counterview — LIVE ritual | ✅ covered (v10/v11). **v12: free tier capped at 2 direct counterviews/day → 429 + upgrade wall (#517); a generated rebuttal distils into a confidence-1 memory (#512).** |
| G18 | The Self-Portrait — LIVE screen (`/app/self-portrait`) | ✅ covered (v10/v11). Unchanged in v12. |
| (Council) | The Council | ✅ shipped (v10 decision-architecture). **v12: chat-sourced councils get a display-summary prefill (#500); the Council deliberates the user's edited matter + persists `matter_edited` (migration 051, #508); the edited matter distils into a confidence-1 memory (#510).** |
| (Mirror) | The Mirror | ✅ shipped + insight-seeded. **v12: the ring-true note distils into a confidence-1 memory (#511).** |

### H / I / J / K

Unchanged from v11 (H1–H6 billing; I1–I7 account incl. Profile screen; J/K deferred). See `SCREENS_TRACKING_v9.md`.

---

## Covered screens — new / updated full specs (v12)

> Specs unchanged since v11 are not reproduced — see `SCREENS_TRACKING_v11.md`. Below are surfaces new or changed in v24.

### C1 — Deep mode: chip-row toggle + free metering (#497, #498, #503, #504)

**Screen:** chat (`apps/web/app/app/(tabs)/…/chat`). **Backend:** `services/conversation_service.py`, `services/rate_limit_service.py` (`FREE_DAILY_DEEP_MODE_LIMIT = 5`), migration 050 (`daily_usage.deep_mode_count`).

- The deep-mode toggle **moved to the chip row**; the separate go-deeper chip was **removed** (#504).
- ON state reads as **filled bronze** (#498); the Pro toggle is wired on the **persona-first** chat path (#497).
- Free tier is **metered at 5/day global** across all personas (not walled) — the quota UX shows on the chip row; Pro/premium unlimited (#503, migration 050).

### C1 — Ritual / insight door chips (#501, #502, #505, #506, #507)

- **Named one-tap ritual door chips** in chat (#501) and **global cross-conversation door-chip surfacing** (#502) — a door persists across the conversation, not just the turn that raised it.
- The **Sunday Letter** suggests a ritual with an **in-voice proposal** (payload keys, #505), rendered as a **ritual door card that routes into the ritual** (#506).
- An **aspiration** insight signal surfaces a **Future Self** door chip on Home (#507).

### D2 — Explore hub copy rewrite + "The portrait" (#514)

**Screen:** `apps/web/app/app/(tabs)/explore` (hub). The copy was corrected to the real architecture — **memories vs noticings** are two distinct stores (`memory_entries` = the user's stated/distilled memories; `insights` = the room's noticings), **saved quotes don't feed the room**, **rituals mostly write not read**, the **Sunday Letter arrives on its own** — plus a new plain **"The portrait"** section. Driven by an interconnection-map audit that found the two stores are separate and that the **letters path reads `insights`, not `memories`**.

### Council — edited-matter deliberation (#500, #508)

**Backend:** `services/council_service.py`, migration 051 (`council_sessions.matter_edited`). Chat-sourced councils get a **display-summary prefill** (#500). The Council now **deliberates the user's edited matter** and persists a `matter_edited` flag (051, #508); the edited matter also **distils into a confidence-1.0 memory** (#510, `distill_user_text_to_memory_task`).

### Memory arc — invisible behaviour change (#510, #511, #512)

**Backend:** `services/memory_service.distill_to_memory`, `workers/arq_worker.distill_user_text_to_memory_task`. No screen, but changes what the room knows: a user's own words (edited Council matter #510, Future-Self note + Mirror ring-true note #511, Counterview rebuttal #512) distil (Haiku, `MIN_DISTILL_WORDS=6`, safety-gated in the task) into a `confidence=1.0`, `entry_type="stated"` memory that feeds chat recall / letters / insights.

---

## Corrections this rotation (docs-vs-reality)

- **CORR-02 (UPDATED) — `system_base.jinja2` carries the cache-split sentinel.** The v11 block order now has a **`{{ cache_sentinel }}` slot between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE** (`system_base.jinja2:112`, #516) — the cache split point (prefix cached, suffix volatile). Any template-insertion instruction must be written against the live file (see `HANDOFF_BRIEF_v24.md` lesson 13.42).
- **CORR-03 (NEW) — the Reflections feed schema union was incomplete.** `SavedQuoteCard` (v11 #475/#476) and the Future-Self review (v11 #450) shipped in the service + frontend without the matching `ReflectionFeedItem` union member; the feed 500'd for affected users. #513 added `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` + a regression test.

---

## App icon — deferred

Unchanged (TD-29). No custom app icon on main. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v12.** Authoritative as of 2026-07-19 (deep-mode chip-row metering · ritual door chips · Council edited matter · Explore copy + portrait · Memory arc · Reflections feed fix · counterview cap · corrections). Supersedes `SCREENS_TRACKING_v11.md` (preserved as historical reference).
