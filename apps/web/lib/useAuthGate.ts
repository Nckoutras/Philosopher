'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from './store'
import { safeReturnTo } from './safeReturnTo'

// BUG-002. THE ONE AUTH GUARD for every protected page.
//
// WHAT WAS WRONG, and it is not the case anyone assumed. 28 pages guarded with:
//
//     useEffect(() => { if (token === null) router.replace('/auth?mode=signin') }, …)
//
// Two defects in three lines, and the second is the expensive one.
//
// (1) NO HYDRATION GATE. The persisted store rehydrates ASYNCHRONOUSLY, so
//     `token` is null for the first frame of every mount — signed in or not. The
//     guard fires on that frame and bounces a signed-in user to /auth.
//
// (2) NO `next=`. The redirect discards the destination.
//
// THE FAILING CASE IS NOT THE SIGNED-OUT DEEP LINK — that one already works.
// middleware.ts reads the `ph_token` COOKIE synchronously, sees nothing, and
// redirects with `next=` intact (middleware.ts:40). The page never renders.
//
// It is the RETURNING USER WITH A VALID COOKIE. Middleware lets them through,
// the page renders, and the client — reading localStorage through a store that
// has not hydrated yet — decides they are signed out and bounces them bare. Two
// token stores (cookie, localStorage), two read timings (synchronous,
// asynchronous), written together by api.setToken (api.ts:650-655) and read
// apart. That race is what share loop PR-2 lands in the middle of: a stranger
// signs up, gets a cookie, and every later deep link is a coin flip.
//
// NEITHER HYDRATION SIGNAL IS SAFE ON ITS OWN, and an earlier draft of this file
// claimed otherwise. Measured in the library rather than reasoned about —
// `node_modules/zustand/middleware.js:417-430`:
//
//     }).then(function () {
//       postRehydrationCallback(stateFromStorage, undefined)
//       _hasHydrated = true                                  // success only
//       finishHydrationListeners.forEach(cb => cb(stateFromStorage))
//     }).catch(function (e) {
//       postRehydrationCallback(undefined, e)                // error: that is all
//     })
//
// On a storage error the catch runs the rehydration callback and STOPS.
// `_hasHydrated` is never set and the finish listeners never fire — so
// `persist.hasHydrated()` stays false forever and `onFinishHydration` never
// resolves. A private window, blocked site data or a throwing storage hangs BOTH
// mechanisms, not just the store field. That is PR4p's shape (CLAUDE.md P-04):
// a hydration guard that passed review and unit tests and hung in production.
//
// THE DEADLINE BELOW IS WHAT MAKES ANY OF THIS SAFE. It is not a refinement.
// Without it this hook waits forever on a browser that cannot read storage, and
// every protected page renders its loading state with no error and no redirect.
//
// The persist API is still preferred over the `hasHydrated` STORE FIELD
// (store.ts:23,153-154, written at :397-400), which carries the same hole plus
// one of its own: its callback ignores the error argument entirely, so it cannot
// even report the failure it swallows. See TD-83.
//
// The three-step dance below is lifted verbatim from the one page that already
// did this correctly (account/page.tsx), and it is all load-bearing:
//   hasHydrated()        — already finished before this component mounted
//   onFinishHydration    — finishes after
//   rehydrate()          — nothing started it; force one rather than wait
//   the deadline         — none of the three will ever answer
// How long to wait for hydration before deciding without it.
//
// NOT A NETWORK CALL. Reading localStorage is synchronous-ish and completes in
// milliseconds on any healthy browser, so 3s is far outside normal and short
// enough that a person staring at a loading state still gets an answer.
//
// A NAMED JUDGEMENT, like the 10s on the welcome page — not a derivation. The
// honest way to replace it is to measure real hydration latency, if anyone ever
// has cause to care.
//
// WHAT HAPPENS WHEN IT FIRES: `token` is whatever memory holds, which is null,
// so the reader goes to sign-in carrying `next=`. That is the correct answer
// rather than a fallback — a browser that cannot read storage has no session to
// restore, and signing in still works: the cookie and the in-memory store carry
// it for the session even if the localStorage write fails.
const HYDRATION_DEADLINE_MS = 3000

export function useAuthGate(): boolean {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)
  // A redirect is a one-way door; firing it twice races two navigations.
  const redirected = useRef(false)

  useEffect(() => {
    if (useStore.persist.hasHydrated()) {
      setHydrated(true)
      return
    }
    const unsub = useStore.persist.onFinishHydration(() => setHydrated(true))
    void useStore.persist.rehydrate()
    // Decide without hydration rather than wait on it forever. See the deadline's
    // own comment: on a storage error nothing above this line will ever fire.
    const deadline = setTimeout(() => setHydrated(true), HYDRATION_DEADLINE_MS)
    return () => {
      clearTimeout(deadline)
      unsub()
    }
  }, [])

  useEffect(() => {
    // The whole point: decide NOTHING until the store has spoken.
    if (!hydrated) return
    if (token !== null) return
    if (redirected.current) return
    redirected.current = true

    // Carry the destination. Built from the CURRENT location rather than passed
    // in, so no caller can forget it and no page has its own copy of the rule.
    //
    // safeReturnTo is the VALIDATOR, reused rather than reimplemented — it is
    // what /auth/verify and /auth/oauth/finish already apply on the way back in.
    // Using it here means a path it would reject on arrival is never emitted in
    // the first place: it allow-lists `/app/` only, so the two post-auth screens
    // under /auth/* (welcome, disclaimer) correctly send no `next=` at all and
    // fall through to DEFAULT_RETURN_TO.
    //
    // THAT IS RIGHT, NOT A LIMITATION, and the reason is not the allow-list. Those
    // destinations are NOT THE USER'S TO CARRY: the disclaimer gate is driven by
    // `needs_disclaimer` on the user object, not by a URL. Someone who still owes
    // consent is routed there after signing in whether or not anyone asked
    // (auth/verify/page.tsx:84-85, auth/welcome/page.tsx:47-48), and a
    // next=/auth/disclaimer would fight that routing for someone who had already
    // accepted.
    const here = window.location.pathname + window.location.search
    const carry = safeReturnTo(here) === here
    router.replace(
      carry
        ? `/auth?mode=signin&next=${encodeURIComponent(here)}`
        : '/auth?mode=signin',
    )
  }, [hydrated, token, router])

  // False while hydrating AND while signed out — callers must not load data in
  // either state. Signed out is transient here: the redirect above is already
  // in flight.
  return hydrated && token !== null
}
