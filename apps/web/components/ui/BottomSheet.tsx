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
        // Anchored top/left/right (not inset-0) at full 100svh. Modern engines already
        // adjust svh viewport units under the global `body { zoom: 1.15 }` (globals.css),
        // so the earlier manual `/1.15` double-compensated and pulled the bottom edge ~13%
        // short of the visible viewport. Full 100svh now lands the bottom edge correctly.
        <div className="fixed top-0 left-0 right-0 z-[60] h-[100svh]">
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
            style={{ maxHeight }}
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
