// @vitest-environment jsdom
//
// THE DEFECT THIS PINS (TD-70, the web half). The insight door — the one the
// "Doubt this" tap opens, /app/counterview?insightId=… — loaded through:
//
//     const cv = await api.counterviewFromInsight(insightId).catch(() => null)
//
// which swallowed everything, a 429 included. Once TD-70 put a cap behind that
// door, a Pro subscriber at the ceiling was shown:
//
//     "There wasn't a clear case to make against this just yet."
//
// That is not a cap notice. It is the app making a claim about the user's own
// insight — that there was nothing there to argue with — when in fact it had
// declined to look. A confident falsehood, and worse than an absence.
//
// This is a NEW case set, not an edit of fairUsePaywall.test.tsx: that file's
// helper is documented as the voluntary form (no ?insightId), so every case in
// it drives handleSubmit and none of them reaches this branch.
//
// WHY THERE IS NO FREE-CAP HALF HERE, unlike the direct door's file: only
// fair_use_limit can arrive on this path. The free daily cap counts
// source='direct' rows and deliberately does not govern this door, so a
// "daily_limit" case would pin a response the server cannot send. What replaces
// it is the last describe block: the upgrade wall must never appear here.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import toast from 'react-hot-toast'
import { track } from '@/lib/analytics'
import { api, RateLimitError } from '@/lib/api'
import { useStore } from '@/lib/store'
import { FAIR_USE_COPY } from '@/lib/fairUseCopy'
import CounterviewPage from '../page'

const mockPush = vi.fn()

// ONE router object, not a fresh one per call. The page's load effect lists
// `router` in its dependencies, so an unstable identity re-runs it on every
// render — which fires the cap toast once per pass and makes a
// toHaveBeenCalledTimes(1) assertion measure the mock instead of the product.
const mockRouter = { push: mockPush, replace: vi.fn(), back: vi.fn() }

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

// Callable with .error — the page calls toast(...) directly.
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const RESET_AT = new Date('2026-09-09T21:00:00Z')
const INSIGHT_ID = '33333333-3333-3333-3333-333333333333'

/** The only cap that can guard this door. */
const fairUseError = () =>
  new RateLimitError({
    resetAt: RESET_AT,
    limit: 150,
    remaining: 0,
    errorCode: 'fair_use_limit',
    upgradeTarget: 'pro',
  })

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({ token: 'test-token' })
  vi.spyOn(api, 'listCounterviews').mockResolvedValue([])
  // jsdom implements no matchMedia, and the staged reveal asks it about
  // prefers-reduced-motion as soon as a counterview is generated. Answering
  // "reduce" skips the timers and renders the verdicts immediately.
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    }),
  })
  // The page reads the id straight off the URL (no useSearchParams — the effect
  // is client-only), so the query string IS the fixture for this path.
  window.history.replaceState({}, '', `/app/counterview?insightId=${INSIGHT_ID}`)
})

afterEach(() => {
  window.history.replaceState({}, '', '/app/counterview')
})

/** Open the insight door with the server refusing. */
async function openInsight(err: unknown): Promise<void> {
  vi.spyOn(api, 'counterviewFromInsight').mockRejectedValue(err)
  render(<CounterviewPage />)
  await waitFor(() => expect(api.counterviewFromInsight).toHaveBeenCalledWith(INSIGHT_ID))
}

function goProButton(): HTMLElement | null {
  return screen.queryByRole('button', { name: /Go Pro/i })
}

describe('the insight door at the Pro fair-use cap', () => {
  it('shows the approved notice', async () => {
    await openInsight(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalledTimes(1))
    const shown = vi.mocked(toast).mock.calls[0][0] as string
    expect(shown).toContain(FAIR_USE_COPY.message)
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('does not claim there was no case to make', async () => {
    // THE ASSERTION THIS FILE EXISTS FOR. The neutral empty state is the right
    // thing to render for a genuine 'empty'/'suppressed' result, and the wrong
    // thing to render for a refusal — it answers a question the server never
    // asked. Matched on an entity-free fragment: the source writes &rsquo;.
    await openInsight(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    expect(screen.queryByText(/clear case to make against this/i)).toBeNull()
  })

  it('never shows the upgrade wall to a subscriber', async () => {
    await openInsight(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    expect(goProButton()).toBeNull()
    expect(screen.queryByText(/Pro removes the limit/i)).toBeNull()
  })

  it('never files upgrade_clicked', async () => {
    await openInsight(fairUseError())

    await waitFor(() => expect(toast).toHaveBeenCalled())
    // No button to tap, so the event cannot fire — asserted anyway, because the
    // event is the part that corrupts the funnel and it must stay impossible.
    expect(track).not.toHaveBeenCalledWith('upgrade_clicked', expect.anything())
  })
})

describe('the insight door on every other failure — unchanged', () => {
  it('still degrades to the neutral state, with no toast', async () => {
    // The prior behaviour for anything that is not a cap. A network failure has
    // nothing to tell the reader that the quiet fallback does not already say.
    await openInsight(new Error('network down'))

    expect(await screen.findByText(/clear case to make against this/i)).toBeTruthy()
    expect(toast).not.toHaveBeenCalled()
  })

  it('does not toast for a 429 carrying some other code', async () => {
    // Defensive: only the cap this door can actually hit speaks. If a different
    // code ever starts arriving here, it should be made deliberate rather than
    // inheriting the fair-use sentence by accident.
    await openInsight(
      new RateLimitError({
        resetAt: RESET_AT,
        limit: 2,
        remaining: 0,
        errorCode: 'daily_limit',
        upgradeTarget: 'pro',
      }),
    )

    expect(await screen.findByText(/clear case to make against this/i)).toBeTruthy()
    expect(toast).not.toHaveBeenCalled()
  })
})

describe('the insight door when it succeeds — unchanged', () => {
  it('renders the counterview and says nothing about limits', async () => {
    vi.spyOn(api, 'counterviewFromInsight').mockResolvedValue({
      id: '44444444-4444-4444-4444-444444444444',
      source: 'insight',
      anchor_text: 'I should never rely on anyone.',
      status: 'generated',
      still_stands: null,
      title: 'Trust and its limits',
      responses: [
        {
          persona_slug: 'miyamoto_musashi',
          persona_name: 'Miyamoto Musashi',
          persona_portrait_url: null,
          position: 0,
          round: 0,
          verdict: 'You call it self-reliance. Name the last time you asked.',
        },
      ],
      turns: [],
      rebuttals_remaining: 2,
      is_saved: false,
    } as Awaited<ReturnType<typeof api.counterviewFromInsight>>)

    render(<CounterviewPage />)

    expect(await screen.findByText(/Name the last time you asked/i)).toBeTruthy()
    expect(toast).not.toHaveBeenCalled()
    expect(goProButton()).toBeNull()
  })
})
