# HANDOFF BRIEF v17 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-03
**Prior version:** `docs/HANDOFF_BRIEF_v16.md` (2026-06-03)
**Generated:** 2026-06-03 (v17 rotation)

**Block trigger for v17 rotation:** PR3a sweep largely executed — 5 of 7 items closed, daily_questions updated, backfill-titles done. State materially different from v16 on bug and data fronts.

**v17 summary (2026-06-03):** PR3a items A, #2, #5, #6, #8 ✅ CLOSED. Memory bugs 🔴 still open. App icon ⏸ DEFERRED. daily_questions updated to 50 phenomenology themes. backfill-titles executed (queued=0). OTP lockout root cause documented. Pro test account created.

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

> **v17 conflict resolution rule:** Where v17 conflicts with v16 or earlier, v17 wins. Production reality always wins over docs.

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

## Top of mind / Next (2026-06-03 — after v17 session)

### PR3a is largely done. One item remains before cold beta.

**Priority order as of end of v17 session:**

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
| #210 eda60f21 | fix: ConversationCard title, today first-day picker, cross-persona chat start (3 fixes, squash) | 2026-06-03 | ✅ merged |
| c9bb3d39 | polish(rituals): half-sphere YvY SVG icon + Letter whole-card tap (+ accidental icon files) | 2026-06-03 | ✅ merged |
| c50779b5 | hotfix: remove oversized photo app-icon (icon mark deferred) | 2026-06-03 | ✅ merged |

Earlier PR history (v12–v16): see `HANDOFF_BRIEF_v16.md §6`.

---

## 7. Environmental configuration

Unchanged from v16. No new env vars in v17 session.

---

## 8. Key file paths (production codebase)

All v16 paths apply. Changes in v17:

### Frontend (apps/web/)

- `app/app/(tabs)/rituals/page.tsx` — UPDATED: half-sphere SVG (YvY card); whole-card tap (Letter card); `Contrast` + `ChevronRight` removed from imports.
- `app/app/(tabs)/today/page.tsx` — UPDATED (PR #210): first-day Reflect opens PersonaPickerSheet.
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

All phases through Block C complete. Oregon complete. alembic_version = `021_create_self_comparisons`.

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

✅ Database               alembic_version = '021_create_self_comparisons'
                          Oregon confirmed live.
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

🟡 Rituals email delivery Letter DB schema live; ARQ delivery not wired.

⚠️ App icon               No custom icon on main. Photo icon tried and removed. Icon mark TBD (TD-29).
```

---

## 13. Session lessons (v17 additions)

### 13.18–13.20 Preserved from v16

See `HANDOFF_BRIEF_v16.md §13`.

### 13.21 — Branching from stale local main creates empty PRs (v17)

The `pr3a` branch was accidentally built from a stale local commit (`569631c4`) predating the `Pr3a (#210)` merge. The branch appeared to have 3 meaningful commits ahead of main, but all three were already in `origin/main`. Always run `git fetch origin && git reset --hard origin/main` before branching for a new PR (P-01). This session resolved it by: deleting the stale branch, pulling origin/main, creating a fresh branch `polish/rituals-app-icon`.

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

**End of HANDOFF_BRIEF v17.** Authoritative as of 2026-06-03 (PR3a micro-polish session). Supersedes `HANDOFF_BRIEF_v16.md` (preserved as historical reference). Where this file conflicts with v16, v17 wins.
