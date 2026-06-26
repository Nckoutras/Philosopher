'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Insight } from '@/lib/api'
import InsightCard from '@/components/chat/InsightCard'
import { renderDiscardUndoToast } from '@/components/chat/discardToast'
import SubPageNav from '@/components/layout/SubPageNav'

export default function InsightsPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        const all = await api.getInsights()
        // created_at desc, non-dismissed only.
        setInsights(all.filter((i) => !i.is_dismissed))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router])

  function handlePrimary(insight: Insight) {
    router.push(
      insight.insight_type === 'shift'
        ? '/app/you-vs-you'
        : `/app/mirror?insightId=${insight.id}`,
    )
  }

  function handleDoubt(insight: Insight) {
    // Counterview navigation (does NOT dismiss the insight) — mirrors Today.
    router.push(`/app/counterview?insightId=${insight.id}`)
  }

  function handleDiscard(insight: Insight) {
    // Optimistically remove, but delay the durable dismiss by 5s so Undo can
    // cancel it (same contract as the Today insight card).
    setInsights((prev) => prev.filter((i) => i.id !== insight.id))
    const timer = setTimeout(() => {
      api.dismissInsight(insight.id).catch(() => {})
    }, 5000)
    renderDiscardUndoToast(() => {
      clearTimeout(timer)
      setInsights((prev) =>
        prev.some((i) => i.id === insight.id) ? prev : [insight, ...prev],
      )
    })
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/today" />
      </div>

      <header className="px-[24px] pt-[12px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Insights
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          What the room has noticed.
        </h1>
      </header>

      {loading ? (
        <p className="px-[24px] py-[24px] font-lora text-[13px] text-sepia italic">Loading…</p>
      ) : insights.length === 0 ? (
        <p className="px-[24px] py-[24px] font-lora text-[14px] text-sepia italic leading-[1.6]">
          No insights yet. As you reflect, the room will surface patterns it notices here.
        </p>
      ) : (
        <div className="px-[16px] pb-[80px] flex flex-col gap-[12px]">
          {insights.map((insight) => (
            <InsightCard
              key={insight.id}
              variant="today"
              content={insight.content}
              insightType={insight.insight_type}
              sourceCount={insight.source_count}
              onPrimary={() => handlePrimary(insight)}
              onDoubt={() => handleDoubt(insight)}
              onDiscard={() => handleDiscard(insight)}
            />
          ))}
        </div>
      )}
    </main>
  )
}
