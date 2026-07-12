'use client'

import { useState } from 'react'
import Image from 'next/image'
import type { Quote } from '@/lib/api'

// A single tap-to-open card in the peek carousel. Read-only / presentational:
// graded portrait + scrim + quote + (real non-English) original + attribution.
// Discuss / The story now live in the detail sheet, opened via onOpen — not here.
// The attribution's source is shown SHORT; when truncated it's tappable and opens
// a small popover with the full citation (without opening the story).
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
  const showOriginal = !!quote.text_original && quote.text_original !== quote.text_en
  // Only tappable when the backend actually shortened it; otherwise the full
  // source already fits and is shown plain (no popover needed).
  const truncated = quote.source_short !== quote.source_locator
  const [showSource, setShowSource] = useState(false)

  // Opening the card (story) always dismisses the source popover first.
  const openCard = () => {
    setShowSource(false)
    onOpen()
  }

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Open “${quote.text_en}”`}
      onClick={openCard}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && showSource) {
          e.stopPropagation()
          setShowSource(false)
          return
        }
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          openCard()
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
          fine-tunes on device. (No z-index here: keeping it out of a stacking context
          lets the attribution's z-30 sit above the z-20 dismiss overlay below.) */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-[10px] px-[24px] pt-[56px] pb-[28px]">
        <p className="font-cormorant text-paper text-[27px] font-medium leading-[1.24] [text-wrap:balance] drop-shadow-[0_1px_10px_rgba(31,27,20,0.5)]">
          {quote.text_en}
        </p>

        {showOriginal && (
          <p className="font-lora italic text-paper/70 text-[14px] leading-snug">
            {quote.text_original}
          </p>
        )}

        {/* Attribution — persona · SHORT source. When truncated the source is a
            tappable button (dotted underline + ⓘ) that toggles the full-source
            popover; the popover sits above the line (z-30 > overlay z-20). */}
        <div className="relative z-30 pt-[2px]">
          <p className="font-lora text-bronze text-[11px] uppercase tracking-[0.16em]">
            {personaName} ·{' '}
            {truncated ? (
              <button
                type="button"
                aria-label={showSource ? 'Hide full source' : `Show full source: ${quote.source_locator}`}
                aria-expanded={showSource}
                onClick={(e) => {
                  e.stopPropagation()
                  setShowSource((v) => !v)
                }}
                onKeyDown={(e) => {
                  // Keep Enter/Space on the source from bubbling to the card (story).
                  if (e.key === 'Enter' || e.key === ' ') e.stopPropagation()
                }}
                className="underline decoration-dotted decoration-bronze/70 underline-offset-2 [touch-action:manipulation]"
              >
                {quote.source_short}
                <span aria-hidden="true"> ⓘ</span>
              </button>
            ) : (
              quote.source_locator
            )}
          </p>

          {showSource && (
            <div
              role="dialog"
              aria-label="Source"
              onClick={(e) => e.stopPropagation()}
              className="absolute bottom-full left-0 mb-[8px] max-w-[88%] rounded-[8px] border-[0.5px] border-bronze bg-paper px-[12px] py-[8px] shadow-card"
            >
              <p className="font-lora text-[9px] uppercase tracking-[0.18em] text-sepia mb-[3px]">
                Source
              </p>
              <p className="font-lora text-ink text-[12px] normal-case tracking-normal leading-snug">
                {quote.source_locator}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Dismiss overlay — only while the popover is open. Covers the card (except
          the source button + popover, which are z-30) so a tap "elsewhere" closes
          the popover WITHOUT opening the story. */}
      {showSource && (
        <div
          className="absolute inset-0 z-20"
          aria-hidden="true"
          onClick={(e) => {
            e.stopPropagation()
            setShowSource(false)
          }}
        />
      )}
    </article>
  )
}
