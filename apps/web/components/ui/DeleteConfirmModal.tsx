'use client'

import { useEffect, useRef, useState } from 'react'

interface Props {
  open: boolean
  title: string
  body: string
  confirmLabel?: string
  loading: boolean
  error: string | null
  onConfirm: () => void
  onClose: () => void
  /** When set, the confirm button stays disabled until the user types this
   *  string EXACTLY (case-sensitive). Used only by account deletion, which is
   *  the one irreversible action in the app — a misclick there cannot be
   *  undone by any support action, because there is nothing left to restore.
   *  Omitted everywhere else: a conversation delete does not earn this much
   *  friction, and adding it would train people to type through the prompt. */
  requireTypedConfirmation?: string
  /** Label rendered above the input. Only read when requireTypedConfirmation
   *  is set. */
  typedConfirmationLabel?: string
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
  requireTypedConfirmation,
  typedConfirmationLabel,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const [typed, setTyped] = useState('')

  // Case-sensitive equality, not trim() or toLowerCase(). The point of typing
  // the word is that it cannot happen by accident, and every softening of the
  // comparison moves it back toward something a stray paste satisfies.
  const confirmBlocked =
    requireTypedConfirmation !== undefined && typed !== requireTypedConfirmation

  // Keyboard (Escape + Tab trap) handlers
  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && !loading) { onClose(); return }
      if (e.key !== 'Tab') return
      const modal = cancelRef.current?.closest('[role="dialog"]') as HTMLElement | null
      if (!modal) return
      // Inputs included: with typed confirmation the field is inside the trap,
      // and a Tab cycle that skipped it would strand keyboard users on a
      // disabled confirm button with no way to reach what enables it.
      const focusable = Array.from(
        modal.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])'),
      )
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

  // Initial focus on Cancel button. Deliberately Cancel and not the input:
  // the safe action is the one that should be one keystroke away.
  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  // A reopened modal starts empty. Without this, cancelling a deletion and
  // reopening it would present an already-satisfied confirmation.
  useEffect(() => {
    if (!open) setTyped('')
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

        {requireTypedConfirmation !== undefined && (
          <div className="mb-6">
            <label
              htmlFor="delete-confirm-input"
              className="block font-lora text-[12px] text-charcoal mb-2"
            >
              {typedConfirmationLabel}
            </label>
            <input
              id="delete-confirm-input"
              type="text"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              disabled={loading}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="none"
              spellCheck={false}
              className="w-full font-lora text-[13px] text-ink bg-vellum border border-edge rounded-sm py-2 px-3 disabled:opacity-50"
            />
          </div>
        )}

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
            disabled={loading || confirmBlocked}
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
