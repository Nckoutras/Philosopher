'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { api, type Persona } from '@/lib/api'
import { useStore } from '@/lib/store'

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
        const rotation = all.filter((p) => p.portrait_url)
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
      {/* Top: full-bleed portrait area (~70% height) */}
      <section className="relative flex-1 min-h-[70vh] [min-height:70svh] overflow-hidden bg-linen">
        {mind && (
          <Image
            src={mind.portrait_url}
            alt={mind.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-top scale-[1.30] origin-top"
          />
        )}

        {/* Dark gradient overlay — top-anchored so hero text is always readable */}
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-black/65 via-black/35 to-transparent pointer-events-none"
        />

        {/* Hero text — V2: white serif + drop shadow */}
        <div className="absolute inset-x-0 top-0 z-10 px-4 pt-12 flex flex-col items-center text-center">
          <h1
            className="font-cormorant font-normal text-white text-[44px] leading-[1.05]"
            style={{ textShadow: '0 2px 8px rgba(0,0,0,0.6), 0 1px 3px rgba(0,0,0,0.8)' }}
          >
            Great Minds
          </h1>
          <p
            className="font-cormorant font-normal text-white/95 text-[19px] mt-2 leading-snug"
            style={{ textShadow: '0 1px 4px rgba(0,0,0,0.5)' }}
          >
            Reflect with the greatest thinkers
          </p>
        </div>
      </section>

      {/* Bottom: Vellum tray */}
      <section className="bg-vellum px-7 pt-4 pb-safe">
        <div className="w-full max-w-[380px] mx-auto">
          {loadError ? (
            <div className="text-center space-y-3">
              <p className="font-lora text-[13px] text-charcoal">
                Could not load today&apos;s mind.
              </p>
              <button
                type="button"
                onClick={() => { setLoadError(false); window.location.reload() }}
                className="font-lora text-[13px] text-sepia underline underline-offset-2"
              >
                Try again
              </button>
            </div>
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
          <div className="mt-5 space-y-2">
            <button
              type="button"
              onClick={() => router.push('/app/onboarding/themes')}
              className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
            >
              Begin
            </button>
            <button
              type="button"
              onClick={() => router.push('/app/explore')}
              className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium border-[0.5px] border-edge bg-white text-ink transition-colors"
            >
              Explore Minds
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}
