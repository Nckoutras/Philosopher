# DESIGN SYSTEM v5 → v6 ADDENDUM (2026-05-22)

> **What this file is:** Targeted delta documenting new components, new token usage conventions, and aesthetic decisions introduced in PR3b through PR4h (2026-05-20 to 2026-05-22).
>
> **How to read this:** `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` remain the structural reference for the color palette, typography, component library (§2–§10), and ornament system. This addendum **extends** those documents with PR3/PR4 wave additions. Where a component or token is not mentioned here, v4 + v5 addendum apply.
>
> **Authoritative status:** Locked 2026-05-22. Component signatures reflect production code as of PR4h. Do not reinterpret token usages documented here.
>
> **Consolidation note:** This addendum should be folded into a future `DESIGN_SYSTEM_v6.md` consolidated doc when the next major design system iteration occurs. Until then, the chain `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md` + this file is the authoritative source of truth.

---

## Why this addendum

PR3b through PR4h introduced:

- **7 new components** — AppHeader, TodaysTopicCard, SwipeableRow, SavedLinePicker, BottomSheet, RitualScheduleSheet, RitualsCard
- **2 new token usage conventions** — `bg-linen` as a selection-state signal; `BRONZE_60/BRONZE_50` as share-card opacity sub-tokens
- **2 major aesthetic decisions** — full-bleed dark splash (PR4h) and mode-aware auth copy (PR4e)

These additions are documented here to prevent specification drift in future sessions.

---

## §A — New components

### §A.1 — `AppHeader`

**File:** `apps/web/components/layout/AppHeader.tsx`
**Introduced:** PR4c #85
**Used in:** All 4 tab pages — Today, Library, Reflections, Account

**Props:** None. Stateless. Reads `new Date()` at render time.

**Output:**
```
Great Minds · Thu, May 22
```

**Rendered structure:**
- Container: `px-[24px] pt-[18px] pb-[10px]`, flex, horizontally centered
- "Great Minds": Cormorant 15px medium italic, Ink color
- "·" separator: Lora 12px, Sepia color
- Date label (`EEE, MMM d` via `date-fns`): Lora 12px, Charcoal color

**Visual intent:** Understated identity mark + temporal anchor. Not a navigation header — no back button, no title prop. Placed at the top of each tab screen above the page content. Kept intentionally minimal.

**Do not:** Add navigation controls, user avatar, or notification badges to `AppHeader`. Those belong in separate components if ever needed.

---

### §A.2 — `TodaysTopicCard`

**File:** `apps/web/components/today/TodaysTopicCard.tsx`
**Introduced:** PR4b #84
**Used in:** Today tab page (`app/app/(tabs)/today/page.tsx`)

**Props:**
```typescript
interface Props {
  user: { full_name: string | null; email: string }
  dailyQuestion: string
  onReflect: (topicText: string) => void
}
```

**Key visual elements:**
- Container: Paper bg, 0.5px Edge border, `rounded-md`
- Eyebrow: Lora 11px uppercase wide-tracked Sepia — "Today's topic."
- **Initials circle:** 40×40px `rounded-full`, Bronze bg (`bg-bronze`), Cormorant 16px medium Vellum text; derived from `user.full_name` via `deriveInitials()` helper in `lib/initials.ts`
- Textarea: expanding, Lora body, faded `text-charcoal/40` placeholder showing the day-deterministic `dailyQuestion`
- "Reflect" button: right-aligned Bronze CTA

**Behavior:** If user submits an empty textarea, `onReflect` receives the `dailyQuestion` text as the topic. The calling page stores the resulting text in `localStorage` as `today_topic_draft_{conversationId}` and the chat page auto-sends it once after `isReady`.

**Bronze initials circle:** This is the canonical pattern for user-as-initiator affordances. 40×40px, `bg-bronze`, Cormorant italic Vellum. Do not use persona avatars in user-context surfaces.

---

### §A.3 — `SwipeableRow`

**File:** `apps/web/components/ui/SwipeableRow.tsx`
**Introduced:** PR4f #89
**Used in:** Reflections page (wraps `SavedLineCard`), Library `PastConversationsView` (wraps `ConversationCard`)

**Props:**
```typescript
interface Props {
  children: ReactNode
  onDelete: () => void
  showHint?: boolean  // default: false
}
```

**Key visual elements:**
- Background reveal: Safety color (`bg-safety` / `#7A4030`) behind the row, showing a `Trash2` (Lucide) icon at right
- Swipe threshold: −80px (`DELETE_THRESHOLD = -80`)
- Below threshold: spring-back animation via framer-motion `useAnimation`
- Above threshold: row slides off left, `onDelete()` fires
- **Discoverability hint:** When `showHint = true` and not previously shown, the row animates: slide −28px then spring back. Gated by `sessionStorage` key (`swipe_hint_seen_reflections` or `swipe_hint_seen_library`) so it shows only on the first session.

**Undo pattern (implemented in the calling page, not in this component):**
- Calling page wraps `onDelete` with: optimistic removal, `setTimeout` for 5s deferred API call, undo toast that restores the item and cancels the timeout.
- `SwipeableRow` only calls `onDelete()` — it does not know about undo. Undo logic is the caller's responsibility.

**Do not:** Use `SwipeableRow` for items that cannot be genuinely deleted. It reveals Safety color, which carries "destructive action" semantics per §1.2.

---

### §A.4 — `SavedLinePicker`

**File:** `apps/web/components/rituals/SavedLinePicker.tsx`
**Introduced:** PR4g #90
**Used in:** `RitualScheduleSheet`

**Props:**
```typescript
interface Props {
  savedLines: SavedLineRead[]
  selectedLineId: string
  onChange: (id: string) => void
  portraitUrlsBySlug: Record<string, string>
}
```

**Key visual elements:**
- **Collapsed row:** 28×28px persona portrait circle (`rounded-full`, `bg-linen-deep` fallback) + truncated quote (single line, `truncate`). Right-side `ChevronDown` (Lucide).
- **Expanded rows:** Each saved line shows portrait + 2-line clamped quote (`line-clamp-2`)
- **Selection state:** Selected row gets `bg-linen` tint (Linen `#E8DCC4`). No checkmark. See §B.1.
- **Portrait fallback:** If image fails to load (`onError`), falls back to Bronze initial circle (same pattern as `TodaysTopicCard` but 28px, not 40px).
- Animation: expand/collapse via framer-motion `AnimatePresence`

**`AvatarCircle` sub-component:** Inline within `SavedLinePicker.tsx`. Not exported. Handles image load + fallback.

---

### §A.5 — `BottomSheet`

**File:** `apps/web/components/ui/BottomSheet.tsx`
**Introduced:** PR3c #82
**Used in:** `RitualScheduleSheet` (and `PersonaPickerSheet` which was refactored to use it)

**Props:**
```typescript
interface Props {
  open: boolean
  onClose: () => void
  children: ReactNode
  maxHeight?: string  // default: '75svh'
}
```

**Key visual elements:**
- Fixed overlay: `inset-0 z-50`
- Backdrop: `bg-[rgba(31,27,20,0.5)]` — Ink color at 50% opacity. Tapping closes the sheet (`onClick={onClose}`)
- Sheet: `absolute inset-x-0 bottom-0`, Paper bg, `rounded-t-xl`
- Animation: `y: "100%" → y: 0` slide-up on open; reversed on close via `AnimatePresence`
- `maxHeight` prop: uses `svh` units (not `vh`) for iOS Safari viewport compatibility (PR4a lesson)
- `role="dialog" aria-modal="true"` for accessibility

**maxHeight note:** Always pass `maxHeight` in `svh` units (e.g. `'75svh'`, `'90svh'`), not `vh`. iOS Safari with visible address bar causes `vh` overflow. This was the PR4a bug.

---

### §A.6 — `RitualScheduleSheet`

**File:** `apps/web/components/rituals/RitualScheduleSheet.tsx`
**Introduced:** PR3c #82
**Used in:** `RitualsCard` (opened when user taps "Letter to future self")

**Props:**
```typescript
interface Props {
  open: boolean
  onClose: () => void
  userEmail: string
}
```

**Key visual elements:**
- Wraps `BottomSheet` with `maxHeight="90svh"`
- Lazy-loads saved lines on open via `api.getPersonas()` + `api.listSavedLines()`
- `SavedLinePicker` for line selection
- Local `<input type="datetime-local">` for scheduling date/time
- Max date: 5 years from today (`maxDate` — backend validator allows up to 5 years)
- Optional personal note textarea
- Submit: calls `api.createScheduledEmail()`; success → toast + `onClose()`
- Error: displayed inline below the submit button

**Date handling:** Uses `toDatetimeLocalString()` helper (inline within this file) for cross-platform `datetime-local` formatting. Does NOT use `strftime('%-d')` — that is Linux-only and lives in the backend cron job.

---

### §A.7 — `RitualsCard`

**File:** `apps/web/components/today/RitualsCard.tsx`
**Introduced:** PR3c #82; "Send to future self" renamed to "Letter to future self" in PR4c #85
**Used in:** Today tab page (4th card, after "Your Reflections")

**Props:**
```typescript
interface Props {
  isPro: boolean
  userEmail: string
}
```

**Three rows (fixed layout):**

| Row | Label | State |
|---|---|---|
| 1 | Letter to future self | Functional — Pro gate → opens `RitualScheduleSheet`; Free gate → `/app/upgrade` |
| 2 | Emerging Patterns | Locked shell (`opacity-50`, `Lock` icon, `ChevronRight`) |
| 3 | Weekly Letter | Locked shell (`opacity-50`, `Lock` icon, `ChevronRight`) |

**Row structure:** Each row is a `<button>` or `<div>`, full-width, with label left-aligned and icon right-aligned. Locked shells are non-interactive (no `onClick`).

**Lock icon:** Lucide `Lock` (14px, Sepia color). `ChevronRight` (14px, Sepia). Both locked rows use identical visual treatment.

**Do not** implement Emerging Patterns or Weekly Letter functionality behind these shells without a deliberate design session. They are intentional placeholders for Pro-tier features that depend on accumulated memory data.

---

## §B — New token usage conventions

### §B.1 — `bg-linen` as selection-state signal

**Previous usage of Linen (`#E8DCC4`):** Persona bubble background, default avatar background, weekly letter unread card, slow connection banner.

**New usage (PR4g):** Selected row highlight in `SavedLinePicker`. The selected saved line receives `bg-linen` as its background tint instead of a checkmark.

**Convention locked:**
- `bg-linen` is the canonical "selected item in a picker" signal.
- Do not use a checkmark for picker row selection — use `bg-linen`.
- Do not use `bg-linen` for hover/focus states — only for confirmed selection.
- `bg-linen-deep` (`#DDD0B5`) remains the token for pre-existing selection contexts (selected chip fill, selected option fill per v4 §1.2). `bg-linen` is the lighter variant used when the entire row tints.

---

### §B.2 — `BRONZE_60` / `BRONZE_50` — share card opacity sub-tokens

**Previous usage of Bronze (`#B89968`):** Bookmarks, premium accents, dividers, app-voice avatar marker, suggested insight border, weekly letter unread dot. Always at full opacity.

**New usage (PR4d):** Share card footer text uses Bronze at reduced opacity:
- URL text: Bronze at 60% opacity (`rgba(184, 153, 104, 0.60)`)
- Date text: Bronze at 50% opacity (`rgba(184, 153, 104, 0.50)`)

**Where these live:** In `apps/api/services/image_service.py` as constants `BRONZE_60` and `BRONZE_50` (Python tuples for Pillow RGBA). These are not Tailwind tokens — they are server-side canvas rendering values.

**Convention:**
- `BRONZE_60` / `BRONZE_50` are **share-card-specific** opacity conventions. They exist because the share card canvas uses direct RGBA pixel values, not CSS tokens.
- Do not proliferate opacity sub-tokens to web UI without explicit design decision. Web surfaces should use `text-bronze` (full opacity) or the Tailwind `text-bronze/60` notation if opacity is needed.
- If a future surface needs Bronze at opacity outside the share card, use `text-bronze/60` in Tailwind — do not create a new Python constant.

---

## §C — Aesthetic decisions

### §C.1 — Splash screen — full-bleed dark (PR4h)

**Previous design:** 3-zone split — cream top zone (logo, tagline), image zone (chesterfield portrait), dark bottom zone (CTA).

**New design (PR4h):** Single full-bleed dark image background (`chesterfield-hero.jpg`, `object-cover object-top`). All content is a transparent overlay:

- **Top:** Minimal title overlay (white Cormorant italic, small tracking). Gradient at top-left for legibility: `linear-gradient(to bottom, rgba(0,0,0,0.55), transparent)`.
- **Bottom:** Outlined CTA button + sign-in link. Gradient at bottom: `linear-gradient(to top, rgba(0,0,0,0.65), transparent)`.
- **Mode routing preserved (PR4e):** CTA href passes `?mode=signup`; sign-in link passes `?mode=signin`.
- **a11y:** All text is rendered HTML — not baked into the image. Font colors are white against dark gradients.

**Rationale:** The 3-zone split fragmented the visual. The chesterfield photograph is the strongest editorial element in the brand asset set; full-bleed makes the image the screen. The gradient overlays ensure legibility without blocking the image.

**Asset:** `chesterfield-hero.jpg` — stored at `apps/web/public/personas/chesterfield-hero.jpg`. Referenced in `apps/web/app/page.tsx` as an `<Image>` with `fill` + `object-cover object-top`.

---

### §C.2 — Auth screen — mode-aware copy (PR4e)

**Previous design:** Auth entry screen showed generic copy regardless of whether the user was signing up or signing in.

**New design (PR4e):** Copy is determined by `?mode=` query parameter:

| Mode param | Headline | Context |
|---|---|---|
| `?mode=signup` | "Create your account." | User arrived via "Begin" / primary CTA on splash |
| `?mode=signin` | "Welcome back." | User arrived via "Sign in" link on splash |
| (none / fallback) | "Create your account." | Defaults to signup framing |

**Implementation:** `AuthForm` component uses `useSearchParams()` to read the `mode` param. Wrapped in `<Suspense>` per Next.js `useSearchParams` SSR requirement (PR4e).

**Copy rationale:** The distinction sets the emotional register before the email field. "Welcome back." signals continuity; "Create your account." signals onboarding. Both use the same form — copy is the only difference.

**Do not** infer mode from user existence check (i.e., do not query the DB before rendering). Mode is entirely determined by which CTA the user tapped. This prevents latency and avoids leaking account existence information.

---

**End of DESIGN_SYSTEM v5→v6 ADDENDUM.** Locked 2026-05-22. Companion to `DESIGN_SYSTEM_v4.md` + `DESIGN_SYSTEM_v4_to_v5_ADDENDUM_2026_05_11.md`.
