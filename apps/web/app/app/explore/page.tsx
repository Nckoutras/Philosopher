'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'

const TIER_LABELS: Record<Persona['tier'], string> = {
  free: 'FREE',
  pro: 'PRO',
  premium: 'PREMIUM',
}

export default function ExplorePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [personas, setPersonas] = useState<Persona[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }
    let cancelled = false
    async function load() {
      try {
        const all = await api.getPersonas()
        if (!cancelled) setPersonas(all)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load')
      }
    }
    load()
    return () => { cancelled = true }
  }, [token, router])

  if (error) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{error}</p>
        <button onClick={() => router.back()} className="font-lora text-[13px] text-sepia underline">Back</button>
      </main>
    )
  }

  if (personas === null) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <header className="relative px-7 pt-6 pb-2">
        <button
          type="button"
          onClick={() => router.back()}
          aria-label="Back"
          className="absolute left-5 top-6 w-8 h-8 flex items-center justify-center text-ink text-[20px]"
        >
          ‹
        </button>
        <h1 className="font-cormorant text-[19px] font-medium text-ink text-center">
          Explore minds
        </h1>
        <p className="mt-3 font-lora text-[11px] uppercase tracking-[0.18em] text-sepia text-center">
          {personas.length} minds
        </p>
      </header>

      <div className="flex-1 px-7 pt-4 pb-safe">
        <div className="w-full max-w-[380px] mx-auto space-y-2">
          {personas.map((p) => (
            <button
              key={p.slug}
              type="button"
              onClick={() => router.push(`/app/persona/${p.slug}`)}
              className="w-full text-left p-4 rounded-md border-[0.5px] bg-linen border-edge transition-colors flex items-center gap-4"
            >
              <div className="w-14 h-14 rounded-full overflow-hidden bg-linen-deep flex-shrink-0">
                {p.portrait_url && (
                  <Image
                    src={p.portrait_url}
                    alt={p.name}
                    width={56}
                    height={56}
                    className="w-full h-full object-cover object-top"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-cormorant text-[17px] font-medium text-ink leading-tight mb-1">
                  {p.name}
                </div>
                {p.tagline && (
                  <div className="font-lora text-[12px] text-charcoal leading-[1.45]">
                    {p.tagline}
                  </div>
                )}
              </div>
              <span
                className={`font-lora text-[10px] uppercase tracking-[0.18em] flex-shrink-0 ${
                  p.tier === 'free' ? 'text-sepia' : 'text-bronze'
                }`}
              >
                {p.tier !== 'free' && '🔒 '}{TIER_LABELS[p.tier]}
              </span>
            </button>
          ))}
        </div>
      </div>
    </main>
  )
}
