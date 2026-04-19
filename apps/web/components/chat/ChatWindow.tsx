'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import { SafetyBanner } from './SafetyBanner'
import type { Persona } from '@/lib/api'

interface Props {
  persona: Persona
}

export function ChatWindow({ persona }: Props) {
  const { messages, isStreaming, streamingContent, safetyActive } = useStore()
  const { send } = useStream()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [inputValue, setInputValue] = useState('')

  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, streamingContent])

  const handleSend = async (text: string) => {
    if (!text.trim() || isStreaming) return
    setInputValue('')
    await send(text)
  }

  return (
    <div className="flex flex-col h-full">

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
            >
              <MessageBubble message={msg} persona={persona} />
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming assistant message */}
        {isStreaming && streamingContent && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <MessageBubble
              message={{
                id: 'streaming',
                role: 'assistant',
                content: streamingContent,
                safety_level: 'none',
                persona_override: false,
                created_at: new Date().toISOString(),
              }}
              persona={persona}
              isStreaming
            />
          </motion.div>
        )}

        {/* Typing indicator — before first chunk arrives */}
        {isStreaming && !streamingContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1 pl-1"
          >
            {[0, 0.15, 0.3].map((delay, i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[var(--gold)]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, delay, repeat: Infinity }}
              />
            ))}
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Safety banner */}
      <AnimatePresence>
        {safetyActive && <SafetyBanner />}
      </AnimatePresence>

      {/* Input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        disabled={isStreaming}
        placeholder={`Speak to ${persona.name}...`}
      />
    </div>
  )
}
