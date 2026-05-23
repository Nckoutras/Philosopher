'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Lock, ChevronRight } from 'lucide-react'
import { useStore } from '@/lib/store'
import AppHeader from '@/components/layout/AppHeader'
import RitualScheduleSheet from '@/components/rituals/RitualScheduleSheet'

export default function RitualsPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'
  const [scheduleOpen, setScheduleOpen] = useState(false)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  function handleBeginLetter() {
    if (!isPro) {
      router.push('/app/upgrade')
      return
    }
    setScheduleOpen(true)
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />

      <header className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Rituals
        </p>
        <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
          Your reflective practices.
        </h1>
      </header>

      <div className="px-[16px] pb-[8px]">
        <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
          Rituals are guided reflective practices that help you return to what your
          conversations surface — recurring questions, assumptions, tensions, and
          patterns. They are designed to deepen reflection over time, not provide
          quick answers.
        </p>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px] mt-[16px]">

        {/* ── Letter to my Future Self — ACTIVE ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px]">
          <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
            Letter to my Future Self
          </p>
          <p className="font-lora text-[13px] text-charcoal leading-[1.5] mt-[6px]">
            Seal a thought. Return to it later.
          </p>
          <button
            type="button"
            onClick={handleBeginLetter}
            className="mt-[14px] flex items-center gap-[4px] border border-[0.5px] border-ink rounded-sm px-[14px] min-h-[40px] font-cormorant text-[15px] font-medium text-ink"
          >
            Begin
            <ChevronRight size={14} strokeWidth={1.5} />
          </button>
        </div>

        {/* ── The Mirror — LOCKED ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] opacity-50">
          <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
            The Mirror
          </p>
          <p className="font-lora text-[13px] text-charcoal leading-[1.5] mt-[6px]">
            What keeps returning, reflected without judgment.
          </p>
          <p className="font-lora text-[12px] text-charcoal leading-[1.5] mt-[6px]">
            Available after 5 conversations or 30 messages with any philosopher.
          </p>
          <div className="flex items-center gap-[6px] mt-[12px]">
            <span className="font-lora text-[11px] text-charcoal">Coming soon</span>
            <Lock size={13} strokeWidth={1.5} className="text-sepia" />
          </div>
        </div>

        {/* ── The Counterview — LOCKED ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] opacity-50">
          <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
            The Counterview
          </p>
          <p className="font-lora text-[13px] text-charcoal leading-[1.5] mt-[6px]">
            Your assumptions, tested from another angle.
          </p>
          <p className="font-lora text-[12px] text-charcoal leading-[1.5] mt-[6px]">
            Available after 5 conversations or 30 messages with any philosopher.
          </p>
          <div className="flex items-center gap-[6px] mt-[12px]">
            <span className="font-lora text-[11px] text-charcoal">Coming soon</span>
            <Lock size={13} strokeWidth={1.5} className="text-sepia" />
          </div>
        </div>

        {/* ── The Weekly Reading — LOCKED ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] opacity-50">
          <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
            The Weekly Reading
          </p>
          <p className="font-lora text-[13px] text-charcoal leading-[1.5] mt-[6px]">
            What your week circled, narrated back.
          </p>
          <p className="font-lora text-[12px] text-charcoal leading-[1.5] mt-[6px]">
            A 3-paragraph weekly reading drawn from your conversations and ritual
            entries. Delivered via email and in-app, after your first active week.
          </p>
          <div className="flex items-center gap-[6px] mt-[12px]">
            <span className="font-lora text-[11px] text-charcoal">Coming soon</span>
            <Lock size={13} strokeWidth={1.5} className="text-sepia" />
          </div>
        </div>

      </div>

      <RitualScheduleSheet
        open={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        userEmail={user?.email ?? ''}
      />
    </main>
  )
}
