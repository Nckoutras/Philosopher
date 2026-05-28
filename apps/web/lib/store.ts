import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Conversation, Message, Subscription, SavedLineRead } from './api'
import { api } from './api'

export interface PaywallDetails {
  upgradeTarget: 'pro' | 'premium'
  resetAt: Date
  limit: number
  personaVoice?: string
}

interface AppStore {
  // Auth
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  setUser: (user: User) => void
  clearAuth: () => void

  // Subscription
  subscription: Subscription | null
  setSubscription: (sub: Subscription) => void
  get plan(): string

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
}

export const useStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Auth
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ user: null, token: null, subscription: null }),

      // Subscription
      subscription: null,
      setSubscription: (sub) => set({ subscription: sub }),
      get plan() {
        const sub = get().subscription
        return sub && ['active', 'trialing'].includes(sub.status) ? sub.plan : 'free'
      },

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
          streamError: null,
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
      resetStreaming: () => set({ isStreaming: false, streamingContent: '', isCorrecting: false, correctionContent: '' }),
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
    }),
    {
      name: 'philosopher-store',
      partialize: (s) => ({ user: s.user, token: s.token, subscription: s.subscription }),
    }
  )
)
