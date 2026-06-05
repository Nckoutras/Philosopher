'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Lock } from 'lucide-react'
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
    if (token === null) router.replace('/auth?mode=signin')
  }, [token, router])

  function handleBeginLetter() {
    if (!isPro) {
      router.push('/app/upgrade')
      return
    }
    setScheduleOpen(true)
  }

  function handleOpenCouncil() {
    if (!isPro) { router.push('/app/upgrade'); return }
    router.push('/app/council')
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />

      <header className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Rituals
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          Your reflective practices.
        </h1>
      </header>

      <div className="px-[16px] pb-[8px]">
        <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
          Rituals are guided reflective practices that help you return to what your
          conversations surface — recurring questions, assumptions, tensions, and
          patterns. They are designed to deepen reflection over time, not provide
          quick answers.
        </p>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px] mt-[16px]">

        {/* ── Message to my Future Self — ACTIVE ── */}
        <button
          type="button"
          onClick={handleBeginLetter}
          className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-start gap-[14px]"
        >
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <Image src="/personas/messagetomyfutureself.png" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              Message to my Future Self
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              Seal a thought now. Let it find you changed.
            </p>
          </div>
        </button>

        {/* ── The Mirror — ACTIVE ── */}
        <button
          type="button"
          onClick={() => router.push('/app/mirror')}
          className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-start gap-[14px]"
        >
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <Image src="/personas/mirror.png" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              The Mirror
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              What keeps returning — not what you said, but what you meant.
            </p>
          </div>
        </button>

        {/* ── You vs. You — ACTIVE ── */}
        <button
          type="button"
          onClick={() => router.push('/app/you-vs-you')}
          className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-start gap-[14px]"
        >
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <Image src="/personas/youvsyou.webp" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              You vs. You
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              You, then. You, now. Watch them disagree.
            </p>
          </div>
        </button>

        {/* ── The Council — ACTIVE (PRO) ── */}
        <button
          type="button"
          onClick={handleOpenCouncil}
          className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-start gap-[14px]"
        >
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <Image src="/personas/boardroom.webp" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              The Council
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              Four minds. One matter. They will not agree.
            </p>
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mt-[10px]">
              Pro
            </p>
          </div>
        </button>

        {/* ── The Counterview — LOCKED ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] opacity-50 flex items-start gap-[14px]">
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <Image src="/personas/thecounterview.png" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              The Counterview
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              The strongest case against what you believe.
            </p>
            <p className="font-lora text-[12px] text-charcoal leading-[1.5] mt-[6px]">
              Available after 5 conversations or 30 messages with any philosopher.
            </p>
            <div className="flex items-center gap-[6px] mt-[12px]">
              <span className="font-lora text-[11px] text-charcoal">Coming soon</span>
              <Lock size={13} strokeWidth={1.5} className="text-sepia" />
            </div>
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
