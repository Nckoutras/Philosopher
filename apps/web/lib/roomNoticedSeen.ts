// Client-only "seen" state for the Home "room noticed" nudge (RoomNoticedCard).
//
// The Home card and the Insights archive both render GET /insights[0], so the
// newest insight appeared in both at once. This tracks which insight ids THIS
// device has already ACTED ON from the Home card (opened a door / doubted /
// discarded) so the nudge stops re-surfacing them — with NO backend change
// (Insight has only is_dismissed; "opened but not dismissed" has no server flag).
//
// Shape: a JSON array of ids in insertion order (oldest first) so the cap drops
// the OLDEST. Every access is try/catch guarded — private-mode / disabled storage
// degrades to "no seen state" (the card falls back to showing the newest [0]) and
// never throws. Only ever touched client-side (event handlers + a post-fetch
// effect), so there is no SSR window.
const KEY = 'wr_roomnoticed_seen'
const CAP = 50

// Tolerant read: a missing, corrupt, or legacy (non-array) value → empty set.
function read(): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : []
  } catch {
    return []
  }
}

// Persist, keeping only the newest CAP ids (drops the oldest). Returns the
// canonical (capped) array so callers use exactly what was stored.
function write(ids: string[]): string[] {
  const capped = ids.slice(-CAP)
  try {
    localStorage.setItem(KEY, JSON.stringify(capped))
  } catch {
    /* private-mode / disabled storage — no-op; seen state simply won't persist */
  }
  return capped
}

// Add an id when the user COMMITS an action on the card. Idempotent — re-adding
// an existing id keeps its original insertion order (no churn).
export function markSeen(id: string): void {
  const ids = read()
  if (ids.includes(id)) return
  write([...ids, id])
}

// Remove an id — used when a discard's 5s Undo fires, so an undone discard does
// NOT leave the insight stuck "seen" (it must return to Home).
export function unmarkSeen(id: string): void {
  write(read().filter((x) => x !== id))
}

// Prune ids the live (non-dismissed) list no longer contains — the server has
// dismissed / garbage-collected them, so there is nothing left to suppress.
// Returns the pruned set. seen := seen ∩ liveIds.
export function pruneSeen(liveIds: string[]): string[] {
  const live = new Set(liveIds)
  return write(read().filter((x) => live.has(x)))
}
