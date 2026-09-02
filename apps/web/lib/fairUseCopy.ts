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

export const FAIR_USE_COPY = {
  message: "You've reached today's limit. Everything here will be waiting when it resets.",
} as const

/** "Resets at 3:00 AM" in the viewer's locale, or '' if the date is unusable.
 *  Additive only: the approved sentence never depends on this succeeding. */
export function resetSuffix(resetAt?: Date): string {
  if (!resetAt || Number.isNaN(resetAt.getTime())) return ''
  const time = resetAt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return ` Resets at ${time}.`
}

export function fairUseMessage(resetAt?: Date): string {
  return FAIR_USE_COPY.message + resetSuffix(resetAt)
}
