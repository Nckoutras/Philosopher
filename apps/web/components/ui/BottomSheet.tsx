'use client'

import { useEffect, ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface Props {
  open: boolean
  onClose: () => void
  children: ReactNode
  maxHeight?: string
}

export default function BottomSheet({ open, onClose, children, maxHeight = '75svh' }: Props) {
  // Close on Escape. (Replaces the previous browser-history dismissal mechanism,
  // which collided with Next.js App Router client navigation and froze the tabs.)
  useEffect(() => {
    if (!open) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

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
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
