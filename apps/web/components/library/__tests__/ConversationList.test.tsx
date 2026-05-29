// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ConversationList from '../ConversationList'
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

function makeConv(id: string, daysAgo: number, name = 'Epictetus'): Conversation {
  return {
    id,
    title: `Title for ${id}`,
    message_count: 5,
    last_message_at: new Date(Date.now() - daysAgo * 86400000).toISOString(),
    created_at: new Date().toISOString(),
    persona: {
      id: `p-${id}`,
      slug: 'epictetus',
      name,
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
    source_persona_slug: null,
    source_context_content: null,
    last_message_snippet: null,
  }
}

describe('ConversationList', () => {
  it('renders loading state', () => {
    render(
      <ConversationList
        conversations={[]}
        portraitUrlsBySlug={{}}
        loading={true}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('Loading…')).toBeTruthy()
  })

  it('renders error state with retry button', () => {
    const retry = vi.fn()
    render(
      <ConversationList
        conversations={[]}
        portraitUrlsBySlug={{}}
        loading={false}
        error={new Error('Network error')}
        onRetry={retry}
      />,
    )
    expect(screen.getByText(/Couldn't load/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(retry).toHaveBeenCalled()
  })

  it('renders empty state when conversations array is empty', () => {
    render(
      <ConversationList
        conversations={[]}
        portraitUrlsBySlug={{}}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('Past conversations gather here.')).toBeTruthy()
  })

  it('renders populated conversations', () => {
    const convs = [makeConv('a', 1), makeConv('b', 10)]
    render(
      <ConversationList
        conversations={convs}
        portraitUrlsBySlug={{}}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getAllByText('Epictetus')).toBeTruthy()
  })

  it('groups this-week conversations under "This week"', () => {
    const convs = [makeConv('a', 1)] // 1 day ago = this week
    render(
      <ConversationList
        conversations={convs}
        portraitUrlsBySlug={{}}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('This week')).toBeTruthy()
  })

  it('groups older conversations under "Earlier"', () => {
    const convs = [makeConv('b', 20)] // 20 days ago = earlier
    render(
      <ConversationList
        conversations={convs}
        portraitUrlsBySlug={{}}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('Earlier')).toBeTruthy()
  })

  it('renders both groups when convs span different weeks', () => {
    const convs = [makeConv('a', 1), makeConv('b', 20)]
    render(
      <ConversationList
        conversations={convs}
        portraitUrlsBySlug={{}}
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('This week')).toBeTruthy()
    expect(screen.getByText('Earlier')).toBeTruthy()
  })
})
