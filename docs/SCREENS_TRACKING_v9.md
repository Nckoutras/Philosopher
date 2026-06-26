# GREAT MINDS — Screens Tracking v9

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 72 screens** (v9 adds **3 new screens**: the **Insights list** (`/app/insights`), the **Profile** screen (`/app/profile`) + its **onboarding** counterpart (`/app/onboarding/profile`). G17 The Counterview is **promoted from placeholder stub → live ritual screen**. The Explore tab re-parents the existing guide (no new screen); the Home tile restructure, chat header Council/Deep-mode/sticky-guest affordances, and letter write-back window are new states/components on existing screens.)
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`)
> - `USER_FLOW_v4.md`
> - `IMPLEMENTATION_BACKLOG_v21.md`
>
> **Last updated:** 2026-06-26 (v9). Current main `fed8d312`.
>
> **Changelog v8 → v9 (2026-06-21→2026-06-26):**
> - **G17 The Counterview — PROMOTED stub → LIVE ritual (#342–#362).** `app/app/counterview/page.tsx` is now the full ritual: `input` (typed belief + revisit list of past counterviews), `insight` (auto-generate from `?insightId=`), and result states. Result screen: large dominant portrait panels (Musashi left / Machiavelli right), a single speaker-toggle verdict frame, line-level **staged reveal** (`prefers-reduced-motion` → final), per-persona **go-deeper** (one sharper round-1 line), **Save** (→ Reflections feed), **Share** (4:5 card), **Start over**. `empty`/`suppressed` (safety) → gentle fallback. Backed by `services/counterview_service.py`, `routers/counterview.py`, migrations 032/033.
> - **NEW screen — Insights list (`/app/insights`, #373).** A minimal standing list of non-dismissed insights, each routing to its reflection (Mirror `?insightId=`, You-vs-You, or Counterview `?insightId=`).
> - **NEW screen — Profile (`/app/profile`) + onboarding profile (`/app/onboarding/profile`, #372).** Two tappable-pill questions (`values`, `disagreement_style`) → `user_preferences.profile` JSONB (037). Onboarding has "Skip for now"; `/app/profile` is the standalone editable version.
> - **Home tile restructure (D1, #373).** Today → "Home" **label only** (URL stays `/app/today`). A 2×2 typographic tile grid (Discussion = inline `TodaysTopicCard`, Insights → `/app/insights`, Library, Rituals) + a 5th wide Sunday tile. Continue/reflections stay inline.
> - **Explore tab (#374).** The Rituals tab in the bottom bar → an **Explore** tab (Compass icon); tabs are now **Home · Explore · Library · Account**. The existing guide is **re-parented** into `app/app/(tabs)/explore/page.tsx` (the standalone `/app/guide` route and the old `/app/explore` redirect are deleted). The `/app/rituals` route is kept (sub-pages + Home tile still resolve) but delisted.
> - **Chat header affordances (C1, #366/#368/#369).** New states on the chat header: **"← Return to {origin}"** (sticky guest active), **Deep-mode toggle** (Pro only), and a **Council (Scale) icon** (visible to all = upsell; Pro → Council pre-filled, free → upgrade).
> - **Letter write-back window (F4/G14, #370).** A quiet end-of-letter `WriteBackPanel` (Pro) in both the weekly reader and `SeasonFinaleView`; editable; fed forward into the next letter.
> - **Saved-line readability (F1, #365):** conversation-sourced saved-line hero opacity 0.12 → 0.06.
> - **Insight marker (#359):** the in-card ornament is now a **luminous Sparkle** (supersedes the v8 "bronze diamond" note). Discard now shows a 5s **undo toast** (#341). Library tab + source conversation carry a **discoverability glow** that clears on open (#356).
> - **Per-ritual explainer screens (#357):** rituals are tappable → `/app/ritual/[slug]` explainers (`RITUAL_INFO`).
> - **Reading-surface type bump (#364):** base body 15px → 17px, with matching bumps to chat bubbles, insight card, counterview verdicts. `body { zoom: 1.15 }` removed (#363).
> - Screen count: 69 → 72; pending count drops (G17 promoted out of pending).
>
> **Changelog v7 → v8 (2026-06-21):** Insight engine surfaces, insight-seeded Mirror state, G17 Counterview **stub**, Season Finale reader. Full text in `SCREENS_TRACKING_v8.md`.
> **Changelog history v1 → v7:** see `SCREENS_TRACKING_v8.md` / `_v7.md`.

---

## Inventory

### A — Authentication & First-time user

Unchanged from v8 (A0 pending spec; A1–A7 covered). See `SCREENS_TRACKING_v7.md`.

### B — Onboarding

| ID | Screen | Status |
|---|---|---|
| B1–B6 | (existing onboarding flow) | ✅ covered (unchanged from v7). |
| **B7** | **Onboarding profile pills** (`/app/onboarding/profile`) | ✅ **NEW v9 (#372).** Two tappable-pill questions (`values`, `disagreement_style`) → `user_preferences.profile` JSONB. "Skip for now" present. Seeds memory + instant forming reflection. First weekly letter untouched. |

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v9 header states (#366/#368/#369):** "← Return to {origin}" when a sticky guest mind is active; Pro **Deep-mode** toggle; **Council (Scale)** icon (all users; Pro→Council pre-filled, free→`/app/upgrade`). **v9 behaviour:** sticky guest mind (responder = `coalesce(active_persona_id, persona_id)`); adaptive reply length (#367); go-deeper now deepens (#368). Carries v8 insight chip. |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered. **C4 limit:** go-deeper now has its own free cap (3/day per home persona). **C9 another-mind:** one-shot remains the default; stickiness only on explicit "Continue with {guest}". |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today | ✅ covered. **v9 (#373): "Home" label** (URL stays `/app/today`); **2×2 tile grid** (`HomeTile`: Discussion=inline `TodaysTopicCard` · Insights→`/app/insights` · Library · Rituals) + **5th wide Sunday tile**; Continue/reflections inline. The redundant "Explore The Wise Room" button removed (#374). Carries v8 insight card. |
| **D7** | **Insights list** (`/app/insights`) | ✅ **NEW v9 (#373).** Minimal list of non-dismissed insights; each routes to Mirror (`?insightId=`), You-vs-You, or Counterview (`?insightId=`). |
| D6 | "Living in the Wise Room" guide | ✅ shipped. **v9: re-parented into the Explore tab** (`app/app/(tabs)/explore/page.tsx`); standalone `/app/guide` deleted (#374). Carries v8 refresh. |
| D2 / D3 / D4 / ~~D5~~ | Explore (list/grid) / search (deferred v2) / (folded) | ✅ covered. **v9:** the 4 "choose a mind" callers now point to `/app/library?mode=browse` (#374). |

### E — Multi-mind features (post-MVP)

Unchanged from v7 (E1–E5 pending, Phase 5).

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / Reflections feed | ✅ covered. **v9: counterview verdicts (`kind="counterview_verdict"`) appear in the unified feed** (`CounterviewVerdictCard`, #350) alongside saved lines, Mirror/Council/insight verdicts. Conversation-sourced saved-line hero opacity 0.12 → 0.06 (#365). |
| F2 | Suggested insights (in-chat) | ✅ covered (live engine, v20). **v9:** Sparkle marker (#359); 5s undo toast on discard (#341). |
| F3 / F4 | Weekly letter inbox / detail | ✅ covered. **v9: F4 gains the write-back window** (`WriteBackPanel`, Pro, #370) in both the weekly reader and `SeasonFinaleView`. Carries v8 monthly Season Finale state. |
| F5 / F6 | Recurring-themes dashboard (deferred v2) / Past conversations | ✅/⏸ (unchanged). |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G1–G11 | Rituals library / detail / flow | ⚠️/✅ as in v7. **v9: rituals tappable → per-ritual explainer screens (`/app/ritual/[slug]`, #357).** |
| G12 | You vs You | ✅ shipped. **v9:** now also sees the onboarding profile (seeded memory). |
| G13 / G14 | Sunday Letter — library / detail | ✅ shipped. **v9: G14 write-back window (#370)** + carries v8 monthly Season Finale. |
| G15 / G16 | Sunday Letter — Revisit picker / share preview | ✅ shipped (unchanged). |
| **G17** | **The Counterview — LIVE ritual** | ✅ **PROMOTED v9 (#342–#362).** Was a placeholder stub (v8). Now the full ritual — see spec below. |

### H / I / J / K

Unchanged from v7 (H1–H6 billing; I1–I6 account; J1/J2/J3/J5; K1/K2 deferred v2). **Profile screen** (account-adjacent) is new — see below. See `SCREENS_TRACKING_v7.md`.

| ID | Screen | Status |
|---|---|---|
| **I7** | **Profile** (`/app/profile`) | ✅ **NEW v9 (#372).** Standalone editable version of the onboarding profile pills (`values`, `disagreement_style`). No nav link yet (Explore-tab entry point is a parked fast-follow). |

---

## Covered screens — new / updated full specs (v9)

> Specs unchanged since v8 are not reproduced — see `SCREENS_TRACKING_v8.md`. Below are surfaces new or changed in v21.

### G17 — The Counterview (LIVE ritual — #342–#362)

**Screen:** `apps/web/app/app/counterview/page.tsx`. **Backend:** `services/counterview_service.py`, `routers/counterview.py`; migrations 032 (`counterviews` + `counterview_responses`) / 033 (`counterview_saves`).

**Entry paths:**
- **Insight-seeded** — `/app/counterview?insightId=<id>` (from the insight card's "Doubt this"). Auto-generates via `POST /insights/{id}/counterview` (DB-level dedup — re-entry returns the same counterview).
- **Voluntary** — the `input` state: a typed-belief textarea ("Make the case") + a **revisit list** of past counterviews (`GET /counterview`, generated-only, ≤10).

**The pair (fixed):** Miyamoto **Musashi** (position 0, left) and Niccolò **Machiavelli** (position 1, right). Each delivers **one ≤10-word line** making the case against the belief — never against the person.

**States:**
- **Generating:** "Putting it to the test…" while `POST /counterview` (typed) or the insight generate runs.
- **Result (staged reveal):** portraits + names → speaker toggle + first verdict → second verdict → anchor + actions; `prefers-reduced-motion` jumps to final.
  - **Verdict frame:** the active speaker's round-0 verdict (italic). **Go-deeper** (MessageCircle) appears if no round-1 exists for that persona → `POST /counterview/{id}/deeper` adds one sharper **≤18-word** round-1 line (capped at one per persona; persona "exhausted" if it returns nothing).
  - **Anchor display:** "Your insight" (insight source) or "Your belief" (direct source).
  - **Actions:** **Save** (optimistic toggle → `counterview_saves`; appears in Reflections as `kind="counterview_verdict"`), **Share** (`SharePreviewModal` counterview variant → 4:5 Pillow card via `POST /share/counterview`; free 3/90d shared with line shares, Pro unlimited), **Start over** (→ input).
- **Empty / suppressed:** a gentle neutral fallback (safety never exposed). `empty` = LLM returned no case; `suppressed` = safety gate (input or output) tripped.

**Recurrence (slice 1, #361):** a `generated` direct counterview enqueues `counterview_belief_task` — embeds the belief, writes a `MemoryEntry` (`entry_type="counterview_belief"`), runs `detect_recurrence` (6h throttle honoured). No migration. Lets the room later notice the beliefs a person leans on.

### Chat header — sticky guest + deep-mode + Council (C1 — #366, #368, #369)

**Component:** `apps/web/components/chat/ChatHeader.tsx`.

- **Return to origin (#366):** when `active_persona_id` ≠ home persona, a "← Return to {origin}" control (→ `DELETE /conversations/{id}/active-mind`). "Continue with {guest}" sets it (→ `POST …/active-mind`). The header persona, thumbnail, quota and resume all follow the resolved responder.
- **Deep-mode toggle (#368):** shown to Pro only; toggles `conversations.deep_mode` (`POST`/`DELETE …/deep-mode`). When on (and Pro and no distress), every reply is deep. Free users see the go-deeper per-tap path (3/day per home persona).
- **Council icon (#369):** lucide `Scale`, visible to **all** users (upsell), enabled once a user message exists. Seeds the last user message (≤600 chars) via `sessionStorage` (`council_prefill` + `council_source='chat'`); **Pro → `/app/council`** pre-filled, **free → `/app/upgrade`**.

### Home tile grid (D1 — #373)

`apps/web/app/app/(tabs)/today/page.tsx`. Title label "Home" (URL unchanged `/app/today`). A 2×2 `HomeTile` grid — **Discussion** (MessageCircle; expands inline to `TodaysTopicCard`), **Insights** (Sparkles → `/app/insights`), **Library** (Archive), **Rituals** — plus a 5th **wide Sunday tile** (`SundayLetterCard`). Continue + reflections cards remain inline below.

### Insights list (D7 — #373)

`apps/web/app/app/insights/page.tsx`. A minimal standing list of non-dismissed insights via `InsightCard`; each routes to its reflection: Mirror (`/app/mirror?insightId=`), You-vs-You (`/app/you-vs-you`), or Counterview (`/app/counterview?insightId=`).

### Profile pills (B7 onboarding / I7 standalone — #372)

`apps/web/app/app/onboarding/profile/page.tsx` (with "Skip for now") and `apps/web/app/app/profile/page.tsx` (standalone editable). Two tappable-pill questions (`values`, `disagreement_style`) → `user_preferences.profile` JSONB (`PATCH /preferences/profile`). Saving seeds embedded `memory_entries` (`entry_type='onboarding_profile'`) and triggers an instant forming reflection (`POST /preferences/profile/reflection`). The persona shows awareness on turn 1 via a `<what_we_know>` prompt block (not recall). Enum→phrase mapping is centralized in `services/profile_text.py`.

### Explore tab (#374)

`apps/web/components/layout/BottomTabBar.tsx` — tabs are **Home · Explore · Library · Account** (Explore = Compass icon, replacing the Rituals tab). `app/app/(tabs)/explore/page.tsx` is the re-parented guide (back chrome stripped; safe-area top padding). The `/app/rituals` route is kept (sub-pages + Home tile resolve) but delisted from the bar. The standalone `/app/guide` route and the old `/app/explore` redirect are deleted; 4 "choose a mind" callers repoint to `/app/library?mode=browse`.

### Letter write-back window (F4 / G14 — #370)

`apps/web/components/letters/WriteBackPanel.tsx`, wired into the weekly reader and `SeasonFinaleView` via `app/app/letters/[id]/page.tsx`. A quiet end-of-letter window (Pro): editable textarea (read-only display once saved), `PATCH /weekly-letters/{id}/write-back` (`weekly_letters.write_back_text`/`write_back_at`, migration 036). One write-back per letter, editable; fed forward as `<reader_wrote_back>` into the next letter. v1: no live reply, no insight-seeding.

---

## App icon — deferred

Unchanged (TD-29). No custom app icon on main. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v9.** Authoritative as of 2026-06-26 (Counterview live ritual · Insights list · Profile pills · Home tiles · Explore tab · chat header affordances · letter write-back). Supersedes `SCREENS_TRACKING_v8.md` (preserved as historical reference).
</content>
