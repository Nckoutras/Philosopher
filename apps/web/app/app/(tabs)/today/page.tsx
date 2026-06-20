'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { ChevronRight } from 'lucide-react'
import { formatItemDate } from '@/lib/formatItemDate'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { DailyQuestion, LastConversation, RecentSavedLine, Insight } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'
import { getGreetingWithName } from '@/lib/useTimeGreeting'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import TodaysTopicCard from '@/components/today/TodaysTopicCard'
import NamePromptCard from '@/components/today/NamePromptCard'
import AppHeader from '@/components/layout/AppHeader'
import SundayLetterCard from '@/components/today/SundayLetterCard'
import InsightCard from '@/components/chat/InsightCard'

// A standing Today insight older than this is treated as stale and not shown,
// so an un-acted insight doesn't linger on the Today screen indefinitely.
const TODAY_INSIGHT_MAX_AGE_DAYS = 14

function formatDateEyebrow(date: Date): string {
  const weekday = date.toLocaleDateString('en-US', { weekday: 'long' }).toUpperCase()
  const month = date.toLocaleDateString('en-US', { month: 'long' }).toUpperCase()
  const day = date.getDate()
  return `${weekday} · ${month} ${day}`
}

function BronzeSparkle() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      className="mx-auto mb-[12px]"
    >
      <line x1="8" y1="1" x2="8" y2="15" stroke="#B89968" strokeWidth="0.7" strokeLinecap="round" />
      <line x1="1" y1="8" x2="15" y2="8" stroke="#B89968" strokeWidth="0.7" strokeLinecap="round" />
      <line x1="3" y1="3" x2="13" y2="13" stroke="#B89968" strokeWidth="0.7" strokeLinecap="round" />
      <line x1="13" y1="3" x2="3" y2="13" stroke="#B89968" strokeWidth="0.7" strokeLinecap="round" />
    </svg>
  )
}

export default function TodayPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'

  const [question, setQuestion] = useState<DailyQuestion | null>(null)
  const [lastConv, setLastConv] = useState<LastConversation | null>(null)
  const [recentLine, setRecentLine] = useState<RecentSavedLine | null>(null)
  const [insight, setInsight] = useState<Insight | null>(null)
  const [loading, setLoading] = useState(true)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [topicPickerOpen, setTopicPickerOpen] = useState(false)
  const [pendingTopic, setPendingTopic] = useState('')

  const namePromptInitialized = useRef(false)
  const [showNamePrompt, setShowNamePrompt] = useState(false)

  const today = new Date()
  const dateEyebrow = formatDateEyebrow(today)
  const isFirstDay = lastConv === null && !loading
  const greeting = isFirstDay ? 'Welcome.' : getGreetingWithName(user?.full_name)

  useEffect(() => {
    if (!loading && !namePromptInitialized.current) {
      namePromptInitialized.current = true
      setShowNamePrompt(!user?.full_name?.trim())
    }
  }, [loading, user])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    async function load() {
      try {
        const [qRes, convRes, lineRes, insightsRes] = await Promise.allSettled([
          api.getTodayQuestion(),
          api.getLastConversation(),
          api.getRecentSavedLine(),
          api.getInsights(),
        ])
        if (qRes.status === 'fulfilled') setQuestion(qRes.value)
        if (convRes.status === 'fulfilled') setLastConv(convRes.value)
        if (lineRes.status === 'fulfilled') setRecentLine(lineRes.value)
        if (insightsRes.status === 'fulfilled') {
          const cutoff = Date.now() - TODAY_INSIGHT_MAX_AGE_DAYS * 24 * 60 * 60 * 1000
          // List is non-dismissed, created_at desc → first within the window is the most recent.
          const recent = insightsRes.value.find(
            (i) => !i.is_dismissed && new Date(i.created_at).getTime() >= cutoff,
          )
          setInsight(recent ?? null)
        }
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token, router])

  function handleFirstDayReflect() {
    setPendingTopic('')
    setTopicPickerOpen(true)
  }

  function handleReflect(topicText: string) {
    setPendingTopic(topicText)
    setTopicPickerOpen(true)
  }

  async function handlePersonaSelected(personaSlug: string) {
    const hasTopic = pendingTopic.trim().length > 0
    try {
      const conv = await api.createConversation(personaSlug, undefined, hasTopic)
      if (hasTopic) localStorage.setItem(`today_topic_draft_${conv.id}`, pendingTopic)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not start conversation. Try again.')
      setTopicPickerOpen(true)
    }
  }

  function handleCardKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      router.push('/app/reflections')
    }
  }

  function handleInsightPrimary() {
    if (!insight) return
    router.push(
      insight.insight_type === 'shift'
        ? '/app/you-vs-you'
        : `/app/mirror?insightId=${insight.id}`,
    )
  }

  function handleInsightDoubt() {
    const current = insight
    if (!current) return
    // Counterview is a stub for now; navigate (do NOT dismiss the insight).
    router.push(`/app/counterview?insightId=${current.id}`)
  }

  async function handleInsightDiscard() {
    const current = insight
    if (!current) return
    setInsight(null)
    try {
      await api.dismissInsight(current.id)
    } catch {
      // Server is_dismissed is the durable no-resurface control; ignore failure.
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum" />
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />
      {/* ── Header ── */}
      <div className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal mb-[4px]">
          {dateEyebrow}
        </p>
        <h1 className="font-cormorant text-[24px] font-medium text-ink leading-tight">
          {greeting}
        </h1>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {/* ── Name capture prompt (nameless users only, session-dismissed) ── */}
        {showNamePrompt && (
          <NamePromptCard onDismiss={() => setShowNamePrompt(false)} />
        )}

        {/* ── Today's topic card ── */}
        {question && user && (
          <TodaysTopicCard
            user={user}
            dailyQuestion={question.question_text}
            onReflect={handleReflect}
          />
        )}

        {/* ── Slice 3b: standing insight card (passive, app-voice; absent when none) ──
            Top billing: when an insight exists it sits above the Continue card;
            with none, Continue stays at the top. */}
        {insight && (
          <InsightCard
            variant="today"
            content={insight.content}
            insightType={insight.insight_type}
            sourceCount={insight.source_count}
            onPrimary={handleInsightPrimary}
            onDoubt={handleInsightDoubt}
            onDiscard={handleInsightDiscard}
          />
        )}

        {/* ── D1a: Continue card (returning user) ── */}
        {!isFirstDay && lastConv && (
          <button
            type="button"
            onClick={() => router.push(`/app/chat/conv/${lastConv.conversation_id}`)}
            className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] flex items-start gap-[12px]"
          >
            <div className="flex-shrink-0">
              {lastConv.persona_portrait_url ? (
                <Image
                  src={lastConv.persona_portrait_url}
                  alt={lastConv.persona_name}
                  width={64}
                  height={64}
                  className="rounded-[2px] object-cover"
                />
              ) : (
                <div className="w-[64px] h-[64px] bg-linen rounded-[2px] flex items-center justify-center">
                  <span className="font-cormorant text-[24px] font-medium text-charcoal">
                    {lastConv.persona_name.charAt(0)}
                  </span>
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal mb-[4px]">
                Continuing.
              </p>
              <p className="font-cormorant text-[20px] font-medium text-ink leading-tight">
                {lastConv.persona_name}
              </p>
              {lastConv.last_message_snippet && (
                <p className="font-lora text-[13px] text-charcoal leading-snug mt-[6px] line-clamp-2">
                  &ldquo;{lastConv.last_message_snippet}&rdquo;
                </p>
              )}
            </div>
            <ChevronRight size={16} strokeWidth={1.5} className="text-sepia flex-shrink-0 self-center" />
          </button>
        )}

        {/* ── D1a: Your reflections card ── */}
        {!isFirstDay && recentLine && (
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
        )}

        {!isFirstDay && recentLine && (
          <div className="flex justify-end mt-[-4px] px-1">
            <Link
              href="/app/reflections"
              className="font-lora text-[13px] text-bronze underline-offset-2 hover:underline"
            >
              See all reflections →
            </Link>
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

        <PersonaPickerSheet
          open={topicPickerOpen}
          onClose={() => setTopicPickerOpen(false)}
          onSelect={handlePersonaSelected}
        />

        {/* Sibling to recentLine card — E2: modal must not be a descendant of
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

        {/* ── D1b: Empty state card (first-day user) ── */}
        {isFirstDay && (
          <div className="bg-paper border border-dashed border-[0.5px] border-edge rounded-md px-[20px] py-[24px]">
            <BronzeSparkle />
            <h2 className="font-cormorant text-[19px] font-normal text-ink text-center leading-snug">
              Your space, beginning to take shape.
            </h2>
            <p className="font-lora text-[13px] text-charcoal text-center leading-[1.6] mt-[8px]">
              Conversations live here once you've started. Begin with today's question above, or
              choose a mind.
            </p>

            <div className="border-t border-[0.5px] border-edge mt-[16px] mb-[16px]" />

            <div className="flex flex-col gap-[13px]">
              {[
                {
                  label: "Answer today's question",
                  desc: 'A single sentence is enough.',
                  icon: (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <rect x="1" y="1" width="10" height="10" rx="1" stroke="#8A7E6A" strokeWidth="1" />
                      <line x1="3" y1="4" x2="9" y2="4" stroke="#8A7E6A" strokeWidth="0.8" />
                      <line x1="3" y1="6" x2="9" y2="6" stroke="#8A7E6A" strokeWidth="0.8" />
                      <line x1="3" y1="8" x2="7" y2="8" stroke="#8A7E6A" strokeWidth="0.8" />
                    </svg>
                  ),
                },
                {
                  label: 'Choose a mind',
                  desc: 'Each thinker offers a different angle.',
                  icon: (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <circle cx="4" cy="6" r="3" stroke="#8A7E6A" strokeWidth="1" />
                      <circle cx="8" cy="6" r="3" stroke="#8A7E6A" strokeWidth="1" />
                    </svg>
                  ),
                },
                {
                  label: 'Save what stays',
                  desc: 'Tap Save line below any reply that lands.',
                  icon: (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <path d="M2 1h8v10l-4-3-4 3V1z" stroke="#B89968" strokeWidth="1" fill="none" />
                    </svg>
                  ),
                },
              ].map(({ label, desc, icon }) => (
                <div key={label} className="flex items-start gap-[10px]">
                  <div className="w-[24px] h-[24px] border border-[0.5px] border-edge flex items-center justify-center flex-shrink-0 rounded-[2px]">
                    {icon}
                  </div>
                  <div>
                    <p className="font-lora text-[13px] font-medium text-ink leading-none">{label}</p>
                    <p className="font-lora text-[12px] text-charcoal leading-[1.45] mt-[2px]">{desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={handleFirstDayReflect}
              className="w-full py-[14px] rounded-sm bg-ink text-vellum font-cormorant text-[17px] font-medium mt-[16px]"
            >
              Start your first conversation.
            </button>
          </div>
        )}

        {!isFirstDay && (
          <SundayLetterCard isPro={isPro} />
        )}

        {/* ── D1a: Explore The Wise Room guide button ── */}
        {!isFirstDay && (
          <button
            type="button"
            onClick={() => router.push('/app/guide')}
            className="w-full py-[14px] rounded-md border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink"
          >
            Explore The Wise Room
          </button>
        )}
      </div>
    </main>
  )
}
