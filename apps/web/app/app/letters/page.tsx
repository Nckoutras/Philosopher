'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { WeeklyLetter } from '@/lib/api'
import AppHeader from '@/components/layout/AppHeader'
import SubPageNav from '@/components/layout/SubPageNav'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatWeekSpan(start: string, end: string): string {
  const s = new Date(start)
  const e = new Date(end)
  const sm = MONTHS[s.getUTCMonth()]
  const sd = s.getUTCDate()
  const em = MONTHS[e.getUTCMonth()]
  const ed = e.getUTCDate()
  const yr = e.getUTCFullYear()
  if (sm === em) return `${sm} ${sd}–${ed}, ${yr}`
  return `${sm} ${sd} – ${em} ${ed}, ${yr}`
}

export default function LettersPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'
  const [letters, setLetters] = useState<WeeklyLetter[] | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    if (!isPro) {
      router.replace('/app/upgrade')
      return
    }
    api.getWeeklyLetters()
      .then(setLetters)
      .catch(() => setLetters([]))
  }, [token, isPro, router])

  const visible = letters?.filter((l) => l.status !== 'suppressed') ?? []

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />

      <div className="px-[24px] pt-[22px] pb-[16px] flex items-center gap-[12px]">
        <SubPageNav fallbackHref="/app/rituals" />
        <div>
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
            Rituals
          </p>
          <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
            The Sunday Letter
          </h1>
        </div>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {letters === null ? (
          <>
            <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex flex-col gap-[8px]">
              <div className="h-[10px] w-[100px] bg-linen rounded animate-pulse" />
              <div className="h-[24px] w-[220px] bg-linen rounded animate-pulse" />
              <div className="h-[12px] w-[160px] bg-linen rounded animate-pulse" />
            </div>
            <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex flex-col gap-[8px]">
              <div className="h-[10px] w-[80px] bg-linen rounded animate-pulse" />
              <div className="h-[24px] w-[200px] bg-linen rounded animate-pulse" />
              <div className="h-[12px] w-[140px] bg-linen rounded animate-pulse" />
            </div>
          </>
        ) : visible.length === 0 ? (
          <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[24px] text-center">
            <p className="font-cormorant text-[19px] font-normal text-ink">
              Your first letter arrives Sunday.
            </p>
            <p className="font-lora text-[15px] text-charcoal mt-[6px] leading-[1.6]">
              After an active week, the mind you spent the most time with writes to you.
            </p>
          </div>
        ) : (
          visible.map((l) => {
            if (l.status === 'generated') {
              return (
                <button
                  key={l.id}
                  type="button"
                  onClick={() => router.push(`/app/letters/${l.id}`)}
                  className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px]"
                >
                  <div className="flex items-start justify-between gap-[8px]">
                    <div className="flex-1 min-w-0">
                      <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia">
                        {formatWeekSpan(l.period_start, l.period_end)}
                      </p>
                      <p className="font-cormorant text-[19px] font-medium text-ink leading-tight mt-[4px]">
                        {l.payload?.title ?? 'A letter for you'}
                      </p>
                      {l.voice_persona_name && (
                        <p className="font-lora text-[13px] text-charcoal mt-[4px]">
                          in the voice of {l.voice_persona_name}
                        </p>
                      )}
                    </div>
                    {l.read_at === null && (
                      <div className="w-[8px] h-[8px] rounded-full bg-bronze flex-shrink-0 mt-[6px]" />
                    )}
                  </div>
                </button>
              )
            }

            // status === 'empty'
            return (
              <div
                key={l.id}
                className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] opacity-60"
              >
                <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia">
                  {formatWeekSpan(l.period_start, l.period_end)}
                </p>
                <p className="font-cormorant text-[17px] text-charcoal mt-[4px]">
                  A quiet week — no letter this time.
                </p>
              </div>
            )
          })
        )}
      </div>
    </main>
  )
}
