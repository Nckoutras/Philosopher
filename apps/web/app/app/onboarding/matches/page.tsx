'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api, type Match, type Persona } from '@/lib/api'

interface EnrichedMatch extends Match {
  name: string
  portraitPath: string
  is_accessible: boolean
  tagline: string | null
}

export default function MatchesPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [best, setBest] = useState<EnrichedMatch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [convLoading, setConvLoading] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }

    let cancelled = false

    async function load() {
      try {
        const [matchesRes, personasRes] = await Promise.all([
          api.getMatches(),
          api.getPersonas(),
        ])

        if (cancelled) return

        const personaBySlug = new Map<string, Persona>(
          personasRes.map((p) => [p.slug, p])
        )

        const enriched: EnrichedMatch[] = matchesRes
          .map((m) => {
            const persona = personaBySlug.get(m.slug)
            if (!persona) return null
            return {
              ...m,
              name: persona.name,
              portraitPath: persona.portrait_url ?? '',
              is_accessible: persona.is_accessible,
              tagline: persona.tagline,
            }
          })
          .filter((m): m is EnrichedMatch => m !== null)

        const accessible = enriched.filter((m) => m.is_accessible)
        const picked = accessible[0] ?? enriched[0] ?? null

        setBest(picked)
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Could not load matches'
        if (message.toLowerCase().includes('complete the questionnaire')) {
          router.replace('/app/onboarding/themes')
          return
        }
        setError(message)
        setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [token, router])

  async function handleBegin() {
    if (!best || convLoading) return
    setConvLoading(true)
    try {
      const draft = sessionStorage.getItem('onboarding_other_text')?.trim() || ''
      const hasTopic = draft.length > 0
      const conv = await api.createConversation(best.slug, undefined, hasTopic)
      if (hasTopic) localStorage.setItem(`today_topic_draft_${conv.id}`, draft)
      sessionStorage.removeItem('onboarding_other_text')
      router.push(`/app/chat/conv/${conv.id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not start conversation.')
      setConvLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Reading the room…</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
        <div className="flex-1 flex flex-col justify-center px-7 py-8 text-center">
          <p className="font-lora text-[13px] text-safety mb-4">{error}</p>
          <button
            onClick={() => router.replace('/app/onboarding/themes')}
            className="font-cormorant text-[15px] text-ink underline"
          >
            Start over
          </button>
        </div>
      </main>
    )
  }

  if (!best) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
        <div className="flex-1 flex flex-col justify-center px-7 py-8 text-center">
          <p className="font-lora text-[13px] text-charcoal mb-4">No matches found.</p>
          <button
            onClick={() => router.replace('/app/onboarding/themes')}
            className="font-cormorant text-[15px] text-ink underline"
          >
            Start over
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Full-bleed portrait area — no overlay branding text */}
      <section className="relative flex-1 min-h-[70vh] [min-height:70svh] overflow-hidden bg-linen">
        {best.portraitPath && (
          <Image
            src={best.portraitPath}
            alt={best.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-top scale-[1.30] origin-top"
          />
        )}
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-black/65 via-black/35 to-transparent pointer-events-none"
        />
      </section>

      {/* Bottom tray */}
      <section className="bg-vellum px-7 pt-4 pb-safe">
        <div className="w-full max-w-[380px] mx-auto">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia text-center">
            Mind of the day
          </p>
          <h2 className="mt-2 font-cormorant text-[24px] font-medium text-ink text-center leading-tight">
            {best.name}
          </h2>
          {best.tagline && (
            <p className="mt-1 font-lora text-[14px] text-charcoal text-center leading-snug">
              {best.tagline}
            </p>
          )}
          <p className="mt-2 font-lora text-[13px] text-sepia italic text-center leading-snug">
            {best.reason}
          </p>

          <div className="mt-5 space-y-2">
            <button
              type="button"
              onClick={handleBegin}
              disabled={convLoading}
              className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:opacity-50 transition-colors"
            >
              {convLoading ? 'Opening…' : 'Begin'}
            </button>
            <button
              type="button"
              onClick={() => router.push('/app/library?mode=browse')}
              className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium border-[0.5px] border-edge bg-white text-ink transition-colors"
            >
              See all minds
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}
