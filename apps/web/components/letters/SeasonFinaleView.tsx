'use client'

import type { ReactNode } from 'react'
import Image from 'next/image'
import type { Persona, WeeklyLetterPayload } from '@/lib/api'

interface Props {
  payload: WeeklyLetterPayload
  voicePersona: Persona | null
  // Always-present sign-off name (the persona lookup behind voicePersona can be
  // null; this string field on the letter never is).
  voicePersonaName: string | null
  suggestedPersona: Persona | null
  periodStart: string
  startingConv: boolean
  onStartConversation: (slug: string) => void
  onRevisit: () => void
  onShare: () => void
  // End-of-letter write-back window, built by the page (keeps this view
  // presentational — the API call and state live in WriteBackPanel).
  writeBackSlot?: ReactNode
}

// "Month Year" (e.g. "June 2026"). period_start is the 1st of the month, stored
// in UTC — render in UTC so the season label can't drift across timezones.
function formatSeasonLabel(start: string): string {
  return new Date(start).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function renderParagraphs(text: string, className: string) {
  return text.split(/\n\n|\n/).filter(Boolean).map((para, i) => (
    <p key={i} className={className}>{para}</p>
  ))
}

const BODY = 'font-lora text-[16px] text-charcoal leading-[1.7]'
const MOVEMENT_LABEL = 'font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[8px]'

// Premium "season finale" reader for monthly letters. Presentational only:
// share/revisit/persona LOGIC stays in the page and arrives via props.
export default function SeasonFinaleView({
  payload,
  // voicePersona is kept in Props for the contract / 4b-iii share card; not
  // destructured here so it can't be flagged as an unused variable.
  voicePersonaName,
  suggestedPersona,
  periodStart,
  startingConv,
  onStartConversation,
  onRevisit,
  onShare,
  writeBackSlot,
}: Props) {
  return (
    <>
      {/* ── Cover ── */}
      <div className="px-[24px] pt-[8px] pb-[8px] text-center">
        <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-sepia mb-[12px]">
          Season · {formatSeasonLabel(periodStart)}
        </p>
        {payload.title && (
          <h1 className="font-cormorant text-[30px] font-medium text-ink leading-tight">
            {payload.title}
          </h1>
        )}
        {/* W-monogram seal — typographic, no image asset */}
        <div className="mx-auto mt-[18px] mb-[24px] w-[46px] h-[46px] rounded-full border border-bronze flex items-center justify-center">
          <span className="font-cormorant text-[26px] text-bronze leading-none">W</span>
        </div>
      </div>

      {/* ── Paper page (floats on the vellum) ── */}
      <div className="mx-[16px] bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[20px] py-[24px] flex flex-col gap-[22px]">
        {payload.opening && (
          <div>
            <p className={MOVEMENT_LABEL}>The through-line</p>
            <div className="flex flex-col gap-[14px]">
              {renderParagraphs(payload.opening, BODY)}
            </div>
          </div>
        )}

        {payload.references && (
          <div>
            <p className={MOVEMENT_LABEL}>What changed</p>
            <div className="flex flex-col gap-[14px]">
              {renderParagraphs(payload.references, BODY)}
            </div>
          </div>
        )}

        {/* Keepsake — centered, set apart between two short bronze rules */}
        {payload.pull_quote && (
          <div className="flex flex-col items-center text-center gap-[12px] py-[4px]">
            <span className="h-px w-[32px] bg-bronze/60" />
            <p className="font-cormorant italic text-[21px] text-ink leading-snug">
              {payload.pull_quote}
            </p>
            <span className="h-px w-[32px] bg-bronze/60" />
          </div>
        )}

        {payload.forward_gesture && (
          <div className="border-t border-[0.5px] border-edge pt-[18px]">
            <p className={MOVEMENT_LABEL}>The season ahead</p>
            <div className="flex flex-col gap-[14px]">
              {renderParagraphs(payload.forward_gesture, BODY)}
            </div>
          </div>
        )}

        {/* Practical takeaway — a quiet, concrete thing to carry the season ahead. */}
        {payload.practical_takeaway && (
          <div className="border-t border-[0.5px] border-edge pt-[18px]">
            <p className={MOVEMENT_LABEL}>To carry this season</p>
            <p className={BODY}>{payload.practical_takeaway}</p>
          </div>
        )}

        {/* Sign-off — closes the letter prose */}
        {voicePersonaName && (
          <div className="mt-[12px] font-cormorant italic text-bronze">
            <p className="text-[17px] leading-snug">Yours faithfully,</p>
            <p className="text-[19px] leading-snug">{voicePersonaName}</p>
          </div>
        )}
      </div>

      {/* ── Footer: write-back + suggested persona + revisit + share ── */}
      <div className="px-[24px] pt-[24px] pb-[40px]">
        {writeBackSlot}

        {suggestedPersona && (
          <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
              Where to turn next
            </p>
            <button
              type="button"
              onClick={() => onStartConversation(suggestedPersona.slug)}
              disabled={startingConv}
              className="w-full flex items-center gap-[14px] text-left disabled:opacity-50"
            >
              <div className="w-[48px] h-[48px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-edge flex items-center justify-center">
                {suggestedPersona.portrait_url ? (
                  <Image
                    src={suggestedPersona.portrait_url}
                    alt={suggestedPersona.name}
                    width={48}
                    height={48}
                    className="object-cover w-full h-full"
                  />
                ) : (
                  <span className="font-cormorant text-[20px] font-medium text-charcoal">
                    {suggestedPersona.name.charAt(0)}
                  </span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
                  {startingConv ? 'Opening…' : suggestedPersona.name}
                </p>
                {suggestedPersona.tagline && (
                  <p className="font-lora text-[13px] text-charcoal mt-[2px]">
                    {suggestedPersona.tagline}
                  </p>
                )}
              </div>
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={onRevisit}
          className="mt-[24px] w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
        >
          Revisit this letter with a mind
        </button>

        {payload.pull_quote && (
          <button
            type="button"
            onClick={onShare}
            className="mt-[12px] w-full h-[48px] rounded-sm border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink transition-colors"
          >
            Share this season
          </button>
        )}
      </div>
    </>
  )
}
