'use client'

import { useEffect } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

// Only insights from the last two weeks light the discoverability glow; older
// ones are stale and shouldn't nag. Trivially tunable.
const INSIGHT_MAX_AGE_DAYS = 14

export default function InsightBootstrap() {
  const token = useStore((s) => s.token)
  const setActiveInsights = useStore((s) => s.setActiveInsights)

  useEffect(() => {
    if (!token) return
    const cutoff = Date.now() - INSIGHT_MAX_AGE_DAYS * 86400000
    api
      .getInsights()
      .then((list) => {
        const filtered = list.filter(
          (i) => i.conversation_id != null && new Date(i.created_at).getTime() >= cutoff,
        )
        setActiveInsights(filtered)
      })
      .catch(() => {})
  }, [token, setActiveInsights])

  return null
}
