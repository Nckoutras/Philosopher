// @vitest-environment jsdom
//
// The coverage label must render the API's authoritative category counts, NOT a count
// derived from the tier-filtered `questions` the client happens to hold.
//
// HOW THIS TEST CAN FAIL. The fixture is deliberately rigged so the two numbers
// DISAGREE: the API reports 10 covered categories, while the questions/answers in the
// same payload cover only 2. A client-side derivation renders "2 από 12"; reading the
// API field renders "10 από 12". Asserting merely that a label exists would pass under
// both, so the assertion is on the number itself.
//
// That disagreement is not artificial — it is exactly the lapsed Pro->free shape: the
// user answered 10 categories while Pro, and their current tier can only see questions
// from 2 of them.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// fireEvent, not user-event: @testing-library/user-event is not a dependency of this
// app and adding one is out of scope for this change. A plain click is enough here.
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import SelfPortraitPage from '../page'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

// Heavy leaf components — not under test, and mounting them pulls in canvas/blob work.
vi.mock('@/components/self-portrait/PortraitRadar', () => ({ PortraitRadar: () => null }))
vi.mock('@/components/self-portrait/PortraitMap', () => ({ PortraitMap: () => null }))

const API_ANSWERED_CATEGORIES = 10
const API_TOTAL_CATEGORIES = 12

// Two questions, both in categories the tier can still see, both answered.
// Client-derived coverage from this set = 2, which must NOT be what renders.
const questions = [
  { id: 'identity_001', category: 'identity', question: 'q1', pills: ['a', 'b'] },
  { id: 'money_001', category: 'money', question: 'q2', pills: ['a', 'b'] },
]

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'test-token', user: { full_name: 'Test User' } as never })
  vi.spyOn(api, 'getSelfPortrait').mockResolvedValue({
    questions,
    answers: { identity_001: 0, money_001: 1 },
    is_pro: false,
    locked_count: 345,
    answered_category_count: API_ANSWERED_CATEGORIES,
    total_category_count: API_TOTAL_CATEGORIES,
  } as never)
  vi.spyOn(api, 'getSelfPortraitPortrait').mockRejectedValue(new Error('not needed'))
})

async function openQuestionsView() {
  render(<SelfPortraitPage />)
  // The entry view renders first; the coverage header lives in the questions view.
  const enter = await screen.findByRole('button', { name: /Continue the questions|Start the journey/ })
  fireEvent.click(enter)
}

describe('Self-Portrait coverage label', () => {
  it('renders the API category counts, not a client-derived count', async () => {
    await openQuestionsView()

    await waitFor(() => {
      expect(
        screen.getByText(`${API_ANSWERED_CATEGORIES} από ${API_TOTAL_CATEGORIES} θεματικές`),
      ).toBeDefined()
    })
  })

  it('does not render the count derived from tier-filtered questions', async () => {
    await openQuestionsView()

    await waitFor(() => {
      expect(screen.getByText(/θεματικές/)).toBeDefined()
    })
    // 2 = the client-derived value this change exists to stop trusting.
    expect(screen.queryByText(`2 από ${API_TOTAL_CATEGORIES} θεματικές`)).toBeNull()
  })
})
