'use client'

import { useEffect } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

export default function SubscriptionBootstrap() {
  const token = useStore((s) => s.token)
  const setSubscription = useStore((s) => s.setSubscription)

  useEffect(() => {
    if (!token) return
    api.getSubscription().then(setSubscription).catch(() => {})
  }, [token, setSubscription])

  return null
}
