'use client'

import { useState } from 'react'
import { MessageCircle } from 'lucide-react'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedCounterview } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'

interface Props { item: ReflectionFeedCounterview; portraitBySlug: Record<string, string> }

export default function CounterviewVerdictCard({ item, portraitBySlug }: Props) {
  const [shareModalOpen, setShareModalOpen] = useState(false)

  return (
    <>
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
          <span className="flex items-center gap-[6px]">
            <MessageCircle size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">COUNTERVIEW</p>
          </span>
          <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">{formatItemDate(item.saved_at)}</span>
        </div>
        {item.anchor_text && (
          <p className="font-cormorant text-[15px] italic text-ink leading-snug mb-[12px]">“{item.anchor_text}”</p>
        )}
        <div className="space-y-[12px]">
          {item.verdicts.map((v) => (
            <div key={v.persona_slug}>
              <p className="font-cormorant text-[18px] text-ink leading-snug">{v.verdict}</p>
              <p className="font-lora text-[10px] uppercase tracking-[0.14em] text-bronze-dark mt-[3px]">{v.persona_name}</p>
            </div>
          ))}
        </div>
        <div className="mt-[10px] flex">
          <button
            onClick={(e) => { e.stopPropagation(); setShareModalOpen(true) }}
            className="px-[12px] min-h-[44px] flex items-center border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
          >
            Share
          </button>
        </div>
      </div>

      <SharePreviewModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        kind="counterview"
        counterviewId={item.counterview_id}
        counterviewPortraits={item.verdicts.map((v) => portraitBySlug[v.persona_slug]).filter(Boolean)}
        quote={item.anchor_text ?? 'the case against this'}
      />
    </>
  )
}
