'use client'

import { clsx } from 'clsx'
import type { Message, Persona } from '@/lib/api'

interface Props {
  message: Message
  persona: Persona
  isStreaming?: boolean
}

export function MessageBubble({ message, persona, isStreaming }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className={clsx(
            'max-w-[72%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm',
            'bg-[var(--bg-surface)] border border-[var(--border)]',
            'text-[var(--text-primary)]',
          )}
        >
          <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
        </div>
      </div>
    )
  }

  // Assistant / persona message
  return (
    <div className="flex gap-3 max-w-[88%]">
      {/* Persona avatar */}
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-sm flex-shrink-0 mt-1"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}
        title={persona.name}
      >
        {persona.avatar_emoji ?? '🏛️'}
      </div>

      <div className="flex-1">
        {/* Safety override badge */}
        {message.persona_override && (
          <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
            style={{ background: 'rgba(201,169,110,0.12)', color: 'var(--gold)', border: '1px solid rgba(201,169,110,0.25)' }}
          >
            <span>⚠</span> A gentle pause
          </div>
        )}

        <div
          className={clsx(
            'prose-philosopher',
            isStreaming && 'streaming-cursor',
          )}
        >
          {/* Render with paragraph breaks */}
          {message.content.split('\n\n').map((para, i) => (
            <p key={i} className={i > 0 ? 'mt-4' : ''}>
              {para.split('\n').map((line, j) => (
                <span key={j}>
                  {j > 0 && <br />}
                  {line}
                </span>
              ))}
            </p>
          ))}
        </div>
      </div>
    </div>
  )
}
