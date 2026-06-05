'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Lock } from 'lucide-react'
import { api } from '@/lib/api'
import type { WeeklyLetter } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'

interface Props {
  isPro: boolean
}

export default function SundayLetterCard({ isPro }: Props) {
  const router = useRouter()
  const [unread, setUnread] = useState<WeeklyLetter | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  useEffect(() => {
    if (!isPro) return
    api.getWeeklyLetters()
      .then((letters) => {
        const found = letters.find((l) => l.status === 'generated' && l.read_at === null)
        setUnread(found ?? null)
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
        className={`relative w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[14px] flex items-center gap-[14px]${!isUnread ? ' opacity-60' : ''}`}
      >
        <div className="w-[56px] h-[56px] flex items-center justify-center text-ink flex-shrink-0">
          <Image src="/personas/sundayletter.png" alt="" width={56} height={56} className="w-full h-full object-cover rounded-[8px]" />
        </div>

        <div className={`flex-1 min-w-0${!isPro ? ' pr-[68px]' : ''}`}>
          <p className="font-cormorant text-[19px] font-medium text-ink">The Sunday Letter</p>
          <p className="font-lora text-[15px] text-charcoal mt-[2px]">
            {!isPro
              ? 'A letter from the mind you spent the week with.'
              : isUnread
              ? 'A new letter is waiting.'
              : 'Your letter arrives Sunday.'}
          </p>
        </div>

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
        <div className="px-6 py-6">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">Rituals</p>
          <h2 className="font-cormorant text-[22px] font-medium text-ink mt-[4px]">The Sunday Letter</h2>
          <p className="font-lora text-[15px] text-charcoal leading-[1.7] mt-[12px]">
            Each Sunday, the mind you spent the most time with that week writes to you — a letter, not a summary. The more you reflect this week, the more there is to write about. Your next letter arrives Sunday.
          </p>
          <button
            type="button"
            onClick={() => { setSheetOpen(false); router.push('/app/explore') }}
            className="mt-[20px] font-cormorant text-[15px] text-bronze"
          >
            Choose a mind →
          </button>
        </div>
      </BottomSheet>
    </>
  )
}
