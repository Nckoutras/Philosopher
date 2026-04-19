'use client'

import { useRouter } from 'next/navigation'
import { ArrowLeft, Brain } from 'lucide-react'
import type { Conversation } from '@/lib/api'

interface Props {
  conversation: Conversation
}

export function ConversationHeader({ conversation }: Props) {
  const router = useRouter()
  const { persona } = conversation

  return (
    <header
      className="flex items-center justify-between px-5 py-4"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/app/dashboard')}
          className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-surface)]"
          style={{ color: 'var(--text-muted)' }}
        >
          <ArrowLeft size={16} />
        </button>

        <div className="flex items-center gap-2.5">
          <span className="text-xl">{persona.avatar_emoji ?? '🏛️'}</span>
          <div>
            <h1 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              {persona.name}
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {persona.era} · {persona.tradition}
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={() => router.push('/app/memory')}
        className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-surface)]"
        style={{ color: 'var(--text-muted)' }}
        title="Your memory"
      >
        <Brain size={16} />
      </button>
    </header>
  )
}
