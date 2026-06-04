'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import RitualScheduleSheet from '@/components/rituals/RitualScheduleSheet'

interface Props {
  isPro: boolean
  userEmail: string
}

export default function RitualsCard({ isPro, userEmail }: Props) {
  const router = useRouter()
  const [scheduleOpen, setScheduleOpen] = useState(false)

  function handleSendToFutureSelf() {
    if (!isPro) {
      router.push('/app/upgrade')
      return
    }
    setScheduleOpen(true)
  }

  return (
    <>
      <div className="bg-paper border border-[0.5px] border-edge rounded-md overflow-hidden">
        <div className="px-[16px] pt-[14px] pb-[2px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
            Rituals.
          </p>
        </div>

        {/* Message to future self */}
        <button
          type="button"
          onClick={handleSendToFutureSelf}
          className="w-full flex items-center justify-between px-[16px] py-[14px] border-t border-[0.5px] border-edge"
        >
          <span className="font-cormorant text-[17px] font-medium text-ink">
            Message to future self
          </span>
          <ChevronRight size={16} strokeWidth={1.5} className="text-sepia flex-shrink-0" />
        </button>


      </div>

      <RitualScheduleSheet
        open={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        userEmail={userEmail}
      />
    </>
  )
}
