'use client'

interface Props {
  content: string
  insightType: string | null
  // Distinct conversations a recurring theme was noticed across. The provenance
  // line renders only when this is present and >= 2 (older insights are null).
  sourceCount?: number | null
  onPrimary: () => void
  // 'Doubt this' navigates to Counterview (does NOT remove the insight).
  onDoubt: () => void
  // 'Discard this' removes the insight (the dismiss action).
  onDiscard: () => void
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
export default function InsightCard({ content, insightType, sourceCount, onPrimary, onDoubt, onDiscard, variant = 'chat' }: Props) {
  const showProvenance = sourceCount != null && sourceCount >= 2
  const primaryLabel = insightType === 'shift' ? 'See how this changed' : 'Reflect in the Mirror'
  const containerClass =
    variant === 'today'
      ? 'bg-paper border-[0.5px] border-bronze rounded-md pt-[18px] px-[18px] pb-[14px] shadow-card'
      : 'ml-[32px] mt-[6px] bg-vellum border-[0.5px] border-bronze rounded-md pt-[18px] px-[18px] pb-[14px]'
  return (
    <div className={containerClass}>
      <p className="font-lora text-[12px] font-medium text-charcoal uppercase tracking-[0.18em]">
        Insight
      </p>
      {showProvenance && (
        <p className="font-lora text-[10px] text-sepia mt-[3px]">
          Noticed across {sourceCount} of your conversations
        </p>
      )}

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
            className="shrink-0 w-[44px] h-[44px] rounded-md object-cover shadow-[0_0_18px_4px_rgba(184,153,104,0.45),0_0_0_1px_rgba(138,115,64,0.55)]"
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

      <div className="flex flex-col gap-[8px] pt-[12px] mt-[14px] border-t-[0.5px] border-edge">
        {/* Row 1: primary action, full width. */}
        <button
          type="button"
          onClick={onPrimary}
          className="w-full bg-ink text-paper font-lora text-[13px] py-[9px] rounded-sm inline-flex items-center justify-center text-center leading-tight"
        >
          {primaryLabel}
        </button>
        {/* Row 2: 'Doubt this' (bordered) sits above 'Discard this', which is the
            quietest action (light edge + sepia) so it doesn't invite removal. */}
        <div className="flex gap-[8px]">
          <button
            type="button"
            onClick={onDoubt}
            className="flex-1 bg-transparent text-ink border-[0.5px] border-ink font-lora text-[13px] py-[9px] rounded-sm"
          >
            Doubt this
          </button>
          <button
            type="button"
            onClick={onDiscard}
            className="flex-1 bg-transparent text-sepia border-[0.5px] border-edge font-lora text-[13px] py-[9px] rounded-sm"
          >
            Discard this
          </button>
        </div>
      </div>
    </div>
  )
}
