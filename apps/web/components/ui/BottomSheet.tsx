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
  useEffect(() => {
    if (!open) return
    window.history.pushState({ modal: 'bottom-sheet' }, '')
    return () => {
      if (window.history.state?.modal === 'bottom-sheet') {
        window.history.back()
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function handlePopState() { onClose() }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
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
