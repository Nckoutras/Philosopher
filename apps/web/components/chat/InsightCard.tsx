'use client'

interface Props {
  content: string
  insightType: string | null
  onPrimary: () => void
  onDismiss: () => void
  // 'chat' (default): left-indented vellum card inside the chat thread.
  // 'today': standing card on the (vellum) Today page — bg-paper for contrast,
  // no chat indent. App-voice identity (bronze border + eyebrow) is shared.
  variant?: 'chat' | 'today'
}

// App-voice insight card per DESIGN_SYSTEM_v4 §3.25 (+ Slice-1 brief copy).
// NOT a persona reply: no glow, no animation. Left-aligned to persona bubbles.
// bg-vellum (#EFE3CC) — deliberately darker than the bg-paper chat surface so
// the card reads as distinct; bronze border + eyebrow carry the app-voice identity.
// The primary action branches on insight type (Slice 2): a 'shift' sends the user
// to You-vs-You; everything else reflects in the Mirror.
export default function InsightCard({ content, insightType, onPrimary, onDismiss, variant = 'chat' }: Props) {
  const primaryLabel = insightType === 'shift' ? 'See how this changed' : 'Reflect in the Mirror'
  const containerClass =
    variant === 'today'
      ? 'bg-paper border-[0.5px] border-bronze rounded-md pt-[18px] px-[18px] pb-[14px] shadow-card'
      : 'ml-[32px] mt-[6px] bg-vellum border-[0.5px] border-bronze rounded-md pt-[18px] px-[18px] pb-[14px]'
  return (
    <div className={containerClass}>
      <p className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em]">
        The Wise Room · Insight
      </p>

      <div className="flex gap-[10px] items-start mt-[10px]">
        {/* Today carries the brand seal (44px medallion); the chat card keeps
            the compact bronze diamond so it stays light inside the thread. */}
        {variant === 'today' ? (
          <img
            src="/insight_seal.png"
            alt=""
            aria-hidden
            width={44}
            height={44}
            className="shrink-0 w-[44px] h-[44px] rounded-md object-cover"
          />
        ) : (
          <span
            aria-hidden
            className="mt-[6px] shrink-0 w-[9px] h-[9px] bg-bronze rotate-45"
          />
        )}
        <p className="font-cormorant text-[17px] italic leading-[1.4] text-ink">
          {content}
        </p>
      </div>

      <div className="flex gap-[8px] pt-[12px] mt-[14px] border-t-[0.5px] border-edge">
        <button
          type="button"
          onClick={onPrimary}
          className="flex-1 bg-ink text-paper font-lora text-[13px] py-[9px] rounded-sm inline-flex items-center justify-center text-center leading-tight"
        >
          {primaryLabel}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="flex-1 bg-transparent text-charcoal border-[0.5px] border-edge font-lora text-[13px] py-[9px] rounded-sm"
        >
          {"Doesn't ring true"}
        </button>
      </div>
    </div>
  )
}
