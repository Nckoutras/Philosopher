# GREAT MINDS — Screens Tracking v10

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 77 screens** (v10 adds **5 new screens**: the **Self-Portrait** screen (`/app/self-portrait`), the **Discuss** launcher (`/app/discuss`), and three **Explore guide** pages — **Conversations** (`/app/explore/conversations`), **Reflections & Portraits** (`/app/explore/reflections`), **The room remembers** (`/app/explore/memory`)). New states/components on existing screens: Home **image-card tiles**, the chat **dilemma/belief doorway chips**, the Home **"room noticed" card**, the Counterview **rebuttal exchange + still-stands line**, the YvY **sentence-owed** save, and the Council **decision-architecture synthesis**.)
>
> **⚠️ Provenance:** the v10 delta (#376–#447) was built outside the working sessions and **reconstructed by reading merged code at `aa3ecafd`** — code-derived, not session-verified.
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`)
> - `USER_FLOW_v4.md`
> - `IMPLEMENTATION_BACKLOG_v22.md`
>
> **Last updated:** 2026-07-09 (v10). Current main `aa3ecafd`.
>
> **Changelog v9 → v10 (2026-06-26→2026-07-09):**
> - **NEW screen — Self-Portrait (`/app/self-portrait`, #387–#427, #437, #447).** A Pro-gated self-knowledge instrument. Quiz (`data/question_bank.json`, 360 questions / 12 categories, interleaved; free tier `FREE_QUESTION_LIMIT=15`) → forming/ready portrait (breadth gate) → radar + territorial map (Shape/Map toggle) → client-canvas share card → persona best-fit + "take best-fit mind to chat". New **Self Portrait** tab (Easel icon) **replaces Library in the bottom bar** (Library still reachable). Backed by `services/self_portrait.py` / `_summary.py` / `_prompts.py`, `routers/preferences.py`, migration 039 (`portrait_cache`).
> - **NEW screen — Discuss (`/app/discuss`, #378).** A topic-discussion launcher (`lib/useTopicConversation.ts`) reached from the Home "Discussion" image tile.
> - **NEW screens — Explore guides (#382, #431, #434).** `/app/explore/conversations` (teaches the in-chat tools; +Council + Deep-mode blocks, #430), `/app/explore/reflections` (reflections & portraits), `/app/explore/memory` ("The room remembers" memory explainer).
> - **Home tile restructure → image cards (D1, #378, #379, #384, #393).** The v9 typographic 2×2 grid became **image-card tiles** (per-tile WebP; Discussion → `/app/discuss`, Insights, Library, Rituals) + the wide Sunday tile; centered/enlarged white tile words; priority above-the-fold images + LQIP blur placeholders. Continuing/Reflections cards relocated.
> - **Counterview rebuttal exchange (G17, #376, #377).** The Counterview result screen gains a **bounded user-rebuttal thread** — rebut the current speaker in place; that persona replies in one ≤18-word line; capped at 3 (`MAX_REBUTTALS`). **+ a quiet "What still stands" closing line** (#443). Backed by `counterview_turns` (038) + `counterviews.still_stands` (041).
> - **Chat doorway chips (C1, #438, #439).** Dilemma/belief signals detected during memory extraction surface **doorway chips** in chat (`InsightCard.tsx`) that route to Council / Counterview.
> - **Home "room noticed" card (D1, #440).** `components/today/RoomNoticedCard.tsx` (`useInsightDoors.ts`) surfaces detected dilemma/belief signals on Home.
> - **Council decision-architecture synthesis (G-council, #386, #444).** The Council close is now a decision instrument — real_question / tension / verdict / next_move (`synthesis_structured` JSONB, 042) — distilled from a chat essence brief; old sessions fall back to the flat synthesis.
> - **YvY sentence-owed save (F1/G12, #442).** "The sentence you owe yourself" can be saved to the Reflections feed (`YvYSentenceCard.tsx`, `self_comparison_saves` 040); + hidden continuity/closing beats (#441).
> - **Letters (F3/F4/G13/G14, #380, #391, #392, #398, #399, #436, #445).** Sunday next-reading line + UTC fix; sign-off + Frame icon; persona thumbnails on saved-reading cards; practical takeaway + continuity; "something new" star for unread letters; prefill on suggested-persona tap; "What went unspoken" avoidance line.
> - **Reflections per-kind type marker (F1, #381).** A quiet per-kind marker on each reflection card.
> - Screen count: 72 → 77.
>
> **Changelog v8 → v9 (2026-06-26):** Counterview promoted stub → live ritual; Insights list; Profile pills; Home tiles; Explore tab; chat header affordances; letter write-back. Full text in `SCREENS_TRACKING_v9.md`.
> **Changelog history v1 → v8:** see `SCREENS_TRACKING_v9.md` / `_v8.md`.

---

## Inventory

### A — Authentication & First-time user

Unchanged from v9 (A0 pending spec; A1–A7 covered). See `SCREENS_TRACKING_v7.md`.

### B — Onboarding

Unchanged from v9 (B1–B6 covered; B7 onboarding profile pills). See `SCREENS_TRACKING_v9.md`.

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v10: dilemma/belief doorway chips (#438/#439)** — signals detected during memory extraction surface `InsightCard` chips routing to Council/Counterview. "Take to Council" moved from a header icon to a **quick-action chip** (#385, `QuickActionsRow.tsx`). Carries v9 header states (return-to-origin, Deep-mode, Council). |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered. **v10: `chat/conv/[id]` resilience (#435)** — opening fallback, graceful 404, Continuing-card sync (addresses PR3a symptoms; verify). |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today | ✅ covered. **v10 (#378/#379/#384/#393): image-card 2×2 tiles** (per-tile WebP; Discussion → `/app/discuss`, Insights → `/app/insights`, Library, Rituals) + wide Sunday tile; centered/enlarged tile words; priority images + LQIP blur; Continuing/Reflections relocated. **+ "The room noticed" card (#440)** surfacing dilemma/belief signals. |
| **D8** | **Discuss launcher** (`/app/discuss`) | ✅ **NEW v10 (#378).** Topic-discussion launcher (`lib/useTopicConversation.ts`) from the Home Discussion tile. |
| D7 | Insights list (`/app/insights`) | ✅ covered (v9). **v10:** now also a route target for the chat doorway chips. |
| D6 | "Living in the Wise Room" guide (Explore tab) | ✅ shipped (v9 re-parented). **v10: Explore index rewritten** (plain-language feature + storage map, higher-contrast titles, pushable heroes, text-first; #428/#429/#432/#446) and expanded with three guide sub-pages (D9–D11). |
| **D9** | **Explore — The Conversations guide** (`/app/explore/conversations`) | ✅ **NEW v10 (#382, #430).** Teaches the in-chat tools; includes Council + Deep-mode blocks; sticky-guest fix; pushable hero. |
| **D10** | **Explore — Reflections & Portraits guide** (`/app/explore/reflections`) | ✅ **NEW v10 (#431).** Explains reflections + the Self-Portrait; pushable hero. |
| **D11** | **Explore — The room remembers** (`/app/explore/memory`) | ✅ **NEW v10 (#434).** Memory explainer + section wiring. |
| D2 / D3 / D4 | Explore (list/grid) / search (deferred v2) / (folded) | ✅ covered. **v10:** Library is **no longer a bottom-tab** (replaced by Self Portrait, #388/#406) but the `/app/library` route + `?mode=browse` callers are unchanged and reachable via Home tile / Explore. |

### E — Multi-mind features (post-MVP)

Unchanged from v7 (E1–E5 pending, Phase 5).

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / Reflections feed | ✅ covered. **v10: YvY "sentence you owe yourself" appears in the feed** (`YvYSentenceCard`, #442, `self_comparison_saves` 040) alongside saved lines, Mirror/Council/Counterview verdicts, insight mirrors. **Quiet per-kind type marker on each card (#381).** |
| F2 | Suggested insights (in-chat) | ✅ covered. **v10: dilemma/belief signal detection (#438)** feeds the chat doorway chips + Home room-noticed card. |
| F3 / F4 | Weekly letter inbox / detail | ✅ covered. **v10 (F3/F4):** next-reading line + UTC `nextSundayLabel` fix (#380); sign-off + Frame icon (#391); persona thumbnails on saved-reading cards (#392); practical takeaway + letter-to-letter continuity (#398); "something new" star for unread Sunday/season letters (#399, `LettersBootstrap.tsx`); prefill first message on suggested-persona tap (#436); "What went unspoken" avoidance line (#445). Carries v9 write-back window. |
| F5 / F6 | Recurring-themes dashboard (deferred v2) / Past conversations | ✅/⏸ (unchanged). |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G1–G11 | Rituals library / detail / flow | ⚠️/✅ as in v9 (per-ritual explainers `/app/ritual/[slug]`). **v10:** `rituals.ts` future-self copy flagged (TD-38) — "isn't sent anywhere" vs the live scheduled-letter delivery. |
| G12 | You vs You | ✅ shipped. **v10: hidden continuity + "sentence you owe yourself" closing beats (#441); the sentence is savable → Reflections (#442).** Also sees the Self-Portrait answers (reinject, #389). |
| G13 / G14 | Sunday Letter — library / detail | ✅ shipped. **v10: takeaway/continuity/avoidance-line + persona thumbnails (see F3/F4).** **Letter to Future Self delivery confirmed LIVE** (APScheduler `send_pending_future_self_emails`, `workers/cron.py:133–204`) — corrects the v9-era "delivery not wired" note. |
| G15 / G16 | Sunday Letter — Revisit picker / share preview | ✅ shipped (unchanged). |
| G17 | The Counterview — LIVE ritual | ✅ covered (v9). **v10: bounded user-rebuttal exchange (#376/#377)** — rebut the current speaker in place, one ≤18-word reply, capped at 3 (`counterview_turns` 038); **+ "What still stands" closing line (#443, `still_stands` 041).** See spec below. |
| **G18** | **The Self-Portrait — LIVE screen** (`/app/self-portrait`) | ✅ **NEW v10 (#387–#427, #437, #447).** Pro-gated quiz + forming/ready portrait + radar/map + share + best-fit. See spec below. |
| (Council) | The Council | ✅ shipped. **v10: decision-architecture synthesis (#386/#444)** — real_question/tension/verdict/next_move from a chat essence brief; old sessions fall back to flat synthesis. |

### H / I / J / K

Unchanged from v9 (H1–H6 billing; I1–I7 account incl. Profile screen; J/K deferred). See `SCREENS_TRACKING_v9.md`.

---

## Covered screens — new / updated full specs (v10)

> Specs unchanged since v9 are not reproduced — see `SCREENS_TRACKING_v9.md`. Below are surfaces new or changed in v22.

### G18 — The Self-Portrait (LIVE screen — #387–#427, #437, #447)

**Screen:** `apps/web/app/app/(tabs)/self-portrait/page.tsx`. **Backend:** `services/self_portrait.py`, `self_portrait_summary.py`, `self_portrait_prompts.py`; `routers/preferences.py`; migration 039 (`user_preferences.portrait_cache`). **Data:** `apps/api/data/question_bank.json` (360 questions / 12 categories).

**Tier gate:** free users see `FREE_QUESTION_LIMIT = 15` questions (round-robin across categories); Pro/premium see all 360. A fresh user with no preferences row still sees the questions (does **not** 404).

**Entry / tab:** the **Self Portrait** bottom tab (Easel icon, `/app/self-portrait`) — **replaced Library in the bar** (#388, renamed #406). Tabs are now **Home · Explore · Self Portrait · Account**.

**Quiz (#387, #390, #394, #418):** interleaved questions across the 12 categories, with a category picker, revisit filter, entry shell (hero + wordmark + subtitle + pill CTAs, #412/#423), a category-coverage progress bar (#417), and quiet acknowledgements. Answers persist to `user_preferences.profile["answers"]` via `PATCH /preferences/self-portrait`; saving enqueues a memory seed + YvY reinject (ARQ).

**Portrait payoff (`GET /preferences/self-portrait/portrait`):** a **breadth gate** — `state` is `forming` until answers span enough life areas, then `ready`. **The payload never carries a count / % / fraction — only `state` + surfaced content.**
- **Forming (#400):** cheap `forming_reflection()` observation lines from the user's OWN answers ("Room notices"), plus Artwork cards. Describes HOW they answered, never a diagnosis.
- **Ready (5b, #396):** a cached **Sonnet summary** + **persona best-fit** (bridge map, ranking the 11 personas). Cache = `portrait_cache` JSONB (039): `{text, best_fit[], answer_count_watermark, generated_at}`. Regenerates synchronously only when missing or `≥ PORTRAIT_REGEN_DELTA (8)` new answers stale; a valid cache is served WITHOUT calling `forming_reflection`. **Best-effort — any summary failure falls back to a prior cache or the forming preview and still returns 200.**

**Visualisation:**
- **Radar (#397, #401, #407–#409, #427):** `components/self-portrait/PortraitRadar.tsx` — curated `theme_scores` as a top-5 pentagon with a compass rose, walnut/perimeter frame, denser data fill (approved mock).
- **Map (#404, #420–#422, #426, #447):** `components/self-portrait/PortraitMap.tsx` — a **Shape/Map toggle** over the same `theme_scores`; static hand-drawn cartographic territories (`map-territories.webp`), rank-assigned names, dominant-territory highlight, X marker, compass-rose needle → dominant theme.
- **Summary line (#424):** a deterministic summary line (`lib/selfPortraitSummary.ts`) — replaced an earlier Pull/Edge strip.

**Actions:**
- **Share (#405, #410, #425):** `lib/portraitShareCard.ts` — a **client-side canvas** card (ungated, preview-first): title, viz, summary line, date, QR. Recomposed to the current radar aesthetic.
- **Best-fit → chat (#437):** "take the best-fit mind to chat" opens a conversation with a prefilled first sentence.

### G17 — The Counterview: rebuttal exchange + still-stands (#376, #377, #443)

**Screen:** `apps/web/app/app/counterview/page.tsx`. **Backend:** `services/counterview_service.py`, `routers/counterview.py`; migrations 038 (`counterview_turns`) / 041 (`counterviews.still_stands`).

- **Rebuttal thread (#376/#377):** on the result screen, the user can **rebut the current speaker in place** → `POST /counterview/{id}/respond` (`{text, persona_slug}`). That persona replies in one tight **≤18-word** line (same tighten-retry as go-deeper). **Bounded at `MAX_REBUTTALS = 3` generated turns** (409 `rebuttal_cap_reached` once met). A suppressed input / empty generation / suppressed output persists a turn with that status (no reply) and still returns 200. The response carries `turns[]` + `rebuttals_remaining`. Stored in `counterview_turns` (own `sequence` axis — the verdict/go-deeper `round` model is untouched).
- **"What still stands" (#443):** a quiet closing line naming what of the belief survives the challenge, generated on the **same LLM call** as the two verdicts (grounded-or-null). `counterviews.still_stands TEXT` (041); old rows stay NULL and render as before.

### D1 — Home image tiles + room-noticed (#378, #379, #384, #393, #440)

`apps/web/app/app/(tabs)/today/page.tsx`. The v9 typographic 2×2 grid became **image-card tiles** (per-tile WebP: `discuss.webp` / `insights.webp` / `revisit.webp` / `rituals.webp`): **Discussion** → `/app/discuss` (`lib/useTopicConversation.ts`), **Insights** → `/app/insights`, **Library**, **Rituals**; + the wide **Sunday** tile. Centered/enlarged white tile words (#379), priority above-the-fold images (#384), LQIP blur placeholders (#393, `scripts/mint-image-lqip.py`). **"The room noticed" card** (#440, `RoomNoticedCard.tsx`, `useInsightDoors.ts`) surfaces detected dilemma/belief signals.

### Explore guides (D9–D11 — #382, #430, #431, #434)

`apps/web/app/app/explore/{conversations,reflections,memory}/page.tsx`, reached from the rewritten Explore index (`app/app/(tabs)/explore/page.tsx`, #428/#429/#432/#446: plain-language feature + storage map, higher-contrast titles, pushable heroes, text-first). Conversations teaches the in-chat tools (+Council + Deep-mode blocks, #430); Reflections & Portraits explains the reflections feed + Self-Portrait (#431); "The room remembers" is the memory explainer (#434).

### Council — decision-architecture synthesis (#386, #444)

`apps/web/app/app/council/page.tsx`; `services/council_service.py`, `council_prompts.py`; `council_sessions.synthesis_structured` JSONB (042). A chat conversation is distilled into an **essence brief** for the members (#386); the Council close is now a decision instrument — **real_question / tension / verdict / next_move** (#444). The flat `synthesis` TEXT column stays populated (verdict beat) so the Reflections feed + share card read it unchanged; old sessions (NULL `synthesis_structured`) fall back to the flat synthesis.

---

## App icon — deferred

Unchanged (TD-29). No custom app icon on main. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v10.** Authoritative as of 2026-07-09 (Self-Portrait screen · Discuss launcher · Explore guide pages · Home image tiles · Counterview rebuttal exchange · Council decision architecture · YvY sentence-owed · letters beats). Supersedes `SCREENS_TRACKING_v9.md` (preserved as historical reference).
