'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

const TIER_LABELS: Record<Persona['tier'], string> = {
  free: 'FREE',
  pro: 'PRO',
  premium: 'PREMIUM',
}

export default function PersonaDetailPage() {
  const router = useRouter()
  const params = useParams<{ slug: string }>()
  const token = useStore((s) => s.token)

  const [persona, setPersona] = useState<Persona | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }

    let cancelled = false

    async function load() {
      try {
        const personas = await api.getPersonas()
        if (cancelled) return
        const found = personas.find((p) => p.slug === params.slug)
        if (!found) {
          setNotFound(true)
          return
        }
        setPersona(found)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [token, params.slug, router])

  if (notFound) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-cormorant text-[20px] text-ink mb-3">
          That mind is not here.
        </p>
        <button
          onClick={() => router.push('/app/onboarding/matches')}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back to your matches
        </button>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{error}</p>
        <button
          onClick={() => router.back()}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back
        </button>
      </main>
    )
  }

  if (!persona) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </main>
    )
  }

  const isLocked = !persona.is_accessible
  const portraitPath = persona.portrait_url
  const bio = persona.bio
  const tierLabel = TIER_LABELS[persona.tier]
  const tierColorClass = persona.tier === 'free' ? 'text-vellum' : 'text-bronze'

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Portrait section */}
      <section className="relative w-full h-[62vh] [height:62svh] overflow-hidden bg-linen flex-shrink-0">
        {portraitPath && (
          <Image
            src={portraitPath}
            alt={persona.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-top scale-[1.30] origin-top"
          />
        )}

        {/* Tier badge */}
        <div
          className={`absolute left-7 font-lora text-[12px] tracking-[0.22em] font-semibold ${tierColorClass}`}
          style={{ top: 'max(1.5rem, env(safe-area-inset-top))', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
        >
          {persona.tier !== 'free' && '🔒 '}{tierLabel}
        </div>

        {/* Close button */}
        <button
          onClick={() => router.back()}
          aria-label="Close"
          className="absolute right-6 w-8 h-8 flex items-center justify-center text-vellum text-[20px]"
          style={{ top: 'max(1.25rem, env(safe-area-inset-top))', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
        >
          ✕
        </button>
      </section>

      {/* Content section */}
      <section className="flex-1 px-7 py-4">
        <div className="w-full max-w-[380px] mx-auto space-y-5">

          {/* Name + tagline */}
          <header className="space-y-2 text-center">
            <h1 className="font-cormorant text-[28px] font-normal text-ink leading-tight">
              {persona.name}
            </h1>
            {persona.tagline && (
              <p className="font-lora text-[13px] text-charcoal italic">
                {persona.tagline}
              </p>
            )}
          </header>

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          {/* Bio — blurred if locked */}
          {bio && (
            <p
              className="font-lora text-[13px] text-charcoal leading-[1.7]"
            >
              {bio}
            </p>
          )}

          {/* CTA section */}
          <div className="pt-3 pb-safe space-y-3">
            {isLocked ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    // Stripe wiring not yet implemented — placeholder
                    alert('Stripe checkout coming soon.')
                  }}
                  className="w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-bronze text-vellum transition-colors"
                >
                  Upgrade to Pro
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/app/onboarding/matches')}
                  className="w-full font-lora text-[12px] text-sepia underline underline-offset-2 text-center"
                >
                  Or pick a free philosopher
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => router.push(`/app/chat/${persona.slug}`)}
                className="w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
              >
                Begin conversation
              </button>
            )}
          </div>

        </div>
      </section>
    </main>
  )
}
