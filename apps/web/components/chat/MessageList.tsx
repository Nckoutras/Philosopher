'use client'

import { useState, useEffect } from 'react'
import { api, type Message } from '@/lib/api'
import { useStore } from '@/lib/store'
import MessageBubble from './MessageBubble'
import QuickActionsRow from './QuickActionsRow'

interface Props {
  messages: Message[]
  onSaveLine: (messageId: string) => void
  onUpgradeConfirm: () => void
  onBringAnotherMind: () => void
  onGoDeeper: () => void
}

export default function MessageList({ messages, onSaveLine, onUpgradeConfirm, onBringAnotherMind, onGoDeeper }: Props) {
  const savedMessageIds = useStore((s) => s.savedMessageIds)
  const activePersonaName = useStore((s) => s.activePersonaName)

  const visible = messages.filter(
    (m): m is Message & { role: 'user' | 'assistant' } =>
      m.role === 'user' || m.role === 'assistant',
  )

  const [personaNames, setPersonaNames] = useState<Record<string, string>>({})
  const hasBroughtIn = visible.some((m) => m.role === 'assistant' && !!m.persona_slug)
  useEffect(() => {
    if (!hasBroughtIn || Object.keys(personaNames).length > 0) return
    api.getPersonas()
      .then((ps) => setPersonaNames(Object.fromEntries(ps.map((p) => [p.slug, p.name]))))
      .catch(() => {})
  }, [hasBroughtIn, personaNames])

  return (
    <div className="flex flex-col gap-3">
      {visible.map((msg) => {
        const slug = msg.persona_slug
        const broughtIn = msg.role === 'assistant' && !!slug
        const broughtInName = broughtIn ? (msg.persona_name ?? (slug ? personaNames[slug] : undefined)) : undefined

        return (
          <div key={msg.id}>
            {broughtIn && broughtInName && (
              <p className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em] mb-1">
                {broughtInName} · brought in
              </p>
            )}
            <MessageBubble
              id={msg.id}
              role={msg.role}
              content={msg.content}
              saved={savedMessageIds.has(msg.id)}
              broughtIn={broughtIn}
            />
            {msg.role === 'assistant' && (
              <QuickActionsRow
                messageId={msg.id}
                saved={savedMessageIds.has(msg.id)}
                onSave={() => onSaveLine(msg.id)}
                onUpgradeConfirm={onUpgradeConfirm}
                onBringAnotherMind={onBringAnotherMind}
                onGoDeeper={onGoDeeper}
              />
            )}
            {broughtIn && activePersonaName && (
              <p className="font-lora text-[10px] text-sepia uppercase tracking-[0.18em] text-center my-2">
                Continuing with {activePersonaName}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
