// One spelling of the /app/upgrade query string, including where Close goes.
//
// WHY THIS MODULE EXISTS. Twelve surfaces route to /app/upgrade and each one
// built its own query string by hand. That was survivable while the string was
// `?source=x`; it stops being survivable now that every caller must also carry a
// returnTo, because a caller that forgets it does not fail — it produces a
// paywall whose Close button silently falls back to /app/today, which is the
// dead end BUG-003 is about. personaLock.ts states the same rationale for the
// locked-mind route: one shared spelling so a fourth caller cannot invent a
// fifth variant.
//
// WHY returnTo AND NOT router.back(). Founder ruling, and the reason is the
// share loop: back() needs a history entry, and there is none when the reader
// arrived from an external link, a fresh tab, or a PWA cold start — which is
// exactly the traffic a share brings. A returnTo is carried in the URL, so it
// survives all three.
//
// THE VALUE IS A PATH, NEVER A URL. It is read back through Γ-2's
// safeReturnTo (lib/safeReturnTo.ts), which allow-lists `/app/` prefixes and
// rejects protocol-relative payloads. Nothing here needs to re-validate: this
// side only has to avoid CONSTRUCTING something the reader will refuse, and
// pathname+search from the live location cannot be off-origin.

import { safeReturnTo } from './safeReturnTo'
import type { UpgradeSource } from './upgradeCopy'

/** The query key. Named so the reader and the writers cannot drift. */
export const RETURN_TO_PARAM = 'returnTo'

/**
 * Where the paywall should send someone who closes it: the page they were on.
 *
 * CALL THIS IN AN EVENT HANDLER, not during render. It reads window.location,
 * which does not exist on the server; a render-time call would put one value in
 * the SSR html and another after hydration. Returns null on the server, and a
 * null returnTo simply means Close falls back to DEFAULT_RETURN_TO — degraded,
 * never broken.
 *
 * pathname + search, because the query IS part of the destination for some of
 * these screens (a letter's ?src=email, a counterview's ?insightId=). Dropping
 * it would return the reader to the right page as the wrong kind of visit — the
 * same defect the middleware's returnTo fixed at `next=`.
 */
export function currentReturnTo(): string | null {
  if (typeof window === 'undefined') return null
  const here = window.location.pathname + window.location.search
  // EMIT NOTHING RATHER THAN SOMETHING THE READER WILL THROW AWAY. The close
  // button runs safeReturnTo over whatever arrives, so a value that validator
  // would refuse -- a marketing page, /auth, anything outside /app/ -- ends at
  // DEFAULT_RETURN_TO either way. Carrying it would only put a parameter in the
  // URL that changes nothing, and `?returnTo=%2F` on a shared link reads like a
  // bug to anyone who looks at it.
  //
  // THE RULE IS NOT RESTATED HERE. Asking safeReturnTo whether it would return
  // the value UNCHANGED is the same question as "is this acceptable", answered
  // by the one implementation that owns it. A second copy of the /app/ prefix
  // test is a second thing to keep in step.
  return safeReturnTo(here) === here ? here : null
}

export interface UpgradeHrefOptions {
  source: UpgradeSource
  /** PaywallModal's specific wall, when there is one. */
  reason?: string
  /** Slug only, for the persona_locked name lookup. Never a display name. */
  persona?: string
  /** Where Close goes. Omit or pass null to accept the default destination. */
  returnTo?: string | null
}

/**
 * The upgrade URL for one surface.
 *
 * URLSearchParams only ever receives defined values here, so no key can
 * serialize as the literal string "undefined" — each optional key is omitted
 * entirely when absent, and the encoding is done once, here.
 */
export function upgradeHref(opts: UpgradeHrefOptions): string {
  const params = new URLSearchParams({ source: opts.source })
  if (opts.reason) params.set('reason', opts.reason)
  if (opts.persona) params.set('persona', opts.persona)
  if (opts.returnTo) params.set(RETURN_TO_PARAM, opts.returnTo)
  return `/app/upgrade?${params.toString()}`
}
