// @vitest-environment jsdom
//
// TD-87. The page guarded on `authed` alone and the profile card read `user`
// bare, so `authed && !user` threw on the page that holds cancellation, export
// and deletion. store.setAuth / clearAuth write `user` and `token` together, so
// that state should not occur; if it does (a partial or hand-edited
// localStorage), the page holds on its placeholder instead of throwing.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import AccountPage from '../page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))

// Session present, so the page gets past the `authed` half of the guard.
vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(api, 'getSubscription').mockImplementation(() => new Promise(() => {}))
})

describe('Account with a session but no user', () => {
  it('renders the placeholder instead of throwing', () => {
    useStore.setState({ user: null, token: 'tok', subscription: null })

    const { container } = render(<AccountPage />)

    expect(screen.queryByText('Your account.')).toBeNull()
    expect(container.querySelector('main')).toBeNull()
    expect(container.firstElementChild?.className).toContain('bg-vellum')
  })

  it('renders the page once the user is present', () => {
    useStore.setState({
      user: { id: 'user-1', email: 'reader@example.com', full_name: 'A Reader' } as never,
      token: 'tok',
      subscription: null,
    })

    render(<AccountPage />)

    expect(screen.getByText('Your account.')).toBeTruthy()
  })
})
