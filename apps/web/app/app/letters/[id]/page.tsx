'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { ChevronLeft } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { WeeklyLetter, Persona } from '@/lib/api'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import SharePreviewModal from '@/components/share/SharePreviewModal'
import SeasonFinaleView from '@/components/letters/SeasonFinaleView'
import WriteBackPanel from '@/components/letters/WriteBackPanel'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatWeekSpan(start: string, end: string): string {
  const s = new Date(start)
  const e = new Date(end)
  const sm = MONTHS[s.getUTCMonth()]
  const sd = s.getUTCDate()
  const em = MONTHS[e.getUTCMonth()]
  const ed = e.getUTCDate()
  const yr = e.getUTCFullYear()
  if (sm === em) return `${sm} ${sd}–${ed}, ${yr}`
  return `${sm} ${sd} – ${em} ${ed}, ${yr}`
}

function renderParagraphs(text: string, className: string) {
  return text.split(/\n\n|\n/).filter(Boolean).map((para, i) => (
    <p key={i} className={className}>{para}</p>
  ))
}

export default function LetterReadPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const token = useStore((s) => s.token)
  const subscription = useStore((s) => s.subscription)
  const isPro = subscription?.status === 'active' && subscription?.plan !== 'free'
  const markLetterRead = useStore((s) => s.markLetterRead)

  const [loading, setLoading] = useState(true)
  const [letter, setLetter] = useState<WeeklyLetter | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [startingConv, setStartingConv] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    if (!isPro) {
      router.replace('/app/upgrade')
      return
    }

    async function load() {
      try {
        const [letterRes, personasRes] = await Promise.allSettled([
          api.getWeeklyLetter(id),
          api.getPersonas(),
        ])
        setLetter(letterRes.status === 'fulfilled' ? letterRes.value : null)
        setPersonas(personasRes.status === 'fulfilled' ? personasRes.value : [])
        // Opening the detail marks it read server-side (read_at); clear the Home
        // "something new" star immediately for this session too.
        if (letterRes.status === 'fulfilled') markLetterRead(id)
      } finally {
        setLoading(false)
        setMounted(true)
      }
    }

    load()
  }, [token, isPro, id, router, markLetterRead])

  async function handleStartConversation(slug: string) {
    if (startingConv) return
    setStartingConv(true)
    try {
      const conv = await api.createConversation(slug)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch {
      setStartingConv(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum">
        <div className="px-[24px] pt-[22px] pb-[16px]">
          <div className="w-[32px] h-[32px] -ml-[4px] mb-[12px]" />
          <div className="h-[10px] w-[120px] bg-linen rounded animate-pulse mb-[10px]" />
          <div className="h-[36px] w-[260px] bg-linen rounded animate-pulse mb-[16px]" />
          <div className="w-[40px] h-[1px] bg-linen mb-[20px]" />
        </div>
        <div className="px-[24px] flex flex-col gap-[12px]">
          <div className="h-[18px] bg-linen rounded animate-pulse" />
          <div className="h-[18px] w-5/6 bg-linen rounded animate-pulse" />
          <div className="h-[18px] w-4/6 bg-linen rounded animate-pulse" />
          <div className="h-[18px] bg-linen rounded animate-pulse mt-[8px]" />
          <div className="h-[18px] w-5/6 bg-linen rounded animate-pulse" />
        </div>
      </main>
    )
  }

  const payload = letter?.payload ?? null
  const isUnavailable = !letter || letter.status !== 'generated' || !payload

  if (isUnavailable) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[22px]">
        <button
          type="button"
          onClick={() => router.push('/app/letters')}
          aria-label="Back to letters"
          className="flex items-center justify-center w-[32px] h-[32px] -ml-[4px] mb-[32px]"
        >
          <ChevronLeft size={20} strokeWidth={1.5} className="text-sepia" />
        </button>
        <p className="font-cormorant text-[22px] font-normal text-ink">
          This letter isn&rsquo;t available.
        </p>
        <button
          type="button"
          onClick={() => router.push('/app/letters')}
          className="mt-[16px] font-lora text-[13px] text-sepia underline underline-offset-2"
        >
          Back to letters
        </button>
      </main>
    )
  }

  const suggestedPersona = payload.suggested_persona_slug
    ? personas.find((p) => p.slug === payload.suggested_persona_slug) ?? null
    : null

  const voicePersona = personas.find((p) => p.slug === letter.voice_persona_slug) ?? null

  // Quiet end-of-letter write-back window, shared by the weekly inline reader and
  // the monthly SeasonFinaleView. The reading is Pro-gated (non-Pro is redirected
  // to /app/upgrade above), so this surface is only ever reached by Pro readers.
  const writeBack = (
    <WriteBackPanel
      letterId={id}
      personaName={letter.voice_persona_name}
      initialWriteBack={letter.write_back_text}
    />
  )

  return (
    <main
      className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]"
      style={{ opacity: mounted ? 1 : 0, transition: 'opacity 0.45s ease' }}
    >
      <div className="px-[24px] pt-[22px] pb-[8px] flex items-center gap-[4px]">
        <button
          type="button"
          onClick={() => router.push('/app/letters')}
          aria-label="Back to letters"
          className="flex items-center justify-center w-[32px] h-[32px] -ml-[4px]"
        >
          <ChevronLeft size={20} strokeWidth={1.5} className="text-sepia" />
        </button>
      </div>

      {letter.kind === 'monthly' ? (
        <SeasonFinaleView
          payload={payload}
          voicePersona={voicePersona}
          voicePersonaName={letter.voice_persona_name}
          suggestedPersona={suggestedPersona}
          periodStart={letter.period_start}
          startingConv={startingConv}
          onStartConversation={handleStartConversation}
          onRevisit={() => setPickerOpen(true)}
          onShare={() => setShareOpen(true)}
          writeBackSlot={writeBack}
        />
      ) : (
      <div className="px-[24px] pb-[40px]">
        {/* Week span */}
        <p className="font-lora text-[12px] uppercase tracking-[0.14em] text-sepia mb-[8px]">
          {formatWeekSpan(letter.period_start, letter.period_end)}
        </p>

        {/* Title */}
        {payload.title && (
          <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight mb-[16px]">
            {payload.title}
          </h1>
        )}

        {/* Bronze divider */}
        <div className="w-[40px] h-[1px] bg-bronze mb-[24px]" />

        {/* Opening */}
        {payload.opening && (
          <div className="flex flex-col gap-[14px] mb-[20px]">
            {renderParagraphs(payload.opening, 'font-lora text-[16px] text-charcoal leading-[1.7]')}
          </div>
        )}

        {/* References */}
        {payload.references && (
          <div className="flex flex-col gap-[14px] mb-[20px]">
            {renderParagraphs(payload.references, 'font-lora text-[16px] text-charcoal leading-[1.7]')}
          </div>
        )}

        {/* Pull quote */}
        {payload.pull_quote && (
          <blockquote className="font-cormorant italic text-[20px] text-ink pl-[16px] border-l-2 border-bronze my-[24px] leading-snug">
            {payload.pull_quote}
          </blockquote>
        )}

        {/* Forward gesture */}
        {payload.forward_gesture && (
          <div className="flex flex-col gap-[14px] mb-[32px]">
            {renderParagraphs(payload.forward_gesture, 'font-lora text-[16px] text-charcoal leading-[1.7]')}
          </div>
        )}

        {/* Practical takeaway — a quiet, concrete thing to carry this week. */}
        {payload.practical_takeaway && (
          <div className="border-t border-[0.5px] border-edge pt-[18px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[8px]">
              To carry this week
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.7]">
              {payload.practical_takeaway}
            </p>
          </div>
        )}

        {/* Sign-off — closes the letter prose */}
        {letter.voice_persona_name && (
          <div className="mt-[28px] mb-[32px] font-cormorant italic text-bronze">
            <p className="text-[17px] leading-snug">Yours faithfully,</p>
            <p className="text-[19px] leading-snug">{letter.voice_persona_name}</p>
          </div>
        )}

        {/* Write back to the persona — quiet, end of letter */}
        {writeBack}

        {/* Suggested next mind */}
        {suggestedPersona && (
          <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[14px] mt-[8px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
              Where to turn next
            </p>
            <button
              type="button"
              onClick={() => handleStartConversation(suggestedPersona.slug)}
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

        {/* Revisit this letter with a chosen mind — opens the persona picker */}
        <button
          type="button"
          onClick={() => setPickerOpen(true)}
          className="mt-[24px] w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
        >
          Revisit this letter with a mind
        </button>

        {payload.pull_quote && (
          <button
            type="button"
            onClick={() => setShareOpen(true)}
            className="mt-[12px] w-full h-[48px] rounded-sm border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink transition-colors"
          >
            Share this letter
          </button>
        )}
      </div>
      )}

      <PersonaPickerSheet
        open={pickerOpen}
        revisitLetterId={id}
        onClose={() => setPickerOpen(false)}
        onCreated={(convId) => router.push(`/app/chat/conv/${convId}`)}
      />

      {payload.pull_quote && (
        <SharePreviewModal
          isOpen={shareOpen}
          onClose={() => setShareOpen(false)}
          kind="letter"
          weeklyLetterId={id}
          letterTitle={payload.title ?? undefined}
          seasonImagePreview={letter.kind === 'monthly'}
          personaName={letter.voice_persona_name ?? undefined}
          portraitUrl={voicePersona?.portrait_url}
          quote={payload.pull_quote}
        />
      )}
    </main>
  )
}
