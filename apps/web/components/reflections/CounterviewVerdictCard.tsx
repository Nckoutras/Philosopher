'use client'

import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedCounterview } from '@/lib/api'

interface Props { item: ReflectionFeedCounterview; portraitBySlug: Record<string, string> }

export default function CounterviewVerdictCard({ item, portraitBySlug }: Props) {
  return (
    <div className="w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
      <div className="flex items-center -space-x-[6px] mb-[10px]">
        {item.verdicts.map((v) => {
          const p = portraitBySlug[v.persona_slug]
          return p
            ? <img key={v.persona_slug} src={p} alt={v.persona_name} width={28} height={28} className="object-cover rounded-full border border-paper flex-shrink-0" />
            : <div key={v.persona_slug} className="w-[28px] h-[28px] bg-edge rounded-full border border-paper flex-shrink-0" aria-hidden="true" />
        })}
      </div>
      <div className="flex items-center justify-between mb-[8px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">COUNTERVIEW</p>
        <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">{formatItemDate(item.saved_at)}</span>
      </div>
      {item.anchor_text && (
        <p className="font-cormorant text-[15px] italic text-sepia leading-snug mb-[12px]">“{item.anchor_text}”</p>
      )}
      <div className="space-y-[12px]">
        {item.verdicts.map((v) => (
          <div key={v.persona_slug}>
            <p className="font-cormorant text-[18px] text-ink leading-snug">{v.verdict}</p>
            <p className="font-lora text-[10px] uppercase tracking-[0.14em] text-bronze-dark mt-[3px]">{v.persona_name}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
