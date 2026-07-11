// Client-only "seen" state for the Home "A line for you" quote nudge
// (QuoteNudgeCard). Mirrors roomNoticedSeen.ts: an id is marked seen when the user
// acts on the card (Discuss) or dismisses it, so that suggestion never re-nudges on
// this device. Dismiss is PERMANENT here, so there is no unmarkSeen counterpart.
//
// Shape: a JSON array of ids in insertion order (oldest first) so the cap drops the
// OLDEST. Every access is try/catch guarded — private-mode / disabled storage
// degrades to "no seen state" and never throws. Only touched client-side.
const KEY = 'wr_quotenudge_seen'
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

// Add an id when the user acts on / dismisses the card. Idempotent — re-adding an
// existing id keeps its original insertion order (no churn).
export function markSeen(id: string): void {
  const ids = read()
  if (ids.includes(id)) return
  write([...ids, id])
}

// Prune ids the live suggested list no longer contains. Returns the pruned set.
// seen := seen ∩ liveIds.
export function pruneSeen(liveIds: string[]): string[] {
  const live = new Set(liveIds)
  return write(read().filter((x) => live.has(x)))
}
