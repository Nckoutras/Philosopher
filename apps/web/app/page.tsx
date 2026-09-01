'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { LandingSections } from '@/components/landing/LandingSections'
import { LANDING_COPY } from '@/lib/landing-copy'
import { useStore } from '@/lib/store'
import { track } from '@/lib/analytics'

// Real LQIP for the hero, minted from public/personas/wise-room-hero-v2.webp (16px
// wide, WebP) — shown as a blurred placeholder so there's no empty-box pop-in
// before Netlify's optimized variant arrives. Regenerate if the source changes.
const HERO_BLUR =
  'data:image/webp;base64,UklGRpgAAABXRUJQVlA4IIwAAAAQBACdASoQABwAPu1orU6ppiSiMAgBMB2JQBOnKAAXGYXayUVZjrLAwAD97YS/2cvXdLufyO5ExuBDiqdHc77Ies996do5K0529pYlJNIPNOaXvOOgund9sybKBXfnUcem5czv7/cd3MIW2gdoyvn0HwIme/7jlm4j8j7Lz0Kl2rvwnneBQXpLKu4AAA=='

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

  // The top of the funnel. Fired only for a signed-OUT visitor: a signed-in
  // user is redirected to /app/today above and never sees the landing page, so
  // counting them would inflate the denominator of every conversion below it.
  //
  // No utm_* or referrer props — posthog-js attaches both to every event on its
  // own (save_campaign_params / save_referrer, unaffected by autocapture:false).
  useEffect(() => {
    if (!authChecked) return
    track('landing_view')
  }, [authChecked])

  // W4: pure vellum background only during auth check — no spinner, no wordmark
  if (!authChecked) {
    return <div className="min-h-screen [min-height:100svh] bg-vellum" />
  }

  return (
    <>
    {/* Fold 1 keeps its own <main> and its exact 100svh height. The marketing
        sections are siblings, NOT children: the hero <Image fill> covers its
        nearest positioned ancestor, so nesting them here would stretch the
        photograph down the whole page. */}
    <main className="relative [min-height:100svh] bg-ink flex flex-col">
      <Image
        src="/personas/wise-room-hero-v2.webp"
        alt=""
        fill
        priority
        // Deliberately UNDER-declared on phones. The layout width is 100vw, but
        // this is a scrimmed background photograph behind text, not detail the
        // reader inspects — so 60vw makes a DPR-3 phone pick the w=750/828
        // variant (~80-92 KB) instead of w=1200 (~148 KB). Desktop keeps 100vw.
        // Bytes are a conversion cost at the top of the funnel; a background at
        // ~1.8x effective density is not a visible one.
        sizes="(max-width: 768px) 60vw, 100vw"
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

        {/* Scroll hint — the ONLY change to fold 1. Static by design: no bounce,
            no chevron animation (v5 §1.7). It sits inside the existing CTA block
            so the safe-area padding above still applies. */}
        <p className="font-lora text-[12px] tracking-[0.18em] uppercase text-vellum/80">
          {LANDING_COPY.scrollHint}
        </p>
      </div>
    </main>

    <LandingSections />
    </>
  )
}
