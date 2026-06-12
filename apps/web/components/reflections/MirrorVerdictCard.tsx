'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
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
