'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { api, SaveLimitError, DuplicateSaveError } from '@/lib/api'
import toast from 'react-hot-toast'
import { renderSavedToast } from '@/components/chat/savedToast'
import ChatHeader from '@/components/chat/ChatHeader'
import OpeningInvocation from '@/components/chat/OpeningInvocation'
import MessageList from '@/components/chat/MessageList'
import StreamingBubble from '@/components/chat/StreamingBubble'
import ErrorMessage from '@/components/chat/ErrorMessage'
import SafetyBubble from '@/components/chat/SafetyBubble'
import SafetyReEntryCard from '@/components/chat/SafetyReEntryCard'
import PaywallModal from '@/components/chat/PaywallModal'
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
  const safetyActive = useStore((s) => s.safetyActive)
  const showPaywall = useStore((s) => s.showPaywall)
  const paywallDetails = useStore((s) => s.paywallDetails)
  const clearPaywall = useStore((s) => s.clearPaywall)
  const loadSavedLines = useStore((s) => s.loadSavedLines)

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
        await loadSavedLines()
      } catch (err) {
        if (cancelled) return
        setCreateError(err instanceof Error ? err.message : 'Could not start conversation')
      }
    }

    init()

    return () => {
      cancelled = true
    }
  }, [params.slug, token, router, setActiveConversation, loadSavedLines])

  // Clear conversation state on unmount
  useEffect(() => {
    return () => {
      clearActiveConversation()
    }
  }, [clearActiveConversation])

  async function handleSaveLine(messageId: string) {
    const state = useStore.getState()

    if (state.savedMessageIds.has(messageId)) {
      const savedLineToRemove = state.savedLines.find(l => l.message_id === messageId)
      if (!savedLineToRemove) return

      useStore.getState().removeAfterDelete(savedLineToRemove.id, messageId)
      try {
        await api.deleteSavedLine(savedLineToRemove.id)
      } catch {
        useStore.setState((s) => ({
          savedLines: [...s.savedLines, savedLineToRemove],
          savedMessageIds: new Set([...s.savedMessageIds, messageId]),
          freeSaveCount: s.freeSaveCount + 1,
        }))
        toast.error('Could not remove. Try again.')
      }
      return
    }

    const isAtLimit =
      state.plan === 'free' &&
      state.freeTierLimit !== null &&
      state.freeSaveCount >= state.freeTierLimit
    if (isAtLimit) return

    state.optimisticSave(messageId)
    renderSavedToast()

    try {
      await api.createSavedLine(messageId)
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
