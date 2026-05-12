'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { api, type Persona } from '@/lib/api'
import { useStore } from '@/lib/store'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Slug → portrait file. Carl Jung intentionally excluded until portrait exists.
const PORTRAIT_PATHS: Record<string, string> = {
  socrates: '/personas/socrates.jpg',
  marcus_aurelius: '/personas/marcus_aurelius.jpg',
  simone_de_beauvoir: '/personas/simone_de_beauvoir.webp',
  epictetus: '/personas/epictetus.webp',
  sigmund_freud: '/personas/sigmund_freud.webp',
}

// Deterministic daily index — same for all users, rotates at UTC midnight.
function mindOfTheDayIndex(rotationSize: number): number {
  const dayMs = 86_400_000
  const dayNumber = Math.floor(Date.now() / dayMs)
  return dayNumber % rotationSize
}

export default function WelcomePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [mind, setMind] = useState<Persona | null>(null)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const all = await api.getPersonas()
        const rotation = all.filter((p) => p.slug in PORTRAIT_PATHS)
        if (rotation.length === 0) {
          if (!cancelled) setLoadError(true)
          return
        }
        const idx = mindOfTheDayIndex(rotation.length)
        if (!cancelled) setMind(rotation[idx])
      } catch {
        if (!cancelled) setLoadError(true)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Top: full-bleed portrait area (~65% height) */}
      <section className="relative flex-1 min-h-[60vh] [min-height:60svh] overflow-hidden bg-linen">
        {mind && (
          <Image
            src={PORTRAIT_PATHS[mind.slug]}
            alt={mind.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-[center_30%]"
          />
        )}

        {/* Subtle gradient from bottom to ensure tray readability if portrait bleeds */}
        <div
          aria-hidden="true"
          className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-vellum/80 to-transparent"
        />

        {/* Hero overlay text */}
        <div className="relative z-10 flex flex-col items-center justify-end h-full px-7 pb-10 text-center">
          <h1 className="font-cormorant text-[38px] font-light text-vellum leading-none drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]">
            Great Minds
          </h1>
          <p className="mt-3 font-cormorant text-[17px] font-normal text-vellum/95 leading-snug drop-shadow-[0_1px_2px_rgba(0,0,0,0.35)]">
            Reflect with the world's
            <br />
            greatest thinkers.
          </p>
          <div className="mt-4">
            <BronzeDivider width={90} />
          </div>
        </div>
      </section>

      {/* Bottom: Vellum tray */}
      <section className="bg-vellum px-7 pt-6 pb-10">
        <div className="w-full max-w-[380px] mx-auto">
          {loadError ? (
            <p className="font-lora text-[13px] text-charcoal text-center">
              Could not load today's mind. Refresh to try again.
            </p>
          ) : (
            <>
              <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia text-center">
                Mind of the day
              </p>
              <h2 className="mt-2 font-cormorant text-[24px] font-medium text-ink text-center leading-tight min-h-[32px]">
                {mind?.name ?? ' '}
              </h2>
              <p className="mt-1 font-lora text-[14px] text-charcoal text-center leading-snug min-h-[42px]">
                {mind?.tagline ?? ' '}
              </p>
            </>
          )}

          {/* CTAs */}
          <div className="mt-7 space-y-3">
            <button
              type="button"
              onClick={() => router.push('/app/onboarding/themes')}
              className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
            >
              Begin
            </button>
            <button
              type="button"
              onClick={() => router.push('/app/explore')}
              className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium border-[0.5px] border-edge bg-white text-ink transition-colors"
            >
              Explore Minds
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}
