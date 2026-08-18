# GREAT MINDS — Screens Tracking v13

> **Purpose:** Full screen inventory of the Great Minds / The Wise Room product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **v13 adds ZERO new screens** — VERIFIED: across `#522..#548`, `git diff --name-status` over `apps/web` reports **1** added file total (`lib/__tests__/refreshSession.test.ts`, a test) and **0** added `page.tsx` files. The delta is defect fixes on existing screens plus backend work.
>
> **⚠️ This file replaces an earlier, never-merged `SCREENS_TRACKING_v13.md`.** See §0.
>
> **Last updated:** 2026-08-18 (v13). **Current main `cace1016`.**
>
> **Companion documents:** `DESIGN_SYSTEM_v4.md` (+ `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`), `USER_FLOW_v4.md`, `IMPLEMENTATION_BACKLOG_v25.md`, `PROJECT_STATE_v25.md`.

---

> ## ⚠️ PROVENANCE
>
> **Every claim here is either VERIFIED THIS ROTATION with its method, or explicitly MARKED UNVERIFIED / UNCARRIED.** "Unchanged." is not used as evidence.
>
> **Verification SHA `cace1016`.** Methods: live code reads at that SHA; `git diff --name-status f8ced63d~1..cace1016 -- apps/web` to derive the exact set of touched surfaces; **executed** `vitest` and `tsc` for the test/typecheck numbers.
>
> **⚠️ The screen-count total is UNCARRIED.** Prior docs state 79. **This rotation verified that the delta adds zero screens, but did not re-derive the 79 baseline.** Treat the total as unverified; treat "no screens added this rotation" as verified.
>
> **⚠️ EVERY user-facing fix listed below is LIVE IN PRODUCTION AND HAS NEVER BEEN SEEN BY A HUMAN.** Eighteen of them. They are verified by unit tests and code reading only.
>
> **This rotation's own PR number is deliberately not asserted.** See §0.

---

## 0. Why this file replaces one with the same name

**The v25 doc rotation was written 2026-08-06 and never merged** — it exists only on the local, unpushed branch `docs/v25-rotation` @ `b15811c0`. `docs/` on `main` stopped at `SCREENS_TRACKING_v12`.

That rotation also asserted, four times, that **"#529 is this rotation (docs only)"**. #529 is `16b213a7`, a product PR that changed the system prompt (UAT A7). A document written to catalogue unverified copied-forward claims made a false claim about a **PR that did not exist yet**.

**Rule now in force:** a rotation document states the range it covers, and never asserts the number, content or existence of its own PR or any unmerged PR.

The old branch was **mined, not merged**.

---

## Changelog v12 → v13 (2026-07-19 → 2026-08-18, `#522–#548`)

Every entry below names the file actually changed, read at `cace1016`.

**Invisible but behaviour-defining:**

- **Chat context window — three PRs (C1; #522, #532, #533).** #522: all three chat paths fetched the **oldest** N messages instead of the newest, so past turn N the persona never saw its own recent output — a tester quoted its previous sentence back and was told *"I didn't say that — you did."* #532: a cache breakpoint on the message history. #533: the sliding window replaced by a **growing, budget-bounded** one. **⚠️ The "window 5 / window 20" framing in v12 and earlier is superseded — do not carry those numbers forward.**
- **Safety record now covers ritual surfaces (#548).** Council, counterview, counterview-rebuttal, self-comparison and scheduled email now write `SafetyEvent` rows; previously chat was the only writer. **No visual change.** ⚠️ **The mirror ring-true note is still not checked at write time — A18c, open.**

**Visible copy and behaviour:**

- **Letters — write-back copy made honest (H/letters, #531).** The panel implied the app would read and answer the reply. It does not: the write-back is stored and re-injected as `<reader_wrote_back>` into the next letter. The system was right; the copy was not. `WriteBackPanel.tsx` +1/−1.
- **Letters — write-backs survive (H/letters, #534, #541, #538).** A write-back was orphaned whenever the weekly voice was re-elected (the prior-letters fetch is scoped to this week's voice; the voice is re-elected weekly from the trailing 7 days). Fixed weekly (#534) and monthly (#541); write-backs now also feed the memory pipeline (#538). `letters/[id]/page.tsx` +1, `WriteBackPanel.tsx` +34.
- **Letters — a ritual-only week now counts (H/letters, #545, #547).** The 2026-08-16 dispatch enqueued **zero** letters: the one active user had spent the week entirely in rituals with 0 chat messages, and eligibility counted only `Message` rows. **The user-visible effect was the letter simply not arriving.**
- **Session no longer expires under an active user (A-auth, #535).** Expiry ran from **issue**, not last use — a user opening the app daily was logged out on day 7 and had to re-verify by email code. `QueryProvider.tsx` +32, `lib/api.ts` +32, `lib/store.ts` touched.
- **Sign-out now actually revokes (A-auth, #543).** Previously client-side only; the JWT stayed valid until natural expiry. Now increments `users.token_version` and every token on every device dies.
- **Paywall shows a real reset time (C5 / F1 / G12, #536, #540).** Every free user at a cap saw *"resets today at «the current time»"* and a limit of 0 — on the conversion surface. The API had been sending correct `X-RateLimit-*` values all along; `CORSMiddleware` had no `expose_headers`, so cross-origin JavaScript could never read them and six call sites in `lib/api.ts` silently fell back. #540 added the missing header on council and you-vs-you. `you-vs-you/page.tsx`, `PaywallModal.tsx` touched.
- **Council answers the person, not the text (I/council, #530).** A pasted Machiavelli line reached each member as a bare user turn, so three of four opened by establishing identity — *"That line is not mine. It belongs to Machiavelli."* The matter is now framed as a person's matter.
- **The persona no longer announces it is an AI (C1, #529).** Asked to answer from his own experience, Jung replied that he is an AI and not the actual person — then spoke in character about his life a few turns later. The prompt line was a boundary written as a proposition, so the model discharged it by **saying** it.
- **Pricing strings aligned (upgrade / legal, #539).** `€99.99 / year` (`upgrade/page.tsx:56`), `€11.99 / month` (`:77`), Terms billing sentence (`terms/page.tsx:65`). **⚠️ The Stripe price objects still hold the old amounts (OPS-006) — the app displays one price and would charge another.**

**No new screens. No dependency changes beyond a lockfile sync.**

> **Changelog v11 → v12:** deep-mode chip-row toggle + free metering; ritual/insight door chips; Council edited-matter flow; Explore hub copy + "The portrait"; Memory arc; Reflections feed 500 fix; counterview free cap; prompt caching. See `SCREENS_TRACKING_v12.md`.

---

## Inventory

Sections not named below are **UNCARRIED** — not re-verified this rotation, so not restated. See `SCREENS_TRACKING_v12.md` and treat that content as unverified.

### A — Authentication & First-time user

| ID | Screen | Status |
|---|---|---|
| A-auth (session) | Sign-in / session lifecycle | ✅ covered. **v13: session survives an active user (#535) — `POST /auth/refresh` called on app load and on foreground return, throttled to 12h. Sign-out now revokes every token on every device (#543).** |
| A-auth (entry) | **Sign-in screen — login vs signup** | ⚠️ **OPEN DEFECT — UAT A8.** The screen does not distinguish logging in from signing up. The tester **created three accounts by accident**. See "A8 — the screen defect with a data consequence" below. |

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered. **v13: the context window is now growing and budget-bounded (#533), after being fixed from oldest-N to newest-N (#522) and cache-anchored (#532). The persona no longer announces being an AI (#529). Rate-limit paywalls show a real reset time (#536).** Carries v12 deep-mode metering, ritual door chips, prompt caching. |
| C2–C9 | (loading / save / retry / limit / offline / safety / greeting / bring-another-mind) | ✅ covered. **v13: every rate-limit path now receives readable `X-RateLimit-*` headers (#536), so C5's reset time is real rather than "now".** |

### G — Rituals (Phase 3)

| ID | Screen | Status |
|---|---|---|
| G12 | You vs You | ✅ covered. **v13: the weekly-limit 429 now carries `X-RateLimit-Reset` (#540), so the meter and paywall show a true reset.** |
| G-council | Council | ✅ covered. **v13: the matter is framed so members counsel the person, not the text (#530).** |
| G-mirror | Mirror — ring-true note | ⚠️ **OPEN DEFECT — A18c.** The note is persisted **unchecked**. `routers/mirrors.py` contains **1** occurrence of "safety" and it is a comment at `:100` about a *downstream* task; there is **no safety call in the file**; `ring_true_note` is written at `:93`. **⚠️ Sibling: `routers/self_comparison.py` has 0 occurrences of "safety" and the same unchecked write at `:101`. Two ring-true surfaces, one reported — fix both or repeat the A17 → A17b pattern.** |

### H — Letters (weekly / season)

| ID | Screen | Status |
|---|---|---|
| H1 | Weekly letter | ✅ covered. **v13: survives malformed LLM JSON (#544) — a 2026-08-09 incident lost a fully-written letter to an unescaped quote while the job reported `j_failed=0`. A ritual-only week now qualifies (#545) — the 2026-08-16 dispatch had sent zero letters to the most active week on record.** |
| H2 | Season (monthly) letter | ✅ covered. **v13: same JSON resilience and same ritual-aware eligibility (#547); monthly write-backs survive to the next season letter (#541).** |
| H3 | Write-back panel | ✅ covered. **v13: copy no longer promises a reply the system never gives (#531); the write-back now reaches the next letter regardless of a voice re-election (#534) and feeds the memory pipeline (#538).** |

### Upgrade / Legal

| ID | Screen | Status |
|---|---|---|
| U1 | Upgrade page | ✅ covered. **v13: €11.99/month, €99.99/year (#539). ⚠️ Displayed price and Stripe price object disagree — OPS-006.** |
| L1 | Terms | ✅ covered. **v13: billing sentence aligned to the locked pricing (#539).** |

### B / D / E / F / I / J / K

**UNCARRIED** — not re-verified this rotation. See `SCREENS_TRACKING_v12.md`.

---

## A8 — the screen defect with a data consequence

**The sign-in screen does not distinguish login from signup.** The tester created **three accounts by accident**. **Open and unfixed.**

**Consequence, verified by live query this cycle:** her activity is **split across two accounts** — a yahoo address (her real, primary account) and a gmail address (the accidental one). On **2026-08-09** a weekly letter was generated for the **accidental** account. Her real account received **none**.

This is not an onboarding polish item. The product's central weekly ritual was delivered to an account its owner did not know she had, while her real account looked inactive. From the inside, it reads as the letters feature not working.

> **Three of this rotation's defects (A17 silent letter loss, A18 zero-letter dispatch, A8 misrouted letter) all end with "the user received nothing", and all three were found by querying data — none by a person using the app.** Nothing currently watches whether letters arrive.

---

## Test and typecheck state for the screen layer — executed at `cace1016`

Both numbers were produced by running the tools on this machine at this SHA. (For the record: the prior doc stated no Node runtime existed here. Node **v20.18.1** / npm **10.8.2** are at `C:\clwn\node-v20.18.1-win-x64`.)

- **`vitest`: 62 failed / 54 passed (116 tests), 16 of 24 files failing.**
- **`tsc --noEmit`: 11 errors — 4 production, 7 test-file.** Production: `app/app/(tabs)/account/page.tsx:112,114,117` (TS18047) and `app/auth/oauth/finish/page.tsx:33` (TS2345). **The previously stated "8 production errors" was wrong.**

**49 of the 62 failures are one config line (TD-51).** `apps/web/vitest.config.ts` contains **0** occurrences of `globals: true`, so `@testing-library/react`'s auto-cleanup guard (`if (typeof afterEach === 'function')`) never fires; `cleanup()` appears **0** times anywhere in `apps/web`. Every `render()` leaves a container in `document.body`, and `screen.*` queries see all prior renders — hence the cascade of "found multiple elements" failures.

**The 49 / 13 split is VERIFIED, not attributed.** Method: `npx vitest run` executed at `cace1016` **twice**, with and without `globals: true` — **62 failed / 54 passed (16 of 24 files) → 13 failed / 103 passed (6 of 24 files)**.

The remaining **13** are stale assertions against components that have since changed, and they are screen-layer facts worth reading here: `EmptyReflections` copy, `DateGrouper` styling, the `QuickActionsRow` "Ask harder" chip (a chip that no longer exists), the `SavedLineCard` portrait fallback, and 3 in `chat/conv/[id]`. **None of the 62 indicates a real product defect** — they are a test-config gap plus drift between tests and shipped copy. The 13 are a separate PR from the one-line config fix.

---

## ⚠️ Process note — P-04 was in scope this rotation

`#535` touched **`lib/store.ts`**, **`components/ui/QueryProvider.tsx`** (a layout-level provider) and **`lib/api.ts`** — three of the five categories `CLAUDE.md` **P-04** names as requiring **preview-deploy validation before merge**, because unit tests and code review are explicitly not sufficient for them.

**Whether a preview deploy was run for #535 is UNVERIFIED** — there is no record of it in the commit or the repo. P-04 exists because `PR4p` had passing unit tests and a clean review and still broke production, since `onRehydrateStorage` timing differs between local dev and the production Next.js build. **This is worth confirming before the next store/auth change, not after.**

---

## App icon — deferred

**UNCARRIED** (TD-29) — not re-verified this rotation. See `SCREENS_TRACKING_v7.md`.

---

**End of SCREENS_TRACKING v13.** Authoritative as of 2026-08-18 at `cace1016`. Supersedes `SCREENS_TRACKING_v12.md` (preserved byte-identical). Replaces the never-merged `docs/v25-rotation` draft, which was mined for re-verifiable claims and not merged.
