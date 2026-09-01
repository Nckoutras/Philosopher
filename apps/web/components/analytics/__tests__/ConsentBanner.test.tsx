// @vitest-environment jsdom
//
// The UI half of the consent gate. lib/__tests__/analytics.test.ts pins the
// module contract; this pins that the banner is actually wired to it — that
// Accept starts the SDK in the same gesture, and that No thanks starts nothing.
//
// HOW THESE CAN FAIL. A banner whose buttons only set state without calling
// initAnalytics fails case 2. One that called initAnalytics on both branches
// fails case 3. A parent that rendered the banner regardless of stored choice
// fails the AnalyticsProvider cases.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { getConsent, setConsent, initAnalytics } from '@/lib/analytics'
import ConsentBanner from '../ConsentBanner'
import AnalyticsProvider from '../AnalyticsProvider'

vi.mock('@/lib/analytics', async () => {
  // Keep the real consent storage — the banner's job is to write it — and mock
  // only the SDK-facing calls.
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics')
  return {
    ...actual,
    initAnalytics: vi.fn(async () => {}),
    identify: vi.fn(),
  }
})

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(''),
}))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

describe('ConsentBanner', () => {
  it('renders the approved copy and two actions', () => {
    render(<ConsentBanner onChoice={vi.fn()} />)
    expect(screen.getByText(/We['’]d like to measure what['’]s working\./)).toBeTruthy()
    expect(
      screen.getByText(/^Usage analytics, EU-hosted, never your conversations/),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Accept' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'No thanks' })).toBeTruthy()
    // Never "Anonymous": once identify() fires the data is pseudonymous, not
    // anonymous, and the notice must not claim otherwise.
    expect(screen.queryByText(/Anonymous/i)).toBeNull()
  })

  it('Accept stores consent and starts the SDK', async () => {
    const onChoice = vi.fn()
    render(<ConsentBanner onChoice={onChoice} />)
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    await waitFor(() => {
      expect(getConsent()).toBe('granted')
      expect(initAnalytics).toHaveBeenCalledTimes(1)
      expect(onChoice).toHaveBeenCalledWith('granted')
    })
  })

  it('No thanks stores the refusal and starts nothing', async () => {
    const onChoice = vi.fn()
    render(<ConsentBanner onChoice={onChoice} />)
    fireEvent.click(screen.getByRole('button', { name: 'No thanks' }))

    await waitFor(() => {
      expect(getConsent()).toBe('denied')
      expect(onChoice).toHaveBeenCalledWith('denied')
    })
    expect(initAnalytics).not.toHaveBeenCalled()
  })
})

describe('AnalyticsProvider', () => {
  it('shows the banner when no choice is stored', async () => {
    render(<AnalyticsProvider />)
    expect(await screen.findByRole('button', { name: 'Accept' })).toBeTruthy()
  })

  it('does not show the banner once a choice exists, and re-inits on granted', async () => {
    setConsent('granted')
    render(<AnalyticsProvider />)

    await waitFor(() => expect(initAnalytics).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: 'Accept' })).toBeNull()
  })

  it('does not show the banner or init after a stored decline', async () => {
    setConsent('denied')
    render(<AnalyticsProvider />)

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Accept' })).toBeNull()
    })
    expect(initAnalytics).not.toHaveBeenCalled()
  })

  it('dismisses the banner after a choice without a reload', async () => {
    render(<AnalyticsProvider />)
    fireEvent.click(await screen.findByRole('button', { name: 'No thanks' }))

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'No thanks' })).toBeNull()
    })
  })
})
