'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Lock, MailOpen, MessagesSquare, BookMarked } from 'lucide-react'
import { MirrorIcon } from '@/components/icons/RitualIcons'
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

        {/* ── Letter to my Future Self — ACTIVE ── */}
        <button
          type="button"
          onClick={handleBeginLetter}
          className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-start gap-[14px]"
        >
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <MailOpen size={40} strokeWidth={1.2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              Letter to my Future Self
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
            <MirrorIcon size={40} strokeWidth={1.2} />
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
            <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
              <circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <path d="M20 1 A19 19 0 0 1 20 39 Z" fill="currentColor" />
            </svg>
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
            <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
              <circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="28" cy="12" r="5" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="12" cy="28" r="5" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="28" cy="28" r="5" fill="none" stroke="currentColor" strokeWidth="1.2" />
            </svg>
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
            <MessagesSquare size={40} strokeWidth={1.2} />
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

        {/* ── The Weekly Reading — LOCKED ── */}
        <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] opacity-50 flex items-start gap-[14px]">
          <div className="w-[56px] h-[56px] flex items-center justify-center flex-shrink-0 text-ink">
            <BookMarked size={40} strokeWidth={1.2} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
              The Weekly Reading
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.5] mt-[6px]">
              Your week, gathered into one reading — sent to you.
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

      </div>

      <RitualScheduleSheet
        open={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        userEmail={user?.email ?? ''}
      />
    </main>
  )
}
