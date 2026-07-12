# HANDOFF BRIEF v23 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-07-12
**Prior version:** `docs/HANDOFF_BRIEF_v22.md` (2026-07-09)
**Generated:** 2026-07-12 (v23 rotation)

**Block trigger for v23 rotation:** A large feature arc landed since the v22 doc (which stopped at PR #447). The **Quotes system ("The Wise Room" authenticated-quote corpus)** was built end-to-end across ~28 PRs (#459–#487) — data layer → 5th bottom tab + screen → interactive discuss/story layer → Pro themed/persona-ranked suggestion + Home nudge → QR-stamped share PNG → save → Reflections feed. Alongside it: the **Future-Self prediction loop** (#449/#450), **Counterview share-title + collapsed history** (#453/#477), **insight seen-state** (#454/#490), **Self-Portrait polish** (#455/#478/#479), a **prompt/persona-voice pass** (tiered emotional-acknowledgment layer #488, cross-turn ADVANCEMENT block #491, ~1.65× deep-mode reflective ceilings #486), the **liquid-glass tab bar + 5th tab** (#458/#460), and the **auth redirect fix** (#489). Migration head moved 042 → 049. This rotation also **corrects** two doc-vs-reality errors (see PROVENANCE + Corrections).

> **⚠️ PROVENANCE — read this before trusting the summary below. Three-way split by PR range:**
> - **#469–#491 — session-reviewed (2026-07-12 session):** reviewed in-session with full diffs. Highest confidence.
> - **#459–#468 — session-reviewed (prior founder+Claude working sessions):** reviewed with full diffs + byte-verification in earlier sessions, not the 2026-07-12 one. High confidence.
> - **#449–#458 — code-derived:** reconstructed by reading merged code at `8a79ca3c`; re-read the source before building on it.
> - **#448 — the v22 doc-rotation PR itself** (docs only).

**v23 summary (2026-07-12):**
- **Quotes / "The Wise Room" ✅ LIVE (#459–#487)** — a curated, **authenticated, source-located** philosopher-quote corpus (198 quotes after the #487 expansion; 12-theme tagged). Free users browse full-bleed portrait cards in a **peek carousel** (gentle auto-advance, no-repeat rotation, detail sheet "The story"); the Pro payoff is **`GET /quotes/suggested`** (themed, **persona-ranked**, Pro-gated — prefers a live `insights.theme` from the **last 14 days**) surfaced as a Home **"A line for you" nudge** (daily-capped, one/day/device). In-card **Discuss** opens a conversation with that persona (persona-locked paywall); **The story** + atomic `discuss_count`/`story_count`. **Share:** `POST /share/quote` → 1080×1350 QR-stamped PNG (`generate_quote_share_image`), full-bleed A1 card, `source_short` (35-char word-boundary) + tappable full-source popover; native phrase lives only in the story, not the card. **Save:** `saved_quotes` (048) → `SavedQuoteCard` in the Reflections feed. New **Quotes** 5th bottom tab. Migrations 045/046/047/048/049; services `quote_suggest.py`, `image_service.generate_quote_share_image`, `reflections_feed_service._quotes`.
- **Future-Self prediction loop ✅ (#449/#450)** — `scheduled_emails` gains `prediction` / `review_text` / `review_at` (migration 043); the arrived letter is now readable **in-app** (`/app/scheduled-letters/[id]`, reached from the email link too); reviewing the prediction on open writes back to Reflections. (Delivery itself was already LIVE via APScheduler — see v22 CORR-01.)
- **Counterview title + collapse ✅ (#453/#477)** — `counterviews.title` (migration 044), a terrain-of-the-belief share-card heading; past-list collapses to 3 with a show-earlier expander.
- **Insight seen-state ✅ (#454/#490)** — "The room noticed" shows only **unseen** insights (client seen state); a Home **tile star** fires for unseen insights (or a waiting Sunday/season letter); visiting **Insights clears the seen set**. `insights.theme` (047) added for quote-nudge ranking.
- **Self-Portrait polish ✅ (#455/#478/#479)** — succinct entry copy (no artwork overlap); share-card title personalised with the user's first name; map drops the X marker for larger, warmer labels.
- **Persona-voice pass ✅ (#457/#485/#486/#488/#491)** — **EMOTIONAL WEIGHT** tiered acknowledgment block (plain/present/warm + optional in-voice calibration, `emotional_acknowledgment` config, #488); **ADVANCEMENT (cross-turn discipline)** block + deep-mode new-layers rule (#491); deep-mode `reflective_reply_max_words` raised ~1.65× across all 11 personas + warm-trio extra (#486); YvY two-selves brevity band (#457); reflection flow skips the profile step once answered (#485). **See CORR-02 for the current `system_base.jinja2` block order.**
- **Tab bar + auth + assets ✅** — liquid-glass active-tab lens + icon magnify (#458), 5th Quotes tab + lens 20% + shortened Portrait label (#460, **CORR-01**); expired sessions redirect to `/auth` not `/login` (#489, `middleware.ts`); transparent insight-seal/Sunday-envelope assets + WebP re-encode + Home LCP priority (#451/#452/#456).

**v22 summary (2026-07-09):** Self-Portrait arc, Counterview rebuttal turns + still-stands, Explore guides, Council decision-architecture, insight doorways + Home room-noticed, Home image tiles, letters/YvY beats; migrations 038–042. Full detail in `HANDOFF_BRIEF_v22.md`.

> **v23 conflict resolution rule:** Where v23 conflicts with v22 or earlier, v23 wins. **Production reality always wins over docs.**

---

## ✅ CORRECTIONS this rotation (docs were wrong — now fixed)

1. **CORR-01 — the bottom tab bar is 5 tabs, not 4; "Self Portrait" is now labelled "Portrait".** `HANDOFF_BRIEF_v22`, `PROJECT_STATE_v22 §17`, and `SCREENS_TRACKING_v10` say **Home · Explore · Self Portrait · Account** (4 tabs). The live `BottomTabBar.tsx` is **Home · Explore · Portrait · Quotes · Account** — the **Quotes** tab was added 4th (#460), the Self-Portrait tab **label** shortened to "Portrait" (#460, route `/app/self-portrait` unchanged), and the liquid-glass lens is `calc(20% - 3px)` wide (was ~25% at 4 tabs; lens introduced #458, set to 20% in #460).
2. **CORR-02 — `system_base.jinja2` gained two blocks mid-template.** v22-era docs predate the EMOTIONAL WEIGHT (#488) and ADVANCEMENT (#491) blocks. Current order: intro → date → **PERSONA** → **EMOTIONAL WEIGHT** [new] → CONVERSATIONAL MOVES → **ADVANCEMENT** [new] → VOICE CALIBRATION → PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES. **Any instruction inserting into this template must be written against the live file — see session lesson 13.42.**

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **.gitignore security debt (CRITICAL — do first).** `.env.local` NOT in `.gitignore`. Single dedicated commit; add `.env.local`, `.env*.local`.
2. **Migration naming (C-04).** Revision id ≤ 32 chars + filename == revision id. 043–049 all comply (verified this rotation).
3. **`API_BASE_URL` must be set on Render API** — else weekly/season **and future-self** letter emails are suppressed by design. `DEPLOY_NOTES.md`.
4. **PR3a memory bugs — still verify.** #435 (`conv/[id]` resilience) likely addresses the symptoms; confirm on smoke test before treating them as closed.
5. **Quote-corpus provenance (NEW).** Quotes render as attributed **verbatim** source-located text with a `confidence` field. Confirm the authentication process for `source_locator` + `confidence` is documented before public launch (hard-rules-adjacent).
6. **Greek/CJK original phrase omitted from the quote share card (NEW, font gap).** Non-Latin `text_original` is dropped from the share PNG pending a bundled Greek/CJK-capable font. Same class as the quote-card font-coverage debt.
7. **TD-38 `rituals.ts` future-self copy** / **TD-39 `insights.source_count` split** — carried from v22 (founder call / confirm-intended).

---

## Top of mind / Next (2026-07-12)

**Priority order:**

0. **Smoke-test the new surfaces (P-03 cadence):**
   - **Quotes / Wise Room:** the Quotes tab shows (5th, before Account); the carousel auto-advances without repeating; the detail sheet + "The story" open; **Discuss** opens a conversation prefilled with the quote (persona-locked paywall for locked personas); **share** exports a QR-stamped PNG that mirrors the on-screen full-bleed card; **save** toggles and the quote appears in Reflections; a **Pro** user sees a Home "A line for you" nudge at most once/day; a **free** user gets `[]` from `/quotes/suggested` and no nudge.
   - **Future-Self:** an arrived scheduled letter opens in-app at `/app/scheduled-letters/[id]`; the prediction shows and a review can be written back → Reflections.
   - **Counterview:** the share card shows a title; the past list collapses to 3 with a working expander.
   - **Insights:** "The room noticed" only shows unseen insights; the Home star fires for an unseen insight; visiting Insights clears it.
   - **Persona voice:** heavy-emotion input gets a one-line acknowledgment in the persona's tier (plain/present/warm) before method; a multi-turn thread visibly advances (no re-delivered interpretations); deep-mode replies use the wider reflective band without padding.
   - **Tab bar:** the liquid-glass lens slides under the active tab across all 5; reduced-motion disables the spring.
   - **Auth:** an expired session redirects to `/auth` (not a 404 `/login`).
1. **PR3a memory bugs — verify #435 closed them.**
2. **Dimitris repetition retest (Freud, deep mode, dream scenario)** — does the new ADVANCEMENT block (#491) stop the repetition? If not, open the conditional **retrieval-dedup** P2 item (retrieval_ids persist but retrieve() never consults them). See `IMPLEMENTATION_BACKLOG_v23`.
3. **Empathy mini-eval (6 personas, heavy input)** — confirm the emotional-acknowledgment tiers land in-character.
4. **A1 `QUOTE_GRADE_*` tuning on a real-device share** — confirm the portrait-background grade reads well on an actual phone.
5. **Cold beta with 3–5 fresh users** — once memory bugs confirmed.
6. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
7. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
8. **Fast-follows (post-first-paying-user):** Quotes tuning (14-day window, nudge cap, ranking weights, `QUOTE_GRADE_*`); TD-37 brevity post-check; TD-38 rituals copy; TD-39 source_count split; Self-Portrait tuning.

### Still-pending from prior sessions

- `.gitignore` security debt — fix before any code PR.
- Author smoke-test voice changes (6 personas) — **now including the v23 emotional-acknowledgment tier + ADVANCEMENT + raised deep-mode ceilings.**
- OTP-01 (ote.gr delivery failure) — investigate Render logs.

---

## Changelog v22 → v23 (PR history)

> Full per-PR table (SHA + description) in `PROJECT_STATE_v23.md §"Changelog v22 → v23"`. Range: **#449–#491** (#448 was the v22 doc PR). Highlights:

| PR | SHA | Description |
|---|---|---|
| #491 | 8a79ca3c | feat(prompts): cross-turn ADVANCEMENT discipline + deep-mode new-layers rule |
| #490 | 13bf5b11 | feat(insights): tile star on Home + seen-clearing on Insights visit |
| #489 | 485f4285 | fix(auth): redirect expired sessions to /auth |
| #488 | 56fd25e2 | feat(personas): tiered emotional-acknowledgment layer |
| #487 | e7bed095 | feat(quotes): migration 049 — corpus 88 → 198 |
| #486 | 3a850160 | feat(deep-mode): raise reflective ceilings ~1.65x |
| #481 | e5508462 | feat(quotes): full-bleed carousel-style quote share card (A1) |
| #475 | de9ca965 | feat(quotes): saved_quotes table (048) + save/unsave/saved + reflections-feed |
| #471 | ced7541a | feat(quotes): quote share PNG renderer + /share/quote (QR-stamped) |
| #468 | df0641d7 | feat(quotes): /suggested ranks live signal theme first (14-day window) |
| #467 | fea4996d | feat(insights): capture optional signal theme (047) |
| #465 | 96644de6 | feat(quotes): GET /quotes/suggested — themed, persona-ranked, Pro-gated |
| #464 | f2fefeeb | feat(quotes): themes column (046) + themed seed |
| #463 | 6839e895 | feat(quotes): interactive layer — Discuss, story, persona-locked paywall |
| #461 | 07e06a77 | feat(quotes): screen — full-bleed portrait cards, shuffle carousel |
| #460 | fc6966af | feat(quotes): 5th tab — add Quotes, shorten Portrait label, lens 20% |
| #459 | 9a3658d5 | feat(quotes): data layer — quotes table (045), verbatim seed, GET /quotes |
| #458 | 8d79c6e2 | feat(tabbar): liquid-glass active-tab lens with icon magnify |
| #453 | c535076d | feat(counterview): share title (migration 044) |
| #450 | fb5040a0 | feat(future-self): prediction + review loop (migration 043) |
| #449 | f6f5e058 | feat(future-self): in-app arrived-letter screen + email link |

Earlier PR history (v21 → v22): see `HANDOFF_BRIEF_v22.md §"Changelog"`.

---

## Earlier session deltas (v16 → v22)

Carried forward by reference. See `HANDOFF_BRIEF_v22.md` (v22 #376–#447) and `HANDOFF_BRIEF_v21.md` (v21 #339–#374).

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + C-01..C-04), current architecture (§2 — **+ quote share PNG via `image_service.generate_quote_share_image` (1080×1350 QR-stamped); `services/quote_suggest.py` themed ranker**), test infra (§3 — **+ `tests/services/test_quote_suggest.py`**), known limitations (§4 — **+ quote-corpus provenance, Greek/CJK share-card font gap; TD-37/38/39 still open**), next-session entry point (§5), PR history (§6 — above), env config (§7 — `API_BASE_URL` load-bearing for weekly/season **and future-self** email), key file paths (§8 — see `PROJECT_STATE_v23.md §17`), decision history (§9), migration plan (§11 — alembic head **`049_quotes_expand`**), deployment readiness (§12 — Quotes live; Future-Self prediction loop live; persona-voice pass live), session lessons (§13 — below), closing note (§14) — **unchanged from v22 except as noted.** See `HANDOFF_BRIEF_v22.md`.

### 13. Session lessons (v23 additions)

- **13.42 — Template insertion points are verified against the live file at brief-writing time, never recalled from session memory.** The ADVANCEMENT brief (#491) carried a stale EMOTIONAL-WEIGHT ordering (it assumed a block position that a prior PR had already shifted); the error was caught only by the implementer's pre-flight read of `system_base.jinja2`. `system_base.jinja2` is edited across many PRs (#488 and #491 both inserted mid-template this rotation), so its block order drifts faster than memory tracks. Rule (per `CLAUDE.md` Rule 3): before writing any "insert X after block Y" instruction for a multiply-edited template, re-read the live file and quote the actual adjacent blocks — never trust a remembered order.
- **13.43 — A verbatim-quote corpus is a separate store from the RAG corpus, and a different trust class.** The `quotes` table (authenticated, source-located, `confidence`-graded, rendered verbatim on shareable cards) is intentionally NOT `source_chunks` (embedded RAG passages the model paraphrases). Persona prompts forbid fabricated quotes and forbid reproducing RAG passages verbatim; the Quotes feature is the *only* place verbatim attributed text ships to users, so its provenance discipline lives with the data, not the model.
- **13.44 — Client-only seen/frequency state belongs in a named lib, mirrored across surfaces.** The quote nudge reused the exact `roomNoticedSeen.ts` pattern (`quoteNudgeSeen.ts` seen-state + `quoteNudgeFrequency.ts` daily cap). Per-device localStorage throttles keep the nudge from re-firing without a server round-trip or a schema column — right call for a cold-beta cosmetic cap; revisit if cross-device consistency ever matters.
- **13.45 — Additive nullable columns / new tables stay the cold-beta default.** 043 (nullable columns) / 044 (nullable column) / 045 + 048 (new tables) / 046 (NOT NULL with a server-default) / 047 (nullable column) / 049 (data-only) are all no-ops for existing rows — old scheduled_emails/counterviews/insights render exactly as before until the new path writes. Same shape as 038–042.

---

**End of HANDOFF_BRIEF v23.** Authoritative as of 2026-07-12 (Quotes / Wise Room corpus · Future-Self prediction loop · Counterview title · insight seen-state · persona-voice pass · corrections). Supersedes `HANDOFF_BRIEF_v22.md` (preserved as historical reference). Where this file conflicts with v22, v23 wins.
