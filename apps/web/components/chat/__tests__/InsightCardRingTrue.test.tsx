// @vitest-environment jsdom
//
// The verdict row on the insight card (Γ-2).
//
// TWO THINGS ARE GUARDED, and they are different in kind.
//
// 1. COVERAGE. The row must render for EVERY insight type and regardless of tier.
//    The card already branches heavily by type — the primary label changes, and
//    'Doubt this' is hidden for belief and aspiration — so "renders for one type"
//    would prove nothing about the other four. Correcting a claim the product
//    made about you is not type-specific.
//
// 2. COPY. Founder-locked and shared with two shipped surfaces (Mirror,
//    You-vs-You). Exact strings, asserted per label, because a paraphrase is the
//    failure mode a "some buttons rendered" test waves through.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { api } from '@/lib/api'
import InsightCard from '../InsightCard'

const ID = 'cccccccc-0000-0000-0000-000000000003'
const TYPES = ['pattern', 'shift', 'dilemma', 'belief', 'aspiration', null]

function renderCard(props: Partial<React.ComponentProps<typeof InsightCard>> = {}) {
  return render(
    <InsightCard
      insightId={ID}
      content="You keep returning to the same decision."
      insightType="pattern"
      onPrimary={vi.fn()}
      onDoubt={vi.fn()}
      onDiscard={vi.fn()}
      {...props}
    />,
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'setInsightRingTrue').mockResolvedValue({} as never)
})

describe('the verdict row renders everywhere', () => {
  it.each(TYPES)('renders for insight_type=%s', (insightType) => {
    renderCard({ insightType })
    expect(screen.getByText('Does this ring true?')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Rings true' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Partly' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'No' })).toBeTruthy()
  })

  it('renders it even for the types that hide Doubt this', () => {
    // belief and aspiration lose a door; they must not lose the verdict with it.
    for (const insightType of ['belief', 'aspiration']) {
      const { unmount } = renderCard({ insightType })
      expect(screen.queryByRole('button', { name: 'Doubt this' })).toBeNull()
      expect(screen.getByText('Does this ring true?')).toBeTruthy()
      unmount()
    }
  })

  it('uses the founder-locked labels and no others', () => {
    renderCard()
    expect(screen.queryByText('Not really')).toBeNull()
    expect(screen.queryByText('Yes')).toBeNull()
  })
})

describe('answering', () => {
  it.each(['yes', 'partly', 'no'] as const)('sends %s and confirms', async (verdict) => {
    const label = { yes: 'Rings true', partly: 'Partly', no: 'No' }[verdict]
    renderCard()

    fireEvent.click(screen.getByRole('button', { name: label }))

    await waitFor(() => expect(api.setInsightRingTrue).toHaveBeenCalledWith(ID, verdict))
    expect(screen.getByText('Noted.')).toBeTruthy()
  })

  it('does not dismiss or navigate when answering', () => {
    // The verdict is a reply to the claim, not a door. A 'no' that also removed
    // the card would make disagreement indistinguishable from discarding — and
    // would widen the 6h throttle server-side.
    const onDiscard = vi.fn()
    const onPrimary = vi.fn()
    const onDoubt = vi.fn()
    renderCard({ onDiscard, onPrimary, onDoubt })

    fireEvent.click(screen.getByRole('button', { name: 'No' }))

    expect(onDiscard).not.toHaveBeenCalled()
    expect(onPrimary).not.toHaveBeenCalled()
    expect(onDoubt).not.toHaveBeenCalled()
    expect(screen.getByText('You keep returning to the same decision.')).toBeTruthy()
  })

  it('shows an already-answered verdict as selected, without asking again', () => {
    renderCard({ ringTrue: 'partly' })
    expect(screen.getByRole('button', { name: 'Partly' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Rings true' }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Noted.')).toBeTruthy()
  })

  it('rolls back when the write fails', async () => {
    // The card must never claim an answer the server did not store — the row is
    // the only memory of it, and these surfaces are stateless.
    vi.spyOn(api, 'setInsightRingTrue').mockRejectedValue(new Error('offline'))
    renderCard()

    fireEvent.click(screen.getByRole('button', { name: 'No' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'No' }).getAttribute('aria-pressed')).toBe('false'),
    )
    expect(screen.queryByText('Noted.')).toBeNull()
  })
})
