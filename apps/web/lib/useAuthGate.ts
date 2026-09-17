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
// WHY `useStore.persist.hasHydrated()` AND NOT THE `hasHydrated` STORE FIELD.
// The field is set inside onRehydrateStorage (store.ts:397-400), whose callback
// ignores its error argument and skips the write when `state` is undefined — a
// private window, blocked site data, a throwing storage. A guard blocking on the
// field would then wait FOREVER. The persist API reports hydration finishing
// either way. (PR4p, per CLAUDE.md P-04, is this exact class: a hydration guard
// that passed review and unit tests and hung in the production build.)
//
// The three-step dance below is lifted verbatim from the one page that already
// did this correctly (account/page.tsx), and it is all load-bearing:
//   hasHydrated()        — already finished before this component mounted
//   onFinishHydration    — finishes after
//   rehydrate()          — nothing started it; force one rather than wait
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
    return unsub
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
    // fall through to DEFAULT_RETURN_TO. A `next=` that the consumer would throw
    // away is noise in a URL a person may see.
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
