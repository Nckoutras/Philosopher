import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Conversation, Message, Subscription } from './api'

interface AppStore {
  // Auth
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  clearAuth: () => void

  // Subscription
  subscription: Subscription | null
  setSubscription: (sub: Subscription) => void
  get plan(): string

  // Active conversation
  activeConversationId: string | null
  setActiveConversation: (id: string | null) => void

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
  resetStreaming: () => void

  // Safety overlay
  safetyActive: boolean
  setSafetyActive: (v: boolean) => void
}

export const useStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Auth
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      clearAuth: () => set({ user: null, token: null, subscription: null }),

      // Subscription
      subscription: null,
      setSubscription: (sub) => set({ subscription: sub }),
      get plan() {
        const sub = get().subscription
        return sub && ['active', 'trialing'].includes(sub.status) ? sub.plan : 'free'
      },

      // Active conversation
      activeConversationId: null,
      setActiveConversation: (id) => set({ activeConversationId: id, messages: [], streamingContent: '' }),

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
      resetStreaming: () => set({ isStreaming: false, streamingContent: '' }),
      safetyActive: false,
      setSafetyActive: (v) => set({ safetyActive: v }),
    }),
    {
      name: 'philosopher-store',
      partialize: (s) => ({ user: s.user, token: s.token, subscription: s.subscription }),
    }
  )
)
