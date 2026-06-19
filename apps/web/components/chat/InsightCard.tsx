'use client'

import { Bookmark } from 'lucide-react'

interface Props {
  content: string
  onReflect: () => void
  onDismiss: () => void
}

// App-voice insight card per DESIGN_SYSTEM_v4 §3.25 (+ Slice-1 brief copy).
// NOT a persona reply: no glow, no animation. Left-aligned to persona bubbles.
// bg-vellum (#EFE3CC) — deliberately darker than the bg-paper chat surface so
// the card reads as distinct; bronze border + eyebrow carry the app-voice identity.
export default function InsightCard({ content, onReflect, onDismiss }: Props) {
  return (
    <div className="ml-[32px] mt-[6px] bg-vellum border-[0.5px] border-bronze rounded-md pt-[18px] px-[18px] pb-[14px]">
      <p className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em]">
        The Wise Room · Insight
      </p>

      <div className="flex gap-[10px] items-start mt-[10px]">
        <span
          aria-hidden
          className="mt-[6px] shrink-0 w-[9px] h-[9px] bg-bronze rotate-45"
        />
        <p className="font-cormorant text-[17px] italic leading-[1.4] text-ink">
          {content}
        </p>
      </div>

      <div className="flex gap-[8px] pt-[12px] mt-[14px] border-t-[0.5px] border-edge">
        <button
          type="button"
          onClick={onReflect}
          className="flex-1 bg-ink text-paper font-lora text-[13px] py-[9px] rounded-sm inline-flex items-center justify-center gap-[6px]"
        >
          <Bookmark size={12} strokeWidth={1.5} />
          Reflect in the Mirror
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="flex-1 bg-transparent text-charcoal border-[0.5px] border-edge font-lora text-[13px] py-[9px] rounded-sm"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
