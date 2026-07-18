'use client'

import { useEffect } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

export default function SubscriptionBootstrap() {
  const token = useStore((s) => s.token)
  const setSubscription = useStore((s) => s.setSubscription)
  const setUser = useStore((s) => s.setUser)
  const setDeepRemaining = useStore((s) => s.setDeepRemaining)

  useEffect(() => {
    if (!token) return
    api.getSubscription().then(setSubscription).catch(() => {})
    // Seed the live deep-mode counter from /me so the chip's lock gate is
    // accurate on boot. This layout wraps the (tabs) routes, NOT the chat
    // routes, so on a deep-link / hard-refresh straight into a chat this never
    // runs and deepRemaining stays -1 → the chip fails OPEN (never locks). That
    // is intentional: the chip is cosmetic, the backend metering is the source
    // of truth (an exhausted free user still won't get a deep reply), and the
    // next send-stream 'start' event corrects deepRemaining so the chip locks.
    // Do not add complexity to close this gap — fail-open on a cosmetic lock is
    // the correct behaviour.
    api.me()
      .then((u) => {
        setUser(u)
        if (typeof u.deep_remaining === 'number') setDeepRemaining(u.deep_remaining)
      })
      .catch(() => {})
  }, [token, setSubscription, setUser, setDeepRemaining])

  return null
}
