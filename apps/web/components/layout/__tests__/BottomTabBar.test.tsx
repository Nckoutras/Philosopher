// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import BottomTabBar from '../BottomTabBar'

let mockPathname = '/app/today'

vi.mock('next/navigation', () => ({
  // The bar navigates via <Link href>, not router.push. prefetch is here so the
  // idle route-warming effect can't throw if it fires.
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => mockPathname,
}))

// jsdom implements no navigation, so a real <Link href> click logs
// "Not implemented: navigation (except hash changes)". The listener runs on bubble,
// after the component's own onClick, so the pending state is already set by the time
// the default is swallowed — this silences the log without weakening any assertion.
beforeAll(() => {
  document.addEventListener('click', (e) => e.preventDefault())
})

beforeEach(() => {
  mockPathname = '/app/today'
})

describe('BottomTabBar', () => {
  it('renders all 5 tabs', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Home')).toBeTruthy()
    expect(screen.getByLabelText('Explore')).toBeTruthy()
    expect(screen.getByLabelText('Portrait')).toBeTruthy()
    expect(screen.getByLabelText('Account')).toBeTruthy()
    expect(screen.getByLabelText('Quotes')).toBeTruthy()
  })

  it('marks Portrait tab as active on /app/self-portrait', () => {
    mockPathname = '/app/self-portrait'
    render(<BottomTabBar />)
    const portraitBtn = screen.getByLabelText('Portrait')
    expect(portraitBtn.getAttribute('aria-current')).toBe('page')
  })

  it('does not mark other tabs as active on /app/self-portrait', () => {
    mockPathname = '/app/self-portrait'
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Home').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Explore').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Account').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Quotes').getAttribute('aria-current')).toBeNull()
  })

  it('links the Quotes tab to /app/quotes', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Quotes').getAttribute('href')).toBe('/app/quotes')
  })

  it('links the Explore tab to /app/explore', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Explore').getAttribute('href')).toBe('/app/explore')
  })
})

// BUG-008 — the PENDING state.
//
// What was there before: `active:opacity-50 active:scale-95`, which is CSS :active.
// It exists only while a finger is down, so neither jsdom nor a browser test can
// meaningfully assert it. What IS ours, and is asserted here, is the class the
// component puts on the tab AFTER the tap and holds until the destination paints.
//
// The visual is `opacity-50 scale-95` — the same pair :active gives, so lift-off
// does not appear to change state, only to persist it.
//
// TOKEN-EXACT, NOT SUBSTRING, and the first draft of this file got it wrong. The
// base className contains `active:opacity-50`, so `.toContain('opacity-50')` is true
// on every tab whether pending or not, and every "not to contain" assertion passed
// vacuously. Splitting on whitespace and comparing whole tokens is the difference
// between asserting the pending class and asserting that the string `opacity-50`
// appears somewhere in a className — which it always does.
describe('BottomTabBar — pending state (BUG-008)', () => {
  const classes = (label: string) =>
    screen.getByLabelText(label).className.split(/\s+/).filter(Boolean)
  const isPending = (label: string) =>
    classes(label).includes('opacity-50') && classes(label).includes('scale-95')

  it('the base class does NOT already carry the pending tokens', () => {
    // Guards the assertion technique itself. If a refactor moved `opacity-50` into
    // the base className, every test below would pass without the feature.
    render(<BottomTabBar />)
    expect(isPending('Quotes')).toBe(false)
    expect(classes('Quotes')).toContain('active:opacity-50')
  })

  it('lights the tapped tab and holds it', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Quotes'))
    // Still lit after the event has settled — this is the whole defect. :active
    // would already be gone by here.
    expect(isPending('Quotes')).toBe(true)
  })

  it('lights only the tapped tab', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Quotes'))
    for (const other of ['Home', 'Explore', 'Portrait', 'Account']) {
      expect(isPending(other)).toBe(false)
    }
  })

  it('does NOT light the tab you are already on', () => {
    // mockPathname is '/app/today', so Home is active. There is no navigation to
    // wait for, and lighting it would flicker the page under the reader's finger.
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Home'))
    expect(isPending('Home')).toBe(false)
  })

  it('clears on ARRIVAL, when the destination is the route rendering', () => {
    const { rerender } = render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Quotes'))
    expect(isPending('Quotes')).toBe(true)

    mockPathname = '/app/quotes'
    rerender(<BottomTabBar />)
    expect(isPending('Quotes')).toBe(false)
  })

  it('counts a DEEPER path under the destination as arrival', () => {
    // Matched on the tab's activePattern, not string equality: a tab whose route
    // redirects into a sub-path must not stay lit forever.
    const { rerender } = render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Portrait'))
    expect(isPending('Portrait')).toBe(true)

    mockPathname = '/app/self-portrait/questions'
    rerender(<BottomTabBar />)
    expect(isPending('Portrait')).toBe(false)
  })

  it('does NOT clear on arrival at some OTHER route', () => {
    const { rerender } = render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Quotes'))

    mockPathname = '/app/explore'
    rerender(<BottomTabBar />)
    // Still waiting on Quotes. A pending state that cleared on any navigation would
    // go dark mid-wait, which is the bug again with extra steps.
    expect(isPending('Quotes')).toBe(true)
  })

  it('gives up after the deadline rather than staying lit forever', () => {
    // A navigation that never completes must not leave a permanently dimmed tab
    // claiming something is still coming (TD-83: a signal that can hang needs a
    // deadline). 5s: 4999ms still lit, 5001ms not.
    vi.useFakeTimers()
    try {
      render(<BottomTabBar />)
      fireEvent.click(screen.getByLabelText('Quotes'))
      expect(isPending('Quotes')).toBe(true)

      act(() => { vi.advanceTimersByTime(4999) })
      expect(isPending('Quotes')).toBe(true)

      act(() => { vi.advanceTimersByTime(2) })
      expect(isPending('Quotes')).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  it('drops the transition under prefers-reduced-motion, but not the state', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Quotes'))
    expect(classes('Quotes')).toContain('motion-reduce:transition-none')
    expect(isPending('Quotes')).toBe(true)
  })
})
