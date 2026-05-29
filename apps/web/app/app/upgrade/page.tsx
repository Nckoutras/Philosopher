'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

export default function UpgradePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [yearlyLoading, setYearlyLoading] = useState(false)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  async function handleSubscribe(interval: 'monthly' | 'yearly') {
    const setLoading = interval === 'yearly' ? setYearlyLoading : setMonthlyLoading
    setLoading(true)
    try {
      const { checkout_url } = await api.createCheckout('pro', interval)
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
          Unlimited minds. Persistent memory. Deeper reflection.
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
            €149 / year
          </p>
          <p className="font-lora text-[12px] text-charcoal mt-[2px]">
            €12.42 / month · save 17%
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
            €14.90 / month
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
