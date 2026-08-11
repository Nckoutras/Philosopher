'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { signOut } from '@/lib/auth'

// How long the tab must have gone unrefreshed before a return to the foreground
// slides the session again. Well under the 7-day token life, and long enough that
// ordinary tab-switching costs nothing.
const FOREGROUND_REFRESH_INTERVAL_MS = 12 * 60 * 60 * 1000

export default function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  )

  // Register the global 401 self-heal handler once. When any authenticated
  // request returns 401 (expired/invalid JWT), clear the session and route to
  // sign-in. Guard (b): if the user is already on an /auth page (e.g. a stray
  // background call 401s during the sign-in flow), clear tokens but do NOT
  // redirect — never bounce an in-progress verify.
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      const onAuthPage = window.location.pathname.startsWith('/auth')
      signOut({ redirect: !onAuthPage })
    })
  }, [])

  // A11 — sliding session. JWT expiry runs from ISSUE, not from last use, so a
  // user who opened the app every day was still logged out on day 7. Refresh on
  // app load and on return to the foreground: those are the moments that reach
  // someone who has been AWAY, which is exactly the user at risk. (A response
  // header would only ever refresh someone already making successful requests.)
  //
  // Fire-and-forget by construction — refreshSession never throws and never
  // clears the session, so this can neither block app load nor surface an error.
  // A genuinely dead token is handled by the 401 self-heal registered above.
  useEffect(() => {
    let lastRefresh = 0

    const maybeRefresh = () => {
      if (Date.now() - lastRefresh < FOREGROUND_REFRESH_INTERVAL_MS) return
      lastRefresh = Date.now()
      void api.refreshSession()
    }

    maybeRefresh()

    const onVisibility = () => {
      if (document.visibilityState === 'visible') maybeRefresh()
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
