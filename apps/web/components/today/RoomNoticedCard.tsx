'use client'

import { useEffect, useState } from 'react'
import { api, type Insight } from '@/lib/api'
import { useInsightDoors } from '@/lib/useInsightDoors'
import { markSeen, unmarkSeen, pruneSeen } from '@/lib/roomNoticedSeen'
import InsightCard from '@/components/chat/InsightCard'

// Home surface for the newest non-dismissed insight of ANY type the user hasn't
// already acted on FROM THIS CARD. Self-fetching (SundayLetterCard pattern):
// GET /insights (no conversation_id) returns non-dismissed, created_at desc. The
// same list is the Insights archive, so surfacing [0] verbatim showed the newest
// insight in both places at once; we instead pick the newest id NOT in the
// client "seen" set (wr_roomnoticed_seen) so the nudge stops repeating what the
// user has opened/doubted/discarded here. Renders nothing when none is unseen.
//
// The existing insight gate (6h throttle + one-per-conversation) IS the budget;
// this only surfaces what already exists. Section eyebrow "THE ROOM NOTICED" sits
// above an unmodified InsightCard variant='today'. Doors come from the shared
// useInsightDoors hook (unchanged): Primary/Doubt navigate away (this page
// unmounts); Discard is the same 5s-undo real dismiss everywhere. Acting on any
// door marks the id seen; a discard Undo un-marks it so it can return.
export default function RoomNoticedCard() {
  const [insight, setInsight] = useState<Insight | null>(null)
  const { primary, doubt, discard } = useInsightDoors()

  useEffect(() => {
    let cancelled = false
    api
      .getInsights()
      .then((list) => {
        if (cancelled) return
        // Self-clean the seen set against the live (non-dismissed) list, then
        // surface the newest insight this device hasn't already acted on here.
        const seen = new Set(pruneSeen(list.map((i) => i.id)))
        setInsight(list.find((i) => !seen.has(i.id)) ?? null)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  if (!insight) return null

  const current = insight

  return (
    <section>
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[8px]">
        THE ROOM NOTICED
      </p>
      <InsightCard
        variant="today"
        content={current.content}
        insightType={current.insight_type}
        sourceCount={current.source_count}
        onPrimary={() => { markSeen(current.id); primary(current) }}
        onDoubt={() => { markSeen(current.id); doubt(current) }}
        onDiscard={() =>
          discard(current, {
            // Commit: mark seen so an opened-but-not-yet-dismissed insight can't
            // re-nudge before the 5s server dismiss lands. Undo: un-mark so the
            // restored insight returns to Home.
            onRemove: () => { markSeen(current.id); setInsight(null) },
            onRestore: () => { unmarkSeen(current.id); setInsight(current) },
          })
        }
      />
    </section>
  )
}
