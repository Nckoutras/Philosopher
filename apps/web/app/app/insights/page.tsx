'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Insight, RecentSavedLine } from '@/lib/api'
import { formatItemDate } from '@/lib/formatItemDate'
import InsightCard from '@/components/chat/InsightCard'
import { useInsightDoors } from '@/lib/useInsightDoors'
import SubPageNav from '@/components/layout/SubPageNav'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import SharePreviewModal from '@/components/share/SharePreviewModal'

export default function InsightsPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const markAllInsightsSeen = useStore((s) => s.markAllInsightsSeen)
  const { primary, doubt, discard } = useInsightDoors()
  const [insights, setInsights] = useState<Insight[]>([])
  const [recentLine, setRecentLine] = useState<RecentSavedLine | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        const [all, line] = await Promise.allSettled([
          api.getInsights(),
          api.getRecentSavedLine(),
        ])
        // created_at desc, non-dismissed only.
        if (all.status === 'fulfilled') {
          const nonDismissed = all.value.filter((i) => !i.is_dismissed)
          setInsights(nonDismissed)
          // Visiting the Insights list is the "seen" moment: clear the Home tile
          // star, the tab star's insight part, and the library glows together.
          // Uses the freshly-fetched ids so it also works on a hard load here.
          markAllInsightsSeen(nonDismissed.map((i) => i.id))
        }
        if (line.status === 'fulfilled') setRecentLine(line.value)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router, markAllInsightsSeen])

  function handleCardKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      router.push('/app/reflections')
    }
  }

  // primary/doubt come straight from the shared hook (byte-identical doors across
  // chat, this tab, and Home). Only the optimistic array update is local to this
  // surface, so handleDiscard threads onRemove/onRestore into the hook's discard.
  function handleDiscard(insight: Insight) {
    discard(insight, {
      onRemove: () => setInsights((prev) => prev.filter((i) => i.id !== insight.id)),
      onRestore: () =>
        setInsights((prev) =>
          prev.some((i) => i.id === insight.id) ? prev : [insight, ...prev],
        ),
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
          What the room has witnessed.
        </h1>
      </header>

      {/* ── Your reflections card — relocated from Home ── */}
      {recentLine && (
        <div className="px-[16px] pb-[12px]">
          <div
            role="button"
            tabIndex={0}
            onClick={() => router.push('/app/reflections')}
            onKeyDown={handleCardKeyDown}
            className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px]"
          >
            <p className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal mb-[8px]">
              Your reflections.
            </p>
            <div className="flex items-start gap-[12px]">
              <div className="flex-shrink-0">
                {recentLine.persona_portrait_url ? (
                  <Image
                    src={recentLine.persona_portrait_url}
                    alt={recentLine.persona_name}
                    width={64}
                    height={64}
                    className="rounded-[2px] object-cover"
                  />
                ) : (
                  <div className="w-[64px] h-[64px] bg-linen rounded-[2px] flex items-center justify-center">
                    <span className="font-cormorant text-[24px] font-medium text-charcoal">
                      {recentLine.persona_name.charAt(0)}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <p className="font-cormorant italic text-[17px] font-normal text-ink leading-[1.5] line-clamp-3">
                  &ldquo;{recentLine.content}&rdquo;
                </p>
                <p className="font-lora text-[13px] text-charcoal mt-[6px]">
                  {recentLine.persona_name} · {formatItemDate(recentLine.saved_at)}
                </p>
              </div>
            </div>
            <div className="mt-[10px] flex items-center gap-[8px] flex-wrap">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); router.push(`/app/chat/conv/${recentLine.conversation_id}`) }}
                className="px-[14px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
              >
                Revisit
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setPickerOpen(true) }}
                className="px-[14px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
              >
                Ask another mind
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setShareModalOpen(true) }}
                className="px-[14px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
              >
                Share
              </button>
            </div>
          </div>
          <div className="flex justify-end mt-[8px] px-1">
            <Link
              href="/app/reflections"
              className="font-lora text-[13px] text-bronze underline-offset-2 hover:underline"
            >
              See all reflections →
            </Link>
          </div>
        </div>
      )}

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
              onPrimary={() => primary(insight)}
              onDoubt={() => doubt(insight)}
              onDiscard={() => handleDiscard(insight)}
            />
          ))}
        </div>
      )}

      {recentLine && (
        <PersonaPickerSheet
          open={pickerOpen}
          excludeSlug={recentLine.persona_slug}
          savedLineId={recentLine.saved_line_id}
          sourceContent={recentLine.content}
          onClose={() => setPickerOpen(false)}
          onCreated={(id) => {
            router.push(`/app/chat/conv/${id}`)
            setPickerOpen(false)
          }}
        />
      )}

      {/* Sibling to the reflections card — modal must not be a descendant of
          the role="button" card wrapper */}
      {recentLine && (
        <SharePreviewModal
          isOpen={shareModalOpen}
          onClose={() => setShareModalOpen(false)}
          savedLineId={recentLine.saved_line_id}
          personaName={recentLine.persona_name}
          portraitUrl={recentLine.persona_portrait_url || undefined}
          quote={recentLine.content}
          conversationId={recentLine.conversation_id}
        />
      )}
    </main>
  )
}
