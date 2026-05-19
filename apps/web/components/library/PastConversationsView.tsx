'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'
import type { Conversation } from '@/lib/api'
import ConversationCard from './ConversationCard'
import EmptyConversationHistory from './EmptyConversationHistory'

function isThisWeek(dateString: string | null): boolean {
  if (!dateString) return false
  return Date.now() - new Date(dateString).getTime() < 7 * 24 * 60 * 60 * 1000
}

interface Props {
  conversations: Conversation[]
  portraitUrlsBySlug: Record<string, string>
  loading: boolean
  error: Error | null
  onRetry: () => void
}

export default function PastConversationsView({
  conversations,
  portraitUrlsBySlug,
  loading,
  error,
  onRetry,
}: Props) {
  const [q, setQ] = useState('')

  if (loading && conversations.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-7 text-center">
        <p className="font-lora text-[13px] text-charcoal mb-4">Couldn&apos;t load conversations.</p>
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

  const trimmed = q.trim()
  const filtered = trimmed
    ? conversations.filter(
        (c) =>
          (c.title ?? '').toLowerCase().includes(trimmed.toLowerCase()) ||
          c.persona.name.toLowerCase().includes(trimmed.toLowerCase()),
      )
    : conversations

  const thisWeek = filtered.filter((c) => isThisWeek(c.last_message_at))
  const earlier = filtered.filter((c) => !isThisWeek(c.last_message_at))

  return (
    <div className="flex flex-col">
      {/* Search bar */}
      <div className="relative px-4 pb-3">
        <Search
          size={14}
          className="absolute left-7 top-1/2 -translate-y-1/2 text-sepia pointer-events-none"
        />
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search conversations"
          className="w-full pl-8 pr-4 py-[8px] bg-linen border border-[0.5px] border-edge
                     rounded-[4px] font-lora text-[13px] text-ink placeholder:text-sepia outline-none"
        />
      </div>

      {conversations.length === 0 ? (
        <EmptyConversationHistory />
      ) : filtered.length === 0 ? (
        <div className="flex items-center justify-center py-12 px-7 text-center">
          <p className="font-lora text-[13px] text-charcoal">
            No conversations matching &ldquo;{q}&rdquo;.
          </p>
        </div>
      ) : (
        <div className="px-4 py-3 flex flex-col gap-4 pb-[80px]">
          {thisWeek.length > 0 && (
            <Group label="This week" conversations={thisWeek} portraitUrlsBySlug={portraitUrlsBySlug} />
          )}
          {earlier.length > 0 && (
            <Group label="Earlier" conversations={earlier} portraitUrlsBySlug={portraitUrlsBySlug} />
          )}
        </div>
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
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-2">{label}</p>
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
