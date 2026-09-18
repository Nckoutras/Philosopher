'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { deriveInitials } from '@/lib/initials'
import { THEME_OPTIONS } from '@/lib/themes'

interface Props {
  user: { full_name: string | null; email: string }
  dailyQuestion: string
  onReflect: (topicText: string) => void
}

export default function TodaysTopicCard({ user, dailyQuestion, onReflect }: Props) {
  const router = useRouter()
  const [topic, setTopic] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  // The day's topic arrives as "Title — subtitle": all 50 active rows in
  // production carry the em-dash, and the subtitle half has never been rendered
  // anywhere. Migration 010's older seeded rows carry no dash at all, so the
  // subtitle is optional and the whole string is the title — which is why this
  // is a split-and-rejoin rather than a destructuring of two guaranteed halves.
  const [topicTitle, ...topicRest] = dailyQuestion.split(/\s+—\s+/)
  const topicSubtitle = topicRest.join(' — ').trim()
  const initials = deriveInitials(user)
  const cardRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    function handleOutsideTap(e: MouseEvent | TouchEvent) {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        textareaRef.current?.blur()
      }
    }
    document.addEventListener('mousedown', handleOutsideTap)
    document.addEventListener('touchstart', handleOutsideTap, { passive: true })
    return () => {
      document.removeEventListener('mousedown', handleOutsideTap)
      document.removeEventListener('touchstart', handleOutsideTap)
    }
  }, [])

  const toggleTheme = (slug: string) => {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    )
  }

  const trimmedTopic = topic.trim()
  const hasSignal = selected.length > 0 || trimmedTopic.length > 0

  // "Initiate reflection" — hand off to the matched-mind onboarding flow.
  // Writes the same sessionStorage contract the onboarding/themes screen uses,
  // then enters at the need step.
  function handleInitiate() {
    if (!hasSignal) return
    sessionStorage.setItem('onboarding_themes', JSON.stringify(selected))
    sessionStorage.setItem('onboarding_other_text', trimmedTopic)
    router.push('/app/onboarding/need')
  }

  // "Quick start" — preserves the prior card behavior: seed the bare topic and
  // open the persona picker directly. A trailing prompt tail was historically
  // mis-attributed to the user, so the topic is sent bare.
  function handleQuickStart() {
    onReflect(trimmedTopic || dailyQuestion)
  }

  return (
    <div ref={cardRef} className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] pt-[14px] pb-[16px]">
      {/* Today's topic (BUG-023). This replaces an eyebrow that read "What brings you
          here?" — word for word the page's own h1 (discuss/page.tsx:48), on the same
          screen. Nothing is lost by the swap and a duplication goes with it.

          The topic needs a surface of its own now that the placeholder is not it, and
          because Quick start below silently seeds this same string: without this block
          that button starts a reflection on a topic the reader has never seen. */}
      <div className="mb-[14px]">
        <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal">
          Today's topic
        </p>
        <p className="font-cormorant text-[19px] font-medium text-ink leading-snug mt-[4px]">
          {topicTitle}
        </p>
        {!!topicSubtitle && (
          <p className="font-lora text-[13px] text-charcoal leading-[1.6] mt-[4px]">
            {topicSubtitle}
          </p>
        )}
      </div>

      {/* Theme pills — same slugs + styling as onboarding/themes */}
      <div className="flex flex-wrap gap-2">
        {THEME_OPTIONS.map(({ slug, label }) => {
          const isSelected = selected.includes(slug)
          return (
            <button
              key={slug}
              type="button"
              onClick={() => toggleTheme(slug)}
              aria-pressed={isSelected}
              className={`px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] transition-colors ${
                isSelected
                  ? 'bg-bronze border-bronze-dark text-ink'
                  : 'bg-white border-bronze/60 text-charcoal shadow-card'
              }`}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Divider row */}
      <div className="flex items-center gap-[10px] mt-[14px] mb-[10px]">
        <span className="flex-1 h-px bg-edge" />
        <span className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
          or describe in your own words
        </span>
        <span className="flex-1 h-px bg-edge" />
      </div>

      <div className="flex items-start gap-[10px]">
        <div className="w-[64px] h-[64px] rounded-full flex-shrink-0 flex items-center justify-center bg-bronze mt-[2px]">
          <span className="font-cormorant text-[24px] font-medium text-vellum">
            {initials}
          </span>
        </div>
        <textarea
          ref={textareaRef}
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Start anywhere."
          className="flex-1 resize-none bg-transparent outline-none font-cormorant italic text-[16px] text-ink leading-snug placeholder:opacity-60 placeholder:not-italic placeholder:font-lora border border-bronze/40 rounded-[2px] focus:border-bronze focus:ring-1 focus:ring-bronze/20 pl-1 pr-3 py-2"
        />
      </div>
      <div className="mt-[12px] flex gap-[10px]">
        <button
          type="button"
          onClick={handleInitiate}
          disabled={!hasSignal}
          className="flex-1 h-[44px] bg-ink text-vellum rounded-[4px] font-cormorant text-[17px] font-medium disabled:bg-linen disabled:text-charcoal transition-colors"
        >
          Initiate reflection
        </button>
        <button
          type="button"
          onClick={handleQuickStart}
          className="flex-1 h-[44px] bg-transparent border border-ink text-ink rounded-[4px] font-cormorant text-[17px] font-medium"
        >
          Quick start
        </button>
      </div>
    </div>
  )
}
