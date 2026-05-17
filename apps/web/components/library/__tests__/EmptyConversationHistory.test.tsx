// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EmptyConversationHistory from '../EmptyConversationHistory'

const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

beforeEach(() => {
  mockPush.mockClear()
})

describe('EmptyConversationHistory', () => {
  it('renders headline', () => {
    render(<EmptyConversationHistory />)
    expect(screen.getByText('Past conversations gather here.')).toBeTruthy()
  })

  it('renders body copy', () => {
    render(<EmptyConversationHistory />)
    expect(
      screen.getByText(/Every conversation you start is saved here/),
    ).toBeTruthy()
  })

  it('renders all 3 instruction items', () => {
    render(<EmptyConversationHistory />)
    expect(screen.getByText('Saved automatically')).toBeTruthy()
    expect(screen.getByText('Resume where you left off')).toBeTruthy()
    expect(screen.getByText('Organized by recency')).toBeTruthy()
  })

  it('renders CTA with correct label', () => {
    render(<EmptyConversationHistory />)
    expect(screen.getByRole('button', { name: 'Explore minds' })).toBeTruthy()
  })

  it('CTA navigates to /app/explore on click', () => {
    render(<EmptyConversationHistory />)
    fireEvent.click(screen.getByRole('button', { name: 'Explore minds' }))
    expect(mockPush).toHaveBeenCalledWith('/app/explore')
  })
})
