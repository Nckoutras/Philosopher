'use client'

import { Suspense, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { consumeShareRef } from '@/lib/consumeShareRef'
import { useStore } from '@/lib/store'
import { safeReturnTo } from '@/lib/safeReturnTo'

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

    // Takes the token as a parameter: TypeScript does not carry the `!token`
    // narrowing above into a nested function, so the closure saw `string | null`.
    async function finish(token: string) {
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

        // PR-2 — the OAuth half of attribution, and the reason it lives here at
        // all rather than at the creation point. The account was created in the
        // server-to-server callback from Google: no browser was present, so
        // nothing there could read the localStorage the share reference lives
        // in. This is the first moment a client exists again.
        //
        // Before the redirect, and after setAuth so the request carries a token.
        // Identical rule to the OTP path, in the same helper: attribute when new,
        // clear either way.
        await consumeShareRef(isNewAccount)

        if (isNewAccount) {
          // This callback CREATED the account. Say so before anything else — the user
          // may have picked a Google account they did not mean to use. /auth/welcome
          // forwards to the disclaimer when it is still needed, so this cannot skip it.
          router.replace('/auth/welcome')
        } else if (needsDisclaimer) {
          router.replace('/auth/disclaimer')
        } else {
          // The LAST branch only, matching the OTP path exactly. `next` arrives
          // from the API, which read it out of the Redis CSRF state entry and had
          // already validated it before storing -- revalidated here regardless,
          // because a query parameter is a query parameter wherever it came from.
          router.replace(safeReturnTo(searchParams.get('next')))
        }
      } catch {
        api.setToken(null)
        toast.error('Sign-in failed. Please try again.')
        router.replace('/auth')
      }
    }

    finish(token)
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
