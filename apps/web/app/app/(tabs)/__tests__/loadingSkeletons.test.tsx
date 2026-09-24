// @vitest-environment jsdom
//
// BUG-008, the half that is not the tab bar.
//
// Home and Quotes both HAD a loading branch. Both rendered an empty <main> — a blank
// vellum screen for the 1-4 seconds the fetch takes. That is the silence the UAT
// reported: the tap appears to have done nothing, so people tap again.
//
// WHY THIS IS A PAGE TEST AND NOT A loading.tsx TEST. There is no loading.tsx
// anywhere in this app and none was added. Every page under app/app is a client
// component that fetches in useEffect, so a Suspense boundary resolves on mount and
// unmounts before the fetch it would be covering even starts. The wait these pages
// have is theirs to render, which is why the fix is in the branch that already
// existed rather than in a new file above it.
//
// Both pages open with `loading` true and return from that branch before any child
// renders, so this harness only has to satisfy the hooks called ahead of it.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => '/app/today',
  useSearchParams: () => new URLSearchParams(),
}))

// Signed in, so nothing short-circuits ahead of the loading branch.
vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))

vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}))

vi.mock('react-hot-toast', () => ({ default: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }) }))

import TodayPage from '../today/page'
import QuotesPage from '../quotes/page'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'test-token', user: { full_name: 'Test User' } as never })
  // The effects fire on mount. They must not reach the network, and they must not
  // RESOLVE either — a resolved promise would flip `loading` false and this test
  // would assert the loaded page instead of the branch it is about. A promise that
  // never settles holds the page in exactly the state under test.
  // The methods are on the prototype, not the instance: see 'the harness' below.
  const never = () => new Promise(() => {})
  const proto = Object.getPrototypeOf(api)
  for (const m of Object.getOwnPropertyNames(proto)) {
    if (m !== 'constructor' && typeof proto[m] === 'function') {
      vi.spyOn(api, m as keyof typeof api).mockImplementation(never as never)
    }
  }
})

describe('the harness', () => {
  // TD-103. The loop above used to walk Object.keys(api). `api` is an ApiClient
  // instance, so its methods live on the prototype and Object.keys never saw
  // them: nothing was mocked, a real request left the test, and its rejection
  // landed as an unhandled error that made a green run exit 1.
  it('mocks the requests the pages make on mount', () => {
    expect(vi.isMockFunction(api.getLastConversation)).toBe(true)
  })
})

describe('the Home loading branch is not a blank screen', () => {
  it('renders skeleton shapes, not an empty main', () => {
    const { container } = render(<TodayPage />)

    const pulses = container.querySelectorAll('.animate-pulse')
    expect(pulses.length).toBeGreaterThan(0)
  })

  it('outlines the header and the 2x2 tile grid it is standing in for', () => {
    // Geometry matters: a skeleton whose shape does not match its content trades one
    // jolt for another. Two header bars + four tiles.
    const { container } = render(<TodayPage />)
    expect(container.querySelectorAll('.animate-pulse').length).toBe(6)
    expect(container.querySelector('.grid-cols-2')).toBeTruthy()
  })

  it('marks the region busy for assistive tech', () => {
    const { container } = render(<TodayPage />)
    expect(container.querySelector('main')?.getAttribute('aria-busy')).toBe('true')
  })
})

describe('the Quotes loading branch is not a blank screen', () => {
  it('renders skeleton shapes, not an empty main', () => {
    const { container } = render(<QuotesPage />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('outlines the carousel: a dominant card with a neighbour peeking', () => {
    const { container } = render(<QuotesPage />)
    const cards = container.querySelectorAll('.animate-pulse')
    expect(cards.length).toBe(2)
    // 80vw inside px-[10vw] is what makes the second card peek rather than sit
    // beside the first. Without it the branch reads as two half-width blocks.
    expect((cards[0] as HTMLElement).className).toContain('w-[80vw]')
  })

  it('marks the region busy for assistive tech', () => {
    const { container } = render(<QuotesPage />)
    expect(container.querySelector('main')?.getAttribute('aria-busy')).toBe('true')
  })
})
