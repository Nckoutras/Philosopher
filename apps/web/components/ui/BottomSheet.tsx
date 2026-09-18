'use client'

import { useEffect, useRef, ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface Props {
  open: boolean
  onClose: () => void
  children: ReactNode
  maxHeight?: string
}

// Everything focusable a sheet can plausibly hold. Deliberately wider than either
// of the two traps already in this codebase, and they do not even agree with each
// other: DeleteConfirmModal.tsx:59 queries `button, input` and
// SharePreviewModal.tsx:163 queries `textarea, button`, so each is blind to what
// the other covers. Sheets carry textareas, inputs, selects and links, and a trap
// that cannot see one lets Tab walk straight out of the dialog through it.
const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'textarea:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

export default function BottomSheet({ open, onClose, children, maxHeight = '75svh' }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  // Whatever had focus when the sheet opened, so it can be handed back on close.
  const returnToRef = useRef<HTMLElement | null>(null)

  // Close on Escape, and keep Tab inside the panel. (Escape replaces the previous
  // browser-history dismissal mechanism, which collided with Next.js App Router
  // client navigation and froze the tabs.)
  //
  // The trap follows the shape already in DeleteConfirmModal/SharePreviewModal —
  // wrap at the two boundaries — with one addition those do not have: a check for
  // focus that is OUTSIDE the panel entirely. Without it the "trap" only works
  // while focus happens to already be inside, and a tap on the page behind the
  // scrim hands Tab back to the document under an aria-modal dialog.
  useEffect(() => {
    if (!open) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key !== 'Tab') return

      const panel = panelRef.current
      if (!panel) return
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE))
      if (!focusable.length) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (!(active instanceof Node) || !panel.contains(active)) {
        e.preventDefault()
        const entry = e.shiftKey ? last : first
        entry.focus()
        return
      }
      if (e.shiftKey && active === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  // Focus INTO the sheet on open, and back OUT to the opener on close. Neither
  // existed: Escape and the scrim both dismissed the panel and left focus wherever
  // it had been — which on a keyboard means the reader resumes tabbing from the top
  // of a document whose sheet just vanished, with nothing announcing either event.
  useEffect(() => {
    if (!open) return
    const opener = document.activeElement
    returnToRef.current = opener instanceof HTMLElement ? opener : null
    closeRef.current?.focus()
    return () => {
      const back = returnToRef.current
      returnToRef.current = null
      // The opener can be gone by the time the sheet closes — a sheet opened from
      // a row that the sheet's own action deleted. Focusing a detached node does
      // not throw; it silently drops focus to <body>, which is the bug this is
      // meant to fix, so the check is on isConnected rather than on null.
      if (back && back.isConnected) back.focus()
    }
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        // Anchored to the viewport BOTTOM: under body zoom:1.15, h-[100svh] can render
        // taller than the visible viewport on iOS. Bottom-anchoring spills the overshoot
        // off the top (harmless) and keeps the panel's pinned footer at the real bottom.
        <div className="fixed bottom-0 left-0 right-0 z-[60] h-[100svh]">
          <motion.div
            className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            className="absolute inset-x-0 bottom-0 bg-paper rounded-t-xl flex flex-col"
            // Single source of safe-area truth for all sheets: the panel insets its own
            // bottom by the home-indicator/browser zone so a pinned footer (or the last
            // scrolled item in footer-less sheets) clears it. Consumers must NOT add
            // env(safe-area-inset-bottom) again in their footer — that double-compensates.
            style={{ maxHeight, paddingBottom: 'env(safe-area-inset-bottom)' }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* The close control belongs to the SHEET, not to each consumer. Of the five
                consumers, two had hand-rolled one into their own header and three had
                none at all — so whether a sheet could be dismissed by anything other
                than a gesture depended on which sheet you opened. This is that button,
                with the same label and classes the two hand-rolled ones used, so a test
                querying aria-label="Close" keeps finding it.

                It is a ROW rather than an absolutely-positioned corner button, and that
                is the whole trick for the header-less panels: quotes/page.tsx opens
                straight into 26px Cormorant at pt-[24px], so anything overlaying the
                corner would sit on the first line of the quote. A flex-shrink-0 row
                pushes every consumer's content clear without the consumer knowing, and
                without a prop telling the sheet which kind of panel it is. */}
            <div className="flex-shrink-0 flex justify-end pr-[6px] pt-[6px]">
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="p-2 font-lora text-[22px] text-sepia leading-none"
              >
                ×
              </button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
