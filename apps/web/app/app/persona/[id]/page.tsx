'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ConversationHeader } from '@/components/chat/ConversationHeader'

export default function PersonaConversationPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { setActiveConversation, setMessages } = useStore()

  // Load conversation messages
  const { data: messages, isLoading, error } = useQuery({
    queryKey: ['messages', id],
    queryFn: () => api.getMessages(id),
    enabled: !!id,
  })

  useEffect(() => {
    if (!id) return
    setActiveConversation(id)
  }, [id, setActiveConversation])

  useEffect(() => {
    if (messages) setMessages(messages)
  }, [messages, setMessages])

  useEffect(() => {
    if (error) router.replace('/app/dashboard')
  }, [error, router])

  // Get persona info from first message's conversation
  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.getConversations(),
  })

  const conversation = conversations.find((c) => c.id === id)

  if (isLoading || !conversation) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-[var(--gold)] animate-pulse" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <ConversationHeader conversation={conversation} />
      <div className="flex-1 overflow-hidden">
        <ChatWindow persona={conversation.persona} />
      </div>
    </div>
  )
}
