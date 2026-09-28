// @vitest-environment jsdom
//
// SAFETY-003 part 2 (founder ruling 2026-09-28, Option A). When a safety event ends
// the council — a crisis matter, or a member verdict withheld after it streamed —
// the page shows the server's crisis text ALONE, in the app-voice bubble, with its
// resources tappable. It used to show "The council cannot meet on this matter." and
// a "Try a different matter" button: no help of any kind, in any language.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { api } from '@/lib/api'
import CouncilPage from '../page'

// ONE router object, as Next's useRouter returns: the page's load effect depends on
// [authed, router] and its cleanup cancels the animation frame, so a fresh object
// per render would re-run the effect and kill the phase loop before it reached the
// crisis state.
const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() }
vi.mock('next/navigation', () => ({
  useRouter: () => router,
}))
vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))

const CRISIS =
  "Some of what you've shared sounds heavy, and your safety matters more than this conversation.\n\n" +
  'In the US, call or text 988. In the UK and Ireland, call Samaritans on 116 123. ' +
  'Anywhere else, find a free, confidential helpline at findahelpline.com.'

const GREEK =
  'Αν κινδυνεύεις άμεσα, κάλεσε το 112. Στην Ελλάδα: 1018 — Γραμμή Παρέμβασης για την ' +
  'Αυτοκτονία (24 ώρες) · 10306 — Γραμμή Ψυχοκοινωνικής Υποστήριξης (24 ώρες, δωρεάν).'

function sse(events: object[]): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new Response(new ReadableStream({
    start(c) { c.enqueue(new TextEncoder().encode(body)); c.close() },
  }))
}

beforeEach(() => {
  vi.restoreAllMocks()
  // The page advances its phases on requestAnimationFrame; drive it with timers.
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 0) as unknown as number)
  vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id))
  vi.spyOn(api, 'getPersonas').mockResolvedValue([] as never)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function convene(events: object[]) {
  vi.spyOn(api, 'streamCouncil').mockResolvedValue(sse(events))
  render(<CouncilPage />)
  const box = await screen.findByPlaceholderText('What do you want the council to consider?')
  fireEvent.change(box, { target: { value: 'I want to kill myself' } })
  fireEvent.click(screen.getByRole('button', { name: /Convene the council/ }))
}

describe('Council — the crisis state (SAFETY-003 part 2)', () => {
  it('shows the crisis text alone, from the event, with no chunk ever arriving', async () => {
    await convene([{ type: 'safety', level: 'high', text: CRISIS }])

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe(CRISIS)
    expect(screen.getByRole('link', { name: '988' }).getAttribute('href')).toBe('tel:988')
    expect(screen.getByRole('link', { name: '116 123' }).getAttribute('href')).toBe('tel:116123')
    expect(screen.getByRole('link', { name: 'findahelpline.com' }).getAttribute('href'))
      .toBe('https://findahelpline.com')
  })

  it('no longer shows the old line or the "Try a different matter" button', async () => {
    await convene([{ type: 'safety', level: 'high', text: CRISIS }])
    await screen.findByRole('alert')
    expect(screen.queryByText(/The council cannot meet on this matter/)).toBeNull()
    expect(screen.queryByRole('button', { name: /Try a different matter/ })).toBeNull()
  })

  it('does not double the text when the chunks follow as usual', async () => {
    await convene([
      { type: 'safety', level: 'high', text: CRISIS },
      { type: 'chunk', data: CRISIS.slice(0, 30) },
      { type: 'chunk', data: CRISIS.slice(30) },
      { type: 'done' },
    ])
    const alert = await screen.findByRole('alert')
    await waitFor(() => expect(alert.textContent).toBe(CRISIS))
  })

  it('still fills from the chunks when the event has no text (an older server)', async () => {
    await convene([
      { type: 'safety', level: 'high' },
      { type: 'chunk', data: CRISIS.slice(0, 30) },
      { type: 'chunk', data: CRISIS.slice(30) },
      { type: 'done' },
    ])
    await waitFor(() => expect(screen.getByRole('alert').textContent).toBe(CRISIS))
  })

  it('keeps a withheld member verdict out of the crisis text', async () => {
    await convene([
      { type: 'member', slug: 'epictetus', name: 'Epictetus' },
      { type: 'chunk', data: 'A lethal dose is closer than you think.' },
      { type: 'safety_override', level: 'high', text: CRISIS },
      { type: 'chunk', data: CRISIS },
      { type: 'done' },
    ])
    const alert = await screen.findByRole('alert')
    await waitFor(() => expect(alert.textContent).toBe(CRISIS))
    expect(screen.queryByText(/lethal dose/)).toBeNull()
  })

  it('renders the Greek text with its numbers tappable', async () => {
    await convene([{ type: 'safety', level: 'high', text: GREEK }])
    const alert = await screen.findByRole('alert')
    expect(alert.getAttribute('lang')).toBe('el')
    expect(screen.getAllByRole('link').map((a) => a.getAttribute('href')))
      .toEqual(['tel:112', 'tel:1018', 'tel:10306'])
  })
})
