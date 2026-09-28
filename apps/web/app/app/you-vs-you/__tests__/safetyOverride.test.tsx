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

// SAFETY-003 part 2 (founder ruling 2026-09-28, Option A): the crisis state shows
// the server's crisis text ALONE, in the app-voice bubble, with its resources
// tappable. It replaced "Let’s set this one aside for now.", which named no help.
// The first test below used to assert that line; it now asserts what replaced it.
const CRISIS =
  "Some of what you've shared sounds heavy, and your safety matters more than this conversation.\n\n" +
  'In the US, call or text 988. In the UK and Ireland, call Samaritans on 116 123. ' +
  'Anywhere else, find a free, confidential helpline at findahelpline.com.'

describe('You vs You — a self answer withheld after it streamed', () => {
  it('drops the streamed answer and shows the crisis text alone', async () => {
    await ask([
      { type: 'self', which: 'then', start: '2026-06-01', end: '2026-07-01' },
      { type: 'chunk', which: 'then', data: HARMFUL },
      { type: 'safety_override', level: 'high', text: CRISIS },
      { type: 'chunk', which: 'safety', data: CRISIS },
      { type: 'done' },
    ])
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe(CRISIS)   // once: the chunk after the event is not appended
    expect(screen.queryByText(HARMFUL)).toBeNull()
    expect(screen.queryByText('Let’s set this one aside for now.')).toBeNull()
  })

  // The crisis gate (ruling 2026-09-25): a high/critical message in the last 14
  // days refuses before anything is generated. Approved copy, and it names no
  // reason — support routing already happened where the flag was raised.
  // UNCHANGED by SAFETY-003: it carries no crisis text and keeps its own line.
  it('shows the approved line when a recent crisis closes the comparison', async () => {
    await ask([{ type: 'safety', level: 'recent' }, { type: 'done' }])
    expect(await screen.findByText('Let’s leave this comparison for another day.')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('leaves a clean run alone', async () => {
    await ask([
      { type: 'self', which: 'then', start: '2026-06-01', end: '2026-07-01' },
      { type: 'chunk', which: 'then', data: 'You asked whether you could afford to go.' },
      { type: 'done' },
    ])
    expect(await screen.findByText('You asked whether you could afford to go.')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })
})

describe('You vs You — a crisis prompt (SAFETY-003 part 2)', () => {
  it('shows the crisis text from the event, with no chunk ever arriving', async () => {
    await ask([{ type: 'safety', level: 'high', text: CRISIS }])
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe(CRISIS)
    expect(screen.getByRole('link', { name: '988' }).getAttribute('href')).toBe('tel:988')
    expect(screen.getByRole('link', { name: '116 123' }).getAttribute('href')).toBe('tel:116123')
    expect(screen.getByRole('link', { name: 'findahelpline.com' }).getAttribute('href'))
      .toBe('https://findahelpline.com')
  })

  it('still fills from the safety chunk when the event has no text (an older server)', async () => {
    await ask([
      { type: 'safety', level: 'high' },
      { type: 'chunk', which: 'safety', data: CRISIS },
      { type: 'done' },
    ])
    expect((await screen.findByRole('alert')).textContent).toBe(CRISIS)
  })

  it('offers no "Ask another" on the crisis state — the crisis text stands alone', async () => {
    await ask([{ type: 'safety', level: 'high', text: CRISIS }])
    await screen.findByRole('alert')
    expect(screen.queryByRole('button', { name: 'Ask another' })).toBeNull()
  })

  it('still offers "Ask another" after a clean run', async () => {
    await ask([
      { type: 'self', which: 'then', start: '2026-06-01', end: '2026-07-01' },
      { type: 'chunk', which: 'then', data: 'You asked whether you could afford to go.' },
      { type: 'done' },
    ])
    expect(await screen.findByRole('button', { name: 'Ask another' })).toBeTruthy()
  })
})
