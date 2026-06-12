'use client'

import { formatDistanceToNow } from 'date-fns'
import type { ReflectionFeedCouncil } from '@/lib/api'

interface Props {
  item: ReflectionFeedCouncil
  portraitBySlug: Record<string, string>
}

// A saved Council verdict (the app-voice synthesis). Non-navigating in v1:
// there is no fetch-by-id for a single council session, so the card displays
// the synthesis and the four participating minds without a tap target.
export default function CouncilVerdictCard({ item, portraitBySlug }: Props) {
  return (
    <div className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[18px] py-[16px]">
      <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[8px]">
        The Council
      </p>
      <p className="font-cormorant text-[19px] font-normal italic text-ink leading-[1.45]">
        {item.synthesis}
      </p>
      <div className="mt-[10px] flex items-center gap-[6px]">
        <div className="flex items-center -space-x-[4px]">
          {item.persona_slugs.map((slug) => {
            const portrait = portraitBySlug[slug]
            return portrait ? (
              <img
                key={slug}
                src={portrait}
                alt={slug}
                width={22}
                height={22}
                className="object-cover rounded-[2px] border border-[0.5px] border-paper flex-shrink-0"
              />
            ) : (
              <div
                key={slug}
                className="w-[22px] h-[22px] bg-edge rounded-[2px] border border-[0.5px] border-paper flex-shrink-0"
                aria-hidden="true"
              />
            )
          })}
        </div>
        <span className="font-lora text-[11px] text-sepia ml-[2px]">
          {formatDistanceToNow(new Date(item.saved_at), { addSuffix: true })}
        </span>
      </div>
    </div>
  )
}
