import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Conversation, Message, Subscription, SavedLineRead, ReflectionFeedItem, Insight } from './api'
import { api } from './api'

function computePlan(sub: Subscription | null): string {
  return sub && ['active', 'trialing'].includes(sub.status) ? sub.plan : 'free'
}

export interface PaywallDetails {
  upgradeTarget: 'pro' | 'premium'
  reason?: 'daily' | 'go_deeper_depth' | 'persona_locked'
  resetAt?: Date
  limit?: number
  personaVoice?: string
}

interface AppStore {
  // Auth
  user: User | null
  token: string | null
  hasHydrated: boolean
  setHasHydrated: (v: boolean) => void
  setAuth: (user: User, token: string) => void
  setUser: (user: User) => void
  clearAuth: () => void

  // Subscription
  subscription: Subscription | null
  setSubscription: (sub: Subscription) => void
  plan: string

  // Insight discoverability glow
  activeInsights: Insight[]                       // transient (refetched)
  seenInsightIds: string[]                        // persisted
  setActiveInsights: (list: Insight[]) => void
  markInsightsSeenForConversation: (conversationId: string) => void

  // Unread Sunday/season letters — drives the "something new" star on Home.
  // TRANSIENT (refetched by LettersBootstrap from read_at, the server truth); not
  // persisted, so a downgrade or reload starts empty rather than lingering.
  unreadLetterIds: string[]
  setUnreadLetterIds: (ids: string[]) => void
  markLetterRead: (id: string) => void

  // Active conversation + persona display data
  activeConversationId: string | null
  activePersonaSlug: string | null
  activePersonaName: string | null
  activePersonaPortraitUrl: string | null
  activePersonaOpeningInvocation: string | null
  setActiveConversation: (
    conversationId: string,
    personaSlug: string,
    personaName: string,
    portraitUrl: string,
    openingInvocation: string | null,
  ) => void
  clearActiveConversation: () => void
  // Sticky guest mind: update only the active persona display fields (header +
  // who-answers-next), without resetting the conversation/messages.
  setActivePersona: (personaSlug: string, personaName: string, portraitUrl: string) => void

  // Messages for active conversation
  messages: Message[]
  setMessages: (messages: Message[]) => void
  appendMessage: (message: Message) => void
  updateLastAssistantMessage: (content: string) => void

  // Streaming state
  isStreaming: boolean
  setStreaming: (v: boolean) => void
  streamingContent: string
  setStreamingContent: (v: string) => void
  appendStreamingContent: (chunk: string) => void
  isCorrecting: boolean
  correctionContent: string
  setCorrection: () => void
  appendCorrectionContent: (chunk: string) => void
  streamingBroughtInName: string | null
  setStreamingBroughtIn: (name: string | null) => void
  resetStreaming: () => void

  // Safety overlay
  safetyActive: boolean
  setSafetyActive: (v: boolean) => void

  // SSE error event state (transient — not persisted)
  streamError: { error_code: string; persona_voice: string } | null
  setStreamError: (err: { error_code: string; persona_voice: string } | null) => void

  // Paywall state (transient — not persisted)
  showPaywall: boolean
  paywallDetails: PaywallDetails | null
  setShowPaywall: (show: boolean, details?: PaywallDetails | null) => void
  clearPaywall: () => void

  // Conversations list cache
  conversations: Conversation[]
  conversationsLoading: boolean
  conversationsError: Error | null
  setConversations: (list: Conversation[]) => void
  setConversationsLoading: (v: boolean) => void
  setConversationsError: (err: Error | null) => void

  // Saved lines
  savedLines: SavedLineRead[]
  savedMessageIds: Set<string>
  freeSaveCount: number
  freeTierLimit: number | null
  savedLinesLoading: boolean
  savedLinesError: Error | null
  loadSavedLines: () => Promise<void>
  optimisticSave: (messageId: string) => void
  revertSave: (messageId: string) => void
  removeAfterDelete: (savedLineId: string, messageId: string) => void

  // Reflections feed (unified lines + mirror/council verdicts)
  feedItems: ReflectionFeedItem[]
  feedLoading: boolean
  feedError: Error | null
  loadReflectionsFeed: () => Promise<void>
  removeFeedLine: (savedLineId: string, messageId: string) => void
  removeFeedMirror: (mirrorId: string) => void
  removeFeedCouncil: (sessionId: string) => void
  removeFeedCounterview: (counterviewId: string) => void
  removeFeedYvY: (selfComparisonId: string) => void
}

export const useStore = create<AppStore>()(
  persist(
    (set) => ({
      // Auth
      user: null,
      token: null,
      hasHydrated: false,
      setHasHydrated: (v) => set({ hasHydrated: v }),
      setAuth: (user, token) => set({ user, token }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ user: null, token: null, subscription: null, plan: 'free' }),

      // Subscription
      subscription: null,
      plan: 'free',
      setSubscription: (sub) => set({ subscription: sub, plan: computePlan(sub) }),

      // Insight discoverability glow
      activeInsights: [],
      seenInsightIds: [],
      setActiveInsights: (list) => set({ activeInsights: list }),
      markInsightsSeenForConversation: (conversationId) => set((s) => {
        const ids = s.activeInsights.filter(i => i.conversation_id === conversationId).map(i => i.id)
        if (ids.length === 0) return {} as Partial<AppStore>
        return { seenInsightIds: Array.from(new Set([...s.seenInsightIds, ...ids])) }
      }),

      // Unread letters — transient; LettersBootstrap fills it from read_at.
      unreadLetterIds: [],
      setUnreadLetterIds: (ids) => set({ unreadLetterIds: ids }),
      markLetterRead: (id) => set((s) =>
        s.unreadLetterIds.includes(id)
          ? { unreadLetterIds: s.unreadLetterIds.filter((x) => x !== id) }
          : ({} as Partial<AppStore>),
      ),

      // Active conversation + persona display data
      activeConversationId: null,
      activePersonaSlug: null,
      activePersonaName: null,
      activePersonaPortraitUrl: null,
      activePersonaOpeningInvocation: null,
      setActiveConversation: (conversationId, personaSlug, personaName, portraitUrl, openingInvocation) =>
        set({
          activeConversationId: conversationId,
          activePersonaSlug: personaSlug,
          activePersonaName: personaName,
          activePersonaPortraitUrl: portraitUrl,
          activePersonaOpeningInvocation: openingInvocation,
          messages: [],
          streamingContent: '',
          isCorrecting: false,
          correctionContent: '',
          streamingBroughtInName: null,
        }),
      clearActiveConversation: () =>
        set({
          activeConversationId: null,
          activePersonaSlug: null,
          activePersonaName: null,
          activePersonaPortraitUrl: null,
          activePersonaOpeningInvocation: null,
          isStreaming: false,
          streamingContent: '',
          isCorrecting: false,
          correctionContent: '',
          streamingBroughtInName: null,
          streamError: null,
        }),
      setActivePersona: (personaSlug, personaName, portraitUrl) =>
        set({
          activePersonaSlug: personaSlug,
          activePersonaName: personaName,
          activePersonaPortraitUrl: portraitUrl,
        }),

      // Messages
      messages: [],
      setMessages: (messages) => set({ messages }),
      appendMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
      updateLastAssistantMessage: (content) =>
        set((s) => {
          const msgs = [...s.messages]
          const last = msgs.findLastIndex((m) => m.role === 'assistant')
          if (last >= 0) msgs[last] = { ...msgs[last], content }
          return { messages: msgs }
        }),

      // Streaming
      isStreaming: false,
      setStreaming: (v) => set({ isStreaming: v }),
      streamingContent: '',
      setStreamingContent: (v) => set({ streamingContent: v }),
      appendStreamingContent: (chunk) => set((s) => ({ streamingContent: s.streamingContent + chunk })),
      isCorrecting: false,
      correctionContent: '',
      setCorrection: () => set({ isCorrecting: true }),
      appendCorrectionContent: (chunk) => set((s) => ({ correctionContent: s.correctionContent + chunk })),
      streamingBroughtInName: null,
      setStreamingBroughtIn: (name) => set({ streamingBroughtInName: name }),
      resetStreaming: () => set({ isStreaming: false, streamingContent: '', isCorrecting: false, correctionContent: '', streamingBroughtInName: null }),
      safetyActive: false,
      setSafetyActive: (v) => set({ safetyActive: v }),

      streamError: null,
      setStreamError: (err) => set({ streamError: err }),

      showPaywall: false,
      paywallDetails: null,
      setShowPaywall: (show, details) =>
        set({ showPaywall: show, paywallDetails: details ?? null }),
      clearPaywall: () => set({ showPaywall: false, paywallDetails: null }),

      conversations: [],
      conversationsLoading: false,
      conversationsError: null,
      setConversations: (list) => set({ conversations: list }),
      setConversationsLoading: (v) => set({ conversationsLoading: v }),
      setConversationsError: (err) => set({ conversationsError: err }),

      // Saved lines
      savedLines: [],
      savedMessageIds: new Set<string>(),
      freeSaveCount: 0,
      freeTierLimit: null,
      savedLinesLoading: false,
      savedLinesError: null,
      loadSavedLines: async () => {
        set({ savedLinesLoading: true, savedLinesError: null })
        try {
          const res = await api.listSavedLines()
          set({
            savedLines: res.items,
            savedMessageIds: new Set(res.items.map((l) => l.message_id)),
            freeSaveCount: res.total_count,
            freeTierLimit: res.free_tier_limit,
            savedLinesLoading: false,
          })
        } catch (err) {
          set({
            savedLinesError: err instanceof Error ? err : new Error('Load failed'),
            savedLinesLoading: false,
          })
        }
      },
      optimisticSave: (messageId) =>
        set((s) => ({
          savedMessageIds: new Set([...s.savedMessageIds, messageId]),
          freeSaveCount: s.freeSaveCount + 1,
        })),
      revertSave: (messageId) =>
        set((s) => {
          const next = new Set(s.savedMessageIds)
          next.delete(messageId)
          return { savedMessageIds: next, freeSaveCount: Math.max(0, s.freeSaveCount - 1) }
        }),
      removeAfterDelete: (savedLineId, messageId) =>
        set((s) => {
          const next = new Set(s.savedMessageIds)
          next.delete(messageId)
          return {
            savedLines: s.savedLines.filter((l) => l.id !== savedLineId),
            savedMessageIds: next,
            freeSaveCount: Math.max(0, s.freeSaveCount - 1),
          }
        }),

      // Reflections feed — separate from loadSavedLines so the chat save
      // paywall state (savedMessageIds/freeSaveCount/freeTierLimit), which the
      // chat pages populate via loadSavedLines, is never disturbed by feed loads.
      feedItems: [],
      feedLoading: false,
      feedError: null,
      loadReflectionsFeed: async () => {
        set({ feedLoading: true, feedError: null })
        try {
          const res = await api.getReflectionsFeed()
          set({ feedItems: res.items, feedLoading: false })
        } catch (err) {
          set({
            feedError: err instanceof Error ? err : new Error('Load failed'),
            feedLoading: false,
          })
        }
      },
      // Deleting a saved line from the feed also decrements the shared paywall
      // counters, mirroring removeAfterDelete so the chat screens stay accurate.
      removeFeedLine: (savedLineId, messageId) =>
        set((s) => {
          const next = new Set(s.savedMessageIds)
          next.delete(messageId)
          return {
            feedItems: s.feedItems.filter(
              (i) => !(i.kind === 'line' && i.id === savedLineId),
            ),
            savedLines: s.savedLines.filter((l) => l.id !== savedLineId),
            savedMessageIds: next,
            freeSaveCount: Math.max(0, s.freeSaveCount - 1),
          }
        }),
      removeFeedMirror: (mirrorId) =>
        set((s) => ({
          feedItems: s.feedItems.filter(
            (i) => !(i.kind === 'mirror_verdict' && i.mirror_id === mirrorId),
          ),
        })),
      removeFeedCouncil: (sessionId) =>
        set((s) => ({
          feedItems: s.feedItems.filter(
            (i) => !(i.kind === 'council_verdict' && i.session_id === sessionId),
          ),
        })),
      removeFeedCounterview: (counterviewId) =>
        set((s) => ({
          feedItems: s.feedItems.filter(
            (i) => !(i.kind === 'counterview_verdict' && i.counterview_id === counterviewId),
          ),
        })),
      removeFeedYvY: (selfComparisonId) =>
        set((s) => ({
          feedItems: s.feedItems.filter(
            (i) => !(i.kind === 'yvy_sentence' && i.self_comparison_id === selfComparisonId),
          ),
        })),
    }),
    {
      name: 'philosopher-store',
      partialize: (s) => ({ user: s.user, token: s.token, subscription: s.subscription, seenInsightIds: s.seenInsightIds }),
      onRehydrateStorage: () => (state) => {
        if (state?.subscription) state.setSubscription(state.subscription)
        state?.setHasHydrated(true)
      },
    }
  )
)
