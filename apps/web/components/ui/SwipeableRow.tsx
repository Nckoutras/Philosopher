'use client'

import { ReactNode, useEffect, useRef } from 'react'
import { motion, useAnimation } from 'framer-motion'
import type { PanInfo } from 'framer-motion'

const REVEAL_THRESHOLD = -80
const REVEALED_X = -80
const spring = { type: 'spring' as const, stiffness: 400, damping: 30 }

interface Props {
  children: ReactNode
  onDeleteRequest: () => void
  showHint?: boolean
  isRevealed: boolean
  onReveal: () => void
  onCollapse: () => void
}

export default function SwipeableRow({
  children,
  onDeleteRequest,
  showHint = false,
  isRevealed,
  onReveal,
  onCollapse,
}: Props) {
  const controls = useAnimation()
  const containerRef = useRef<HTMLDivElement>(null)
  const hintShownRef = useRef(false)
  const isMountedRef = useRef(false)

  // Hint: animate to full reveal and bounce back on first session render
  useEffect(() => {
    if (showHint && !hintShownRef.current) {
      hintShownRef.current = true
      const run = async () => {
        await controls.start({ x: REVEALED_X, transition: { duration: 0.45, ease: 'easeOut' } })
        await controls.start({ x: 0, transition: { duration: 0.55, ease: 'easeInOut' } })
      }
      run()
    }
  }, [showHint, controls])

  // Sync animation when parent collapses this row (e.g. sibling swipe, outside tap)
  useEffect(() => {
    if (!isMountedRef.current) {
      isMountedRef.current = true
      return
    }
    controls.start({ x: isRevealed ? REVEALED_X : 0, transition: spring })
  }, [isRevealed, controls])

  // Collapse via outside tap while revealed
  useEffect(() => {
    if (!isRevealed) return
    function handlePointerDown(e: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onCollapse()
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [isRevealed, onCollapse])

  function handleDragEnd(_: PointerEvent, info: PanInfo) {
    if (isRevealed) {
      // Rightward swipe > 5px collapses; effect drives animation to x=0
      if (info.offset.x > 5) {
        onCollapse()
      } else {
        controls.start({ x: REVEALED_X, transition: spring })
      }
    } else {
      // Leftward swipe past threshold reveals; effect drives animation to x=REVEALED_X
      if (info.offset.x < REVEAL_THRESHOLD) {
        onReveal()
      } else {
        controls.start({ x: 0, transition: spring })
      }
    }
  }

  return (
    <div ref={containerRef} className="relative overflow-hidden">
      <div className="absolute inset-0 bg-danger flex items-center justify-end">
        <button
          type="button"
          onClick={onDeleteRequest}
          tabIndex={isRevealed ? 0 : -1}
          aria-hidden={!isRevealed}
          className="w-[80px] h-full flex items-center justify-center font-lora text-[13px] text-vellum"
        >
          Delete
        </button>
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
