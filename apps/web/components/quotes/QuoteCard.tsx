'use client'

import Image from 'next/image'
import type { Quote } from '@/lib/api'

// A single tap-to-open card in the peek carousel. Read-only / presentational:
// graded portrait + scrim + quote + (real non-English) original + attribution.
// Discuss / The story now live in the detail sheet, opened via onOpen — not here.
export default function QuoteCard({
  quote,
  personaName,
  portraitUrl,
  onOpen,
}: {
  quote: Quote
  personaName: string
  portraitUrl: string | null
  onOpen: () => void
}) {
  // Only surface the original when it's a REAL non-English original — present AND
  // actually different from the English line. English-source quotes (text_original
  // null, or equal to text_en) render no original line at all — and since the line
  // is the only thing that would carry a separator, there is no stray dash either.
  const showOriginal = !!quote.text_original && quote.text_original !== quote.text_en

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Open “${quote.text_en}”`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className="relative h-full w-full cursor-pointer overflow-hidden rounded-[20px] bg-vellum shadow-card [touch-action:manipulation]"
    >
      {/* Full-bleed portrait. A uniform museum grade (restrained grayscale + warm
          sepia) makes all mismatched source photos read as one documentary family.
          Falls back to bg-vellum when portrait is null. */}
      {portraitUrl && (
        <Image
          src={portraitUrl}
          alt={personaName}
          fill
          sizes="80vw"
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

      {/* Text block, anchored bottom in the scrim. Read-only now (no action row), and
          lowered so the quote clears the face — pt/pb are starting values the founder
          fine-tunes on device. */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-[10px] px-[24px] pt-[56px] pb-[28px]">
        <p className="font-cormorant text-paper text-[27px] font-medium leading-[1.24] [text-wrap:balance] drop-shadow-[0_1px_10px_rgba(31,27,20,0.5)]">
          {quote.text_en}
        </p>

        {showOriginal && (
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
