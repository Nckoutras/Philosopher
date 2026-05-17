'use client'

import type { Message } from '@/lib/api'
import { useStore } from '@/lib/store'
import MessageBubble from './MessageBubble'
import QuickActionsRow from './QuickActionsRow'

interface Props {
  messages: Message[]
  onSaveLine: (messageId: string) => void
  onUpgradeConfirm: () => void
}

export default function MessageList({ messages, onSaveLine, onUpgradeConfirm }: Props) {
  const savedMessageIds = useStore((s) => s.savedMessageIds)

  const visible = messages.filter(
    (m): m is Message & { role: 'user' | 'assistant' } =>
      m.role === 'user' || m.role === 'assistant',
  )

  return (
    <div className="flex flex-col gap-3">
      {visible.map((msg) => (
        <div key={msg.id}>
          <MessageBubble
            id={msg.id}
            role={msg.role}
            content={msg.content}
            saved={savedMessageIds.has(msg.id)}
          />
          {msg.role === 'assistant' && (
            <QuickActionsRow
              messageId={msg.id}
              saved={savedMessageIds.has(msg.id)}
              onSave={() => onSaveLine(msg.id)}
              onUpgradeConfirm={onUpgradeConfirm}
            />
          )}
        </div>
      ))}
    </div>
  )
}
