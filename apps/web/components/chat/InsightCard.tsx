'use client'

import { useState } from 'react'
import { Sparkle } from 'lucide-react'
import { api } from '@/lib/api'

// The verdict row, reusing the Mirror's shipped copy verbatim (mirror/page.tsx).
// One speech act, one wording, three surfaces — Mirror, You-vs-You and now the
// insight card. A fourth phrasing for the same question would make the three read
// as three different questions.
const RING_TRUE_OPTIONS = [
  { value: 'yes' as const, label: 'Rings true' },
  { value: 'partly' as const, label: 'Partly' },
  { value: 'no' as const, label: 'No' },
]

// Frozen app-voice observation line shown above the quoted user statement for the
// doorway insight types (Slice 2). Absent for pattern/shift, which render unchanged.
const OBSERVATION_LINES: Record<string, string> = {
  dilemma: 'This sounds like a decision with two sides.',
  belief: 'This sounds like a belief you lean on.',
}

interface Props {
  // Needed only for the verdict PATCH. The card owns that call itself so both
  // surfaces that render it get the row without either one wiring it up.
  insightId: string
  // The verdict already on the row, if the reader has answered before. Rendered
  // as the selected option so an answered card never asks again as if new.
  ringTrue?: 'yes' | 'partly' | 'no' | null
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
export default function InsightCard({ insightId, ringTrue = null, content, insightType, sourceCount, onPrimary, onDoubt, onDiscard, variant = 'chat' }: Props) {
  // TWO STATES, NOT ONE, and the split is the whole point (Γ-2b).
  //
  // `verdict` is optimistic — the button you pressed lights up immediately,
  // because a tap that does nothing for a round trip feels broken.
  // `confirmed` is NOT optimistic. "Noted." means the server stored it, so it
  // waits for the write to resolve. Founder ruling: "Noted." must mean stored.
  //
  // On failure both revert and the card asks again, rather than claiming an
  // answer that never landed — the row is the only memory of it, and every
  // surface that renders this card is stateless.
  const [verdict, setVerdict] = useState<'yes' | 'partly' | 'no' | null>(ringTrue)
  // Seeded true when the row arrived with a verdict: that one IS stored.
  const [confirmed, setConfirmed] = useState(ringTrue != null)
  const [submitting, setSubmitting] = useState(false)

  async function handleRingTrue(value: 'yes' | 'partly' | 'no') {
    if (submitting) return
    const previousVerdict = verdict
    const previousConfirmed = confirmed
    setVerdict(value)
    setConfirmed(false)
    setSubmitting(true)
    try {
      await api.setInsightRingTrue(insightId, value)
      setConfirmed(true)
    } catch {
      setVerdict(previousVerdict)
      setConfirmed(previousConfirmed)
    } finally {
      setSubmitting(false)
    }
  }

  const showProvenance = sourceCount != null && sourceCount >= 2
  // Doorway types (Slice 2): the user's own words get an app-voice observation line
  // above and are quoted below; the primary is a distinct door per type.
  // Aspiration content is first-person user voice (like dilemma/belief), so it's
  // quoted; it has no observation line (degrades gracefully, like shift/pattern).
  const isDoorway = insightType === 'dilemma' || insightType === 'belief' || insightType === 'aspiration'
  const observationLine = insightType ? OBSERVATION_LINES[insightType] : undefined
  const primaryLabel =
    insightType === 'dilemma'
      ? 'Take it to the Council'
      : insightType === 'belief'
        ? 'Put it under pressure'
        : insightType === 'aspiration'
          ? 'Write to your future self'
          : insightType === 'shift'
            ? 'See how this changed'
            : 'Reflect in the Mirror'
  // A belief's primary IS the counterview door, and doubting an aspiration →
  // Counterview is nonsensical, so 'Doubt this' is hidden for both. Other types
  // keep both secondaries.
  const showDoubt = insightType !== 'belief' && insightType !== 'aspiration'
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

      {observationLine && (
        <p className="font-lora text-[13px] text-charcoal mt-[8px] leading-[1.5]">
          {observationLine}
        </p>
      )}

      <div className="flex gap-[10px] items-start mt-[10px]">
        {/* Today carries the brand armchair-with-W mark (44px); the chat card keeps
            the compact bronze diamond so it stays light inside the thread. */}
        {variant === 'today' ? (
          <img
            src="/self-portrait/appbutton.webp"
            alt=""
            aria-hidden
            width={52}
            height={52}
            className="shrink-0 w-[52px] h-[52px] object-contain drop-shadow-[0_0_10px_rgba(184,153,104,0.35)]"
          />
        ) : (
          <Sparkle size={13} strokeWidth={1.5} className="mt-[5px] shrink-0 text-bronze fill-bronze drop-shadow-[0_0_5px_rgba(184,153,104,0.9)]" aria-hidden="true" />
        )}
        <p className="font-cormorant text-[19px] italic leading-[1.4] text-ink">
          {isDoorway ? `“${content}”` : content}
        </p>
      </div>

      {/* The verdict row (Γ-2). Above the doors, because it is a reply to the
          claim rather than another place to go. Rendered for EVERY insight type
          and every tier: correcting something the product asserted about you is
          not type-specific and is not a paid feature. */}
      <div className="flex flex-col items-center gap-[10px] pt-[12px] mt-[14px] border-t-[0.5px] border-edge">
        <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.18em] text-charcoal text-center">
          Does this ring true?
        </p>
        <div className="flex gap-[8px] flex-wrap justify-center">
          {RING_TRUE_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleRingTrue(value)}
              aria-pressed={verdict === value}
              className={[
                'font-lora text-[13px] px-[16px] py-[8px] rounded-full transition-colors',
                verdict === value
                  ? 'border-[1.5px] border-bronze bg-bronze/10 text-bronze'
                  : 'border-[1.5px] border-bronze text-charcoal',
                confirmed && verdict !== value ? 'opacity-40' : '',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>
        {confirmed && (
          <p className="font-lora text-[12px] text-sepia italic">Noted.</p>
        )}
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
          {showDoubt && (
            <button
              type="button"
              onClick={onDoubt}
              className="flex-1 bg-transparent text-ink border-[0.5px] border-ink font-lora text-[13px] py-[9px] rounded-sm"
            >
              Doubt this
            </button>
          )}
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
