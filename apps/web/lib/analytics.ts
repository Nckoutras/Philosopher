// Analytics — PostHog, EU-hosted, behind explicit opt-in consent.
//
// THE CONSENT CONTRACT. PostHog must not initialize, set a cookie, or send a
// byte before the user presses Accept. That is enforced structurally rather
// than by a runtime flag: the SDK is loaded by `import('posthog-js')` inside
// initAnalytics(), which is the only place consent is read as a precondition.
// A user who declines never downloads the library at all.
//
// WHY A STANDALONE localStorage KEY, not a Zustand slice. The persisted store
// hydrates asynchronously (lib/store.ts `hasHydrated` exists because of the
// PR4p hydration regression, CLAUDE.md P-04). A consent value that reads
// `undefined` for one frame would either flash the banner at someone who has
// already accepted, or — worse — let init race ahead of a stored DECLINE.
// A synchronous read has no such window.
//
// SILENT FAILURE (§18). Nothing here ever dereferences `window.posthog`. The
// module holds its own reference, set only after a successful import+init. An
// adblocked or failed SDK leaves it null, so every entry point below no-ops:
// no console errors, no thrown promise, nothing blocking the UI.
import type { PostHog } from 'posthog-js'

export type AnalyticsProps = Record<string, string | number | boolean>

export type ConsentValue = 'granted' | 'denied'

export const CONSENT_KEY = 'tw_analytics_consent'

// Set only after import + init both succeed. Null means "do nothing" in every
// code path, which is also the adblocked case.
let ph: PostHog | null = null
// Guards against a second init from a re-mounted provider or a rapid toggle.
let initStarted = false

const isDev = process.env.NODE_ENV !== 'production'

function debug(...args: unknown[]): void {
  if (isDev) console.debug('[analytics]', ...args)
}

/**
 * The stored choice, or null if the user has not chosen yet.
 *
 * Wrapped because localStorage throws outright in some contexts (Safari private
 * mode, storage disabled by policy) rather than returning null. A throw here
 * must read as "no choice recorded", never as consent.
 */
export function getConsent(): ConsentValue | null {
  try {
    const v = localStorage.getItem(CONSENT_KEY)
    return v === 'granted' || v === 'denied' ? v : null
  } catch {
    return null
  }
}

export function setConsent(value: ConsentValue): void {
  try {
    localStorage.setItem(CONSENT_KEY, value)
  } catch {
    // Storage unavailable: the choice cannot be remembered across reloads, but
    // it must still hold for this session. Callers act on the return of
    // initAnalytics/optOutAnalytics, not on a successful write.
  }
}

/** True once the SDK is loaded and initialized. Exported for tests and the toggle. */
export function isInitialized(): boolean {
  return ph !== null
}

/**
 * Load and start PostHog. No-ops unless consent is currently 'granted'.
 *
 * Safe to call repeatedly — the second call returns immediately. Never throws:
 * a blocked or missing SDK resolves normally with `ph` still null.
 */
export async function initAnalytics(): Promise<void> {
  if (initStarted || ph !== null) return
  if (getConsent() !== 'granted') return
  if (typeof window === 'undefined') return

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  const apiHost = process.env.NEXT_PUBLIC_POSTHOG_HOST
  if (!key || !apiHost) {
    debug('not configured — NEXT_PUBLIC_POSTHOG_KEY/HOST missing')
    return
  }

  initStarted = true
  try {
    const mod = await import('posthog-js')
    const posthog = mod.default
    posthog.init(key, {
      api_host: apiHost,
      // Anonymous visitors still produce $pageview (the landing half of the
      // landing→signup→paid funnel); a person profile is only created once
      // identify() fires after sign-in.
      person_profiles: 'identified_only',
      // Fired manually by PageviewTracker — the App Router does not do a full
      // page load on navigation, so the SDK's own autocapture would record
      // only the first route of a session.
      capture_pageview: false,
    })
    // posthog-js PERSISTS an opt-out (a __ph_opt_in_out_<token> cookie), and
    // init() restores it. Without this, a user who switched Analytics off and
    // back on — or who reloads after re-consenting — gets a successful init
    // whose every capture() is silently dropped inside the SDK. The failure is
    // invisible from our side: capture() still returns normally.
    if (posthog.has_opted_out_capturing()) posthog.opt_in_capturing()
    ph = posthog
  } catch {
    // Adblock, offline, CDN failure. Stay silent and stay off.
    initStarted = false
    debug('SDK unavailable — analytics disabled for this session')
  }
}

/**
 * Stop capturing and drop the cookie. Used by the Account toggle.
 *
 * opt_out_capturing() is called before the reference is dropped so the SDK
 * clears its own cookie; without it a disabled toggle would leave the id
 * cookie sitting in the browser.
 */
export function optOutAnalytics(): void {
  try {
    ph?.opt_out_capturing()
    ph?.reset()
  } catch {
    // A half-initialized SDK is still a successful opt-out from our side.
  }
  ph = null
  initStarted = false
}

export function track(event: string, props?: AnalyticsProps): void {
  if (!ph) {
    debug(event, props ?? {})
    return
  }
  try {
    ph.capture(event, props)
  } catch {
    // Never let a capture failure surface in a click handler.
  }
}

/**
 * Attach subsequent events to a known user.
 *
 * The internal user id ONLY. An email must never become a distinct_id or a
 * person property — the guard below is deliberate belt-and-braces next to the
 * call site's own discipline, because a distinct_id is effectively permanent
 * once written and there is no cheap way to unsend one.
 */
export function identify(userId: string): void {
  if (!userId || userId.includes('@')) {
    debug('identify refused — id must be an internal user id, not an email')
    return
  }
  if (!ph) return
  try {
    ph.identify(userId)
  } catch {
    // As above.
  }
}

/** Called on sign-out, before the full-page redirect. */
export function resetAnalytics(): void {
  try {
    ph?.reset()
  } catch {
    // As above.
  }
}
