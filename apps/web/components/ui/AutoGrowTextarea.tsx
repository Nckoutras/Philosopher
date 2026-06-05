'use client'

import { useLayoutEffect, useRef } from 'react'

interface Props {
  value: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  disabled?: boolean
  minRows?: number
  maxHeight?: number
  className?: string
  ariaLabel?: string
}

export default function AutoGrowTextarea({
  value,
  onChange,
  onKeyDown,
  placeholder,
  disabled,
  minRows = 1,
  maxHeight = 120,
  className,
  ariaLabel,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    const h = Math.min(el.scrollHeight, maxHeight)
    el.style.height = h + 'px'
    el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
  }, [value, maxHeight])

  return (
    <textarea
      ref={ref}
      rows={minRows}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      disabled={disabled}
      placeholder={placeholder}
      aria-label={ariaLabel}
      className={`resize-none ${className ?? ''}`}
    />
  )
}
