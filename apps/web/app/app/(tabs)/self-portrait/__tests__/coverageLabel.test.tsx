// @vitest-environment jsdom
//
// The coverage label must render the API's authoritative category counts, NOT a count
// derived from the tier-filtered `questions` the client happens to hold.
//
// HOW THIS TEST CAN FAIL. The fixture is deliberately rigged so the two numbers
// DISAGREE: the API reports 10 covered categories, while the questions/answers in the
// same payload cover only 2. A client-side derivation renders "2 of 12"; reading the
// API field renders "10 of 12". Asserting merely that a label exists would pass under
// both, so the assertion is on the number itself.
//
// That disagreement is not artificial — it is exactly the lapsed Pro->free shape: the
// user answered 10 categories while Pro, and their current tier can only see questions
// from 2 of them.
//
// AMENDED, NOT GREEN-ED (BUG-016). The three assertions below previously pinned the
// label in GREEK ("10 από 12 θεματικές") — the one Greek string left in an English UI,
// in an app with no i18n system at all: no locale files, no library, <html lang="en">.
// The string changed in page.tsx, so the assertion changed with it, in the same commit.
// Nothing was relaxed to make it pass: the rigged 10-vs-2 fixture is untouched and both
// assertions still turn on the NUMBER, which is what this file exists to guard.
//
// One assertion was also TIGHTENED while it was open. The presence check used a bare
// /θεματικές/ regex; the English equivalent /themes/ would also match the "CURRENT
// THEME" label the questions view renders further down (page.tsx:739), so it would pass
// for the wrong reason on a page where the coverage label had vanished entirely. It is
// now the exact full string.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// fireEvent, not user-event: @testing-library/user-event is not a dependency of this
// app and adding one is out of scope for this change. A plain click is enough here.
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import SelfPortraitPage from '../page'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  // The page reads usePathname for the Pro link's returnTo (BUG-003). A mock
  // that omits a hook the component calls does not fail as "missing mock" -- it
  // throws inside render, which reads as the component being broken.
  usePathname: () => '/app/self-portrait',
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

// Every field the page reads, set explicitly (C-06). `answers` is the only axis the
// count tests vary; leaving the rest here keeps each override honest about what it
// is actually changing.
function mockPortrait(overrides: { questions?: unknown[]; answers?: Record<string, number> } = {}) {
  vi.spyOn(api, 'getSelfPortrait').mockResolvedValue({
    questions: overrides.questions ?? questions,
    answers: overrides.answers ?? { identity_001: 0, money_001: 1 },
    is_pro: false,
    locked_count: 345,
    answered_category_count: API_ANSWERED_CATEGORIES,
    total_category_count: API_TOTAL_CATEGORIES,
  } as never)
  // Rejected on purpose: with no portrait, `state` is never 'ready', so the progress
  // line is deterministically "Portrait forming" and the count is the only variable.
  vi.spyOn(api, 'getSelfPortraitPortrait').mockRejectedValue(new Error('not needed'))
}

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'test-token', user: { full_name: 'Test User' } as never })
  mockPortrait()
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
        screen.getByText(`${API_ANSWERED_CATEGORIES} of ${API_TOTAL_CATEGORIES} themes`),
      ).toBeDefined()
    })
  })

  it('does not render the count derived from tier-filtered questions', async () => {
    await openQuestionsView()

    await waitFor(() => {
      expect(
        screen.getByText(`${API_ANSWERED_CATEGORIES} of ${API_TOTAL_CATEGORIES} themes`),
      ).toBeDefined()
    })
    // 2 = the client-derived value this change exists to stop trusting.
    expect(screen.queryByText(`2 of ${API_TOTAL_CATEGORIES} themes`)).toBeNull()
  })
})

// BUG-016, second half: the progress line read "1 answers" at exactly one answer.
// The count is the user's own answer total, so 1 is not an edge case — it is the
// state every single person passes through, once, on their first answer.
describe('Self-Portrait answer-count label', () => {
  const threeQuestions = [
    { id: 'identity_001', category: 'identity', question: 'q1', pills: ['a', 'b'] },
    { id: 'money_001', category: 'money', question: 'q2', pills: ['a', 'b'] },
    { id: 'work_001', category: 'work', question: 'q3', pills: ['a', 'b'] },
  ]

  it('says "0 answers" before the first answer', async () => {
    mockPortrait({ questions: threeQuestions, answers: {} })
    await openQuestionsView()

    await waitFor(() => {
      expect(screen.getByText('Portrait forming · 0 answers')).toBeDefined()
    })
  })

  it('says "1 answer", singular, at exactly one', async () => {
    mockPortrait({ questions: threeQuestions, answers: { identity_001: 0 } })
    await openQuestionsView()

    await waitFor(() => {
      expect(screen.getByText('Portrait forming · 1 answer')).toBeDefined()
    })
    // The bug this test exists for. Asserting the singular alone would still pass if
    // some future change rendered both forms, so the plural is pinned absent too.
    expect(screen.queryByText('Portrait forming · 1 answers')).toBeNull()
  })

  it('says "3 answers", plural, at many', async () => {
    mockPortrait({
      questions: threeQuestions,
      answers: { identity_001: 0, money_001: 1, work_001: 0 },
    })
    await openQuestionsView()

    await waitFor(() => {
      expect(screen.getByText('Portrait forming · 3 answers')).toBeDefined()
    })
  })
})
