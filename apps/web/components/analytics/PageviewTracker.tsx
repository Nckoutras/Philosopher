'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { track } from '@/lib/analytics'

/**
 * Manual $pageview on every App Router navigation.
 *
 * The router does not do a full page load between routes, so the SDK's own
 * autocapture would record only the first route of a session — hence
 * capture_pageview:false at init and this component.
 *
 * MUST be rendered inside a <Suspense> boundary. useSearchParams() without one
 * fails the production build (the house workaround is split-component +
 * Suspense — see library/page.tsx, auth/page.tsx, auth/verify, oauth/finish).
 *
 * Query strings are kept deliberately: /app/upgrade?source=…&reason=… is the
 * funnel data #576 started emitting, and it only exists in $current_url.
 */
export default function PageviewTracker() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!pathname) return
    const qs = searchParams?.toString()
    // track() is a no-op until consent + init, so this is safe to fire on every
    // navigation regardless of consent state.
    track('$pageview', { $current_url: qs ? `${pathname}?${qs}` : pathname })
  }, [pathname, searchParams])

  return null
}
