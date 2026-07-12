# GREAT MINDS — Screens Tracking v11

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 79 screens** (v11 adds **2 new screens**: the **Quotes / "The Wise Room"** screen (`/app/quotes`) and the **Future-Self arrived-letter** screen (`/app/scheduled-letters/[id]`)). New states/components on existing screens: the **5th "Quotes" bottom tab** + liquid-glass lens, the Home **"A line for you" quote nudge**, the Quotes **share PNG + save→Reflections**, the Counterview **share title + collapsed history**, the Home **insight seen-state (tile star)**, and the persona-prompt **EMOTIONAL WEIGHT + ADVANCEMENT** blocks behind every chat.)
>
> **⚠️ Provenance (three-way split by PR range):** the v11 delta spans **#449–#491**. **#469–#491 session-reviewed** (2026-07-12 session, full diffs); **#459–#468 session-reviewed** (prior founder+Claude sessions, full diffs + byte-verification); **#449–#458 code-derived** (reconstructed from merged code at `8a79ca3c` — re-read the source before building on it); **#448** was the v22 doc PR.
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`)
> - `USER_FLOW_v4.md`
> - `IMPLEMENTATION_BACKLOG_v23.md`
>
> **Last updated:** 2026-07-12 (v11). Current main `8a79ca3c`.
>
> **Changelog v10 → v11 (2026-07-09→2026-07-12):**
> - **NEW screen — Quotes / "The Wise Room" (`/app/quotes`, #459–#487).** A full-bleed portrait-card **peek carousel** over an authenticated, source-located philosopher-quote corpus (198 quotes after #487; 12-theme tagged). Gentle auto-advance, no-repeat rotation, read-only cards, a detail sheet ("The story"). Free users browse; the Pro payoff is **`GET /quotes/suggested`** (themed, persona-ranked, Pro-gated; 14-day live signal-theme window) surfaced as a Home nudge. In-card **Discuss** opens a conversation with that quote's persona (persona-locked paywall); atomic `discuss_count`/`story_count`. Backed by `routers/quotes.py`, `services/quote_suggest.py`, migrations 045/046/047/048/049. New **Quotes** 5th bottom tab (#460).
> - **NEW screen — Future-Self arrived-letter (`/app/scheduled-letters/[id]`, #449/#450).** The scheduled Letter-to-Future-Self is now readable **in-app** (also reached from the email link), carrying the written `prediction` + a `review` beat that lands in Reflections (migration 043).
> - **Bottom tab bar → 5 tabs + liquid-glass lens (CORR-01, #458, #460).** The bar is now **Home · Explore · Portrait · Quotes · Account** (Quotes added 4th; "Self Portrait" label shortened to "Portrait"; lens `calc(20% - 3px)`). **Corrects the v10 "4 tabs · Self Portrait" record.**
> - **Home "A line for you" quote nudge (D1, #466/#468).** A Pro, daily-capped (`quoteNudgeFrequency.ts`, one/day/device) nudge card surfacing a themed suggestion with a Discuss action + client seen-state (`quoteNudgeSeen.ts`).
> - **Home insight seen-state (D1, #454/#490).** "The room noticed" shows only **unseen** insights; a **tile star** fires for an unseen insight or a waiting Sunday/season letter; visiting **Insights clears the seen set**.
> - **Reflections gains SavedQuoteCard (F1, #475/#476).** Saved corpus quotes join the unified feed (`self_comparison_saves`-style `saved_quotes` 048; `SavedQuoteCard`).
> - **Counterview share title + collapsed history (G17, #453/#477).** `counterviews.title` (044) as a terrain-of-the-belief share-card heading; the past list collapses to 3 with a show-earlier expander.
> - **Self-Portrait polish (G18, #455/#478/#479).** Succinct entry copy (no artwork overlap); share-card title personalised with first name; map drops the X marker for larger, warmer labels.
> - **Chat persona-prompt blocks (C1, #488/#491).** Every chat now runs an **EMOTIONAL WEIGHT** tiered-acknowledgment block (plain/present/warm) and an **ADVANCEMENT (cross-turn discipline)** block; deep-mode reflective ceilings raised ~1.65× (#486). See CORR-02 for the template block order.
> - **Auth (A-guard, #489).** Expired sessions redirect to `/auth`, not the nonexistent `/login` (`middleware.ts`).
> - Screen count: 77 → 79.
>
> **Changelog v9 → v10 (2026-06-26→2026-07-09):** Self-Portrait screen; Discuss launcher; three Explore guides; Home image tiles; Counterview rebuttal exchange; Council decision architecture; YvY sentence-owed; letters beats. Full text in `SCREENS_TRACKING_v10.md`.
> **Changelog history v1 → v9:** see `SCREENS_TRACKING_v10.md` / `_v9.md`.

---

## Inventory

### A — Authentication & First-time user

Unchanged from v10 (A0 pending spec; A1–A7 covered). **v11: expired-session guard now redirects to `/auth`, not `/login` (#489, `middleware.ts`).** See `SCREENS_TRACKING_v7.md`.

### B — Onboarding

Unchanged from v10 (B1–B6 covered; B7 onboarding profile pills). **v11: the reflection profile step is skipped once answered (#485); first-run unchanged.** See `SCREENS_TRACKING_v9.md`.

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v11: the persona system prompt gained an EMOTIONAL WEIGHT tiered-acknowledgment block (#488) + an ADVANCEMENT cross-turn-discipline block (#491); deep-mode reflective ceilings raised ~1.65× (#486).** See CORR-02 for template order. Carries v10 doorway chips (#438/#439) + quick-action "Take to Council" chip (#385). A quote's **Discuss** action (D8/Quotes) opens a chat here, prefilled with the quote (persona-locked paywall). |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered. **v11: #469 fixed an "another-mind" revert error.** Carries v10 `chat/conv/[id]` resilience (#435). |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today | ✅ covered. **v11: Home "A line for you" quote nudge (#466/#468)** — Pro, daily-capped, Discuss action, seen-state (`quoteNudgeCard`, `quoteNudgeFrequency.ts`, `quoteNudgeSeen.ts`). **Insight seen-state (#454/#490):** "The room noticed" shows only unseen insights; a tile star fires for an unseen insight / waiting letter; Insights-visit clears the seen set. Carries v10 image-card tiles + Discuss route. |
| **D12** | **Quotes / "The Wise Room"** (`/app/quotes`) | ✅ **NEW v11 (#459–#487).** Full-bleed portrait-card peek carousel over the authenticated quote corpus; detail sheet + share + save + Pro suggestion. See spec below. |
| D8 | Discuss launcher (`/app/discuss`) | ✅ covered (v10). Unchanged. |
| D7 | Insights list (`/app/insights`) | ✅ covered. **v11:** visiting this screen clears the Home insight seen-set (#490). |
| D6 / D9 / D10 / D11 | "Living in the Wise Room" guide + Explore guide sub-pages | ✅ shipped (v10). Unchanged in v11. |
| D2 / D3 / D4 | Explore (list/grid) / search (deferred v2) / (folded) | ✅ covered. **v11:** Library remains a non-tab route (`/app/library`), reachable via Home tile / Explore; the bottom bar's 4th slot is now **Quotes**, not Library or Portrait. |

### E — Multi-mind features (post-MVP)

Unchanged from v7 (E1–E5 pending, Phase 5).

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / Reflections feed | ✅ covered. **v11: saved corpus quotes appear in the feed** (`SavedQuoteCard`, #475/#476, `saved_quotes` 048) alongside saved lines, Mirror/Council/Counterview verdicts, insight mirrors, YvY sentence-owed. Carries v10 per-kind type marker (#381). |
| F2 | Suggested insights (in-chat) | ✅ covered. **v11: `insights.theme` (047, #467)** captured at signal-write feeds the quote-nudge ranker. |
| F3 / F4 | Weekly letter inbox / detail | ✅ covered (v10 beats). Unchanged in v11. |
| **F7** | **Future-Self arrived-letter** (`/app/scheduled-letters/[id]`) | ✅ **NEW v11 (#449/#450).** In-app view of an arrived scheduled Letter-to-Future-Self; shows the written `prediction` + a review beat → Reflections (migration 043). See spec below. |
| F5 / F6 | Recurring-themes dashboard (deferred v2) / Past conversations | ✅/⏸ (unchanged). |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G1–G11 | Rituals library / detail / flow | ⚠️/✅ as in v10. **v11:** `rituals.ts` future-self copy still flagged (TD-38). |
| G12 | You vs You | ✅ shipped (v10). **v11: a brevity band on the two selves (#457).** |
| G13 / G14 | Sunday Letter — library / detail | ✅ shipped (v10 beats). Unchanged in v11. |
| G15 / G16 | Sunday Letter — Revisit picker / share preview | ✅ shipped (unchanged). |
| G17 | The Counterview — LIVE ritual | ✅ covered (v10 rebuttal exchange + still-stands). **v11: a share-card title (`counterviews.title` 044, #453)** + the past list collapses to 3 with a show-earlier expander (#477). |
| G18 | The Self-Portrait — LIVE screen (`/app/self-portrait`) | ✅ covered (v10). **v11: succinct entry copy / no artwork overlap (#455); share-card title personalised with first name (#478); map drops the X marker for larger, warmer labels (#479).** Tab **label shortened to "Portrait"** (#460, route unchanged) — see CORR-01. |
| (Council) | The Council | ✅ shipped (v10 decision-architecture synthesis). Unchanged in v11. |

### H / I / J / K

Unchanged from v10 (H1–H6 billing; I1–I7 account incl. Profile screen; J/K deferred). **v11: bronze account frames (#482, `style`).** See `SCREENS_TRACKING_v9.md`.

---

## Covered screens — new / updated full specs (v11)

> Specs unchanged since v10 are not reproduced — see `SCREENS_TRACKING_v10.md`. Below are surfaces new or changed in v23.

### D12 — Quotes / "The Wise Room" (LIVE screen — #459–#487)

**Screen:** `apps/web/app/app/(tabs)/quotes/page.tsx`. **Card:** `apps/web/components/quotes/QuoteCard.tsx`. **Backend:** `routers/quotes.py`, `services/quote_suggest.py`, `services/image_service.py` (share PNG), `services/reflections_feed_service.py` (`_quotes`). **Migrations:** 045 (`quotes`), 046 (`quotes.themes`), 047 (`insights.theme`), 048 (`saved_quotes`), 049 (corpus 88 → 198). **Data:** `apps/api/data/quotes_seed.json`, `apps/api/db/seed_quotes.py`, `apps/api/db/migrations/data/quotes_049_data.json`.

**Corpus:** authenticated, **source-located** philosopher quotes — `text_en`, native `text_original` (nullable), `source_locator`, `translation_note`, `confidence`, `context`, `themes TEXT[]`, `discuss_count`/`story_count`, `is_active`. **198 quotes** after the #487 expansion. This is a distinct store from the RAG `source_chunks` — verbatim, not paraphrased (see backlog TD-41 provenance / lesson 13.43).

**Entry / tab:** the **Quotes** bottom tab (Quote icon, `/app/quotes`), inserted 4th (before Account). The bar is now **Home · Explore · Portrait · Quotes · Account** — 5 tabs, liquid-glass lens `calc(20% - 3px)` (CORR-01).

**Browse (#461, #470):** full-bleed portrait cards in a **peek carousel** with gentle auto-advance, no-repeat rotation, read-only cards, and a **detail sheet ("The story")**.

**Interact (#462, #463, #484):** atomic `POST /quotes/{id}/discuss` + `POST /quotes/{id}/story` (204 increments); in-card **Discuss** prefills a conversation with the quote (`lib/quotePrefill.ts`) with that quote's persona (**persona-locked paywall** for locked personas); larger story text (#484).

**Suggestion + nudge — Pro (#465–#468):** `GET /quotes/suggested` — themed, **persona-ranked**, **Pro-gated** (`[]` for free). Prefers a live `insights.theme` from the **last 14 days**; else preference-derived themes. Surfaced as the Home **"A line for you" nudge** (Pro, daily-capped one/day/device, `quoteNudgeFrequency.ts`; seen-state `quoteNudgeSeen.ts`).

**Share (#471–#474, #480–#483):** `POST /share/quote` → **1080×1350 QR-stamped PNG** (`generate_quote_share_image`; portrait-background grade `QUOTE_GRADE_*`). Full-bleed A1 card; `source_short` (35-char, word-boundary) on card + PNG, tappable full-source popover; the **native phrase lives only in the story, not the card**; the share preview **mirrors the sent card**. **Non-Latin `text_original` is omitted from the PNG pending a Greek/CJK font (TD-42).**

**Save → Reflections (#475/#476):** `POST`/`DELETE /quotes/{id}/save` + `GET /quotes/saved`; `saved_quotes` (048, soft-delete). Saved quotes render as **`SavedQuoteCard`** in the unified Reflections feed.

### F7 — Future-Self arrived-letter (LIVE screen — #449/#450)

**Screen:** `apps/web/app/app/scheduled-letters/[id]/page.tsx` (+ list `scheduled-letters/page.tsx`). **Backend:** `routers/scheduled_emails.py`, `services/template_service.py`, `workers/cron.py`; migration 043. **Delivery** was already live via APScheduler (`send_pending_future_self_emails`; v22 CORR-01).

The arrived Letter-to-Future-Self is now readable **in-app** (also reached from the email link). Migration 043 adds `prediction` (the user's stated prediction at write-time), `review_text`, and `review_at`; reviewing the prediction on open writes the review into the Reflections surface. All columns nullable — old scheduled letters render as before.

### G17 — The Counterview: share title + collapsed history (#453/#477)

**Screen:** `apps/web/app/app/counterview/page.tsx`. **Backend:** `services/counterview_service.py`, `routers/counterview.py`; migration 044 (`counterviews.title`).

- **Share title (#453):** `counterviews.title TEXT` (044) — a terrain-of-the-belief heading for the Counterview share card. Nullable; old rows render as before.
- **Collapsed history (#477):** the past-counterview list collapses to 3, with a "show earlier" expander.

(Carries the v10 rebuttal exchange (038) + "What still stands" line (041) — see `SCREENS_TRACKING_v10.md §G17`.)

### C1 — Chat persona-prompt blocks (#486, #488, #491)

**Template:** `apps/api/prompts/system_base.jinja2`. **Configs:** `personas/_models.py`, `_base.py`, `<persona>.py`; `services/conversation_service.py` (deep-mode ceiling).

- **EMOTIONAL WEIGHT (#488):** a tiered acknowledgment block driven by each persona's `emotional_acknowledgment` config — `plain` / `present` / `warm` — plus an optional in-voice calibration line. Character-safe. **Sits between PERSONA and CONVERSATIONAL MOVES.**
- **ADVANCEMENT — cross-turn discipline (#491):** 4 numbered rules forcing forward motion (never re-deliver a settled interpretation, build on affirmation, treat user-repetition as a stuck signal, open new ground). Plus a deep-mode new-layers rule. **Sits between CONVERSATIONAL MOVES and VOICE CALIBRATION.**
- **Deep-mode ceilings (#486):** per-persona `reflective_reply_max_words` raised ~1.65× (go-deeper band), warm-trio extra.

See CORR-02 for the full current template block order.

---

## Corrections this rotation (docs-vs-reality)

- **CORR-01 — bottom tab bar is 5 tabs, not 4; "Self Portrait" → "Portrait".** v10 (lines 106, 63) records **Home · Explore · Self Portrait · Account** (4 tabs, "Library replaced by Self Portrait"). The live `BottomTabBar.tsx` is **Home · Explore · Portrait · Quotes · Account** — Quotes added 4th (#460), the Self-Portrait tab **label** shortened to "Portrait" (#460, `/app/self-portrait` route unchanged), lens `calc(20% - 3px)` (lens introduced #458, set 20% in #460).
- **CORR-02 — `system_base.jinja2` block order.** v10-era references predate the EMOTIONAL WEIGHT (#488) and ADVANCEMENT (#491) blocks. Current order: intro → date → **PERSONA** → **EMOTIONAL WEIGHT** [new] → CONVERSATIONAL MOVES → **ADVANCEMENT** [new] → VOICE CALIBRATION → PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES. Any template-insertion instruction must be written against the live file (see `HANDOFF_BRIEF_v23.md` lesson 13.42).

---

## App icon — deferred

Unchanged (TD-29). No custom app icon on main. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v11.** Authoritative as of 2026-07-12 (Quotes / Wise Room screen · Future-Self arrived-letter screen · 5-tab liquid-glass bar · Home quote nudge + insight seen-state · Counterview title · persona-prompt blocks · corrections). Supersedes `SCREENS_TRACKING_v10.md` (preserved as historical reference).
