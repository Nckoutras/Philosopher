// @vitest-environment jsdom
//
// THE DEFECT THIS PINS (BUG-001 residue). Two things on /app/welcome, and the
// second is the one a user could not escape.
//
// (1) `api.getLastConversation()` had no deadline. While `hasConversations` is
//     null the page renders two grey placeholder divs in the CTA slots. The
//     .catch covered a REJECTION; a HANG left those placeholders inert forever.
//     That is the literal "Begin does nothing" from the 2026-09-14 UAT — not a
//     dead button, a button that was never rendered.
//
// (2) The error state offered only "Try again" → window.location.reload(),
//     which repeats the same failing call. A user whose token is
//     stale-but-present is looped by that: the reload cannot fix the thing that
//     is broken. There was no sign-out and no route anywhere else.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import * as auth from '@/lib/auth'
import WelcomePage from '../page'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
}))
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

// The page's own deadline. A LITERAL, not an import: the point of the boundary
// case is that 10s is the number, not that some number is used.
const TIMEOUT_MS = 10_000

const PERSONA = {
  id: '1', slug: 'lao_tzu', name: 'Lao Tzu', era: null, tradition: null,
  tier: 'free', tagline: 'The way', portrait_url: '/personas/lao_tzu.webp',
  bio: null, is_accessible: true,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({ token: 'a.b.c' })
  vi.spyOn(useStore.persist, 'hasHydrated').mockReturnValue(true)
  vi.spyOn(api, 'getPersonas').mockResolvedValue([PERSONA] as never)
})

afterEach(() => { vi.useRealTimers() })

describe('the hasConversations read', () => {
  it('does not sit on inert placeholders forever when it hangs', async () => {
    vi.useFakeTimers()
    // Never settles — a hung connection, not a rejection.
    vi.spyOn(api, 'getLastConversation').mockImplementation(
      () => new Promise(() => {}) as never,
    )
    render(<WelcomePage />)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })

    // One millisecond short: still waiting, nothing said.
    await act(async () => { vi.advanceTimersByTime(TIMEOUT_MS - 1) })
    expect(screen.queryByText(/Could not load today/i)).toBeNull()

    // The deadline lands, and a hang becomes the handled state.
    await act(async () => { vi.advanceTimersByTime(1) })
    expect(screen.getByText(/Could not load today/i)).toBeTruthy()
  })

  it('does not fire the deadline against a call that came back', async () => {
    vi.useFakeTimers()
    vi.spyOn(api, 'getLastConversation').mockResolvedValue(null as never)
    render(<WelcomePage />)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })

    await act(async () => { vi.advanceTimersByTime(TIMEOUT_MS * 2) })
    expect(screen.queryByText(/Could not load today/i)).toBeNull()
  })
})

describe('the error state', () => {
  it('offers a route out that is not another reload', async () => {
    // THE ASSERTION THIS FILE EXISTS FOR. Reload repeats the failing call, so a
    // stale-but-present token loops here. Sign out does not depend on that call.
    vi.spyOn(api, 'getPersonas').mockRejectedValue(new Error('500'))
    vi.spyOn(api, 'getLastConversation').mockResolvedValue(null as never)
    const signOut = vi.spyOn(auth, 'signOut').mockImplementation(() => {})

    render(<WelcomePage />)
    await waitFor(() => expect(screen.getByText(/Could not load today/i)).toBeTruthy())

    const escape = screen.getByRole('button', { name: /sign in again/i })
    expect(escape).toBeTruthy()
    fireEvent.click(escape)
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('keeps Try again as well — reload is right for a transient failure', async () => {
    vi.spyOn(api, 'getPersonas').mockRejectedValue(new Error('500'))
    vi.spyOn(api, 'getLastConversation').mockResolvedValue(null as never)

    render(<WelcomePage />)
    await waitFor(() => expect(screen.getByText(/Could not load today/i)).toBeTruthy())
    expect(screen.getByRole('button', { name: /try again/i })).toBeTruthy()
  })
})
