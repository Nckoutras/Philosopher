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
}

// Quiet end-of-letter window: a short space for the reader to write back to the
// persona. No live reply in v1 — the text is captured and carried into the next
// letter. Deliberately not a loud CTA: a soft prompt, a plain field, a small send.
export default function WriteBackPanel({ letterId, personaName, initialWriteBack }: Props) {
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
          {to} will carry this forward.
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
