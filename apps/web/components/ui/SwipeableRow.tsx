'use client'

import { ReactNode, useEffect, useRef } from 'react'
import { motion, useAnimation } from 'framer-motion'
import type { PanInfo } from 'framer-motion'
import { Trash2 } from 'lucide-react'

interface Props {
  children: ReactNode
  onDelete: () => void
  showHint?: boolean
}

const DELETE_THRESHOLD = -80

export default function SwipeableRow({ children, onDelete, showHint = false }: Props) {
  const controls = useAnimation()
  const hintShownRef = useRef(false)

  useEffect(() => {
    if (showHint && !hintShownRef.current) {
      hintShownRef.current = true
      const sequence = async () => {
        await controls.start({ x: -28, transition: { duration: 0.45, ease: 'easeOut' } })
        await controls.start({ x: 0, transition: { duration: 0.55, ease: 'easeInOut' } })
      }
      sequence()
    }
  }, [showHint, controls])

  async function handleDragEnd(_: PointerEvent, info: PanInfo) {
    if (info.offset.x < DELETE_THRESHOLD) {
      await controls.start({ x: -500, opacity: 0, transition: { duration: 0.2 } })
      onDelete()
    } else {
      controls.start({ x: 0, transition: { type: 'spring', stiffness: 400, damping: 30 } })
    }
  }

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-0 bg-safety flex items-center justify-end pr-4">
        <Trash2 size={20} className="text-vellum" strokeWidth={1.5} />
      </div>
      <motion.div
        drag="x"
        dragConstraints={{ left: -120, right: 0 }}
        dragElastic={0.15}
        animate={controls}
        onDragEnd={handleDragEnd}
        className="relative bg-vellum"
      >
        {children}
      </motion.div>
    </div>
  )
}
