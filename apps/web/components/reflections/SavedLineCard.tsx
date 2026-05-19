'use client'

import { formatDistanceToNow } from 'date-fns'
import type { SavedLineRead } from '@/lib/api'

interface Props {
  item: SavedLineRead
  portraitUrl: string
  onClick: () => void
}

export default function SavedLineCard({ item, portraitUrl, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[18px] py-[16px]"
    >
      <p className="font-cormorant text-[17px] font-normal italic text-ink leading-[1.45]">
        {item.message_content}
      </p>
      <div className="mt-[8px] flex items-center gap-[6px]">
        {portraitUrl ? (
          <img
            src={portraitUrl}
            alt={item.persona_display_name}
            width={28}
            height={28}
            className="object-cover rounded-[2px] flex-shrink-0"
          />
        ) : (
          <div className="w-[28px] h-[28px] bg-edge rounded-[2px] flex-shrink-0" aria-hidden="true" />
        )}
        <span className="font-lora text-[11px] text-sepia">
          {item.persona_display_name} · {formatDistanceToNow(new Date(item.saved_at), { addSuffix: true })}
        </span>
      </div>
    </button>
  )
}
