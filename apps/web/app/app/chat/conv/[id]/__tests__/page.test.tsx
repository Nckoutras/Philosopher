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

// THE SINGULAR RESPONSE, which is what the page actually calls (TD-86 step 2,
// cause 6). The page has called `api.getConversation(params.id)` since #83; this
// file has mocked `getConversations` (plural) since #106 and mocks the singular
// nowhere, so the real method ran unmocked, Promise.all rejected, and the page never
// left its loading state. Three tests failed on one missing mock.
//
// C-06: every field the page reads off this object is set here EXPLICITLY, including
// the two whose correct value is null and the one whose correct value is false. The
// page reads conv.id, conv.persona.slug, conv.persona.name, conv.origin_persona_slug,
// conv.origin_persona_name and conv.deep_mode (page.tsx:238-256). A MagicMock-shaped
// omission here would not throw — setOrigin would take the fallback branch and
// setDeepMode would store undefined — so the test would pass or fail for reasons
// unrelated to what it claims to check.
const mockConversation = {
  id: 'conv-abc',
  title: 'Test convo',
  message_count: 3,
  last_message_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  // null on both: this conversation was not opened from another mind, so the page
  // falls back to conv.persona for the origin (page.tsx:253-256).
  origin_persona_slug: null,
  origin_persona_name: null,
  deep_mode: false,
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
}

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
    token: 'test-token',
    activeConversationId: null,
    activePersonaSlug: null,
    messages: [],
    safetyActive: false,
    streamError: null,
  })
  vi.spyOn(apiModule.api, 'getConversation').mockResolvedValue(mockConversation as never)
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

  it('redirects to sign-in CARRYING the destination when there is no token', async () => {
    // CHANGED DELIBERATELY (BUG-002). This asserted `'/auth'` — bare, with the
    // destination discarded. That was the defect: a reader sent here by a shared
    // link lost the conversation they came for and landed on welcome.
    //
    // It also now waits, because useAuthGate decides nothing until the persisted
    // store has hydrated. The old guard fired on the first frame, which is what
    // bounced signed-IN users whose store had not arrived yet.
    // The URL matters: safeReturnTo allow-lists `/app/` only, so the gate emits
    // no next= from jsdom's default location of '/'. Putting the test where the
    // page actually lives is the difference between asserting the behaviour and
    // asserting the harness.
    window.history.replaceState({}, '', '/app/chat/conv/conv-abc')
    useStore.setState({ token: null })
    render(<ExistingConversationPage />)
    await waitFor(() => expect(mockReplace).toHaveBeenCalled())
    const target = mockReplace.mock.calls[0][0] as string
    expect(target.startsWith('/auth?mode=signin')).toBe(true)
    expect(target).toContain('next=')
    expect(decodeURIComponent(target)).toContain('/app/chat/conv/conv-abc')
    window.history.replaceState({}, '', '/')
  })
})
