'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { api, SaveLimitError, DuplicateSaveError } from '@/lib/api'
import toast from 'react-hot-toast'
import { renderSavedToast } from '@/components/chat/savedToast'
import ChatHeader from '@/components/chat/ChatHeader'
import MessageList from '@/components/chat/MessageList'
import StreamingBubble from '@/components/chat/StreamingBubble'
import ErrorMessage from '@/components/chat/ErrorMessage'
import SafetyBubble from '@/components/chat/SafetyBubble'
import SafetyReEntryCard from '@/components/chat/SafetyReEntryCard'
import PaywallModal from '@/components/chat/PaywallModal'
import ChatInput from '@/components/chat/ChatInput'

export default function ExistingConversationPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()

  const token = useStore((s) => s.token)
  const _hasHydrated = useStore((s) => s._hasHydrated)
  const messages = useStore((s) => s.messages)
  const streamingContent = useStore((s) => s.streamingContent)
  const activeConversationId = useStore((s) => s.activeConversationId)
  const personaName = useStore((s) => s.activePersonaName) ?? ''
  const portraitUrl = useStore((s) => s.activePersonaPortraitUrl) ?? ''
  const safetyActive = useStore((s) => s.safetyActive)
  const showPaywall = useStore((s) => s.showPaywall)
  const paywallDetails = useStore((s) => s.paywallDetails)
  const setActiveConversation = useStore((s) => s.setActiveConversation)
  const setMessages = useStore((s) => s.setMessages)
  const clearActiveConversation = useStore((s) => s.clearActiveConversation)
  const clearPaywall = useStore((s) => s.clearPaywall)
  const setSafetyActive = useStore((s) => s.setSafetyActive)
  const setStreamError = useStore((s) => s.setStreamError)
  const loadSavedLines = useStore((s) => s.loadSavedLines)

  const [loadError, setLoadError] = useState<string | null>(null)
  const { send } = useStream()

  // Auto-scroll to last message whenever messages or streaming content changes
  useEffect(() => {
    const sentinel = document.getElementById('chat-scroll-sentinel')
    sentinel?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Load existing conversation on mount
  useEffect(() => {
    // Wait for Zustand persist to rehydrate from localStorage before deciding
    // whether to redirect. Without this, direct URL navigation runs this effect
    // before the persisted token is read, sees token===null, and redirects to
    // /auth even when the user is logged in. See store.ts onRehydrateStorage.
    if (!_hasHydrated) return
    if (token === null) {
      router.replace('/auth')
      return
    }

    // Already loaded this conversation
    if (activeConversationId === params.id) return

    let cancelled = false
    setLoadError(null)
    // Clear stale safety/error state
    setSafetyActive(false)
    setStreamError(null)

    async function init() {
      try {
        // Fetch all data in parallel: conversation list (for metadata), full personas (for portrait_url), messages
        const [convs, personas, msgs] = await Promise.all([
          api.getConversations(),
          api.getPersonas(),
          api.getMessages(params.id),
        ])
        if (cancelled) return

        const conv = convs.find((c) => c.id === params.id)
        if (!conv) {
          setLoadError('Conversation not found')
          return
        }

        const personaFull = personas.find((p) => p.slug === conv.persona.slug)

        // setActiveConversation clears messages — call it first, then setMessages
        setActiveConversation(
          conv.id,
          conv.persona.slug,
          conv.persona.name,
          personaFull?.portrait_url ?? '',
          null, // existing conversation: no opening invocation
        )
        setMessages(msgs)
        await loadSavedLines()
      } catch (err) {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Could not load conversation')
      }
    }

    init()

    return () => {
      cancelled = true
    }
  }, [params.id, _hasHydrated, token, router, activeConversationId, setActiveConversation, setMessages, setSafetyActive, setStreamError, loadSavedLines])

  // Clear conversation state on unmount
  useEffect(() => {
    return () => {
      clearActiveConversation()
    }
  }, [clearActiveConversation])

  async function handleSaveLine(messageId: string) {
    const state = useStore.getState()
    const isAtLimit =
      state.plan === 'free' &&
      state.freeTierLimit !== null &&
      state.freeSaveCount >= state.freeTierLimit
    if (isAtLimit) return

    state.optimisticSave(messageId)
    renderSavedToast()

    try {
      await api.createSavedLine(messageId)
      useStore.getState().loadSavedLines()
    } catch (err) {
      if (err instanceof SaveLimitError) {
        useStore.getState().revertSave(messageId)
        useStore.getState().setShowPaywall(true, { upgradeTarget: 'pro', resetAt: new Date(), limit: 3 })
      } else if (err instanceof DuplicateSaveError) {
        // 409: silent no-op — optimistic state is correct
      } else {
        useStore.getState().revertSave(messageId)
        toast.error('Could not save. Try again.')
      }
    }
  }

  function handleUpgradeConfirm() {
    useStore.getState().setShowPaywall(true, { upgradeTarget: 'pro', resetAt: new Date(), limit: 3 })
  }

  const isReady = activeConversationId === params.id

  if (loadError) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{loadError}</p>
        <button
          onClick={() => router.push('/app/library')}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back to conversations
        </button>
      </main>
    )
  }

  if (!isReady) {
    return (
      <main className="min-h-screen [min-height:100svh] flex items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-paper">
      <ChatHeader personaName={personaName} portraitUrl={portraitUrl} />
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        <MessageList
          messages={messages}
          onSaveLine={handleSaveLine}
          onUpgradeConfirm={handleUpgradeConfirm}
        />
        {safetyActive ? (
          <>
            <SafetyBubble />
            <SafetyReEntryCard />
          </>
        ) : (
          <>
            <StreamingBubble />
            <ErrorMessage send={send} />
          </>
        )}
        <div id="chat-scroll-sentinel" />
      </div>
      <ChatInput
        send={send}
        placeholder={safetyActive ? 'Write when you\'re ready…' : undefined}
      />
      <PaywallModal
        open={showPaywall}
        details={paywallDetails}
        onClose={clearPaywall}
      />
    </main>
  )
}
