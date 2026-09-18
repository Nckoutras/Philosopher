// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EmptyReflections from '../EmptyReflections'

describe('EmptyReflections', () => {
  // COPY VERIFIED AGAINST THE PRODUCT AND AGAINST THE SPEC, not assumed (TD-45).
  // These four assertions pinned copy from a "§4.3" that no longer governs: the
  // strings survive only in DESIGN_SYSTEM_v4 and SCREENS_TRACKING_v4-v7, all
  // superseded. The current SCREENS_TRACKING_v14 specifies neither string — the
  // empty state is not described there at all — so no live spec contradicts what
  // ships, and this is a test catching up rather than a product regression.
  // The §4.3 citations are dropped from the test names with the copy, because a
  // citation to a superseded document is worse than none.
  it('renders the headline', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('Nothing saved yet.')).toBeTruthy()
  })

  it('renders the body copy', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText(/When a reply lands, tap Save line below it/)).toBeTruthy()
  })

  it('renders 3-item instruction list', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('Save what resonates')).toBeTruthy()
    expect(screen.getByText('Group by mind or theme')).toBeTruthy()
    expect(screen.getByText('Return when you need them')).toBeTruthy()
  })

  it('renders the CTA', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('Choose a mind')).toBeTruthy()
  })

  it('calls onStartConversation when CTA tapped', () => {
    const fn = vi.fn()
    render(<EmptyReflections onStartConversation={fn} />)
    fireEvent.click(screen.getByText('Choose a mind'))
    expect(fn).toHaveBeenCalledOnce()
  })
})
