// Daily-cap throttle for the Home quote nudge (QuoteNudgeCard): at most one nudge
// surfaced per local calendar day. Stores the last-shown local date as YYYY-MM-DD.
// try/catch guarded — private-mode / disabled storage degrades to "not shown"
// (the card may surface again) and never throws. Client-only.
const KEY = 'wr_quotenudge_lastshown'

// Local calendar date as YYYY-MM-DD (not UTC — the cap should follow the user's day).
function todayLocal(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// True if a nudge has already been surfaced today on this device.
export function shownToday(): boolean {
  try {
    return localStorage.getItem(KEY) === todayLocal()
  } catch {
    return false
  }
}

// Record that a nudge was surfaced today.
export function markShownToday(): void {
  try {
    localStorage.setItem(KEY, todayLocal())
  } catch {
    /* private-mode / disabled storage — no-op; the cap simply won't persist */
  }
}
