# PHILOSOPHER — Project State v19

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v19 = v18 baseline (2026-06-15, captured through PR #313) + 2026-06-16 session delta.** This session shipped (docs-only reflection of code PRs #315–#316): **portrait assets standardized to WebP** (1024px/q82) across all personas in both stores, with **migration 026** repointing the 6 non-webp `portrait_url`s (#315); and **two new pro-tier personas — George Orwell + Miyamoto Musashi** — wired end-to-end (persona modules, brain YAML, matching affinities, RAG policy, **migration 027**), taking the roster from **9 → 11** (#316). See the v19 session delta below.
>
> **v18 = v17 baseline (2026-06-13, captured through PR #275) + 2026-06-13→06-15 session delta.** This session shipped: the **Sunday Letter / Weekly Reading** end-to-end (table 022; list/detail/**hard-delete**/**share** endpoints; reading-library search; next-Sunday card + returning-user archive link); **Reading "Revisit"** (`POST /conversations/reading-revisit` + `REVISIT_OPENING` + post-gen safety gate; revisit-mode `PersonaPickerSheet` + detail-page button); **Letter share** (wax-seal card `POST /weekly-letters/{id}/share` + `SharePreviewModal kind='letter'`); the **unified Reflections feed + Mirror saves** (P2-SMOKE-10/11 — now DONE; table 025); `formatItemDate`; Reflections client-side search; plus a polish/fixes batch (iOS share-sheet, chat-freeze, UI polish, council/guide styling).
>
> **Generated:** 2026-06-16 (v19 rotation) · **Last updated:** 2026-06-16 (session delta #315–#316; current main `0a42b0cb`)

> **v19 conflict resolution rule:** Where v19 conflicts with v18 or earlier, v19 wins. Production reality always wins over docs.

> **⚠️ Migration-log debt corrected in v18:** v17's schema table stopped at migration `021`, but migrations `022_create_weekly_letters` (06-04), `023_add_message_kind` (06-07) and `024_saved_line_conclusion_source` (06-09) had already landed on main before the v17 doc was written (#276, 06-13). v18 brings the head current to `025_create_mirror_saves`. See §4.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive — scheduled deletion ~2026-06-09; do not write to it. All Render services must point to Oregon.**

---

## 2026-06-16 Session Delta — Persona roster 9 → 11 (Orwell + Musashi) · WebP portrait standard

> Appended as v19. Where this conflicts with earlier sections, this section wins. **Current main SHA: `0a42b0cb` (PR #316).**

### Portrait assets standardized to WebP — SHIPPED (#315)

All persona portraits are now **WebP, 1024px, quality 82**. PR #315 delivered new oil-painting portraits and converted the remaining non-webp assets so the whole roster is uniform.

- **Both asset stores carry the `.webp` files and must stay in sync:** `apps/web/public/personas/<slug>.webp` (frontend) and `apps/api/static/personas/<slug>.webp` (API static).
- **Migration 026 (`026_personas_portrait_webp`)** repointed the **6** previously non-webp `portrait_url`s in the DB (carl_jung, lao_tzu, machiavelli, oscar_wilde were `.png`; marcus_aurelius, socrates were `.jpg`) to `/personas/<slug>.webp`. Epictetus, Freud, de Beauvoir were already `.webp` and were re-exported in place.
- The guide screen (`apps/web/app/app/guide/page.tsx`) image `src`s were updated to `.webp`.
- **Convention (now standing):** WebP is the portrait asset format standard (not PNG/JPG); any new persona portrait ships `.webp` to **both** stores. See `CLAUDE.md`.

### Two new pro-tier personas — George Orwell + Miyamoto Musashi — SHIPPED (#316)

The roster is now **11 personas** (was 9). Both new personas are **`tier=pro`, `is_active=true`**, wired end-to-end:

- **Persona modules:** `apps/api/personas/george_orwell.py`, `apps/api/personas/miyamoto_musashi.py` — `PersonaConfig` built from the v0.9.1 design YAML (character_anchors, register_range, behavioral_parameters, anti_flexing, forbidden_lexicon, response_length_words, safety, worldview verbatim from YAML; voice/system_fragment/calibration authored in the `niccolo_machiavelli.py` style). Registered in `PERSONA_REGISTRY` (`apps/api/personas/__init__.py`).
- **Brain YAML:** `apps/api/philosopher_brain/personas/orwell.yaml`, `musashi.yaml`.
- **Matching:** `services/matching_service.py` `PERSONA_AFFINITIES` weights added for both (all 12 themes + 4 needs). `EXCLUDED_SLUGS` unchanged (both are matchable). Smoke: decision+challenge surfaces Musashi; controversy/self-deception+challenge surfaces Orwell.
- **RAG / corpus policy:**
  - **`george_orwell` → added to `EXCLUDED_PERSONAS`** in `scripts/corpus_sources.py` (US copyright: major works + many essays remain under publication-based copyright up to ~95 yrs). **Voice-engineered only; zero source chunks.** Excluded set is now `{carl_jung, simone_de_beauvoir, george_orwell}`.
  - **`miyamoto_musashi` → NOT excluded**, but **absent from `CORPUS_SOURCES`** (his originals are public domain; deferred until a rights-clean English translation is sourced). **Zero chunks for now.**
  - `retrieval_sources = []` for both.
- **Migration 027 (`027_add_orwell_musashi`, down_revision `026_personas_portrait_webp`):** self-contained data migration — **no app-code import**; `config` jsonb is an **immutable inline literal snapshot** of each `PersonaConfig` (verified identical to `to_dict()` at authoring time, then frozen); `bio = about_en` verbatim from the design YAML; `portrait_url = /personas/<slug>.webp`; `is_active = true`; `tier = pro`. DOWN deletes the 2 rows by slug.

**Roster after v19 (11):**
- **Free (3):** Marcus Aurelius, Socrates, Lao Tzu
- **Pro (8):** Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli, **George Orwell**, **Miyamoto Musashi**

**Deferred / known:** Musashi RAG ingestion (pending a rights-clean public-domain translation); Council default-panel rotation for the new personas (optional product call — not done; Council roster unchanged: Machiavelli, Epictetus, Freud, de Beauvoir). The 9 pre-existing personas are otherwise untouched.

> **alembic head is now `027_add_orwell_musashi`** (chain: …`025_create_mirror_saves` → `026_personas_portrait_webp` → `027_add_orwell_musashi`). Migrations 026–027 are data/asset migrations, not schema changes.

---

## 2026-06-15 Session Delta — Sunday Letter end-to-end · Reading Revisit · Letter share · Reflections feed + Mirror saves

> Appended as v18. Where this conflicts with earlier sections, this section wins. **Current main SHA: `70059bc3` (PR #313).**

### Sunday Letter / Weekly Reading — SHIPPED (was placeholder-locked in v17 §9.7)

The Weekly Reading ritual is no longer a "Coming this season" placeholder. The full reader surface now ships:

- **`weekly_letters` table (migration 022, 2026-06-04).** `user_id` FK CASCADE, `voice_persona_id` FK NULL, `period_start/period_end`, `status ∈ {generated,empty,suppressed}`, `payload` JSONB (fields: `title`, `opening`, `references`, `pull_quote`, `forward_gesture`, `suggested_persona_slug`, `status`), `read_at`, `email_sent_at`, `created_at`. `UNIQUE(user_id, period_start)` + `ix_weekly_letters_user_id`.
- **Endpoints (`apps/api/routers/weekly_letters.py`, prefix `/weekly-letters`):**
  - `GET /weekly-letters` — list the user's letters.
  - `GET /weekly-letters/{id}` — single letter.
  - **`DELETE /weekly-letters/{id}` → 204 — HARD delete** (no soft-delete column on this table). Reading-library "delete" removes the row. (#308)
  - **`POST /weekly-letters/{id}/share`** — wax-seal share card PNG for the letter's `pull_quote`. Free tier: 3 per 90-day rolling window on the **shared** `share_screenshot:{user.id}` counter (same bucket as mirror/line/council shares); Pro/premium unlimited. (#312)
- **Interpretive prompt + per-persona cross-letter continuity** landed in #298 (`d5c49b1f`).
- **Frontend:** reading library `apps/web/app/app/letters/page.tsx` (list + **client-side search** + hard-delete); reading detail `apps/web/app/app/letters/[id]/page.tsx` (Revisit + Share buttons). Sunday-letter card on Today shows the **next-Sunday date**; returning users get an **archive link** to past letters. (#309)

### Reading "Revisit" — a persona's candid read of the weekly letter (#310, #311, #313)

- **`POST /conversations/reading-revisit` → 201** (`apps/api/routers/conversations.py`). Creates a conversation whose **first assistant message** is the chosen persona's sharp, candid read of the user, generated **non-stream** from the weekly letter.
- **`create_reading_revisit` (`conversation_service.py:274`):** loads the letter (must be `status='generated'` and owned by the user), access-gates the target persona, assembles the reading from payload fields **in order** (`title`, `opening`, `references`, `pull_quote`, `forward_gesture`, skipping empties), then **`build_system(persona)` FIRST + `"\n\n" + REVISIT_OPENING` appended** (the safety/HARD-RULES layer is preserved, never replaced). One `llm_client.complete(model=MODEL_PRO, max_tokens=1024)`; the synthetic user turn carrying the `<letter>…</letter>` is **not persisted**.
- **Revisit judges *on the reading*, not a free chat:** `REVISIT_OPENING` instructs the persona to deliver its own clear-eyed read ("name the pattern you see"), not summarise the letter, open on a position (not a question), and end with a single genuine invitation.
- **Revisit-mode `PersonaPickerSheet` + a Revisit button** on the reading detail page select the voice. (#311)

### Mirror saves + unified Reflections feed — P2-SMOKE-10/11 DONE (was "in progress" in v17)

- **`mirror_saves` table (migration 025, 2026-06-12)** — mirrors `council_saves` exactly: `user_id` FK CASCADE, `mirror_id` FK CASCADE, `saved_at`, `deleted_at`, `UNIQUE(user_id, mirror_id)` + `ix_mirror_saves_user`. Additive — no change to `saved_lines` or `mirrors`. (#277)
- **`GET /reflections/feed`** (`apps/api/routers/reflections.py` + `services/reflections_feed_service.py`) — unified feed of saved lines + Mirror/Council verdicts. Share-from-verdict cards + Council 4-persona thumbnail row + faded ritual-hero share backgrounds. (#279–#281)
- **Gravity-gated conclusions are now a savable unit:** `messages.message_kind` (migration 023, default `'standard'`); `saved_lines.source_type` CHECK extended to allow `'conclusion'` (migration 024). When a `message_kind='conclusion'` message is saved, the SavedLine is tagged `source_type='conclusion'`.

### Dates + search

- **`formatItemDate` (`apps/web/lib/formatItemDate.ts`, #306)** — relative time within 7 days, absolute date beyond. Consumed by `today/page.tsx`, `CouncilVerdictCard`, `MirrorVerdictCard`, `SavedLineCard`.
- **Reflections client-side search** over the unified feed (#307); **reading-library client-side search** (#308).

### Polish & fixes batch (summarized — full granularity in git log / HANDOFF §6)

- **iOS share-sheet reliability:** pre-generate image so the native share sheet opens for pro/premium (#295), retry pre-generation (#305), fall back to download on failure (#292), more prominent wordmark/date on cards (#301, #1cabf350).
- **Chat-freeze fix** (#283) + **UI-polish batch** (#282) — *note: these two were logged into the v11 docs by the anomalous PR #284, not v17; restated here for the correct v18 lineage.*
- **You vs You:** forming preview as 2–3 short bullets (#300); admin bypass for the forming gate, thresholds unchanged (#296).
- **Reflections styling:** bronze borders, bolder headers/inline dates, round council thumbnails, faded app-hero on chat-saved card, filled-primary Save CTA, source eyebrow titles (#289–#294, #297).
- **Council:** paper surface on persona responses for readability (#299).
- **Guide / onboarding:** "Explore The Wise Room" minds + rituals imagery (#304); onboarding adds dilemma/controversy/doubt/freedom themes + matching weights (#303).
- **Rituals:** throttle streaming auto-scroll 4→24 words (#302).
- **Today/sheet polish:** last-conversation title 20px/medium (#286); BottomSheet anchored to viewport bottom + cleared floating tab-bar footprint for the Letter submit button on iOS (#287, #288); reverted Sunday-card dismiss-X, enlarged modal close-× tap targets (#285).

### Key superseded facts (v18)

- **P2-SMOKE-10/11 (unified Reflections feed + Mirror saves)** — was "🟡 in progress, branch `feat/mirror-saves`, not yet built" → **🟢 DONE. `mirror_saves` (025) + `GET /reflections/feed` shipped (#277, #279–#281).**
- **Weekly Reading ritual** — was "🔴 placeholder-locked ('Coming this season')" → **🟢 reader surface SHIPPED: list/detail/hard-delete/share + Revisit. ARQ email delivery still not wired** (`email_sent_at` column exists, unused).
- **Migration head** — was `021_create_self_comparisons` → **`025_create_mirror_saves`** (022–025 logged in v18).
- **`saved_lines.source_type`** — was `{manual_save, kept_insight}` → **adds `conclusion`** (024).

---

## 2026-06-12 Session Delta — P0-SMOKE tab/sheet batch + P3-SMOKE-08 Today/guide consolidation

> Appended as v17. Where this conflicts with earlier sections, this section wins.

**Code merged to main (current main SHA: `57e1ef4d`):**

- **PR #273 (`d5b16ccb`) — bottom-anchored tab bar + sheet safe-area; svh `/1.15` double-compensation dropped. Closes P0-SMOKE-01 / 03a / 03b.**
  - Tab bar rebuilt as a bottom-anchored frosted pill, now a fixed floating element out of flow (`components/layout/BottomTabBar.tsx`); the `(tabs)` shell reserves its footprint via `paddingBottom: calc(4rem + env(safe-area-inset-bottom) + 12px + 8px)`.
  - `BottomSheet` now owns `env(safe-area-inset-bottom)` as the single source of safe-area truth for all sheets (`components/ui/BottomSheet.tsx`).
  - The manual `100svh / 1.15` divisor was removed from the `(tabs)` shell (`app/app/(tabs)/layout.tsx`), `BottomSheet`, and the Mirror host picker (`app/app/mirror/page.tsx`). Root-cause finding: modern engines already adjust `svh` viewport units under the global `body { zoom: 1.15 }`, so the manual `/1.15` was a **double-compensation** that pulled the bottom edge ~13% short. Full `100svh` now lands the bottom edge correctly. **This supersedes TD-30** (see backlog): the coupling premise was wrong — the divisors were not load-bearing and are now all removed while `zoom: 1.15` itself still ships.
  - Files: `(tabs)/layout.tsx`, `mirror/page.tsx`, `BottomTabBar.tsx`, `RitualScheduleSheet.tsx`, `BottomSheet.tsx`.
- **Conversation deletion → DONE.** (P0-SMOKE deletion item closed.)

- **P3-SMOKE-08 → CLOSED. Three phases:**
  - **PR-A (`bfcd4d3b` / #274, branch `feat/today-consolidated-card`):** `TodaysTopicCard` redesigned into the consolidated "What brings you here?" entry surface — eyebrow renamed from "What's on your mind?", multi-select theme pills (8 shared slugs) + "or describe in your own words" free-text divider. **"Initiate reflection"** (primary, disabled until a pill or text is present) writes the onboarding sessionStorage contract and routes to `/app/onboarding/need`; **"Quick start"** (outlined) preserves the prior topic → `PersonaPickerSheet` → chat behavior. `THEME_OPTIONS` extracted to `apps/web/lib/themes.ts` as the single source of truth (mirrors the backend Pydantic enum); `onboarding/themes/page.tsx` now imports it (import-only, no behavior change — **the route file still exists**). The Today → `/app/onboarding/themes` navigation was removed (that route is no longer reachable from Today).
  - **PR-B — NO-OP with finding.** The single matched-mind journey (need → top-1 most-suitable accessible mind, Mind-of-the-Day style, seeded chat, "See all minds") **was already shipped in PR #217 (`ca1fac53`).** The backlog's "B4 3-match screen" premise was **stale** — there is no 3-match screen to build. Recorded explicitly so future sessions do not re-plan against B4.
  - **PR-C (`57e1ef4d` / #275, branch `feat/wise-room-guide`):** new `/app/guide` "Living in the Wise Room" explainer screen. Today bottom button relabeled "Explore minds" → **"Living in the Wise Room"** (routes to `/app/guide`). Explore remains reachable via the Library tab and via the matches "See all minds" link.

- **P2-SMOKE-10 / 11 → IN PROGRESS.** Architecture approved: **Option B additive.** A new `mirror_saves` table mirroring `council_saves`; a unified Reflections feed endpoint; share cards with faded ritual hero backgrounds; the Council card gains a 4-persona thumbnail row. Additive only (no rewrite of existing save paths). Not yet built — branch `feat/mirror-saves` in flight.

**Netlify operational notes (record as facts, not state):**

- **Drawer disabled** on Netlify.
- **Preview password / SSO protection intentionally disabled** (so preview deploys are openly reachable for smoke testing).

**Key superseded facts (v17):**

- **Tab bar / bottom sheet positioning** — was `100svh/1.15`-compensated full-viewport overlays (P0-SMOKE-01/03a/03b open) → **CLOSED. PR #273: bottom-anchored floating pill + sheet-owned safe-area; all `/1.15` divisors removed (double-compensation finding).**
- **TodaysTopicCard "What's on your mind?"** → **REPLACED with consolidated "What brings you here?" card (PR #274): pills + free text, Initiate reflection → need flow, Quick start → picker.**
- **Backlog B4 "3-match screen"** — was assumed unbuilt → **STALE / NO-OP. Single matched-mind journey shipped in PR #217. Do not re-plan against B4.**
- **Today bottom button "Explore minds"** → **relabeled "Living in the Wise Room" → `/app/guide` (PR #275).**
- **TD-30 (`/1.15` coupling across three sites)** → **SUPERSEDED. Divisors were double-compensation, now all removed (PR #273); `body { zoom: 1.15 }` removal tracked as a separate post-cold-beta backlog item.**

---

## 2026-06-03 Session Delta — PR3a micro-polish + daily_questions

> Appended as v17. Where this conflicts with v16 or prior sections, this section wins.

**Code merged to main (current main SHA: `c50779b5`):**

- **PR #210 (squash `eda60f21`) — three production bug fixes:**
  - `apps/web/components/library/ConversationCard.tsx` — card now shows conversation title with `last_message_snippet` as fallback. Fixes BUG-013 and PR3a item #2: title no longer demoted to snippet-first rendering.
  - `apps/web/app/app/(tabs)/today/page.tsx` — first-day "Reflect" no longer hardcodes Marcus Aurelius; opens `PersonaPickerSheet` instead. Opening message skipped only when a topic already exists.
  - `apps/web/components/personas/PersonaPickerSheet.tsx` — cross-persona "Ask another mind" now starts the chat correctly: `onClose()` called before the async conversation create, so `history.back()` no longer reverts `router.push`. Fixes PR3a item A.

- **Rituals micro-polish (merged separately):**
  - `apps/web/app/app/(tabs)/rituals/page.tsx`:
    - You-vs-You card: `<Contrast size={40} strokeWidth={1.2} />` replaced with an inline half-sphere SVG (`<circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1.2" />` + `<path d="M20 1 A19 19 0 0 1 20 39 Z" fill="currentColor" />`). Closes PR3a item #5.
    - Letter-to-Future-Self card: outer `<div>` wrapper changed to `<button onClick={handleBeginLetter}>` making the whole card the tap target; inner "Begin" `<button>` and `<ChevronRight>` removed. Pro-gate and `RitualScheduleSheet` preserved unchanged. Closes PR3a item #8.
    - Import line: `ChevronRight` and `Contrast` removed from `lucide-react` import.

- **App icon — landed accidentally, removed via hotfix:**
  - `apps/web/public/personas/appbutton.png` (1122×1402 px, 8-bit RGB, ~2.1 MB) was copied to `apps/web/app/icon.png` and `apps/web/app/apple-icon.png` in the rituals PR. Both files landed on main (`c9bb3d39`) and were removed in a follow-up hotfix (`c50779b5`).
  - **DECISION: app-icon mark DEFERRED.** The Chesterfield armchair photo stays as brand/hero/OG image only. A purpose-built icon mark is required before wiring Next.js `icon.png` / `apple-icon.png` — design TBD. Closes PR3a item B as deferred (not done).

**Production database (Oregon `bvzeuwzqgnqcghvqghtb`) — data changes, no migrations:**

- **`daily_questions` table updated:** 30 philosophical prompts deactivated (`active=false`, rows preserved, reversible). 50 modern-phenomenology themes inserted (`display_order` 1000–1049, `active=true`). Topics include: loneliness, social-media relationships, doomscrolling, AI threats to work, and related phenomenology themes. Rotation endpoint `GET /api/v1/today/question` selects `WHERE active=true ORDER BY display_order`, picks entry by day-of-year index. Closes PR3a item #6.

- **`backfill-titles` endpoint executed:** `POST /api/v1/admin/backfill-titles` returned `{queued: 0}`. No title debt outstanding — all qualifying conversations (`message_count >= 6 AND title IS NULL`) had already been titled by the ARQ Haiku worker. No further backfill action needed.

**Operational notes (record as facts, not state):**

- **Oregon DB confirmed canonical:** `bvzeuwzqgnqcghvqghtb` (us-west-2) is the only live database. Ireland project `plecolxlzshkfvybszgs` (eu-west-1) = deprecated rollback buffer; scheduled deletion ~2026-06-09; never query.

- **Pro test account:** `nckoutras+pro1@gmail.com` granted Pro tier via `UPDATE subscriptions SET plan='pro', status='active'`. A free subscription row auto-creates at signup — grant is `UPDATE`, not `INSERT`.

- **OTP lockout root cause documented:** Upstash Redis key `otp_request:{email}` rate-limits OTP requests to 5/hour (`auth.py`). This is separate from the DB-side OTP attempt lockout (`OTP_MAX_ATTEMPTS=5`). Workaround for testing: use `+alias` email variants — each alias is a distinct rate-limit bucket.

**Key superseded facts (v17):**

- **BUG-013 — ConversationCard title never renders:** was `last_message_snippet ?? title` → **CLOSED. Fixed in PR #210: `title ?? last_message_snippet`. Title now renders first; snippet is the fallback.**
- **PR3a item A — Ask another mind chat stuck:** was unresolved → **CLOSED. Fixed in PR #210: `onClose()` called before async create in `PersonaPickerSheet.tsx`.**
- **PR3a item #5 — YvY icon unclear:** was `<Contrast>` (lucide) → **CLOSED. Replaced with inline half-sphere SVG (`currentColor`).**
- **PR3a item #8 — Letter card pushbutton:** was inner `<button>Begin</button>` inside `<div>` → **CLOSED. Whole-card `<button onClick={handleBeginLetter}>`.**
- **PR3a item #6 — phenomenology prompts:** was 30 philosophical prompts → **CLOSED. 50 modern-phenomenology themes active in `daily_questions`.**
- **PR3a item B — app icon:** was "in sweep" → **DEFERRED. Photo icon tried and removed. Icon mark design TBD.**
- **Backfill-titles:** was "not yet executed" → **DONE. Executed 2026-06-03; queued=0.**
- **PR3a sweep:** was "not started" → **PARTIALLY COMPLETE.** Remaining: memory bugs (fresh-chat missing opening message/thumbnail; home "Continuing" 404s).
- **`today/page.tsx` first-day picker:** was hardcoded Marcus Aurelius → **FIXED. Opens PersonaPickerSheet (PR #210).**

---

## v16 Session Deltas (2026-06-01 through 2026-06-03)

See `PROJECT_STATE_v16.md` for full v16 session detail: The Council (PRs #182–#186), You vs You (PRs #193–#202), Revenue chain + TD-11 + PR3a triage.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 async · asyncpg |
| Database | PostgreSQL 17 (Supabase). **Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2) — CONFIRMED LIVE.** Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy / inactive; scheduled deletion ~2026-06-09. |
| Queue/Cache | Redis (Upstash) + ARQ + APScheduler |
| LLM | Anthropic Claude — wired and live for chat + Council synthesis |
| Embeddings | OpenAI text-embedding-3-small (2476 chunks live across 7 personas) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage; Google OAuth dormant (PR4k) |
| Billing | Stripe (sandbox — checkout + portal + webhook live; PR1 #77) |
| Email | Resend (free tier, test sender — custom domain in progress) |
| Analytics | PostHog (configured, unused) |
| Image rendering | Pillow (PIL) — server-side PNG generation for share cards (reflections + council) |

### Hosting

Unchanged from v15. Netlify (canonical), Render (API + worker, paid tier), Supabase Oregon.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-06-15** — Sunday Letter end-to-end (#298, #308, #309, #312, #313), Reading Revisit (#310, #311), unified Reflections feed + Mirror saves (#277, #279–#281), `formatItemDate` (#306), Reflections search (#307), plus iOS-share / styling / guide polish batch. Current main: `70059bc3`. Prior deploy 2026-06-12 — PR #273/#274/#275 (`57e1ef4d`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3-5 fresh users still pending)

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v12.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v12.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

Real-time streaming architecture shipped (PR-A / Bug #4). See §6.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; €14.90/mo + €149/yr; PR1 #77)
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false` confirmed disabled on both API and worker (2026-06-03). Tier enforcement is live via `get_user_tier`.
- **Paywall system wired:** Yes
- **Google OAuth:** Dormant
- **Rituals tab:** Live (PR4o) — ritual cards shown; **Mirror ✅ SHIPPED** (PRs #166–#173); **Council ✅ SHIPPED** (PRs #182–#186); **You vs You ✅ SHIPPED** (PRs #193–#202); **Weekly Reading / Sunday Letter ✅ reader surface SHIPPED** (v18: table 022; list/detail/hard-delete/share + Revisit; ARQ email delivery still not wired); **Counterview** still placeholder-locked; Letter to Future Self is functional (ARQ delivery not yet wired). **Rituals micro-polish shipped 2026-06-03:** half-sphere SVG for YvY card; Letter card is whole-card tap.
- **Reflections:** Unified feed live (v18, #279–#281) — saved lines + Mirror/Council verdicts; **Mirror saves** via `mirror_saves` table (025); client-side search; share-from-verdict cards.
- **Share v3:** Live (PR4ag1); **Council share:** Live (C7c / #186)
- **Greeting personalization:** Live (PR-D #129)
- **Name capture prompt:** Live (PR-D2 #130)

---

## 3. Personas registered

**11 personas in production (v19; was 9). All have full Section 5.7 character config + bio + portrait (WebP).** Portrait config carried over from v12; roster expanded in v19 (#316).

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli, **George Orwell (v19, #316)**, **Miyamoto Musashi (v19, #316)**

**Council roster (fixed):** Machiavelli, Epictetus, Freud, de Beauvoir — all Pro-tier personas. (Unchanged in v19 — Orwell/Musashi not added to the default Council panel.)

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001–014 | See v12/v11/v9 for full history | Pre-v12 | — |
| **015** | **FK indexes: 20 btree indexes on FK columns across 10 tables** | **2026-05-26** | **L1 / #124** |
| **016** | **messages.persona_id nullable FK → personas.id + ix_messages_persona_id** | **2026-05-29** | **PR-B / 71ce6e3** |
| **017** | **mirrors table: uq_mirrors_user_period_kind UNIQUE(user_id, period_start, kind); kind ∈ {weekly,preview}; status ∈ {generated,empty,suppressed}; payload JSONB; ring_true fields** | **2026-06-01** | **Mirror / #168** |
| **018** | **users.mirror_host_slug VARCHAR(100) NULL** | **2026-06-01** | **Mirror / #171** |
| **019** | **council_cases + council_sessions + council_responses tables + indexes** | **2026-06-01** | **Council C5–C7b** |
| **020** | **council_saves (id UUID PK, user_id FK CASCADE, session_id FK CASCADE, saved_at, deleted_at NULL) + UNIQUE(user_id, session_id) + ix_council_saves_user** | **2026-06-01** | **Council C7b** |
| **021** | **self_comparisons (id UUID PK, user_id FK CASCADE, prompt TEXT NOT NULL, then/now window timestamps, payload JSONB, status, ring_true fields, created_at) + ix_self_comparisons_user** | **2026-06-02** | **YvY PR1 #193** |
| **022** | **weekly_letters (id UUID PK, user_id FK CASCADE, voice_persona_id FK NULL, period_start/period_end, status CHECK ∈ {generated,empty,suppressed}, payload JSONB, read_at, email_sent_at, created_at) + UNIQUE(user_id, period_start) + ix_weekly_letters_user_id** | **2026-06-04** | **Weekly Reading** |
| **023** | **messages.message_kind VARCHAR(20) NOT NULL DEFAULT 'standard' (no CHECK)** | **2026-06-07** | **Conclusions** |
| **024** | **saved_lines.source_type CHECK extended → {manual_save, kept_insight, conclusion}** | **2026-06-09** | **Conclusions** |
| **025** | **mirror_saves (id UUID PK, user_id FK CASCADE, mirror_id FK CASCADE, saved_at, deleted_at NULL) + UNIQUE(user_id, mirror_id) + ix_mirror_saves_user** | **2026-06-12** | **P2-SMOKE-10 / #277** |
| **026** | **personas portrait_url → WebP — data migration, no schema change. Repoints the 6 non-webp `portrait_url`s (4 `.png`, 2 `.jpg`) to `/personas/<slug>.webp`** | **2026-06-16** | **#315** |
| **027** | **add george_orwell + miyamoto_musashi — data migration, no schema change. Inserts 2 persona rows (tier=pro, is_active=true, config = immutable inline literal snapshot, bio = about_en verbatim, portrait_url = /personas/<slug>.webp); no app-code import** | **2026-06-16** | **#316** |

**alembic_version = `027_add_orwell_musashi`** (026–027 logged in v19; chain …025 → 026 → 027). 022–025 were logged in v18; v17's table had stopped at 021.

### Oregon region migration — CONFIRMED LIVE

**Live DB = Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` (eu-west-1) = legacy, inactive; scheduled deletion ~2026-06-09.**

### Live database state (2026-06-03)

```
alembic_version:        021_create_self_comparisons ✓
daily_questions:        50 active (display_order 1000–1049, phenomenology themes)
                        30 inactive (original philosophical prompts, active=false, reversible)
users count:            ~3-4 (founder + test accounts incl. nckoutras+pro1@gmail.com; no organic users)
personas count:         11 (v19, #316; all active, all with bio + WebP portrait + error_messages)
conversations:          87+ (testing adds more)
messages:               227+ (testing adds more)
source_chunks:          2476 chunks across 7 personas (unchanged by v19: Orwell is copyright-excluded → 0 chunks; Musashi deferred, not in CORPUS_SOURCES → 0 chunks)
mirrors:                rows from preview cron
council_cases:          table live (019)
council_sessions:       table live (019)
council_responses:      table live (019)
council_saves:          table live (020)
self_comparisons:       table live (021)
weekly_letters:         table live (022)
mirror_saves:           table live (025)
messages.message_kind:  column live (023; default 'standard')
saved_lines.source_type: {manual_save, kept_insight, conclusion} (024)
```

> **Note:** `alembic_version` is now `027_add_orwell_musashi` (v19; was `025_create_mirror_saves` in v18). Confirm the Oregon DB has applied 022–027 (Render auto-runs alembic on deploy; verify if in doubt). 026 and 027 are data/asset migrations (portrait_url repoint; 2 persona inserts) — no schema change.

### RLS state

**RLS DISABLED on all public tables.** Unchanged from v12.

---

## 5. Backend endpoints

All v16 endpoints apply. See `PROJECT_STATE_v16.md §5` for the full base list (Council, self-comparison, etc.). **New since v17:**

| Method · Path | Router | Notes |
|---|---|---|
| `GET /weekly-letters` | `weekly_letters.py` | List user's Sunday Letters |
| `GET /weekly-letters/{id}` | `weekly_letters.py` | Single letter |
| `DELETE /weekly-letters/{id}` → 204 | `weekly_letters.py` | **HARD delete** (no soft-delete column) |
| `POST /weekly-letters/{id}/share` | `weekly_letters.py` | Wax-seal share PNG; free = 3/90-day on shared `share_screenshot:{user.id}` counter |
| `POST /conversations/reading-revisit` → 201 | `conversations.py` | Persona's candid read of the letter; non-stream; post-gen safety gate |
| `GET /reflections/feed` | `reflections.py` | Unified feed: saved lines + Mirror/Council verdicts |
| Mirror/letter share endpoints | `share.py`, `mirrors.py` | Mirror-save + share-card surfaces (P2-SMOKE-10/11) |

---

## 6. Send-message architecture (PATH A — canonical)

Unchanged from v15. See v15 §6.

---

## 7. Council architecture

Unchanged from v16. See `PROJECT_STATE_v16.md §7`.

---

## 8. Persona error messages

All 9 pre-existing personas have `llm_unavailable` error messages in DB (unchanged from v12 §7). **v19 note (#316):** migration 027's `config` snapshot for Orwell + Musashi does **not** include an `error_messages` map, so for those two `get_error_voice` (`services/persona_voice.py`) falls back to the **generic** `_FALLBACKS["llm_unavailable"]` message rather than a persona-specific voice. Adding per-persona error voice for the new personas is a possible follow-up (not a blocker).

---

## 9. LLM provider validation

Unchanged from v12 §8. Sonnet 4.6 (24/24) and Haiku 4.5 (23/24) both pass quality bar.

---

## 10. Locked decisions

All 24 from v16 remain locked. No new locked decisions in v17 session.

---

## 11. Reconciliation history

Unchanged from v12. See v12/v11/v9 §10 for C-RECON-1 through C-RECON-8.

---

## 12. BETA bypass system

**`BETA_GRANT_PRO_TO_ALL` = OFF.** Confirmed disabled on both API and worker services (2026-06-03 revenue chain session). TD-11 canonical tier resolver shipped (#203). `get_user_tier` is the single source of truth; `get_current_user_plan` wraps it. Dual tier resolution tech debt resolved.

---

## 13. Frontend architecture

### Rituals page (`apps/web/app/app/(tabs)/rituals/page.tsx`) — updated v17

- You-vs-You card icon: inline half-sphere SVG (circle + right-semicircle path, `currentColor`). Replaces lucide `<Contrast>`.
- Letter-to-Future-Self card: whole card is `<button onClick={handleBeginLetter}>`. Inner "Begin" button and `<ChevronRight>` removed. Pro-gate and `RitualScheduleSheet` preserved.

### Council screen, SharePreviewModal, You vs You screen, Latency topology

Unchanged from v16. See `PROJECT_STATE_v16.md §13`.

---

## 14. Session metrics

### 2026-06-15 session — Sunday Letter · Revisit · Letter share · Reflections feed

| Metric | Value |
|---|---|
| PRs merged | #277–#313 (37 PRs; v17 doc had stopped at #275) |
| Production regressions | 0 (chat-freeze fix #283 + iOS share-sheet hardening shipped) |
| Migrations deployed | 022 weekly_letters, 023 message_kind, 024 saved_line conclusion, 025 mirror_saves (022–024 predate the window but were unlogged) |
| New tables | `weekly_letters` (022), `mirror_saves` (025) |
| New endpoints | `GET/DELETE/POST /weekly-letters/*`, `POST /conversations/reading-revisit`, `GET /reflections/feed` |
| New static asset | `apps/api/static/rituals/sundayletter.png` (letter share card) |
| Key features | Sunday Letter reader (search + hard-delete + share + Revisit), unified Reflections feed + Mirror saves, `formatItemDate` |

### 2026-06-03 session — PR3a micro-polish + daily_questions

| Metric | Value |
|---|---|
| PRs merged | PR #210 `eda60f21` (3 bug fixes); rituals polish `c9bb3d39` (rituals micro-polish + accidental icon); hotfix `c50779b5` (icon removal) |
| Production regressions | 0 |
| Migrations deployed | None |
| New tables | None |
| New endpoints | None |
| DB data changes | `daily_questions`: 50 phenomenology themes active (display_order 1000–1049); old 30 deactivated. `backfill-titles` executed; queued=0. |
| Files changed | `ConversationCard.tsx`, `today/page.tsx`, `PersonaPickerSheet.tsx` (PR #210); `rituals/page.tsx` (polish) |
| PR3a items closed | A (chat stuck), #2 (title), #5 (YvY icon), #6 (prompts), #8 (Letter tap). Item B (app icon) deferred. Memory bugs still pending. |

### 2026-06-03 session — Revenue chain + PR3a triage

See `PROJECT_STATE_v16.md §14`.

### Earlier sessions

See `PROJECT_STATE_v16.md §14` for Council, You vs You, Mirror, and earlier sessions.

---

## 15. Known bugs (active)

### Carried from v16

- **BUG-012** — Zustand hydration race (hard refresh / direct URL on protected routes flashes to /auth). TD-10. PR4ai deferred. Approach requires Netlify preview smoke test.

### Open issues carried from v16

- **OTP-01** — OTP delivery failure for ote.gr (Greek ISP). Workaround: use gmail. Not related to any PR code changes.
- **OPS-001** — `nkoutr@ote.gr` subscription `current_period_end = NULL` (pre-#205 row). Needs manual re-sync via Stripe dashboard or admin endpoint.

### Closed this session (v17)

- **BUG-013 — ConversationCard title never renders:** CLOSED 2026-06-03. Fixed in PR #210: `title ?? last_message_snippet`. Title now renders first; snippet is fallback.

### New tech debt logged (v17)

None this session.

---

## 16. Environment variables

Unchanged from v16. See `PROJECT_STATE_v16.md §16`.

---

## 17. Key file paths (production codebase)

All v16/v17 paths apply. New/updated in v18:

### Backend (apps/api/)

- `routers/weekly_letters.py` — NEW: list/get/`DELETE`/`POST {id}/share` for Sunday Letters.
- `routers/reflections.py` — `GET /reflections/feed` (unified feed); `services/reflections_feed_service.py` — NEW.
- `routers/conversations.py` — `POST /reading-revisit`; `services/conversation_service.py:create_reading_revisit` + `REVISIT_OPENING` constant.
- `services/image_service.py` — `generate_letter_share_image` (wax-seal card; uses `static/rituals/sundayletter.png`).
- `static/rituals/sundayletter.png` — NEW asset (required by letter share). Siblings: `boardroom.webp`, `mirror.webp`.
- `db/migrations/versions/022_create_weekly_letters.py`, `023_add_message_kind.py`, `024_saved_line_conclusion_source.py`, `025_create_mirror_saves.py`.

### Frontend (apps/web/)

- `lib/formatItemDate.ts` — NEW (#306): relative within 7 days, absolute beyond.
- `app/app/letters/page.tsx` — Sunday Letter reading library (list + search + hard-delete).
- `app/app/letters/[id]/page.tsx` — reading detail (Revisit + Share buttons).
- `components/share/SharePreviewModal.tsx` — UPDATED: `kind='letter'` (wax-seal preview).
- `components/personas/PersonaPickerSheet.tsx` — UPDATED: revisit mode.
- `components/reflections/{CouncilVerdictCard,MirrorVerdictCard,SavedLineCard}.tsx` — UPDATED: `formatItemDate`; unified-feed styling.
- `app/app/(tabs)/reflections/page.tsx` — UPDATED: unified feed + client-side search.
- `app/app/(tabs)/rituals/page.tsx` — UPDATED (v17): half-sphere SVG for YvY card; Letter card whole-card tap; `Contrast` + `ChevronRight` removed from imports.
- `app/app/(tabs)/today/page.tsx` — UPDATED (PR #210): first-day Reflect opens PersonaPickerSheet; opening message skipped only when topic exists.
- `components/library/ConversationCard.tsx` — UPDATED (PR #210): `title ?? last_message_snippet` (was `last_message_snippet ?? title`).
- `components/personas/PersonaPickerSheet.tsx` — UPDATED (PR #210): `onClose()` called before async create.

---

## 18. CLAUDE.md violations log

### Carried from v16

- 2026-05-17 — silent deletion of `apps/api/db/ingest_sources.py` (C3a)
- 2026-05-23 — PR4p bundled two logical changes (P-02 violation)
- 2026-05-23 — PR4q empty commit due to stale local main (P-01 violation)

### 2026-06-03 v17 session

No new CLAUDE.md violations.

---

## 19. Open / Closed items

### Open items (P0 launch blockers)

- [ ] **🟡 PR3a cold-beta sweep — partially complete.** Remaining: memory bugs (fresh-chat missing opening message/thumbnail; home "Continuing" 404s). All other PR3a items closed (see below).
- [ ] **OPS-001 — nkoutr@ote.gr current_period_end re-sync** — pre-#205 row has NULL current_period_end; needs manual re-sync.
- [ ] **source_chunks re-ingest** into Oregon via OpenAI embeddings script (TD-22); status unconfirmed post-switch
- [ ] **Post-Oregon smoke test** (login, chat, rituals/Mirror/Council, share, library, RAG retrieval)
- [ ] **bugfixes-3 — auth race fix** (TD-10; PR4ai deferred; preview smoke test required)
- [ ] **Mobile 12-point nav smoke test**
- [ ] **Cold beta with 3–5 fresh users**
- [ ] **Consolidated polish PR** (Block B visual closure)
- [ ] **Lawyer review** of Terms v1.1 / Privacy v1.1 / Disclaimer v1.0
- [ ] **DNS + Resend domain verification** for `thegreatminds.app`
- [ ] **GDPR / DPA infrastructure**
- [ ] **Founder runbooks**
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation**
- [ ] **RLS policies** as defense-in-depth
- [ ] **UAT** with 3–5 testers, ≥2/5 spontaneous "I'd pay"

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. Must fix before any further PR work. Branch: `chore/gitignore-env-local`.
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu (live since 2026-05-30, author-testing pending)
- [ ] **PR-D2 production smoke test** — PENDING (blocked by OTP delivery failure to ote.gr). Workaround: test with gmail address.

### Open items (P1 — Council fast-follows)

- [ ] **Per-verdict → reflections save** — needs investigation: `saved_lines` is message-centric; council responses live in `council_responses`, not `messages`. Design required before build.
- [ ] **Council share card redesign** — boardroom bg, date header, 4 member portrait thumbnails, centered synthesis text.
- [ ] **Reflection share card redesign** — center text, smaller/lower thumbnail.
- [ ] **compress mirror.png** — 2.3MB PNG → WebP.

### Open items (P1 — general)

- [ ] **OTP-01 — OTP delivery failure for ote.gr** — investigate Render logs
- [ ] **render.yaml sync:false** — add `sync: false` to ALL secrets
- [ ] **Upstash 80% quota alert** — set up in Upstash dashboard
- [ ] **Render env-var-change notification** — set up operational monitoring
- [ ] **Startup health check** — fail loudly on missing critical secrets
- [ ] **TD-05** — Wire generate_insight_task
- [ ] **TD-10** — Zustand hydration race fix (preview smoke test mandatory)
- [ ] **I1 Account hub build**
- [ ] **A6+A7 disclaimer endpoint integration tests**
- [ ] **App-icon mark design** — deferred from PR3a. Photo icon removed; need purpose-built icon mark before wiring `icon.png` / `apple-icon.png`.

### Open items (P2 — tech debt)

- [ ] **TD-12** — Soft-delete pattern for conversations
- [ ] **TD-13** — Modal abstraction (when 4th modal needed)
- [ ] **TD-17** — Weekly Reading full implementation (post cold-beta)
- [ ] **TD-21** — passive_deletes audit
- [ ] **branding** — "The Wise Room" vs "Great Minds" still unresolved across codebase (FROM_EMAIL, FRONTEND_URL, copy); separate thread in progress

### Closed items (2026-06-15) — Sunday Letter · Revisit · Letter share · Reflections feed

- [x] **CLOSED 2026-06-15** — **P2-SMOKE-10 / 11**: unified Reflections feed + Mirror saves. `mirror_saves` table (025) + `GET /reflections/feed` + share-from-verdict cards + Council 4-persona thumbnail row + hero-bg share cards (#277, #279–#281).
- [x] **CLOSED 2026-06-15** — **Weekly Reading / Sunday Letter reader surface**: `weekly_letters` (022); list/detail/**hard-delete**/**share** endpoints; reading-library search; next-Sunday card + returning-user archive link; interpretive prompt + cross-letter continuity (#298, #308, #309, #312, #313). (ARQ email delivery still open — see below.)
- [x] **CLOSED 2026-06-15** — **Reading Revisit**: `POST /conversations/reading-revisit` + `REVISIT_OPENING` + post-gen safety gate; revisit-mode `PersonaPickerSheet` + detail-page button (#310, #311).
- [x] **CLOSED 2026-06-15** — **`formatItemDate`** (#306) + **Reflections client-side search** (#307).
- [x] **CLOSED 2026-06-15** — **Gravity-gated conclusions savable**: `messages.message_kind` (023) + `saved_lines.source_type='conclusion'` (024).

### Newly opened (2026-06-15)

- [ ] **Weekly Reading ARQ email delivery** — `weekly_letters.email_sent_at` column exists but no ARQ send task is wired. Same gap as Letter-to-Future-Self delivery. P1.

### Closed items (2026-06-12) — P0-SMOKE tab/sheet batch + P3-SMOKE-08

- [x] **CLOSED 2026-06-12** — P0-SMOKE-01 / 03a / 03b: tab bar + bottom-sheet positioning. PR #273: bottom-anchored frosted pill, sheet-owned `env(safe-area-inset-bottom)`, all `100svh/1.15` divisors removed (double-compensation finding). Supersedes TD-30.
- [x] **CLOSED 2026-06-12** — Conversation deletion.
- [x] **CLOSED 2026-06-12** — P3-SMOKE-08 (all three phases): PR-A consolidated "What brings you here?" Today card + `THEME_OPTIONS` → `lib/themes.ts` (#274); PR-B NO-OP — matched-mind journey already shipped in #217, B4 3-match premise stale; PR-C "Living in the Wise Room" `/app/guide` + Today button rewire (#275).

### Closed items (2026-06-03) — PR3a micro-polish session

- [x] **CLOSED 2026-06-03** — PR3a item A: Ask another mind chat stuck. Fixed: `onClose()` before async create in `PersonaPickerSheet.tsx` (PR #210).
- [x] **CLOSED 2026-06-03** — PR3a item #2 / BUG-013: ConversationCard title. Fixed: `title ?? last_message_snippet` in `ConversationCard.tsx` (PR #210).
- [x] **CLOSED 2026-06-03** — Today first-day Reflect hardcoded Marcus. Fixed: opens `PersonaPickerSheet`; opening message skipped only when topic exists (PR #210).
- [x] **CLOSED 2026-06-03** — PR3a item #5: YvY ritual card icon. Replaced `<Contrast>` with inline half-sphere SVG.
- [x] **CLOSED 2026-06-03** — PR3a item #8: Letter to Future Self card. Whole-card `<button>` replacing inner Begin button.
- [x] **CLOSED 2026-06-03** — PR3a item #6: phenomenology prompts. 50 modern-phenomenology themes active in `daily_questions`; old 30 deactivated (reversible).
- [x] **CLOSED 2026-06-03** — Backfill-titles executed. `queued=0` — no title debt outstanding.

### Closed items (2026-06-03) — Revenue chain session

- [x] **CLOSED 2026-06-03** — TD-11 canonical tier resolver shipped (#203)
- [x] **CLOSED 2026-06-03** — BETA_GRANT_PRO_TO_ALL confirmed OFF on both API and worker
- [x] **CLOSED 2026-06-03** — Stripe webhook URL corrected; current_period_end fix (#205); account auth hydration fix (#207)
- [x] **CLOSED 2026-06-03** — Revenue chain verified end-to-end in TEST/sandbox

### Closed items (2026-06-02 and earlier)

See `PROJECT_STATE_v16.md §19` for full history.

---

## 20. Pre-Launch Blockers

> These items gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [x] ~~**`BETA_GRANT_PRO_TO_ALL`**~~ — 🟢 **CONFIRMED OFF** (2026-06-03)
- [x] ~~**TD-11 — Tier resolution unified refactor**~~ — 🟢 **COMPLETE** (#203, 2026-06-03)
- [x] ~~**End-to-end Stripe sandbox test**~~ — 🟢 **COMPLETE** (2026-06-03)
- [ ] **Another-mind feature gate (post-cold-beta)** — add a feature-level Pro gate before disabling BETA bypass for real paying users.
- [ ] **Systemic frontend `plan` reliability bug** — `plan` getter unreliable outside `(tabs)/layout.tsx`. Fix before paid launch.
- [ ] **Live Stripe wiring** — sandbox complete; live wiring requires: live Stripe keys + live price IDs + a separate live-mode webhook + `ENVIRONMENT=production` on Render API.

---

**End of PROJECT_STATE v18.** Authoritative as of 2026-06-15 (Sunday Letter / Revisit / Letter share / Reflections feed session). Supersedes `PROJECT_STATE_v17.md` (preserved as historical reference).
