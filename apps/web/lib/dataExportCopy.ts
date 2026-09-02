// User-facing copy for data export. APPROVED 2026-09-02, applied verbatim.
//
// Collected here for the same reason as accountDeletionCopy: approved strings
// land as one edit to one file. No PENDING_COPY tripwire on this module — the
// copy was approved before the UI was written, so there was never a placeholder
// to guard against.
//
// The 413 detail string lives SERVER-side (routers/auth.py
// EXPORT_TOO_LARGE_DETAIL) because the server is what decides the export is too
// large, and the client shows whatever detail the server sends. It names
// support@thewiseroom.app — the address already published as the data-controller
// contact in the Privacy Policy and Terms, which is where §7 already directs
// GDPR requests. A test pins the two to each other so they cannot drift.

export const DATA_EXPORT_COPY = {
  /** Card section label. */
  sectionLabel: 'Your data',

  /** The row the user taps. */
  trigger: 'Download my data',

  /** While the request is in flight. */
  loading: 'Preparing your data…',

  /** 429 — the one-per-hour limit. */
  rateLimited: 'You can download your data once an hour. Please try again shortly.',

  /** Anything else. */
  genericError: 'Could not prepare your download. Please try again.',
} as const

/** philosopher-data-YYYY-MM-DD.json — date in the viewer's own timezone, which
 *  is the date they will think of it by. */
export function exportFilename(now: Date = new Date()): string {
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `philosopher-data-${yyyy}-${mm}-${dd}.json`
}
