# PHILOSOPHER — Project State v22

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v22 = v21 baseline (2026-06-26, captured through PR #374 / `fed8d312`) + 2026-06-26→2026-07-09 delta (#375–#447).** The dominant arc is the **Self-Portrait** feature, built end-to-end across ~38 PRs (quiz → forming/ready portrait → radar + territorial map → shareable card → observation surfaces → best-fit-to-chat), plus **Counterview user-rebuttal turns**, the **Explore guides** build-out, **Council decision-architecture**, **dilemma/belief insight doorways + Home "room noticed" card**, a **Home image-tile** redesign, and letters/YvY continuity beats. Migrations **038–042**.
>
> **Migration head moved 037 → 042.**
>
> **v21 = v20 baseline + #339–#374:** Counterview ritual end-to-end (backfill), chat sticky-guest / adaptive length / go-deeper depth + Pro deep mode, Chat → Council, letter write-back, onboarding profile pills, Home tiles + Explore tab. Migrations 032–037. Full detail in `PROJECT_STATE_v21.md`.
>
> **Generated:** 2026-07-09 (v22 rotation) · **Last updated:** 2026-07-09 (Self-Portrait arc + Counterview turns + Explore guides + Council decision architecture + insight doorways + corrections; current main `aa3ecafd`)

> **v22 conflict resolution rule:** Where v22 conflicts with v21 or earlier, v22 wins. **Production reality always wins over docs.**

> **⚠️ PROVENANCE — read this before trusting Part A.** #375 is the v21 doc PR itself (it documented through #374). **None of #376–#447 was reviewed in a v21→v22 working session** — the entire v22 delta (Self-Portrait, Counterview turns, Explore guides, Council decision architecture, insight doorways, Home redesign, letters/YvY beats) was built outside these sessions and its v22 documentation was **reconstructed by reading the merged code at `aa3ecafd`**, not from session review. Treat Part A as code-derived, not session-verified — re-read the source before building on it.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive; do not write to it. All Render services must point to Oregon.**

---

## Part A — v22 delta (#376–#447) — reconstructed from merged code

> Built between the v21 doc cut (#374/#375) and this rotation, across a prior/founder session series. **Reconstructed by reading the merged code at `aa3ecafd`**, not session-reviewed. Re-read the source before building on it.

### A1. Self-Portrait — the dominant new feature (~38 PRs, #387–#427, #433, #437, #447)

A Pro-gated self-knowledge instrument: the user answers themed questions, and the room renders a present-tense "portrait" of the life areas they weigh most — as a radar shape, a territorial map, a shareable card, and a best-fit persona recommendation.

- **Question bank + quiz UI (#387, #388, #390, #394, #418):** `apps/api/data/question_bank.json` — **360 questions across 12 categories** (conflict, desire, family, fear, friendship, identity, meaning, money, mortality, relationships, solitude, work_and_ambition). The quiz interleaves questions across categories (round-robin), with a category picker, revisit filter, entry shell, and quiet acknowledgements. Screen: `app/app/(tabs)/self-portrait/page.tsx`.
- **Tier gate (#388):** free users see `FREE_QUESTION_LIMIT = 15` questions (round-robin across categories, `services/self_portrait.py:visible_questions`); Pro/premium see all 360. `GET /preferences/self-portrait` returns the visible set + stored answers + `is_pro` + `locked_count`; a fresh user (no preferences row) still sees the questions (does **not** 404).
- **Answer persistence + fan-out (#387, #389):** answers are stored in `user_preferences.profile["answers"]` (reuses the 037 `profile` JSONB — no new column for answers). ARQ pipe (`workers/arq_worker.py`) seeds answers into `memory_entries`, feeds Sunday letters, and reinjects into You-vs-You; edits emit an "edit-as-change" shift signal. Guards YvY.
- **Forming → ready portrait (#395, #396, #397, #400):** `GET /preferences/self-portrait/portrait` is a **breadth-aware gate** — `state='forming'` until answers span enough life areas, then `state='ready'`. The payload **never carries a count / % / fraction**, only `state` + surfaced content.
  - **Forming** — cheap `forming_reflection()` observation lines from the user's OWN answers ("Room notices"), plus artwork cards; describes HOW they answered, never a diagnosis.
  - **Ready (5b)** — a cached **Sonnet summary** + **persona best-fit** (bridge map). Cache lives in **`user_preferences.portrait_cache` JSONB (migration 039)**: `{text, best_fit[], answer_count_watermark, generated_at}`. Regenerates synchronously only when the cache is missing or `≥ PORTRAIT_REGEN_DELTA (8)` new answers stale, then writes back. A valid cache is served WITHOUT calling `forming_reflection` (a ready open never pays both LLM paths). Summary generation is best-effort with a failure-cooldown — any failure falls back to a prior cache or the forming preview and still returns 200 (never 500s the portrait). Services: `self_portrait.py`, `self_portrait_prompts.py`, `self_portrait_summary.py`.
- **Radar view (#397, #401, #402, #403, #407, #408, #409, #411, #427):** `components/self-portrait/PortraitRadar.tsx` — curated `theme_scores` axes rendered as a top-5 pentagon with a compass rose, walnut/perimeter frame, denser data fill, evolved to the approved mock.
- **Map view (#404, #407, #411, #420–#422, #426, #447):** `components/self-portrait/PortraitMap.tsx` — a Shape/Map toggle over the same `theme_scores`. Evolved from decorative tethers → data-driven territories → static hand-drawn cartographic territories (`map-territories.webp`) with rank-assigned names, a dominant-territory highlight, an X marker, and a compass-rose needle pointing to the dominant theme. Re-arted in #447.
- **Shareable card (#405, #410, #425, #432):** `lib/portraitShareCard.ts` — a client-side canvas card (ungated, preview-first): title, viz, deterministic summary line, date, QR. Recomposed several times to the current radar aesthetic.
- **Observation surfaces (#400, #408, #424):** `lib/selfPortraitObservations.ts`, `lib/selfPortraitObservationCards.ts`, `lib/selfPortraitCaption.ts`, `lib/selfPortraitMapCaptions.ts`, `lib/selfPortraitSummary.ts` — answer-pause "Room notices", observation cards, and a **deterministic summary line** (replaced an earlier Pull/Edge strip).
- **Entry + coverage (#412, #416, #417, #419, #423):** entry-screen hero + wordmark/subtitle + pill CTAs; a category-coverage progress bar; mock-aligned revisit card list with double CTA.
- **Best-fit → chat (#437):** from the ready portrait, "take the best-fit mind to chat" opens a conversation with a prefilled first sentence.
- **Tab bar (#388, #406):** a new **Self Portrait** tab (Easel icon, `/app/self-portrait`) — it **replaced Library in the bottom bar**. Tabs are now **Home · Explore · Self Portrait · Account**. Library remains reachable (Home tile / Explore); the `/app/library` route is unchanged.
- **Assets (#401, #413, #414, #415, #433):** theme/card WebP set under `public/self-portrait/`; `rose.png → rose.webp` (99.8% smaller, then transparent line-art), `mirror.png → mirror.webp` (~97% smaller), `appbutton.png`.

### A2. Counterview — bounded user-rebuttal turns (#376, #377, #443)

Extends the shipped Counterview ritual with a **short, bounded back-and-forth**.

- **`counterview_turns` table (migration 038):** one row per rebuttal turn — `sequence`, `persona_slug` (the current speaker = who answers), `user_text` (passed `check_input` before insert), `persona_response` (≤18-word reply, NULL unless `status='generated'`), `status ∈ {generated,empty,suppressed}`. `UNIQUE (counterview_id, sequence)` orders the thread and guards the insert race. **Kept on its own table so `counterview_responses.round` (verdict/go-deeper axis, capped at 1) is untouched — the two axes never share a key.**
- **`POST /counterview/{id}/respond` (`CounterviewRespondRequest{text, persona_slug}`):** the current speaker replies in one tight (≤18-word) line, same tighten-retry as go-deeper. Bounded at **`MAX_REBUTTALS = 3` generated** turns per counterview (`409 rebuttal_cap_reached` once met). A suppressed input / empty generation / suppressed output persists a turn with that status (no reply) and still returns 200. The returned `CounterviewOut` carries `turns[]` + updated `rebuttals_remaining`. Service: `counterview_service.py:respond_to_rebuttal`. Tests: `tests/services/test_counterview_rebuttal.py`.
- **Rebut-in-place UI (#377):** `app/app/counterview/page.tsx` — rebut the current speaker in place (#11 UI).
- **"What still stands" closing line (#443):** `counterviews.still_stands TEXT` (migration 041) — one quiet closing line naming what of the belief survives the challenge, generated on the **same LLM call** as the two verdicts (grounded-or-null). Old rows stay NULL and render as before.

### A3. Explore guides build-out (#382, #428, #429, #430, #431, #432, #434, #446)

The Explore tab (re-parented guide, v21) grew into a set of plain-language teaching pages.

- **"The Conversations" guide (#382, #430):** `app/app/explore/conversations/page.tsx` — teaches the in-chat tools; #430 added **Council + Deep-mode** blocks and a sticky-guest fix.
- **"Reflections & portraits" guide (#431):** `app/app/explore/reflections/page.tsx` + pushable hero.
- **"The room remembers" memory explainer (#434):** `app/app/explore/memory/page.tsx` + section wiring.
- **Explore index rewrite (#428, #429, #432, #446):** plain-language feature + storage map, higher-contrast titles, pushable hero image for "The conversations", text-first restructure, hero crop fix (reveal armchair+window, unclip W wordmark).

### A4. Council — decision architecture (#386, #444)

- **Essence brief (#386):** `council_service.py` / `council_prompts.py` distil a chat conversation into an essence brief for the members before they deliberate.
- **Decision instrument (#444):** `council_sessions.synthesis_structured JSONB` (migration 042) — the structured close **real_question / tension / verdict / next_move**. The flat `synthesis` TEXT column stays populated (with the verdict beat) so the Reflections feed and share card keep reading it unchanged; old sessions have `synthesis_structured NULL` and the live screen (`app/app/council/page.tsx`) falls back to the flat synthesis.

### A5. Insight doorways + Home "room noticed" (#438, #439, #440, #556607d7)

- **Dilemma/belief signal detection (#438):** `memory_service.py` (via `conversation_service.py` + `arq_worker.py`) detects explicitly-stated dilemma/belief signals during memory extraction and promotes at most one per call to an `Insight` (safety-clean, same throttle/dedup gate as recurrence; `source_count=None` on this path — see §19 note).
- **Doorway chips (#439):** `app/app/chat/conv/[id]/page.tsx` + `components/chat/InsightCard.tsx` — dilemma/belief "doorway" chips route into Council / Counterview.
- **Home "The room noticed" card (#440):** `components/today/RoomNoticedCard.tsx` + `lib/useInsightDoors.ts` — surfaces detected signals on Home.

### A6. Home redesign + letters + YvY + chat (misc)

- **Home image tiles (#378, #379, #384, #393):** `app/app/(tabs)/today/page.tsx` — the v21 typographic 2×2 grid became **image-card tiles** (WebP per tile: discuss/insights/revisit/rituals), a new **Discuss route** (`app/app/discuss/page.tsx` + `lib/useTopicConversation.ts`), Continuing/Reflections cards relocated (into `library`/`insights`), centered/enlarged white tile words, priority above-the-fold images, and LQIP blur placeholders (`scripts/mint-image-lqip.py`).
- **Letters (#380, #391, #392, #398, #399, #436, #445):** Sunday next-reading line + `nextSundayLabel` UTC fix; letter sign-off + Portrait tab Frame icon + insights title copy; persona thumbnail on saved-reading cards; practical takeaway per letter + light letter-to-letter continuity; the "something new" star extended to unread Sunday/season letters (`components/layout/LettersBootstrap.tsx`); prefill first message on suggested-persona tap; **"What went unspoken" avoidance line** in the letter generator (`arq_worker.py`).
- **You-vs-You (#389, #441, #442):** reinject into Self-Portrait + edit-as-change shift signal; hidden continuity + "sentence owed" closing beats; **save "the sentence you owe yourself" to the Reflections feed** — `self_comparison_saves` table (migration 040, mirrors `counterview_saves`), `POST`/`DELETE /self-comparison/{id}/save`, `reflections_feed_service` pulls `payload["closing"]["sentence_owed"]`, rendered by `components/reflections/YvYSentenceCard.tsx`.
- **Chat (#385, #435):** "take to Council" moved from a header icon to a quick-action chip (`components/chat/QuickActionsRow.tsx`); `chat/conv/[id]` resilience — opening fallback, graceful 404, Continuing-card sync.
- **Store fix (#383):** `lib/store.ts` — derive `plan` as real state instead of a getter (Zustand persist freeze).

---

## Changelog v21 → v22 (PR history, newest first)

| PR | SHA | Description |
|---|---|---|
| #447 | aa3ecafd | feat(self-portrait): re-art map + retarget label anchors to new territories |
| #446 | 29b13062 | fix(explore): reveal armchair+window in hero, unclip W wordmark |
| #445 | 9193a697 | feat(letter): "What went unspoken" avoidance line |
| #444 | 2eaa2914 | feat(council): decision architecture — real question, roles, one next move (migration 042) |
| #443 | e53bf770 | feat(counterview): "What still stands" closing line (migration 041) |
| #442 | 78f46e63 | feat(yvy): save "sentence you owe yourself" to Reflections feed (migration 040) |
| #441 | c721bfcf | feat(yvy): hidden continuity + sentence owed closing beats |
| #440 | 556607d7 | feat(home): The room noticed card |
| #439 | 42bba1ba | feat(chat): dilemma/belief doorway chips |
| #438 | b06fc677 | feat(insights): detect dilemma/belief signals via memory extraction |
| #437 | 6ca644c2 | feat(portrait): take best-fit mind to chat with prefilled first sentence |
| #436 | 4c654272 | feat(letters): prefill first message on suggested-persona tap |
| #435 | 87f9e6af | fix(chat): conv/[id] resilience — opening fallback, graceful 404, Continuing sync |
| #434 | dd805368 | feat(explore): The room remembers explainer + section wiring |
| #433 | c7393653 | chore(self-portrait): add appbutton.png asset |
| #432 | 8ee89697 | polish(self-portrait,explore): spacing, map share fix, radar enlargement, summary, text-first |
| #431 | ac73eb62 | feat(explore): reflections & portraits guide + pushable hero |
| #430 | e0be7a68 | feat(explore): conversations guide — add Council + Deep mode, sticky-guest fix |
| #429 | 4eb859de | feat(explore): pushable hero image for The conversations |
| #428 | abe4dd28 | feat(explore): plain-language feature + storage map, higher-contrast titles |
| #427 | bafb3384 | feat(self-portrait): denser radar data fill |
| #426 | 629317f7 | feat(self-portrait): map label polish — brown names, dominant highlight, X marker |
| #425 | e1117848 | feat(self-portrait): recompose share card — title, larger viz, summary, date, QR |
| #424 | 1b242def | feat(self-portrait): replace Pull/Edge strip with deterministic summary line |
| #423 | 1dce0e5b | feat(entry): wordmark + subtitle, enlarged hero |
| #422 | 53c63069 | feat(map): static hand-drawn territories, rank-assigned names, needle → dominant |
| #421 | ea5ab152 | feat(map): territory polish — cartographic shapes, stacked labels, strip card |
| #420 | e267419b | feat(map): data-driven stable-world territories + single-axis strip |
| #419 | acd4b507 | feat(revisit): mock-aligned card list + double CTA |
| #418 | 9b7c2900 | feat(questions): mock-aligned restyle (wordmark, coverage header, notices, pills) |
| #417 | dedafcae | feat(portrait): category-coverage progress bar |
| #416 | 3f19889f | style(portrait): legacy blocks on vellum + entry hero fill-crop |
| #415 | 7a645d49 | chore(assets): transparent line-art rose |
| #414 | c2a5aefd | chore(assets): compress mirror.png → mirror.webp (~97% smaller) |
| #413 | be677335 | chore(assets): compress self-portrait rose.png → rose.webp (99.8% smaller) |
| #412 | 5196e1cf | feat(portrait): entry screen hero + pill CTAs |
| #411 | 4725112a | feat(portrait): map compass rose overlay + needle, revisit/pill polish |
| #410 | 4c6e15e6 | feat(portrait): recompose share card to new radar aesthetic |
| #409 | b96f3a3b | feat(portrait): larger radar, raster rose, perimeter frame, wider toggle |
| #408 | 114a50fe | feat(portrait): restyle radar + page to approved mock (pentagon, rose, cards, pills) |
| #407 | 8bf4f380 | feat(portrait): walnut-framed radar, territorial map, caption, share/save buttons |
| #406 | b7a180e4 | feat(portrait): rename tab to "Self Portrait" + easel icon |
| #405 | 2622e264 | feat(self-portrait): Phase B3 — shareable portrait card (client canvas, preview-first) |
| #404 | 759cf1a9 | feat(self-portrait): Phase B2 — map view + Shape/Map toggle |
| #403 | 4795da12 | fix(self-portrait): frame texture opacity + transparent radar + guard watermark |
| #402 | 20f1fbca | fix(self-portrait): gate radar frame texture behind USE_RADAR_FRAME |
| #401 | 79ba3135 | feat(self-portrait): UX phase B — PortraitRadar + theme/card asset set |
| #400 | 4c0ee1e4 | feat(self-portrait): Phase A — "Room notices", artwork cards, observation pools |
| #399 | 2c7b4e9b | feat(ui): extend "something new" star to unread Sunday/season letters |
| #398 | a673506d | feat(letters): practical takeaway per letter + light continuity |
| #397 | 22e389df | feat(self-portrait): payoff 5c — view toggle + portrait render + YvY cross-link |
| #396 | 0028a7f2 | feat(self-portrait): payoff 5b — Sonnet summary + persona best-fit (cached, cooldown) |
| #395 | 0497853a | feat(self-portrait): payoff 5a — breadth gate + forming endpoint + cache column (migration 039) |
| #394 | fa9eb175 | feat(self-portrait): interleave questions + category picker, revisit filter, entry shell |
| #393 | 4bedc777 | perf(images): blur LQIP placeholders for hero + home tiles |
| #392 | 2953a53c | feat(letters): persona thumbnail on saved-reading cards |
| #391 | 6490df63 | feat(ui): letter sign-off + Portrait tab Frame icon + insights title copy |
| #390 | 1fd2ef2f | content(self-portrait): expand question bank to 360 (12 categories) |
| #389 | d8a8c9bd | feat(self-portrait): YvY reinject + edit-as-change shift signal |
| #388 | c4563db6 | feat(self-portrait): quiz UI + GET endpoint + Pro gating; Library→Portrait tab |
| #387 | 2ed07ad4 | feat(self-portrait): backend pipe — persist answers, seed to memory, feed Sunday letters |
| #386 | d73326ca | feat(council): distil chat conversation into an essence brief for the members |
| #385 | 91177592 | feat(chat): move "take to Council" from header icon to a quick-action chip |
| #384 | 0a294c89 | perf(home): mark above-the-fold tile images as priority |
| #383 | 421d70ec | fix(store): derive `plan` as real state instead of a getter (Zustand persist freeze) |
| #382 | 6d4d23ab | feat(explore): "The Conversations" guide — teach the in-chat tools |
| #381 | 7fbf039b | feat(reflections): quiet per-kind type marker on each reflection card |
| #380 | 1951b4c6 | feat(sunday-letter): clean folder + next-reading line; fix nextSundayLabel UTC |
| #379 | bb32fe84 | feat(home): center + enlarge the white word on Home image tiles |
| #378 | 69ccd580 | feat(home): image-card 2×2 tiles + Discuss route; relocate Continuing/Reflections |
| #377 | e34c6be6 | feat(counterview): rebut the current speaker in place (#11 UI) |
| #376 | f8209f1a | feat(counterview): bounded user rebuttal exchange — POST /counterview/{id}/respond (migration 038) |
| #375 | 12c6441d | docs: v21 / v9 rotation (the v21 doc cut — docs only) |

Earlier PR history (v20 → v21): see `PROJECT_STATE_v21.md`.

---

## Earlier session deltas (v16 → v21)

Carried forward by reference (additive convention):
- **v21** (#339–#374, Counterview backfill + chat depth/router + letters write-back + onboarding profile + Home/Explore, migrations 032–037) — `PROJECT_STATE_v21.md`.
- **v20 / v19 / v18 and earlier** — `PROJECT_STATE_v20.md` / `_v19.md` / `_v18.md`.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

Unchanged from v19–v21. (Next.js 14 / FastAPI / Postgres 17 Supabase Oregon / Redis+ARQ / **APScheduler in-process for cron** / Anthropic Claude / OpenAI embeddings / OTP+JWT / Stripe sandbox / Resend / Pillow share cards / client-side canvas for the portrait share card.)

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-07-09** — Self-Portrait arc (#387–#427, #433, #437, #447), Counterview turns (#376, #377) + still-stands (#443), Explore guides (#382, #428–#434, #446), Council decision architecture (#386, #444), insight doorways + room-noticed (#438–#440), Home image tiles (#378, #379, #384, #393), letters/YvY beats. Current main: `aa3ecafd`. Prior deploy 2026-06-26 — #374 (`fed8d312`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3–5 fresh users still pending)

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; PR1 #77). Live wiring pending (TD-28).
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false`. Tier enforcement live via `get_user_tier`.
- **Rituals:** **Mirror ✅** · **Council ✅** (+ Chat → Council v21; **+ decision-architecture synthesis v22, #444**) · **You vs You ✅** (**+ sentence-owed save → Reflections v22, #442**) · **Weekly Reading / Sunday Letter ✅** (+ ARQ/APScheduler email, season finale, write-back; **+ takeaway/continuity/avoidance-line v22**) · **Counterview ✅** (**+ bounded user rebuttal turns + still-stands closing v22, #376/#377/#443**) · **Letter to Future Self ✅ delivery LIVE** (APScheduler cron, see §19 correction) — **no remaining unbuilt rituals.**
- **Self-Portrait:** **LIVE (v22, Pro-gated quiz)** — 360-question bank / 12 categories; forming → ready portrait (breadth gate); Sonnet summary + persona best-fit (cached `portrait_cache`, 039); radar + territorial map (Shape/Map toggle); shareable client-canvas card; best-fit → chat. New **Self Portrait** tab (replaced Library in the bar).
- **Insight engine:** LIVE — recurrence + shift detector; **v22: dilemma/belief signal detection (#438) + doorway chips (#439) + Home "room noticed" card (#440).**
- **Reflections:** Unified feed — saved lines + Mirror/Council/Counterview verdicts + `kind="insight"` mirrors + **`kind` YvY sentence-owed (v22, #442)**; client-side search.
- **Share:** v3 / Council / Letter / Season / Counterview 4:5 / **Self-Portrait card (client canvas, v22).**

---

## 3. Personas registered

Unchanged — **11 personas** (Free: Marcus Aurelius, Socrates, Lao Tzu; Pro: de Beauvoir, Epictetus, Freud, Jung, Wilde, Machiavelli, Orwell, Musashi). Council roster fixed (Machiavelli, Epictetus, Freud, de Beauvoir). Counterview pair fixed (Musashi + Machiavelli). See `PROJECT_STATE_v19.md §3`. The Self-Portrait **best-fit** recommendation ranks these same personas against the user's answers (bridge map, cached).

---

## 4. Database schema

### Migrations applied (chronological — new since v21)

| Rev | Description | PR |
|---|---|---|
| 001–037 | See `PROJECT_STATE_v21.md §4` / earlier for full history | — |
| **038** | **`counterview_turns` table** (bounded user rebuttal exchange; `sequence`, `persona_slug`, `user_text`, `persona_response`, `status ∈ {generated,empty,suppressed}`; UNIQUE `(counterview_id, sequence)`) | **#376** |
| **039** | **`user_preferences.portrait_cache` JSONB NULL** (Self-Portrait summary/best-fit cache) | **#395** |
| **040** | **`self_comparison_saves` table** (soft-delete `deleted_at`; unique `(user_id, self_comparison_id)`; feeds Reflections) | **#442** |
| **041** | **`counterviews.still_stands` TEXT NULL** ("what still stands" closing line) | **#443** |
| **042** | **`council_sessions.synthesis_structured` JSONB NULL** (real_question / tension / verdict / next_move) | **#444** |

**alembic_version = `042_council_synthesis_json`** (chain …037 → 038 → 039 → 040 → 041 → 042). All revision ids ≤ 32 chars; filenames equal revision ids (per C-04).

### Live database state (verify on Render deploy)

```
alembic_version:           042_council_synthesis_json  (Render auto-runs alembic on deploy; confirm 038–042 applied)
counterview_turns:         live (038); status ∈ {generated,empty,suppressed}; UNIQUE (counterview_id, sequence)
counterviews:              still_stands (041)  [+ 032 core]
user_preferences:          profile JSONB (037; now also holds Self-Portrait "answers") + portrait_cache JSONB (039)
self_comparison_saves:     live (040); soft-delete deleted_at
council_sessions:          synthesis_structured JSONB (042); flat synthesis TEXT retained
personas count:            11 (all active, WebP portraits)
source_chunks:             2476 across 7 personas (Orwell copyright-excluded; Musashi deferred → 0 chunks each)
```

### RLS state

**RLS DISABLED on all public tables.** Unchanged.

---

## 5. Backend endpoints

All v21 endpoints apply (see `PROJECT_STATE_v21.md §5`). **New / changed since v21:**

| Method · Path | Router | Notes |
|---|---|---|
| `GET /preferences/self-portrait` | `preferences.py` | **NEW (#388).** Visible questions (tier-filtered, free 15) + stored answers + `is_pro` + `locked_count`. No 404 for fresh users. |
| `GET /preferences/self-portrait/portrait` | `preferences.py` | **NEW (#395/#396).** Breadth gate: `forming` (own-answer observations) / `ready` (cached Sonnet summary + best-fit). Never returns a count/%. Best-effort — always 200. |
| `PATCH /preferences/self-portrait` | `preferences.py` | **NEW (#387).** Persist answers into `profile["answers"]`; enqueues memory seed + YvY reinject. |
| `POST /counterview/{id}/respond` | `counterview.py` | **NEW (#376).** Bounded user rebuttal (`MAX_REBUTTALS=3`; 409 on cap); current speaker replies ≤18 words. Returns `turns[]` + `rebuttals_remaining`. |
| `POST` · `DELETE /self-comparison/{id}/save` | `self_comparison.py` | **NEW (#442).** Save/soft-delete the YvY "sentence you owe yourself" → Reflections feed. |
| `POST /council` | `council.py` | **CHANGED (#386/#444):** essence brief from chat; response now carries `synthesis_structured` (real_question/tension/verdict/next_move) alongside flat `synthesis`. |

---

## 6–18.

Sections 6 (send-message), 7 (Council — now decision-architecture synthesis), 8–18 — **unchanged from v19–v21 except as noted in Part A.** See `PROJECT_STATE_v21.md` / `_v20.md`.

### 14. Session metrics — v22 (2026-06-26→2026-07-09)

| Metric | Value |
|---|---|
| PRs merged | #376–#447 (#375 was the v21 doc PR) |
| Migrations deployed | 038 counterview_turns, 039 portrait_cache, 040 self_comparison_saves, 041 counterview_still_stands, 042 council_synthesis_json |
| New services | `services/self_portrait.py`, `self_portrait_prompts.py`, `self_portrait_summary.py` |
| New screens | `/app/self-portrait` (quiz + portrait), `/app/discuss`, `/app/explore/conversations`, `/app/explore/reflections`, `/app/explore/memory` |
| Key features | Self-Portrait arc (quiz → forming/ready portrait → radar/map → share card → best-fit-to-chat); Counterview rebuttal turns + still-stands; Explore guides; Council decision architecture; dilemma/belief insight doorways + Home room-noticed; Home image tiles; letters/YvY continuity beats |

### 17. Key file paths — new/updated in v22

**Backend:**
- `apps/api/services/self_portrait.py` — NEW: `visible_questions`, breadth gate, forming/ready, cache read/write.
- `apps/api/services/self_portrait_prompts.py` / `self_portrait_summary.py` — NEW: Sonnet summary + best-fit.
- `apps/api/routers/preferences.py` — self-portrait GET/GET-portrait/PATCH endpoints.
- `apps/api/data/question_bank.json` — 360 questions / 12 categories.
- `apps/api/services/counterview_service.py` + `routers/counterview.py` — `respond_to_rebuttal`, `MAX_REBUTTALS`, `still_stands`.
- `apps/api/services/council_service.py` + `council_prompts.py` + `routers/council.py` — essence brief + `synthesis_structured`.
- `apps/api/services/memory_service.py` + `routers/self_comparison.py` + `services/reflections_feed_service.py` — dilemma/belief signals; YvY sentence-owed save/feed.
- `apps/api/workers/arq_worker.py` — self-portrait seed + YvY reinject; letter takeaway/continuity/avoidance-line.
- `apps/api/db/migrations/versions/038_*`…`042_*`.

**Frontend:**
- `apps/web/app/app/(tabs)/self-portrait/page.tsx` — quiz + forming/ready portrait + radar/map + share.
- `apps/web/components/self-portrait/PortraitRadar.tsx` / `PortraitMap.tsx` / `Artwork.tsx` — NEW viz.
- `apps/web/lib/portraitShareCard.ts` / `selfPortrait*.ts` — NEW share card + observation/summary/caption libs.
- `apps/web/app/app/counterview/page.tsx` — rebuttal exchange + still-stands.
- `apps/web/app/app/explore/{conversations,reflections,memory}/page.tsx` — NEW guides.
- `apps/web/app/app/(tabs)/explore/page.tsx` — index rewrite + pushable heroes.
- `apps/web/app/app/(tabs)/today/page.tsx` + `app/app/discuss/page.tsx` + `lib/useTopicConversation.ts` — Home image tiles + Discuss route.
- `apps/web/components/today/RoomNoticedCard.tsx` + `lib/useInsightDoors.ts` + `components/chat/InsightCard.tsx` — insight doorways.
- `apps/web/components/reflections/YvYSentenceCard.tsx` — YvY sentence-owed feed card.
- `apps/web/components/layout/BottomTabBar.tsx` — Self Portrait tab (replaced Library in bar).
- `apps/web/components/layout/LettersBootstrap.tsx` + `components/today/SundayLetterCard.tsx` + `app/app/letters/*` — letter star / takeaway / continuity / prefill.
- `apps/web/lib/store.ts` — `plan` as real state (persist-freeze fix).
- `apps/web/lib/api.ts` — self-portrait, counterview respond, council synthesis, YvY save clients.

---

## 19. Open / Closed items

### Open items (P0 launch blockers) — carried from v20/v21

Unchanged set: **PR3a memory bugs** (some addressed by #435 conv/[id] resilience — verify), OPS-001 (ote.gr re-sync), source_chunks re-ingest (TD-22), post-Oregon smoke test, TD-10 auth race, mobile nav smoke test, cold beta, consolidated polish PR, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, `PHENOMENOLOGY_BRIDGE_ENABLED` confirmation, RLS, UAT. See `PROJECT_STATE_v21.md §19`.

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. (Carried — still open.)
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### Corrections applied this rotation (docs-vs-reality)

- ✅ **Letter to Future Self delivery is LIVE — the v21 "ARQ delivery not wired / still open" item was FALSE and is REMOVED.** Delivery ships via **APScheduler**, not ARQ: `send_pending_future_self_emails` at **`apps/api/workers/cron.py:133–204`** (`AsyncIOScheduler`, `IntervalTrigger(minutes=5)`) delivers `ScheduledEmail` rows where `scheduled_for <= now() AND status='pending'`, per-row try/except, via `send_email`. The v21 doc's literal "ARQ not wired" was technically true but misleading — it missed that delivery runs on a different mechanism. **Gated on `API_BASE_URL`/asset base being set** (same operational dependency as weekly/season email).

### New OPEN items logged this rotation

- [ ] **`rituals.ts:42` stale copy (OPEN — founder call).** The `'future-self'` ritual body reads *"It isn't sent anywhere; the room keeps it as your stated direction."* This is the future-self **direction declaration** (feeds Sunday/monthly readings), which genuinely is not emailed — BUT the same-named **scheduled "Letter to Future Self"** (`ScheduledEmail`, `routers/scheduled_emails.py`) DOES email the user via the live cron above. The copy is arguably correct for the declaration yet misleading given the emailing feature exists. **Decide:** reword the copy, or leave (two distinct features sharing a name). Not asserted as a confirmed bug — flagged for judgment.
- [ ] **`insights.source_count` — populated by one generator, null by the other (BY DESIGN — confirm intended).** NOT "never populated" as first suspected: `memory_service.py:363,421` (`detect_recurrence`) sets `source_count = len(distinct prior conversations)+1`. The newer dilemma/belief **signal** path (`memory_service.py:181–187`, #438) deliberately sets `source_count=None` (documented "not a cross-conversation recurrence"). The provenance line renders only when `source_count >= 2`, so signal-path insights simply omit it. **Confirm this split is intended** (recurrence carries provenance; signals don't) — no code change unless the product wants signals to carry a count.

### Carried tech debt / parked

- [ ] **TD-37 — dormant brevity post-check** (carried, `PROJECT_STATE_v21.md §19`). **Wire or retire post-first-paying-user.**
- [ ] Carried parked items: Home tiles → custom images (**partially addressed** — Home now uses image-card tiles, #378; verify this closes it), `/app/profile` Explore entry point, insight-seeding from letter write-back (OUT of v1), letter write-back fed-forward truncation, adaptive-length/go-deeper threshold tuning, Counterview voice/threshold tuning.
- [ ] **Self-Portrait tuning (NEW):** breadth-gate thresholds, `PORTRAIT_REGEN_DELTA=8`, `FREE_QUESTION_LIMIT=15`, best-fit bridge-map weights — launch defaults; tune on cold-beta volume.

### Revenue blockers (P0 before first paying user) — carried

- [ ] **Stripe renewal webhook (live)**; **`ENVIRONMENT=production`** on Render API; **`API_BASE_URL`** set (else weekly/season **and future-self** emails suppressed by design); **Live Stripe keys + live price IDs** (TD-28).

### Closed / superseded this rotation

- [x] **CORRECTED** — **Letter to Future Self ARQ delivery** open item removed (delivery live via APScheduler; see corrections above).

---

## 20. Pre-Launch Blockers

> These gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [x] ~~`BETA_GRANT_PRO_TO_ALL`~~ — 🟢 OFF (2026-06-03)
- [x] ~~TD-11 tier resolution~~ — 🟢 COMPLETE (#203)
- [x] ~~End-to-end Stripe sandbox test~~ — 🟢 COMPLETE
- [ ] **Another-mind feature gate (post-cold-beta).**
- [ ] **Systemic frontend `plan` reliability bug** — #383 addressed one persist-freeze cause; verify before paid launch.
- [ ] **Live Stripe wiring (TD-28)** — live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` + `API_BASE_URL`.

---

**End of PROJECT_STATE v22.** Authoritative as of 2026-07-09 (Self-Portrait arc · Counterview rebuttal turns · Explore guides · Council decision architecture · insight doorways · Home image tiles · corrections). Supersedes `PROJECT_STATE_v21.md` (preserved as historical reference). Where this file conflicts with v21, v22 wins.
