'use client'

import Image from 'next/image'
import type { Quote } from '@/lib/api'

// A single full-bleed card that fills the carousel viewport. Display-only —
// Discuss / The story arrive in PR-4.
export default function QuoteCard({
  quote,
  personaName,
  portraitUrl,
  onDiscuss,
  onStory,
}: {
  quote: Quote
  personaName: string
  portraitUrl: string | null
  onDiscuss: () => void
  onStory: () => void
}) {
  return (
    <article className="relative h-full w-full overflow-hidden bg-vellum">
      {/* Full-bleed portrait. A uniform museum grade (restrained grayscale + warm
          sepia) makes all 11 mismatched source photos read as one documentary
          family — NOT era styling. Falls back to bg-vellum when portrait is null. */}
      {portraitUrl && (
        <Image
          src={portraitUrl}
          alt={personaName}
          fill
          sizes="100vw"
          className="object-cover [filter:grayscale(0.35)_sepia(0.16)_contrast(1.02)_brightness(0.97)]"
        />
      )}

      {/* Low-opacity bronze veil — final unifier over the graded photo. */}
      <div className="absolute inset-0 bg-bronze/10" aria-hidden="true" />

      {/* Bottom scrim: ink → transparent over the lower ~half, so text stays legible
          over any portrait, light or dark. */}
      <div
        className="absolute inset-x-0 bottom-0 h-[62%] bg-gradient-to-t from-ink via-ink/70 to-transparent"
        aria-hidden="true"
      />

      {/* Text block, anchored bottom inside the scrim. Bottom padding clears the
          floating tab bar and gives the action row room. */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-[10px] px-[24px] pt-[88px] pb-[44px]">
        <p className="font-cormorant text-paper text-[27px] font-medium leading-[1.24] [text-wrap:balance] drop-shadow-[0_1px_10px_rgba(31,27,20,0.5)]">
          {quote.text_en}
        </p>

        {quote.text_original && (
          <p className="font-lora italic text-paper/70 text-[14px] leading-snug">
            {quote.text_original}
          </p>
        )}

        <p className="font-lora text-bronze text-[11px] uppercase tracking-[0.16em] pt-[2px]">
          {personaName} · {quote.source_locator}
        </p>

        {/* Actions — presentational only; orchestration lives in the page. */}
        <div className="flex gap-[10px] pt-[8px]">
          <button
            type="button"
            onClick={onDiscuss}
            className="flex-1 rounded-full border border-bronze/60 bg-ink/25 py-[9px] font-lora text-[13px] text-paper backdrop-blur-sm transition active:scale-95 [touch-action:manipulation]"
          >
            Discuss
          </button>
          <button
            type="button"
            onClick={onStory}
            className="flex-1 rounded-full border border-bronze/60 bg-ink/25 py-[9px] font-lora text-[13px] text-paper backdrop-blur-sm transition active:scale-95 [touch-action:manipulation]"
          >
            The story
          </button>
        </div>
      </div>
    </article>
  )
}
