'use client'

import Image from 'next/image'
import { Bookmark } from 'lucide-react'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedQuote } from '@/lib/api'

interface Props {
  item: ReflectionFeedQuote
}

// A saved corpus quote in the Reflections feed. Display-only — swipe-to-delete is
// handled by the enclosing SwipeableRow. Mirrors SavedLineCard's density; the full
// source_locator only appears when the short form was actually truncated.
export default function SavedQuoteCard({ item }: Props) {
  const truncated = item.source_short !== item.source_locator

  return (
    <div className="relative overflow-hidden w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
      <Image src="/personas/wise-room-hero.webp" alt="" aria-hidden fill sizes="100vw"
        className="object-cover opacity-[0.06] pointer-events-none" />
      <div className="relative">
        <div className="flex items-center justify-between mb-[8px]">
          <span className="flex items-center gap-[6px]">
            <Bookmark size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">
              SAVED QUOTE
            </p>
          </span>
          <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">
            {formatItemDate(item.saved_at)}
          </span>
        </div>

        <p className="font-cormorant text-[17px] font-normal italic text-ink leading-[1.45]">
          {item.text_en}
        </p>

        <div className="mt-[8px] flex items-center gap-[6px]">
          {item.persona_portrait_url ? (
            <img
              src={item.persona_portrait_url}
              alt={item.persona_name}
              width={31}
              height={31}
              className="object-cover rounded-[2px] flex-shrink-0"
            />
          ) : (
            <div className="w-[31px] h-[31px] bg-edge rounded-[2px] flex-shrink-0" aria-hidden="true" />
          )}
          <span className="font-lora text-[11px] text-sepia">
            {item.persona_name} · {item.source_short}
          </span>
        </div>

        {truncated && (
          <p className="mt-[6px] font-lora text-[10px] text-sepia/80 leading-snug">
            {item.source_locator}
          </p>
        )}
      </div>
    </div>
  )
}
