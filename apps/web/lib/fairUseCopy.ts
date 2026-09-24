// Pro fair-use cap copy. APPROVED 2026-09-02, applied verbatim.
//
// NOT A PAYWALL. This is shown to a subscriber, who has nothing left to buy, so
// the string does not sell, apologise, or explain the economics. It says what
// happened and that nothing was lost. useStream routes error_code
// "fair_use_limit" here and never to setShowPaywall().
//
// The reset time is appended by the caller from RateLimitError.resetAt in the
// viewer's own timezone. The approved sentence itself is unchanged by that —
// "when it resets" stays, and the time is additive.
//
// THE MONTHLY SENTENCE, approved 2026-09-24, mirrors the daily one word for word
// except the window. Its reset is weeks away, so the suffix is a DATE ("Resets on
// October 1."), never a clock time — "Resets at 1:00 AM" on a monthly refusal
// would tell a subscriber they are back tomorrow when they are not.

import type { FairUsePeriod } from '@/lib/api'

export const FAIR_USE_COPY = {
  message: "You've reached today's limit. Everything here will be waiting when it resets.",
  monthly: "You've reached this month's limit. Everything here will be waiting when it resets.",
} as const

/** "Resets at 3:00 AM" in the viewer's locale, or '' if the date is unusable.
 *  Additive only: the approved sentence never depends on this succeeding. */
export function resetSuffix(resetAt?: Date): string {
  if (!resetAt || Number.isNaN(resetAt.getTime())) return ''
  const time = resetAt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return ` Resets at ${time}.`
}

/** "Resets on October 1." in the viewer's locale, or '' if the date is unusable.
 *  The monthly reset is 00:00 UTC on the 1st, so the date is read in UTC: in a
 *  timezone behind UTC the local date would be the last day of the old month. */
export function resetDateSuffix(resetAt?: Date): string {
  if (!resetAt || Number.isNaN(resetAt.getTime())) return ''
  const day = resetAt.toLocaleDateString(undefined, { month: 'long', day: 'numeric', timeZone: 'UTC' })
  return ` Resets on ${day}.`
}

/** The notice for a fair_use_limit refusal. `period` absent = 'day'. */
export function fairUseMessage(resetAt?: Date, period?: FairUsePeriod): string {
  if (period === 'month') return FAIR_USE_COPY.monthly + resetDateSuffix(resetAt)
  return FAIR_USE_COPY.message + resetSuffix(resetAt)
}
