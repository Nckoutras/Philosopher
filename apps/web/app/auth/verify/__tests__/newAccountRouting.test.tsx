// @vitest-environment jsdom
//
// verify/page.tsx must send a user to /auth/welcome ONLY when the verification CREATED
// the account, and to the pre-existing destinations otherwise.
//
// HOW THESE CAN FAIL. Each case asserts the exact destination, so a version that always
// routes to /auth/welcome fails case 2 and 3, and one that never routes there fails
// case 1. Asserting only "replace was called" would pass under all three, which is the
// bug this file exists to prevent.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { api } from '@/lib/api'

const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  useSearchParams: () => new URLSearchParams('email=someone%40example.com'),
}))

import VerifyPage from '../page'

const CODE = '123456'

function mockVerify({
  isNewAccount,
  needsDisclaimer,
}: {
  isNewAccount?: boolean
  needsDisclaimer: boolean
}) {
  vi.spyOn(api, 'verifyOtp').mockResolvedValue({
    access_token: 'tok',
    token_type: 'bearer',
    user: {
      id: 'u-1',
      email: 'someone@example.com',
      full_name: null,
      needs_disclaimer: needsDisclaimer,
    },
    ...(isNewAccount === undefined ? {} : { is_new_account: isNewAccount }),
  } as never)
}

/** Fill the six code boxes, then submit.
 *
 * A multi-character value at index 0 is the screen's own autofill path — it distributes
 * the digits across all six boxes in one change (page.tsx:34-43). The submit button is
 * disabled until the code is a full six digits, so the click has to come after. */
async function enterCode() {
  const { container } = render(<VerifyPage />)

  const first = await waitFor(() => {
    const el = container.querySelector('input[inputMode="numeric"]')
    if (!el) throw new Error('code inputs not rendered')
    return el as HTMLInputElement
  })
  fireEvent.change(first, { target: { value: CODE } })

  const submit = await waitFor(() => {
    const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement | null
    if (!btn || btn.disabled) throw new Error('submit still disabled — code not complete')
    return btn
  })
  fireEvent.click(submit)
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('verify → post-verification routing', () => {
  it('routes a JUST-CREATED account to /auth/welcome', async () => {
    // needs_disclaimer is true as well, to prove the new-account branch wins: the user
    // must learn about the account before being asked to accept anything.
    mockVerify({ isNewAccount: true, needsDisclaimer: true })
    await enterCode()

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/welcome'))
  })

  it('routes an existing user needing the disclaimer to /auth/disclaimer', async () => {
    mockVerify({ isNewAccount: false, needsDisclaimer: true })
    await enterCode()

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/disclaimer'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })

  it('routes an existing, already-accepted user straight to /app/today', async () => {
    mockVerify({ isNewAccount: false, needsDisclaimer: false })
    await enterCode()

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })

  it('treats an ABSENT is_new_account as not-new', async () => {
    // The field is optional on AuthResponse and defaults False on the backend. A
    // response without it must behave exactly as before this change.
    mockVerify({ needsDisclaimer: false })
    await enterCode()

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(mockReplace).not.toHaveBeenCalledWith('/auth/welcome')
  })
})
