'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { benefitLine, isUpgradeSource, FALLBACK_LINE } from '@/lib/upgradeCopy'
import { DEFAULT_RETURN_TO, safeReturnTo } from '@/lib/safeReturnTo'
import { RETURN_TO_PARAM } from '@/lib/upgradeHref'

// THE WAY OUT (BUG-003). Twelve surfaces route here and none of them left the
// reader a door: this route sits OUTSIDE the (tabs) group, so there is no tab
// bar either, and browser Back is the only escape. That is fine in a browser
// tab and a trap in a PWA or a native wrapper, which is where a shared link
// lands. Moving the route inside (tabs) to inherit a tab bar was considered and
// rejected -- a paywall with a tab bar is still a paywall you cannot close, and
// it would put the wall inside the app shell it is supposed to sit above.
//
// WHERE IT GOES is a validated returnTo, not router.back(). back() needs a
// history entry and there is none on a cold open from a shared link, which is
// precisely the traffic this screen is about to get. safeReturnTo is Γ-2's
// existing validator, unchanged: /app/ prefixes only, protocol-relative
// payloads refused, and DEFAULT_RETURN_TO ('/app/today') for everything else.
function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      type="button"
      onClick={onClose}
      aria-label="Close"
      className="absolute right-[16px] w-[32px] h-[32px] flex items-center justify-center text-charcoal text-[20px] rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-bronze"
      style={{ top: 'max(0.75rem, env(safe-area-inset-top))' }}
    >
      ✕
    </button>
  )
}

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

  // WHERE CLOSE GOES. Validated every time it is read, never trusted from the
  // URL: safeReturnTo allow-lists /app/ paths and answers DEFAULT_RETURN_TO for
  // an absent, off-origin or malformed value, so a hand-edited
  // ?returnTo=//evil.com closes to Today rather than off-site.
  //
  // router.replace, not push: the paywall should not stay in history behind the
  // page the reader just returned to, or Back walks them straight back into it.
  const handleClose = useCallback(() => {
    router.replace(safeReturnTo(searchParams.get(RETURN_TO_PARAM)))
  }, [router, searchParams])

  // Escape dismisses, matching BottomSheet (components/ui/BottomSheet.tsx) so
  // the app has one keyboard contract for "get me out of this" rather than two.
  // A full page rather than a modal, so there is no focus trap to maintain and
  // nothing to restore focus to -- the tab order is the page's own.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') handleClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [handleClose])

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
    <main className="relative min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <CloseButton onClose={handleClose} />
      <div className="px-[24px] pt-[22px] pb-[16px] pr-[56px]">
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

// The Suspense fallback, and it CARRIES THE CLOSE CONTROL TOO.
//
// A wall with no exit on a slow first paint is the same bug as a wall with no
// exit — briefer, and worse on the connection least able to afford it. The
// fallback is what a reader on a slow phone actually looks at.
//
// IT READS window.location, NOT useSearchParams, and that is the whole reason
// this is a separate component rather than inline JSX. useSearchParams is the
// hook this boundary exists to suspend; calling it here would suspend the
// fallback itself. window.location.search is the same string, unsuspended, and
// it is read INSIDE the click handler — which only ever runs on the client, so
// there is no server/client divergence to hydrate around. The returnTo is
// therefore just as accurate here as in the resolved page.
function FallbackShell() {
  const router = useRouter()
  const handleClose = () => {
    const next =
      typeof window === 'undefined'
        ? null
        : new URLSearchParams(window.location.search).get(RETURN_TO_PARAM)
    router.replace(safeReturnTo(next))
  }
  return (
    <main className="relative min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <CloseButton onClose={handleClose} />
      <div className="px-[24px] pt-[22px] pb-[16px] pr-[56px]">
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
    <Suspense fallback={<FallbackShell />}>
      <UpgradeContent />
    </Suspense>
  )
}
