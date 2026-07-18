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
  // Sticky guest: make a brought-in guest the active mind for subsequent turns.
  // Optional — only the canonical /conv/[id] surface supports stickiness; the
  // fresh-start /chat/[slug] page omits it (its identity keys on the home slug),
  // so the chip is hidden there and another-mind stays one-shot.
  onContinueWithGuest?: (slug: string, name: string) => void
  // Named one-tap ritual door (D1a): the insight type surfaces as a door chip on the
  // LAST assistant message only. onInsightDoor routes via the existing door;
  // onInsightDismiss is the 5s-undo dismiss. No in-chat card anymore.
  insightType?: string | null
  onInsightDoor?: () => void
  onInsightDismiss?: () => void
  onTakeToCouncil?: () => void
}

export default function MessageList({ messages, onSaveLine, onUpgradeConfirm, onBringAnotherMind, onGoDeeper, onContinueWithGuest, insightType, onInsightDoor, onInsightDismiss, onTakeToCouncil }: Props) {
  const savedMessageIds = useStore((s) => s.savedMessageIds)
  const activePersonaSlug = useStore((s) => s.activePersonaSlug)

  const visible = messages.filter(
    (m): m is Message & { role: 'user' | 'assistant' } =>
      m.role === 'user' || m.role === 'assistant',
  )

  // The insight door chip anchors to the most recent assistant message.
  const lastAssistantId = [...visible].reverse().find((m) => m.role === 'assistant')?.id ?? null

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
                insightType={msg.id === lastAssistantId ? (insightType ?? null) : null}
                onInsightDoor={onInsightDoor}
                onInsightDismiss={onInsightDismiss}
                showCouncilChip={msg.id === lastAssistantId}
                onTakeToCouncil={onTakeToCouncil}
                continueWithName={onContinueWithGuest && broughtIn && slug && slug !== activePersonaSlug ? (broughtInName ?? null) : null}
                onContinueWith={onContinueWithGuest && broughtIn && slug ? () => onContinueWithGuest(slug, broughtInName ?? '') : undefined}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
