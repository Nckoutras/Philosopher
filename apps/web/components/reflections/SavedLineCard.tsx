'use client'

import { useState } from 'react'
import Image from 'next/image'
import { formatDistanceToNow } from 'date-fns'
import type { SavedLineRead } from '@/lib/api'
import SharePreviewModal from '@/components/share/SharePreviewModal'

interface Props {
  item: SavedLineRead
  portraitUrl: string
  onClick: () => void
  onAskAnotherMind?: () => void
}

export default function SavedLineCard({ item, portraitUrl, onClick, onAskAnotherMind }: Props) {
  const [shareModalOpen, setShareModalOpen] = useState(false)

  return (
    <>
      {/* W2: outer div handles the Revisit tap (whole-card navigation).
          "Ask another mind" is an explicit inner button with stopPropagation. */}
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
        className="relative overflow-hidden w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px] cursor-pointer"
      >
        <Image src="/personas/wise-room-hero.webp" alt="" aria-hidden fill sizes="100vw"
          className="object-cover opacity-[0.12] pointer-events-none" />
        <div className="relative">
        <div className="flex items-center justify-between mb-[8px]">
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">
            FROM YOUR CONVERSATIONS
          </p>
          <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">
            {formatDistanceToNow(new Date(item.saved_at), { addSuffix: true })}
          </span>
        </div>
        <p className="font-cormorant text-[17px] font-normal italic text-ink leading-[1.45]">
          {item.message_content}
        </p>
        <div className="mt-[8px] flex items-center gap-[6px]">
          {portraitUrl ? (
            <img
              src={portraitUrl}
              alt={item.persona_display_name}
              width={31}
              height={31}
              className="object-cover rounded-[2px] flex-shrink-0"
            />
          ) : (
            <div className="w-[31px] h-[31px] bg-edge rounded-[2px] flex-shrink-0" aria-hidden="true" />
          )}
          <span className="font-lora text-[11px] text-sepia">
            {item.persona_display_name}
          </span>
        </div>

        {onAskAnotherMind && (
          <div className="mt-[10px] flex items-center gap-[8px] flex-wrap">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onClick()
              }}
              className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
            >
              Revisit
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onAskAnotherMind()
              }}
              className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
            >
              Ask another mind
            </button>
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
        )}
        </div>
      </div>

      {/* Sibling to role="button" — E2 accessibility: modal must not be a descendant
          of an interactive element */}
      <SharePreviewModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        savedLineId={item.id}
        personaName={item.persona_display_name}
        portraitUrl={portraitUrl || undefined}
        quote={item.message_content}
        conversationId={item.conversation_id}
      />
    </>
  )
}
