// @vitest-environment jsdom
//
// One test per web call site added by the taxonomy PR. Each asserts the
// property KEYS the event carries and that no property VALUE is free text —
// values that would need fixtures are not asserted, keys are.
//
// The free-text check is the point. The registry test guards property NAMES;
// this guards what actually gets sent, which is where a regression would
// actually leak: someone adds `title: letter.payload.title` and the name looks
// innocent. Every value must be a bounded enum, an id, a count or a bucket.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { track } from '@/lib/analytics'
import { latencyBucket, deviceClass, ANALYTICS_EVENTS } from '@/lib/analyticsEvents'
import { useStore } from '@/lib/store'

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

const mockPush = vi.fn()
const mockReplace = vi.fn()
let search = ''

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
  usePathname: () => '/',
  useParams: () => ({ id: 'letter-1' }),
}))

vi.mock('next/image', () => ({
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}))

/**
 * A value is safe if it is a number, a boolean, null/undefined, or a SHORT
 * string with no whitespace runs — i.e. an id, slug, enum or bucket. Anything
 * sentence-shaped fails, which is what a leaked title or body would look like.
 */
function assertNoFreeText(props: Record<string, unknown>) {
  for (const [key, value] of Object.entries(props)) {
    if (value == null || typeof value === 'number' || typeof value === 'boolean') continue
    expect(typeof value, `${key} must be a scalar`).toBe('string')
    const s = value as string
    expect(s.length, `${key} is too long to be an enum or id: ${s.slice(0, 40)}`).toBeLessThanOrEqual(64)
    // Two or more words is prose, not an enum. Ids and buckets never contain a space.
    expect(s.includes(' '), `${key} contains a space — enums and ids do not`).toBe(false)
  }
}

function propsOf(eventName: string): Record<string, unknown> {
  const call = (track as unknown as { mock: { calls: unknown[][] } }).mock.calls.find(
    (c) => c[0] === eventName,
  )
  expect(call, `${eventName} was not fired`).toBeTruthy()
  return (call![1] ?? {}) as Record<string, unknown>
}

beforeEach(() => {
  vi.clearAllMocks()
  search = ''
  localStorage.clear()
  useStore.setState({ token: null, user: null, activePersonaSlug: 'socrates' })
})

describe('landing_view', () => {
  it('fires for a signed-out visitor with no custom props', async () => {
    const { default: RootPage } = await import('@/app/page')
    render(<RootPage />)

    await waitFor(() => expect(track).toHaveBeenCalledWith('landing_view'))
    // posthog-js attaches utm_* and $referrer itself; declaring them here would
    // duplicate what the SDK already sends.
    expect(ANALYTICS_EVENTS.landing_view).toEqual([])
  })

  it('does not fire for a signed-in visitor, who never sees the page', async () => {
    useStore.setState({ token: 'tok' })
    const { default: RootPage } = await import('@/app/page')
    render(<RootPage />)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/app/today'))
    expect(track).not.toHaveBeenCalledWith('landing_view')
  })
})

describe('signup_started', () => {
  it('fires on submit with source + device, and never the email', async () => {
    const { default: AuthPage } = await import('@/app/auth/page')
    render(<AuthPage />)

    const email = await screen.findByPlaceholderText('you@example.com')
    // A distinctive canary: if any part of it reaches the props, the assertion
    // below cannot pass by coincidence.
    fireEvent.change(email, { target: { value: 'leaky-canary@example.org' } })
    fireEvent.submit(email.closest('form')!)

    await waitFor(() => expect(track).toHaveBeenCalledWith('signup_started', expect.anything()))
    const props = propsOf('signup_started')
    expect(Object.keys(props).sort()).toEqual(['device', 'source'])
    expect(JSON.stringify(props)).not.toContain('leaky-canary')
    expect(JSON.stringify(props)).not.toContain('@')
    assertNoFreeText(props)
  })
})

describe('helpers', () => {
  it('latencyBucket returns bounded enum values, never a raw number', () => {
    const buckets = [0, 999, 1000, 2999, 3000, 7999, 8000, 19999, 20000, 120000].map(latencyBucket)
    expect(new Set(buckets)).toEqual(
      new Set(['under_1s', '1_3s', '3_8s', '8_20s', 'over_20s']),
    )
    for (const b of buckets) expect(b).not.toMatch(/[0-9]{4,}/)
  })

  it('deviceClass returns one of three classes and never the user agent', () => {
    const d = deviceClass()
    expect(['mobile', 'tablet', 'desktop', 'unknown']).toContain(d)
    expect(d.length).toBeLessThan(16)
  })
})

describe('property values across the declared taxonomy', () => {
  it('every declared property name is a bounded identifier', () => {
    for (const [event, props] of Object.entries(ANALYTICS_EVENTS)) {
      for (const p of props as readonly string[]) {
        expect(p.length, `${event}.${p}`).toBeLessThanOrEqual(32)
        expect(p, `${event}.${p}`).toMatch(/^[$a-z][a-z0-9_]*$/)
      }
    }
  })
})
