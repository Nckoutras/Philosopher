# Home "room noticed" — show only UNSEEN insights (item 2, option α) — STEP 0

**Branch:** `feat/room-noticed-unseen` · **Date:** 2026-07-10 · Client-only, no backend.

## 1. Duplication mechanism — CONFIRMED

Both surfaces call the **same** `GET /insights` (no `conversation_id`), which returns
non-dismissed insights, `created_at` desc. The newest one (`[0]`) therefore renders in
BOTH places at once:

- **Home nudge:** `RoomNoticedCard.tsx:25-27` — `api.getInsights().then(list => setInsight(list[0] ?? null))`.
  Shows only `list[0]` under the "THE ROOM NOTICED" eyebrow.
- **Insights archive:** `app/app/insights/page.tsx:35,39,167` — `api.getInsights()` →
  `.filter(i => !i.is_dismissed)` → `insights.map(...)` renders the **whole** list,
  including `[0]`.

So the newest insight appears as the Home nudge **and** as the top row of the Insights
archive simultaneously. That is the duplication. (`api.getInsights` is defined at
`api.ts:1067`.)

## 2. Insight has only `is_dismissed` — CONFIRMED

`interface Insight` (`api.ts:187-195`): `id, content, insight_type, source_count?,
conversation_id, is_dismissed, created_at`. **No `seen`/`viewed` field.** A client-side
seen-set is the only way to track "opened but not dismissed" without a backend change.

## 3. Normal route page (localStorage available) — CONFIRMED

`RoomNoticedCard` is mounted by `app/app/(tabs)/today/page.tsx` (`'use client'`, line 1)
at line 202 (`<RoomNoticedCard />`). This is a normal Next.js client route on the app
origin — `localStorage` is available. **Not** an artifact/iframe sandbox.

## 4. `useInsightDoors()` semantics — REPORTED (no double-handle)

`lib/useInsightDoors.ts`:

- **`primary(insight)`** (30-53): `router.push(...)` for every type — dilemma → council
  (or `/app/upgrade` for free), belief → counterview, shift → you-vs-you, else → mirror.
  **Navigates away; does NOT dismiss.**
- **`doubt(insight)`** (56-58): `router.push('/app/counterview?insightId=…')`.
  **Navigates away; does NOT dismiss.**
- **`discard(insight, {onRemove, onRestore})`** (62-74): optimistic `onRemove()` +
  a 5s-delayed durable `api.dismissInsight(id)` (server `is_dismissed = true`) + undo
  toast. **Does dismiss server-side.**

**Double-handle check:** adding an id to a client `localStorage` seen-set on
`onPrimary`/`onDiscard` does not collide with the hook — `primary`/`doubt` never touch
storage, and `discard`'s server dismiss is orthogonal to the client set. The seen-set is
purely additive. **No double-handling.** ✅

## ⚠️ Gap that needs a decision — the third door (`onDoubt`)

The `today` InsightCard renders **three** actions, not two (`InsightCard.tsx`): **Primary**
(97), **"Doubt this"** (shown when `insight_type !== 'belief'`, 51/105-111), and **Discard**
(116). The brief marks an insight SEEN on `onPrimary` **and** `onDiscard` only.

But **`onDoubt` also acts on the card and navigates away without dismissing** — so a user
who taps "Doubt this" on a Home insight leaves it neither dismissed nor seen, and it will
**resurface as the Home nudge next visit** — the exact duplication class we're fixing.

- For **belief** insights this is moot: "Doubt this" is hidden (`showDoubt = false`) because
  primary *is* the counterview door, and primary already marks seen.
- For **dilemma / shift / pattern** insights, "Doubt this" is a live door that would escape
  the seen-set.

**Recommendation:** also add the id to the seen-set on **`onDoubt`** — it is an "acted on
this card" signal identical to primary (navigates away, no dismiss). It stays client-only
and does not touch `useInsightDoors` semantics or the dismiss flow. If you'd rather keep the
brief exactly as written (primary + discard only), I'll do that — but "Doubt this" will keep
re-nudging non-belief insights.

## Proposed STEP 1 (unchanged from brief, pending your call on `onDoubt`)
- `localStorage` key `wr_roomnoticed_seen` = JSON array of insight ids, try/catch guarded
  (private-mode → fall back to today's `[0]` behaviour, never crash).
- Pick the newest insight whose id ∉ seen-set (not just `[0]`); none → render `null`.
- Add id to the set on `onPrimary` + `onDiscard` **(+ `onDoubt`, recommended)**.
- Trim the set to the last ~50 ids.
- Insights archive, insight model/endpoints, `useInsightDoors`, dismiss flow: untouched.

**HARD STOP — awaiting approval (and your `onDoubt` decision) before building.**

---

# STEP 1 — BUILT (approved: `onDoubt` = mark seen; + 3 hardening rules)

## Files
- **New** `apps/web/lib/roomNoticedSeen.ts` — the client seen-set (localStorage
  `wr_roomnoticed_seen`). Pure functions `markSeen / unmarkSeen / pruneSeen`, all
  try/catch guarded, client-only.
- **Modified** `apps/web/components/today/RoomNoticedCard.tsx` — picks the newest
  UNSEEN insight and marks seen on every door.

## Behaviour
- Fetch `getInsights()` → `pruneSeen(liveIds)` → surface
  `list.find(i => !seen.has(i.id)) ?? null` (newest id ∉ seen; `null` when none).
- `onPrimary` / `onDoubt` → `markSeen(id)` then the (unchanged) hook navigates away.
- `onDiscard` → `discard(insight, { onRemove, onRestore })`:
  - `onRemove` (commit): `markSeen(id)` + hide — covers the "opened but not yet
    dismissed" 5s gap so it can't re-nudge.
  - `onRestore` (Undo): `unmarkSeen(id)` + restore — an undone discard returns to Home.

## Hardening rules — how each is met
1. **Discard-undo:** seen is added in `onRemove` and removed in `onRestore`
   (`unmarkSeen`), so an undone discard is not left "seen".
2. **Storage shape:** stored as a JSON **array in insertion order**; `write()` keeps
   the newest 50 via `slice(-CAP)` (drops the OLDEST). `read()` wraps `JSON.parse` in
   try/catch and rejects non-array/legacy values → empty set, never throws.
3. **Dismissed self-clean:** `pruneSeen(liveIds)` runs on every fetch —
   `seen := seen ∩ liveIds` — so ids the server no longer returns (dismissed / GC'd)
   drop out and the set can't accrete.

## Untouched (as promised)
Insights archive, insight model/endpoints, `useInsightDoors` semantics, the dismiss
flow, every other Home card. No migration, no endpoint, no backend.

## Verification
- Only importer of the new module is `RoomNoticedCard`; `today/page.tsx` (unchanged)
  is its only mount. No other dependents.
- All storage access is inside a post-fetch effect + event handlers (never during
  render) → no SSR `localStorage` window.
- **`tsc` could NOT run — no Node/npm available in this environment.** Verified by
  inspection: `markSeen/unmarkSeen` return `void`, `pruneSeen` returns `string[]`,
  `current.id` is `string`, and the picked value is `Insight | null`. **Please
  confirm a clean `tsc` / preview build on your side before merge.**
- Fallback proof: if `localStorage` throws (private mode), `read()` → `[]`, so
  `seen` is empty and the card shows `list[0]` — today's behaviour, no crash.
