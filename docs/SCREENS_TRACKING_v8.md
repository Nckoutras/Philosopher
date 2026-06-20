# GREAT MINDS — Screens Tracking v8

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 69 screens** (v8 adds **1 new screen**: G17 The Counterview — placeholder stub. The insight surfaces from #323/#327/#332/#333/#334 are new states/components on existing screens (C1 chat, D1 Today, F2 insight); the insight-seeded reflection is a new state of the Mirror reader; the monthly season finale is a new state of the letter detail (F4/G14).)
> **Effective specced count: 49** (Blocks 1–6 + Block 9 covered; D6 + G13–G16 shipped; G17 stub pending fuller spec; A0 pending spec)
> **Pending: 15** (A0 spec + Block 7 Rituals fuller-flow specs incl. G17 Counterview ritual + Block 8 Multi-mind 5 + K1/K2 deferred v2 + D4 deferred v2 + F5 deferred v2)
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`) — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect
> - `IMPLEMENTATION_BACKLOG_v20.md` — non-UI implementation work
>
> **Last updated:** 2026-06-21 (v8).
>
> **Changelog v7 → v8 (2026-06-21):**
> - **Insight engine surfaces (live, #323/#324/#327/#332/#333/#334).** The "Suggested insight" (F2) is now a real engine: a recurrence/shift detector writes durable Insights and surfaces them in three places — (1) an in-chat quietly-glowing **chip** on the last assistant message that expands to the **InsightCard** (C1/F2); (2) a passive standing **insight card on Today** (D1, `variant='today'`, brand seal `/insight_seal.png`, 14-day staleness window); (3) the card's **three actions**: "Reflect in the Mirror" (primary), "Doubt this" (→ G17 Counterview stub, does NOT dismiss), "Discard this" (dismiss). A **provenance line** ("Noticed across N of your conversations") shows when `source_count >= 2`. A `shift` insight's primary is "See how this changed" → G12 You vs You.
> - **Insight-seeded Mirror — new state of the Mirror reader (#335/#336/#337).** "Reflect in the Mirror" routes to `/app/mirror?insightId=<id>`; the reader POSTs `/insights/{id}/reflect`, shows a **"Holding up the mirror…"** wait, then runs the existing said/meant + thread reveal in the source persona's voice. `empty`/`suppressed` → a gentle neutral fallback (no animation/controls). The weekly mirror reader (no `insightId`) is unchanged.
> - **G17 The Counterview — placeholder stub (#334).** New screen `app/app/counterview/page.tsx` — DS v5 vellum, Cormorant "Counterview", a quiet "on its way" line, back control. Target of "Doubt this". The ritual itself is unbuilt.
> - **Monthly Season Finale reader — new state of F4/G14 letter detail (#328–#331).** When `letter.kind === 'monthly'`, `app/app/letters/[id]/page.tsx` renders `components/letters/SeasonFinaleView.tsx` (through-line / what changed / season ahead / keepsake pull-quote + typographic W-monogram seal); a branded season share card via `seasonImagePreview`.
> - **D6 Guide refresh (#318/#320/#322):** Wise Room copy refresh + ritual rename + minds synced to 11; minds tappable to persona detail; responsive thumbnails + press effect + taller hero. Sunday-letter links → buttons (#319, G13/G14). iOS share Send gated on prepared image (#321).
> - Screen count: 68 → 69; pending unchanged at 15 (G17 added as both a stub screen and a pending ritual spec).
>
> **Changelog v6 → v7 (2026-06-16):** No new screens; persona portraits → WebP standard (#315); roster 9 → 11 with Orwell + Musashi Pro pills (#316). Full text in `SCREENS_TRACKING_v7.md`.
>
> **Changelog history v1 → v6:** see `SCREENS_TRACKING_v7.md` (Blocks 3–9 additions, A0, G5–G16, J4 dropped, etc.).

---

## Inventory

### A — Authentication & First-time user

Unchanged from v7 (A0 pending spec; A1–A7 covered). See `SCREENS_TRACKING_v7.md`.

### B — Onboarding

Unchanged from v7 (B1–B6 covered). See `SCREENS_TRACKING_v7.md`.

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v8: in-chat insight chip** on the last assistant message (`QuickActionsRow`) → expands to `InsightCard` (variant `chat`) when the recurrence/shift detector has written an Insight (#323). |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered (unchanged from v7). |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today | ✅ covered. **v8: passive insight card** (`InsightCard variant='today'`, brand seal `/insight_seal.png`, `TODAY_INSIGHT_MAX_AGE_DAYS=14`) surfaces the insight spine; primary "Reflect in the Mirror" → `/app/mirror?insightId=`; "Doubt this" → G17; "Discard this" dismisses (#327, #332). Carries v7 state (consolidated "What brings you here?" card, Sunday-letter card, greeting/NamePromptCard). |
| D6 | "Living in the Wise Room" guide | ✅ shipped. **v8: copy refresh + ritual rename + minds synced to 11; tappable minds → persona detail; responsive thumbnails + press effect + taller hero (#318/#320/#322).** |
| D2 / D3 / D4 / ~~D5~~ | Explore (list/grid) / search (deferred v2) / (folded) | ✅ covered (unchanged from v7). |

### E — Multi-mind features (post-MVP)

Unchanged from v7 (E1–E5 pending, Phase 5).

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / Reflections feed | ✅ covered. **v8: insight-seeded mirrors (`kind="insight"`) appear in the unified feed** like any saved Mirror (save/ring-true/share). Carries v6 unified feed + search. |
| F2 | Suggested insights (in-chat) | ✅ covered — **v8: now a live engine, not lite.** Recurrence + shift detector (`detect_recurrence`, wired into the ARQ `extract_memory_task`); in-chat chip + Today card + three-action card + provenance. See "Insight surfaces" spec below. |
| F3 / F4 | Weekly letter inbox / detail | ✅ covered. **v8: F4 gains the monthly Season Finale state** — `SeasonFinaleView` renders when `kind==='monthly'` (#330); season share card (#331). See G14 + "Season Finale" spec below. |
| F5 / F6 | Recurring-themes dashboard (deferred v2) / Past conversations | ✅/⏸ (unchanged from v7). |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G1–G11 | Rituals library / detail / flow / Mirror setup-rounds-closing / Counterview setup-rounds-closing / Weekly Reading placeholder | ⚠️/✅ as in v7 (G5–G10 pending fuller specs; G11 superseded by the reader surface). |
| G12 | You vs You | ✅ shipped (unchanged from v7). |
| G13 | Sunday Letter — reading library | ✅ shipped. **v8: links → buttons (#319).** |
| G14 | Sunday Letter — reading detail | ✅ shipped. **v8: monthly `kind` → `SeasonFinaleView` (#330); season share card (#331).** |
| G15 | Sunday Letter — Revisit persona picker | ✅ shipped (unchanged from v7). |
| G16 | Sunday Letter — share preview | ✅ shipped (unchanged from v7). |
| **G17** | **The Counterview — placeholder stub** | ⚠️ **NEW v8 (#334). Stub only:** `app/app/counterview/page.tsx` — DS v5 vellum, Cormorant "Counterview", quiet "on its way" line, back control. Target of the insight card's "Doubt this". **The Counterview ritual (G8–G10 fuller flow) is still unbuilt/undesigned.** |

### H / I / J / K

Unchanged from v7 (H1–H6 billing covered; I1–I6 account covered; J1/J2/J3/J5 covered, J4 dropped; K1/K2 deferred v2). See `SCREENS_TRACKING_v7.md`.

---

## Covered screens — new / updated full specs (v8)

> Specs unchanged since v7 (A/B/C2–C9/D2–D6/F1/F3/F6/H/I/J) are not reproduced here — see `SCREENS_TRACKING_v7.md`. Below are the surfaces new or changed in v20.

### Insight surfaces (F2 engine — #323, #324, #327, #332, #333, #334)

**Component:** `apps/web/components/chat/InsightCard.tsx` (shared by chat + Today via `variant`).

**Engine (backend):** `services/memory_service.py:detect_recurrence`, wired into the ARQ `extract_memory_task`. Writes a durable `Insight` (`insight_type` `pattern` | `shift`, `source_count`) when a just-raised memory echoes prior OTHER conversations (cosine ≥ 0.75, ≥1 prior match; throttle 6h/user, max one per conversation).

**Eyebrow:** "The Wise Room · Insight" (Lora 9px, sepia, uppercase, 0.18em).

**Provenance line (#333):** directly under the eyebrow, when `source_count != null && source_count >= 2`: "Noticed across {N} of your conversations" (Lora 10px, sepia). Absent otherwise.

**Ornament:**
- **chat variant** (left-indented vellum card inside the thread): compact bronze diamond (9×9, rotate-45).
- **today variant** (standing card on Today, bg-paper): 44×44 brand seal `/insight_seal.png` (#332).

**Content:** the insight text (Cormorant 17px italic, ink).

**Three actions (#334), clear hierarchy:**
- **Row 1 — "Reflect in the Mirror"** (primary, full-width, bg-ink). For a `shift` insight: **"See how this changed"** → `/app/you-vs-you`. For non-shift: → **`/app/mirror?insightId={id}`** (insight-seeded reflection).
- **Row 2 — "Doubt this"** (bordered, border-ink) → **`/app/counterview?insightId={id}`** (G17 stub). **Does NOT dismiss.**
- **Row 2 — "Discard this"** (quietest: border-edge + sepia) → dismisses the insight (`PATCH /insights/{id}/dismiss` + remove from view).

**In-chat chip (C1):** before expansion, a quietly-glowing chip on the last assistant message (`QuickActionsRow`); tap expands to the card. **Today (D1):** the card stands directly (no chip), within the 14-day staleness window.

### Mirror reader — insight-seeded state (G-section / Mirror — #335, #336, #337)

**Screen:** `apps/web/app/app/mirror/page.tsx` (same reader as the weekly Mirror).

**Entry:** `/app/mirror?insightId=<id>`. The reader reads `insightId` from `window.location.search` inside the load effect (Suspense-safe, no `useSearchParams`).

**States:**
- **Generating:** a brief **"Holding up the mirror…"** screen (Cormorant italic, vellum) while `POST /insights/{id}/reflect` runs (synchronous, a few seconds).
- **Generated:** the existing reveal animation (said/meant moments + thread) in the **source persona's voice**, with save / "did this ring true" / share — all reused unchanged (the insight mirror is a `Mirror` row, `kind="insight"`). Re-opening the same insight returns the same mirror (dedup by `insight_id`) — no second wait.
- **Empty / suppressed:** a gentle neutral fallback — "There wasn't enough there to hold up to the light just yet." + back control. No reveal animation, no save/ring-true/share. Same copy for empty and suppressed (never exposes safety detection).

**Weekly mirror (no `insightId`):** unchanged — `get_latest_mirror` excludes `kind="insight"` (#336), so the weekly reader never shows an insight mirror.

### G17 — The Counterview (placeholder stub — #334)

**Status:** ⚠️ stub. `apps/web/app/app/counterview/page.tsx`.

**Structure:** DS v5 vellum full-screen; back control (top-left); centered eyebrow "The Wise Room" (Lora, bronze-dark, uppercase); Cormorant "Counterview" heading; a quiet Lora/sepia line ("A second reading of this insight — the case against it — is on its way.").

**Behavior:** reached from the insight card's "Doubt this". Receives `?insightId=` in the URL but does **not** read it yet (deliberately no `useSearchParams` until the ritual is built — avoids a Suspense boundary in a do-nothing stub). The Counterview ritual (rounds/closing — G8–G10) is undesigned/unbuilt.

### F4 / G14 — Monthly Season Finale reader (#328–#331)

**Component:** `apps/web/components/letters/SeasonFinaleView.tsx`. **Dispatch:** `apps/web/app/app/letters/[id]/page.tsx` renders it when `letter.kind === 'monthly'` (else the standard weekly reader).

**Structure:** a premium season reader — through-line (opening) / what changed (references) / the season ahead (forward_gesture) / a centered keepsake pull-quote bracketed by bronze rules / a typographic **W-monogram seal** (no image asset).

**Share:** branded season card via `seasonImagePreview={letter.kind === 'monthly'}` into `SharePreviewModal` (#331) — no new static asset.

**Backend:** `generate_monthly_letter_task` (calendar month, `MONTHLY_MIN_MESSAGES=15`) writes a `weekly_letters` row with `kind='monthly'` (migration 029); `WeeklyLetterOut.kind` exposed (#329); delivered by email via the shared `_maybe_send_weekly_letter_email` (`reading_label="monthly"`).

---

## App icon — deferred

Unchanged from v7 (TD-29). No custom app icon on main. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v8.** Authoritative as of 2026-06-21 (Insight engine surfaces · insight-seeded Mirror state · G17 Counterview stub · Season Finale reader). Supersedes `SCREENS_TRACKING_v7.md` (preserved as historical reference).
