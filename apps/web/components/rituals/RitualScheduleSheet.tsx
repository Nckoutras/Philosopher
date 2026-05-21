'use client'

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import type { SavedLineRead } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'

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
  const [note, setNote] = useState('')
  const [scheduledFor, setScheduledFor] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)

  // Lazy-load saved lines on first open
  useEffect(() => {
    if (!open || savedLines !== null) return
    api.listSavedLines()
      .then((res) => {
        setSavedLines(res.items)
        if (res.items.length > 0) setSelectedLineId(res.items[0].id)
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
  const maxDate = toDatetimeLocalString(new Date(Date.now() + 365 * 24 * 60 * 60 * 1000))
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
        `Letter scheduled for ${d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`
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
          <p className="font-cormorant text-[19px] font-medium text-ink">
            Send to future self
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
      <div className="overflow-y-auto flex-1 px-6 py-5 flex flex-col gap-[18px]">

        {/* Reflection picker */}
        <div>
          <label className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia block mb-[8px]">
            Reflection
          </label>
          {savedLines === null ? (
            <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
          ) : savedLines.length === 0 ? (
            <p className="font-lora text-[13px] text-charcoal leading-[1.55]">
              No saved reflections yet. Tap <em>Save line</em> on any persona reply first.
            </p>
          ) : (
            <select
              value={selectedLineId}
              onChange={(e) => setSelectedLineId(e.target.value)}
              className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[13px] text-ink appearance-none"
            >
              {savedLines.map((sl) => (
                <option key={sl.id} value={sl.id}>
                  {sl.persona_display_name} — {sl.message_content.length > 60
                    ? sl.message_content.slice(0, 60) + '…'
                    : sl.message_content}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Note textarea */}
        <div>
          <label className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia block mb-[8px]">
            A note for your future self{' '}
            <span className="normal-case tracking-normal text-charcoal">(optional)</span>
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="What do you want to remember? What question are you sitting with?"
            className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[13px] text-ink placeholder:text-charcoal resize-none"
          />
        </div>

        {/* Datetime picker (C1: local time, not UTC) */}
        <div>
          <label className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia block mb-[8px]">
            Deliver on
          </label>
          <input
            type="datetime-local"
            value={scheduledFor}
            min={minDate}
            max={maxDate}
            onChange={(e) => setScheduledFor(e.target.value)}
            className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[13px] text-ink [color-scheme:light]"
          />
          <p className="font-lora text-[11px] text-charcoal mt-[4px]">
            Minimum 1 hour from now · Maximum 1 year
          </p>
        </div>

        {/* Recipient (read-only v1) */}
        <div>
          <label className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia block mb-[8px]">
            To
          </label>
          <p className="font-lora text-[13px] text-charcoal">{userEmail}</p>
        </div>

        {fieldError && (
          <p className="font-lora text-[13px] text-red-600 leading-snug">{fieldError}</p>
        )}
      </div>

      {/* ── Submit ── */}
      <div
        className="px-6 pt-4 border-t border-[0.5px] border-edge flex-shrink-0"
        style={{ paddingBottom: 'max(24px, env(safe-area-inset-bottom))' }}
      >
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-[14px] bg-ink text-vellum rounded-sm font-cormorant text-[17px] font-medium disabled:opacity-40"
        >
          {submitting ? 'Scheduling…' : 'Schedule letter'}
        </button>
      </div>
    </BottomSheet>
  )
}
