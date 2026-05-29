'use client'

import { useEffect } from 'react'
import { useStore } from '@/lib/store'
import type { PaywallDetails } from '@/lib/store'

interface Props {
  open: boolean
  details: PaywallDetails | null
  onClose: () => void
}

function formatResetAt(date: Date): string {
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (date.toDateString() === now.toDateString()) return `today at ${timeStr}`
  if (date.toDateString() === tomorrow.toDateString()) return `tomorrow at ${timeStr}`
  return `on ${date.toLocaleDateString([], { month: 'long', day: 'numeric' })} at ${timeStr}`
}

export default function PaywallModal({ open, details, onClose }: Props) {
  const personaName = useStore((s) => s.activePersonaName)

  useEffect(() => {
    if (!open) return
    window.history.pushState({ modal: 'paywall-modal' }, '')
    return () => {
      if (window.history.state?.modal === 'paywall-modal') {
        window.history.back()
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    function handlePopState() { onClose() }
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('popstate', handlePopState)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('popstate', handlePopState)
    }
  }, [open, onClose])

  if (!open || !details) return null

  const upgradeLabel = details.upgradeTarget === 'premium' ? 'Premium' : 'Pro'
  const personaLabel = personaName ?? 'this mind'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paywall-title"
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal card */}
      <div className="relative z-10 w-full max-w-[400px] bg-paper rounded-lg p-8 shadow-[0_8px_32px_rgba(31,27,20,0.18)]">
        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 font-lora text-[18px] text-sepia hover:text-ink transition-colors leading-none"
        >
          ×
        </button>

        <h2
          id="paywall-title"
          className="font-cormorant text-[26px] font-medium text-ink leading-tight mb-4"
        >
          Daily limit reached.
        </h2>

        <p className="font-lora text-[13px] text-charcoal leading-relaxed mb-2">
          You&apos;ve used today&apos;s reflections with {personaLabel}.
        </p>

        <p className="font-lora text-[13px] text-charcoal leading-relaxed mb-8">
          Your free conversations reset{' '}
          {formatResetAt(details.resetAt)}.
        </p>

        <div className="flex flex-col gap-3">
          <div className="relative group">
            <button
              disabled
              className="w-full bg-[rgba(31,27,20,0.3)] text-[rgba(239,227,204,0.6)] font-lora text-[14px] py-3 px-6 rounded-sm cursor-not-allowed"
            >
              Upgrade to {upgradeLabel} → Coming soon
            </button>
            {/* Desktop tooltip */}
            <span
              role="tooltip"
              className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-ink text-vellum font-lora text-[11px] rounded-sm whitespace-nowrap pointer-events-none"
            >
              Subscriptions launching soon.
            </span>
          </div>

          <button
            onClick={onClose}
            className="font-lora text-[13px] text-sepia underline underline-offset-2 text-center hover:text-ink transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
