'use client'

import { Sparkle } from 'lucide-react'
import { formatItemDate } from '@/lib/formatItemDate'
import type { ReflectionFeedYvYSentence } from '@/lib/api'

interface Props { item: ReflectionFeedYvYSentence }

// A saved You-vs-You "sentence you owe yourself" line. Minimal by design — the
// eyebrow, the sentence, and the date. No Share (a YvY share card is a separate
// future item). Mirrors the CounterviewVerdictCard container vocabulary.
export default function YvYSentenceCard({ item }: Props) {
  return (
    <div className="w-full text-left bg-paper border border-bronze rounded-md shadow-card px-[18px] py-[16px]">
      <div className="flex items-center justify-between mb-[8px]">
        <span className="flex items-center gap-[6px]">
          <Sparkle size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold">A SENTENCE YOU OWE YOURSELF</p>
        </span>
        <span className="font-lora text-[10px] text-bronze-dark font-semibold flex-shrink-0 ml-[8px]">{formatItemDate(item.saved_at)}</span>
      </div>
      <p className="font-cormorant italic text-[19px] text-ink leading-snug">{item.sentence}</p>
    </div>
  )
}
