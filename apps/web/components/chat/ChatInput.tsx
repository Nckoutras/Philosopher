'use client'

import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { SendHorizontal } from 'lucide-react'

// ── ChatInput ────────────────────────────────────────────────────────────────

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSend: (v: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ value, onChange, onSend, disabled, placeholder }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-resize
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend(value)
    }
  }

  return (
    <div className="px-4 pb-6 pt-2">
      <div
        className="flex items-end gap-2 rounded-2xl px-4 py-3"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-strong)' }}
      >
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder ?? 'Write your thought...'}
          className={clsx(
            'flex-1 resize-none bg-transparent text-sm outline-none',
            'text-[var(--text-primary)] placeholder:text-[var(--text-muted)]',
            'leading-relaxed min-h-[24px]',
          )}
        />
        <button
          onClick={() => onSend(value)}
          disabled={disabled || !value.trim()}
          className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center',
            'transition-all duration-150',
            value.trim() && !disabled
              ? 'bg-[var(--gold)] text-[#0f0e0d] hover:opacity-90'
              : 'text-[var(--text-muted)] opacity-40 cursor-not-allowed',
          )}
        >
          <SendHorizontal size={15} />
        </button>
      </div>
      <p className="mt-1.5 text-center text-xs text-[var(--text-muted)]">
        Shift+Enter for new line
      </p>
    </div>
  )
}
