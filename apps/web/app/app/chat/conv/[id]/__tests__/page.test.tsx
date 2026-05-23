// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ExistingConversationPage from '../page'
import * as apiModule from '@/lib/api'
import { useStore } from '@/lib/store'

const mockPush = vi.fn()
const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: vi.fn() }),
  useParams: () => ({ id: 'conv-abc' }),
}))

vi.mock('@/lib/useStream', () => ({
  useStream: () => ({ send: vi.fn() }),
}))

vi.mock('@/components/chat/ChatHeader', () => ({
  default: ({ personaName }: { personaName: string }) => <div data-testid="chat-header">{personaName}</div>,
}))
vi.mock('@/components/chat/MessageList', () => ({
  default: () => <div data-testid="message-list" />,
}))
vi.mock('@/components/chat/StreamingBubble', () => ({
  default: () => null,
}))
vi.mock('@/components/chat/ErrorMessage', () => ({
  default: () => null,
}))
vi.mock('@/components/chat/SafetyBubble', () => ({
  default: () => null,
}))
vi.mock('@/components/chat/SafetyReEntryCard', () => ({
  default: () => null,
}))
vi.mock('@/components/chat/PaywallModal', () => ({
  default: () => null,
}))
vi.mock('@/components/chat/ChatInput', () => ({
  default: () => <div data-testid="chat-input" />,
}))

const mockConversations = [
  {
    id: 'conv-abc',
    title: 'Test convo',
    message_count: 3,
    last_message_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    persona: {
      id: 'p1',
      slug: 'epictetus',
      name: 'Epictetus',
      era: null,
      tradition: null,
      tier: 'free',
      tagline: null,
      avatar_emoji: null,
      opening_invocation: null,
      bio: '',
      portrait_url: '',
      is_accessible: true,
    },
  },
]

const mockPersonas = [
  {
    id: 'p1',
    slug: 'epictetus',
    name: 'Epictetus',
    era: null,
    tradition: null,
    tier: 'free' as const,
    tagline: null,
    avatar_emoji: null,
    opening_invocation: null,
    bio: '',
    portrait_url: 'https://example.com/epictetus.jpg',
    is_accessible: true,
  },
]

const mockMessages = [
  {
    id: 'm1',
    role: 'assistant' as const,
    content: 'Hello',
    safety_level: 'none',
    persona_override: false,
    created_at: new Date().toISOString(),
  },
]

beforeEach(() => {
  mockPush.mockClear()
  mockReplace.mockClear()
  // Reset store to logged-in state
  useStore.setState({
    _hasHydrated: true,
    token: 'test-token',
    activeConversationId: null,
    activePersonaSlug: null,
    messages: [],
    safetyActive: false,
    streamError: null,
  })
  vi.spyOn(apiModule.api, 'getConversations').mockResolvedValue(mockConversations as never)
  vi.spyOn(apiModule.api, 'getPersonas').mockResolvedValue(mockPersonas as never)
  vi.spyOn(apiModule.api, 'getMessages').mockResolvedValue(mockMessages as never)
})

describe('ExistingConversationPage', () => {
  it('sets activeConversationId and loads messages on mount', async () => {
    render(<ExistingConversationPage />)
    await waitFor(() => {
      expect(useStore.getState().activeConversationId).toBe('conv-abc')
    })
    await waitFor(() => {
      expect(useStore.getState().messages).toHaveLength(1)
    })
  })

  it('renders ChatHeader with persona name once loaded', async () => {
    render(<ExistingConversationPage />)
    await waitFor(() => {
      expect(screen.getByTestId('chat-header')).toBeTruthy()
    })
    expect(screen.getByText('Epictetus')).toBeTruthy()
  })

  it('does not pass openingInvocation (null) to setActiveConversation', async () => {
    const spy = vi.spyOn(useStore.getState(), 'setActiveConversation')
    render(<ExistingConversationPage />)
    await waitFor(() => {
      expect(spy).toHaveBeenCalled()
    })
    const callArgs = spy.mock.calls[0]
    // 5th argument is openingInvocation — must be null for existing conversations
    expect(callArgs[4]).toBeNull()
  })

  it('redirects to /auth when no token', () => {
    useStore.setState({ token: null, _hasHydrated: true })
    render(<ExistingConversationPage />)
    expect(mockReplace).toHaveBeenCalledWith('/auth')
  })
})
