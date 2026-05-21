'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { useStore } from '@/lib/store'

export default function RootPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    if (token) {
      router.replace('/app/today')
    } else {
      setAuthChecked(true)
    }
  }, [token, router])

  // W4: pure vellum background only during auth check — no spinner, no wordmark
  if (!authChecked) {
    return <div className="min-h-screen [min-height:100svh] bg-vellum" />
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum max-w-[380px] mx-auto overflow-hidden">
      {/* ── Cream zone ── */}
      <div className="bg-vellum px-[24px] pt-[44px] pb-[16px] flex flex-col items-center gap-[8px]">
        <h1 className="font-cormorant text-[38px] font-normal text-ink text-center leading-none">
          Great Minds
        </h1>
        <BronzeDivider width={100} />
        <p className="font-cormorant text-[22px] font-medium text-ink text-center leading-snug mt-[2px]">
          Reflect with the greatest thinkers
        </p>
        <p className="font-lora text-[14px] text-charcoal text-center">Speak your mind.</p>
        <p className="font-lora text-[14px] text-charcoal text-center">
          Think it through with timeless perspectives.
        </p>
      </div>

      {/* ── Hero image with cream fade at top edge ── */}
      <div className="relative flex-1 min-h-[300px]">
        <Image
          src="/personas/chesterfield-hero.jpg"
          alt=""
          fill
          priority
          className="object-cover object-top"
        />
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[80px] pointer-events-none z-10"
          style={{ background: 'linear-gradient(to bottom, #EFE3CC 0%, transparent 100%)' }}
        />
      </div>

      {/* ── Dark CTA zone ── */}
      <div className="bg-ink px-[24px] pt-[24px] pb-[32px] flex flex-col items-center gap-[10px]">
        <button
          type="button"
          onClick={() => router.push('/auth?mode=signup')}
          className="w-full py-[14px] rounded-[4px] border border-vellum/60 font-cormorant text-[17px] font-medium text-vellum"
        >
          Begin your reflection
        </button>
        <button
          type="button"
          onClick={() => router.push('/auth?mode=signin')}
          className="font-lora text-[14px] text-vellum/70 underline underline-offset-2 decoration-[0.5px]"
        >
          Sign in
        </button>
        <p className="font-lora text-[10px] tracking-[0.15em] uppercase text-sepia/60 text-center mt-[6px]">
          Premium reflective companion · 18+
        </p>
      </div>
    </main>
  )
}
