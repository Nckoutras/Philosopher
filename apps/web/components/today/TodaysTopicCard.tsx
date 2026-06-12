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
  const heavyPhrase = dailyQuestion.split(/\s+—\s+/)[0].trim()
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
      <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal mb-[10px]">
        What brings you here?
      </p>

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
          placeholder={heavyPhrase}
          className="flex-1 resize-none bg-transparent outline-none font-cormorant italic text-[16px] text-ink leading-snug placeholder:opacity-60 placeholder:italic placeholder:font-cormorant border border-bronze/40 rounded-[2px] focus:border-bronze focus:ring-1 focus:ring-bronze/20 pl-1 pr-3 py-2"
        />
      </div>
      {!topic && (
        <p className="font-lora text-[12px] italic text-charcoal/80 mt-[8px] pl-[74px]">
          (or tap in to write your own)
        </p>
      )}
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
