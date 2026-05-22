'use client'

import { format } from 'date-fns'

export default function AppHeader() {
  const dateLabel = format(new Date(), 'EEE, MMM d')

  return (
    <div className="px-[24px] pt-[18px] pb-[10px] flex items-center justify-center gap-[8px]">
      <span className="font-cormorant text-[18px] font-medium text-ink italic">
        Great Minds
      </span>
      <span className="font-lora text-[12px] text-sepia">·</span>
      <span className="font-lora text-[12px] text-charcoal">
        {dateLabel}
      </span>
    </div>
  )
}
