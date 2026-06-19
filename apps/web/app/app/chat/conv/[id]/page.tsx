'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AnotherMindSheet from '@/components/chat/AnotherMindSheet'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { api, SaveLimitError, DuplicateSaveError, type Insight } from '@/lib/api'
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
import SubPageNav from '@/components/layout/SubPageNav'

// Delay before the single extra recurrence re-poll fires after a turn boundary.
// The insight is written by an async worker, so the boundary poll often lands
// too early; this catch-up poll is a same-session testing affordance. Trivially
// tunable/removable — set to 0 / delete the timeout to disable.
const INSIGHT_REPOLL_MS = 7000

// Insights dismissed during THIS browser session. Module-scoped so it survives
// page remounts within the SPA (server-side is_dismissed is the real, durable
// "never resurface" control; this just suppresses instantly without a refetch).
const sessionDismissedInsightIds = new Set<string>()

export default function ExistingConversationPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()

  const token = useStore((s) => s.token)
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
  const activePersonaSlug = useStore((s) => s.activePersonaSlug)

  const [loadError, setLoadError] = useState<string | null>(null)
  const [inputDraft, setInputDraft] = useState<string | undefined>(undefined)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [insight, setInsight] = useState<Insight | null>(null)
  const [insightExpanded, setInsightExpanded] = useState(false)
  const { send, sendAnotherMind, sendGoDeeper } = useStream()
  const hasSentTopicRef = useRef(false)
  // Assistant-message count last observed; null until baselined on conversation
  // load, so the initial load is not mistaken for a turn boundary.
  const prevAssistantCountRef = useRef<number | null>(null)

  const handleBringAnotherMind = () => setPickerOpen(true)
  const isReady = activeConversationId === params.id

  // Fetch this conversation's recurrence insight and pick the first that is
  // neither server-dismissed nor dismissed this session. A merely-seen (not
  // dismissed) insight may re-light on a later boundary — that's intended.
  const refreshInsight = useCallback(async () => {
    try {
      const list = await api.getInsights(params.id)
      const next = list.find(
        (i) => !i.is_dismissed && !sessionDismissedInsightIds.has(i.id),
      ) ?? null
      setInsight(next)
    } catch {
      // Silent: the insight chip is a quiet affordance, never a hard failure.
    }
  }, [params.id])

  useEffect(() => {
    const sentinel = document.getElementById('chat-scroll-sentinel')
    sentinel?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }

    if (activeConversationId === params.id) return

    let cancelled = false
    setLoadError(null)
    setSafetyActive(false)
    setStreamError(null)

    async function init() {
      try {
        const [conv, personas, msgs] = await Promise.all([
          api.getConversation(params.id),
          api.getPersonas(),
          api.getMessages(params.id),
        ])
        if (cancelled) return

        const personaFull = personas.find((p) => p.slug === conv.persona.slug)

        setActiveConversation(
          conv.id,
          conv.persona.slug,
          conv.persona.name,
          personaFull?.portrait_url ?? '',
          null,
        )

        // Pre-fill input draft for cross-persona conversations (written by PersonaPickerSheet)
        const draft = localStorage.getItem(`cross_persona_draft_${params.id}`)
        if (draft) {
          setInputDraft(draft)
          localStorage.removeItem(`cross_persona_draft_${params.id}`)
        }

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
  }, [params.id, token, router, activeConversationId, setActiveConversation, setMessages, setSafetyActive, setStreamError, loadSavedLines, setInputDraft])

  useEffect(() => {
    return () => {
      clearActiveConversation()
    }
  }, [clearActiveConversation])

  useEffect(() => {
    if (!isReady || hasSentTopicRef.current) return
    const key = `today_topic_draft_${params.id}`
    const draft = localStorage.getItem(key)
    if (draft && messages.length === 0) {
      hasSentTopicRef.current = true
      localStorage.removeItem(key)
      send(draft, true)
    }
  }, [isReady, params.id, messages.length, send])

  // Reset insight state when switching conversations.
  useEffect(() => {
    setInsight(null)
    setInsightExpanded(false)
    prevAssistantCountRef.current = null
  }, [params.id])

  // Fetch on conversation load.
  useEffect(() => {
    if (!isReady) return
    refreshInsight()
  }, [isReady, refreshInsight])

  // Turn-boundary detection: when the assistant-message count grows, re-poll
  // immediately and once more after a short delay (the worker writes the insight
  // asynchronously, so the immediate poll usually misses it).
  useEffect(() => {
    if (!isReady) return
    const count = messages.filter((m) => m.role === 'assistant').length
    if (prevAssistantCountRef.current === null) {
      prevAssistantCountRef.current = count // baseline (initial load, not a boundary)
      return
    }
    if (count > prevAssistantCountRef.current) {
      prevAssistantCountRef.current = count
      refreshInsight()
      const t = setTimeout(refreshInsight, INSIGHT_REPOLL_MS)
      return () => clearTimeout(t)
    }
    prevAssistantCountRef.current = count
  }, [messages, isReady, refreshInsight])

  function handleInsightPrimary() {
    // Branch on insight type (Slice 2): a 'shift' goes to You-vs-You (which
    // enforces its own Pro gate); everything else reflects in the Mirror. No
    // theme seeding either way — later slice.
    if (insight?.insight_type === 'shift') {
      router.push('/app/you-vs-you')
    } else {
      router.push('/app/mirror')
    }
  }

  async function handleInsightDismiss() {
    const current = insight
    if (!current) return
    sessionDismissedInsightIds.add(current.id)
    setInsight(null)
    setInsightExpanded(false)
    try {
      await api.dismissInsight(current.id)
    } catch {
      // Server-side is_dismissed is the durable control; a failed PATCH just
      // means it may reappear next session. Session set already cleared it now.
    }
  }

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

  if (loadError) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{loadError}</p>
        <button
          onClick={() => router.push('/app/today')}
          className="font-lora text-[13px] text-sepia underline"
        >
          Home
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
      <SubPageNav fallbackHref="/app/library" showHome={false} />
      <ChatHeader personaName={personaName} portraitUrl={portraitUrl} />

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        <MessageList
          messages={messages}
          onSaveLine={handleSaveLine}
          onUpgradeConfirm={handleUpgradeConfirm}
          onBringAnotherMind={handleBringAnotherMind}
          onGoDeeper={() => sendGoDeeper()}
          insightContent={insight?.content ?? null}
          insightType={insight?.insight_type ?? null}
          insightExpanded={insightExpanded}
          onInsightTap={() => setInsightExpanded(true)}
          onInsightPrimary={handleInsightPrimary}
          onInsightDismiss={handleInsightDismiss}
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
        key={inputDraft ?? 'empty'}
        send={send}
        placeholder={safetyActive ? 'Write when you\'re ready…' : undefined}
        initialValue={inputDraft}
      />
      <PaywallModal
        open={showPaywall}
        details={paywallDetails}
        onClose={clearPaywall}
      />
      <AnotherMindSheet
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        excludeSlug={activePersonaSlug ?? ''}
        onSelect={(slug) => { setPickerOpen(false); sendAnotherMind(slug) }}
      />
    </main>
  )
}
