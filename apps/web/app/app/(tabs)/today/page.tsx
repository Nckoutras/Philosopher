'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { ChevronRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api, ShareLimitError } from '@/lib/api'
import type { DailyQuestion, LastConversation, RecentSavedLine } from '@/lib/api'
import { getTimeGreeting } from '@/lib/useTimeGreeting'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import RitualsCard from '@/components/today/RitualsCard'
import TodaysTopicCard from '@/components/today/TodaysTopicCard'
import AppHeader from '@/components/layout/AppHeader'

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
  const activePersonaSlug = useStore((s) => s.activePersonaSlug)
  const user = useStore((s) => s.user)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'

  const [question, setQuestion] = useState<DailyQuestion | null>(null)
  const [lastConv, setLastConv] = useState<LastConversation | null>(null)
  const [recentLine, setRecentLine] = useState<RecentSavedLine | null>(null)
  const [loading, setLoading] = useState(true)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [shareLoading, setShareLoading] = useState(false)
  const [topicPickerOpen, setTopicPickerOpen] = useState(false)
  const [pendingTopic, setPendingTopic] = useState('')

  const today = new Date()
  const dateEyebrow = formatDateEyebrow(today)
  const isFirstDay = lastConv === null && !loading
  const greeting = isFirstDay ? 'Welcome.' : getTimeGreeting()

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
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

  useEffect(() => {
    window.history.pushState({ floor: 'today' }, '', '/app/today')
    function handlePopState() {
      window.history.pushState({ floor: 'today' }, '', '/app/today')
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  async function handleFirstDayReflect() {
    if (!question) return
    const slug = activePersonaSlug ?? 'marcus_aurelius'
    try {
      const conv = await api.createConversation(slug)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch {
      router.push('/app/library')
    }
  }

  function handleReflect(topicText: string) {
    setPendingTopic(topicText)
    setTopicPickerOpen(true)
  }

  async function handlePersonaSelected(personaSlug: string) {
    try {
      const conv = await api.createConversation(personaSlug, undefined, true)
      localStorage.setItem(`today_topic_draft_${conv.id}`, pendingTopic)
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

  async function handleShare(savedLineId: string, personaName: string, content: string, conversationId: string) {
    const shortShareText = `${personaName} told me:\nthegreatminds.app`
    const fullShareText  = `${personaName} told me:\n\n${content}\n\nthegreatminds.app`
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    const url = `${origin}/app/chat/conv/${conversationId}`

    setShareLoading(true)
    try {
      const blob = await api.createShareScreenshot(savedLineId)
      const file = new File([blob], 'reflection.png', { type: 'image/png' })

      if (typeof navigator !== 'undefined' && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], text: shortShareText })
      } else {
        // Desktop / no Web Share Level 2: download image + copy full text
        const blobUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = blobUrl
        a.download = 'reflection.png'
        a.click()
        URL.revokeObjectURL(blobUrl)
        await navigator.clipboard.writeText(fullShareText + '\n' + url).catch(() => {})
        toast('Image saved — share it from your downloads')
      }
    } catch (err) {
      if (err instanceof ShareLimitError) {
        toast((t) => (
          <span>
            Free share limit reached (3/90 days).{' '}
            <a
              href="/app/upgrade"
              onClick={() => toast.dismiss(t.id)}
              style={{ textDecoration: 'underline' }}
            >
              Upgrade
            </a>
          </span>
        ))
        return
      }
      // Fallback: text-only share
      try {
        if (typeof navigator !== 'undefined' && navigator.share) {
          await navigator.share({ title: 'Great Minds', text: fullShareText, url })
        } else {
          await navigator.clipboard.writeText(fullShareText + '\n' + url)
          toast('Copied to clipboard')
        }
      } catch {
        // user cancelled
      }
    } finally {
      setShareLoading(false)
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
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[4px]">
          {dateEyebrow}
        </p>
        <h1 className="font-cormorant text-[24px] font-normal text-ink leading-tight">
          {greeting}
        </h1>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {/* ── Today's topic card ── */}
        {question && user && (
          <TodaysTopicCard
            user={user}
            dailyQuestion={question.question_text}
            onReflect={handleReflect}
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
              <p className="font-lora text-[10px] font-medium uppercase tracking-[0.18em] text-sepia mb-[4px]">
                Continuing.
              </p>
              <p className="font-cormorant text-[17px] font-semibold text-ink leading-tight">
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
            <p className="font-lora text-[10px] font-medium uppercase tracking-[0.18em] text-sepia mb-[8px]">
              Your reflections.
            </p>
            <p className="font-cormorant italic text-[17px] font-normal text-ink leading-[1.5] line-clamp-3">
              &ldquo;{recentLine.content}&rdquo;
            </p>
            <div className="mt-[8px] flex items-center gap-[6px]">
              {recentLine.persona_portrait_url ? (
                <img
                  src={recentLine.persona_portrait_url}
                  alt={recentLine.persona_name}
                  width={64}
                  height={64}
                  className="rounded-[2px] object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-[64px] h-[64px] bg-linen rounded-[2px] flex items-center justify-center flex-shrink-0">
                  <span className="font-cormorant text-[24px] font-medium text-charcoal">
                    {recentLine.persona_name.charAt(0)}
                  </span>
                </div>
              )}
              <span className="font-lora text-[11px] text-sepia">
                {recentLine.persona_name} · {formatDistanceToNow(new Date(recentLine.saved_at), { addSuffix: true })}
              </span>
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
                onClick={(e) => { e.stopPropagation(); handleShare(recentLine.saved_line_id, recentLine.persona_name, recentLine.content, recentLine.conversation_id) }}
                disabled={shareLoading}
                className="px-[14px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal disabled:opacity-50"
              >
                {shareLoading ? 'Sharing…' : 'Share'}
              </button>
            </div>
          </div>
        )}

        {/* ── Rituals card ── */}
        {!isFirstDay && (
          <RitualsCard
            isPro={isPro ?? false}
            userEmail={user?.email ?? ''}
          />
        )}

        {recentLine && (
          <PersonaPickerSheet
            open={pickerOpen}
            excludeSlug={recentLine.persona_slug}
            savedLineId={recentLine.saved_line_id}
            sourceContent={recentLine.content}
            onClose={() => setPickerOpen(false)}
            onCreated={(id) => {
              setPickerOpen(false)
              router.push(`/app/chat/conv/${id}`)
            }}
          />
        )}

        <PersonaPickerSheet
          open={topicPickerOpen}
          onClose={() => setTopicPickerOpen(false)}
          onSelect={handlePersonaSelected}
        />

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

        {/* ── D1a: Start fresh button ── */}
        {!isFirstDay && (
          <button
            type="button"
            onClick={() => router.push('/app/welcome')}
            className="w-full py-[14px] rounded-md border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink"
          >
            Start fresh
          </button>
        )}
      </div>
    </main>
  )
}
