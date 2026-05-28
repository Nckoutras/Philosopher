# HANDOFF BRIEF v13 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-05-28
**Prior version:** `docs/HANDOFF_BRIEF_v12.md` (2026-05-26)
**Generated:** 2026-05-28 (v13 rotation)

**Block trigger for v13 baseline regen:** 2026-05-28 session shipped 4 PRs (Bug #1, PR-A/Bug #4, PR-D, PR-D2), resolved 2 production incidents (Upstash quota, missing API key), and locked 7 strategic decisions (rituals scope, weekly reading spec, council mode, press further, typography V1, data collection policy, brand rename). Also surfaces new operational debt (gitignore, render.yaml) that must be addressed before any further PR work.

**Status:**
- Block A ✅ FULLY CLOSED (5/5)
- Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending)
- Block C ✅ FULLY COMPLETE — real-time streaming added PR-A (#128)
- Stripe sandbox ✅ COMPLETE (PR1 #77, 2026-05-19)
- Paywall + BETA bypass ✅ COMPLETE (PR4j #100)
- Share v3 ✅ COMPLETE (PR4ag1 #122)
- Rituals tab + page ✅ COMPLETE (PR4o + PR4ah) — Mirror/Counterview/Weekly Reading placeholder-locked
- Greeting personalization ✅ COMPLETE (PR-D #129)
- Name capture prompt ✅ MERGED (PR-D2 #130) — smoke test partially blocked by OTP issue
- Bug #1 ✅ FIXED (#127 — BottomSheet history.back race)
- Bug #4 ✅ FIXED (PR-A #128 — real-time streaming)
- Oregon region migration 🟡 IN PROGRESS — data partial, DATABASE_URL switch unconfirmed
- Upstash ✅ Pay-as-You-Go (upgraded 2026-05-27)
- ANTHROPIC_API_KEY ✅ Re-added to both services (2026-05-27/28)

> **v13 conflict resolution rule:** Where v13 conflicts with v12 or earlier, v13 wins. Production reality always wins over docs.

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

These must be addressed before the next PR brief is dispatched. Do NOT skip to feature work.

### 1. .gitignore security debt (CRITICAL — do first)

`.env.local` is **NOT** in `.gitignore`. Production secrets (DATABASE_URL, ANTHROPIC_API_KEY, Stripe keys, JWT_SECRET, etc.) are one accidental `git add -A` away from being committed to the public GitHub repo.

**Action required:** Single dedicated commit before any other PR:
- Branch: `chore/gitignore-env-local`
- File changed: `.gitignore` only
- Patterns to add: `.env.local`, `.env*.local`

**Do this first. No other PR work until this is done.**

### 2. PR-D2 production smoke test PENDING

The NamePromptCard save flow (What should we call you? → enter name → Save) has NOT been fully smoke tested in production. The intended test was blocked by an OTP delivery failure to the founder's ote.gr address.

**Workaround:** Use a Gmail address for OTP testing — deliverability is confirmed higher.

**Required smoke test:** Sign in with gmail → confirm Today page shows NamePromptCard (user must have null `full_name`) → type name → tap Save → confirm greeting updates → confirm "Not now" dismissal → confirm card doesn't reappear in the same session.

### 3. OTP delivery failure for ote.gr (investigation pending)

At end of 2026-05-28 session, OTP send to nkoutr@ote.gr failed with "we couldn't send the code". DB check confirmed no new `otp_codes` record was created — failure occurred BEFORE the DB insert step.

**Render logs investigation pending.** Likely candidates:
- Resend deliverability issue with ote.gr (Greek ISP)
- Resend API error or rate limit
- Rate-limiting based on stale May 14 attempt in DB

**This is NOT related to PR-D2 code.** OTP routes were not touched in PR-D2.

**Workaround:** Use gmail for OTP testing until root cause is identified.

### 4. Render env var protection (operational debt)

ANTHROPIC_API_KEY disappeared from BOTH `philosopher-api` and `philosopher-worker` services between May 25-27. Cause unconfirmed — possibly a blueprint sync without `sync: false` flag in render.yaml.

**Required actions (after .gitignore fix):**
- Add `sync: false` to `render.yaml` for ALL secrets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `JWT_SECRET`, `SECRET_KEY`, `REDIS_URL`, `DATABASE_URL`, `RESEND_API_KEY`
- Implement startup health check that fails loudly on missing critical secrets
- Set up Upstash 80% quota alert (Upstash dashboard)
- Set up Render env-var-change notification

---

## Changelog v12 → v13

### Bug #1 (#127) — BottomSheet history.back navigation race (2026-05-28)

**Files:** `apps/web/app/app/(tabs)/today/page.tsx`, `apps/web/app/app/(tabs)/reflections/page.tsx`

**Root cause:** "Ask another mind" picker → choose persona → navigation killed by stale `history.back()` call from BottomSheet cleanup `useEffect`. The `setPickerOpen(false)` / `setPickerLine(null)` state setters fired BEFORE `router.push`, so React batched the cleanup `useEffect` while `history.state` still showed `{modal: 'bottom-sheet'}`, causing the cleanup to call `history.back()` and kill the navigation.

**Fix:** Reorder — `router.push` fires first (synchronously updates `history.state`), then state setter triggers cleanup which now finds `history.state.modal !== 'bottom-sheet'` and skips `history.back()`.

**Status:** ✅ Verified working on mobile Safari.

---

### Production incident — Upstash quota (2026-05-27)

Upstash free-tier 500k commands/month limit was hit, causing the `philosopher-worker` to crash. All ARQ tasks (title generation, memory extraction, etc.) were failing silently.

**Resolution:** Upstash upgraded from free to Pay-as-You-Go ($0.2/100k commands). Worker redeployed. Services confirmed healthy. Rate: ~0.2¢ per 1000 Redis commands — negligible at current load.

**Operational debt added:** Upstash 80% quota alert not yet set up. Add to next render.yaml / ops PR.

---

### Production incident — ANTHROPIC_API_KEY missing (2026-05-27/28)

ANTHROPIC_API_KEY disappeared from both `philosopher-api` AND `philosopher-worker` Render services. Cause unconfirmed — possibly a blueprint sync operation without `sync: false` flag.

**Impact:** All LLM calls (chat, title generation) were failing with authentication errors. Chat was broken for an unknown window between May 25-27.

**Resolution:** ANTHROPIC_API_KEY manually re-added to both services in Render dashboard. Both redeployed. Production smoke test passed: chat working, title generation working.

**Operational debt added:** render.yaml needs `sync: false` on all secrets (TD-24).

---

### Bug #4 / PR-A (#128) — Real-time streaming + inline correction (2026-05-28)

**Files:**
- `apps/api/services/conversation_service.py` — real-time stream + correction flow
- `apps/web/lib/api.ts` — `SSEEventCorrection` type added
- `apps/web/lib/store.ts` — `isCorrecting`, `correctionContent`, `setCorrection`, `appendCorrectionContent`, `resetStreaming` updates
- `apps/web/lib/useStream.tsx` — correction event routing, `contentBeforeCorrection` fallback
- `apps/web/components/chat/StreamingBubble.tsx` — correction visual
- `apps/web/app/globals.css` — `@keyframes fade-in` added

**Previous behavior:** LLM stream was buffered server-side, then yielded all at once after postprocessing completed. This caused 60+ second stalls (postprocessing + up to 3 regen attempts × 10-15s each).

**New behavior:**
- Chunks yielded to client as LLM generates (3-7s first chunk)
- Postprocessing (`check_universal_forbidden`) runs in background AFTER stream completes
- If check fails: new SSE event `'correction'` fires
  - Frontend: fades original content (text-charcoal opacity-55, 300ms transition)
  - Bronze 0.5px divider appears
  - "Let me put that again." renders in font-cormorant italic text-[13px] text-sepia — **LOCKED COPY, do not vary**
  - Regen streams in real-time
  - Fade-in: opacity 0→1 + translateY 4px→0, 250ms ease-out, fill mode
- If regen also fails: `_deterministic_strip` on regen text, saved stripped

**New structured log events (5):** `postprocessing_correction_triggered`, `postprocessing_correction_passed`, `postprocessing_correction_stripped`, `postprocessing_correction_failed`, `post_gen_safety_override`. All include `user_id`, `conversation_id`, `persona_slug`.

**Trade-offs accepted (documented):**
- ~17% of messages may briefly show Section 5.7-violating content before correction fires
- 0.1-2s persona content exposure before post-gen safety override
- Mid-stream errors → partial message + error event, no retry
- Regen-also-fails: user sees streamed content, DB saves stripped version

**Status:** ✅ 4/4 smoke scenarios passed.

---

### PR-D (#129) — Greeting personalization (2026-05-28)

**Files:** `apps/web/lib/useTimeGreeting.ts`, `apps/web/app/app/(tabs)/today/page.tsx`

- `getGreetingWithName(fullName, now?)` helper added to `useTimeGreeting.ts`
- Today page calls it with `user?.full_name`
- First name derived via `full_name?.trim().split(/\s+/)[0]` (same pattern as `arq_worker.py:202`)
- Graceful fallback: null / empty / whitespace → "Good morning." (no trailing comma)
- Currently personalizes for Google OAuth users only (OTP users get name via PR-D2)

**Status:** ✅ Live in production.

---

### PR-D2 (#130) — Name capture deferred prompt (2026-05-28)

**New endpoint:** `PATCH /api/v1/auth/me`
- Auth: `Depends(get_current_user)` — updates own record only
- Request schema: `UpdateMeRequest` — `full_name` trim + non-empty + max 100 chars
- Response: `UserOut` (same shape as `GET /auth/me`)

**New component:** `apps/web/components/today/NamePromptCard.tsx`
- Shows for nameless OTP users on Today (`full_name` null/empty/whitespace)
- LOCKED COPY: "What should we call you?" / "First name" placeholder / "Save" / "Not now"
- Card styling: bg-paper, border-edge 0.5px, shadow-card, rounded-sm
- Prompt: font-cormorant text-[19px] text-ink
- Input: bg-white border-ink, font-lora text-[15px]
- Save button: bg-ink text-vellum font-cormorant text-[16px] medium
- Animation: fade + maxHeight collapse, 250ms opacity / 350ms max-height, `onTransitionEnd` → `onDismiss`
- Save flow: `api.updateMe` → `setUser` → animate out → `onDismiss`
- Session-only dismissal (in-memory `useState`, not persisted)

**Store change:** `setUser: (user) => set({ user })` setter added to `apps/web/lib/store.ts`

**API change:** `api.updateMe(fullName: string)` method added to `apps/web/lib/api.ts`

**Today page:** Conditional render with `namePromptInitialized` ref for one-time snapshot on load

**Status:** ✅ Merged to production. Smoke test partially blocked by OTP delivery failure to ote.gr. See §open-issues #2.

---

### Strategic decisions locked (2026-05-28)

See `IMPLEMENTATION_BACKLOG_v13.md` §v13 Consolidation Summary and §9.7 for full detail. Key decisions:

1. Rituals launch scope = Option B (Mirror, Counterview, Letter, Weekly Reading placeholder)
2. Weekly Reading = renamed F3/F4 — single canonical feature, not a new system
3. Council Mode = Phase 5 / post-launch Premium
4. "Ask harder" → "Press further" rename + mode toggle (PR-E)
5. Typography V1 = labels/headers only; body text untouched (PR-F)
6. Data collection: name-only deferred prompt; no demographics
7. Brand rename "Great Minds" → "The Wise Room" — separate thread, in progress

---

## 1. Pre-Work Investigation Protocol

Unchanged from v12. Defined in `CLAUDE.md` at repo root. Mandatory for all multi-PR work. P-01 through P-06 apply to ALL sessions.

---

## 2. Current architecture

### Chat flow

PATH A SSE streaming endpoint. Real-time streaming added in PR-A (v13). See §changelog PR-A detail.

### Subscription / tier resolution

Unchanged from v12. See v12 §2 for flow diagram. TD-11 (tier consolidation) remains pre-paid-launch requirement.

### Latency topology (from v12)

```
User (Greece) → Netlify CDN → Render Oregon us-west-2
                              → Supabase (Ireland or Oregon — DATABASE_URL switch unconfirmed)

Target post-migration:
User (Greece) → Netlify CDN → Render Oregon → Supabase Oregon (same-region, ~5ms)
```

Oregon migration data: COMPLETE (v12). DATABASE_URL switch: unconfirmed — not addressed in 2026-05-28 session.

---

## 3. Test infrastructure

```
~292+ backend tests (v12 baseline; no new tests added in 2026-05-28 session)
~43+ frontend tests (v12 baseline)
```

No test changes in 2026-05-28 session.

---

## 4. Known limitations and not-yet-wired features

All v12 limitations apply. Additions and updates since v12:

### 4.13 Real-time streaming trade-offs (NEW v13)

See §changelog PR-A for full detail. Trade-offs intentionally accepted:
- Brief Section 5.7 violation window during streaming (~17% of messages)
- 0.1-2s persona content exposure before post-gen safety override
- Mid-stream errors → no retry (partial message shown)
- Regen-also-fails → user sees streamed content; DB saves stripped version

### 4.14 NamePromptCard session-only dismissal (NEW v13)

"Not now" dismissal on NamePromptCard is in-memory only — the card reappears on next session. This is intentional for v1. If repeated prompting becomes user experience friction, add `localStorage` persistence or a `dismissed_name_prompt_at` column in `user_preferences`.

### 4.15 OTP delivery to ote.gr (NEW v13)

OTP codes may not deliver to ote.gr (Greek ISP). See §open-issues #3. Workaround: gmail.

---

## 5. Next session entry point

**Priority order as of 2026-05-28:**

### Phase 0 — Operational cleanup (do before any code PR)

1. **Fix .gitignore** — add `.env.local`, `.env*.local`. Branch `chore/gitignore-env-local`. Single commit. Squash merge.
2. **Smoke test PR-D2** — sign in with gmail, verify NamePromptCard save flow end-to-end.
3. **Investigate OTP-01** — check Render logs for ote.gr delivery failure root cause.

### Phase 1 — Remaining Oregon migration (P0, if not already done)

4. Verify Oregon DATABASE_URL switch status in Render env.
5. If not switched: migrate remaining tables → switch → smoke test → re-ingest source_chunks.
6. If switched: confirm RAG retrieval working post-switch.

### Phase 2 — Brief #1 feature queue

7. **PR-C** — Library F6 spec restoration (1-2 days)
   - Fix duplicate persona name on conversation cards
   - Add last-message snippet (~70 chars + ellipsis)
   - Likely needs backend extension to conversation list endpoint
8. **PR-F** — Typography V1 (2-3 days, labels/headers only)
9. **PR-G** — F2 verification + Sunday counter (2-4 days)
10. **PR-E** — Press further mode toggle (3-4 days)
11. **PR-B** — C9 Bring another mind (4-6 days, biggest)

### Phase 3 — Infrastructure hardening

12. **TD-24** — render.yaml `sync: false` for all secrets + startup health check + alerts

### Phase 4 — Launch track

13. Block B consolidated polish PR
14. Pre-launch items (lawyer review, DNS, GDPR/DPA, runbooks)
15. UAT (≥2/5 spontaneous "I'd pay")

---

## 6. PR history (v12 → v13)

| PR | Description | Date | Status |
|---|---|---|---|
| PR4r | Actual rollback: revert hydration guard, keep api import fix | 2026-05-24/25 | ✅ merged |
| PR4s #108 | Conversation delete P0 fix | 2026-05-24 | ✅ merged |
| PR4t #109 | RitualsCard removed from Today | 2026-05-24 | ✅ merged |
| PR4v #110 | Cleanup: TD-14/15/16 | 2026-05-24 | ✅ merged |
| PR4u #111 | Edge state pages | 2026-05-24 | ✅ merged |
| PR4w | Docs v11 rotation | 2026-05-25 | ✅ merged |
| PR4x #113 | OTP autofill mobile fix | 2026-05-25 | ✅ merged |
| PR4y | Auth redirect → /auth?mode=signin | 2026-05-25 | ✅ merged |
| PR4z | Pull-to-refresh disabled | 2026-05-25 | ✅ merged |
| PR4aa | Titles prompt hardening + backfill | 2026-05-25 | ✅ merged |
| PR4ab | PersonaPickerSheet stuck state + errors + toasts | 2026-05-25 | ✅ merged |
| PR4u2 | Library search empty state card | 2026-05-25 | ✅ merged |
| PR4ad | Today card thumbnail uniformity | 2026-05-25 | ✅ merged |
| PR4ae #120 | Library readability | 2026-05-26 | ✅ merged |
| PR4af #121 | Account scheduled letters card removed | 2026-05-26 | ✅ merged |
| PR4ag1 #122 | Share card v3 + spacebar fix | 2026-05-26 | ✅ merged |
| PR4ah #123 | RitualIcons.tsx + nav tab symbol swap | 2026-05-26 | ✅ merged |
| L1 #124 | Migration 015: 20 btree FK indexes | 2026-05-26 | ✅ merged |
| Bug #1 #127 | BottomSheet history.back race fix | 2026-05-28 | ✅ merged |
| PR-A #128 | Real-time streaming + inline correction (Bug #4) | 2026-05-28 | ✅ merged |
| PR-D #129 | Greeting personalization with first name | 2026-05-28 | ✅ merged |
| PR-D2 #130 | Name capture deferred prompt + PATCH /me | 2026-05-28 | ✅ merged |

---

## 7. Environmental configuration

### Backend (Render)

```
DATABASE_URL                    ⚠️ Status unconfirmed — Oregon switch not addressed in 2026-05-28 session
                                 If Ireland: aws-0-eu-west-1.pooler.supabase.com:5432
                                 If Oregon: aws-0-us-west-2.pooler.supabase.com:5432
                                 Verify in Render dashboard before assuming

REDIS_URL                       ✅ Set (Upstash Pay-as-You-Go as of 2026-05-27)
RESEND_API_KEY                  ✅ Set
FROM_EMAIL                      "Great Minds <onboarding@resend.dev>"
JWT_SECRET                      ✅ Set
ANTHROPIC_API_KEY               ✅ Re-added 2026-05-27/28 (had disappeared — both services updated)
ANTHROPIC_MEMORY_MODEL          "claude-haiku-4-5-20251001"
PHENOMENOLOGY_BRIDGE_ENABLED    ⚠️ State unverified

FRONTEND_URL                    "https://thinkalike.netlify.app"
BETA_GRANT_PRO_TO_ALL           "true" — all users treated as Pro; toggle false before paid launch
GOOGLE_OAUTH_ENABLED            "false"
GOOGLE_CLIENT_ID                (placeholder)
GOOGLE_CLIENT_SECRET            (placeholder)

STRIPE_SECRET_KEY               ✅ Set
STRIPE_WEBHOOK_SECRET           ✅ Set
STRIPE_PRICE_PRO_MONTHLY        ✅ Set — €14.90/mo
STRIPE_PRICE_PRO_YEARLY         ✅ Set — €149/yr
STRIPE_PRICE_PREMIUM_MONTHLY    ✅ Set — placeholder

BASE_URL                        ⚠️ DEPRECATED (PR4k) — safe to remove (TD-14)
ANTHROPIC_MODEL (config.py)     ⚠️ ORPHANED — not read by conversation_service.py (TD-03)
```

⚠️ **render.yaml sync:false NOT YET ADDED.** All secrets above are vulnerable to accidental sync reset until TD-24 is implemented.

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY  ✅ Set
```

---

## 8. Key file paths (production codebase)

### Backend (apps/api/)

All v12 paths apply. Additions since v12:

- `routers/auth.py` — `PATCH /api/v1/auth/me` endpoint (PR-D2 #130)
- `schemas/__init__.py` — `UpdateMeRequest` schema (PR-D2 #130)
- `services/conversation_service.py` — real-time streaming + correction flow (PR-A #128)

### Frontend (apps/web/)

All v12 paths apply. Additions and changes since v12:

- `app/app/(tabs)/today/page.tsx` — Bug #1 fix (#127) + greeting with name (PR-D #129) + NamePromptCard render (PR-D2 #130)
- `app/app/(tabs)/reflections/page.tsx` — Bug #1 fix (#127)
- `components/today/NamePromptCard.tsx` — NEW FILE (PR-D2 #130)
- `lib/useTimeGreeting.ts` — `getGreetingWithName` helper (PR-D #129)
- `lib/api.ts` — `SSEEventCorrection` type + `api.updateMe` method (PR-A + PR-D2)
- `lib/store.ts` — correction state slices + `setUser` setter (PR-A + PR-D2)
- `lib/useStream.tsx` — correction event routing (PR-A #128)
- `components/chat/StreamingBubble.tsx` — correction visual (PR-A #128)
- `app/globals.css` — `@keyframes fade-in` (PR-A #128)

---

## 9. Decision history (v13 additions)

### 2026-05-27 — Upstash Pay-as-You-Go upgrade

Free-tier 500k commands/month limit was hit and crashed the worker. Upgraded to Pay-as-You-Go at $0.2/100k commands. At current cold-beta scale this is negligible cost; will grow proportionally with users.

### 2026-05-28 — Real-time streaming architecture (PR-A / Bug #4)

Old: buffer-then-release (60+ second stalls). New: stream as LLM generates; postprocess in background; correction event if safety check fails. Trade-offs explicitly accepted (see §4.13).

### 2026-05-28 — Rituals scope for launch locked (Option B)

3 functional rituals + 1 placeholder. Mirror and Counterview both editorial (no chat bubbles), house-persona assigned, auto-save to F1. Council Mode deferred to Phase 5 Premium. Full spec in IMPLEMENTATION_BACKLOG_v13.md §9.7.

### 2026-05-28 — Weekly Reading canonized as F3/F4

Weekly Reading is not a new feature — it IS F3/F4 Weekly Letter, renamed and spec-clarified. Single canonical surface: Sunday email + F3 inbox + F4 detail + Rituals tile. Pro-only.

### All prior decisions from v12 §9

Unchanged. See v12/v11/v9/v8 for full history.

---

## 10. Section 5.7 framework — status

Unchanged from v12. All 9 personas have full character config. All elements live.

**Correction copy locked (PR-A):** "Let me put that again." — font-cormorant italic text-[13px] text-sepia. Do not vary.

---

## 11. Migration plan — status

All phases through Block C complete. Unchanged from v12. Oregon migration data complete; DATABASE_URL switch unconfirmed.

---

## 12. Deployment readiness

```
✅ Backend                Render web service philosopher-api
                          philosopher-api-z9l9.onrender.com
                          ✅ Paid Starter tier — no cold-start
                          ✅ ANTHROPIC_API_KEY confirmed re-added 2026-05-27/28

✅ Worker                 Render worker philosopher-worker
                          ✅ Paid Starter tier — no cold-start
                          ✅ ANTHROPIC_API_KEY confirmed re-added
                          ✅ Upstash Pay-as-You-Go (was free, hit limit 2026-05-27)

⚠️ Database               STATUS UNCONFIRMED
                          alembic_version = '015_add_fk_indexes'
                          Oregon data migration complete (v12); DATABASE_URL switch unconfirmed.
                          Verify in Render env before proceeding with Oregon-dependent work.

🟡 Oregon migration       bvzeuwzqgnqcghvqghtb (us-west-2)
                          Data: ✅ schema + ref data. 🟡 user/app tables partial.
                          DATABASE_URL switch: ⚠️ unconfirmed.
                          source_chunks re-ingest: pending (TD-22).

🟡 Redis (Upstash)        ✅ Pay-as-You-Go ($0.2/100k commands)
                          ⚠️ 80% quota alert not yet set up

🟡 Email                  Resend free tier (test sender)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS
                          ⚠️ OTP delivery failing to ote.gr (investigation pending)

✅ Frontend (canonical)   Netlify thinkalike.netlify.app

✅ LLM                    Anthropic API wired (real-time streaming + correction flow live)

✅ Stripe                 Sandbox wired. End-to-end test pending.

🟡 Google OAuth           Dormant (GOOGLE_OAUTH_ENABLED=false).

🟡 Rituals email delivery Letter DB schema live; ARQ delivery not wired.
```

---

## 13. Session lessons (v13 additions)

### 13.1–13.9 Preserved from v12

See v12 §13 for full text. Key rules: P-01 through P-06 in CLAUDE.md.

### 13.10 Upstash free-tier quota is a silent failure mode (NEW v13 — 2026-05-27)

Upstash free tier (500k commands/month) hit limit → worker crashed silently. No alert, no visible error to the user on the frontend — chat appeared to work but title generation and memory extraction were failing in the background. 

Lesson: set up 80% quota alert immediately after upgrading to any metered plan. Quota exhaustion on a production dependency is effectively a silent outage.

### 13.11 Env var disappearance is a real production risk (NEW v13 — 2026-05-27/28)

ANTHROPIC_API_KEY disappeared from BOTH Render services between May 25-27. The production app was broken (all chat failing) for an unknown window. Root cause unconfirmed — possibly a `render.yaml` blueprint sync that overwrote env vars.

Two lessons:
1. `render.yaml` needs `sync: false` for ALL secrets to prevent accidental overwrite (TD-24).
2. A startup health check that verifies required env vars on boot would have surfaced this failure immediately instead of silently.

### 13.12 OTP delivery is provider-dependent (NEW v13 — 2026-05-28)

OTP to nkoutr@ote.gr failed before the DB insert step — meaning Resend rejected or rate-limited the delivery at the API call level. ote.gr is a Greek ISP; deliverability through Resend's test sender is unverified.

Lesson: test all email flows with a major-provider address (gmail, outlook) during cold beta. ISP-hosted addresses may have deliverability issues that don't surface until real users try to sign in. This is especially important before flipping to a custom domain sender.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v12. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. P-01 through P-06 apply to ALL sessions.

### The most important context for the next session

**Three things in order:**

1. **Fix .gitignore first.** Production secrets are one `git add -A` away from the public repo. This is the highest-priority item — above all feature work.

2. **Oregon migration DATABASE_URL switch is unconfirmed.** Check Render env before doing any work that assumes Oregon is live. If the switch happened silently (possible given the ANTHROPIC_API_KEY incident), the latency picture has already changed. If it didn't, completing it is the highest-leverage infrastructure change remaining.

3. **PR-D2 smoke test is incomplete.** The name-save flow hasn't been verified end-to-end in production. Use gmail for OTP, sign in, confirm NamePromptCard appears (user must have null `full_name`), save name, confirm greeting personalizes. This is a 5-minute check.

After those three: the brief sequence in §5 Phase 2 (PR-C → PR-F → PR-G → PR-E → PR-B) is the path to launch.

### Documentation hygiene

v13 baseline regen triggered by session volume (4 PRs, 2 production incidents, 7 strategic decisions locked). Next baseline regen threshold: major architecture change OR similar session volume. Until then, append `*_v13_ADDENDUM_<date>.md` instead of rewriting v13.

### Launch timeline from here

Realistic from end of 2026-05-28 session: 8-12 weeks.
- Brief #1 complete (PR-C, PR-F, PR-G, PR-E, PR-B): ~3 weeks
- Brand rename merged: ~1-2 weeks parallel
- Briefs #2-#5 complete: 6-9 weeks
- Cold beta + Stripe live + DNS cutover: 2-3 weeks
- **Target: early-to-mid August 2026.**

---

**End of HANDOFF_BRIEF v13.** Authoritative as of 2026-05-28. Supersedes `HANDOFF_BRIEF_v12.md` (preserved as historical reference). Where v13 conflicts with v12, v13 wins.
