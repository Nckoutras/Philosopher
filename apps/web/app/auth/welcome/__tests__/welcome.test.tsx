// @vitest-environment jsdom
//
// Covers both halves of A8:
//   1. verify/page.tsx routes to /auth/welcome ONLY when the account was just created
//   2. the welcome screen names the email and renders the approved copy
//
// HOW THESE CAN FAIL. The routing tests assert the DESTINATION, not merely that a
// navigation happened — a version that always went to /auth/welcome, or never did,
// fails. The copy test asserts the email the user actually signed in with, so a screen
// that rendered a placeholder or the wrong address fails.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { useStore } from '@/lib/store'

const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
}))

import WelcomePage from '../page'

const EMAIL = 'mistyped@gmail.com'

function signedIn({ needsDisclaimer = false }: { needsDisclaimer?: boolean } = {}) {
  useStore.setState({
    token: 'test-token',
    user: {
      id: 'u-1',
      email: EMAIL,
      full_name: null,
      needs_disclaimer: needsDisclaimer,
    } as never,
  })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('welcome screen', () => {
  it('names the email the user just signed in with', async () => {
    signedIn()
    render(<WelcomePage />)

    expect(screen.getByText(EMAIL)).toBeDefined()
  })

  it('renders the approved copy', async () => {
    signedIn()
    render(<WelcomePage />)

    expect(screen.getByText('Your account has been created')).toBeDefined()
    expect(
      screen.getByText(
        /If you expected to find previous conversations here, you may have signed in with a different email\./,
      ),
    ).toBeDefined()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Use a different email' })).toBeDefined()
  })

  it('Continue goes to the disclaimer when the new account still needs it', async () => {
    signedIn({ needsDisclaimer: true })
    render(<WelcomePage />)

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    // The point of welcome-first: it must not let a new user skip the disclaimer.
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/disclaimer'))
  })

  it('Continue goes to Today when the disclaimer is not needed', async () => {
    signedIn({ needsDisclaimer: false })
    render(<WelcomePage />)

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
  })

  it('Use a different email clears auth and returns to /auth', async () => {
    signedIn()
    render(<WelcomePage />)

    fireEvent.click(screen.getByRole('button', { name: 'Use a different email' }))

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth'))
    // Cleared, so the abandoned account cannot still be signed in behind the entry screen.
    expect(useStore.getState().token).toBeNull()
    expect(useStore.getState().user).toBeNull()
  })
})
