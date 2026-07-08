'use client'

import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api, type Insight } from '@/lib/api'
import { renderDiscardUndoToast } from '@/components/chat/discardToast'

// Single source of truth for the four insight "doors" — the primary action per
// type, the Doubt destination, and the 5s-undo discard. Consumed by all three
// surfaces (chat conv/[id], the Insights tab, and the Home "room noticed" card)
// so a dilemma/belief/shift/pattern insight behaves byte-identically wherever it
// appears. isPro is derived here from the store `plan` (the dilemma gate's single
// source of truth), so callers never re-derive it.
//
// Discard is state-agnostic: the shared part (durable dismiss delayed 5s so Undo
// can cancel it, plus the toast) lives here; each caller owns its optimistic UI
// via onRemove/onRestore. The server `is_dismissed` flag is the durable control —
// a discard here is a real dismiss everywhere.
export function useInsightDoors() {
  const router = useRouter()
  const plan = useStore((s) => s.plan)
  const isPro = plan === 'pro' || plan === 'premium'

  // The 4-way primary door. Neither dilemma nor belief dismisses on tap.
  //  - dilemma → the Council (Pro → seed council_prefill/source='nudge'/
  //    conversation; free → the /app/upgrade wall).
  //  - belief  → Counterview (the Doubt-this destination; the primary IS that door).
  //  - shift   → You-vs-You (its own Pro gate downstream).
  //  - else    → reflect in the Mirror.
  function primary(insight: Insight) {
    if (insight.insight_type === 'dilemma') {
      if (!isPro) {
        router.push('/app/upgrade')
        return
      }
      sessionStorage.setItem('council_prefill', insight.content.slice(0, 600))
      sessionStorage.setItem('council_source', 'nudge')
      if (insight.conversation_id) {
        sessionStorage.setItem('council_conversation_id', insight.conversation_id)
      }
      router.push('/app/council')
      return
    }
    if (insight.insight_type === 'belief') {
      router.push(`/app/counterview?insightId=${insight.id}`)
      return
    }
    router.push(
      insight.insight_type === 'shift'
        ? '/app/you-vs-you'
        : `/app/mirror?insightId=${insight.id}`,
    )
  }

  // 'Doubt this' navigates to Counterview and does NOT dismiss the insight.
  function doubt(insight: Insight) {
    router.push(`/app/counterview?insightId=${insight.id}`)
  }

  // Optimistically remove via onRemove, but delay the durable dismiss by 5s so
  // Undo (onRestore) can cancel it. If the window elapses, the PATCH commits.
  function discard(
    insight: Insight,
    { onRemove, onRestore }: { onRemove: () => void; onRestore: () => void },
  ) {
    onRemove()
    const timer = setTimeout(() => {
      api.dismissInsight(insight.id).catch(() => {})
    }, 5000)
    renderDiscardUndoToast(() => {
      clearTimeout(timer)
      onRestore()
    })
  }

  return { primary, doubt, discard }
}
