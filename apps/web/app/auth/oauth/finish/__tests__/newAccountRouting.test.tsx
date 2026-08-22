// @vitest-environment jsdom
//
// oauth/finish must send a user to /auth/welcome ONLY when the callback CREATED the
// account, and to the pre-existing destinations otherwise (A8b).
//
// HOW THESE CAN FAIL. Every case asserts the exact DESTINATION, so a version that always
// routes to /auth/welcome fails cases 2 and 3, and one that never routes there fails
// case 1. Asserting only "replace was called" would pass under all of them.
//
// Case 4 pins the absent-parameter behaviour: `new_account` is read with `=== '1'`, so a
// redirect from a backend that does not send it must behave exactly as before A8b. That
// is the frontend half of the guarantee the "0"/"1" convention carries.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

const mockReplace = vi.fn()
let search = ''

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  useSearchParams: () => new URLSearchParams(search),
}))

import OAuthFinishPage from '../page'

const EMAIL = 'picked-the-wrong-one@gmail.com'

function arrive(params: Record<string, string>, { needsDisclaimer = false } = {}) {
  search = new URLSearchParams({ token: 'tok', ...params }).toString()

  vi.spyOn(api, 'setToken').mockImplementation(() => {})
  vi.spyOn(api, 'me').mockResolvedValue({
    id: 'u-1',
    email: EMAIL,
    full_name: null,
    needs_disclaimer: needsDisclaimer,
  } as never)

  render(<OAuthFinishPage />)
}

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: null, user: null })
})

describe('oauth/finish → post-callback routing', () => {
  it('routes a JUST-CREATED account to /auth/welcome', async () => {
    // needs_disclaimer is 1 as well, to prove the new-account branch wins: the user
    // learns about the account before being asked to accept anything.
    arrive({ new_account: '1', needs_disclaimer: '1' }, { needsDisclaimer: true })

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/welcome'))
  })

  it('routes an existing user needing the disclaimer to /auth/disclaimer', async () => {
    arrive({ new_account: '0', needs_disclaimer: '1' }, { needsDisclaimer: true })

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/disclaimer'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })

  it('routes an existing, already-accepted user straight to /app/today', async () => {
    arrive({ new_account: '0', needs_disclaimer: '0' })

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })

  it('treats an ABSENT new_account as not-new', async () => {
    arrive({ needs_disclaimer: '0' })

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })

  it('populates the store BEFORE navigating — the order /auth/welcome depends on', async () => {
    // /auth/welcome reads needs_disclaimer from the STORE. If setAuth moved after the
    // navigation, welcome would read an empty store and send every new Google user to
    // /app/today, skipping the disclaimer. This pins the ordering.
    arrive({ new_account: '1', needs_disclaimer: '1' }, { needsDisclaimer: true })

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/welcome'))

    const state = useStore.getState()
    expect(state.token).toBe('tok')
    expect(state.user?.email).toBe(EMAIL)
    expect(state.user?.needs_disclaimer).toBe(true)
  })
})
