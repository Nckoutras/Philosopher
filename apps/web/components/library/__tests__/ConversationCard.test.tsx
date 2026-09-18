// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ConversationCard from '../ConversationCard'
import type { Conversation } from '@/lib/api'

const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))
vi.mock('next/image', () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}))

function makeConv(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: 'conv-123',
    title: 'On the nature of virtue',
    message_count: 14,
    last_message_at: new Date(Date.now() - 86400000).toISOString(), // yesterday
    created_at: new Date().toISOString(),
    persona: {
      id: 'p1',
      slug: 'epictetus',
      name: 'Epictetus',
      era: null,
      tradition: null,
      tier: 'free',
      tagline: 'Stoic wisdom',
      avatar_emoji: null,
      opening_invocation: null,
      bio: '',
      portrait_url: '',
      is_accessible: true,
    },
    source_persona_slug: null,
    source_context_content: null,
    last_message_snippet: null,
    // Added to Conversation after these fixtures were written (api.ts:199-202).
    // Explicit rather than cast away: deep_mode drives a visible badge, and origin_*
    // drive the "Return to [origin]" link, so a fixture that omits them tests a
    // conversation shape the API cannot return (C-06).
    origin_persona_slug: null,
    origin_persona_name: null,
    deep_mode: false,
    ...overrides,
  }
}

beforeEach(() => {
  mockPush.mockClear()
})

describe('ConversationCard', () => {
  it('renders persona name', () => {
    render(<ConversationCard conversation={makeConv()} />)
    expect(screen.getByText('Epictetus')).toBeTruthy()
  })

  it('renders meta line with message count and Yesterday', () => {
    render(<ConversationCard conversation={makeConv()} />)
    const metaEl = screen.getByText(/14 messages/)
    expect(metaEl).toBeTruthy()
    expect(metaEl.textContent).toContain('Yesterday')
  })

  it('renders title when present', () => {
    render(<ConversationCard conversation={makeConv({ title: 'On virtue' })} />)
    expect(screen.getByText('On virtue')).toBeTruthy()
  })

  it('renders fallback snippet when title is null', () => {
    render(
      <ConversationCard conversation={makeConv({ title: null })} />,
    )
    expect(screen.getByText(/Epictetus/)).toBeTruthy()
  })

  it('navigates to correct conv route on tap', () => {
    render(<ConversationCard conversation={makeConv({ id: 'abc-456' })} />)
    const btn = screen.getByRole('button')
    fireEvent.click(btn)
    expect(mockPush).toHaveBeenCalledWith('/app/chat/conv/abc-456')
  })

  it('renders portrait image when portraitUrl provided', () => {
    render(
      <ConversationCard
        conversation={makeConv()}
        portraitUrl="https://example.com/portrait.jpg"
      />,
    )
    const img = screen.getByAltText('Epictetus') as HTMLImageElement
    expect(img.src).toContain('example.com/portrait.jpg')
  })

  it('renders initials fallback when no portraitUrl', () => {
    render(<ConversationCard conversation={makeConv()} />)
    expect(screen.getByText('E')).toBeTruthy()
  })
})
