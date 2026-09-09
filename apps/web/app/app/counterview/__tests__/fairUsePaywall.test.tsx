// @vitest-environment jsdom
//
// THE DEFECT THIS PINS. /counterview refuses with two different 429s: the free
// daily cap (error_code "daily_limit") and the Pro fair-use cost cap
// ("fair_use_limit"). They are otherwise identical — same status, same
// X-RateLimit headers — and before this PR handleSubmit's catch read neither:
//
//     if (e instanceof RateLimitError) setLimitResetAt(e.resetAt)
//
// so a Pro subscriber who hit the cost cap was shown "Pro removes the limit."
// and a Go Pro button. That is a conversion defect and a data defect at once:
// it sells a tier the user already owns, and a tap files upgrade_clicked from
// someone with nothing to upgrade to, polluting upgrade intent.
//
// BOTH DIRECTIONS ARE ASSERTED. A fix that routed everything to the toast would
// be just as wrong as the bug — a free user must still get the wall, because for
// them it is the correct and useful thing to see. The free-cap half of this file
// is what stops the over-correction, and it asserts the Go Pro tap end to end,
// event included.
//
// Copy is matched on entity-free fragments ("Pro removes the limit"), never on
// the full sentence: the source writes &rsquo; so the rendered text carries a
// curly apostrophe, and pinning that is a runner detail, not a product fact.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import toast from 'react-hot-toast'
import { track } from '@/lib/analytics'
import { api, RateLimitError } from '@/lib/api'
import { useStore } from '@/lib/store'
import { FAIR_USE_COPY } from '@/lib/fairUseCopy'
import CounterviewPage from '../page'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

// Callable with .error — the page calls toast(...) directly.
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const RESET_AT = new Date('2026-09-09T21:00:00Z')

/** The Pro cost cap: no body copy, headers only. */
const fairUseError = () =>
  new RateLimitError({
    resetAt: RESET_AT,
    limit: 150,
    remaining: 0,
    errorCode: 'fair_use_limit',
    upgradeTarget: 'pro',
  })

/** The free daily cap. Note the code is "daily_limit" here, not "rate_limited". */
const freeCapError = () =>
  new RateLimitError({
    resetAt: RESET_AT,
    limit: 2,
    remaining: 0,
    errorCode: 'daily_limit',
    upgradeTarget: 'pro',
  })

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({ token: 'test-token' })
  vi.spyOn(api, 'listCounterviews').mockResolvedValue([])
})

/** Render the voluntary form (no ?insightId), type a belief, submit. */
async function submitBelief(err: RateLimitError): Promise<void> {
  vi.spyOn(api, 'createCounterview').mockRejectedValue(err)
  render(<CounterviewPage />)

  const textarea = await screen.findByPlaceholderText(/I believe/i)
  fireEvent.change(textarea, { target: { value: 'Ambition is always worth it.' } })
  fireEvent.click(screen.getByRole('button', { name: /Make the case/i }))

  await waitFor(() => expect(api.createCounterview).toHaveBeenCalled())
}

function goProButton(): HTMLElement | null {
  return screen.queryByRole('button', { name: /Go Pro/i })
}

describe('counterview at the Pro fair-use cap', () => {
  it('shows the approved notice', async () => {
    await submitBelief(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalledTimes(1))
    const shown = vi.mocked(toast).mock.calls[0][0] as string
    expect(shown).toContain(FAIR_USE_COPY.message)
    expect(shown).toContain(
      "You've reached today's limit. Everything here will be waiting when it resets.",
    )
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('does not show the limit panel', async () => {
    await submitBelief(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    expect(screen.queryByText(/Pro removes the limit/i)).toBeNull()
    expect(screen.queryByText(/Resets/i)).toBeNull()
  })

  it('does not show a Go Pro button — the user is already a subscriber', async () => {
    await submitBelief(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    expect(goProButton()).toBeNull()
  })

  it('never files upgrade_clicked', async () => {
    await submitBelief(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    // No button to tap, so the event cannot fire — asserted anyway, because the
    // event is the part that corrupts the funnel and it must stay impossible.
    expect(track).not.toHaveBeenCalledWith('upgrade_clicked', expect.anything())
  })
})

describe('counterview at the FREE daily cap — unchanged', () => {
  it('still shows the limit panel and its reset time', async () => {
    await submitBelief(freeCapError())

    expect(await screen.findByText(/Pro removes the limit/i)).toBeTruthy()
    expect(screen.getByText(/Resets/i)).toBeTruthy()
  })

  it('still shows the Go Pro button, and does not toast', async () => {
    await submitBelief(freeCapError())

    await waitFor(() => expect(goProButton()).not.toBeNull())
    expect(toast).not.toHaveBeenCalled()
  })

  it('still files upgrade_clicked and routes on the tap', async () => {
    await submitBelief(freeCapError())

    await waitFor(() => expect(goProButton()).not.toBeNull())
    fireEvent.click(goProButton()!)

    expect(track).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'counterview',
      reason: 'none',
    })
    expect(mockPush).toHaveBeenCalledWith('/app/upgrade?source=counterview')
  })
})
