// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SavedLineCard from '../SavedLineCard'
import type { SavedLineRead } from '@/lib/api'

const item: SavedLineRead = {
  id: 'sl-1',
  message_id: 'm-1',
  persona_id: 'p-1',
  persona_slug: 'marcus-aurelius',
  persona_display_name: 'Marcus Aurelius',
  message_content: 'You have power over your mind, not outside events.',
  conversation_id: 'c-1',
  saved_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
  source_type: 'manual',
}

describe('SavedLineCard', () => {
  it('renders message content as quote', () => {
    render(<SavedLineCard item={item} portraitUrl="" onClick={vi.fn()} />)
    expect(screen.getByText('You have power over your mind, not outside events.')).toBeTruthy()
  })

  it('renders persona display name', () => {
    render(<SavedLineCard item={item} portraitUrl="" onClick={vi.fn()} />)
    expect(screen.getByText(/Marcus Aurelius/)).toBeTruthy()
  })

  it('calls onClick when card tapped', () => {
    const fn = vi.fn()
    render(<SavedLineCard item={item} portraitUrl="" onClick={fn} />)
    fireEvent.click(screen.getByRole('button'))
    expect(fn).toHaveBeenCalledOnce()
  })

  it('renders portrait img when portraitUrl provided', () => {
    render(
      <SavedLineCard
        item={item}
        portraitUrl="https://example.com/portrait.jpg"
        onClick={vi.fn()}
      />,
    )
    expect(screen.getByRole('img')).toBeTruthy()
  })

  // VERIFIED against SavedLineCard.tsx, not assumed (TD-45). The fallback at :49-52
  // is unchanged and still correct; what changed is that the card gained a decorative
  // background <Image alt="" aria-hidden> at :31 that renders on every card. The old
  // assertion was `container.querySelector('img')` — ANY img in the subtree — so the
  // decorative one broke a test about the PORTRAIT.
  //
  // queryByRole('img') is the fix and is also the stricter question: the
  // accessibility tree excludes aria-hidden nodes, so this asserts "no portrait is
  // exposed to a reader", which is what the fallback is for. A raw querySelector
  // would have to special-case the decoration and would break again on the next one.
  it('exposes no portrait image when portraitUrl is empty', () => {
    render(<SavedLineCard item={item} portraitUrl="" onClick={vi.fn()} />)
    expect(screen.queryByRole('img')).toBeNull()
  })
})
