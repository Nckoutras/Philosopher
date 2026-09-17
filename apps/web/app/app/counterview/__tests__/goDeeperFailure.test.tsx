// @vitest-environment jsdom
//
// THE DEFECT THIS PINS (BUG-007). "Go deeper" had ONE outcome set for TWO
// different things. handleDeeper read:
//
//     const gotDeeper = updated.responses.some(r => r.persona_slug === slug && r.round === 1)
//     if (!gotDeeper) setExhausted(prev => new Set(prev).add(slug))
//   } catch {
//     setExhausted(prev => new Set(prev).add(slug))   // 400/404 → don't loop the tap
//   }
//
// and the render read only that set:
//
//     const canDeepen = !deeper && !exhausted.has(slug)
//
// So a 500, a 502 or a dropped connection removed the tap, silently, and left
// the reader looking at exactly what a persona with nothing more to say looks
// like. The app reported an absence of an answer as an answer. Worse, the
// backend does not charge a line that never arrived
// (services/counterview_service.py:600-601), so the retry being denied is one the
// server was already willing to serve.
//
// A hang was the same defect with no bottom: there was no deadline on the
// request at all, so a connection that never closed spun the icon forever.
//
// WHAT THIS FILE ASSERTS, AND WHY BOTH HALVES ARE HERE. A fix that simply
// stopped writing `exhausted` would be as wrong as the bug: a persona that
// genuinely answered "nothing more" must still lose the tap, or the reader is
// invited to re-ask a question already answered. The two paths are asserted
// separately and asserted to be DISJOINT — the success-but-empty case must
// produce no error line, and the thrown case must not close the door.
//
// Copy is matched on entity-free fragments; the source is plain ASCII here but
// the neighbouring files write &rsquo; and the convention is worth keeping.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import type { Counterview } from '@/lib/api'
import CounterviewPage from '../page'

const mockPush = vi.fn()

// ONE router object — the load effect lists `router` in its dependencies, so an
// unstable identity re-runs it on every render.
const mockRouter = { push: mockPush, replace: vi.fn(), back: vi.fn() }

vi.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const CV_ID = '55555555-5555-5555-5555-555555555555'
const INSIGHT_ID = '66666666-6666-6666-6666-666666666666'
const MUSASHI = 'miyamoto_musashi'
const MACHIAVELLI = 'niccolo_machiavelli'

// The deadline the page puts on one go-deeper. Duplicated here as a LITERAL on
// purpose: importing the constant would make this test agree with the page by
// construction, and the point of the boundary case below is that 90s is the
// number, not merely that some number is used.
const DEEPER_TIMEOUT_MS = 90_000

/** Two voices, round-0 only — the state the reader is in before any tap. */
const baseCounterview = (): Counterview => ({
  id: CV_ID,
  source: 'insight',
  anchor_text: 'I should never rely on anyone.',
  status: 'generated',
  still_stands: null,
  title: 'Trust and its limits',
  responses: [
    {
      persona_slug: MUSASHI,
      persona_name: 'Miyamoto Musashi',
      persona_portrait_url: null,
      position: 0,
      round: 0,
      verdict: 'You call it self-reliance. Name the last time you asked.',
    },
    {
      persona_slug: MACHIAVELLI,
      persona_name: 'Niccolo Machiavelli',
      persona_portrait_url: null,
      position: 1,
      round: 0,
      verdict: 'A man alone is not free. He is merely unguarded.',
    },
  ],
  turns: [],
  rebuttals_remaining: 2,
  is_saved: false,
}) as Counterview

/** The same counterview after a successful deepening of the active speaker. */
const withDeeperLine = (): Counterview => {
  const cv = baseCounterview()
  return {
    ...cv,
    responses: [
      ...cv.responses,
      {
        persona_slug: MUSASHI,
        persona_name: 'Miyamoto Musashi',
        persona_portrait_url: null,
        position: 0,
        round: 1,
        verdict: 'The sword you keep sheathed still rusts.',
      },
    ],
  } as Counterview
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({ token: 'test-token' })
  vi.spyOn(api, 'listCounterviews').mockResolvedValue([])
  // jsdom implements no matchMedia, and the staged reveal asks it about
  // prefers-reduced-motion. Answering "reduce" skips the phase timers, which
  // also keeps the fake-timer cases below free of unrelated pending timeouts.
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
  window.history.replaceState({}, '', `/app/counterview?insightId=${INSIGHT_ID}`)
})

afterEach(() => {
  vi.useRealTimers()
  window.history.replaceState({}, '', '/app/counterview')
})

/** Open the reader on a generated two-voice counterview. */
async function openReader(): Promise<void> {
  vi.spyOn(api, 'counterviewFromInsight').mockResolvedValue(baseCounterview())
  render(<CounterviewPage />)
  await screen.findByText(/Name the last time you asked/i)
}

/**
 * The same, for the deadline cases — which run on fake timers installed BEFORE
 * the render, so `findByText` has no real clock to poll on. Flushing with
 * `advanceTimersByTimeAsync(0)` settles the load effect without moving the
 * clock, which is what keeps the boundary assertion below exact.
 */
async function openReaderOnFakeTimers(): Promise<void> {
  vi.spyOn(api, 'counterviewFromInsight').mockResolvedValue(baseCounterview())
  render(<CounterviewPage />)
  await act(async () => { await vi.advanceTimersByTimeAsync(0) })
  expect(screen.queryByText(/Name the last time you asked/i)).toBeTruthy()
}

function deeperButton(): HTMLElement | null {
  return screen.queryByRole('button', { name: /go deeper/i })
}

function retryButton(): HTMLElement | null {
  return screen.queryByRole('button', { name: /try again/i })
}

function errorLine(): HTMLElement | null {
  return screen.queryByText(/Could not go deeper just now/i)
}

// ─────────────────────────────────────────────────────────────────────────────

describe('go deeper — when the request FAILS', () => {
  it('keeps the tap and offers a retry, rather than reporting exhaustion', async () => {
    // THE ASSERTION THIS FILE EXISTS FOR. A throw tells us nothing about
    // whether the persona has more to say, so the door must stay open.
    await openReader()
    vi.spyOn(api, 'deeperCounterview').mockRejectedValue(new Error('500 Internal Server Error'))

    fireEvent.click(deeperButton()!)

    await waitFor(() => expect(errorLine()).toBeTruthy())
    expect(retryButton()).toBeTruthy()
    // The original tap is still there too — the retry is an addition, not a
    // replacement, and either affordance must work.
    expect(deeperButton()).toBeTruthy()
  })

  it('renders no spinner once the failure has landed', async () => {
    // The bug's other face: a request that ends must stop looking like one that
    // has not. deepeningSlug is cleared in `finally`, so the icon returns.
    await openReader()
    vi.spyOn(api, 'deeperCounterview').mockRejectedValue(new Error('502 Bad Gateway'))

    fireEvent.click(deeperButton()!)

    await waitFor(() => expect(errorLine()).toBeTruthy())
    expect(document.querySelector('.animate-spin')).toBeNull()
  })

  it('recovers on the retry, and clears the error with it', async () => {
    // End to end: the tap the user was being denied actually produces the line.
    await openReader()
    const deeper = vi
      .spyOn(api, 'deeperCounterview')
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(withDeeperLine())

    fireEvent.click(deeperButton()!)
    await waitFor(() => expect(retryButton()).toBeTruthy())

    fireEvent.click(retryButton()!)

    expect(await screen.findByText(/The sword you keep sheathed still rusts/i)).toBeTruthy()
    expect(errorLine()).toBeNull()
    expect(retryButton()).toBeNull()
    expect(deeper).toHaveBeenCalledTimes(2)
  })

  it('confines the failure to the persona it happened to', async () => {
    // "In place, for that persona" — the other voice is untouched, and tapping
    // across to it must not inherit an error it did not produce.
    await openReader()
    vi.spyOn(api, 'deeperCounterview').mockRejectedValue(new Error('500'))

    fireEvent.click(deeperButton()!)
    await waitFor(() => expect(errorLine()).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: 'Niccolo Machiavelli' }))

    expect(await screen.findByText(/He is merely unguarded/i)).toBeTruthy()
    expect(errorLine()).toBeNull()
    expect(deeperButton()).toBeTruthy()
  })
})

describe('go deeper — when the request SUCCEEDS with nothing in it', () => {
  it('marks the persona exhausted and withdraws the tap', async () => {
    // The other half, and the reason the fix is not "stop writing exhausted".
    // A clean 200 that carries no round-1 IS the persona saying nothing more.
    await openReader()
    vi.spyOn(api, 'deeperCounterview').mockResolvedValue(baseCounterview())

    fireEvent.click(deeperButton()!)

    await waitFor(() => expect(deeperButton()).toBeNull())
  })

  it('says nothing about an error, because none occurred', async () => {
    // The disjointness assertion. These two paths share no state: an empty
    // success must never reach the error copy, and the case above must never
    // reach `exhausted`.
    await openReader()
    vi.spyOn(api, 'deeperCounterview').mockResolvedValue(baseCounterview())

    fireEvent.click(deeperButton()!)

    await waitFor(() => expect(deeperButton()).toBeNull())
    expect(errorLine()).toBeNull()
    expect(retryButton()).toBeNull()
  })
})

describe('go deeper — the deadline', () => {
  it('is 90 seconds, and a hang becomes a failure rather than a spinner', async () => {
    // Stands in for fetch: pending forever, rejecting only when the caller's
    // signal aborts — which is exactly what an aborted fetch does.
    //
    // PLAIN `useFakeTimers()`, deliberately — NOT `{ shouldAdvanceTime: true }`.
    // That option advances the fake clock by real elapsed time, so the real
    // milliseconds spent rendering and flushing get added to whatever this test
    // advances, and the boundary below crosses 90s early on a slow machine.
    // Written that way first, it failed here by 19ms: an assertion about the
    // runner wearing the costume of an assertion about the product.
    vi.useFakeTimers()
    await openReaderOnFakeTimers()

    let received: AbortSignal | undefined
    vi.spyOn(api, 'deeperCounterview').mockImplementation(
      (_id: string, _slug: string, signal?: AbortSignal) =>
        new Promise<Counterview>((_resolve, reject) => {
          received = signal
          signal?.addEventListener('abort', () =>
            reject(new DOMException('The operation was aborted.', 'AbortError')),
          )
        }),
    )

    fireEvent.click(deeperButton()!)
    await act(async () => {})

    // The page passes a signal at all — without one the deadline cannot bite.
    expect(received).toBeInstanceOf(AbortSignal)

    // One millisecond short of the deadline: still in flight, nothing said.
    await act(async () => {
      vi.advanceTimersByTime(DEEPER_TIMEOUT_MS - 1)
    })
    expect(errorLine()).toBeNull()
    expect(received!.aborted).toBe(false)

    // The deadline lands.
    await act(async () => {
      vi.advanceTimersByTime(1)
    })
    expect(received!.aborted).toBe(true)
    expect(errorLine()).toBeTruthy()
    expect(retryButton()).toBeTruthy()
    // And it is a FAILURE, not exhaustion — the tap survives a timeout.
    expect(deeperButton()).toBeTruthy()
  })

  it('does not fire against a request that already came back', async () => {
    // A late abort on a settled request would be harmless to the promise but
    // would leave a timer holding a reference for 90s after every tap.
    vi.useFakeTimers()
    await openReaderOnFakeTimers()

    let received: AbortSignal | undefined
    vi.spyOn(api, 'deeperCounterview').mockImplementation(
      async (_id: string, _slug: string, signal?: AbortSignal) => {
        received = signal
        return withDeeperLine()
      },
    )

    fireEvent.click(deeperButton()!)
    await act(async () => {})
    expect(screen.queryByText(/The sword you keep sheathed still rusts/i)).toBeTruthy()

    await act(async () => {
      vi.advanceTimersByTime(DEEPER_TIMEOUT_MS * 2)
    })
    expect(received!.aborted).toBe(false)
    expect(errorLine()).toBeNull()
  })
})

describe('go deeper — the double-submit guard, unchanged', () => {
  it('ignores a second tap while the first is still in flight', async () => {
    // NOT a new behaviour and NOT touched by this PR — pinned because the fix
    // restructured the function around it, and because no automated test
    // covered it before (the acceptance for it was a UAT item).
    await openReader()

    let settle: ((cv: Counterview) => void) | undefined
    const deeper = vi.spyOn(api, 'deeperCounterview').mockImplementation(
      () => new Promise<Counterview>((resolve) => { settle = resolve }),
    )

    fireEvent.click(deeperButton()!)
    await waitFor(() => expect(deeper).toHaveBeenCalledTimes(1))

    // Three more taps while the first has not come back.
    fireEvent.click(deeperButton()!)
    fireEvent.click(deeperButton()!)
    fireEvent.click(deeperButton()!)

    expect(deeper).toHaveBeenCalledTimes(1)

    await act(async () => { settle!(withDeeperLine()) })
    expect(await screen.findByText(/The sword you keep sheathed still rusts/i)).toBeTruthy()
  })
})
