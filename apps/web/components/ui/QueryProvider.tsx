'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { signOut } from '@/lib/auth'

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

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
