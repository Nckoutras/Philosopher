'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { ChevronRight, MessageCircle, Archive, Sparkles } from 'lucide-react'
import { ReturningPathIcon } from '@/components/icons/RitualIcons'
import { formatItemDate } from '@/lib/formatItemDate'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { DailyQuestion, LastConversation, RecentSavedLine } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'
import { getGreetingWithName } from '@/lib/useTimeGreeting'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import TodaysTopicCard from '@/components/today/TodaysTopicCard'
import NamePromptCard from '@/components/today/NamePromptCard'
import AppHeader from '@/components/layout/AppHeader'
import SundayLetterCard from '@/components/today/SundayLetterCard'

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

// A single category tile in the Home 2×2 grid. Typographic (DS v5 vellum/bronze):
// icon + cormorant label + one-line lora descriptor. Square via aspect-square so the
// four form a clean grid. `active` reflects the Discussion tile's expanded state.
function HomeTile({
  icon,
  label,
  desc,
  active = false,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  desc: string
  active?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={[
        'aspect-square w-full text-left rounded-md border border-[0.5px] px-[16px] py-[14px]',
        'flex flex-col justify-between shadow-card transition-colors active:opacity-80',
        '[touch-action:manipulation] [-webkit-tap-highlight-color:transparent]',
        active ? 'bg-linen border-bronze text-ink' : 'bg-paper border-edge text-ink',
      ].join(' ')}
    >
      <span className="text-bronze">{icon}</span>
      <span className="block">
        <span className="block font-cormorant text-[20px] font-medium text-ink leading-tight">
          {label}
        </span>
        <span className="block font-lora text-[13px] text-charcoal leading-[1.4] mt-[4px]">
          {desc}
        </span>
      </span>
    </button>
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
  const [loading, setLoading] = useState(true)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [topicPickerOpen, setTopicPickerOpen] = useState(false)
  const [pendingTopic, setPendingTopic] = useState('')
  // Discussion tile expands the "What brings you here?" card inline below the grid.
  const [showDiscussion, setShowDiscussion] = useState(false)

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
        const [qRes, convRes, lineRes] = await Promise.allSettled([
          api.getTodayQuestion(),
          api.getLastConversation(),
          api.getRecentSavedLine(),
        ])
        if (qRes.status === 'fulfilled') setQuestion(qRes.value)
        if (convRes.status === 'fulfilled') setLastConv(convRes.value)
        if (lineRes.status === 'fulfilled') setRecentLine(lineRes.value)
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

        {/* ── Home: 2×2 category tile grid ── */}
        <div className="grid grid-cols-2 gap-[12px]">
          <HomeTile
            icon={<MessageCircle size={22} strokeWidth={1.5} />}
            label="Discussion"
            desc="Bring what's on your mind."
            active={showDiscussion}
            onClick={() => setShowDiscussion((v) => !v)}
          />
          <HomeTile
            icon={<Sparkles size={22} strokeWidth={1.5} />}
            label="Insights"
            desc="What the room has noticed."
            onClick={() => router.push('/app/insights')}
          />
          <HomeTile
            icon={<Archive size={22} strokeWidth={1.5} />}
            label="Library"
            desc="Your conversations and minds."
            onClick={() => router.push('/app/library')}
          />
          <HomeTile
            icon={<ReturningPathIcon size={22} strokeWidth={1.5} />}
            label="Rituals"
            desc="Your reflective practices."
            onClick={() => router.push('/app/rituals')}
          />
        </div>

        {/* ── Discussion tile: inline-expanded "What brings you here?" card ── */}
        {showDiscussion && question && user && (
          <TodaysTopicCard
            user={user}
            dailyQuestion={question.question_text}
            onReflect={handleReflect}
          />
        )}

        {/* ── 5th wide tile: The Sunday Letter (unchanged card) ── */}
        {!isFirstDay && (
          <SundayLetterCard isPro={isPro} />
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

        {/* ── D1a: Explore The Wise Room guide button (PR-B replaces with Explore tab) ── */}
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
