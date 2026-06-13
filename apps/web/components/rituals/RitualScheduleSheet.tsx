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
}

function toDatetimeLocalString(d: Date): string {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function RitualScheduleSheet({ open, onClose, userEmail }: Props) {
  const [savedLines, setSavedLines] = useState<SavedLineRead[] | null>(null)
  const [selectedLineId, setSelectedLineId] = useState('')
  const [portraitUrlsBySlug, setPortraitUrlsBySlug] = useState<Record<string, string>>({})
  const [note, setNote] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)

  // Lazy-load saved lines + personas on first open
  useEffect(() => {
    if (!open || savedLines !== null) return
    Promise.all([api.listSavedLines(), api.getPersonas()])
      .then(([linesRes, personas]) => {
        setSavedLines(linesRes.items)
        if (linesRes.items.length > 0) setSelectedLineId(linesRes.items[0].id)
        const map: Record<string, string> = {}
        for (const p of personas) {
          if (p.portrait_url) map[p.slug] = p.portrait_url
        }
        setPortraitUrlsBySlug(map)
      })
      .catch(() => setSavedLines([]))
  }, [open, savedLines])

  // Reset transient state on close, preserve savedLines cache
  useEffect(() => {
    if (!open) {
      setNote('')
      setScheduledFor('')
      setFieldError(null)
    }
  }, [open])

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
        scheduled_for: new Date(scheduledFor).toISOString(),
      })
      onClose()
      const d = new Date(scheduledFor)
      toast.success(
        `Message scheduled for ${d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
      )
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
          className="font-lora text-[20px] text-sepia leading-none ml-4 flex-shrink-0"
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

        {/* Reflection picker */}
        <div>
          <label className="font-lora text-[12px] font-medium uppercase tracking-[0.18em] text-charcoal block mb-[8px]">
            Reflection
          </label>
          {savedLines === null ? (
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
      {/* Plain 24px — BottomSheet's panel now owns the env(safe-area-inset-bottom)
          inset, so adding it here too would double-compensate. */}
      <div className="px-6 pt-4 pb-6 border-t border-[0.5px] border-edge flex-shrink-0">
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
