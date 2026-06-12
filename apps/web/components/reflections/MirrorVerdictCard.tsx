'use client'

import { formatDistanceToNow } from 'date-fns'
import type { ReflectionFeedMirror } from '@/lib/api'

interface Props {
  item: ReflectionFeedMirror
  portraitUrl: string
}

// A saved Mirror verdict. Non-navigating in v1: there is no fetch-by-id for a
// single mirror, so the card displays the closing line without a tap target.
export default function MirrorVerdictCard({ item, portraitUrl }: Props) {
  return (
    <div className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[18px] py-[16px]">
      <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[8px]">
        The Mirror
      </p>
      <p className="font-cormorant text-[19px] font-normal italic text-ink leading-[1.45]">
        {item.thread}
      </p>
      <div className="mt-[8px] flex items-center gap-[6px]">
        {item.host_persona_name && portraitUrl ? (
          <img
            src={portraitUrl}
            alt={item.host_persona_name}
            width={28}
            height={28}
            className="object-cover rounded-[2px] flex-shrink-0"
          />
        ) : (
          <div className="w-[28px] h-[28px] bg-edge rounded-[2px] flex-shrink-0" aria-hidden="true" />
        )}
        <span className="font-lora text-[11px] text-sepia">
          {item.host_persona_name ? `${item.host_persona_name} · ` : ''}
          {formatDistanceToNow(new Date(item.saved_at), { addSuffix: true })}
        </span>
      </div>
    </div>
  )
}
