'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'

// Shared "topic → start a conversation" wiring used by both the Home first-day
// button and the /app/discuss route. Holds the pending topic + the persona
// picker open-state, and starts the conversation once a mind is chosen. This is
// the single source of truth for the Quick-start path that TodaysTopicCard's
// onReflect feeds into — do not fork it per-page.
export function useTopicConversation() {
  const router = useRouter()
  const [pendingTopic, setPendingTopic] = useState('')
  const [topicPickerOpen, setTopicPickerOpen] = useState(false)

  // Seed a topic (may be empty) and open the persona picker.
  function startWithTopic(topicText: string) {
    setPendingTopic(topicText)
    setTopicPickerOpen(true)
  }

  async function handlePersonaSelected(personaSlug: string) {
    const hasTopic = pendingTopic.trim().length > 0
    try {
      const conv = await api.createConversation(personaSlug, undefined, hasTopic)
      if (hasTopic) localStorage.setItem(`today_topic_draft_${conv.id}`, pendingTopic)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not start conversation. Try again.')
      setTopicPickerOpen(true)
    }
  }

  return {
    pendingTopic,
    setPendingTopic,
    topicPickerOpen,
    setTopicPickerOpen,
    startWithTopic,
    handlePersonaSelected,
  }
}
