'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { benefitLine, isUpgradeSource, FALLBACK_LINE } from '@/lib/upgradeCopy'

function UpgradeContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = useStore((s) => s.token)
  const [yearlyLoading, setYearlyLoading] = useState(false)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  const rawSource = searchParams.get('source')
  const reason = searchParams.get('reason')
  const personaSlug = searchParams.get('persona')
  // Only an allowlisted source is ever sent onward to checkout. An unknown one
  // still reaches PostHog through $pageview's $current_url, so nothing is lost
  // by refusing to forward it.
  const source = isUpgradeSource(rawSource) ? rawSource : null

  // The persona's DISPLAY NAME never comes from the URL — only a slug does, and
  // only as a lookup key. This resolves it against the API's own list, so a
  // hand-typed ?persona=Anything%20At%20All finds no match and the line falls
  // back to its no-name variant rather than rendering an attacker's string.
  //
  // There is no persona cache in this app (eight pages each call getPersonas
  // independently), so this page fetches its own. Deliberately not a cache
  // refactor: that is a larger change than this PR.
  const [personaName, setPersonaName] = useState<string | null>(null)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  useEffect(() => {
    if (!personaSlug) return
    let cancelled = false
    api
      .getPersonas()
      .then((personas) => {
        if (cancelled) return
        const match = personas.find((p) => p.slug === personaSlug)
        if (match) setPersonaName(match.name)
      })
      .catch(() => {
        // Silent by design: the no-name line reads correctly on its own, so a
        // failed lookup has nothing to report to the user.
      })
    return () => {
      cancelled = true
    }
  }, [personaSlug])

  // Renders the no-name variant on first paint and swaps to the named one when
  // the lookup resolves — no flash of wrong copy, no layout dependence on a
  // network call.
  const subtitle = benefitLine({ source: rawSource, reason, personaName })

  async function handleSubscribe(interval: 'monthly' | 'yearly') {
    const setLoading = interval === 'yearly' ? setYearlyLoading : setMonthlyLoading
    setLoading(true)
    try {
      // source rides into Stripe's session + subscription metadata, so
      // checkout_started and subscription_activated can both be split by the
      // paywall that produced them — which is the ratio this page exists for.
      const { checkout_url } = await api.createCheckout('pro', interval, source ?? undefined)
      window.location.href = checkout_url
    } catch {
      toast.error('Could not start checkout. Try again.')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <div className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[4px]">
          Upgrade
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          Choose your plan.
        </h1>
        <p className="font-lora text-[13px] text-charcoal mt-[6px] leading-snug">
          {subtitle}
        </p>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {/* ── Yearly card (preferred, shown first) ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[16px]">
          <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-[#B89968] mb-[8px]">
            Best value
          </p>
          <p className="font-cormorant text-[20px] font-medium text-ink leading-tight">
            Pro — Yearly
          </p>
          <p className="font-cormorant text-[17px] text-ink mt-[2px]">
            €99.99 / year
          </p>
          <p className="font-lora text-[12px] text-charcoal mt-[2px]">
            €8.33 / month · save 30%
          </p>
          <button
            type="button"
            onClick={() => handleSubscribe('yearly')}
            disabled={yearlyLoading || monthlyLoading}
            className="mt-[14px] w-full py-[12px] rounded-[4px] bg-ink text-vellum font-cormorant text-[17px] font-medium disabled:opacity-50"
          >
            {yearlyLoading ? 'Opening…' : 'Subscribe'}
          </button>
        </div>

        {/* ── Monthly card ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[16px]">
          <p className="font-cormorant text-[20px] font-medium text-ink leading-tight">
            Pro — Monthly
          </p>
          <p className="font-cormorant text-[17px] text-ink mt-[2px]">
            €11.99 / month
          </p>
          <button
            type="button"
            onClick={() => handleSubscribe('monthly')}
            disabled={yearlyLoading || monthlyLoading}
            className="mt-[14px] w-full py-[12px] rounded-[4px] border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink disabled:opacity-50"
          >
            {monthlyLoading ? 'Opening…' : 'Subscribe'}
          </button>
        </div>

        <p className="font-lora text-[11px] text-charcoal text-center leading-snug mt-[4px]">
          Cancel anytime via Account.{' '}
          <Link href="/legal/terms" className="underline underline-offset-2 decoration-[0.5px]">Terms</Link>
          {' · '}
          <Link href="/legal/privacy" className="underline underline-offset-2 decoration-[0.5px]">Privacy</Link>
        </p>
      </div>
    </main>
  )
}

export default function UpgradePage() {
  // useSearchParams without a Suspense boundary fails the production build —
  // the house pattern is split-component + Suspense (library/page.tsx,
  // auth/page.tsx, auth/verify, oauth/finish, PageviewTracker).
  //
  // The fallback renders the page's own shell with the generic line rather than
  // a blank screen: on a slow first paint the user sees the offer, not nothing.
  return (
    <Suspense
      fallback={
        <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
          <div className="px-[24px] pt-[22px] pb-[16px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[4px]">
              Upgrade
            </p>
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Choose your plan.
            </h1>
            <p className="font-lora text-[13px] text-charcoal mt-[6px] leading-snug">
              {FALLBACK_LINE}
            </p>
          </div>
        </main>
      }
    >
      <UpgradeContent />
    </Suspense>
  )
}
