'use client'

import { useEffect } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

// Mirrors InsightBootstrap: a shell-level loader that tells the tab bar whether a
// Sunday/season letter is waiting unread, so the "something new" star can light
// without the letters page being open. `read_at` (set server-side when a letter
// detail is opened) is the source of truth — no client seen-tracking. Pro-gated
// because the letters list 403s for non-Pro; the store state is transient, so a
// downgrade simply yields an empty list on the next mount (no stale star).
export default function LettersBootstrap() {
  const token = useStore((s) => s.token)
  const plan = useStore((s) => s.plan)
  const setUnreadLetterIds = useStore((s) => s.setUnreadLetterIds)

  useEffect(() => {
    if (!token || plan === 'free') return
    api
      .getWeeklyLetters()
      .then((letters) => {
        // Weekly AND monthly share this table; one unified "unread letter" signal.
        const ids = letters
          .filter((l) => l.status === 'generated' && l.read_at === null)
          .map((l) => l.id)
        setUnreadLetterIds(ids)
      })
      .catch(() => {})
  }, [token, plan, setUnreadLetterIds])

  return null
}
