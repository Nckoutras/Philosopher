'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
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
    <main
      className="relative [min-height:100svh] bg-ink bg-cover bg-center flex flex-col"
      style={{ backgroundImage: "url('/personas/chesterfield-hero.jpg')" }}
    >
      {/* Subtle dark gradient at top for title legibility */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-ink/40 to-transparent pointer-events-none"
      />

      {/* Title block */}
      <div className="relative z-10 pt-[18vh] flex flex-col items-center px-6 text-center">
        <h1 className="font-cormorant text-[42px] sm:text-[52px] font-medium text-vellum tracking-tight">
          Great Minds
        </h1>
        <div className="my-[14px]">
          <BronzeDivider width={120} />
        </div>
        <p className="font-cormorant italic text-[18px] sm:text-[20px] text-vellum/85">
          Reflect with the greatest thinkers.
        </p>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Subtle dark gradient at bottom for CTA legibility */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 h-[30%] bg-gradient-to-t from-ink/50 to-transparent pointer-events-none"
      />

      {/* CTA block */}
      <div
        className="relative z-10 px-[24px] pb-[32px] flex flex-col items-center gap-[16px]"
        style={{ paddingBottom: 'max(32px, env(safe-area-inset-bottom))' }}
      >
        <button
          type="button"
          onClick={() => router.push('/auth?mode=signup')}
          className="w-full max-w-[420px] py-[16px] rounded-[4px] border border-vellum/70 font-cormorant text-[14px] uppercase tracking-[0.18em] text-vellum"
        >
          Begin your reflection
        </button>
        <button
          type="button"
          onClick={() => router.push('/auth?mode=signin')}
          className="font-lora text-[12px] uppercase tracking-[0.18em] text-vellum/80 underline underline-offset-4 decoration-[0.5px]"
        >
          Sign in
        </button>
      </div>
    </main>
  )
}
