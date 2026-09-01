// @vitest-environment jsdom
//
// The upgrade page's first tests. Every paywall used to arrive at the same
// "Unlimited minds. Persistent memory. Deeper reflection." — the URL has
// carried source/reason since #576 and the page ignored both.
//
// TWO THINGS ARE BEING GUARDED, and they are different in kind.
//
// 1. COPY. One test per approved row, asserting the EXACT string. Copy is a
//    founder-approved object; an assertion that only checked "some line
//    rendered" would let a paraphrase through.
//
// 2. THE URL IS UNTRUSTED. source, reason and persona all arrive from a query
//    string. Nothing may be interpolated into rendered copy: an unknown source
//    renders the fallback (never blank, never "undefined"), and a persona name
//    is only ever taken from the API's own list — a slug that is not in it gets
//    the no-name line, and an attacker-supplied name never appears at all.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { benefitLine, FALLBACK_LINE, UPGRADE_SOURCES } from '@/lib/upgradeCopy'
import UpgradePage from '../page'

const mockReplace = vi.fn()
let search = ''

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

const PERSONAS = [
  { slug: 'marcus_aurelius', name: 'Marcus Aurelius' },
  { slug: 'socrates', name: 'Socrates' },
] as unknown as Awaited<ReturnType<typeof api.getPersonas>>

beforeEach(() => {
  vi.clearAllMocks()
  search = ''
  useStore.setState({ token: 'tok' })
  vi.spyOn(api, 'getPersonas').mockResolvedValue(PERSONAS)
  vi.spyOn(api, 'createCheckout').mockResolvedValue({ checkout_url: 'https://stripe.test/s/1' })
  // window.location.href assignment in handleSubscribe
  Object.defineProperty(window, 'location', {
    value: { href: '' },
    writable: true,
  })
})

// ── the copy rows, exact strings ────────────────────────────────────────────

describe('benefitLine — one case per approved row', () => {
  it('daily', () => {
    expect(benefitLine({ source: 'paywall_modal', reason: 'daily' })).toBe(
      "Today's free conversations are spent. Pro has no daily cap — and a memory that holds what you've said.",
    )
  })

  it('go_deeper_depth and deep_mode share one line', () => {
    const expected = 'Go as deep as the question needs. Pro removes the depth limits.'
    expect(benefitLine({ source: 'paywall_modal', reason: 'go_deeper_depth' })).toBe(expected)
    expect(benefitLine({ source: 'paywall_modal', reason: 'deep_mode' })).toBe(expected)
  })

  it('save_limit', () => {
    expect(benefitLine({ source: 'paywall_modal', reason: 'save_limit' })).toBe(
      'Keep every line worth keeping. Pro lifts the three-line limit.',
    )
  })

  it('persona_locked with a resolved name', () => {
    expect(benefitLine({ source: 'persona_locked', personaName: 'Marcus Aurelius' })).toBe(
      'Marcus Aurelius speaks on Pro — along with all eleven minds.',
    )
  })

  it('persona_locked with no name', () => {
    expect(benefitLine({ source: 'persona_locked' })).toBe('All eleven minds speak on Pro.')
  })

  it('council', () => {
    expect(benefitLine({ source: 'council' })).toBe(
      'The Council convenes on Pro: four minds, one verdict.',
    )
  })

  it('letter', () => {
    expect(benefitLine({ source: 'letter' })).toBe(
      'Your Sunday Letter arrives on Pro — a reading of your week, in the voice you spoke with most.',
    )
  })

  it('fallback for no params at all', () => {
    expect(benefitLine({})).toBe(FALLBACK_LINE)
  })

  it('reason wins over source when both are present', () => {
    // A reason names the wall the user actually hit; a source only names the
    // screen. Every reason-carrying arrival comes from PaywallModal, whose
    // source is the less informative of the two.
    expect(benefitLine({ source: 'council', reason: 'save_limit' })).toBe(
      'Keep every line worth keeping. Pro lifts the three-line limit.',
    )
  })

  it('the six sources with no approved line render the fallback', () => {
    for (const s of ['ritual', 'counterview', 'self_portrait', 'account', 'share', 'insight_door']) {
      expect(benefitLine({ source: s })).toBe(FALLBACK_LINE)
    }
  })
})

// ── the URL is untrusted ────────────────────────────────────────────────────

describe('unknown and hostile input', () => {
  it('an unknown source renders the fallback, never blank and never "undefined"', () => {
    const line = benefitLine({ source: 'not_a_real_source', reason: 'not_a_real_reason' })
    expect(line).toBe(FALLBACK_LINE)
    expect(line).not.toContain('undefined')
    expect(line.length).toBeGreaterThan(0)
  })

  it('never interpolates a query value into the rendered line', () => {
    const hostile = '<script>alert(1)</script>'
    const line = benefitLine({ source: hostile, reason: hostile, personaName: null })
    expect(line).toBe(FALLBACK_LINE)
    expect(line).not.toContain('script')
  })

  it('every declared source produces a non-empty line', () => {
    for (const s of UPGRADE_SOURCES) {
      const line = benefitLine({ source: s })
      expect(line.length).toBeGreaterThan(0)
      expect(line).not.toContain('undefined')
    }
  })
})

// ── the page ────────────────────────────────────────────────────────────────

describe('UpgradePage', () => {
  it('renders the generic line with no params', async () => {
    render(<UpgradePage />)
    expect(await screen.findByText(FALLBACK_LINE)).toBeTruthy()
    expect(screen.getByText('Choose your plan.')).toBeTruthy()
  })

  it('renders the council line from ?source=council', async () => {
    search = 'source=council'
    render(<UpgradePage />)
    expect(
      await screen.findByText('The Council convenes on Pro: four minds, one verdict.'),
    ).toBeTruthy()
  })

  it('resolves the persona NAME from the API, not from the URL', async () => {
    search = 'source=persona_locked&persona=marcus_aurelius'
    render(<UpgradePage />)

    // No-name variant first — it reads correctly on its own, so there is no
    // flash of wrong copy while the lookup is in flight.
    expect(await screen.findByText('All eleven minds speak on Pro.')).toBeTruthy()
    expect(
      await screen.findByText('Marcus Aurelius speaks on Pro — along with all eleven minds.'),
    ).toBeTruthy()
  })

  it('a slug not in the persona list keeps the no-name line', async () => {
    search = 'source=persona_locked&persona=not-a-real-slug'
    render(<UpgradePage />)
    await waitFor(() => expect(api.getPersonas).toHaveBeenCalled())
    expect(screen.getByText('All eleven minds speak on Pro.')).toBeTruthy()
  })

  it('a NAME supplied in the URL is never rendered', async () => {
    // The attack this guards: ?persona=<something that looks like a name>.
    // Only slugs are read, and only as a lookup key.
    search = 'source=persona_locked&persona=Sponsored%20By%20Acme'
    render(<UpgradePage />)
    await waitFor(() => expect(api.getPersonas).toHaveBeenCalled())
    expect(screen.queryByText(/Acme/)).toBeNull()
    expect(screen.getByText('All eleven minds speak on Pro.')).toBeTruthy()
  })

  it('a failed persona lookup falls back silently', async () => {
    search = 'source=persona_locked&persona=marcus_aurelius'
    vi.spyOn(api, 'getPersonas').mockRejectedValue(new Error('offline'))
    render(<UpgradePage />)
    expect(await screen.findByText('All eleven minds speak on Pro.')).toBeTruthy()
  })

  it('passes an allowlisted source to createCheckout', async () => {
    search = 'source=council&reason=daily'
    render(<UpgradePage />)
    fireEvent.click((await screen.findAllByText('Subscribe'))[0])

    await waitFor(() =>
      expect(api.createCheckout).toHaveBeenCalledWith('pro', 'yearly', 'council'),
    )
  })

  it('does NOT forward an unknown source to createCheckout', async () => {
    // It still reaches PostHog through $pageview's $current_url, so refusing to
    // forward it loses nothing and keeps Stripe metadata to the known enum.
    search = 'source=whatever_this_is'
    render(<UpgradePage />)
    fireEvent.click((await screen.findAllByText('Subscribe'))[0])

    await waitFor(() => expect(api.createCheckout).toHaveBeenCalled())
    expect(api.createCheckout).toHaveBeenCalledWith('pro', 'yearly', undefined)
  })

  it('omits source entirely when there is none', async () => {
    render(<UpgradePage />)
    fireEvent.click((await screen.findAllByText('Subscribe'))[1])

    await waitFor(() =>
      expect(api.createCheckout).toHaveBeenCalledWith('pro', 'monthly', undefined),
    )
  })
})
