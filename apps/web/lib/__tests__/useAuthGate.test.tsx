// @vitest-environment jsdom
//
// THE DEFECT THIS PINS (BUG-002). 28 protected pages guarded like this:
//
//     useEffect(() => { if (token === null) router.replace('/auth?mode=signin') }, …)
//
// with no hydration gate and no `next=`. The persisted store rehydrates
// ASYNCHRONOUSLY, so `token` is null on the first frame of every mount whether
// or not there is a session — and the guard fired on that frame.
//
// WHICH USER THIS ACTUALLY BROKE, because it is not the obvious one. A
// signed-out deep link was always fine: middleware.ts reads the ph_token COOKIE
// synchronously, sees nothing, and redirects with `next=` intact before the page
// renders at all. The person this broke is the RETURNING user with a valid
// cookie — middleware waves them through, the page renders, and the client
// bounces them bare because localStorage has not arrived yet. Two token stores,
// two read timings, written together and read apart.
//
// That is what share loop PR-2 lands in the middle of, which is why the `next=`
// half matters as much as the hydration half. A perfect hydration gate that
// still redirected bare would be the same defect with better timing.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { useAuthGate } from '@/lib/useAuthGate'

const replace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn() }),
}))

/** Minimal consumer: renders what the gate returns. */
function Probe() {
  const authed = useAuthGate()
  return <div data-testid="gate">{authed ? 'READY' : 'WAITING'}</div>
}

function gate(): string {
  return screen.getByTestId('gate').textContent ?? ''
}

/**
 * Drive zustand's persist hydration by hand.
 *
 * `finish` is captured from onFinishHydration so a test can decide WHEN
 * hydration completes — which is the whole subject here. Nothing about these
 * tests works if hydration is allowed to just happen.
 */
function stubPersist({ alreadyHydrated }: { alreadyHydrated: boolean }) {
  // Typed as the store's own PersistListener, not `() => void`: zustand hands the
  // listener the hydrated state, and a narrower signature is a type error rather
  // than a convenience.
  type Listener = Parameters<typeof useStore.persist.onFinishHydration>[0]
  const listeners: Listener[] = []
  const rehydrate = vi.fn()
  vi.spyOn(useStore.persist, 'hasHydrated').mockReturnValue(alreadyHydrated)
  vi.spyOn(useStore.persist, 'onFinishHydration').mockImplementation((fn: Listener) => {
    listeners.push(fn)
    return () => {
      const i = listeners.indexOf(fn)
      if (i >= 0) listeners.splice(i, 1)
    }
  })
  vi.spyOn(useStore.persist, 'rehydrate').mockImplementation(rehydrate as never)
  return {
    rehydrate,
    finish: async () => {
      await act(async () => { listeners.forEach((f) => f(useStore.getState())) })
    },
    listenerCount: () => listeners.length,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({ token: null })
  window.history.replaceState({}, '', '/app/today')
})

afterEach(() => {
  window.history.replaceState({}, '', '/')
})

describe('before hydration finishes', () => {
  it('redirects NOBODY — not even a genuinely signed-out visitor', async () => {
    // THE ASSERTION THIS FILE EXISTS FOR. `token` is null here for the same
    // reason it is null for a signed-IN user mid-hydration: the store has not
    // spoken. Acting on it is the bug, and it is a bug even when the eventual
    // answer turns out to be "signed out".
    const h = stubPersist({ alreadyHydrated: false })
    render(<Probe />)

    expect(gate()).toBe('WAITING')
    expect(replace).not.toHaveBeenCalled()
    expect(h.rehydrate).toHaveBeenCalled() // nothing started it; force one
  })

  it('does not report ready to the page either', async () => {
    // The other half: a page must not start loading data on a token it cannot
    // trust yet. WAITING is the correct answer to both questions.
    stubPersist({ alreadyHydrated: false })
    render(<Probe />)
    expect(gate()).toBe('WAITING')
  })
})

describe('when hydration restores a session', () => {
  it('reports ready and never redirects — the returning-user case', async () => {
    // The user middleware waved through on a valid cookie. Before this hook they
    // were bounced to /auth on the first frame, losing the page they asked for.
    const h = stubPersist({ alreadyHydrated: false })
    render(<Probe />)
    expect(gate()).toBe('WAITING')

    await act(async () => { useStore.setState({ token: 'a.b.c' }) })
    await h.finish()

    await waitFor(() => expect(gate()).toBe('READY'))
    expect(replace).not.toHaveBeenCalled()
  })

  it('handles hydration that finished BEFORE the component mounted', async () => {
    // The race the other way. persist.hasHydrated() already true means
    // onFinishHydration will never fire again, so a hook that only subscribed
    // would wait forever.
    useStore.setState({ token: 'a.b.c' })
    stubPersist({ alreadyHydrated: true })
    render(<Probe />)

    await waitFor(() => expect(gate()).toBe('READY'))
    expect(replace).not.toHaveBeenCalled()
  })
})

describe('when hydration confirms no session', () => {
  it('redirects to sign-in carrying next=, and only after hydration', async () => {
    const h = stubPersist({ alreadyHydrated: false })
    render(<Probe />)
    expect(replace).not.toHaveBeenCalled()

    await h.finish()

    await waitFor(() => expect(replace).toHaveBeenCalledTimes(1))
    expect(replace).toHaveBeenCalledWith(
      '/auth?mode=signin&next=%2Fapp%2Ftoday',
    )
  })

  it('preserves the destination QUERY, not just the path', async () => {
    // A letter arrives as /app/letters/x?src=email. Dropping ?src=email sends the
    // reader to the right page as the wrong kind of visit — the API writes read_at
    // without the attribution, which reads downstream as organic discovery.
    window.history.replaceState({}, '', '/app/letters/abc?src=email')
    const h = stubPersist({ alreadyHydrated: false })
    render(<Probe />)
    await h.finish()

    await waitFor(() => expect(replace).toHaveBeenCalled())
    const target = replace.mock.calls[0][0] as string
    const next = decodeURIComponent(new URL(target, 'https://x').searchParams.get('next') ?? '')
    expect(next).toBe('/app/letters/abc?src=email')
  })

  it('emits NO next= for a path safeReturnTo would reject on arrival', async () => {
    // The two post-auth screens under /auth/* use this hook too. safeReturnTo
    // allow-lists /app/ only, so a next= pointing at /auth/welcome would be
    // discarded by the consumer — emitting it would put a lie in a URL a person
    // can see. Validator reused, not reimplemented.
    window.history.replaceState({}, '', '/auth/welcome')
    const h = stubPersist({ alreadyHydrated: false })
    render(<Probe />)
    await h.finish()

    await waitFor(() => expect(replace).toHaveBeenCalled())
    expect(replace).toHaveBeenCalledWith('/auth?mode=signin')
  })

  it('redirects exactly once under a slow auth provider', async () => {
    // NO REDIRECT LOOP. Hydration finishing, a re-render, and a second effect run
    // must not each fire a navigation — two in flight is how a loop starts.
    const h = stubPersist({ alreadyHydrated: false })
    const { rerender } = render(<Probe />)
    await h.finish()
    await waitFor(() => expect(replace).toHaveBeenCalledTimes(1))

    // Three more chances to fire: re-render, a store write, another hydration
    // callback — the shape a slow or flapping provider produces.
    rerender(<Probe />)
    await act(async () => { useStore.setState({ token: null }) })
    await h.finish()
    rerender(<Probe />)

    expect(replace).toHaveBeenCalledTimes(1)
  })
})

describe('when hydration NEVER completes', () => {
  // THE CASE THAT HAD NO TEST, and the one that nearly shipped as a hang.
  //
  // zustand sets _hasHydrated and fires the finish listeners only in the .then
  // of its hydrate promise (node_modules/zustand/middleware.js:417-430). The
  // .catch runs the rehydration callback with the error and stops. So on a
  // storage error — private window, blocked site data, a throwing storage —
  // hasHydrated() stays false forever AND onFinishHydration never resolves.
  //
  // Every earlier case here resolves hydration one way or the other, which is
  // exactly why none of them could see this. Without the deadline the hook waits
  // on a promise that has already failed and every protected page renders its
  // loading state indefinitely, with no error and no redirect.
  const DEADLINE_MS = 3000

  it('decides at the deadline instead of waiting forever', async () => {
    vi.useFakeTimers()
    // Hydration that never finishes: false forever, and no listener ever called.
    vi.spyOn(useStore.persist, 'hasHydrated').mockReturnValue(false)
    vi.spyOn(useStore.persist, 'onFinishHydration').mockImplementation(() => () => {})
    vi.spyOn(useStore.persist, 'rehydrate').mockImplementation((() => {}) as never)

    render(<Probe />)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })

    // One millisecond short: still waiting, and correctly so.
    await act(async () => { vi.advanceTimersByTime(DEADLINE_MS - 1) })
    expect(gate()).toBe('WAITING')
    expect(replace).not.toHaveBeenCalled()

    // The deadline lands and the hook decides WITHOUT hydration.
    await act(async () => { vi.advanceTimersByTime(1) })
    expect(replace).toHaveBeenCalledTimes(1)
    // And it is a real decision, not a bare bounce: the destination survives, so
    // the reader lands back where they asked to be once signed in.
    expect(replace).toHaveBeenCalledWith('/auth?mode=signin&next=%2Fapp%2Ftoday')
    vi.useRealTimers()
  })

  it('does not fire the deadline once hydration has answered', async () => {
    // A late setHydrated(true) is harmless, but a timer left running after
    // unmount is a leak on every protected page in the app.
    vi.useFakeTimers()
    useStore.setState({ token: 'a.b.c' })
    vi.spyOn(useStore.persist, 'hasHydrated').mockReturnValue(true)
    vi.spyOn(useStore.persist, 'onFinishHydration').mockImplementation(() => () => {})
    vi.spyOn(useStore.persist, 'rehydrate').mockImplementation((() => {}) as never)

    render(<Probe />)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(gate()).toBe('READY')

    await act(async () => { vi.advanceTimersByTime(DEADLINE_MS * 2) })
    expect(replace).not.toHaveBeenCalled()
    vi.useRealTimers()
  })
})
