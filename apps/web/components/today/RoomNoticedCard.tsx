'use client'

import { useEffect, useState } from 'react'
import { api, type Insight } from '@/lib/api'
import { useInsightDoors } from '@/lib/useInsightDoors'
import InsightCard from '@/components/chat/InsightCard'

// Home surface for the newest non-dismissed insight of ANY type. Self-fetching
// (SundayLetterCard pattern): GET /insights (no conversation_id) returns
// non-dismissed, created_at desc — [0] is the single newest. The existing insight
// gate (6h throttle + one-per-conversation) IS the budget; this only surfaces what
// already exists. Renders nothing when there is none (most days — by design).
//
// Section eyebrow "THE ROOM NOTICED" sits above an unmodified InsightCard
// variant='today'. Doors come from the shared useInsightDoors hook, so behavior is
// byte-identical to the chat chip and the Insights tab. Primary/Doubt navigate
// away (this page unmounts); Discard is the same 5s-undo real dismiss everywhere.
export default function RoomNoticedCard() {
  const [insight, setInsight] = useState<Insight | null>(null)
  const { primary, doubt, discard } = useInsightDoors()

  useEffect(() => {
    let cancelled = false
    api
      .getInsights()
      .then((list) => {
        if (!cancelled) setInsight(list[0] ?? null)
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
        onPrimary={() => primary(current)}
        onDoubt={() => doubt(current)}
        onDiscard={() =>
          discard(current, {
            onRemove: () => setInsight(null),
            onRestore: () => setInsight(current),
          })
        }
      />
    </section>
  )
}
