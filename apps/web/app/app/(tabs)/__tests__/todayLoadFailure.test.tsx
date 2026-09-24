// @vitest-environment jsdom
//
// TD-103, the production half. Today's load() awaited api.getLastConversation()
// inside try/finally with no catch, so a failed request was an unhandled
// rejection — in the browser, not just in the test that first surfaced it.
//
// Ruled 2026-09-24: log it and render the empty state. The empty state is the
// isFirstDay branch, which is what a null lastConv already means once loading
// has finished; the only change is that the failure is caught and said.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => '/app/today',
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/useAuthGate', () => ({ useAuthGate: () => true }))

vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}))

vi.mock('react-hot-toast', () => ({ default: Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() }) }))

import TodayPage from '../today/page'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

let consoleError: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'test-token', user: { full_name: 'Test User' } as never })
  // Every other request the page makes on mount stays pending, so the only thing
  // that settles is the one under test.
  const never = () => new Promise(() => {})
  const proto = Object.getPrototypeOf(api)
  for (const m of Object.getOwnPropertyNames(proto)) {
    if (m !== 'constructor' && typeof proto[m] === 'function') {
      vi.spyOn(api, m as keyof typeof api).mockImplementation(never as never)
    }
  }
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  consoleError.mockRestore()
})

describe('Today when the last-conversation request fails', () => {
  it('logs the failure and renders the empty state', async () => {
    const failure = new Error('Not authenticated')
    vi.spyOn(api, 'getLastConversation').mockRejectedValue(failure)

    render(<TodayPage />)

    expect(await screen.findByText('Start your first conversation.')).toBeTruthy()
    expect(consoleError).toHaveBeenCalledWith('today load failed:', failure)
  })
})
