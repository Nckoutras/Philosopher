'use client'

import { useState } from 'react'
import Image from 'next/image'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedCouncil } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'

interface Props {
  item: ReflectionFeedCouncil
  portraitBySlug: Record<string, string>
}

// A saved Council verdict (the app-voice synthesis). Non-navigating in v1:
// there is no fetch-by-id for a single council session, so the card displays
// the synthesis and the four participating minds without a tap target. The
// Share action opens the same SharePreviewModal (kind='council') the Council
// ritual screen uses — co-located per-card, matching SavedLineCard.
export default function CouncilVerdictCard({ item, portraitBySlug }: Props) {
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const councilPortraits = item.persona_slugs
    .map((slug) => portraitBySlug[slug])
    .filter(Boolean)

  return (
    <>
      <div className="relative overflow-hidden w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
        <Image src="/personas/boardroom.webp" alt="" aria-hidden fill sizes="100vw"
          className="object-cover opacity-[0.10] pointer-events-none" />
        <div className="relative">
        {/* #4 round thumbnails, top-left */}
        <div className="flex items-center -space-x-[6px] mb-[10px]">
          {item.persona_slugs.map((slug) => {
            const portrait = portraitBySlug[slug]
            return portrait ? (
              <img key={slug} src={portrait} alt={slug} width={28} height={28}
                className="object-cover rounded-full border border-paper flex-shrink-0" />
            ) : (
              <div key={slug} className="w-[28px] h-[28px] bg-edge rounded-full border border-paper flex-shrink-0" aria-hidden="true" />
            )
          })}
        </div>
        <div className="flex items-center justify-between mb-[8px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">
            COUNCIL VERDICT
          </p>
          <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">
            {formatItemDate(item.saved_at)}
          </span>
        </div>
        <p className="font-cormorant text-[19px] font-normal italic text-ink leading-[1.45]">
          {item.synthesis}
        </p>
        <div className="mt-[10px] flex items-center gap-[8px] flex-wrap">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setShareModalOpen(true)
            }}
            className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
          >
            Share
          </button>
        </div>
        </div>
      </div>

      <SharePreviewModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        kind="council"
        councilSessionId={item.session_id}
        councilPortraits={councilPortraits}
        quote={item.synthesis}
      />
    </>
  )
}
