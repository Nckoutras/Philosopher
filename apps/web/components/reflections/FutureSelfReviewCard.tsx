'use client'

import { Sparkle } from 'lucide-react'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedFutureSelfReview } from '@/lib/api'

interface Props { item: ReflectionFeedFutureSelfReview }

// A reviewed future-self letter: the prediction (context) + what actually
// happened. Display-only — editing lives on the arrived-letter screen. Mirrors
// the YvYSentenceCard container vocabulary; no Share, no delete.
export default function FutureSelfReviewCard({ item }: Props) {
  return (
    <div className="w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
      <div className="flex items-center justify-between mb-[8px]">
        <span className="flex items-center gap-[6px]">
          <Sparkle size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">A PREDICTION, REVISITED</p>
        </span>
        <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">{formatItemDate(item.saved_at)}</span>
      </div>
      {item.prediction && (
        <p className="font-lora text-[12px] text-charcoal leading-[1.55] mb-[8px]">
          You predicted: {item.prediction}
        </p>
      )}
      <p className="font-cormorant italic text-[19px] text-ink leading-snug whitespace-pre-wrap">{item.review_text}</p>
    </div>
  )
}
