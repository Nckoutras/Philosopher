'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { LastConversation } from '@/lib/api'
import { getGreetingWithName } from '@/lib/useTimeGreeting'
import { useTopicConversation } from '@/lib/useTopicConversation'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import NamePromptCard from '@/components/today/NamePromptCard'
import AppHeader from '@/components/layout/AppHeader'
import SundayLetterCard from '@/components/today/SundayLetterCard'
import RoomNoticedCard from '@/components/today/RoomNoticedCard'
import QuoteNudgeCard from '@/components/today/QuoteNudgeCard'

// Real LQIPs for the four home tiles, minted from the actual public/personas
// source files (16px wide, WebP). Shown as blurred placeholders so the tiles —
// now de-prioritized (no eager preload) — don't pop in from an empty box.
// Regenerate if a tile artwork changes.
const TILE_BLUR: Record<string, string> = {
  '/personas/discuss.webp':
    'data:image/webp;base64,UklGRpQAAABXRUJQVlA4IIgAAAAQBACdASoQABgAPu1kqU2ppaQiMAgBMB2JQBOmUABGWiv18JrvFpD1oAD0SfdRW/Pt0D5ynJrCIeTr5cRJg1U8uoGg1MHrfYXOqImwYpQb/xLz63C4ss0Dr9eoeXuyg68gMFxapAqKQZHrBEP0a94YQZ52HPcnu4hywxVlix/Kpu+SJM6l8AAA',
  '/personas/insights.webp':
    'data:image/webp;base64,UklGRp4AAABXRUJQVlA4IJIAAABwBACdASoQABgAPu1iqU2ppaQiMAgBMB2JZACdMoACL1ltB44ok7c2IbiogAD8dQ3/HrpXu8xu/wsvL8U26ubZ/I0U1dbvDOHTF+EOnrcmCZl+V2nX40vabV3HNwBV1itXe3bff2NAVrCHLxH7mDYfiXAL/cTe5KAv589Z/i6HQLn2hPGIvI7k1YKIH3B8SEwAAA==',
  '/personas/revisit.webp':
    'data:image/webp;base64,UklGRnIAAABXRUJQVlA4IGYAAAAQBACdASoQABgAPu1iqU2ppaOiMAgBMB2JYwCdACFsBfhV+qpslKvzTAD+6a0RV2BfC8YHe14Jak6TOrG0C7+hL3q5cy8LrNzp9Vpkreua6MXvhgXr7uB9k6BrXAlHBE+3YuoKwAA=',
  '/personas/rituals.webp':
    'data:image/webp;base64,UklGRnIAAABXRUJQVlA4IGYAAAAQBACdASoQABgAPu1iqU2ppaOiMAgBMB2JYwCdACHhYT+YqW0ZarfHAAD+70o+xQZ/0C25feXFYKWmCvKhjXZQkC4odq6+1lmI8E2OpRDueZ+J9q4l2fahF2xzrzP8W0AUW5dAAAA=',
}

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

// A single category tile in the Home 2×2 grid: full-bleed artwork with the
// category word centered in white (cormorant) over a soft radial scrim for
// legibility. Square via aspect-square so the four form a clean grid.
function ImageTile({
  src,
  label,
  onClick,
  priority = false,
}: {
  src: string
  label: string
  onClick: () => void
  priority?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="relative aspect-square w-full overflow-hidden rounded-md border border-[0.5px] border-edge shadow-card active:opacity-90 [touch-action:manipulation] [-webkit-tap-highlight-color:transparent]"
    >
      <Image
        src={src}
        alt=""
        fill
        priority={priority}
        sizes="(max-width: 768px) 50vw, 200px"
        placeholder={TILE_BLUR[src] ? 'blur' : 'empty'}
        blurDataURL={TILE_BLUR[src]}
        className="object-cover"
      />
      {/* soft centered radial scrim so the white label stays legible over any artwork */}
      <span
        aria-hidden="true"
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0.45)_0%,transparent_70%)]"
      />
      <span className="absolute inset-0 flex items-center justify-center px-[12px] text-center font-cormorant text-[24px] font-medium text-white leading-tight">
        {label}
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

  const [lastConv, setLastConv] = useState<LastConversation | null>(null)
  const [loading, setLoading] = useState(true)

  // Shared topic → start-conversation wiring (first-day button + /app/discuss).
  const { topicPickerOpen, setTopicPickerOpen, startWithTopic, handlePersonaSelected } =
    useTopicConversation()

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
        // lastConv still drives isFirstDay (greeting, Sunday tile, empty state),
        // even though the "Continuing." card itself now lives in Library.
        const convRes = await api.getLastConversation()
        setLastConv(convRes)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token, router])

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

        {/* ── Home: 2×2 category tile grid (image cards) ── */}
        <div className="grid grid-cols-2 gap-[12px]">
          <ImageTile
            src="/personas/discuss.webp"
            label="Discussion"
            priority
            onClick={() => router.push('/app/discuss')}
          />
          <ImageTile
            src="/personas/insights.webp"
            label="Insights"
            priority
            onClick={() => router.push('/app/insights')}
          />
          <ImageTile
            src="/personas/revisit.webp"
            label="Library"
            onClick={() => router.push('/app/library')}
          />
          <ImageTile
            src="/personas/rituals.webp"
            label="Rituals"
            onClick={() => router.push('/app/rituals')}
          />
        </div>

        {/* ── 5th wide tile: The Sunday Letter (unchanged card) ── */}
        {!isFirstDay && (
          <SundayLetterCard isPro={isPro} />
        )}

        {/* ── "The room noticed": newest non-dismissed insight, if any. Self-
            fetching; renders nothing most days. Inherits the gap-[12px] rhythm. ── */}
        <RoomNoticedCard />

        {/* ── "A line for you": one themed, persona-ranked quote (Pro, daily-capped).
            Self-gating; renders nothing for free users or once shown today. ── */}
        <QuoteNudgeCard isPro={isPro} />

        {/* The "Continuing." card now lives in Library; "Your reflections." in Insights. */}

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
              onClick={() => startWithTopic('')}
              className="w-full py-[14px] rounded-sm bg-ink text-vellum font-cormorant text-[17px] font-medium mt-[16px]"
            >
              Start your first conversation.
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
