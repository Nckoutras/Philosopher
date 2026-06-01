# HANDOFF BRIEF v15 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-01
**Prior version:** `docs/HANDOFF_BRIEF_v14.md` (2026-05-30)
**Generated:** 2026-06-01 (v15 rotation)

**Block trigger for v15 baseline regen:** Mirror feature shipped end-to-end (PRs #166–#173, 2026-06-01). Weekly "said → meant" reflection artifact: generator task, idempotent cron (weekly + preview), eligible-host config, ring-true feedback loop, host picker UI. Migrations 017 + 018. Session volume sufficient for rotation.

**v15 baseline (2026-06-01):** Mirror ✅ COMPLETE. Oregon DB confirmed live. BETA_GRANT_PRO_TO_ALL still enabled — top revenue-gate blocker. Next: Stripe checkout smoke test (with BETA off) → Rituals guided programs.

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
- Typography PR-F ✅ COMPLETE (2026-05-29)
- C9 "Bring another mind" / PR-B ✅ COMPLETE (2026-05-29) — Pro-gated; cross-mind awareness shipped
- Voice overhaul ✅ COMPLETE (2026-05-30) — check_brevity live; ending-variation rule; Socrates elenchus; all 9 personas tightened
- **The Mirror ✅ COMPLETE (2026-06-01)** — PRs #166–#173; generator + idempotent cron + host picker + ring-true; migrations 017 + 018; eligible-host config locked; end-to-end verified
- Oregon region migration ✅ CONFIRMED LIVE — bvzeuwzqgnqcghvqghtb (us-west-2); Ireland project legacy/inactive
- Upstash ✅ Pay-as-You-Go (upgraded 2026-05-27)
- ANTHROPIC_API_KEY ✅ Re-added to both services (2026-05-27/28)

> **v15 conflict resolution rule:** Where v15 conflicts with v14 or earlier, v15 wins. Production reality always wins over docs.

## v15 Session Delta (2026-06-01)

> v15 = v14 baseline + Mirror feature shipped. Where v15 conflicts with v14, v15 wins.

**Shipped (all squash-merged to main, PRs #166–#173):**

- **The Mirror** — weekly "said → meant" reflection artifact, end-to-end live & verified. Full detail in `PROJECT_STATE_v15.md §v15 Session Delta`.

**Key superseded facts:**
- `alembic_version` = **`018_user_mirror_host`** (was `016_message_persona_id`). Two new migrations: `017_create_mirrors` + `018_user_mirror_host`.
- Mirror status: 🔴 BLOCKED → **🟢 SHIPPED**.
- Live DB: Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). Ireland `plecolxlzshkfvybszgs` = **legacy / inactive**.
- 4 new endpoints: `GET /mirrors/latest`, `POST /mirrors/{id}/ring-true`, `GET /mirrors/hosts`, `POST /mirrors/host`.
- MIRROR_PROMPT is **separate from `prompt_builder.py`** (chat path). Verdict-guard is Mirror-only.

**PRE-LAUNCH BLOCKER logged:** `BETA_GRANT_PRO_TO_ALL=true` must be disabled before Stripe revenue is live. Requires TD-11 first.

---

## v14 Session Delta (2026-05-29)

> v14 = v13 baseline + 2026-05-29 session. Where v14 conflicts with v13, v14 wins.

**Shipped this session (all squash-merged):**
- **Typography PR-F** (`feat/typography-v1`, `feat/typography-phase2`) — chat reading text → 16px; Cormorant titles → font-medium (500); comprehension prose → 15px. Final scale: chat 16 / titles 500 / comprehension 15 / saved-lines 17 / chrome unchanged.
- **PR-B / C9 "Bring another mind"** (headline Pro feature) — mid-chat second opinion from another persona; the guest reply renders inline; the conversation continues with the home persona. Five PRs: backend engine (`feat/pr-b1-another-mind-backend`, #71ce6e3), picker + streaming UI (`feat/pr-b2-another-mind-ui`, #ff37f36), gate bugfix (`fix/another-mind-gate-backend-authority`, #225a68d), attribution (`feat/pr-b3-brought-in-attribution`) + live attribution (`feat/pr-b3v2-live-attribution`). Live-tested OK.
- **Cross-mind awareness** (`feat/cross-mind-awareness`, #cea8f29) — a persona now recognises a brought-in guest's words instead of mistaking them for its own. LLM history labels turns by another mind as "[Name]: ..."; a `CROSS_MIND_NOTE` is appended only when such turns exist; symmetric; the home path is byte-identical when no brought-in turns exist. No schema/SSE/storage change.

**Supersedes prior facts:**
- `alembic_version` is now **`016_message_persona_id`** (was `015_add_fk_indexes`). Migration 016 = nullable `messages.persona_id` FK → personas.id + index `ix_messages_persona_id`.
- New endpoint **POST /api/v1/conversations/{id}/another-mind** (SSE; Pro-gated → 403 `upgrade_required`; same-persona → 400; rate-limited to target). The single-home-send-endpoint statement still holds for the home path; this is a distinct additive endpoint.
- `conversation_service.py` now has TWO streaming entrypoints: `stream_response` (home) + `stream_another_mind` (guest); both apply cross-mind history labelling.

**File paths (additions/changes):**
- Backend: `db/migrations/versions/016_message_persona_id.py` (NEW), `models/__init__.py` (Message.persona_id + persona rel), `schemas/__init__.py` (MessageOut.persona_slug, AnotherMindCreate), `routers/conversations.py` (persona eager-load + persona_slug; POST /another-mind), `services/conversation_service.py` (stream_another_mind; `_build_lm_messages` / `CROSS_MIND_NOTE`).
- Frontend: `lib/api.ts`, `lib/useStream.tsx`, `lib/store.ts` (streamingBroughtInName), `components/chat/AnotherMindSheet.tsx` (NEW), `StreamingBubble.tsx`, `MessageList.tsx`, `QuickActionsRow.tsx`, both chat pages; typography across MessageBubble/SafetyBubble/ErrorMessage + ~21 titles + 11 comprehension lines.

**Newly logged items:**
- 🔴 **Systemic frontend `plan` reliability bug** — client `plan` getter unreliable on any route outside `(tabs)/layout.tsx` (where `SubscriptionBootstrap` runs); affects all client-side plan gates. Fix before paid launch. Ties to TD-11.
- 🟡 **Another-mind feature gate (post-beta)** — backend gates per-persona, NOT feature-level. Add a feature-level Pro gate before turning off `BETA_GRANT_PRO_TO_ALL`.
- ⏸ **Enhancement — switch to the brought-in mind** (persona switching mid-conversation). Post-validation only.

**Status:** C9 / PR-B COMPLETE; cross-mind awareness COMPLETE; typography PR-F COMPLETE. Critical path to revenue (unchanged, still open): cold-beta validation → live Stripe → TD-11 + another-mind feature gate → paid launch.

---

## v14 Addendum — Voice Overhaul (2026-05-30)

> Appended to v14 baseline. Where this conflicts with earlier v14 content, this addendum wins.

**Shipped this session (all merged to main):**

- **`check_brevity` wired into live post-stream path** — previously dead code; word bands were never enforced at runtime. Enforcement is now active for all 9 personas.
- **Global ending-variation rule (`system_base.jinja2`)** — ~40% question / ~40% no-question / ~20% mixed endings. Carve-out: personas whose own `ResponseSpec` mandates a question are exempt from the no-question bucket.
- **Socrates elenchus cycle** — upgraded from "exactly one question, no exceptions" (contradicted the elenctic method) to the full cycle: ask → synthesise → expose contradiction. Biography gated under ANTI-FLEXING.
- **All 9 personas tightened** — bands + 2026-voice bullets + ANTI-FLEXING bullets + `voice_calibration_examples` added for: Marcus Aurelius, Socrates, Epictetus, Oscar Wilde, Carl Jung, Sigmund Freud, Simone de Beauvoir, Niccolò Machiavelli, Lao Tzu. Each persona's cognitive signature preserved.

**Critical gap closed:**
Oscar Wilde, Niccolò Machiavelli, and Lao Tzu previously had **no `ResponseLengthSpec`** — `check_brevity` was skipped entirely for them. Now all 9 personas have specs; brevity enforcement is universally active.

**Per-persona word bands (from source):**

| Persona | standard (min–max) | first (max) | reflective (max) |
|---|---|---|---|
| Marcus Aurelius | 20–55 | 40 | 75 |
| Socrates | 20–55 | 35 | 70 |
| Epictetus | 20–55 | 35 | 70 |
| Oscar Wilde | 20–55 | 40 | 75 |
| Carl Jung | 25–60 | 40 | 80 |
| Sigmund Freud | 25–60 | 40 | 80 |
| Simone de Beauvoir | 30–65 | 50 | 90 |
| Niccolò Machiavelli | 25–60 | 40 | 80 |
| Lao Tzu | 15–45 | 35 | 70 |

**Pending author smoke-test (voice changes live, not yet author-tested):**
Oscar Wilde, Carl Jung, Sigmund Freud, Simone de Beauvoir, Niccolò Machiavelli, Lao Tzu.

---

## Top of mind / Next (2026-06-01)

### Mirror is shipped. What's next.

**Priority order as of 2026-06-01:**

1. **Stripe checkout smoke test + disable `BETA_GRANT_PRO_TO_ALL`** — revenue gate. Must run TD-11 (tier resolution refactor) first. Then flip BETA flag off. Then test Stripe checkout end-to-end with a real test card. This is the highest-leverage item before public launch.

2. **Rituals guided programs** — Counterview + remaining guided program specs. Scope NOT YET DESIGNED. User-stated need: purpose/progress, not more chat. The Mirror is the first ritual artifact; Counterview is the second (spec §1.3.2 — locked in Option B but implementation not designed). Design with Claude (chat) before any build brief.

3. **Mirror fast-follows** (post-first-paying-user, NOT before):
   - Branded email postcard (host's closing words + thumbnail + date; reuse Resend infra)
   - Host-aware handoff: "Continue with {host}" CTA → reuse existing `CROSS_MIND_NOTE` pattern
   - Smart input cap on Mirror generator (cost control at scale; never crude truncation)

### Still-pending from prior sessions

- `.gitignore` security debt — **must fix before any code PR** (branch `chore/gitignore-env-local`)
- Author smoke-test voice changes — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu
- PR-D2 production smoke test — use gmail workaround
- OTP-01 (ote.gr delivery failure) — investigate Render logs

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

**Priority order as of 2026-06-01:**

### Phase 0 — Operational cleanup (do before any code PR)

1. **Fix .gitignore** — add `.env.local`, `.env*.local`. Branch `chore/gitignore-env-local`. Single commit. Squash merge.
2. **Smoke test PR-D2** — sign in with gmail, verify NamePromptCard save flow end-to-end.
3. **Investigate OTP-01** — check Render logs for ote.gr delivery failure root cause.
4. **Author smoke-test voice changes** — test Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu in production (voice changes live, author-testing pending).

### Phase 1 — Revenue gate [HIGHEST PRIORITY]

5. **TD-11 — Tier resolution unified refactor** — consolidate `get_current_user_plan` + `get_user_tier` into a single function. Required before BETA flag can be safely disabled.
6. **Disable `BETA_GRANT_PRO_TO_ALL`** — set to `false` in Render env after TD-11 is deployed. Verify no enforcement breakage.
7. **End-to-end Stripe sandbox test** — test card → webhook → entitlement → portal → cancel → tier downgrade. Must be run with BETA flag OFF.

### Phase 2 — Rituals guided programs [retention]

8. **Design session with Claude (chat)** — Counterview spec + guided program flows. Scope NOT YET DESIGNED. Do not dispatch a build brief until design is complete.
9. **Investigate `insights` table** — exists in live DB (0 rows); likely leverage point for progress payoff. Determine why the generator is not running before designing around it.

### Phase 3 — Mirror fast-follows (post-first-paying-user)

10. Branded email postcard — reuse Resend infra.
11. Host-aware handoff — reuse `CROSS_MIND_NOTE` pattern.
12. Smart input cap on Mirror generator — cost control at scale.

### Phase 4 — Remaining Brief #1 queue

13. **PR-C** — Library F6 spec restoration (1-2 days)
14. **PR-G** — F2 verification + Sunday counter (2-4 days)
15. **PR-E** — Press further mode toggle (3-4 days)

### Phase 5 — Infrastructure hardening

16. **TD-24** — render.yaml `sync: false` for all secrets + startup health check + alerts

### Phase 6 — Launch track

17. Block B consolidated polish PR
18. Pre-launch items (lawyer review, DNS, GDPR/DPA, runbooks)
19. UAT (≥2/5 spontaneous "I'd pay")
20. Cold validation with external users (retention + willingness-to-pay)

---

## 6. PR history (v12 → v15)

| PR | Description | Date | Status |
|---|---|---|---|
| #166 | Mirror: prompt shape | 2026-06-01 | ✅ merged |
| #167 | Mirror: voice | 2026-06-01 | ✅ merged |
| #168 | Mirror: idempotent generator + migration 017_create_mirrors | 2026-06-01 | ✅ merged |
| #169 | Mirror: weekly + preview cron jobs | 2026-06-01 | ✅ merged |
| #170 | Mirror: universal verdict-guard in MIRROR_PROMPT | 2026-06-01 | ✅ merged |
| #171 | Mirror: host storage + eligible-hosts + set-host endpoints + migration 018 | 2026-06-01 | ✅ merged |
| #172 | Mirror: weekly cron uses each user's chosen host | 2026-06-01 | ✅ merged |
| #173 | Mirror: host picker — tappable header + bottom sheet | 2026-06-01 | ✅ merged |
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
DATABASE_URL                    ✅ Oregon — aws-0-us-west-2.pooler.supabase.com:5432
                                 Project: bvzeuwzqgnqcghvqghtb (us-west-2) — CONFIRMED LIVE
                                 Ireland project plecolxlzshkfvybszgs (eu-west-1) = LEGACY / INACTIVE

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
                          alembic_version = '016_message_persona_id'
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

### 13.13 `get_db` auto-commits on success; flush-only persists within transaction (NEW v15 — 2026-06-01)

SQLAlchemy `db.flush()` persists changes to the DB within the current transaction (the row is readable in the same session) but does NOT commit. The `get_db` FastAPI dependency auto-commits on successful request completion. Do not call `db.commit()` manually inside service functions — let the dependency handle it. If you need the record ID before the response returns, use `db.flush()` + `db.refresh(obj)`.

### 13.14 MIRROR_PROMPT and `prompt_builder.py` are separate execution paths (NEW v15 — 2026-06-01)

The Mirror uses its own prompt template (MIRROR_PROMPT) and is generated by a dedicated ARQ task (`generate_weekly_mirror_task`). `prompt_builder.py` is for normal chat only. Changes to one path do not affect the other. The verdict-guard in MIRROR_PROMPT is Mirror-specific — it does not apply to persona chat responses.

### 13.15 SVG open paths require `fill="none"` (NEW v15 — 2026-06-01)

When using SVG `<path>` elements that form open curves (not closed loops), set `fill="none"` explicitly. Without it, mobile Safari fills the open area with the current colour, producing unexpected artefacts. Applies to any decorative SVG in Mirror or chat UI.

### 13.16 Optimistic UI catch can silently hide write failures (NEW v15 — 2026-06-01)

If a frontend update uses optimistic UI (state updated before API confirms) and the error path is swallowed by a silent `catch`, the UI looks correct even when the API write fails. Always verify that writes landed in the DB during smoke tests — not just that the UI looks right.

### 13.17 Live DB is Oregon — always inspect the Oregon project (NEW v15 — 2026-06-01)

Production DATABASE_URL points to Supabase Oregon `bvzeuwzqgnqcghvqghtb` (us-west-2). The Ireland project `plecolxlzshkfvybszgs` is legacy and inactive. All Supabase console work (migration verification, row counts, query inspection) must be done in the Oregon project.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v12. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. P-01 through P-06 apply to ALL sessions.

### The most important context for the next session

**Three things in order:**

1. **Fix .gitignore first.** Production secrets are one `git add -A` away from the public repo. This is the highest-priority item — above all feature work.

2. **Disable `BETA_GRANT_PRO_TO_ALL` before any Stripe test.** The flag is currently `true` — all users are granted Pro for free. Revenue cannot be validated until this is off. TD-11 (tier resolution refactor) must land first.

3. **PR-D2 smoke test is still incomplete.** The name-save flow hasn't been fully verified end-to-end in production. Use gmail for OTP, sign in, confirm NamePromptCard appears (user must have null `full_name`), save name, confirm greeting personalizes. This is a 5-minute check.

After those three: the revenue gate (§5 Phase 1) is the critical path.

### Documentation hygiene

v15 rotation triggered by Mirror feature shipping end-to-end (8 PRs, 2 migrations, major new feature complete). Next baseline regen threshold: major architecture change OR similar session volume. Until then, append `*_v15_ADDENDUM_<date>.md` instead of rewriting v15.

### Launch timeline from here

Realistic from end of 2026-06-01 session: 6-10 weeks.
- Revenue gate (TD-11 + BETA off + Stripe test): ~1-2 weeks
- Rituals guided programs (Counterview + guided programs): ~3-5 weeks
- Cold beta + DNS cutover: 2-3 weeks
- **Target: mid-to-late July 2026.**

---

**End of HANDOFF_BRIEF v15.** Authoritative as of 2026-06-01. Supersedes `HANDOFF_BRIEF_v14.md` (preserved as historical reference). Where v15 conflicts with v14, v15 wins.
