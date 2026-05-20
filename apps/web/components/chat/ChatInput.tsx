'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'
import { useStore } from '@/lib/store'

interface Props {
  send: (content: string) => void
  placeholder?: string
  initialValue?: string
}

export default function ChatInput({ send, placeholder = 'Write your thought…', initialValue }: Props) {
  const [value, setValue] = useState(initialValue ?? '')
  const isStreaming = useStore((s) => s.isStreaming)
  const activeConversationId = useStore((s) => s.activeConversationId)
  const disabled = isStreaming || activeConversationId === null

  const handleSend = () => {
    const content = value.trim()
    if (!content || disabled) return
    send(content)
    setValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-edge bg-vellum px-4 py-3 pb-safe flex items-end gap-2">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="flex-1 resize-none bg-white rounded-sm px-3 py-2 font-lora text-base text-ink placeholder:text-sepia focus:outline-none disabled:opacity-50"
        style={{ maxHeight: '120px' }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send"
        className="h-9 w-9 flex items-center justify-center bg-ink text-vellum rounded-sm font-cormorant text-[16px] disabled:opacity-40 transition-opacity flex-shrink-0"
      >
        {isStreaming ? '…' : <Send size={16} strokeWidth={1.5} />}
      </button>
    </div>
  )
}
