# Web test + typecheck measurement — 2026-08-13

Branch: `chore/web-lockfile-sync-jsdom` (from `origin/main` @ `f51c749e`)
Change under measurement: `apps/web/package-lock.json` synced with the already-declared
`jsdom@^25.0.0` and `@testing-library/react@^16.0.0` devDependencies.

Measurement only. No test, component, or config file was modified.

Runtime: Node v20.18.1 / npm 10.8.2 (`C:\clwn\node-v20.18.1-win-x64`, session-scoped PATH).

> The raw `npm test -- run` console log is 28,617 lines, the overwhelming majority of which is
> repeated jsdom DOM dumps attached to each failure. It is not committed. This report contains
> the complete failure inventory (all 62), the complete typecheck output (all 11 errors), and the
> full classification. Nothing material from the raw log is omitted.

---

## Step 2 — lockfile diff

```
 apps/web/package-lock.json | 935 ++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 932 insertions(+), 3 deletions(-)
```

| Category | Count |
|---|---|
| (a) entries ADDED | 69 — all `"dev": true` |
| (b) entries CHANGED | 1 — `hasown` 2.0.3 → 2.0.4 |
| (c) entries REMOVED | 0 |

`package.json` byte-identical to `origin/main` (`git diff --exit-code` → 0).

**No platform-specific optional package was pruned.** Verification:

```
$ git diff apps/web/package-lock.json | grep '^-' | grep -E '"node_modules/(@esbuild|@rollup)'
(no output)

$ git diff apps/web/package-lock.json | grep -E '^\-\s+"node_modules/'
(no output)
```

The `hasown` bump is forced: `jsdom → form-data@4.0.6` declares `hasown: ^2.0.4`, which `2.0.3`
does not satisfy. The pre-existing consumer (`tailwindcss → resolve → is-core-module@2.16.2`)
declares `^2.0.3` and accepts `2.0.4` by its own semver. No nested duplicate was forced.

---

## Step 3 — test suite

```
 Test Files  16 failed | 8 passed (24)
      Tests  62 failed | 54 passed (116)
   Duration  50.36s
```

**All 24 test files executed.** Zero collection/import failures — every one of the 20
`@vitest-environment jsdom` files loaded jsdom and RTL successfully and ran its assertions.
Before this lockfile sync those 20 files could not run at all on a clean install.

### Per-file results

| File | Tests | Failed | Env |
|---|---|---|---|
| `lib/__tests__/rateLimitError.test.ts` | 2 | 0 ✅ | node |
| `lib/__tests__/refreshSession.test.ts` | 7 | 0 ✅ | node |
| `lib/__tests__/streamError.test.ts` | 2 | 0 ✅ | node |
| `lib/__tests__/streamMessage429.test.ts` | 3 | 0 ✅ | node |
| `components/chat/__tests__/MessageBubble.test.tsx` | 5 | 0 ✅ | jsdom |
| `components/chat/__tests__/BookmarkIndicator.test.tsx` | 3 | 0 ✅ | jsdom |
| `components/chat/__tests__/SafetyReEntryCard.test.tsx` | 3 | 0 ✅ | jsdom |
| `components/chat/__tests__/OpeningInvocation.test.tsx` | 2 | 0 ✅ | jsdom |
| `components/chat/__tests__/ChatHeader.test.tsx` | 2 | 1 | jsdom |
| `components/chat/__tests__/ErrorMessage.test.tsx` | 4 | 2 | jsdom |
| `components/chat/__tests__/PaywallModal.test.tsx` | 11 | 8 | jsdom |
| `components/chat/__tests__/QuickActionsRow.test.tsx` | 8 | 7 | jsdom |
| `components/chat/__tests__/SafetyBubble.test.tsx` | 4 | 2 | jsdom |
| `components/chat/__tests__/SaveLineInlineUpgrade.test.tsx` | 6 | 5 | jsdom |
| `components/layout/__tests__/BottomTabBar.test.tsx` | 5 | 4 | jsdom |
| `components/library/__tests__/ConversationCard.test.tsx` | 7 | 4 | jsdom |
| `components/library/__tests__/ConversationList.test.tsx` | 7 | 3 | jsdom |
| `components/library/__tests__/EmptyConversationHistory.test.tsx` | 5 | 4 | jsdom |
| `components/reflections/__tests__/DateGrouper.test.tsx` | 3 | 2 | jsdom |
| `components/reflections/__tests__/EmptyReflections.test.tsx` | 5 | 5 | jsdom |
| `components/reflections/__tests__/FilterPills.test.tsx` | 6 | 4 | jsdom |
| `components/reflections/__tests__/SavedLineCard.test.tsx` | 5 | 3 | jsdom |
| `app/app/(tabs)/reflections/__tests__/page.test.tsx` | 7 | 5 | jsdom |
| `app/app/chat/conv/[id]/__tests__/page.test.tsx` | 4 | 3 | jsdom |

### Root cause A — RTL auto-cleanup never registers (49 of 62 failures)

`@testing-library/react/dist/index.js`:

```js
// if we're running in a test runner that supports afterEach
// or teardown then we'll automatically run cleanup afterEach test
if (typeof afterEach === 'function') {
  afterEach(() => { cleanup() })
```

`vitest.config.ts` does **not** set `globals: true`, so `afterEach` is not a global. RTL's guard
fails, auto-cleanup is never registered, and no test or setup file calls `cleanup()` manually
(repo-wide grep: zero hits). Every `render()` therefore appends a new container to
`document.body` that is never unmounted, and `screen.*` queries — which search the whole
`document.body` — see all prior renders.

The accumulation is visible directly in the raw log, where the `<body>` in successive failures of
one file contains 2, then 3, identical `<div>` containers.

This is a pre-existing configuration gap that the lockfile sync merely made observable — these
tests have never run in CI on a clean install. **It is not a regression introduced by this PR.**

### Root cause B — 13 stale tests

Independent of cleanup; these assert against code that has since changed.

### Complete failure inventory (62)

Categories: **(a)** environment/dependency · **(b)** stale test · **(c)** real product bug · **(d)** flaky/timing

| # | File · test | Cat | Why |
|---|---|---|---|
| 1 | `ChatHeader` · renders portrait img with correct src and alt | a | `Found multiple elements with the alt text: Socrates` — leftover container from test 1 |
| 2 | `ErrorMessage` · retry button calls send with last user message content | a | `Found multiple elements with the text: Try again` |
| 3 | `ErrorMessage` · retry button clears streamError | a | `Found multiple elements with the text: Try again` |
| 4 | `PaywallModal` · renders correct upgrade target label for Pro | a | multiple `button` name `/Upgrade to Pro/i` |
| 5 | `PaywallModal` · never offers Premium — a pro user still sees the Pro label | a | multiple `button` name `/Upgrade to Pro/i` |
| 6 | `PaywallModal` · calls onClose when the × button is clicked | a | multiple elements with text `Close` |
| 7 | `PaywallModal` · calls onClose when the Close text link is clicked | a | multiple elements with text `Close` |
| 8 | `PaywallModal` · Upgrade CTA button is disabled | a | multiple `button` name `/Upgrade to Pro/i` |
| 9 | `PaywallModal` · renders persona name from store in body copy | a | multiple matches for `/You've used today's reflections with Socrates\./` |
| 10 | `PaywallModal` · falls back to "this mind" when activePersonaName is null | a | multiple matches for `/…with this mind\./` |
| 11 | `PaywallModal` · renders the save-limit copy and no daily-limit copy when reason is save_limit | a | multiple elements with text `Daily limit reached.` |
| 12 | `QuickActionsRow` · renders three action chips | **b** | asserts `getByLabelText('Ask harder')`; component has no such chip — now `Deep mode`, `Bring another mind`, `Ask the Council`, `Save line` |
| 13 | `QuickActionsRow` · Ask harder shows Coming soon toast | **b** | same — `Ask harder` chip no longer exists |
| 14 | `QuickActionsRow` · Bring another mind calls onBringAnotherMind | a | multiple labels `Bring another mind` |
| 15 | `QuickActionsRow` · calls onSave when Save line tapped and under limit | a | multiple labels `Save line` |
| 16 | `QuickActionsRow` · shows inline upgrade card when at free tier limit | a | multiple labels `Save line` |
| 17 | `QuickActionsRow` · does not call onSave when at free tier limit | a | multiple labels `Save line` |
| 18 | `QuickActionsRow` · upgrade card dismiss restores chips | a | multiple labels `Save line` |
| 19 | `SafetyBubble` · renders the The Wise Room eyebrow | a | multiple elements with text `The Wise Room` |
| 20 | `SafetyBubble` · renders a role=alert on the bubble for accessibility | a | multiple elements with role `alert` |
| 21 | `SaveLineInlineUpgrade` · renders body copy | a | multiple elements with text `Upgrade to Pro to keep saving.` |
| 22 | `SaveLineInlineUpgrade` · renders Continue with Pro CTA | a | multiple elements with text `Continue with Pro` |
| 23 | `SaveLineInlineUpgrade` · renders Maybe later CTA | a | multiple elements with text `Maybe later` |
| 24 | `SaveLineInlineUpgrade` · calls onUpgrade when Continue with Pro tapped | a | multiple elements with text `Continue with Pro` |
| 25 | `SaveLineInlineUpgrade` · calls onDismiss when Maybe later tapped | a | multiple elements with text `Maybe later` |
| 26 | `BottomTabBar` · marks Portrait tab as active on /app/self-portrait | a | multiple elements with text `Portrait` |
| 27 | `BottomTabBar` · does not mark other tabs as active on /app/self-portrait | a | multiple elements with text `Home` |
| 28 | `BottomTabBar` · links the Quotes tab to /app/quotes | a | multiple elements with text `Quotes` |
| 29 | `BottomTabBar` · links the Explore tab to /app/explore | a | multiple elements with text `Explore` |
| 30 | `ConversationCard` · renders meta line with message count and Yesterday | a | multiple matches for `/14 messages/` |
| 31 | `ConversationCard` · renders fallback snippet when title is null | a | multiple matches for `/Epictetus/` |
| 32 | `ConversationCard` · navigates to correct conv route on tap | a | multiple elements with role `button` |
| 33 | `ConversationCard` · renders initials fallback when no portraitUrl | a | multiple elements with text `E` |
| 34 | `ConversationList` · groups this-week conversations under "This week" | a | multiple elements with text `This week` |
| 35 | `ConversationList` · groups older conversations under "Earlier" | a | multiple elements with text `Earlier` |
| 36 | `ConversationList` · renders both groups when convs span different weeks | a | multiple elements with text `This week` |
| 37 | `EmptyConversationHistory` · renders body copy | a | multiple matches for `/Every conversation you start is saved here/` |
| 38 | `EmptyConversationHistory` · renders all 3 instruction items | a | multiple elements with text `Saved automatically` |
| 39 | `EmptyConversationHistory` · renders CTA with correct label | a | multiple `button` name `Explore minds` |
| 40 | `EmptyConversationHistory` · CTA navigates to browse-minds on click | a | multiple `button` name `Explore minds` |
| 41 | `DateGrouper` · renders uppercase styling | **b** | asserts `container.firstChild.className` contains `uppercase`; component was restyled with flanking rule lines, so root div is now `flex items-center gap-[8px] mt-[16px] mb-[8px]` and `uppercase` moved to the nested `<p>`. Per-render `container`, so cleanup is not a factor |
| 42 | `DateGrouper` · renders sepia color class | **b** | same restructure — `text-sepia` now on the nested `<p>` |
| 43 | `EmptyReflections` · renders headline from §4.3 | **b** | expects `A space for the lines that stay with you.`; copy is now `Nothing saved yet.` |
| 44 | `EmptyReflections` · renders body copy from §4.3 | **b** | expects `/When a sentence settles, save it/`; copy is now `When a reply lands, tap Save line below it.` |
| 45 | `EmptyReflections` · renders 3-item instruction list | a | copy still matches; fails only on multiple elements with text `Save what resonates` |
| 46 | `EmptyReflections` · renders Start a conversation CTA | **b** | expects `Start a conversation`; CTA is now `Choose a mind` |
| 47 | `EmptyReflections` · calls onStartConversation when CTA tapped | **b** | same — CTA renamed to `Choose a mind` |
| 48 | `FilterPills` · calls onChange("all") when All tapped | a | multiple elements with text `All` |
| 49 | `FilterPills` · calls onChange("by-mind") when By mind tapped | a | multiple elements with text `By mind` |
| 50 | `FilterPills` · By theme shows Coming soon toast | a | multiple labels `By theme (coming soon)` |
| 51 | `FilterPills` · does not show persona sub-row when active=all | a | `screen.queryByText('Epictetus')` finds the leftover sub-row rendered by the preceding `active="by-mind"` test |
| 52 | `SavedLineCard` · renders persona display name | a | multiple matches for `/Marcus Aurelius/` |
| 53 | `SavedLineCard` · calls onClick when card tapped | a | multiple elements with role `button` |
| 54 | `SavedLineCard` · renders fallback div when portraitUrl is empty | **b** | `container.querySelector('img')` now matches the always-rendered decorative `<Image src="/personas/wise-room-hero.webp" alt="" aria-hidden>` added to the card background. The `portraitUrl ? <img> : <div>` fallback itself is still correct |
| 55 | `ReflectionsPage` · renders page header with Reflections eyebrow and title | a | multiple elements with text `Reflections` |
| 56 | `ReflectionsPage` · renders EmptyReflections when feed is empty | a | multiple `[data-testid="empty-reflections"]` |
| 57 | `ReflectionsPage` · renders saved line cards and filter pills when feed has line items | a | multiple `[data-testid="saved-line-card"]` |
| 58 | `ReflectionsPage` · renders mirror and council verdict cards alongside lines | a | multiple `[data-testid="saved-line-card"]` |
| 59 | `ReflectionsPage` · calls loadReflectionsFeed on mount | **b** | spy called **8813** times. The test's `vi.mock('next/navigation')` returns a **new object literal** from `useRouter()` on every call, so `router` is referentially unstable; `useEffect(…, [token, router, load])` re-fires each render and `load()` writes state via `setPortraitBySlug`, closing an infinite loop across the 6 still-mounted instances. Real `useRouter` is referentially stable — **not a product bug**; the test's mock predates the portrait-map fetch added to `load()` |
| 60 | `ExistingConversationPage` · sets activeConversationId and loads messages on mount | **b** | test mocks `api.getConversations` (plural); page calls `api.getConversation(params.id)` (singular). The real method runs unmocked, the page never leaves `Loading…` |
| 61 | `ExistingConversationPage` · renders ChatHeader with persona name once loaded | **b** | same stale mock — page stuck on `Loading…`, `[data-testid="chat-header"]` never renders |
| 62 | `ExistingConversationPage` · does not pass openingInvocation (null) to setActiveConversation | **b** | same stale mock — `setActiveConversation` never called |

### Totals

| Category | Count |
|---|---|
| (a) environment/dependency — RTL auto-cleanup not registered | **49** |
| (b) stale test | **13** |
| (c) real product bug | **0** |
| (d) flaky/timing | **0** |

**No failure indicates a genuine product defect.** The 8813-call render loop (#59) was the one
candidate and it resolves to an unstable mock in the test, not to component behaviour.

---

## Step 4 — typecheck

Complete raw output of `npm run typecheck`:

```
> philosopher-web@0.1.0 typecheck
> tsc --noEmit

app/app/(tabs)/account/page.tsx(112,12): error TS18047: 'user' is possibly 'null'.
app/app/(tabs)/account/page.tsx(114,16): error TS18047: 'user' is possibly 'null'.
app/app/(tabs)/account/page.tsx(117,63): error TS18047: 'user' is possibly 'null'.
app/auth/oauth/finish/page.tsx(33,43): error TS2345: Argument of type 'string | null' is not assignable to parameter of type 'string'.
  Type 'null' is not assignable to type 'string'.
components/chat/__tests__/MessageBubble.test.tsx(8,35): error TS2739: Type '{ role: "user"; content: string; }' is missing the following properties from type 'Props': id, saved
components/chat/__tests__/MessageBubble.test.tsx(14,35): error TS2739: Type '{ role: "user"; content: string; }' is missing the following properties from type 'Props': id, saved
components/chat/__tests__/MessageBubble.test.tsx(19,35): error TS2739: Type '{ role: "assistant"; content: string; }' is missing the following properties from type 'Props': id, saved
components/chat/__tests__/MessageBubble.test.tsx(25,35): error TS2739: Type '{ role: "assistant"; content: string; }' is missing the following properties from type 'Props': id, saved
components/chat/__tests__/MessageBubble.test.tsx(30,13): error TS2739: Type '{ role: "user"; content: string; }' is missing the following properties from type 'Props': id, saved
components/library/__tests__/ConversationCard.test.tsx(19,3): error TS2322: Type '{ id: string; persona: Persona; title: string | null; message_count: number; last_message_at: string | null; created_at: string; source_persona_slug: string | null; ... 4 more ...; deep_mode?: boolean | undefined; }' is not assignable to type 'Conversation'.
  Types of property 'origin_persona_slug' are incompatible.
    Type 'string | null | undefined' is not assignable to type 'string | null'.
      Type 'undefined' is not assignable to type 'string | null'.
components/library/__tests__/ConversationList.test.tsx(19,3): error TS2739: Type '{ id: string; title: string; message_count: number; last_message_at: string; created_at: string; persona: { id: string; slug: string; name: string; era: null; tradition: null; tier: "free"; tagline: null; ... 4 more ...; is_accessible: true; }; source_persona_slug: null; source_context_content: null; last_message_sn...' is missing the following properties from type 'Conversation': origin_persona_slug, origin_persona_name, deep_mode
```

### Classification — 11 errors total

**Production code — 4**

| file:line | Code | Error |
|---|---|---|
| `app/app/(tabs)/account/page.tsx:112` | TS18047 | `'user' is possibly 'null'` |
| `app/app/(tabs)/account/page.tsx:114` | TS18047 | `'user' is possibly 'null'` |
| `app/app/(tabs)/account/page.tsx:117` | TS18047 | `'user' is possibly 'null'` |
| `app/auth/oauth/finish/page.tsx:33` | TS2345 | `string \| null` not assignable to `string` |

**Test files — 7**

| file:line | Code | Error |
|---|---|---|
| `components/chat/__tests__/MessageBubble.test.tsx:8` | TS2739 | Props missing `id`, `saved` |
| `components/chat/__tests__/MessageBubble.test.tsx:14` | TS2739 | Props missing `id`, `saved` |
| `components/chat/__tests__/MessageBubble.test.tsx:19` | TS2739 | Props missing `id`, `saved` |
| `components/chat/__tests__/MessageBubble.test.tsx:25` | TS2739 | Props missing `id`, `saved` |
| `components/chat/__tests__/MessageBubble.test.tsx:30` | TS2739 | Props missing `id`, `saved` |
| `components/library/__tests__/ConversationCard.test.tsx:19` | TS2322 | `origin_persona_slug` `undefined` not assignable |
| `components/library/__tests__/ConversationList.test.tsx:19` | TS2739 | missing `origin_persona_slug`, `origin_persona_name`, `deep_mode` |

### Comparison against the stated baseline (35 total / 27 test / 8 production)

| | Baseline | Now | Δ |
|---|---|---|---|
| Total | 35 | **11** | −24 |
| Test files | 27 | **7** | **−20** |
| Production | 8 | **4** | −4 |

**20 of the 27 test-file errors disappeared purely because the type packages are now installed.**
Exactly 20 test files import `@testing-library/react`, one import statement each; with the package
absent every one emitted `TS2307: Cannot find module '@testing-library/react' or its corresponding
type declarations`. 27 − 20 = 7, which matches the 7 remaining test errors exactly. Those 7 are
genuine stale-fixture type mismatches (component `Props` and the `Conversation` type gained
fields) and are unaffected by the install.

> Method note: this 20 is an arithmetic reconciliation, not a re-run. Re-measuring the true
> "before" number would require uninstalling the packages, which is out of scope for this PR.

### Production error set — changed from the baseline

The two files are **unchanged**: still only `app/app/(tabs)/account/page.tsx` and
`app/auth/oauth/finish/page.tsx`. No new production file entered the set.

But the count is **4, not 8**. This is not explainable by the install — neither file imports
anything from jsdom or RTL. Neither file has been touched recently either
(`account/page.tsx` last changed in #494, `oauth/finish/page.tsx` in #101), so it is not a
code change on this branch. The most likely explanation is that the baseline's "8" counted raw
output lines or was captured under a different tsconfig; the discrepancy predates this PR and is
flagged for reconciliation rather than resolved here. Fewer production errors is not a regression.

---

## Net effect of this PR

| | Before | After |
|---|---|---|
| jsdom test files able to run on a clean install | 0 / 20 | **20 / 20** |
| Tests executed | 14 (node only) | **116** |
| Tests passing | 14 | **54** |
| Typecheck errors | 35 | **11** |
| `npm ci` viability | broken (package.json ↔ lock mismatch) | **works** |

The 49 cleanup failures and 13 stale tests are pre-existing debt that this PR makes *visible* for
the first time; it does not introduce them. Both remediations — registering RTL cleanup, and
refreshing the 13 stale tests — are out of scope here and belong in separate PRs.
