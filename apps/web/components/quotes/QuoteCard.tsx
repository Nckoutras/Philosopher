'use client'

import Image from 'next/image'
import type { Quote } from '@/lib/api'

// A single full-bleed card that fills the carousel viewport. Display-only —
// Discuss / The story arrive in PR-4.
export default function QuoteCard({
  quote,
  personaName,
  portraitUrl,
}: {
  quote: Quote
  personaName: string
  portraitUrl: string | null
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
        className="absolute inset-x-0 bottom-0 h-[55%] bg-gradient-to-t from-ink via-ink/70 to-transparent"
        aria-hidden="true"
      />

      {/* Text block, anchored bottom inside the scrim. Bottom padding clears the
          floating tab bar. */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-[10px] px-[24px] pt-[88px] pb-[40px]">
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
      </div>
    </article>
  )
}
