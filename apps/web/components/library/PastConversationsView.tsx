'use client'

import { useState, useRef, useEffect } from 'react'
import { Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Conversation } from '@/lib/api'
import ConversationCard from './ConversationCard'
import EmptyConversationHistory from './EmptyConversationHistory'
import SwipeableRow from '@/components/ui/SwipeableRow'

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
  const [pendingDeletes, setPendingDeletes] = useState<Set<string>>(new Set())
  const deleteTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const [isFirstLibraryRender] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return !sessionStorage.getItem('swipe_hint_seen_library')
  })

  useEffect(() => {
    if (isFirstLibraryRender) {
      sessionStorage.setItem('swipe_hint_seen_library', '1')
    }
  }, [isFirstLibraryRender])

  useEffect(() => {
    const timers = deleteTimersRef.current
    return () => {
      timers.forEach((t) => clearTimeout(t))
      timers.clear()
    }
  }, [])

  function handleDelete(conversationId: string) {
    setPendingDeletes((prev) => new Set(prev).add(conversationId))

    const timer = setTimeout(async () => {
      try {
        await api.deleteConversation(conversationId)
        useStore.getState().setConversations(
          useStore.getState().conversations.filter((c) => c.id !== conversationId),
        )
      } catch {
        setPendingDeletes((prev) => {
          const next = new Set(prev)
          next.delete(conversationId)
          return next
        })
        toast.error('Could not delete. Try again.')
      } finally {
        deleteTimersRef.current.delete(conversationId)
      }
    }, 5000)
    deleteTimersRef.current.set(conversationId, timer)

    toast.custom(
      (t) => (
        <div className="bg-ink text-vellum font-lora text-[13px] rounded-sm px-[16px] py-[12px] flex items-center gap-[16px]">
          <span>Deleted conversation</span>
          <button
            type="button"
            onClick={() => {
              const pending = deleteTimersRef.current.get(conversationId)
              if (pending) {
                clearTimeout(pending)
                deleteTimersRef.current.delete(conversationId)
              }
              setPendingDeletes((prev) => {
                const next = new Set(prev)
                next.delete(conversationId)
                return next
              })
              toast.dismiss(t.id)
            }}
            className="font-cormorant text-[15px] font-medium underline underline-offset-2 decoration-[0.5px]"
          >
            Undo
          </button>
        </div>
      ),
      { duration: 5000 },
    )
  }

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

  const visibleConversations = conversations.filter((c) => !pendingDeletes.has(c.id))

  const trimmed = q.trim()
  const filtered = trimmed
    ? visibleConversations.filter(
        (c) =>
          (c.title ?? '').toLowerCase().includes(trimmed.toLowerCase()) ||
          c.persona.name.toLowerCase().includes(trimmed.toLowerCase()),
      )
    : visibleConversations

  const thisWeek = filtered.filter((c) => isThisWeek(c.last_message_at))
  const earlier = filtered.filter((c) => !isThisWeek(c.last_message_at))
  const hintId = isFirstLibraryRender ? (thisWeek[0]?.id ?? earlier[0]?.id ?? null) : null

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

      {visibleConversations.length === 0 ? (
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
            <Group
              label="This week"
              conversations={thisWeek}
              portraitUrlsBySlug={portraitUrlsBySlug}
              onDelete={handleDelete}
              hintId={hintId}
            />
          )}
          {earlier.length > 0 && (
            <Group
              label="Earlier"
              conversations={earlier}
              portraitUrlsBySlug={portraitUrlsBySlug}
              onDelete={handleDelete}
              hintId={hintId}
            />
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
  onDelete,
  hintId,
}: {
  label: string
  conversations: Conversation[]
  portraitUrlsBySlug: Record<string, string>
  onDelete: (id: string) => void
  hintId: string | null
}) {
  return (
    <div>
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-2">{label}</p>
      <div className="flex flex-col gap-2">
        {conversations.map((conv) => (
          <SwipeableRow
            key={conv.id}
            onDelete={() => onDelete(conv.id)}
            showHint={conv.id === hintId}
          >
            <ConversationCard
              conversation={conv}
              portraitUrl={portraitUrlsBySlug[conv.persona.slug]}
            />
          </SwipeableRow>
        ))}
      </div>
    </div>
  )
}
