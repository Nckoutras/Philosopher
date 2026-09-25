// @vitest-environment jsdom
//
// You-vs-You post-generation safety (founder ruling 2026-09-24, the TD-101 pattern).
// The server checks each self's answer after it has streamed and, on a positive,
// sends `safety_override`. The page must drop the answer it already typed out and
// show its safety line, exactly as it does for the input-side `safety` event.
// Without the override case the harmful text would stay on screen.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { api } from '@/lib/api'
import YouVsYouPage from '../page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))
vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))

const HARMFUL = 'A lethal dose is closer than you think.'

function sse(events: object[]): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new Response(new ReadableStream({
    start(c) { c.enqueue(new TextEncoder().encode(body)); c.close() },
  }))
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(api, 'getSelfComparisonStatus').mockResolvedValue({
    unlocked: true, total_signals: 30, reason: null, forming_preview: [],
    then: null, now: null, weekly_remaining: 3, weekly_limit: 5, plan: 'pro',
  })
  vi.spyOn(api, 'listSavedLines').mockResolvedValue({ items: [] } as never)
  vi.spyOn(api, 'listSelfComparisons').mockResolvedValue([])
})

async function ask(events: object[]) {
  vi.spyOn(api, 'streamSelfComparison').mockResolvedValue(sse(events))
  render(<YouVsYouPage />)
  const box = await screen.findByPlaceholderText(/Ask both of you something/)
  fireEvent.change(box, { target: { value: 'What am I afraid of?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask both selves' }))
}

describe('You vs You — a self answer withheld after it streamed', () => {
  it('drops the streamed answer and shows the safety line', async () => {
    await ask([
      { type: 'self', which: 'then', start: '2026-06-01', end: '2026-07-01' },
      { type: 'chunk', which: 'then', data: HARMFUL },
      { type: 'safety_override', level: 'high' },
      { type: 'chunk', which: 'safety', data: 'If you are in danger, please reach out.' },
      { type: 'done' },
    ])
    expect(await screen.findByText('Let’s set this one aside for now.')).toBeTruthy()
    expect(screen.queryByText(HARMFUL)).toBeNull()
  })

  it('leaves a clean run alone', async () => {
    await ask([
      { type: 'self', which: 'then', start: '2026-06-01', end: '2026-07-01' },
      { type: 'chunk', which: 'then', data: 'You asked whether you could afford to go.' },
      { type: 'done' },
    ])
    expect(await screen.findByText('You asked whether you could afford to go.')).toBeTruthy()
    expect(screen.queryByText('Let’s set this one aside for now.')).toBeNull()
  })
})
