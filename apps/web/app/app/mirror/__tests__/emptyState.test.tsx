// @vitest-environment jsdom
//
// BUG-021 residue — the Mirror empty state.
//
// It read "Keep talking with the minds — the mirror gathers what matters": no
// threshold, no timing, and the same words for two opposite situations. A reader who
// qualifies and is waiting up to an hour, and a reader who does not yet qualify, saw
// identical output.
//
// ONE TEST PER STATE WAS ASKED FOR. There is ONE state, and that is the finding:
// GET /mirrors/latest returns MirrorOut | None, one bit, and the page loads nothing
// else bearing on eligibility. So these assert what the single rendered state must
// say — a condition and a timing — rather than pretending to a distinction the page
// cannot make.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => '/app/mirror',
  useSearchParams: () => new URLSearchParams(),
}))
vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }),
}))
vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}))

import MirrorPage from '../page'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'test-token', user: { full_name: 'T' } as never })
  // No mirror yet — the only signal the endpoint gives, and the state under test.
  vi.spyOn(api, 'getLatestMirror').mockResolvedValue(null as never)
  vi.spyOn(api, 'getPersonas').mockResolvedValue([] as never)
})

describe('the Mirror empty state', () => {
  it('names the condition, so a reader who does not qualify knows what is missing', async () => {
    render(<MirrorPage />)
    await waitFor(() => {
      expect(
        screen.getByText(/It takes about three conversations before there is enough to reflect on/),
      ).toBeTruthy()
    })
  })

  it('names the timing, so a reader who DOES qualify knows the wait is bounded', async () => {
    // The hourly preview cron is the real bound. Without this, a qualifying reader
    // waits up to an hour with no way to tell whether the system is working.
    render(<MirrorPage />)
    await waitFor(() => {
      expect(screen.getByText(/usually appears within the hour/)).toBeTruthy()
    })
  })

  it('mentions the weekly path too, since a first mirror can arrive by either', async () => {
    render(<MirrorPage />)
    await waitFor(() => {
      expect(screen.getByText(/a fuller one each Monday/)).toBeTruthy()
    })
  })

  it('does not carry the old copy, which said neither', async () => {
    render(<MirrorPage />)
    await waitFor(() => {
      expect(screen.getByText(/three conversations/)).toBeTruthy()
    })
    expect(screen.queryByText(/the mirror gathers what matters/)).toBeNull()
  })

  it('invents no numbers: exactly the thresholds the cron actually uses', async () => {
    // workers/cron.py:277 — hourly, >=3 active conversations in 72h.
    // workers/cron.py:238 — Mondays, >=5 user messages in 7 days.
    // "three" and "Monday" and "the hour" are those. Nothing else numeric belongs
    // here, and "minds" in particular would be a number nobody measured: the
    // threshold counts distinct CONVERSATIONS, which can be with one persona.
    const { container } = render(<MirrorPage />)
    await waitFor(() => {
      expect(screen.getByText(/three conversations/)).toBeTruthy()
    })
    const body = container.textContent ?? ''
    expect(body).not.toMatch(/three minds/i)
    expect(body).not.toMatch(/06:00|UTC/)
    // No progress language — this is a reflective product, not a game.
    expect(body).not.toMatch(/\b\d+\s*(of|\/)\s*\d+\b/)
  })

  it('still offers the way back', async () => {
    render(<MirrorPage />)
    await waitFor(() => {
      expect(screen.getByText('Back to rituals')).toBeTruthy()
    })
  })
})
