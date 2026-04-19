'use client'

import { motion } from 'framer-motion'

export function SafetyBanner() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      className="mx-4 mb-2 px-4 py-3 rounded-xl text-sm"
      style={{
        background: 'rgba(201,169,110,0.08)',
        border: '1px solid rgba(201,169,110,0.2)',
        color: 'var(--gold)',
      }}
    >
      <p className="font-medium mb-0.5">A moment of care</p>
      <p className="text-xs opacity-80" style={{ color: 'var(--text-secondary)' }}>
        Our companion has paused to ensure you have access to real support.
      </p>
    </motion.div>
  )
}
