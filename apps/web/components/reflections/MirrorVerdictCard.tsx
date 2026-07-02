'use client'

import { useState } from 'react'
import Image from 'next/image'
import { MirrorIcon } from '@/components/icons/RitualIcons'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedMirror } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'

interface Props {
  item: ReflectionFeedMirror
  portraitUrl: string
}

// A saved Mirror verdict. Non-navigating in v1: there is no fetch-by-id for a
// single mirror, so the card displays the closing line without a tap target.
// The Share action opens the same SharePreviewModal (kind='mirror') the Mirror
// ritual screen uses — co-located per-card, matching SavedLineCard.
export default function MirrorVerdictCard({ item, portraitUrl }: Props) {
  const [shareModalOpen, setShareModalOpen] = useState(false)

  return (
    <>
      <div className="relative overflow-hidden w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
        <Image src="/personas/mirror.webp" alt="" aria-hidden fill sizes="100vw"
          className="object-cover opacity-[0.10] pointer-events-none" />
        <div className="relative">
        <div className="flex items-center justify-between mb-[8px]">
          <span className="flex items-center gap-[6px]">
            <MirrorIcon size={13} strokeWidth={1.5} className="text-bronze-dark" />
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">
              FROM THE MIRROR
            </p>
          </span>
          <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">
            {formatItemDate(item.saved_at)}
          </span>
        </div>
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
            {item.host_persona_name ?? ''}
          </span>
        </div>

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
        kind="mirror"
        mirrorId={item.mirror_id}
        personaName={item.host_persona_name ?? undefined}
        portraitUrl={portraitUrl || undefined}
        quote={item.thread}
      />
    </>
  )
}
