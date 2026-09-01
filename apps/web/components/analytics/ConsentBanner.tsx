'use client'

import { setConsent, initAnalytics, type ConsentValue } from '@/lib/analytics'

interface Props {
  onChoice: (value: ConsentValue) => void
}

/**
 * Opt-in analytics notice. Shown only when no choice is stored yet — the parent
 * owns that condition, so this component never decides its own visibility.
 *
 * Non-blocking by construction: no backdrop, no focus trap, no scroll lock. A
 * user who ignores it can use the whole product; nothing is captured until they
 * press Accept.
 */
export default function ConsentBanner({ onChoice }: Props) {
  async function choose(value: ConsentValue) {
    setConsent(value)
    // Accept starts the SDK in the same gesture, so the pageview the user is
    // currently on is the first thing recorded. Decline loads nothing.
    if (value === 'granted') await initAnalytics()
    onChoice(value)
  }

  return (
    <div
      role="region"
      aria-label="Analytics consent"
      // z-40 keeps it UNDER the tab bar (z-50), the paywall modal (z-50) and
      // BottomSheet (z-60) — a consent notice must never cover a paywall or a
      // safety surface. It clears the tab bar's footprint spatially instead,
      // using the same reservation (tabs)/layout.tsx makes for it.
      className="fixed inset-x-0 bottom-0 z-40 px-[16px] pointer-events-none"
      style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom) + 20px)' }}
    >
      <div className="pointer-events-auto mx-auto max-w-[520px] bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px]">
        <p className="font-cormorant text-[17px] font-medium text-ink leading-tight">
          We&rsquo;d like to measure what&rsquo;s working.
        </p>
        <p className="font-lora text-[12px] text-charcoal leading-snug mt-[4px]">
          Usage analytics, EU-hosted, never your conversations &mdash; off unless you say yes.
        </p>
        <div className="flex gap-[8px] mt-[12px]">
          <button
            type="button"
            onClick={() => void choose('granted')}
            className="flex-1 py-[10px] rounded-[4px] bg-ink text-vellum font-cormorant text-[16px] font-medium"
          >
            Accept
          </button>
          <button
            type="button"
            onClick={() => void choose('denied')}
            className="flex-1 py-[10px] rounded-[4px] border border-[0.5px] border-ink font-cormorant text-[16px] font-medium text-ink"
          >
            No thanks
          </button>
        </div>
      </div>
    </div>
  )
}
