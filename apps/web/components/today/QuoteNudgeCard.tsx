'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { api, type SuggestedQuote } from '@/lib/api'
import { markSeen, pruneSeen } from '@/lib/quoteNudgeSeen'
import { shownToday, markShownToday } from '@/lib/quoteNudgeFrequency'
import { openingFor } from '@/lib/quotePrefill'
import { THEME_OPTIONS } from '@/lib/themes'

function themeLabel(slug: string): string | null {
  return THEME_OPTIONS.find((o) => o.slug === slug)?.label ?? null
}

// Home nudge: one themed, persona-ranked quote for the current Pro user. Self-
// gating — Pro-only (free users get an empty endpoint), daily-capped, and it never
// re-surfaces a suggestion this device has acted on or dismissed. Renders nothing
// when any gate fails. Mirrors RoomNoticedCard (self-fetch + seen-set).
export default function QuoteNudgeCard({ isPro }: { isPro: boolean }) {
  const router = useRouter()
  const [quote, setQuote] = useState<SuggestedQuote | null>(null)
  const [personaName, setPersonaName] = useState<string>('')
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    // Self-gate: Pro-only, at most one nudge per local day — skip the fetch entirely.
    if (!isPro || shownToday()) return
    let cancelled = false
    Promise.all([api.getSuggestedQuotes(), api.getPersonas()])
      .then(([suggested, personas]) => {
        if (cancelled) return
        // Prune the seen set against the live suggestions, then take the first
        // this device hasn't already acted on / dismissed.
        const seen = new Set(pruneSeen(suggested.map((q) => q.id)))
        const pick = suggested.find((q) => !seen.has(q.id)) ?? null
        if (!pick) return
        const nameMap = new Map(personas.map((p) => [p.slug, p.name]))
        setPersonaName(nameMap.get(pick.persona_slug) ?? pick.persona_slug)
        setQuote(pick)
        markShownToday() // counts against the daily cap only when one is actually shown
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [isPro])

  if (!quote) return null

  const current = quote
  const label = current.matched_themes.length ? themeLabel(current.matched_themes[0]) : null

  async function handleDiscuss() {
    void api.incrementDiscuss(current.id).catch(() => {}) // fire-and-forget demand signal
    if (starting) return
    setStarting(true)
    try {
      const conv = await api.createConversation(current.persona_slug)
      // Seed the composer only (read-and-cleared on chat mount) — never auto-sent.
      sessionStorage.setItem(`chat_prefill_${conv.id}`, openingFor(current).slice(0, 600))
      markSeen(current.id) // acted on — don't re-nudge this suggestion
      router.push(`/app/chat/conv/${conv.id}`)
    } catch {
      // Pro-only card ⇒ persona-lock 403 not expected; any error fails calm.
      markSeen(current.id)
      setQuote(null)
      setStarting(false)
      toast('Could not open the conversation. Try again in a moment.')
    }
  }

  function handleDismiss() {
    markSeen(current.id)
    setQuote(null)
  }

  return (
    <section>
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[8px]">
        A LINE FOR YOU
      </p>
      <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[20px] py-[18px] shadow-card flex flex-col gap-[12px]">
        <p className="font-cormorant text-ink text-[22px] font-medium leading-[1.28]">
          {current.text_en}
        </p>

        <p className="font-lora text-bronze text-[11px] uppercase tracking-[0.16em]">
          {personaName} · {current.source_locator}
        </p>

        {label && (
          <p className="font-lora text-sepia text-[12px] leading-relaxed">
            Resonates with your {label}.
          </p>
        )}

        <div className="flex items-center gap-[16px] pt-[2px]">
          <button
            type="button"
            onClick={handleDiscuss}
            className="rounded-full bg-ink text-paper font-lora text-[13px] px-[18px] py-[9px] transition active:opacity-80 [touch-action:manipulation]"
          >
            Discuss this
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            className="font-lora text-sepia text-[13px] underline underline-offset-2 active:opacity-60 [touch-action:manipulation]"
          >
            Not now
          </button>
        </div>
      </div>
    </section>
  )
}
