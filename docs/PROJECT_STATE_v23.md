# PHILOSOPHER — Project State v23

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v23 = v22 baseline (2026-07-09, captured through PR #447 / `aa3ecafd`) + 2026-07-09→2026-07-12 delta (#448–#491).** The dominant arc is the **Quotes system ("The Wise Room" authenticated-quote corpus)**, built end-to-end across ~28 PRs (data layer → 5th bottom tab + screen → interactive discuss/story layer → Pro themed/persona-ranked suggestion + Home nudge → share PNG → save → Reflections feed), plus the **Future-Self prediction loop** (prediction-on-write / review-on-open + in-app arrived-letter screen), **Counterview share-title + collapsed history**, **insight seen-state** (Home star + Insights-visit clearing), **Self-Portrait polish**, and a **prompt/persona-voice** pass (tiered emotional-acknowledgment layer, cross-turn ADVANCEMENT discipline, ~1.65× deep-mode reflective ceilings). Migrations **043–049**.
>
> **Migration head moved 042 → 049.**
>
> **v22 = v21 baseline + #376–#447:** the **Self-Portrait** feature end-to-end (quiz → forming/ready portrait → radar + territorial map → shareable card → best-fit-to-chat), Counterview user-rebuttal turns + still-stands, Explore guides, Council decision-architecture, dilemma/belief insight doorways + Home room-noticed, Home image tiles, letters/YvY beats. Migrations 038–042. Full detail in `PROJECT_STATE_v22.md`.
>
> **Generated:** 2026-07-12 (v23 rotation) · **Last updated:** 2026-07-12 (Quotes / Wise Room corpus · Future-Self prediction loop · Counterview title · insight seen-state · persona-voice pass · corrections; current main `8a79ca3c`)

> **v23 conflict resolution rule:** Where v23 conflicts with v22 or earlier, v23 wins. **Production reality always wins over docs.**

> **⚠️ PROVENANCE — read this before trusting Part A. Three-way split by PR range:**
> - **#469–#491 — session-reviewed (2026-07-12 session).** Reviewed in-session with full diffs. Highest confidence.
> - **#459–#468 — session-reviewed (prior founder+Claude working sessions).** Reviewed with full diffs + byte-verification in earlier sessions, not the 2026-07-12 one. High confidence.
> - **#449–#458 — code-derived.** Reconstructed by reading merged code at `8a79ca3c`, not session-reviewed. Re-read the source before building on it.
> - **#448 — the v22 doc-rotation PR itself** (docs only; no product surface).

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive; do not write to it. All Render services must point to Oregon.**

---

## Part A — v23 delta (#449–#491)

> Built between the v22 doc cut (#447/#448) and this rotation. Provenance per PR range above: **#459–#491 session-reviewed** (full diffs); **#449–#458 code-derived** (reconstructed from merged code at `8a79ca3c`).

### A1. Quotes — "The Wise Room" corpus (the dominant new feature, ~28 PRs, #459–#487)

A curated corpus of **authenticated, source-located** philosopher quotes surfaced as full-bleed portrait cards. Free users browse; the personalised suggestion + nudge + in-card discussion is the Pro payoff.

- **Data layer (#459, #464, #487):** `quotes` table (migration **045**) — `persona_slug`, `text_en`, `text_original` (native-language phrase, nullable), `source_locator`, `translation_note`, `confidence`, `context`, `discuss_count`, `story_count`, `is_active`, `created_at`. Themes added as `themes TEXT[] NOT NULL` + GIN index (migration **046**, #464). Corpus **expanded 88 → 198** (migration **049**, #487 — rewrote all 88 existing contexts + inserted 110 new quotes). Seed + data: `apps/api/data/quotes_seed.json`, `apps/api/db/seed_quotes.py`, and the frozen migration payload `apps/api/db/migrations/data/quotes_049_data.json` (per C-01, self-contained).
- **Tab + screen (#460, #461, #469, #470):** a **5th bottom tab — Quotes** (Quote icon, `/app/quotes`), inserted 4th, before Account (see CORR-01). Screen `apps/web/app/app/(tabs)/quotes/page.tsx` — full-bleed portrait cards in a **peek carousel** with gentle auto-advance, no-repeat rotation, read-only cards, and a detail sheet ("The story"). #469 fixed tab order (Quotes 4th) + Home seal / insights thumbnail.
- **Interactive layer (#462, #463, #484):** atomic `discuss_count` / `story_count` increment endpoints; in-card **Discuss** (prefills a conversation with the quote, `lib/quotePrefill.ts`), **The story** expansion, per-card analytics, and a **persona-locked paywall** (discussing a quote opens a conversation with that quote's persona — gated for locked personas). Larger story text (#484).
- **Suggestion + nudge — the Pro payoff (#465, #466, #467, #468):** `GET /quotes/suggested` — themed, **persona-ranked**, **Pro-gated** (returns `[]` for free users). Ranking prefers a **live signal theme** captured on the insight in the **last 14 days** (`insights.theme`, migration **047**, #467; ranker `services/quote_suggest.py`), falling back to preference-derived themes. Home **"A line for you" nudge card** (`QuoteNudgeCard`) — Pro, **daily-capped** (client-side `lib/quoteNudgeFrequency.ts`: at most one nudge/day/device), with a Discuss action and seen-state (`lib/quoteNudgeSeen.ts`).
- **Share (#471, #472, #473, #474, #480, #481, #482, #483):** `POST /share/quote` (`routers/share.py`) renders a **1080×1350 QR-stamped PNG** (`generate_quote_share_image`, `services/image_service.py`; portrait-background grade constants `QUOTE_GRADE_COLOR/CONTRAST/BRIGHTNESS`). Share button + `SharePreviewModal` quote variant (#472); `source_short` (35-char, word-boundary) on cards + PNG (#473) with a tappable full-source popover (#474, full source in the story); the **native phrase lives only in the story, not the card** (#480); **full-bleed carousel-style A1 share card** (#481); filled-bronze quote actions + bronze account frames (#482, `style`); share preview **mirrors the full-bleed sent card** (#483).
- **Save → Reflections (#475, #476):** `saved_quotes` table (migration **048**) — `user_id`/`quote_id` FKs `ON DELETE CASCADE`, soft-delete `deleted_at`, `UNIQUE (user_id, quote_id)`, partial index `WHERE deleted_at IS NULL`. `POST` / `DELETE /quotes/{id}/save` + `GET /quotes/saved` (returns saved quote ids). Saved quotes join the unified Reflections feed as **`SavedQuoteCard`** (`services/reflections_feed_service.py:_quotes`, active saves newest-first).

### A2. Future-Self — prediction loop close (#449, #450)

Extends the (already-live) scheduled Letter-to-Future-Self with a written **prediction** and a **review** beat that lands in Reflections.

- **Schema (migration 043, #450):** `scheduled_emails` gains `prediction TEXT`, `review_text TEXT`, `review_at TIMESTAMPTZ` — the user's stated prediction at write-time and their review when the letter arrives. All nullable no-ops for existing rows.
- **In-app arrived-letter screen (#449):** `apps/web/app/app/scheduled-letters/[id]/page.tsx` — the arrived letter is now readable in-app (reached from the email link too); `routers/scheduled_emails.py` + `services/template_service.py` + `workers/cron.py` carry the prediction/review surface.
- **Review → Reflections (#450):** reviewing the prediction on open writes the review back into the Reflections surface.

### A3. Counterview — share title + collapsed history (#453, #477)

- **`counterviews.title` (migration 044, #453):** a "terrain-of-the-belief" heading for the Counterview share card. Nullable; old rows render as before.
- **Collapsed past list (#477):** the Counterview past-list collapses to 3 with a "show earlier" expander.

### A4. Insights — theme capture + client seen-state (#454, #467, #490)

- **Signal theme (migration 047, #467):** `insights.theme TEXT NULL` — an optional life-theme captured at signal-write time, consumed by the quote-nudge ranker (A1).
- **Home seen-state (#454, #490):** "The room noticed" now shows **only unseen** insights (client-side seen state). A **tile star** on Home fires for unseen insights (or a waiting Sunday/season letter), and visiting **Insights clears the seen set** (#490, `BottomTabBar.tsx` Home star wiring + Insights-visit clearing).

### A5. Self-Portrait — polish (#455, #478, #479)

- **Entry (#455):** succinct entry copy, no artwork overlap.
- **Share card (#478):** personalises the share-card title with the user's first name.
- **Map (#479):** dropped the X marker; larger, warmer territory labels.

### A6. Prompt / persona voice (#457, #485, #486, #488, #491)

- **Tiered emotional-acknowledgment layer (#488):** a new **EMOTIONAL WEIGHT** block in `system_base.jinja2`, driven by a persona `emotional_acknowledgment` config (`personas/_models.py`, `_base.py`; per-persona configs). Three tiers — `plain` / `present` / `warm` — plus an optional in-voice calibration line. Character-safe (each persona keeps its own register). **Inserted between PERSONA and CONVERSATIONAL MOVES** (see CORR-02).
- **Cross-turn ADVANCEMENT discipline (#491):** a new **ADVANCEMENT (cross-turn discipline)** block — 4 numbered rules forcing the conversation forward (never re-deliver a settled interpretation, build on affirmation, treat user-repetition as a stuck signal, open new ground rather than restate). **Inserted between CONVERSATIONAL MOVES and VOICE CALIBRATION** (see CORR-02). Also adds a deep-mode **new-layers** rule.
- **Deep-mode reflective ceilings (#486):** raised per-persona `reflective_reply_max_words` ~**1.65×** across all 11 personas (the go-deeper "reflective" band, `conversation_service.py`), with an extra allowance for the warm trio.
- **YvY brevity band (#457):** a brevity band on the two-selves reply.
- **Reflection skip-profile (#485):** the reflection flow skips the profile step once it has been answered; first-run is unchanged.

### A7. Tab bar — liquid-glass lens + 5th tab (#458, #460)

- **Liquid-glass active-tab lens (#458):** `BottomTabBar.tsx` gains a spring-animated frosted "lens" that slides under the active tab and magnifies its glyph (decorative; the color active-state remains the a11y source of truth).
- **5th tab + lens 20% (#460):** adding the Quotes tab took the bar to 5 tabs; the lens width dropped to `calc(20% - 3px)` and the Portrait label shortened (see CORR-01).

### A8. Auth + assets (#489, #451, #452, #456)

- **Expired-session redirect (#489):** `apps/web/middleware.ts` — expired sessions redirect to **`/auth`**, not the nonexistent `/login`.
- **Assets (#451, #452, #456):** transparent insight-seal medallion (#451, landed as two commits under one PR#), transparent Sunday-letter envelope + `contain` thumbnails (#452), WebP re-encode + Home LCP-priority image (#456).

---

## Changelog v22 → v23 (PR history, newest first)

| PR | SHA | Description |
|---|---|---|
| #491 | 8a79ca3c | feat(prompts): cross-turn ADVANCEMENT discipline + deep-mode new-layers rule |
| #490 | 13bf5b11 | feat(insights): tile star on Home + seen-clearing on Insights visit |
| #489 | 485f4285 | fix(auth): redirect expired sessions to /auth, not nonexistent /login |
| #488 | 56fd25e2 | feat(personas): tiered emotional-acknowledgment layer, character-safe |
| #487 | e7bed095 | feat(quotes): migration 049 — rewrite 88 contexts + add 110 quotes (88→198) |
| #486 | 3a850160 | feat(deep-mode): raise reflective ceilings ~1.65x, warm trio extra |
| #485 | 8b5175de | feat(reflection): skip profile step once answered; first-run unchanged |
| #484 | 3c6eccad | feat(quotes): larger story text for readability |
| #483 | 1fbdfe41 | fix(quotes): share preview mirrors the full-bleed sent card |
| #482 | 90ba7254 | style(quotes,account): filled-bronze quote actions + bronze account frames |
| #481 | e5508462 | feat(quotes): full-bleed carousel-style quote share card (A1) |
| #480 | c92880ea | feat(quotes): native phrase lives only in the story, not the card |
| #479 | 3fdaaa95 | polish(portrait-map): drop X marker, larger + warmer labels |
| #478 | e9b44519 | feat(portrait): personalize share card title with user first name |
| #477 | af621f83 | feat(counterview): collapse past list to 3 + show-earlier expander |
| #476 | 5d8050f7 | feat(quotes): save toggle + SavedQuoteCard in Reflections feed |
| #475 | de9ca965 | feat(quotes): saved_quotes table (048) + save/unsave/saved endpoints + reflections-feed |
| #474 | baf0f7af | feat(quotes): short source on cards + tappable full-source popover, full source in story |
| #473 | a42fa01e | feat(quotes): source_short (35-char, word-boundary) for cards + share PNG |
| #472 | 8c21481f | feat(quotes): share button + SharePreviewModal quote variant |
| #471 | ced7541a | feat(quotes): quote share PNG renderer + /share/quote (QR-stamped) |
| #470 | e1c4869c | feat(quotes): peek carousel, gentle auto-advance, no-repeat rotation, read-only cards, detail sheet |
| #469 | ebfea197 | fix: tab order (quotes 4th), another-mind revert error, Home seal + insights thumbnail |
| #468 | df0641d7 | feat(quotes): /suggested ranks live signal theme first (3a, 14-day window) |
| #467 | fea4996d | feat(insights): capture optional signal theme (047) for quote-nudge 3a |
| #466 | bdd2d6ae | feat(quotes): A-line-for-you nudge card — Pro, daily-capped, Discuss |
| #465 | 96644de6 | feat(quotes): GET /quotes/suggested — themed, persona-ranked, Pro-gated |
| #464 | f2fefeeb | feat(quotes): themes column (046) + themed seed |
| #463 | 6839e895 | feat(quotes): interactive layer — Discuss prefill, The story, analytics, persona-locked paywall |
| #462 | 93d92bec | feat(quotes): atomic discuss/story increment endpoints |
| #461 | 07e06a77 | feat(quotes): screen — full-bleed portrait cards, shuffle carousel |
| #460 | fc6966af | feat(quotes): 5th tab — add Quotes, shorten Portrait label, lens 20% |
| #459 | 9a3658d5 | feat(quotes): data layer — quotes table (045), verbatim seed, GET /quotes |
| #458 | 8d79c6e2 | feat(tabbar): liquid-glass active-tab lens with icon magnify |
| #457 | 65b05490 | fix(yvy): brevity band on the two selves |
| #456 | b12d2e2e | perf(assets): webp re-encode + home LCP priority |
| #455 | 81f5cd72 | fix(self-portrait): succinct entry copy, no artwork overlap |
| #454 | 409b0847 | feat(home): room-noticed shows only unseen insights (client-side seen state) |
| #453 | c535076d | feat(counterview): share title (migration 044) |
| #452 | c6092eb9 | fix(assets): transparent Sunday letter envelope + contain thumbs |
| #451 | e3034f8a / fe685987 | fix(assets): transparent insight seal medallion (two commits, one PR#) |
| #450 | fb5040a0 | feat(future-self): prediction on write + review on open → Reflections (migration 043) |
| #449 | f6f5e058 | feat(future-self): in-app arrived-letter screen + email link |
| #448 | a53a9e7f | docs: v22 rotation (docs only — the v22 doc cut) |

Earlier PR history (v21 → v22): see `PROJECT_STATE_v22.md`.

---

## Earlier session deltas (v16 → v22)

Carried forward by reference (additive convention):
- **v22** (#376–#447, Self-Portrait arc + Counterview turns + Explore guides + Council decision architecture + insight doorways + Home image tiles, migrations 038–042) — `PROJECT_STATE_v22.md`.
- **v21** (#339–#374, migrations 032–037) — `PROJECT_STATE_v21.md`.
- **v20 / v19 / v18 and earlier** — `PROJECT_STATE_v20.md` / `_v19.md` / `_v18.md`.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

Unchanged from v19–v22. (Next.js 14 / FastAPI / Postgres 17 Supabase Oregon / Redis+ARQ / **APScheduler in-process for cron** / Anthropic Claude / OpenAI embeddings / OTP+JWT / Stripe sandbox / Resend / Pillow share cards — **now including the quote share PNG (`image_service.generate_quote_share_image`, 1080×1350 QR-stamped)** / client-side canvas for the portrait share card.)

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-07-12** — Quotes / Wise Room corpus (#459–#487), Future-Self prediction loop (#449/#450), Counterview title + collapse (#453/#477), insight seen-state (#454/#490), Self-Portrait polish (#455/#478/#479), persona-voice pass (#457/#485/#486/#488/#491), tab-bar liquid-glass + 5th tab (#458/#460), auth redirect (#489), assets (#451/#452/#456). Current main: `8a79ca3c`. Prior deploy 2026-07-09 — #447 (`aa3ecafd`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3–5 fresh users still pending)

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; PR1 #77). Live wiring pending (TD-28).
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false`. Tier enforcement live via `get_user_tier`.
- **Rituals:** **Mirror ✅** · **Council ✅** (decision-architecture synthesis, v22) · **You vs You ✅** (sentence-owed save → Reflections, v22; **+ brevity band on the two selves, v23 #457**) · **Weekly Reading / Sunday Letter ✅** · **Counterview ✅** (bounded user rebuttal turns + still-stands, v22; **+ share title (044) + collapsed history, v23 #453/#477**) · **Self-Portrait ✅** (v22; **+ entry/share/map polish, v23 #455/#478/#479**) · **Letter to Future Self ✅ delivery LIVE** (APScheduler cron; **+ prediction-on-write / review-on-open loop, v23 #449/#450, migration 043**) — **no remaining unbuilt rituals.**
- **Quotes / "The Wise Room":** **LIVE (v23)** — 198-quote authenticated corpus (12-theme tagged); full-bleed portrait-card carousel screen; interactive discuss/story layer (persona-locked paywall); Pro themed + persona-ranked `GET /quotes/suggested` (14-day live signal-theme window) + Home "A line for you" nudge (daily-capped); QR-stamped share PNG; save → Reflections feed. New **Quotes** 5th bottom tab.
- **Insight engine:** LIVE — recurrence + shift + dilemma/belief signal detection; **v23: optional `theme` capture (047) for quote suggestion + Home seen-state (#454/#490).**
- **Reflections:** Unified feed — saved lines + Mirror/Council/Counterview verdicts + `kind="insight"` mirrors + YvY sentence-owed + **saved corpus quotes (v23, #475/#476, `SavedQuoteCard`).**
- **Share:** v3 / Council / Letter / Season / Counterview 4:5 / Self-Portrait card / **Quote card (1080×1350 QR-stamped PNG, v23).**

---

## 3. Personas registered

Unchanged — **11 personas** (Free: Marcus Aurelius, Socrates, Lao Tzu; Pro: de Beauvoir, Epictetus, Freud, Jung, Wilde, Machiavelli, Orwell, Musashi). Council roster fixed (Machiavelli, Epictetus, Freud, de Beauvoir). Counterview pair fixed (Musashi + Machiavelli). See `PROJECT_STATE_v19.md §3`. **v23 persona-config changes are additive fields, not new personas:** each persona gains an `emotional_acknowledgment` tier (#488) and a raised `reflective_reply_max_words` ceiling (#486). The Quotes corpus and Self-Portrait best-fit both range over these same 11 personas.

---

## 4. Database schema

### Migrations applied (chronological — new since v22)

| Rev | Description | PR |
|---|---|---|
| 001–042 | See `PROJECT_STATE_v22.md §4` / earlier for full history | — |
| **043** | **`scheduled_emails` +`prediction` TEXT / +`review_text` TEXT / +`review_at` TIMESTAMPTZ** (Future-Self prediction/review loop) | **#450** |
| **044** | **`counterviews.title` TEXT NULL** (terrain-of-the-belief share-card heading) | **#453** |
| **045** | **`quotes` table** (`persona_slug`, `text_en`, `text_original`, `source_locator`, `translation_note`, `confidence`, `context`, `discuss_count`, `story_count`, `is_active`, `created_at`) | **#459** |
| **046** | **`quotes.themes` TEXT[] NOT NULL** + GIN `idx_quotes_themes` | **#464** |
| **047** | **`insights.theme` TEXT NULL** (optional life-theme for quote-nudge ranking) | **#467** |
| **048** | **`saved_quotes` table** (`user_id`/`quote_id` FKs ON DELETE CASCADE; soft-delete `deleted_at`; UNIQUE `(user_id, quote_id)`; partial idx WHERE `deleted_at IS NULL`) | **#475** |
| **049** | **quotes corpus expansion** (data migration: rewrite 88 contexts + insert 110 quotes, 88 → 198; frozen payload `db/migrations/data/quotes_049_data.json`) | **#487** |

**alembic_version = `049_quotes_expand`** (chain …042 → 043 → 044 → 045 → 046 → 047 → 048 → 049). All revision ids ≤ 32 chars; filenames equal revision ids (per C-04, verified this rotation).

### Live database state (verify on Render deploy)

```
alembic_version:           049_quotes_expand  (Render auto-runs alembic on deploy; confirm 043–049 applied)
quotes:                    live (045); themes TEXT[] (046); 198 rows after 049 corpus expansion
saved_quotes:              live (048); soft-delete deleted_at; UNIQUE (user_id, quote_id)
insights:                  theme TEXT (047)  [+ source_count, prior columns]
counterviews:              title (044)  [+ still_stands 041, 032 core]
scheduled_emails:          prediction / review_text / review_at (043)
council_sessions:          synthesis_structured JSONB (042); flat synthesis TEXT retained
user_preferences:          profile JSONB (037) + portrait_cache JSONB (039)
personas count:            11 (all active, WebP portraits)
source_chunks:             2476 across 7 personas (Orwell copyright-excluded; Musashi deferred → 0 chunks each)
```

Note: the `quotes` corpus is a **separate, authenticated-verbatim quote store** and is unrelated to `source_chunks` (the RAG retrieval corpus). Quotes are seeded/migrated, not embedded.

### RLS state

**RLS DISABLED on all public tables.** Unchanged.

---

## 5. Backend endpoints

All v22 endpoints apply (see `PROJECT_STATE_v22.md §5`). **New / changed since v22:**

| Method · Path | Router | Notes |
|---|---|---|
| `GET /quotes` | `quotes.py` | **NEW (#459).** The active corpus as `QuoteOut[]` (verbatim `text_en`, `text_original`, `source_locator`, `themes`, counts). |
| `GET /quotes/suggested` | `quotes.py` | **NEW (#465/#468).** Themed, persona-ranked, **Pro-gated** (`[]` for free). Prefers a live `insights.theme` from the **last 14 days**; else preference-derived themes. Registered before `/{quote_id}` so `suggested` is never captured. |
| `GET /quotes/saved` | `quotes.py` | **NEW (#475).** Ids of the user's active saved quotes. |
| `POST /quotes/{id}/discuss` | `quotes.py` | **NEW (#462).** Atomic `discuss_count` increment (204). |
| `POST /quotes/{id}/story` | `quotes.py` | **NEW (#462).** Atomic `story_count` increment (204). |
| `POST` · `DELETE /quotes/{id}/save` | `quotes.py` | **NEW (#475).** Save / soft-delete a corpus quote → Reflections feed. |
| `POST /share/quote` | `share.py` | **NEW (#471).** Renders a 1080×1350 QR-stamped share PNG for a corpus quote. |
| `GET` (scheduled-letter arrived view) | `scheduled_emails.py` | **CHANGED (#449/#450).** Carries `prediction` / `review_text` / `review_at` (043) for the in-app arrived-letter screen + review-back. |

---

## 6–18.

Sections 6 (send-message), 7 (Council), 8–18 — **unchanged from v19–v22 except as noted in Part A.** The system prompt template (`prompts/system_base.jinja2`) changed in v23 — see CORR-02 for the current block order. See `PROJECT_STATE_v22.md` / earlier.

### 14. Session metrics — v23 (2026-07-09→2026-07-12)

| Metric | Value |
|---|---|
| PRs merged | #449–#491 (#448 was the v22 doc PR) |
| Migrations deployed | 043 future_self_prediction, 044 counterview_title, 045 quotes, 046 quotes_themes, 047 insight_theme, 048 saved_quotes, 049 quotes_expand |
| New services | `services/quote_suggest.py`; `image_service.generate_quote_share_image`; `reflections_feed_service._quotes` |
| New screens | `/app/quotes` (Wise Room carousel + detail sheet); `/app/scheduled-letters/[id]` (Future-Self arrived-letter view) |
| Key features | Quotes / Wise Room corpus (data → tab → interactive → Pro suggestion + nudge → share → save → Reflections); Future-Self prediction loop; Counterview title + collapsed history; insight seen-state; persona-voice pass (emotional-acknowledgment layer, ADVANCEMENT block, deep-mode ceilings) |

### 17. Key file paths — new/updated in v23

**Backend:**
- `apps/api/routers/quotes.py` — `GET /quotes`, `/quotes/suggested`, `/quotes/saved`, `POST /{id}/discuss|story|save`, `DELETE /{id}/save`.
- `apps/api/services/quote_suggest.py` — themed + persona-ranked suggestion (14-day signal-theme window).
- `apps/api/services/image_service.py` — `generate_quote_share_image` + `QUOTE_GRADE_*` grade constants; `routers/share.py:POST /quote`.
- `apps/api/services/reflections_feed_service.py` — `_quotes` (saved corpus quotes into the feed).
- `apps/api/data/quotes_seed.json` / `apps/api/db/seed_quotes.py` / `apps/api/db/migrations/data/quotes_049_data.json` — corpus seed + frozen 049 payload.
- `apps/api/prompts/system_base.jinja2` — EMOTIONAL WEIGHT block (#488) + ADVANCEMENT block (#491); see CORR-02.
- `apps/api/personas/_models.py` / `_base.py` / `<persona>.py` — `emotional_acknowledgment` tier (#488) + raised `reflective_reply_max_words` (#486).
- `apps/api/services/conversation_service.py` — deep-mode reflective ceiling (~1.65×) + new-layers directive.
- `apps/api/routers/scheduled_emails.py` + `services/template_service.py` + `workers/cron.py` — Future-Self prediction/review surface.
- `apps/api/db/migrations/versions/043_*`…`049_*`.

**Frontend:**
- `apps/web/app/app/(tabs)/quotes/page.tsx` — Wise Room carousel + detail sheet.
- `apps/web/components/quotes/QuoteCard.tsx` — full-bleed portrait quote card.
- `apps/web/lib/quotePrefill.ts` / `quoteNudgeFrequency.ts` / `quoteNudgeSeen.ts` — Discuss prefill; daily-cap throttle; nudge seen-state.
- `apps/web/components/layout/BottomTabBar.tsx` — 5th Quotes tab, liquid-glass lens (20%), shortened Portrait label, Home seen-star wiring.
- `apps/web/app/app/scheduled-letters/page.tsx` + `[id]/page.tsx` — Future-Self arrived-letter screen.
- `apps/web/middleware.ts` — expired-session redirect to `/auth` (#489).
- `apps/web/lib/api.ts` — quote list/suggested/save/share clients; scheduled-letter prediction/review fields.

---

## 19. Open / Closed items

### Open items (P0 launch blockers) — carried from v20/v21/v22

Unchanged set: **PR3a memory bugs** (verify #435 closed them), OPS-001 (ote.gr re-sync), source_chunks re-ingest (TD-22), post-Oregon smoke test, TD-10 auth race, mobile nav smoke test, cold beta, consolidated polish PR, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, `PHENOMENOLOGY_BRIDGE_ENABLED` confirmation, RLS, UAT. See `PROJECT_STATE_v22.md §19` / `_v21.md §19`.

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. (Carried — still open.)
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu — **now including the v23 emotional-acknowledgment tier + ADVANCEMENT block + raised deep-mode ceilings.**

### Corrections applied this rotation (docs-vs-reality)

- ✅ **CORR-01 — Bottom tab bar is now 5 tabs, not 4; "Self Portrait" is labelled "Portrait".** `PROJECT_STATE_v22.md §17` / `SCREENS_TRACKING_v10` state **Home · Explore · Self Portrait · Account** (4 tabs). The live `BottomTabBar.tsx` has **5 tabs: Home · Explore · Portrait · Quotes · Account** — the **Quotes** tab was added 4th (#460), the Self-Portrait tab **label** shortened to "Portrait" (#460, route `/app/self-portrait` unchanged), and the liquid-glass lens width is `calc(20% - 3px)` (was ~25% at 4 tabs; #458 introduced the lens, #460 set 20%).
- ✅ **CORR-02 — `system_base.jinja2` block order gained two blocks mid-template.** v22-era docs predate the EMOTIONAL WEIGHT (#488) and ADVANCEMENT (#491) blocks. The **current** order is: (1) intro/disclaimers → (2) current date → (3) **PERSONA** (fragment, TONE, STRUCTURE, REGISTER, CHALLENGE, QUESTIONING, DO NOT USE) → (4) **EMOTIONAL WEIGHT** [NEW #488] → (5) CONVERSATIONAL MOVES → (6) **ADVANCEMENT (cross-turn discipline)** [NEW #491] → (7) VOICE CALIBRATION → (8) PHENOMENOLOGY BRIDGE → (9) profile → (10) memories → (11) GROUNDING PASSAGES → (12) HARD RULES. Any instruction that inserts into this template MUST be written against the live file, never from recalled ordering.

### New OPEN items logged this rotation

- [ ] **Quote corpus provenance discipline (confirm).** The `quotes` table stores **verbatim, source-located** text with a `confidence` field and `translation_note`/`text_original` for non-English originals. This is a hard-rules-adjacent area (the persona prompt forbids fabricated quotes). **Confirm** the corpus verification process (who authenticates `source_locator` + `confidence`) is documented before public launch, since these render as attributed verbatim quotes on shareable cards.
- [ ] **Greek/CJK original phrase omitted from the quote share card (font gap).** Non-Latin `text_original` values are omitted from the share PNG by design pending a bundled Greek/CJK-capable font (see IMPLEMENTATION_BACKLOG_v23 P2). Same class of gap as the quote-card font-coverage debt.

### Carried tech debt / parked

- [ ] **TD-37 — dormant brevity post-check** (carried). **Wire or retire post-first-paying-user.**
- [ ] **TD-38 — `rituals.ts` future-self copy** (founder call: reword vs leave). Carried from v22.
- [ ] **TD-39 — `insights.source_count` recurrence-vs-signal split** (confirm intended). Carried from v22.
- [ ] Carried parked items: `/app/profile` Explore entry point, insight-seeding from letter write-back (OUT of v1), letter write-back fed-forward truncation, adaptive-length/go-deeper threshold tuning, Counterview voice/threshold tuning, Self-Portrait tuning (breadth gate / regen delta / free-question count / best-fit weights).
- [ ] **Quotes tuning (NEW):** 14-day signal-theme window, quote-nudge daily cap (1/day/device), persona-ranking weights, `QUOTE_GRADE_*` share-card grade constants — launch defaults; tune on cold-beta volume + a real-device share.
- [ ] **Retrieval dedup (P2, conditional — NEW):** `retrieval_ids` persist per message but `retrieve()` never consults them; same-topic turns re-serve identical chunks. **Open ONLY if the Dimitris repetition retest shows the ADVANCEMENT block (#491) is insufficient.** See IMPLEMENTATION_BACKLOG_v23.

### Revenue blockers (P0 before first paying user) — carried

- [ ] **Stripe renewal webhook (live)**; **`ENVIRONMENT=production`** on Render API; **`API_BASE_URL`** set (else weekly/season **and future-self** emails suppressed by design); **Live Stripe keys + live price IDs** (TD-28).

### Closed / superseded this rotation

- [x] **Quotes / "The Wise Room" corpus** — shipped end-to-end (#459–#487). No longer a backlog concept; now a live feature with a tuning tail.
- [x] **Future-Self prediction loop** — shipped (#449/#450); the delivery correction from v22 (CORR-01 there) stands.

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

**End of PROJECT_STATE v23.** Authoritative as of 2026-07-12 (Quotes / Wise Room corpus · Future-Self prediction loop · Counterview title · insight seen-state · persona-voice pass · corrections). Supersedes `PROJECT_STATE_v22.md` (preserved as historical reference). Where this file conflicts with v22, v23 wins.
