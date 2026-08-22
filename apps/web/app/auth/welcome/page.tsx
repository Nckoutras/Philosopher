'use client'

/**
 * Shown ONCE, immediately after an OTP verification that CREATED the account.
 *
 * Sign-in is passwordless and account creation is implicit: verifying a code for an
 * email with no user row creates one (routers/auth.py:198). Every screen after that was
 * byte-identical whether you signed in or just created an account — so a UAT tester who
 * typed a gmail address instead of her yahoo one landed in a brand-new empty account
 * that looked exactly like her real one. Her activity ended up split across two
 * accounts, and a weekly letter went to the accidental one while her real account got
 * none. She did not know the second account existed.
 *
 * WHY HERE AND NOT ON THE ENTRY SCREEN. Telling an unauthenticated caller whether an
 * email is known is account enumeration. By this point the user has proven control of
 * the mailbox, so naming the address leaks nothing they do not already have.
 *
 * WHY BEFORE THE DISCLAIMER. A new account normally still needs the disclaimer, and
 * `Continue` forwards there when it does — this screen cannot swallow it. Welcome comes
 * first so the user is not asked to accept terms under an account they are about to
 * abandon. It also means disclaimer/page.tsx needs no change at all: it still ends at
 * /app/today exactly as before.
 *
 * The just-created account is left in the database. An orphaned empty row is harmless;
 * deleting a row the user has just proven they own is a larger, riskier change.
 */

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { signOut } from '@/lib/auth'

export default function WelcomePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)

  // The email is read from the store, never from a query param — it must not appear in
  // a URL or in browser history.
  const email = user?.email ?? ''

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  function handleContinue() {
    // The disclaimer gate is the SAME value verify/page.tsx reads. A new account that
    // still needs it goes there; only an account that does not goes straight to Today.
    if (user?.needs_disclaimer) {
      router.replace('/auth/disclaimer')
    } else {
      router.replace('/app/today')
    }
  }

  function handleDifferentEmail() {
    // The canonical "become signed out" — clears the ph_token cookie, localStorage and
    // the persisted store. redirect:false because it would otherwise send the user to
    // /auth?mode=signin; this flow goes to /auth.
    signOut({ redirect: false })
    router.replace('/auth')
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
              Your account has been created
            </h1>
            <p className="font-lora text-[13px] text-charcoal">{email}</p>
          </header>

          <p className="font-lora text-[13px] text-charcoal leading-[1.65] text-center">
            If you expected to find previous conversations here, you may have signed in
            with a different email.
          </p>

          <div className="space-y-4">
            <button
              type="button"
              onClick={handleContinue}
              className="w-full h-[52px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
            >
              Continue
            </button>

            <button
              type="button"
              onClick={handleDifferentEmail}
              className="w-full font-lora text-[13px] text-sepia underline underline-offset-2 decoration-[0.5px] text-center"
            >
              Use a different email
            </button>
          </div>

        </div>
      </div>
    </main>
  )
}
