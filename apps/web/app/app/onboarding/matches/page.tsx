'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api, type Match, type Persona } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

interface EnrichedMatch extends Match {
  name: string
  portraitPath: string
}

export default function MatchesPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [matches, setMatches] = useState<EnrichedMatch[] | null>(null)
  const [error, setError] = useState<string | null>(null)

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
            }
          })
          .filter((m): m is EnrichedMatch => m !== null)

        setMatches(enriched)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Could not load matches'
        // 404 from /matches means user hasn't completed prefs yet
        if (message.toLowerCase().includes('complete the questionnaire')) {
          router.replace('/app/onboarding/themes')
          return
        }
        setError(message)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [token, router])

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

  if (matches === null) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Reading the room…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 pt-8 pb-safe">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          <header className="space-y-3 text-center">
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Three minds for you
            </h1>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Based on what you shared, these can be a good fit.
            </p>
          </header>

          <div className="space-y-2">
            {matches.map((m) => (
              <button
                key={m.slug}
                type="button"
                onClick={() => router.push(`/app/persona/${m.slug}`)}
                className="w-full text-left p-4 rounded-md border-[0.5px] bg-linen border-edge transition-colors flex items-center gap-4"
              >
                <div className="w-14 h-14 rounded-full overflow-hidden bg-linen-deep flex-shrink-0">
                  {m.portraitPath && (
                    <Image
                      src={m.portraitPath}
                      alt={m.name}
                      width={56}
                      height={56}
                      className="w-full h-full object-cover object-top"
                    />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-cormorant text-[17px] font-medium text-ink leading-tight mb-1">
                    {m.name}
                  </div>
                  <div className="font-lora text-[12px] text-charcoal leading-[1.45]">
                    {m.reason}
                  </div>
                </div>
                <span className="font-cormorant text-[20px] text-sepia flex-shrink-0">›</span>
              </button>
            ))}
          </div>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => router.push('/app/explore')}
              className="font-lora text-[12px] text-sepia underline underline-offset-2"
            >
              See all minds
            </button>
          </div>

        </div>
      </div>
    </main>
  )
}
