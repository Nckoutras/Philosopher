'use client'

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { useAuthGate } from '@/lib/useAuthGate'
import { track } from '@/lib/analytics'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { RITUALS, RITUAL_INFO } from '@/lib/rituals'
import { currentReturnTo, upgradeHref } from '@/lib/upgradeHref'

// The two labels, named rather than inlined so a wording change is one line.
//
// NEITHER IS NEW COPY. 'Begin' is the verb the welcome screen already uses for
// its primary action; 'Upgrade to Pro' is lifted verbatim from the persona
// detail page's gated CTA, which is the nearest existing instance of this exact
// button. Reused rather than invented, because a fourth spelling of "pay us" is
// a product decision and this is a dead-end fix.
const LABEL_ENTER = 'Begin'
const LABEL_GATED = 'Upgrade to Pro'

export default function RitualExplainerPage() {
  const router = useRouter()
  const params = useParams<{ slug: string }>()
  const token = useStore((s) => s.token)
  useAuthGate()
  // computePlan's output (lib/store.ts), which counts 'trialing' as entitled.
  // NOT the `subscription?.status === 'active' && plan !== 'free'` spelling the
  // rituals tab uses one door over: that one reads a trialing subscriber as
  // free and would offer them a paywall they have already passed. Two of the
  // three existing call sites handle trialing; the rituals tab is the outlier,
  // and is left alone here rather than fixed in a dead-end batch.
  const plan = useStore((s) => s.plan)
  const isPro = plan !== 'free'

  const meta = RITUALS.find((r) => r.slug === params.slug)
  const info = RITUAL_INFO[params.slug]

  // THE THIRD STATE THE BRIEF ASKS FOR CANNOT HAPPEN HERE, and saying so is
  // cheaper than a branch nobody can reach. /app/* is guarded twice before this
  // renders: middleware.ts redirects an unauthenticated request to
  // /auth?mode=signin&next=<this path>, and the token effect above replaces the
  // route client-side if the store says otherwise. A signed-out reader never
  // sees this page, so the CTA is two-state, not three -- and the destination
  // they came for is already preserved by the middleware's `next`.
  const gated = meta ? meta.pro && !isPro : false

  function handleCta() {
    if (!meta) return
    if (meta.pro && !isPro) {
      // A DELIBERATE CTA, so it fires. The registry's rule
      // (lib/analyticsEvents.ts) is that upgrade_clicked belongs to buttons
      // whose whole purpose is "upgrade", and NOT to the guard redirects that
      // push someone to /app/upgrade because they tried to do something else.
      // This button is the former: the reader read the page and pressed the one
      // action on it.
      track('upgrade_clicked', { surface: meta.source, reason: 'none' })
      router.push(upgradeHref({ source: meta.source, returnTo: currentReturnTo() }))
      return
    }
    router.push(meta.entry)
  }

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

          {/* THE ONE ACTION (BUG-018). This page explained a ritual and then
              left the reader on it -- intent created and wasted, on the six
              pages whose whole job is to create that intent.

              ONE button, never two. A second "or do this instead" is how a
              detail page becomes a menu, and the reader has already chosen
              which ritual they are reading about. Which button it is comes from
              lib/rituals.ts, so the six routes cannot drift apart. */}
          <button
            type="button"
            onClick={handleCta}
            className={`w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium transition-colors ${
              gated ? 'bg-bronze text-vellum' : 'bg-ink text-vellum'
            }`}
          >
            {gated ? LABEL_GATED : LABEL_ENTER}
          </button>
        </div>
      </section>
    </main>
  )
}
