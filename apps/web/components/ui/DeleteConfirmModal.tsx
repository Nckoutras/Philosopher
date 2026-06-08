'use client'

import { useEffect, useRef } from 'react'

interface Props {
  open: boolean
  title: string
  body: string
  confirmLabel?: string
  loading: boolean
  error: string | null
  onConfirm: () => void
  onClose: () => void
}

export default function DeleteConfirmModal({
  open,
  title,
  body,
  confirmLabel = 'Delete',
  loading,
  error,
  onConfirm,
  onClose,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  // Keyboard (Escape + Tab trap) handlers
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && !loading) { onClose(); return }
      if (e.key !== 'Tab') return
      const modal = cancelRef.current?.closest('[role="dialog"]') as HTMLElement | null
      if (!modal) return
      const focusable = Array.from(modal.querySelectorAll<HTMLElement>('button:not([disabled])'))
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, loading, onClose])

  // Initial focus on Cancel button
  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-confirm-title"
      className="fixed inset-0 z-50 flex items-center justify-center px-6"
    >
      <div
        className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
        aria-hidden="true"
        onClick={() => { if (!loading) onClose() }}
      />

      <div className="relative z-10 w-full max-w-[340px] bg-paper rounded-lg p-6 shadow-[0_8px_32px_rgba(31,27,20,0.18)]">
        <h2
          id="delete-confirm-title"
          className="font-cormorant text-[22px] font-medium text-ink leading-tight mb-2"
        >
          {title}
        </h2>
        <p className="font-lora text-[13px] text-charcoal leading-relaxed mb-6">
          {body}
        </p>

        <div className="flex gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onClose}
            disabled={loading}
            className="flex-1 font-lora text-[13px] text-charcoal border border-edge rounded-sm py-2.5 px-4 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 font-lora text-[13px] text-vellum bg-danger rounded-sm py-2.5 px-4 flex items-center justify-center disabled:opacity-70"
          >
            {loading ? (
              <span
                className="inline-block w-3.5 h-3.5 border-[0.8px] border-vellum/30 border-t-vellum rounded-full animate-spin-slow"
                aria-label="Deleting…"
              />
            ) : (
              confirmLabel
            )}
          </button>
        </div>

        {error && (
          <p role="alert" className="font-lora text-[12px] text-danger mt-3 text-center">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
