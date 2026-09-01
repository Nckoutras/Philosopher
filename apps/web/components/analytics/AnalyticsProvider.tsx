'use client'

import { Suspense, useEffect, useState } from 'react'
import { useStore } from '@/lib/store'
import { getConsent, initAnalytics, identify, type ConsentValue } from '@/lib/analytics'
import ConsentBanner from './ConsentBanner'
import PageviewTracker from './PageviewTracker'

/**
 * Owns the consent lifecycle for the whole app. Mounted once in the root
 * layout, inside QueryProvider — root and not (tabs), because (tabs) does not
 * wrap the landing page, /auth, /app/chat, /app/upgrade or /legal, and the
 * funnel this exists to measure starts on a route (tabs) never sees.
 *
 * Renders nothing but the banner and the (Suspense-wrapped) pageview tracker.
 */
export default function AnalyticsProvider() {
  // `undefined` = not read yet (SSR and first paint). The banner must not
  // render in that state or it flashes on every load for someone who already
  // chose. `null` = read, and no choice stored.
  const [consent, setConsentState] = useState<ConsentValue | null | undefined>(undefined)
  const userId = useStore((s) => s.user?.id)

  useEffect(() => {
    const stored = getConsent()
    setConsentState(stored)
    if (stored === 'granted') void initAnalytics()
  }, [])

  // Keyed off the user id rather than the two setAuth() call sites: a returning
  // user with a persisted token re-enters through SubscriptionBootstrap's
  // api.me() and hits neither sign-in path, so identifying there only would
  // leave them anonymous forever. identify() is idempotent, and it no-ops until
  // the SDK is up.
  useEffect(() => {
    if (!userId) return
    identify(userId)
  }, [userId, consent])

  return (
    <>
      <Suspense fallback={null}>
        <PageviewTracker />
      </Suspense>
      {consent === null && <ConsentBanner onChoice={setConsentState} />}
    </>
  )
}
