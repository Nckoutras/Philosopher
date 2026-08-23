# GREAT MINDS — Screens Tracking v14

> **Purpose:** Screen inventory for The Wise Room. Covered (✅) or pending (⚠️).
>
> **v14 adds ONE screen** — `app/auth/welcome/page.tsx` (#553). **VERIFIED:** across
> `#549..#563`, `git diff --name-status cace1016..ef3e2d89 -- apps/web` reports **1** added
> `page.tsx` and **3** modified. v13 added none; v14 adds one — so v13's "zero new screens"
> framing does not carry to this cycle.
>
> **Range covered:** `#549` … `#563`. **Verification SHA:** `ef3e2d89`. **Date:** 2026-08-23.
>
> **Companion documents:** `PROJECT_STATE_v26.md`, `IMPLEMENTATION_BACKLOG_v26.md`,
> `HANDOFF_BRIEF_v26.md`. `DESIGN_SYSTEM_v4.md` and `USER_FLOW_v4.md` are UNCARRIED.

---

> ## ⚠️ PROVENANCE
>
> **Every claim is VERIFIED THIS ROTATION with its method, or MARKED UNVERIFIED /
> UNCARRIED.** "Unchanged." is not used as evidence.
>
> **Methods:** `git diff --name-status cace1016..ef3e2d89 -- apps/web` for the touched set;
> `find apps/web/app -name page.tsx | wc -l` for the file count; direct reads of each
> changed screen; **executed** `vitest` and `tsc`.
>
> **⚠️ The screen-count total remains UNCARRIED.** Prior docs state 79; v13 did not
> re-derive it and neither did this rotation. What *is* verified: **42** `page.tsx` files
> exist, and this range adds exactly **1**. Treat 79 as unverified; treat the delta as
> measured.
>
> **⚠️ Every screen change below is LIVE IN PRODUCTION AND HAS NOT BEEN SEEN BY A HUMAN
> USING THE APP.** Four surfaces. They are verified by unit tests and code reading only.
> This is the same standing gap v13 recorded, unchanged in substance.
>
> **This rotation's own PR number is deliberately not asserted.**

---

## Changelog v13 → v14 (`#549` … `#563`)

The complete `apps/web` delta, from `git diff --name-status`:

| Change | File | PR |
|---|---|---|
| **A** | `app/auth/welcome/page.tsx` | #553 |
| M | `app/auth/verify/page.tsx` | #553 |
| M | `app/auth/oauth/finish/page.tsx` | #554 |
| M | `app/app/(tabs)/self-portrait/page.tsx` | #552 |
| M | `app/layout.tsx` | #555 |
| M | `lib/api.ts` | #552, #553 |
| M | `vitest.config.ts` | #551 |
| A | 4 × `public/icons/*.png`, `public/manifest.json`, `public/sw.js` | #555 |
| A | 4 × `__tests__/*.test.tsx` | #552, #553, #554 |

No other `apps/web` file was touched in the range.

---

## A8 — the login/signup defect: now answered after verification, not before it

v13 recorded this as **OPEN AND UNFIXED**, and as the rotation's most consequential
screen defect: sign-in does not distinguish logging in from signing up, a UAT tester
created three accounts by accident, and a weekly letter went to an account she did not
know existed while her real account received none.

**#553 and #554 address it — at the point where addressing it is safe.**

The fix is not on the entry screen, and the reason is recorded in the new screen's own
header: telling an *unauthenticated* caller whether an email is already known is account
enumeration. So the signal fires immediately after verification instead, when the user has
already proven control of the mailbox and naming the address leaks nothing.

Mechanism, verified by reading all three files:

- `TokenResponse.is_new_account: bool = False` — set **only** when that request created the
  account, and only **after** successful verification. It defaults `False`, so the login /
  register / refresh mint sites needed no edit; the diff not touching them is the guarantee.
- `app/auth/verify/page.tsx:82` and `app/auth/oauth/finish/page.tsx:48` both
  `router.replace('/auth/welcome')` when the flag is set. Both paths, not just OTP — #554
  exists because #553 covered only one of them.
- `app/auth/welcome/page.tsx` (103 lines) names the address the account was created under
  and offers a way out. The email is read from the store, never from a query param, so it
  never enters a URL or browser history.
- It sits **before** the disclaimer and forwards there when one is still needed, so a user
  is not asked to accept terms under an account they are about to abandon. `disclaimer/page.tsx`
  required no change.

**What is fixed:** a user who mistypes an address is now told, once, that this is a new
account — on both the OTP and Google paths.

**What is NOT fixed, and should not be recorded as fixed:** the entry screen still does not
distinguish login from signup, which is the literal wording of A8. The accidental account
is still created and left in the database — deliberately, per the screen's header: an
orphaned empty row is harmless, and deleting a row a user has just proven they own is a
larger and riskier change. **Nothing recovers the split-activity state the UAT tester is
already in**, and nothing yet watches whether letters arrive.

⚠️ **Never seen by a human.** Covered by `auth/welcome/__tests__/welcome.test.tsx` and two
`newAccountRouting.test.tsx` files — unit tests only.

---

## Inventory — changed sections only

Sections not named below are **UNCARRIED** — not re-verified this rotation, so not
restated. See `SCREENS_TRACKING_v13.md` and treat that content as unverified.

### A — Authentication & First-time user

| ID | Screen | Status |
|---|---|---|
| A-auth (entry) | **Sign-in screen — login vs signup** | ⚠️ **STILL OPEN (UAT A8, narrowed).** The entry screen itself is unchanged and still does not distinguish the two. The consequence is mitigated after verification — see above — not at the point of the mistake. |
| A-welcome | **New-account welcome** — `/auth/welcome` | ✅ **NEW (#553, #554).** Shown once, immediately after a verification that created the account, on both OTP and Google paths. Names the address; offers an exit; forwards to the disclaimer when one is due. ⚠️ never seen by a human. |
| A-auth (session) | Sign-in / session lifecycle | UNCARRIED — not re-verified this rotation. |

### G — Rituals

| ID | Screen | Status |
|---|---|---|
| G-self-portrait | Self-portrait | ✅ covered. **v14: shows how many themed categories are covered (#552).** The count comes from stored answers, not filtered ones — pinned by `coverageLabel.test.tsx`. ⚠️ never seen by a human. |
| G-mirror | Mirror | ✅ covered. **v14: the ring-true note is safety-checked before it is persisted (#557).** No visible change — and no user can currently reach the gate: the page has **0** text inputs, so no note is ever sent. See `PROJECT_STATE_v26.md §4`. |
| G12 | You vs You | ✅ covered. **v14: same ring-true gate (#557), same unreachability** — the page's single `textarea` is the prompt, not a note. On the safety path this endpoint returns 200 with a body instead of its usual 204; both are 2xx and the client reads neither. |

### Shell

| ID | Screen | Status |
|---|---|---|
| — | App shell / layout | ✅ **v14: installable as an Android PWA (#555)** — `manifest.json`, `sw.js`, and four icons added; `app/layout.tsx` links the manifest. ⚠️ **Not verified on a device.** The files exist and the build passes; whether the install prompt actually appears on Android has not been observed. |

---

## Test and typecheck state for the screen layer — executed at `ef3e2d89`

Both numbers were produced by running the tools on this machine at this SHA.

| Tool | Result |
|---|---|
| `vitest run` | **13 failed, 119 passed (132)**; 6 of 28 files |
| `tsc --noEmit` | **11** errors |

**The 13 are unchanged in count from v13 and are all pre-existing.** #551 closed TD-51 by
adding `globals: true`, which cleared 49 of the 62 that existed then — exactly the 62 → 13
that v25 measured and predicted. The remaining 13, itemised this rotation:

| File | Failures |
|---|---|
| `app/app/chat/conv/[id]/__tests__/page.test.tsx` | 3 |
| `components/reflections/__tests__/EmptyReflections.test.tsx` | 4 |
| `components/reflections/__tests__/DateGrouper.test.tsx` | 2 |
| `components/chat/__tests__/QuickActionsRow.test.tsx` | 2 |
| `components/reflections/__tests__/FilterPills.test.tsx` | 1 |
| `components/reflections/__tests__/SavedLineCard.test.tsx` | 1 |

One is triaged this rotation — **TD-52**, the `FilterPills` toast spy
(`FilterPills.test.tsx:65`): the spy is not called with the asserted two-argument
signature. Root cause still untriaged, and `QuickActionsRow > Ask harder shows Coming soon
toast` fails identically. The other 11 are **UNTRIAGED** — no cause was established for
any of them this rotation, and none should be described as understood.

`next.config.js` still sets `ignoreBuildErrors: true` and `ignoreDuringBuilds: true`
(verified by direct read, `:5` and `:8`), so **`npm run build` validates neither of these
numbers**. That is TD-47, still open.

---

## App icon — no longer deferred for PWA purposes

v13 deferred it. #555 added `icon-192.png`, `icon-512.png` and maskable variants under
`public/icons/`, plus `manifest.json`. **Verified present** by `git diff --name-status`.

⚠️ **Not verified as rendering.** No device install was performed, and no visual check of
the maskable safe-zone was made. The files exist; how they look on a home screen is
unknown.
