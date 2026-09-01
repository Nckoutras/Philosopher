// @vitest-environment jsdom
//
// Consent must be withdrawable from the Account page — the privacy policy now
// says so in §8, so this is a compliance surface, not a convenience.
//
// HOW THESE CAN FAIL. Case 2 asserts opt_out_capturing is reached via
// optOutAnalytics, so a toggle that only flipped local state (leaving the SDK
// capturing and its cookie in place) fails it while still looking correct on
// screen. Case 1 pins that the row reflects STORED consent rather than a
// default — a toggle that always rendered Off would fail it.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { getConsent, setConsent, initAnalytics, optOutAnalytics } from '@/lib/analytics'
import AccountPage from '../page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics')
  return {
    ...actual,
    initAnalytics: vi.fn(async () => {}),
    optOutAnalytics: vi.fn(),
  }
})

const USER = {
  id: 'user-1',
  email: 'reader@example.com',
  full_name: 'A Reader',
  avatar_url: null,
  is_admin: false,
  onboarded_at: null,
  created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  useStore.setState({ user: USER, token: 'tok', subscription: null })
  vi.spyOn(api, 'getSubscription').mockResolvedValue({
    plan: 'free',
    status: 'active',
  } as unknown as Awaited<ReturnType<typeof api.getSubscription>>)
})

async function renderAccount() {
  render(<AccountPage />)
  return screen.findByRole('switch', { name: 'Analytics' })
}

describe('Account — analytics toggle', () => {
  it('reflects the stored choice rather than a default', async () => {
    setConsent('granted')
    const toggle = await renderAccount()

    expect(toggle.getAttribute('aria-checked')).toBe('true')
    expect(screen.getByText('On')).toBeTruthy()
  })

  it('switching off opts out of capturing and drops the cookie', async () => {
    setConsent('granted')
    const toggle = await renderAccount()
    fireEvent.click(toggle)

    await waitFor(() => {
      expect(getConsent()).toBe('denied')
      // Not merely a stored 'denied' — the live SDK must be stopped too.
      expect(optOutAnalytics).toHaveBeenCalledTimes(1)
      expect(screen.getByText('Off')).toBeTruthy()
    })
  })

  it('switching on stores consent and starts the SDK', async () => {
    setConsent('denied')
    const toggle = await renderAccount()
    expect(toggle.getAttribute('aria-checked')).toBe('false')

    fireEvent.click(toggle)

    await waitFor(() => {
      expect(getConsent()).toBe('granted')
      expect(initAnalytics).toHaveBeenCalledTimes(1)
      expect(screen.getByText('On')).toBeTruthy()
    })
  })

  it('shows Off when no choice has been made', async () => {
    const toggle = await renderAccount()
    expect(toggle.getAttribute('aria-checked')).toBe('false')
    expect(optOutAnalytics).not.toHaveBeenCalled()
    expect(initAnalytics).not.toHaveBeenCalled()
  })
})
