'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

export const dynamic = 'force-dynamic'

function OAuthFinish() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const attempted = useRef(false)

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true

    const token = searchParams.get('token')
    const needsDisclaimer = searchParams.get('needs_disclaimer') === '1'
    // Set by the callback when THIS sign-in created the account (A8b). An absent
    // parameter reads as false, so a redirect from an older backend behaves exactly as
    // it did before this change.
    const isNewAccount = searchParams.get('new_account') === '1'

    if (!token) {
      toast.error('Sign-in failed. Please try again.')
      router.replace('/auth?error=oauth_no_token')
      return
    }

    async function finish() {
      try {
        api.setToken(token)
        const user = await api.me()
        // LOAD-BEARING ORDER — setAuth MUST stay before the navigation below.
        // /auth/welcome reads `needs_disclaimer` from the STORE, not from a query
        // param. If this line moves after the navigation, welcome reads an empty store,
        // its Continue falls through to /app/today, and every new Google user skips the
        // disclaimer — a legal-consent gap with no failing test to catch it, because
        // the routing itself would still look correct.
        useStore.getState().setAuth(user, token)
        if (isNewAccount) {
          // This callback CREATED the account. Say so before anything else — the user
          // may have picked a Google account they did not mean to use. /auth/welcome
          // forwards to the disclaimer when it is still needed, so this cannot skip it.
          router.replace('/auth/welcome')
        } else if (needsDisclaimer) {
          router.replace('/auth/disclaimer')
        } else {
          router.replace('/app/today')
        }
      } catch {
        api.setToken(null)
        toast.error('Sign-in failed. Please try again.')
        router.replace('/auth')
      }
    }

    finish()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
      <p className="font-lora text-[13px] text-charcoal">Signing you in…</p>
    </main>
  )
}

export default function OAuthFinishPage() {
  return (
    <Suspense fallback={null}>
      <OAuthFinish />
    </Suspense>
  )
}
