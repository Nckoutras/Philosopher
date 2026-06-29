'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { useStore } from '@/lib/store'

// Real LQIP for the hero, minted from public/personas/wise-room-hero.webp (16px
// wide, WebP) — shown as a blurred placeholder so there's no empty-box pop-in
// before Netlify's optimized variant arrives. Regenerate if the source changes.
const HERO_BLUR =
  'data:image/webp;base64,UklGRpgAAABXRUJQVlA4IIwAAAAwBACdASoQABwAPu1mqk2ppaQiMAgBMB2JQBOnKAAXGYXawc+mxK9PphAA/e2Ev9nL13S7n8juRMbgQ4qnR3O+yHrPfenaOStOdvaWJSTSDzTml8u796Z8P8aKT3u0JBLaYH7iD5tWWAtiHzFKC11PJfn2D1z3N+b23D+EH7G5gSS+mHzZ4gLkClRAAA=='

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
    <main className="relative [min-height:100svh] bg-ink flex flex-col">
      <Image
        src="/personas/wise-room-hero.webp"
        alt=""
        fill
        priority
        sizes="100vw"
        placeholder="blur"
        blurDataURL={HERO_BLUR}
        className="absolute inset-0 object-cover object-center"
      />

      {/* Subtle dark gradient at top for title legibility */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-ink/40 to-transparent pointer-events-none"
      />

      {/* Title block */}
      <div className="relative z-10 pt-[18vh] flex flex-col items-center px-6 text-center">
        <h1 className="font-cormorant text-[42px] sm:text-[52px] font-medium text-vellum tracking-tight">
          The Wise Room
        </h1>
        <div className="my-[14px]">
          <BronzeDivider width={120} />
        </div>
        <p className="font-cormorant italic text-[18px] sm:text-[20px] text-vellum">
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
          className="w-full max-w-[420px] py-[16px] rounded-full bg-paper text-ink font-cormorant text-[18px] font-medium"
        >
          Begin your Reflection
        </button>
        <button
          type="button"
          onClick={() => router.push('/auth?mode=signin')}
          className="w-full max-w-[420px] py-[16px] rounded-full border border-bronze bg-transparent text-bronze font-cormorant text-[16px]"
        >
          Sign in
        </button>
      </div>
    </main>
  )
}
