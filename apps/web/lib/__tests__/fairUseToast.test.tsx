// @vitest-environment jsdom
//
// WHAT THIS COVERS AND WHY IT DID NOT EXIST. The Pro fair-use cap
// (PRO_DAILY_FAIR_USE_LIMIT = 150) refuses with error_code "fair_use_limit" and
// a body carrying NO copy at all — every user-facing word comes from the client.
// The handling in useStream is correct and has been since it shipped; what was
// missing was any test of it, so its first render would have been a real Pro
// subscriber's screen. A grep for fairUseMessage / fair_use_limit / FAIR_USE_COPY
// across apps/web tests returned zero before this file.
//
// THE ASSERTION THAT MATTERS is not that a toast appears — it is that the
// PAYWALL DOES NOT. `rate_limited` and `fair_use_limit` are both 429s with
// identical headers, and the only thing separating them is the error code. A
// client that stops branching on it shows a paying subscriber an upgrade prompt
// for a tier they already own. That case is asserted on real store state
// (showPaywall / paywallDetails), not on a mocked setter, because the defect
// would be visible in the store the modal reads.
//
// ALL THREE BRANCHES ARE TESTED SEPARATELY even though they are identical
// today. That duplication is the point: send / sendAnotherMind / sendGoDeeper
// each carry their own copy of the check, and a future edit to two of the three
// is exactly the change one test would let through.
//
// The reset time is asserted as a shape, never as a formatted string. It is
// produced by toLocaleTimeString, so its exact text depends on the runner's ICU
// data and timezone — pinning it would pass here and fail on CI, which is the
// failure mode the 2026-09-01 log entry was written about.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import toast from 'react-hot-toast'
import { api, RateLimitError } from '@/lib/api'
import { useStore } from '@/lib/store'
import { FAIR_USE_COPY } from '@/lib/fairUseCopy'
import { useStream } from '../useStream'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

// useStream calls toast(...) directly for the fair-use notice and toast.error(...)
// for generic failures, so the mock must be callable AND carry .error — an
// object-only mock (the shape used by the older hook tests) would throw here and
// the throw would be swallowed by the same catch block under test.
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const RESET_AT = new Date('2026-09-09T21:00:00Z')

/** The 429 the backend actually sends at the Pro cap: no body copy, headers only. */
function fairUseError(resetAt: Date = RESET_AT): RateLimitError {
  return new RateLimitError({
    resetAt,
    limit: 150,
    remaining: 0,
    errorCode: 'fair_use_limit',
    upgradeTarget: 'pro',
  })
}

/** The free-tier 429, which must keep routing to the paywall. */
function freeCapError(): RateLimitError {
  return new RateLimitError({
    resetAt: RESET_AT,
    limit: 5,
    remaining: 0,
    errorCode: 'rate_limited',
    personaVoice: 'You have reached your daily message limit with this philosopher.',
    upgradeTarget: 'pro',
  })
}

// The three send paths, each with the api method it calls and how it is invoked.
const BRANCHES = [
  {
    name: 'send',
    method: 'streamMessage' as const,
    call: (s: ReturnType<typeof useStream>) => s.send('hello'),
  },
  {
    name: 'sendAnotherMind',
    method: 'streamAnotherMind' as const,
    call: (s: ReturnType<typeof useStream>) => s.sendAnotherMind('socrates'),
  },
  {
    name: 'sendGoDeeper',
    method: 'streamGoDeeper' as const,
    call: (s: ReturnType<typeof useStream>) => s.sendGoDeeper(),
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({
    activeConversationId: 'conv-1',
    plan: 'pro',
    showPaywall: false,
    paywallDetails: null,
    messages: [],
  })
})

async function run(
  branch: (typeof BRANCHES)[number],
  err: RateLimitError,
): Promise<void> {
  vi.spyOn(api, branch.method).mockRejectedValue(err)
  const { result } = renderHook(() => useStream())
  await act(async () => {
    await branch.call(result.current)
  })
}

describe.each(BRANCHES)('fair-use cap on $name', (branch) => {
  it('shows the approved notice, not an error toast', async () => {
    await run(branch, fairUseError())

    expect(toast).toHaveBeenCalledTimes(1)
    const shown = vi.mocked(toast).mock.calls[0][0] as string

    // Pinned twice on purpose: against the exported constant, so the module
    // stays the single source, and against the literal, so editing the constant
    // alone cannot silently change what a subscriber reads.
    expect(shown).toContain(FAIR_USE_COPY.message)
    expect(shown).toContain(
      "You've reached today's limit. Everything here will be waiting when it resets.",
    )
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('never opens the paywall — the user is already a subscriber', async () => {
    await run(branch, fairUseError())

    // Read from the store the modal actually renders off, not from a spy.
    expect(useStore.getState().showPaywall).toBe(false)
    expect(useStore.getState().paywallDetails).toBeNull()
  })

  it('appends the reset time after the approved sentence', async () => {
    await run(branch, fairUseError())

    const shown = vi.mocked(toast).mock.calls[0][0] as string
    expect(shown.startsWith(FAIR_USE_COPY.message)).toBe(true)
    // Shape, not a formatted time: the exact text is the runner's ICU output.
    expect(shown.slice(FAIR_USE_COPY.message.length)).toMatch(/^ Resets at .+\.$/)
  })

  it('still shows the approved sentence when the reset time is unusable', async () => {
    await run(branch, fairUseError(new Date('not-a-date')))

    const shown = vi.mocked(toast).mock.calls[0][0] as string
    // Additive only: a bad date drops the suffix and never the sentence.
    expect(shown).toBe(FAIR_USE_COPY.message)
    expect(useStore.getState().showPaywall).toBe(false)
  })

  it('routes the FREE-tier 429 to the paywall instead — the discrimination', async () => {
    await run(branch, freeCapError())

    // This is the half that fails if the errorCode check is ever dropped: with
    // no branch, both codes take one path and one of these two tests is wrong.
    expect(useStore.getState().showPaywall).toBe(true)
    expect(toast).not.toHaveBeenCalled()
  })
})
