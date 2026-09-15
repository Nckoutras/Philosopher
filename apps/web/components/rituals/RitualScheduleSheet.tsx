'use client'

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import type { SavedLineRead } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'
import SavedLinePicker from './SavedLinePicker'

interface Props {
  open: boolean
  onClose: () => void
  userEmail: string
  // Γ-6 "Return to this". When set, the sheet is PRE-BOUND to one saved line:
  // the picker is replaced by that line, because the person already chose it —
  // in the conversation, on the thing they were reading. Re-asking "which
  // reflection?" immediately after would undo the whole gesture.
  //
  // Absent (the Rituals-tab door) everything below behaves exactly as before.
  presetLineId?: string
  // Confirmation toast for the pre-bound door, founder-locked 2026-09-15. The
  // Rituals door keeps its own date-stating toast: there the person has just
  // set a date on a form and the date is the confirmation, where here they
  // tapped one preset and the promise is the confirmation.
  confirmationText?: string
}

function toDatetimeLocalString(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Γ-6 preset horizons, founder-locked 2026-09-15. Three, not a calendar: the
// gesture is "bring this back to me", and the decision it asks for is roughly
// how far away, which three answers cover. The datetime-local field below stays
// exactly as it was for anyone who wants an actual date — this adds a faster
// path to it, it does not replace it.
//
// Days, not months, deliberately. addMonths arithmetic has to answer what "in a
// month" means on the 31st, and every answer to that is a rule nobody asked for.
const PRESETS: { label: string; days: number }[] = [
  { label: 'In a week', days: 7 },
  { label: 'In a month', days: 30 },
  { label: 'In three months', days: 90 },
]

export default function RitualScheduleSheet({ open, onClose, userEmail, presetLineId, confirmationText }: Props) {
  const [savedLines, setSavedLines] = useState<SavedLineRead[] | null>(null)
  const [selectedLineId, setSelectedLineId] = useState('')
  const [portraitUrlsBySlug, setPortraitUrlsBySlug] = useState<Record<string, string>>({})
  const [note, setNote] = useState('')
  const [prediction, setPrediction] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)

  // Lazy-load saved lines + personas on first open
  useEffect(() => {
    if (!open || savedLines !== null) return
    Promise.all([api.listSavedLines(), api.getPersonas()])
      .then(([linesRes, personas]) => {
        setSavedLines(linesRes.items)
        // Never override a pre-bound line with "the newest one". The caller's
        // choice is the whole point of that door, and this load is async — so
        // without the guard the selection would silently change under the user
        // a moment after the sheet opened.
        if (!presetLineId && linesRes.items.length > 0) setSelectedLineId(linesRes.items[0].id)
        const map: Record<string, string> = {}
        for (const p of personas) {
          if (p.portrait_url) map[p.slug] = p.portrait_url
        }
        setPortraitUrlsBySlug(map)
      })
      .catch(() => setSavedLines([]))
  }, [open, savedLines, presetLineId])

  // Reset transient state on close, preserve savedLines cache
  useEffect(() => {
    if (!open) {
      setNote('')
      setPrediction('')
      setScheduledFor('')
      setFieldError(null)
    }
  }, [open])

  // Bind the caller's line whenever the sheet opens on it. In the effect rather
  // than in useState's initialiser because this component is mounted once and
  // reopened many times — an initialiser would bind the FIRST line the chat ever
  // passed and then keep it for every later tap.
  useEffect(() => {
    if (open && presetLineId) setSelectedLineId(presetLineId)
  }, [open, presetLineId])

  const minDate = toDatetimeLocalString(new Date(Date.now() + 60 * 60 * 1000))
  const maxDate = toDatetimeLocalString(new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000))
  const canSubmit = selectedLineId !== '' && scheduledFor !== '' && !submitting

  async function handleSubmit() {
    if (!canSubmit) return
    setSubmitting(true)
    setFieldError(null)
    try {
      await api.createScheduledEmail({
        saved_line_id: selectedLineId,
        note: note.trim() || undefined,
        prediction: prediction.trim() || undefined,
        scheduled_for: new Date(scheduledFor).toISOString(),
      })
      onClose()
      if (confirmationText) {
        toast.success(confirmationText)
      } else {
        const d = new Date(scheduledFor)
        toast.success(
          `Message scheduled for ${d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
        )
      }
    } catch (err) {
      setFieldError(err instanceof Error ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <BottomSheet open={open} onClose={onClose} maxHeight="90svh">
      {/* ── Header ── */}
      <div className="px-6 pt-5 pb-3 border-b border-[0.5px] border-edge flex items-start justify-between flex-shrink-0">
        <div>
          <p className="font-cormorant text-[21px] font-medium text-ink">
            Message to future self
          </p>
          <p className="font-lora text-[12px] text-charcoal mt-[2px]">
            A reflection arrives in your inbox at the date you choose.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="p-2 font-lora text-[22px] text-sepia leading-none ml-4 flex-shrink-0"
        >
          ×
        </button>
      </div>

      {/* ── Form body ── */}
      <div className="overflow-y-auto flex-1 min-h-0 px-6 py-5 flex flex-col gap-[18px]">

        {/* Datetime picker (C1: local time, not UTC) */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            Deliver on
          </label>
          {/* Γ-6 presets. They WRITE THE DATE FIELD rather than bypassing it, so
              there is one source of truth for scheduled_for and the person can see
              what they just chose — and adjust it. aria-pressed marks the active
              one; a preset whose date the user then edits by hand simply stops
              matching, which is the honest state. */}
          <div className="flex gap-[6px] flex-wrap mb-[8px]">
            {PRESETS.map((preset) => {
              const value = toDatetimeLocalString(
                new Date(Date.now() + preset.days * 24 * 60 * 60 * 1000)
              )
              const active = scheduledFor === value
              return (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => setScheduledFor(value)}
                  aria-pressed={active}
                  className={
                    active
                      ? 'bg-linen-deep text-ink border border-ink font-medium px-[10px] py-[6px] font-lora text-[13px] rounded-sm'
                      : 'bg-paper text-ink border border-[0.5px] border-edge px-[10px] py-[6px] font-lora text-[13px] rounded-sm transition-colors'
                  }
                >
                  {preset.label}
                </button>
              )
            })}
          </div>
          <input
            type="datetime-local"
            value={scheduledFor}
            min={minDate}
            max={maxDate}
            onChange={(e) => setScheduledFor(e.target.value)}
            className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[15px] font-medium text-ink [color-scheme:light] transition-[border-color,box-shadow] duration-200 focus:outline-none focus:border-bronze focus:ring-1 focus:ring-bronze/20"
          />
          <p className="font-lora text-[12px] text-charcoal mt-[4px]">
            Minimum 1 hour from now · Maximum 5 years
          </p>
        </div>

        {/* Note textarea */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            A note for your future self
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="What do you want to remember?"
            className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[15px] font-medium text-ink placeholder:text-charcoal/40 placeholder:font-normal resize-none transition-[border-color,box-shadow] duration-200 focus:outline-none focus:border-bronze focus:ring-1 focus:ring-bronze/20"
          />
        </div>

        {/* Prediction textarea (043 — optional, surfaced only on the arrived screen) */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            A prediction
          </label>
          <textarea
            value={prediction}
            onChange={(e) => setPrediction(e.target.value)}
            maxLength={200}
            rows={2}
            placeholder="What will have changed?"
            className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[15px] font-medium text-ink placeholder:text-charcoal/40 placeholder:font-normal resize-none transition-[border-color,box-shadow] duration-200 focus:outline-none focus:border-bronze focus:ring-1 focus:ring-bronze/20"
          />
          <p className="font-lora text-[12px] text-charcoal mt-[4px]">
            Optional. Guess where you&rsquo;ll be by the time it arrives — you&rsquo;ll see it again then.
          </p>
        </div>

        {/* Reflection picker */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            Reflection
          </label>
          {presetLineId ? (
            // Pre-bound door: show WHICH line, never a chooser. Falls back to a
            // neutral line of text while the lazy load is still in flight — the
            // submit does not depend on this render, only on selectedLineId.
            <p className="font-lora text-[14px] text-ink leading-[1.55]">
              {savedLines?.find((l) => l.id === presetLineId)?.message_content ?? 'The line you marked.'}
            </p>
          ) : savedLines === null ? (
            <p className="font-lora text-[14px] text-sepia italic">Loading…</p>
          ) : savedLines.length === 0 ? (
            <p className="font-lora text-[14px] text-charcoal leading-[1.55]">
              No saved reflections yet. Tap <em>Save line</em> on any persona reply first.
            </p>
          ) : (
            <SavedLinePicker
              savedLines={savedLines}
              selectedLineId={selectedLineId}
              onChange={setSelectedLineId}
              portraitUrlsBySlug={portraitUrlsBySlug}
            />
          )}
        </div>

        {/* Recipient (read-only v1) */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            To
          </label>
          <p className="font-lora text-[14px] text-charcoal">{userEmail}</p>
        </div>

        {fieldError && (
          <p className="font-lora text-[14px] text-red-600 leading-snug">{fieldError}</p>
        )}
      </div>

      {/* ── Submit ── */}
      {/* Clears the floating tab bar footprint (4rem pill + 12px lift + 8px breathing)
          so the submit button isn't overpainted by the bar's backdrop-filter on iOS.
          Excludes safe-area on purpose — the BottomSheet panel already insets
          env(safe-area-inset-bottom) as the single source of truth. */}
      <div className="px-6 pt-4 pb-[calc(4rem+12px+8px)] border-t border-[0.5px] border-edge flex-shrink-0">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-[14px] bg-ink text-vellum rounded-sm font-cormorant text-[17px] font-medium disabled:opacity-40"
        >
          {submitting ? 'Scheduling…' : 'Schedule message'}
        </button>
      </div>
    </BottomSheet>
  )
}
