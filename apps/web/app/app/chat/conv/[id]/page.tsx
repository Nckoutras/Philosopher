'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import AnotherMindSheet from '@/components/chat/AnotherMindSheet'
import { useStore } from '@/lib/store'
import { useStream } from '@/lib/useStream'
import { api, SaveLimitError, DuplicateSaveError, ConversationNotFoundError, type Insight } from '@/lib/api'
import toast from 'react-hot-toast'
import { renderSavedToast } from '@/components/chat/savedToast'
import { useInsightDoors } from '@/lib/useInsightDoors'
import { markSeen, unmarkSeen, pruneSeen } from '@/lib/roomNoticedSeen'
import ChatHeader from '@/components/chat/ChatHeader'
import OpeningInvocation from '@/components/chat/OpeningInvocation'
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
  const openingInvocation = useStore((s) => s.activePersonaOpeningInvocation)
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
  const setActivePersona = useStore((s) => s.setActivePersona)
  const plan = useStore((s) => s.plan)
  const deepRemaining = useStore((s) => s.deepRemaining)
  const setShowPaywall = useStore((s) => s.setShowPaywall)
  const markInsightsSeenForConversation = useStore((s) => s.markInsightsSeenForConversation)

  const [loadError, setLoadError] = useState<string | null>(null)
  const [inputDraft, setInputDraft] = useState<string | undefined>(undefined)
  const [pickerOpen, setPickerOpen] = useState(false)
  // Immutable origin/home persona for this conversation (for "Return to [origin]").
  const [origin, setOrigin] = useState<{ slug: string; name: string } | null>(null)
  // Pro sticky deep mode: reflects conversations.deep_mode; survives reload.
  const [deepMode, setDeepMode] = useState(false)
  const isPro = plan === 'pro' || plan === 'premium'
  const [insight, setInsight] = useState<Insight | null>(null)
  // deepLocked: a free user out of daily deep allowance. Takes precedence over
  // the on-state in the chip. deepRemaining is -1 for pro/premium (never locks)
  // and may be a stale -1 on a hard-refresh straight into chat before /me runs
  // — fail-open by design (backend metering is the source of truth).
  const deepLocked = !isPro && deepRemaining === 0
  const { send, sendAnotherMind } = useStream()
  const { primary, discard } = useInsightDoors()
  const hasSentTopicRef = useRef(false)
  // Assistant-message count last observed; null until baselined on conversation
  // load, so the initial load is not mistaken for a turn boundary.
  const prevAssistantCountRef = useRef<number | null>(null)

  const handleBringAnotherMind = () => setPickerOpen(true)
  const isReady = activeConversationId === params.id

  // Sticky guest: make the brought-in guest the active mind for next turns.
  async function handleContinueWithGuest(slug: string, name: string) {
    try {
      const updated = await api.setActiveMind(params.id, slug)
      setActivePersona(updated.persona.slug, updated.persona.name, updated.persona.portrait_url)
    } catch {
      toast.error('Could not switch. Please try again.')
    }
  }

  // Return to origin: clear the sticky guest back to the home persona.
  async function handleReturnToOrigin() {
    try {
      const updated = await api.clearActiveMind(params.id)
      setActivePersona(updated.persona.slug, updated.persona.name, updated.persona.portrait_url)
    } catch {
      toast.error('Could not switch. Please try again.')
    }
  }

  // Pro sticky deep mode: toggle on/off. Pro-only (the toggle is not rendered for
  // free users, and the endpoint + read site are Pro-gated regardless).
  async function handleToggleDeepMode() {
    const next = !deepMode
    setDeepMode(next) // optimistic
    try {
      const updated = next ? await api.setDeepMode(params.id) : await api.clearDeepMode(params.id)
      setDeepMode(updated.deep_mode)
    } catch {
      setDeepMode(!next) // revert
      toast.error('Could not change deep mode. Please try again.')
    }
  }

  const isGuestActive = !!origin && activePersonaSlug !== null && activePersonaSlug !== origin.slug

  // Take to the Council: seed the matter from the last user message (the thing
  // they most recently raised), capped at Council's 600-char matter limit.
  const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user')?.content ?? ''

  // Visible to EVERYONE (upsell surface). Pro → seed sessionStorage (reusing the
  // mirror→council pattern) + open the pre-filled Council. Free → the EXACT
  // existing Council wall (/app/upgrade), same as rituals' Council entry.
  function handleTakeToCouncil() {
    if (!isPro) {
      router.push('/app/upgrade')
      return
    }
    if (!lastUserMessage.trim()) return
    sessionStorage.setItem('council_prefill', lastUserMessage.slice(0, 600))
    sessionStorage.setItem('council_source', 'chat')
    sessionStorage.setItem('council_conversation_id', params.id)
    router.push('/app/council')
  }

  // Fetch this conversation's recurrence insight and pick the first that is
  // neither server-dismissed nor dismissed this session. A merely-seen (not
  // dismissed) insight may re-light on a later boundary — that's intended.
  //
  // If the scoped fetch finds nothing, fall back to the GLOBAL list (D1b): a signal
  // from ANOTHER conversation lights a door chip here too, filtered by the shared
  // Home seen-state (wr_roomnoticed_seen) so once acted-on/dismissed anywhere it
  // stops nagging. Scoped insights re-light until dismissed (high relevance); global
  // ones respect the seen set (lower relevance, cross-surface).
  const refreshInsight = useCallback(async () => {
    try {
      const list = await api.getInsights(params.id)
      const next = list.find(
        (i) => !i.is_dismissed && !sessionDismissedInsightIds.has(i.id),
      ) ?? null
      if (next) {
        setInsight(next)
        return
      }
      // Global fallback: newest non-dismissed insight from any conversation this
      // device hasn't already acted on (via Home or here). Prune the seen set to
      // the live ids first, then exclude dismissed / session-dismissed / seen.
      const global = await api.getInsights()
      const seen = new Set(pruneSeen(global.map((i) => i.id)))
      const globalNext = global.find(
        (i) => !i.is_dismissed && !sessionDismissedInsightIds.has(i.id) && !seen.has(i.id),
      ) ?? null
      setInsight(globalNext)
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

        // conv.persona is the coalesced ACTIVE mind (sticky guest survives reload);
        // origin_persona_* is the immutable home for the "Return to [origin]" link.
        // Empty conversations (abandoned topic / cross-persona rows) carry no opening
        // message; fall back to the active persona's opening_invocation so the room is
        // never blank — mirrors chat/[slug]. Non-empty conversations show their own
        // history and get null (the greeting, if any, is already a message row).
        setActiveConversation(
          conv.id,
          conv.persona.slug,
          conv.persona.name,
          personaFull?.portrait_url ?? '',
          msgs.length === 0 ? (personaFull?.opening_invocation ?? null) : null,
        )
        setOrigin(
          conv.origin_persona_slug && conv.origin_persona_name
            ? { slug: conv.origin_persona_slug, name: conv.origin_persona_name }
            : { slug: conv.persona.slug, name: conv.persona.name },
        )
        setDeepMode(conv.deep_mode)

        // Pre-fill input draft for cross-persona conversations (written by PersonaPickerSheet)
        const draft = localStorage.getItem(`cross_persona_draft_${params.id}`)
        // One-shot prefill from a letter suggested-persona tap (council_prefill
        // convention): read-and-clear on mount, fills the composer only — never
        // auto-sends. Cross-persona draft wins if both are present; the composer is
        // empty at load, so nothing is overwritten.
        const prefill = sessionStorage.getItem(`chat_prefill_${params.id}`)
        sessionStorage.removeItem(`chat_prefill_${params.id}`)
        if (draft) {
          setInputDraft(draft)
          localStorage.removeItem(`cross_persona_draft_${params.id}`)
        } else if (prefill) {
          setInputDraft(prefill)
        }

        setMessages(msgs)
        await loadSavedLines()
      } catch (err) {
        if (cancelled) return
        // A deleted/missing conversation (e.g. a stale Continuing/Library card) is a
        // dead end, not an error to sit on: send the user back to Library with a note
        // instead of the failure screen. All other errors keep the dead-end screen.
        if (err instanceof ConversationNotFoundError) {
          toast('This conversation is no longer available')
          router.replace('/app/library')
          return
        }
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
    prevAssistantCountRef.current = null
  }, [params.id])

  // Opening the source conversation clears its discoverability glow.
  useEffect(() => {
    if (params.id) markInsightsSeenForConversation(params.id)
  }, [params.id, markInsightsSeenForConversation])

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

  // Doors come from the shared hook (byte-identical across chat, the Insights tab,
  // and Home). Discard additionally suppresses re-poll for this session via the
  // module-scoped set — chat-only, so it lives in the onRemove/onRestore callbacks.
  // An insight is "global" (surfaced here from ANOTHER conversation) when its origin
  // conversation is not this one. Global actions update the shared Home seen set so
  // "acted anywhere → gone everywhere"; scoped insights keep their re-light behavior.
  function handleInsightPrimary() {
    if (!insight) return
    if (insight.conversation_id !== params.id) markSeen(insight.id)
    primary(insight)
  }

  function handleInsightDiscard() {
    const current = insight
    if (!current) return
    const isGlobal = current.conversation_id !== params.id
    discard(current, {
      onRemove: () => {
        sessionDismissedInsightIds.add(current.id)
        // Global: mark seen immediately so it can't re-nudge (Home or here) before
        // the 5s server dismiss lands — mirrors RoomNoticedCard.
        if (isGlobal) markSeen(current.id)
        setInsight(null)
      },
      onRestore: () => {
        sessionDismissedInsightIds.delete(current.id)
        if (isGlobal) unmarkSeen(current.id)
        setInsight(current)
      },
    })
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
      <ChatHeader
        personaName={personaName}
        portraitUrl={portraitUrl}
        originName={origin?.name ?? null}
        isGuestActive={isGuestActive}
        onReturnToOrigin={handleReturnToOrigin}
      />

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {openingInvocation && <OpeningInvocation text={openingInvocation} />}
        <MessageList
          messages={messages}
          onSaveLine={handleSaveLine}
          onUpgradeConfirm={handleUpgradeConfirm}
          onBringAnotherMind={handleBringAnotherMind}
          deepMode={deepMode}
          deepLocked={deepLocked}
          onToggleDeepMode={handleToggleDeepMode}
          onDeepPaywall={() => setShowPaywall(true, { upgradeTarget: 'pro', reason: 'deep_mode' })}
          onContinueWithGuest={handleContinueWithGuest}
          insightType={insight?.insight_type ?? null}
          onInsightDoor={handleInsightPrimary}
          onInsightDismiss={handleInsightDiscard}
          onTakeToCouncil={handleTakeToCouncil}
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
        excludeSlugs={[activePersonaSlug, origin?.slug].filter(Boolean) as string[]}
        onSelect={(slug) => { setPickerOpen(false); sendAnotherMind(slug) }}
      />
    </main>
  )
}
