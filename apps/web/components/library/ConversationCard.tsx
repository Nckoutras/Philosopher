'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { ChevronRight, Sparkle } from 'lucide-react'
import type { Conversation } from '@/lib/api'
import { useStore } from '@/lib/store'

function formatDatePart(dateString: string | null): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const dateDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  if (dateDay.getTime() === today.getTime()) return 'Today'
  if (dateDay.getTime() === yesterday.getTime()) return 'Yesterday'
  const diffDays = Math.floor((today.getTime() - dateDay.getTime()) / 86400000)
  if (diffDays < 7) return date.toLocaleDateString('en', { weekday: 'long' })
  return date.toLocaleDateString('en', { month: 'short', day: 'numeric' })
}

function formatTime(dateString: string | null): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleTimeString('en', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function buildMetaLine(conv: Conversation): string {
  const parts: string[] = []
  const datePart = formatDatePart(conv.last_message_at)
  if (datePart) parts.push(datePart)
  const timePart = formatTime(conv.last_message_at)
  if (timePart) parts.push(timePart)
  const msgCount = conv.message_count
  if (msgCount > 0) parts.push(`${msgCount} message${msgCount === 1 ? '' : 's'}`)
  return parts.join(' · ')
}

interface Props {
  conversation: Conversation
  portraitUrl?: string
}

export default function ConversationCard({ conversation, portraitUrl }: Props) {
  const router = useRouter()
  const { persona, title, last_message_snippet } = conversation

  const subject = title ?? last_message_snippet ?? ''
  const metaLine = buildMetaLine(conversation)
  const avatarUrl = portraitUrl || persona.portrait_url || ''

  const activeInsights = useStore((s) => s.activeInsights)
  const seenInsightIds = useStore((s) => s.seenInsightIds)
  const hasUnseenInsight = activeInsights.some(
    (i) => i.conversation_id === conversation.id && !seenInsightIds.includes(i.id),
  )

  return (
    <button
      type="button"
      onClick={() => router.push(`/app/chat/conv/${conversation.id}`)}
      className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md p-4 flex items-center gap-4 transition-colors active:bg-linen"
      aria-label={`Open conversation with ${persona.name}`}
    >
      {/* 36×36 persona avatar */}
      <div className="relative flex-shrink-0">
        <div className="w-14 h-14 rounded-full overflow-hidden bg-linen flex items-center justify-center">
          {avatarUrl ? (
            <Image
              src={avatarUrl}
              alt={persona.name}
              width={56}
              height={56}
              className="w-full h-full object-cover object-top"
            />
          ) : (
            <span className="font-cormorant text-[17px] font-medium text-charcoal">
              {persona.name.charAt(0)}
            </span>
          )}
        </div>
        {hasUnseenInsight && (
          <Sparkle size={14} strokeWidth={1.5} className="absolute -top-[3px] -right-[3px] text-bronze fill-bronze drop-shadow-[0_0_6px_rgba(184,153,104,0.9)]" aria-hidden="true" />
        )}
      </div>

      {/* Middle content */}
      <div className="flex-1 min-w-0">
        <p className="font-cormorant text-[20px] font-medium text-ink leading-tight truncate">
          {persona.name}
        </p>
        <p className="font-lora text-[13px] text-charcoal leading-tight mt-[2px]">
          {metaLine}
        </p>
        {subject && (
          <p className={`font-lora text-[13px] text-charcoal leading-tight mt-[3px] truncate ${title ? 'font-semibold' : 'italic'}`}>
            {subject}
          </p>
        )}
      </div>

      {/* Chevron */}
      <ChevronRight size={16} strokeWidth={1.5} className="text-sepia flex-shrink-0" />
    </button>
  )
}
