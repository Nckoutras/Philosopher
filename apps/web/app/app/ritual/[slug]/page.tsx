'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { RITUALS, RITUAL_INFO } from '@/lib/rituals'

export default function RitualExplainerPage() {
  const router = useRouter()
  const params = useParams<{ slug: string }>()
  const token = useStore((s) => s.token)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  const meta = RITUALS.find((r) => r.slug === params.slug)
  const info = RITUAL_INFO[params.slug]

  if (!meta || !info) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-cormorant text-[20px] text-ink mb-3">That practice isn’t here.</p>
        <button onClick={() => router.back()} className="font-lora text-[13px] text-sepia underline">Back</button>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <section className="relative w-full h-[40vh] [height:40svh] overflow-hidden bg-linen flex-shrink-0">
        <Image src={meta.src} alt={meta.name} fill priority sizes="100vw" className={meta.slug === 'sunday-letter' ? 'object-contain' : 'object-cover'} />
        <button
          onClick={() => router.back()}
          aria-label="Close"
          className="absolute right-6 w-8 h-8 flex items-center justify-center text-vellum text-[20px]"
          style={{ top: 'max(1.25rem, env(safe-area-inset-top))', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
        >
          ✕
        </button>
      </section>

      <section className="flex-1 px-7 py-5">
        <div className="w-full max-w-[380px] mx-auto space-y-5">
          <header className="space-y-2 text-center">
            <p className="font-lora text-[11px] uppercase tracking-[0.22em] text-bronze-dark">The Wise Room · Ritual</p>
            <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">{meta.name}</h1>
            <p className="font-lora text-[13px] text-charcoal italic">{info.tagline}</p>
          </header>
          <div className="flex justify-center"><BronzeDivider width={80} /></div>
          <p className="font-lora text-[15px] text-charcoal leading-[1.7]">{info.body}</p>
          <div className="space-y-3 pt-1">
            <div>
              <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark mb-1">On its own</p>
              <p className="font-lora text-[14px] text-charcoal leading-[1.6]">{info.onItsOwn}</p>
            </div>
            <div>
              <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark mb-1">Over time</p>
              <p className="font-lora text-[14px] text-charcoal leading-[1.6]">{info.overTime}</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
