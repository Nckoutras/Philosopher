# HANDOFF BRIEF v18 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-15
**Prior version:** `docs/HANDOFF_BRIEF_v17.md` (2026-06-13)
**Generated:** 2026-06-15 (v18 rotation)

**Block trigger for v18 rotation:** A full feature block landed since the v17 doc (which stopped at PR #275) — the Sunday Letter / Weekly Reading reader surface, Reading Revisit, Letter share, and the unified Reflections feed + Mirror saves. Migration head moved 021 → 025. State materially different from v17.

**v18 summary (2026-06-15):** Sunday Letter end-to-end ✅ (search + hard-delete + share + Revisit). Reading Revisit ✅ (`POST /conversations/reading-revisit`, post-gen safety gate). Letter share ✅ (wax-seal card, `SharePreviewModal kind='letter'`). P2-SMOKE-10/11 ✅ DONE (unified Reflections feed + `mirror_saves`). `formatItemDate` ✅. Reflections search ✅. Polish/iOS-share/chat-freeze batch ✅. Migrations 022–025 logged (022–024 predated the window but were unlogged in v17). Current main: `70059bc3`.

**2026-06-12 update:** P0-SMOKE-01/03a/03b ✅ CLOSED (PR #273 — bottom-anchored tab bar + sheet safe-area; `/1.15` double-compensation dropped; TD-30 superseded). Conversation deletion ✅ DONE. P3-SMOKE-08 ✅ CLOSED (PR-A #274; PR-B no-op vs #217; PR-C #275 `/app/guide`). TD-32 (zoom removal) logged.

**Status:**
- Block A ✅ FULLY CLOSED (5/5)
- Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending)
- Block C ✅ FULLY COMPLETE — real-time streaming added PR-A (#128)
- Stripe sandbox ✅ COMPLETE (PR1 #77, 2026-05-19)
- Paywall + BETA bypass ✅ COMPLETE (PR4j #100)
- Share v3 ✅ COMPLETE (PR4ag1 #122)
- Rituals tab + page ✅ COMPLETE (PR4o + PR4ah) — Mirror/Council live; Counterview/Weekly Reading placeholder-locked
- Greeting personalization ✅ COMPLETE (PR-D #129)
- Name capture prompt ✅ MERGED (PR-D2 #130) — smoke test partially blocked by OTP issue
- Bug #1 ✅ FIXED (#127 — BottomSheet history.back race)
- Bug #4 ✅ FIXED (PR-A #128 — real-time streaming)
- Typography PR-F ✅ COMPLETE (2026-05-29)
- C9 "Bring another mind" / PR-B ✅ COMPLETE (2026-05-29) — Pro-gated; cross-mind awareness shipped
- Voice overhaul ✅ COMPLETE (2026-05-30)
- **The Mirror ✅ COMPLETE (2026-06-01)** — PRs #166–#173; generator + cron + host picker + ring-true; migrations 017 + 018
- **The Council ✅ COMPLETE (2026-06-01)** — PRs #182–#186; 4 members; verdicts + synthesis SSE; save/unsave; share PNG; migrations 019 + 020; boardroom screen live
- **WiseMark ✅ SHIPPED (#191)** — standalone icon component
- **You vs You ✅ COMPLETE (2026-06-02)** — PRs #193–#202; migration 021; dual-self SSE; closing card + ring-true; weekly limits; usage meter
- **TD-11 ✅ DONE (#203, 2026-06-03)** — canonical tier resolver
- **BETA_GRANT_PRO_TO_ALL ✅ OFF (2026-06-03)**
- **Revenue chain ✅ CLOSED IN TEST/SANDBOX (2026-06-03)**
- **PR3a item A ✅ CLOSED (PR #210, 2026-06-03)** — Ask another mind chat stuck fixed
- **PR3a item #2 / BUG-013 ✅ CLOSED (PR #210, 2026-06-03)** — ConversationCard title fixed
- **Today first-day Reflect ✅ FIXED (PR #210, 2026-06-03)** — opens PersonaPickerSheet, no longer hardcodes Marcus
- **PR3a item #5 ✅ CLOSED (2026-06-03)** — YvY ritual card: half-sphere SVG replaces `<Contrast>`
- **PR3a item #8 ✅ CLOSED (2026-06-03)** — Letter card: whole-card tap target
- **PR3a item #6 ✅ CLOSED (2026-06-03)** — daily_questions: 50 phenomenology themes active
- **backfill-titles ✅ DONE (2026-06-03)** — executed; queued=0
- Oregon region migration ✅ CONFIRMED LIVE — bvzeuwzqgnqcghvqghtb (us-west-2)
- **Sunday Letter / Weekly Reading ✅ reader SHIPPED (2026-06-15)** — table 022; list/detail/hard-delete/share + search + Revisit; ARQ email delivery open (TD-33)
- **Reading Revisit ✅ SHIPPED (2026-06-15)** — `POST /conversations/reading-revisit`; post-gen safety gate; revisit-mode picker
- **Letter share ✅ SHIPPED (2026-06-15)** — wax-seal card `POST /weekly-letters/{id}/share`; needs `static/rituals/sundayletter.png`
- **Unified Reflections feed + Mirror saves ✅ DONE (2026-06-15)** — P2-SMOKE-10/11; `mirror_saves` 025; `GET /reflections/feed`

> **v18 conflict resolution rule:** Where v18 conflicts with v17 or earlier, v18 wins. Production reality always wins over docs.

---

## 2026-06-15 Session Delta — Sunday Letter · Reading Revisit · Letter share · Reflections feed

> Appended as v18. Where this conflicts with earlier sections, this section wins. **Current main SHA: `70059bc3` (PR #313).**

**Sunday Letter / Weekly Reading — reader surface shipped:**
- `weekly_letters` table (migration 022, 06-04): `payload` JSONB carries `title`/`opening`/`references`/`pull_quote`/`forward_gesture`/`suggested_persona_slug`/`status`; `UNIQUE(user_id, period_start)`.
- `apps/api/routers/weekly_letters.py` — `GET /weekly-letters`, `GET /weekly-letters/{id}`, **`DELETE /weekly-letters/{id}` → 204 (HARD delete — no soft-delete column)**, **`POST /weekly-letters/{id}/share`** (wax-seal PNG; free = 3/90-day on the shared `share_screenshot:{user.id}` counter).
- Interpretive prompt + per-persona cross-letter continuity (#298). Frontend: `app/app/letters/page.tsx` (library + client-side search + hard-delete), `app/app/letters/[id]/page.tsx` (Revisit + Share). Today Sunday-card → next-Sunday date + returning-user archive link (#309).
- **`apps/api/static/rituals/sundayletter.png` is a required asset** for the letter share card (`image_service.generate_letter_share_image`). Siblings: `boardroom.webp`, `mirror.webp`.

**Reading Revisit (#310, #311, #313):**
- `POST /conversations/reading-revisit` → 201. `conversation_service.create_reading_revisit` loads the letter (must be `status='generated'` + owned), assembles the reading from payload fields **in order** (skipping empties), then **`build_system(persona)` FIRST + `REVISIT_OPENING` appended** — the safety/HARD-RULES layer is preserved, never replaced. One non-stream `complete(MODEL_PRO, max_tokens=1024)`; the synthetic `<letter>` user turn is **not persisted**.
- **The revisit judges *on the reading*** — the persona delivers its own candid read of the person, not a summary; opens on a position (not a question); ends with a single genuine invitation.
- **Post-gen safety gate:** `safety_service.check_output(text)` runs on the generated read (same as the streaming path) — on suppression the text is replaced with the app-voice safe line, a `safety_event` is logged, and the row is marked `persona_override`.
- **No post-gen brevity band on revisit:** `check_brevity` is NOT applied on this path — only the safety gate runs. Do not add a brevity pass without a product decision (TD-34).

**Unified Reflections feed + Mirror saves (P2-SMOKE-10/11 — #277, #279–#281):**
- `mirror_saves` table (025) mirrors `council_saves` exactly (additive). `GET /reflections/feed` + `services/reflections_feed_service.py` unify saved lines + Mirror/Council verdicts; share-from-verdict cards; Council 4-persona thumbnail row; hero-bg share cards.
- Gravity-gated conclusions are savable: `messages.message_kind` (023, default `'standard'`) + `saved_lines.source_type` CHECK extended to `'conclusion'` (024).

**Dates + search:** `formatItemDate` (`apps/web/lib/formatItemDate.ts`, #306) — relative <7d, absolute beyond; consumed by Today + the three reflection cards. Reflections client-side search (#307).

**Polish / fixes batch (summarized — per-PR rows in §6):** iOS share-sheet reliability (#295, #305, #292, #301), chat-freeze fix (#283), UI-polish batch (#282), YvY forming preview + admin bypass (#296, #300), reflections/council/guide styling (#289–#294, #297, #299, #304), onboarding themes (#303), auto-scroll throttle (#302), BottomSheet/tab-bar iOS polish (#285–#288).

**⚠️ Doc-lineage note:** PR #284 ("docs(v11)") logged the chat-freeze fix (#283) + UI-polish batch (#282) into the **v11** docs, not v17. Per additive convention v11 is untouched; both are restated here in their correct v18 lineage.

---

## 2026-06-12 Session Delta — P0-SMOKE tab/sheet batch + P3-SMOKE-08

> Appended as v17. Where this conflicts with earlier sections, this section wins.

**Code merged to main (current main SHA: `57e1ef4d`):**

- **PR #273 (`d5b16ccb`) — bottom-anchored tab bar + sheet safe-area; `100svh/1.15` double-compensation dropped. Closes P0-SMOKE-01 / 03a / 03b.**
  - `components/layout/BottomTabBar.tsx` — tab bar rebuilt as a bottom-anchored frosted pill (fixed floating element out of flow).
  - `app/app/(tabs)/layout.tsx` — `h-[calc(100svh/1.15)]` → `h-[100svh]`; reserves the pill's footprint via `paddingBottom: calc(4rem + env(safe-area-inset-bottom) + 12px + 8px)`.
  - `components/ui/BottomSheet.tsx` — `/1.15` divisor + `maxHeight` calc removed; now owns `env(safe-area-inset-bottom)` (single source of safe-area truth for all sheets).
  - `app/app/mirror/page.tsx` — host-picker `/1.15` divisor removed.
  - `components/rituals/RitualScheduleSheet.tsx` — touched in the same pass.
  - **Finding:** modern engines already adjust `svh` under `body { zoom: 1.15 }`; the manual `/1.15` was double-compensation pulling the bottom edge ~13% short. **TD-30 superseded** — the divisors were not load-bearing. Zoom-hack removal now stands alone as TD-32.

- **Conversation deletion → DONE.**

- **P3-SMOKE-08 → CLOSED (three phases):**
  - **PR-A (`bfcd4d3b` / #274, `feat/today-consolidated-card`):** `components/today/TodaysTopicCard.tsx` redesigned into the consolidated "What brings you here?" card — theme pills (8 shared slugs) + free-text; "Initiate reflection" (primary) → `/app/onboarding/need`; "Quick start" (outlined) → topic → `PersonaPickerSheet` → chat. `THEME_OPTIONS` extracted to `apps/web/lib/themes.ts` (single source of truth; `onboarding/themes/page.tsx` imports it — route file kept). Today → `/app/onboarding/themes` nav removed.
  - **PR-B — NO-OP (finding):** the single matched-mind journey (need → top-1 mind, seeded chat, "See all minds") **was already shipped in PR #217 (`ca1fac53`)**. The backlog **B4 "3-match screen" premise was stale** — nothing to build. Recorded so future sessions don't re-plan against B4.
  - **PR-C (`57e1ef4d` / #275, `feat/wise-room-guide`):** new `apps/web/app/app/guide/page.tsx` "Living in the Wise Room" explainer. Today bottom button "Explore minds" → **"Living in the Wise Room"** (→ `/app/guide`). Explore still reachable via Library tab + matches "See all minds".

- **P2-SMOKE-10 / 11 → IN PROGRESS.** Approved architecture: **Option B additive** — `mirror_saves` table mirroring `council_saves`; unified Reflections feed endpoint; share cards with faded ritual hero backgrounds; Council card gains a 4-persona thumbnail row. Branch `feat/mirror-saves` in flight.

**Netlify operational notes:**
- Drawer disabled.
- Preview password / SSO protection intentionally disabled (preview deploys openly reachable for smoke testing).

---

## 2026-06-03 Session Delta — PR3a micro-polish + daily_questions

> Appended as v17. Where this conflicts with v16 or prior sections, this section wins.

**Code merged to main (current main SHA: `c50779b5`):**

- **PR #210 (`eda60f21`) — three bug fixes:**
  - `apps/web/components/library/ConversationCard.tsx`: `title ?? last_message_snippet`. Was `last_message_snippet ?? title` — title never rendered. BUG-013 + PR3a item #2 closed.
  - `apps/web/app/app/(tabs)/today/page.tsx`: first-day "Reflect" now opens `PersonaPickerSheet` instead of hardcoding Marcus Aurelius. Opening message skipped only when a topic exists.
  - `apps/web/components/personas/PersonaPickerSheet.tsx`: `onClose()` before async create. History.back no longer reverts router.push. PR3a item A (chat stuck) closed.

- **Rituals micro-polish:**
  - `apps/web/app/app/(tabs)/rituals/page.tsx` — You-vs-You card: inline half-sphere SVG (circle + right-semicircle path, `currentColor`); replaces `<Contrast>`. Item #5 closed.
  - Letter-to-Future-Self: whole card is `<button onClick={handleBeginLetter}>`. Inner "Begin" `<button>` and `<ChevronRight>` removed. Pro-gate + `RitualScheduleSheet` preserved. Item #8 closed.
  - Imports: `Contrast` and `ChevronRight` removed from `lucide-react`.

- **App icon — tried, landed accidentally, hotfixed:**
  - `appbutton.png` (1122×1402 px, ~2.1 MB) copied as `apps/web/app/icon.png` and `apple-icon.png`. Both landed on main (`c9bb3d39`). Removed in hotfix (`c50779b5`).
  - **DECISION: app-icon mark DEFERRED.** Photo too large and wrong shape for favicon/PWA icon. Purpose-built icon mark required (TD-29). Item B deferred.

**Database (no migrations; data changes only):**
- `daily_questions`: 50 phenomenology themes inserted (display_order 1000–1049, active=true); old 30 deactivated (active=false, reversible). Item #6 closed.
- `backfill-titles` executed: `{queued: 0}`. No title debt. Done.

**Operational facts:**
- Oregon `bvzeuwzqgnqcghvqghtb` confirmed canonical. Ireland `plecolxlzshkfvybszgs` = deprecated; deletion ~2026-06-09.
- Pro test account `nckoutras+pro1@gmail.com` granted via `UPDATE subscriptions`.
- OTP lockout root cause: Upstash Redis `otp_request:{email}` 5/hour. Workaround: `+alias` = fresh rate-limit bucket.

**PRs that failed / were reversed:**
- `polish/rituals-app-icon` accidentally included icon files in the merge. Hotfix `hotfix/remove-photo-icon` removed them.

**Key superseded facts:**
- `ConversationCard.tsx`: `last_message_snippet ?? title` → `title ?? last_message_snippet`. **BUG-013 CLOSED.**
- `PersonaPickerSheet.tsx`: `onClose()` before create. **PR3a item A CLOSED.**
- `today/page.tsx`: first-day picker opens sheet. **Not hardcoded.**
- `rituals/page.tsx` YvY icon: half-sphere SVG. **Item #5 CLOSED.**
- `rituals/page.tsx` Letter card: whole-card button. **Item #8 CLOSED.**
- `daily_questions`: 50 phenomenology themes active. **Item #6 CLOSED.**

---

## v16 Session Deltas (2026-06-01 through 2026-06-03)

See `HANDOFF_BRIEF_v16.md` for full v16 session detail: The Council (PRs #182–#186), You vs You (PRs #193–#202), Revenue chain (TD-11, BETA off, Stripe verified, PR3a triage).

---

## Top of mind / Next (2026-06-15 — after Sunday Letter / Revisit / Reflections-feed session)

### Sunday Letter reader, Reading Revisit, Letter share, and unified Reflections feed all shipped. PR3a memory bugs still lead.

**Priority order as of end of 2026-06-15 session:**

0. **Smoke-test the new surfaces (P-03 cadence):** Sunday Letter list/detail/search/**hard-delete**, letter **share** (confirm `sundayletter.png` renders), **Revisit** flow (persona picker → candid read), unified Reflections feed + Mirror saves. These touch a new router, a new generation path, and share — verify before the next feature brief.

0b. **Newly tracked debt:** TD-33 (Weekly Reading ARQ email delivery — `email_sent_at` unused), TD-34 (cache the non-stream Revisit completion). Both deferrable.

1. **PR3a memory bugs — 🔴 not started (highest priority):**
   - Fresh-chat missing opening message/thumbnail
   - Home "Continuing" 404s
   All other PR3a items closed. This is the only remaining cold-beta blocker in the PR3a sweep.

2. **Cold beta with 3–5 fresh users** — date to be locked once memory bugs resolved.

3. **Live Stripe wiring (TD-28) — 🔴 not started (P0 before any real payment):**
   - Live Stripe keys + live price IDs
   - Separate live-mode webhook (same path `/api/v1/billing/webhook`, different signing secret)
   - `ENVIRONMENT=development` → `production` on Render API

4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync** — NULL pre-#205 row; manual re-sync needed.

5. **App-icon mark (TD-29)** — design required before next attempt. Do NOT copy another photo PNG.

6. **You vs You fast-follows** (post-first-paying-user, NOT before launch):
   - Funnel analytics, rolling-both window anchor (v2).

7. **Council fast-follows** (post-first-paying-user, NOT before launch):
   - Per-verdict saves (design first), Council share card redesign, Reflection share card redesign.

8. **Rituals guided programs** — Counterview spec §1.3.2 ready; implementation not yet designed. Design with Claude (chat) before brief dispatch.

9. **Deferred from PR3a** (post-cold-beta):
   - Item #3: Google/Apple OAuth (backend `auth_oauth_router` scaffolding exists)
   - Item #4: Surface The Council in Rituals
   - Item #7: Intent/mode selection screen

### Still-pending from prior sessions

- `.gitignore` security debt — **must fix before any code PR** (branch `chore/gitignore-env-local`)
- Author smoke-test voice changes — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu
- PR-D2 production smoke test — use gmail workaround
- OTP-01 (ote.gr delivery failure) — investigate Render logs
- compress mirror.png (2.3MB → WebP)

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

### 1. .gitignore security debt (CRITICAL — do first)

`.env.local` is **NOT** in `.gitignore`. Production secrets are one accidental `git add -A` away from the public repo.

**Action required:** Single dedicated commit before any other PR:
- Branch: `chore/gitignore-env-local`
- File changed: `.gitignore` only
- Patterns to add: `.env.local`, `.env*.local`

### 2. PR-D2 production smoke test PENDING

Blocked by OTP delivery failure to ote.gr. Workaround: use Gmail.

### 3. OTP delivery failure for ote.gr (investigation pending)

OTP to `nkoutr@ote.gr` fails before DB insert. Render logs investigation pending.
Root cause of rate-limit lockout confirmed: Upstash Redis `otp_request:{email}` 5/hour (`auth.py`). Workaround: `+alias` email.

### 4. Render env var protection (operational debt)

ANTHROPIC_API_KEY disappeared between May 25-27. `render.yaml` needs `sync: false` on all secrets.

---

## Changelog v16 → v17

### PR #273 (`d5b16ccb`) — 2026-06-12

Bottom-anchored frosted tab bar; `BottomSheet` owns `env(safe-area-inset-bottom)`; `100svh/1.15` divisor removed from `(tabs)/layout.tsx`, `BottomSheet.tsx`, `mirror/page.tsx` (double-compensation finding — TD-30 superseded). Also touched `RitualScheduleSheet.tsx`. Closes P0-SMOKE-01/03a/03b.

### PR #274 (`bfcd4d3b`) — 2026-06-12

Consolidated "What brings you here?" Today card (`TodaysTopicCard.tsx`): pills + free text, Initiate reflection → `need` flow, Quick start → picker. `THEME_OPTIONS` → `apps/web/lib/themes.ts` single source of truth. P3-SMOKE-08 phase 1.

### PR #275 (`57e1ef4d`) — 2026-06-12

`/app/guide` "Living in the Wise Room" explainer; Today button "Explore minds" → "Living in the Wise Room". P3-SMOKE-08 phase 3. (Phase 2 was a no-op — matched-mind journey already in #217.)

### PR #210 (`eda60f21`)

**Three bug fixes (squash merged)**

- `apps/web/components/library/ConversationCard.tsx` — `title ?? last_message_snippet`
- `apps/web/app/app/(tabs)/today/page.tsx` — first-day picker + opening message guard
- `apps/web/components/personas/PersonaPickerSheet.tsx` — `onClose()` before async create

### Rituals micro-polish (merged as `c9bb3d39`)

- `apps/web/app/app/(tabs)/rituals/page.tsx` — half-sphere SVG (YvY card) + whole-card button (Letter card)

### Hotfix icon removal (`c50779b5`)

- `apps/web/app/icon.png` and `apps/web/app/apple-icon.png` removed. Photo icon landed accidentally; deferred.

---

## 1. Pre-Work Investigation Protocol

Unchanged from v12. Defined in `CLAUDE.md` at repo root. Mandatory for all multi-PR work. P-01 through P-06 apply to ALL sessions.

---

## 2. Current architecture

Unchanged from v16. See `HANDOFF_BRIEF_v16.md §2`.

---

## 3. Test infrastructure

```
~292+ backend tests (v12 baseline)
~43+ frontend tests (v12 baseline)
```

No test changes in v17 session.

---

## 4. Known limitations and not-yet-wired features

All v16 limitations apply. Updates since v16:

### 4.18 ConversationCard title — CLOSED (v17)

`ConversationCard.tsx` now renders `title ?? last_message_snippet`. Title renders first; snippet is fallback. BUG-013 closed.

### 4.20 App icon not wired (NEW v17)

`apps/web/app/icon.png` and `apps/web/app/apple-icon.png` do not exist on main. Photo icon tried and removed (too large, wrong shape). Purpose-built icon mark required before next attempt (TD-29).

### 4.21 daily_questions rotation (NEW v17)

`GET /api/v1/today/question` now rotates across 50 modern-phenomenology themes (display_order 1000–1049). Old 30 philosophical prompts are inactive (`active=false`, reversible). `backfill-titles` executed; queued=0.

### Limitations 4.16, 4.17, 4.19 from v16

Still apply. See `HANDOFF_BRIEF_v16.md §4`.

---

## 5. Next session entry point

**Priority order as of 2026-06-03 (end of v17 session):**

### Phase 0 — Operational cleanup (do before any code PR)

1. **Fix .gitignore** — branch `chore/gitignore-env-local`. Single commit.
2. **Smoke test PR-D2** — sign in with gmail, verify NamePromptCard save flow.
3. **Investigate OTP-01** — Render logs for ote.gr failure.
4. **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### Phase 1 — Revenue gate [COMPLETE ✅]

- ~~TD-11~~ ✅ DONE (#203)
- ~~Disable BETA_GRANT_PRO_TO_ALL~~ ✅ DONE
- ~~End-to-end Stripe sandbox test~~ ✅ DONE

### Phase 1b — PR3a cold-beta sweep [NEARLY COMPLETE]

5. **PR3a memory bugs** — fresh-chat missing opening message/thumbnail; home "Continuing" 404s. Last remaining item.
   *(All other PR3a items closed in v17 session.)*

### Phase 1c — Live Stripe wiring (before any real payment)

6. **TD-28 — Live Stripe wiring** — live keys + live price IDs + live-mode webhook (URL fix + live signing secret) + `ENVIRONMENT=production` on Render API.

### Phase 1d — OPS cleanup

7. **OPS-001 — nkoutr@ote.gr re-sync.**
8. **TD-29 — App-icon mark** — design + implement once mark is ready.

### Phase 2 — Council fast-follows (post-first-paying-user, NOT before)

9. **Per-verdict → reflections save** — investigation brief first.
10. **Council share card redesign** — boardroom bg, date header, 4 portrait thumbnails.
11. **Reflection share card redesign** — center text, smaller/lower thumbnail.
12. **compress mirror.png** — 2.3MB → WebP.

### Phase 3 — Rituals guided programs [retention]

13. **Design session** — Counterview spec + guided program flows. Do NOT dispatch build brief without design.

### Phase 4 — Mirror fast-follows (post-first-paying-user)

14. Branded email postcard. Host-aware handoff. Smart input cap.

### Phase 5 — Remaining Brief #1 queue

15. **PR-C** — Library F6 spec restoration (1-2 days)
16. **PR-G** — F2 verification + Sunday counter (2-4 days)
17. **PR-E** — Press further mode toggle (3-4 days)

### Phase 6 — Infrastructure hardening

18. **TD-24** — render.yaml `sync: false` for all secrets + startup health check + alerts.

### Phase 7 — Launch track

19. Block B consolidated polish PR
20. Pre-launch items (lawyer review, DNS, GDPR/DPA, runbooks)
21. UAT (≥2/5 spontaneous "I'd pay")
22. Cold validation with external users

---

## 6. PR history (v16 → v17)

| PR | Description | Date | Status |
|---|---|---|---|
| #313 70059bc3 | feat(letter-share): letter kind in SharePreviewModal + Share button on reading page | 2026-06-15 | ✅ merged |
| #312 eeb365ab | feat(letter-share): `POST /weekly-letters/{id}/share` — wax-seal share card | 2026-06-15 | ✅ merged |
| #311 b750fb29 | feat(revisit): revisit-mode persona picker + button on reading detail page | 2026-06-15 | ✅ merged |
| #310 46483f85 | feat(reading-revisit): `POST /conversations/reading-revisit` — persona's candid read | 2026-06-15 | ✅ merged |
| #309 96af0e59 | feat(sunday-letter): next-Sunday date; returning users get archive link | 2026-06-15 | ✅ merged |
| #308 9a773a26 | feat(reading-library): search + hard-delete (`DELETE /weekly-letters/{id}`) | 2026-06-15 | ✅ merged |
| #307 12d74894 | feat(reflections): client-side search over the feed | 2026-06-15 | ✅ merged |
| #306 e2219134 | feat(dates): `formatItemDate` — absolute date for items older than 7 days | 2026-06-15 | ✅ merged |
| #305 741f3001 | fix(share): retry pre-generation so iOS share opens natively | 2026-06-15 | ✅ merged |
| #304 8e6285e2 | feat(guide): Explore The Wise Room — minds + rituals imagery | 2026-06-15 | ✅ merged |
| #303 8edce496 | feat(onboarding): dilemma/controversy/doubt/freedom themes + weights | 2026-06-15 | ✅ merged |
| #302 f78415cc | fix(rituals): throttle streaming auto-scroll (4→24 words) | 2026-06-15 | ✅ merged |
| #301 1cabf350 | style(share): more prominent wordmark + date on shared cards | 2026-06-15 | ✅ merged |
| #300 ec21fd46 | feat(you-vs-you): forming preview as 2–3 short bullets | 2026-06-15 | ✅ merged |
| #299 e42416fc | style(council): paper surface on persona responses | 2026-06-15 | ✅ merged |
| #298 d5c49b1f | feat(weekly-letter): interpretive prompt + per-persona cross-letter continuity | 2026-06-15 | ✅ merged |
| #297 0c641e95 | style(ui): saved-line thumbnail +10%; mirror said/meant emphasis | 2026-06-15 | ✅ merged |
| #296 aea3d287 | feat(you-vs-you): admin bypass for forming gate (thresholds unchanged) | 2026-06-15 | ✅ merged |
| #295 09129a5f | fix(share): pre-generate image for pro/premium so iOS share sheet opens | 2026-06-14 | ✅ merged |
| #289–#294 | style(reflections): bronze borders, headers/dates, round thumbnails, hero bg, filled Save CTA, source eyebrows | 2026-06-14 | ✅ merged |
| #287/#288 | fix(web): anchor BottomSheet to viewport bottom; clear tab-bar footprint for Letter submit (iOS) | 2026-06-14 | ✅ merged |
| #285/#286 | fix(web): revert Sunday-card dismiss-X + enlarge modal close-×; Today title 20px/medium | 2026-06-13 | ✅ merged |
| #283 3f2ea116 | fix(chat): chat-freeze investigation/§5 fix *(logged in v11 docs by #284)* | 2026-06-13 | ✅ merged |
| #282 9760ea7a | feat: UI-polish batch *(logged in v11 docs by #284)* | 2026-06-13 | ✅ merged |
| #279–#281 | feat(reflections): unified feed + ritual share cards + share-from-verdict (PR-29b/c/d) | 2026-06-13 | ✅ merged |
| #277 e796af31 | feat(mirror): save Mirror verdicts via `mirror_saves` (P2-SMOKE-10 phase 1) | 2026-06-13 | ✅ merged |
| #275 57e1ef4d | feat(today): "Living in the Wise Room" `/app/guide` explainer + button rewire (P3-SMOKE-08 phase 3) | 2026-06-12 | ✅ merged |
| #274 bfcd4d3b | feat(today): consolidated "What brings you here?" card + `THEME_OPTIONS`→`lib/themes.ts` (P3-SMOKE-08 phase 1) | 2026-06-12 | ✅ merged |
| #273 d5b16ccb | fix(web): bottom-anchored tab bar + sheet safe-area; drop `svh/1.15` double-compensation (P0-SMOKE-01/03a/03b) | 2026-06-12 | ✅ merged |
| #210 eda60f21 | fix: ConversationCard title, today first-day picker, cross-persona chat start (3 fixes, squash) | 2026-06-03 | ✅ merged |
| c9bb3d39 | polish(rituals): half-sphere YvY SVG icon + Letter whole-card tap (+ accidental icon files) | 2026-06-03 | ✅ merged |
| c50779b5 | hotfix: remove oversized photo app-icon (icon mark deferred) | 2026-06-03 | ✅ merged |

Earlier PR history (v12–v16): see `HANDOFF_BRIEF_v16.md §6`.

---

## 7. Environmental configuration

Unchanged from v16. No new env vars in v17 session.

---

## 8. Key file paths (production codebase)

All v16/v17 paths apply. New in v18:

### Backend (apps/api/)

- `routers/weekly_letters.py` — NEW: list/get/`DELETE`/`POST {id}/share` (Sunday Letters).
- `routers/reflections.py` — `GET /reflections/feed`; `services/reflections_feed_service.py` — NEW.
- `routers/conversations.py` — `POST /reading-revisit`; `services/conversation_service.py` — `create_reading_revisit` + `REVISIT_OPENING`.
- `services/image_service.py` — `generate_letter_share_image` (uses `static/rituals/sundayletter.png`).
- `static/rituals/sundayletter.png` — NEW asset (required by letter share).
- `db/migrations/versions/022_create_weekly_letters.py`, `023_add_message_kind.py`, `024_saved_line_conclusion_source.py`, `025_create_mirror_saves.py`.

### Frontend (apps/web/) — v18

- `lib/formatItemDate.ts` — NEW (#306).
- `app/app/letters/page.tsx` — Sunday Letter library (list + search + hard-delete).
- `app/app/letters/[id]/page.tsx` — reading detail (Revisit + Share).
- `components/share/SharePreviewModal.tsx` — `kind='letter'`.
- `components/personas/PersonaPickerSheet.tsx` — revisit mode.
- `components/reflections/{CouncilVerdictCard,MirrorVerdictCard,SavedLineCard}.tsx` — `formatItemDate` + unified-feed styling.
- `app/app/(tabs)/reflections/page.tsx` — unified feed + client-side search.

### Frontend (apps/web/) — v17 carryover

- `lib/themes.ts` — NEW (PR #274): `THEME_OPTIONS` single source of truth (mirrors backend Pydantic enum); consumed by `TodaysTopicCard` and `onboarding/themes/page.tsx`.
- `app/app/guide/page.tsx` — NEW (PR #275): "Living in the Wise Room" explainer screen.
- `components/today/TodaysTopicCard.tsx` — UPDATED (PR #274): consolidated "What brings you here?" card (pills + free text; Initiate reflection → `need`; Quick start → picker).
- `components/layout/BottomTabBar.tsx` — UPDATED (PR #273): bottom-anchored frosted floating pill (fixed, out of flow).
- `app/app/(tabs)/layout.tsx` — UPDATED (PR #273): `100svh` (no `/1.15`); reserves tab-bar footprint via `paddingBottom`.
- `components/ui/BottomSheet.tsx` — UPDATED (PR #273): owns `env(safe-area-inset-bottom)`; `/1.15` divisor + `maxHeight` calc removed.
- `app/app/mirror/page.tsx` — UPDATED (PR #273): host-picker `/1.15` divisor removed.
- `app/app/(tabs)/today/page.tsx` — UPDATED (PR #274 removed Today → `/app/onboarding/themes` nav; "Explore minds" button relabeled to "Living in the Wise Room" → `/app/guide` in PR #275). Earlier (PR #210): first-day Reflect opens PersonaPickerSheet.
- `app/app/(tabs)/rituals/page.tsx` — UPDATED: half-sphere SVG (YvY card); whole-card tap (Letter card); `Contrast` + `ChevronRight` removed from imports.
- `components/library/ConversationCard.tsx` — UPDATED (PR #210): `title ?? last_message_snippet`.
- `components/personas/PersonaPickerSheet.tsx` — UPDATED (PR #210): `onClose()` before async create.

---

## 9. Decision history (v17 additions)

### 2026-06-03 — App icon mark deferred

Photo asset (`appbutton.png`, 1122×1402 px) is not suitable as a favicon/PWA/apple-touch icon: wrong aspect ratio, too large, not optimized. The Chesterfield armchair photo remains as brand/hero/OG image only. A purpose-built icon mark must be designed before wiring `apps/web/app/icon.png` and `apps/web/app/apple-icon.png`. Do NOT use any full-bleed photo PNG as the app icon.

### 2026-06-03 — daily_questions phenomenology rotation

50 modern-phenomenology themes are the canonical "What's on your mind?" prompt pool going forward. The old 30 philosophical prompts remain in the table with `active=false` — they are a recoverable safety net, not deleted. If a theme needs updating, `UPDATE daily_questions SET active=false WHERE display_order=<N>` and insert a replacement.

### 2026-06-03 — OTP rate-limit workaround documented

The 5/hour OTP rate-limit per email is enforced at the Upstash Redis layer (`otp_request:{email}` key in `auth.py`). Using a `+alias` (e.g., `founder+test2@gmail.com`) creates a separate rate-limit bucket. This is a testing-only workaround; not a production feature.

### All prior decisions from v16 §9

Unchanged.

---

## 10. Section 5.7 framework — status

Unchanged from v12.

---

## 11. Migration plan — status

All phases through Block C complete. Oregon complete. alembic_version = **`025_create_mirror_saves`** (v18; 022–025 added — verify the Oregon DB has applied them, as 022–024 predate the window).

---

## 12. Deployment readiness

```
✅ Backend                Render web service philosopher-api
                          philosopher-api-z9l9.onrender.com
                          ✅ Paid Starter tier
                          ✅ ANTHROPIC_API_KEY confirmed

✅ Worker                 Render worker philosopher-worker
                          ✅ Paid Starter tier
                          ✅ Upstash Pay-as-You-Go

✅ Database               alembic_version = '025_create_mirror_saves'
                          Oregon confirmed live. (Confirm 022–025 applied.)
                          DATABASE_URL → Oregon bvzeuwzqgnqcghvqghtb.
                          Ireland plecolxlzshkfvybszgs deprecated; deletion ~2026-06-09.

🟡 Redis (Upstash)        ✅ Pay-as-You-Go
                          ⚠️ 80% quota alert not yet set up

🟡 Email                  Resend free tier (test sender)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS
                          ⚠️ OTP delivery failing to ote.gr (investigation pending)

✅ Frontend (canonical)   Netlify thinkalike.netlify.app

✅ LLM                    Anthropic API wired — chat + Council synthesis live

✅ Stripe                 Sandbox: end-to-end verified (2026-06-03). Revenue chain CLOSED in TEST.
                          ⚠️ LIVE wiring pending (TD-28): live keys + live price IDs + live-mode webhook + ENVIRONMENT=production

🟡 Google OAuth           Dormant (GOOGLE_OAUTH_ENABLED=false).

🟡 Rituals email delivery Letter-to-Future-Self + Weekly Reading DB schema live; ARQ delivery not wired (TD-33).

⚠️ App icon               No custom icon on main. Photo icon tried and removed. Icon mark TBD (TD-29).
```

---

## 13. Session lessons (v17 additions)

### 13.18–13.20 Preserved from v16

See `HANDOFF_BRIEF_v16.md §13`.

### 13.21 — Branching from stale local main creates empty PRs (v17)

The `pr3a` branch was accidentally built from a stale local commit (`569631c4`) predating the `Pr3a (#210)` merge. The branch appeared to have 3 meaningful commits ahead of main, but all three were already in `origin/main`. Always run `git fetch origin && git reset --hard origin/main` before branching for a new PR (P-01). This session resolved it by: deleting the stale branch, pulling origin/main, creating a fresh branch `polish/rituals-app-icon`.

### 13.23 — The `100svh/1.15` divisor was double-compensation, not a fix (v17, 2026-06-12)

The chain of tab-bar/sheet positioning fixes (#260–#264) layered a manual `/1.15` divisor onto viewport-unit heights to "compensate" for `body { zoom: 1.15 }`. PR #273 found this was wrong: modern engines already adjust `svh` under `zoom`, so the divisor *double*-compensated and pushed bottom edges ~13% short. Removing it (plain `100svh`) and re-architecting the tab bar as a bottom-anchored floating pill that reserves its own footprint fixed the class of bug. Lesson: when a hack needs escalating "compensation" across more sites each PR, suspect the compensation itself is the bug. TD-30 (which assumed the divisors were load-bearing) is superseded; the real cleanup is removing `zoom: 1.15` entirely (TD-32, post-cold-beta).

### 13.24 — Verify a backlog item still describes reality before planning against it (v17, 2026-06-12)

P3-SMOKE-08 phase B was specified as a "B4 3-match screen" build. Investigation showed the single matched-mind journey had already shipped in PR #217 — the B4 premise was stale. Phase B became a no-op with a recorded finding instead of duplicate work. Lesson: re-confirm the current production behavior (per CLAUDE.md Rule 3 / Pre-Work Investigation) before dispatching a build brief against an older backlog item.

### 13.25 — Dynamically-generated "sharpest" content must re-run the post-gen safety gate (v18, 2026-06-15)

Reading Revisit is the app's most pointed generated content — a persona's blunt, candid read of the user. `create_reading_revisit` therefore runs the **same** post-generation safety gate as the streaming path (`safety_service.check_output`), suppressing to the app-voice safe line + logging a `safety_event` on override. It does this even though the path is non-stream and the read is built from already-safe letter payload. Lesson: any new generation surface that can produce persona-voice text must pass `check_output` before persistence/display — the gate is per-surface, not just on the main chat stream. Note the deliberate asymmetry: revisit runs the **safety** gate but **not** the brevity band (`check_brevity`) — brevity is a chat-turn affordance, not a safety control.

### 13.26 — Append to `build_system`, never replace it (v18, 2026-06-15)

`REVISIT_OPENING` is concatenated **after** `prompt_builder.build_system(persona)` so the HARD-RULES / safety layer that `build_system` emits stays intact. When adding a new mode prompt (revisit, future ritual openings), append to the system prompt — do not hand-assemble a system string that drops the safety preamble.

### 13.27 — The v17 doc under-logged migrations; keep the schema table at HEAD (v18, 2026-06-15)

v17's schema table stopped at `021`, but `022`–`024` (weekly_letters, message_kind, saved_line conclusion) had already shipped to main before the v17 doc was written. v18 reconciled the head to `025`. Lesson: when rotating docs, diff the alembic `versions/` dir against the doc's migration table — a feature can ship its migration several PRs before its UI, and the schema log is the easiest thing to let drift.

### 13.22 — Photo PNG is not an app icon

`appbutton.png` (1122×1402, non-square, 2.1 MB) was tried as `icon.png`/`apple-icon.png`. Next.js / browsers / Apple require square icons, typically 192×192 to 1024×1024 px. A photo at 1122×1402 is wrong shape and size. Always verify dimensions before wiring app icons.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v12. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. P-01 through P-06 apply to ALL sessions.

### The most important context for the next session

**Five things in order:**

1. **Fix .gitignore first.** `.env.local` NOT in `.gitignore`. Highest-priority item above all feature work.

2. **PR3a memory bugs are the last cold-beta blocker.** All other PR3a items closed. Fix fresh-chat missing opening message/thumbnail and home "Continuing" 404s, then cold beta can proceed.

3. **Revenue chain is CLOSED in TEST/sandbox.** Next gate is live Stripe wiring (TD-28): live keys, live price IDs, *separate* live-mode webhook with its own signing secret, `ENVIRONMENT=production` on Render.

4. **App icon mark is DEFERRED (TD-29).** Do NOT use any photo PNG. A purpose-built square icon mark must be designed. The Chesterfield photo is brand/hero/OG only.

5. **Brand name is "The Wise Room" (locked).** Rename audit pending across docs, code, Stripe. Do not rename until audit complete and founder approves.

### Documentation hygiene

v17 rotation triggered by PR3a largely executing (5/7 items closed, daily_questions updated, backfill-titles done). Next baseline regen threshold: cold beta begins OR major new feature block complete. Until then, append `*_v17_ADDENDUM_<date>.md` instead of rewriting v17.

### Launch timeline from here

Realistic from end of 2026-06-03 v17 session: 3-5 weeks.
- PR3a memory bugs: ~1 week.
- Cold beta + DNS cutover: 1-2 weeks.
- Counterview design + build: ~2-3 weeks.
- Live Stripe wiring: ~1 week.
- **Target: mid-July 2026.**

---

**End of HANDOFF_BRIEF v18.** Authoritative as of 2026-06-15 (Sunday Letter / Revisit / Letter share / Reflections feed session). Supersedes `HANDOFF_BRIEF_v17.md` (preserved as historical reference). Where this file conflicts with v17, v18 wins.
