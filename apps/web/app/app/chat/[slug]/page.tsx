'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { api } from '@/lib/api'
import ChatHeader from '@/components/chat/ChatHeader'
import OpeningInvocation from '@/components/chat/OpeningInvocation'
import MessageList from '@/components/chat/MessageList'
import StreamingBubble from '@/components/chat/StreamingBubble'
import ErrorMessage from '@/components/chat/ErrorMessage'
import ChatInput from '@/components/chat/ChatInput'

export default function ChatPage() {
  const params = useParams<{ slug: string }>()
  const router = useRouter()

  const token = useStore((s) => s.token)
  const messages = useStore((s) => s.messages)
  const streamingContent = useStore((s) => s.streamingContent)
  const activeConversationId = useStore((s) => s.activeConversationId)
  const activePersonaSlug = useStore((s) => s.activePersonaSlug)
  const personaName = useStore((s) => s.activePersonaName) ?? ''
  const portraitUrl = useStore((s) => s.activePersonaPortraitUrl) ?? ''
  const openingInvocation = useStore((s) => s.activePersonaOpeningInvocation)
  const setActiveConversation = useStore((s) => s.setActiveConversation)
  const clearActiveConversation = useStore((s) => s.clearActiveConversation)

  const [createError, setCreateError] = useState<string | null>(null)
  const { send } = useStream()

  // Scroll-to-bottom sentinel ref handled via inline ref callback on the sentinel div
  useEffect(() => {
    const sentinel = document.getElementById('chat-scroll-sentinel')
    sentinel?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Initialise conversation on mount (or when slug/token changes)
  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }

    const state = useStore.getState()
    if (
      state.activeConversationId !== null &&
      state.activePersonaSlug === params.slug
    ) {
      return
    }

    let cancelled = false
    setCreateError(null)

    async function init() {
      try {
        // Fetch conversation + full persona data in parallel (portrait_url not in create response)
        const [conv, personas] = await Promise.all([
          api.createConversation(params.slug),
          api.getPersonas(),
        ])
        if (cancelled) return
        const personaFull = personas.find((p) => p.slug === params.slug)
        setActiveConversation(
          conv.id,
          params.slug,
          conv.persona.name,
          personaFull?.portrait_url ?? '',
          conv.persona.opening_invocation,
        )
      } catch (err) {
        if (cancelled) return
        setCreateError(err instanceof Error ? err.message : 'Could not start conversation')
      }
    }

    init()

    return () => {
      cancelled = true
    }
  }, [params.slug, token, router, setActiveConversation])

  // Clear conversation state on unmount
  useEffect(() => {
    return () => {
      clearActiveConversation()
    }
  }, [clearActiveConversation])

  const isReady = activeConversationId !== null && activePersonaSlug === params.slug

  if (createError) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{createError}</p>
        <button
          onClick={() => router.back()}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back
        </button>
      </main>
    )
  }

  if (!isReady) {
    return (
      <main className="min-h-screen [min-height:100svh] flex items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Summoning…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-paper">
      <ChatHeader personaName={personaName} portraitUrl={portraitUrl} />
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {openingInvocation && <OpeningInvocation text={openingInvocation} />}
        <MessageList messages={messages} />
        <StreamingBubble />
        <ErrorMessage send={send} />
        <div id="chat-scroll-sentinel" />
      </div>
      <ChatInput send={send} />
    </main>
  )
}
