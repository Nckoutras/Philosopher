import { api } from './api'
import { useStore } from './store'
import { resetAnalytics } from './analytics'

/**
 * The single definition of "become signed out."
 *
 * Clears all three token stores that a session lives in:
 *   - the ph_token cookie (read by middleware) and the ph_token localStorage
 *     key (read by api.loadToken), both via api.setToken(null)
 *   - the persisted Zustand store (user/token/subscription/plan) via clearAuth()
 *
 * Then, by default, does a full-page redirect to the sign-in screen so no stale
 * in-memory React state survives.
 *
 * Callers:
 *   - the account page Sign out button — signOut() (redirect: true)
 *   - the global 401 self-heal handler — redirect suppressed when the user is
 *     already on an /auth page, so an expired background request can never bounce
 *     an in-progress sign-in / OTP-verify flow.
 */
export function signOut({ redirect = true }: { redirect?: boolean } = {}): void {
  api.setToken(null)
  useStore.getState().clearAuth()
  // Before the redirect below, not after: window.location.replace tears the
  // page down, so a reset queued afterwards would never run and the next user
  // of this browser would inherit the previous distinct_id.
  resetAnalytics()
  if (redirect && typeof window !== 'undefined') {
    window.location.replace('/auth?mode=signin')
  }
}
