'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import AutoGrowTextarea from '@/components/ui/AutoGrowTextarea'

interface Props {
  letterId: string
  personaName: string | null
  // Existing write-back, if the reader has already responded to this letter.
  // When present the panel renders read-only (one write-back per letter; the
  // backend overwrites on re-submit, but v1 shows the saved words quietly).
  initialWriteBack: string | null
  // Cadence of the letter being answered. Only the post-submit confirmation
  // branches on it: "what comes next" is seven days for a weekly letter and a
  // whole month for a season one, and a tester watched for a reply the
  // following week after writing back to a season letter. (A14.)
  letterKind: 'weekly' | 'monthly'
}

// Which season letter a write-back sent NOW will actually reach.
//
// The monthly cron fires on the last calendar day of the month at 17:00 UTC, so
// on that day this month's season letter is already dispatched (or about to be)
// and the words travel to the NEXT one. Every other day of the month, they reach
// this month's. Months are uneven, so the last day is computed rather than assumed:
// `new Date(y, m + 1, 0)` is the final day of month m, and `new Date(y, m + 1, 1)`
// rolls December into January of the following year on its own.
function seasonLetterMonthName(now: Date = new Date()): string {
  const lastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const target =
    now.getDate() >= lastDayOfMonth
      ? new Date(now.getFullYear(), now.getMonth() + 1, 1)
      : new Date(now.getFullYear(), now.getMonth(), 1)
  return target.toLocaleString('en-US', { month: 'long' })
}

// Quiet end-of-letter window: a short space for the reader to write back to the
// persona. No live reply in v1 — the text is captured and carried into the next
// letter. Deliberately not a loud CTA: a soft prompt, a plain field, a small send.
export default function WriteBackPanel({ letterId, personaName, initialWriteBack, letterKind }: Props) {
  const [text, setText] = useState('')
  const [saved, setSaved] = useState<string | null>(initialWriteBack)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(false)

  const to = personaName ?? 'the room'

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || submitting) return
    setSubmitting(true)
    setError(false)
    try {
      const updated = await api.writeBackToLetter(letterId, trimmed)
      setSaved(updated.write_back_text ?? trimmed)
      setText('')
    } catch {
      setError(true)
      setSubmitting(false)
    }
  }

  // Already written back — show the saved words quietly, with a soft confirmation.
  if (saved) {
    return (
      <div className="mt-[28px] pt-[20px] border-t border-[0.5px] border-edge">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
          You wrote back
        </p>
        <p className="font-lora italic text-[15px] text-charcoal leading-[1.7] pl-[14px] border-l-2 border-bronze/60">
          {saved}
        </p>
        <p className="font-lora text-[12px] text-sepia mt-[12px]">
          {letterKind === 'monthly' ? (
            <>
              Kept. {to} doesn&rsquo;t reply here — your words travel with the correspondence and reach whoever writes the season letter at the end of {seasonLetterMonthName()}.
            </>
          ) : (
            <>
              Kept. {to} doesn&rsquo;t reply here — your words travel with the correspondence and reach whoever writes this Sunday.
            </>
          )}
        </p>
      </div>
    )
  }

  return (
    <div className="mt-[28px] pt-[20px] border-t border-[0.5px] border-edge">
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
        Write back to {to}
      </p>
      <AutoGrowTextarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={submitting}
        minRows={2}
        maxHeight={200}
        placeholder="A line back to them…"
        ariaLabel={`Write back to ${to}`}
        className="w-full bg-white border-[0.5px] border-edge rounded-[10px] px-[14px] py-[10px] font-lora text-[15px] text-ink leading-[1.6] placeholder:text-sepia/60 focus:outline-none focus:border-bronze/50"
      />
      <div className="mt-[10px] flex items-center justify-end gap-[12px]">
        {error && (
          <span className="font-lora text-[12px] text-sepia">Couldn&rsquo;t send — try again.</span>
        )}
        <button
          type="button"
          onClick={handleSend}
          disabled={submitting || text.trim().length === 0}
          className="h-[36px] px-[18px] rounded-sm bg-ink text-vellum font-cormorant text-[15px] font-medium transition-opacity disabled:opacity-40"
        >
          {submitting ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
