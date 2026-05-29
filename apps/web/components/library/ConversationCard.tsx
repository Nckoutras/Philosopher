'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import type { Conversation } from '@/lib/api'

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

  const snippet = last_message_snippet ?? title ?? ''
  const metaLine = buildMetaLine(conversation)
  const avatarUrl = portraitUrl || persona.portrait_url || ''

  return (
    <button
      type="button"
      onClick={() => router.push(`/app/chat/conv/${conversation.id}`)}
      className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md p-4 flex items-center gap-4 transition-colors active:bg-linen"
      aria-label={`Open conversation with ${persona.name}`}
    >
      {/* 36×36 persona avatar */}
      <div className="w-14 h-14 flex-shrink-0 rounded-full overflow-hidden bg-linen flex items-center justify-center">
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

      {/* Middle content */}
      <div className="flex-1 min-w-0">
        <p className="font-cormorant text-[17px] font-medium text-ink leading-tight truncate">
          {persona.name}
        </p>
        <p className="font-lora text-[12px] text-sepia leading-tight mt-[2px]">
          {metaLine}
        </p>
        {snippet && (
          <p className="font-lora text-[13px] text-charcoal italic leading-tight mt-[3px] truncate">
            {snippet}
          </p>
        )}
      </div>

      {/* Chevron */}
      <ChevronRight size={16} strokeWidth={1.5} className="text-sepia flex-shrink-0" />
    </button>
  )
}
