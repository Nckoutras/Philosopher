'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import AppHeader from '@/components/layout/AppHeader'

export default function AccountPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)
  const storeSubscription = useStore((s) => s.subscription)
  const setSubscription = useStore((s) => s.setSubscription)

  const [portalLoading, setPortalLoading] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    if (!storeSubscription) {
      api.getSubscription().then(setSubscription).catch(() => {})
    }
    // Show success toast when returning from Stripe Checkout
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      if (params.get('checkout') === 'success') {
        toast.success('Welcome to Pro.')
        api.getSubscription().then(setSubscription).catch(() => {})
        // Remove the query param without a full reload
        window.history.replaceState({}, '', window.location.pathname)
      }
    }
  }, [token, router, storeSubscription, setSubscription])

  const displayName = user?.full_name ?? user?.email ?? ''
  const initial = displayName.charAt(0).toUpperCase()
  const plan = storeSubscription
    ? ['active', 'trialing'].includes(storeSubscription.status) && storeSubscription.plan !== 'free'
      ? storeSubscription.plan.charAt(0).toUpperCase() + storeSubscription.plan.slice(1)
      : 'Free'
    : 'Free'

  async function handleSubscriptionTap() {
    if (plan === 'Free') {
      router.push('/app/upgrade')
      return
    }
    setPortalLoading(true)
    try {
      const { portal_url } = await api.getPortalUrl()
      window.open(portal_url, '_blank', 'noopener,noreferrer')
    } catch {
      toast.error('Could not open subscription portal. Try again.')
    } finally {
      setPortalLoading(false)
    }
  }

  function handleSignOut() {
    useStore.getState().clearAuth()
    window.location.replace('/auth?mode=signin')
  }

  if (!user) {
    return <div className="min-h-screen [min-height:100svh] bg-vellum" />
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />
      {/* ── Header ── */}
      <div className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[4px]">
          Account
        </p>
        <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
          Your account.
        </h1>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {/* ── Profile card ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[20px] flex flex-col items-center gap-[6px]">
          <div className="w-[48px] h-[48px] rounded-full bg-linen flex items-center justify-center">
            <span className="font-cormorant text-[24px] font-medium text-charcoal leading-none">
              {initial}
            </span>
          </div>
          {user.full_name && (
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight mt-[4px]">
              {user.full_name}
            </p>
          )}
          <p className="font-lora text-[13px] text-charcoal">{user.email}</p>
        </div>

        {/* ── Subscription card ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md overflow-hidden">
          <div className="px-[16px] pt-[14px] pb-[2px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
              Subscription
            </p>
          </div>
          <button
            type="button"
            onClick={handleSubscriptionTap}
            disabled={portalLoading}
            className="w-full flex items-center justify-between px-[16px] py-[14px]"
          >
            <span className="font-cormorant text-[17px] font-medium text-ink">{plan}</span>
            <ChevronRight size={16} strokeWidth={1.5} className="text-sepia" />
          </button>
        </div>

        {/* ── Sign out card ── */}
        <button
          type="button"
          onClick={handleSignOut}
          className="w-full bg-paper border border-[0.5px] border-edge rounded-md py-[16px] text-center font-cormorant text-[17px] font-medium text-ink"
        >
          Sign out
        </button>
      </div>
    </main>
  )
}
