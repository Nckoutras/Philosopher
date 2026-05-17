'use client'

import type { Conversation } from '@/lib/api'
import ConversationCard from './ConversationCard'
import EmptyConversationHistory from './EmptyConversationHistory'

function isThisWeek(dateString: string | null): boolean {
  if (!dateString) return false
  const diffMs = Date.now() - new Date(dateString).getTime()
  return diffMs < 7 * 24 * 60 * 60 * 1000
}

interface Props {
  conversations: Conversation[]
  portraitUrlsBySlug: Record<string, string>
  loading: boolean
  error: Error | null
  onRetry: () => void
}

export default function ConversationList({ conversations, portraitUrlsBySlug, loading, error, onRetry }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-7 text-center">
        <p className="font-lora text-[13px] text-charcoal mb-4">
          Couldn't load conversations.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="font-lora text-[13px] text-ink underline underline-offset-2 decoration-[0.5px]"
        >
          Try again
        </button>
      </div>
    )
  }

  if (conversations.length === 0) {
    return <EmptyConversationHistory />
  }

  const thisWeek = conversations.filter((c) => isThisWeek(c.last_message_at))
  const earlier = conversations.filter((c) => !isThisWeek(c.last_message_at))

  return (
    <div className="px-4 py-3 flex flex-col gap-4">
      {thisWeek.length > 0 && (
        <Group label="This week" conversations={thisWeek} portraitUrlsBySlug={portraitUrlsBySlug} />
      )}
      {earlier.length > 0 && (
        <Group label="Earlier" conversations={earlier} portraitUrlsBySlug={portraitUrlsBySlug} />
      )}
    </div>
  )
}

function Group({
  label,
  conversations,
  portraitUrlsBySlug,
}: {
  label: string
  conversations: Conversation[]
  portraitUrlsBySlug: Record<string, string>
}) {
  return (
    <div>
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-2">
        {label}
      </p>
      <div className="flex flex-col gap-2">
        {conversations.map((conv) => (
          <ConversationCard
            key={conv.id}
            conversation={conv}
            portraitUrl={portraitUrlsBySlug[conv.persona.slug]}
          />
        ))}
      </div>
    </div>
  )
}
