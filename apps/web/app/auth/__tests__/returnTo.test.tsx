// @vitest-environment jsdom
//
// Where sign-in sends you, on both paths.
//
// THE LOOP THIS CLOSES. The Sunday letter is the only return loop that ships. A
// reader whose 7-day session has lapsed — which is every reader who engages ONLY
// through the letter, since the cookie and the JWT both last exactly one week —
// clicked the email, was bounced to sign-in, and landed on Today. The letter that
// called them was never opened, and `?src=email` never reached the API, so the
// §16 gate under-counted precisely those readers.
//
// BOTH PATHS ARE ASSERTED SEPARATELY. OTP carries `next` in the URL; Google parks
// it server-side in the Redis CSRF state entry and the API hands it back on the
// finish URL. They arrive by different routes and must agree on the destination,
// so neither test stands in for the other.
//
// AND THE TWO BRANCHES THAT MUST IGNORE IT. A brand-new account has no letter to
// return to, and the disclaimer is a consent gate. A returnTo that jumped either
// would be a bug with legal weight, not a routing nicety.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

const mockReplace = vi.fn()
let search = ''

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
}))

import VerifyPage from '../verify/page'
import OAuthFinishPage from '../oauth/finish/page'

const LETTER = '/app/letters/7f3c1a90-0000-4000-8000-000000000001'
const LETTER_WITH_MARKER = `${LETTER}?src=email`

const RETURNING_USER = {
  user: { id: 'u1', email: 'reader@example.com', needs_disclaimer: false },
  access_token: 'a.b.c',
  is_new_account: false,
}

beforeEach(() => {
  mockReplace.mockClear()
  search = ''
  vi.restoreAllMocks()
  vi.spyOn(useStore.getState(), 'setAuth').mockImplementation(() => {})
})

/** Fill the six code boxes and submit. */
async function submitCode(container: HTMLElement) {
  const boxes = container.querySelectorAll('input')
  fireEvent.paste(boxes[0].parentElement as HTMLElement, {
    clipboardData: { getData: () => '123456' },
  })
  await waitFor(() => expect((boxes[5] as HTMLInputElement).value).toBe('6'))
  fireEvent.submit(container.querySelector('form') as HTMLFormElement)
}

// ── OTP ──────────────────────────────────────────────────────────────────────

describe('OTP verify — the destination', () => {
  it('returns a lapsed reader to the letter, marker intact', async () => {
    // The assertion the whole feature exists for. `src=email` must survive, or
    // the reader arrives as an unattributed visit and email_opened_at is never
    // written — the loop looks closed and the gate still reads low.
    search = `email=reader%40example.com&next=${encodeURIComponent(LETTER_WITH_MARKER)}`
    vi.spyOn(api, 'verifyOtp').mockResolvedValue(RETURNING_USER as never)

    const { container } = render(<VerifyPage />)
    await submitCode(container)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith(LETTER_WITH_MARKER))
  })

  it('still lands on Today when there is no returnTo', async () => {
    search = 'email=reader%40example.com'
    vi.spyOn(api, 'verifyOtp').mockResolvedValue(RETURNING_USER as never)

    const { container } = render(<VerifyPage />)
    await submitCode(container)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
  })

  it.each([
    ['//evil.com', 'protocol-relative'],
    ['https://evil.com', 'absolute'],
    ['/auth?mode=signin', 'outside /app/'],
  ])('sends a hostile returnTo (%s, %s) to Today', async (hostile) => {
    search = `email=reader%40example.com&next=${encodeURIComponent(hostile)}`
    vi.spyOn(api, 'verifyOtp').mockResolvedValue(RETURNING_USER as never)

    const { container } = render(<VerifyPage />)
    await submitCode(container)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(mockReplace).not.toHaveBeenCalledWith(hostile)
  })

  it('ignores returnTo for a NEW account — welcome comes first', async () => {
    search = `email=reader%40example.com&next=${encodeURIComponent(LETTER_WITH_MARKER)}`
    vi.spyOn(api, 'verifyOtp').mockResolvedValue({
      ...RETURNING_USER,
      is_new_account: true,
    } as never)

    const { container } = render(<VerifyPage />)
    await submitCode(container)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/welcome'))
    expect(mockReplace).not.toHaveBeenCalledWith(LETTER_WITH_MARKER)
  })

  it('ignores returnTo when the disclaimer is still owed', async () => {
    search = `email=reader%40example.com&next=${encodeURIComponent(LETTER_WITH_MARKER)}`
    vi.spyOn(api, 'verifyOtp').mockResolvedValue({
      ...RETURNING_USER,
      user: { ...RETURNING_USER.user, needs_disclaimer: true },
    } as never)

    const { container } = render(<VerifyPage />)
    await submitCode(container)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/disclaimer'))
    expect(mockReplace).not.toHaveBeenCalledWith(LETTER_WITH_MARKER)
  })
})

// ── Google ───────────────────────────────────────────────────────────────────

describe('Google finish — the same destination, by a different road', () => {
  beforeEach(() => {
    vi.spyOn(api, 'setToken').mockImplementation(() => {})
    vi.spyOn(api, 'me').mockResolvedValue({ id: 'u1', email: 'reader@example.com' } as never)
  })

  it('returns a lapsed reader to the letter, marker intact', async () => {
    search = `token=a.b.c&needs_disclaimer=0&new_account=0&next=${encodeURIComponent(LETTER_WITH_MARKER)}`

    render(<OAuthFinishPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith(LETTER_WITH_MARKER))
  })

  it('still lands on Today when the API sent no returnTo', async () => {
    search = 'token=a.b.c&needs_disclaimer=0&new_account=0'

    render(<OAuthFinishPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
  })

  it('sends a hostile returnTo to Today even though the API validated it', async () => {
    // Defence in depth on purpose. The API validates before storing and again on
    // the way out, and this page validates a third time — because the value
    // arrives as a query parameter, and a query parameter is untrusted wherever
    // it claims to have come from.
    search = `token=a.b.c&needs_disclaimer=0&new_account=0&next=${encodeURIComponent('//evil.com')}`

    render(<OAuthFinishPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
  })

  it('ignores returnTo for a NEW Google account — welcome comes first', async () => {
    search = `token=a.b.c&needs_disclaimer=0&new_account=1&next=${encodeURIComponent(LETTER_WITH_MARKER)}`

    render(<OAuthFinishPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/welcome'))
    expect(mockReplace).not.toHaveBeenCalledWith(LETTER_WITH_MARKER)
  })

  it('ignores returnTo when the disclaimer is still owed', async () => {
    search = `token=a.b.c&needs_disclaimer=1&new_account=0&next=${encodeURIComponent(LETTER_WITH_MARKER)}`

    render(<OAuthFinishPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/auth/disclaimer'))
    expect(mockReplace).not.toHaveBeenCalledWith(LETTER_WITH_MARKER)
  })
})
