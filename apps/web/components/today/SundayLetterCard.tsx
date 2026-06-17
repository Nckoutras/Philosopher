'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Lock } from 'lucide-react'
import { api } from '@/lib/api'
import type { WeeklyLetter } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'

function nextSundayLabel(): string {
  const M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const d = new Date()
  const add = d.getDay() === 0 ? 0 : 7 - d.getDay()
  const sun = new Date(d); sun.setDate(d.getDate() + add)
  return `${M[sun.getMonth()]} ${sun.getDate()}`
}

interface Props {
  isPro: boolean
}

export default function SundayLetterCard({ isPro }: Props) {
  const router = useRouter()
  const [unread, setUnread] = useState<WeeklyLetter | null>(null)
  const [hasReading, setHasReading] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)

  useEffect(() => {
    if (!isPro) return
    api.getWeeklyLetters()
      .then((letters) => {
        const found = letters.find((l) => l.status === 'generated' && l.read_at === null)
        setUnread(found ?? null)
        setHasReading(letters.some((l) => l.status === 'generated'))
      })
      .catch(() => {})
  }, [isPro])

  function handleClick() {
    if (!isPro) {
      router.push('/app/upgrade')
      return
    }
    if (unread) {
      router.push(`/app/letters/${unread.id}`)
    } else {
      setSheetOpen(true)
    }
  }

  const isUnread = isPro && unread !== null

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        className={`relative w-full text-center bg-paper border border-[0.5px] border-edge rounded-md shadow-card overflow-hidden min-h-[200px] px-[16px] pb-[18px] flex flex-col items-center justify-end${!isUnread ? ' opacity-60' : ''}`}
      >
        <svg aria-hidden="true" className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 100 100">
          <line x1="0" y1="0" x2="50" y2="44" stroke="#B89968" strokeWidth="1" strokeOpacity="0.4" vectorEffect="non-scaling-stroke" />
          <line x1="100" y1="0" x2="50" y2="44" stroke="#B89968" strokeWidth="1" strokeOpacity="0.4" vectorEffect="non-scaling-stroke" />
        </svg>

        <div className="absolute left-1/2 top-[44%] -translate-x-1/2 -translate-y-1/2 w-[56px] h-[56px]">
          <Image src="/personas/sundayletter.png" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
        </div>

        <p className="relative font-cormorant text-[19px] font-medium text-ink">The Sunday Letter</p>
        <p className="relative font-lora text-[15px] text-charcoal mt-[2px]">
          {!isPro
            ? 'A letter from the mind you spent the week with.'
            : isUnread
            ? 'A new letter is waiting.'
            : `Your letter arrives Sunday, ${nextSundayLabel()}.`}
        </p>

        {!isPro && (
          <div className="absolute top-[12px] right-[12px] flex items-center gap-[5px]">
            <Lock size={13} strokeWidth={1.5} className="text-sepia" />
            <span className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze">Pro</span>
          </div>
        )}

        {isUnread && (
          <div className="absolute top-[12px] right-[12px] w-[8px] h-[8px] rounded-full bg-bronze" />
        )}
      </button>

      <BottomSheet open={sheetOpen} onClose={() => setSheetOpen(false)} maxHeight="60svh">
        {/* The floating tab bar (BottomTabBar, backdrop-blur) paints over the sheet on
            iOS regardless of z-index, so clear its footprint here. Mirrors (tabs)/layout's
            scroll reservation MINUS the safe-area term — the BottomSheet panel already
            insets env(safe-area-inset-bottom) (single source of truth, d5b16ccb), so
            re-adding it would double-compensate. 4rem pill + 12px lift + 8px breathing. */}
        <div className="px-6 pt-6 pb-[calc(4rem+12px+8px)]">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">Rituals</p>
          <h2 className="font-cormorant text-[22px] font-medium text-ink mt-[4px]">The Sunday Letter</h2>
          {hasReading ? (
            <>
              <p className="font-lora text-[15px] text-charcoal leading-[1.7] mt-[12px]">
                Your next letter arrives this Sunday, {nextSundayLabel()}.
              </p>
              <button
                type="button"
                onClick={() => { setSheetOpen(false); router.push('/app/letters') }}
                className="mt-[20px] w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
              >
                View your readings
              </button>
            </>
          ) : (
            <>
              <p className="font-lora text-[15px] text-charcoal leading-[1.7] mt-[12px]">
                Each Sunday, the mind you spent the most time with that week writes to you — a letter, not a summary. The more you reflect this week, the more there is to write about. Your next letter arrives Sunday, {nextSundayLabel()}.
              </p>
              <button
                type="button"
                onClick={() => { setSheetOpen(false); router.push('/app/explore') }}
                className="mt-[20px] w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
              >
                Choose a mind
              </button>
            </>
          )}
        </div>
      </BottomSheet>
    </>
  )
}
