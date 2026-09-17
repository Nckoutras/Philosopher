// @vitest-environment jsdom
//
// The one action on a ritual detail page (BUG-018).
//
// WHAT WAS WRONG. /app/ritual/<slug> explained a ritual in four paragraphs and
// then offered nothing: a ✕ back to Explore and no way in. Six pages whose only
// job is to create intent, each ending in a dead end. The UAT register called it
// "intent is created and then wasted", which is exactly right.
//
// WHY THE TABLE IS DRIVEN FROM lib/rituals.ts. Six routes, six answers, and the
// wrong answer is invisible: a gated ritual pointed at the generic `ritual`
// source still routes, still renders, still converts -- it just reports the
// wrong thing in PostHog forever, which is BUG-004 repeating. So the cases below
// are enumerated from RITUALS itself rather than hand-listed here; a seventh
// ritual added without deciding what its button does fails this file.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RITUALS } from '@/lib/rituals'
import { isUpgradeSource } from '@/lib/upgradeCopy'

const push = vi.fn()
const replace = vi.fn()
let slug = 'council'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
  useParams: () => ({ slug }),
}))

const track = vi.fn()
vi.mock('@/lib/analytics', () => ({ track: (...a: unknown[]) => track(...a) }))

// next/image needs no real loader here; the page is being read for its button.
vi.mock('next/image', () => ({ default: () => null }))

let plan = 'free'
let token: string | null = 'tok'
vi.mock('@/lib/store', () => ({
  useStore: (sel: (s: { plan: string; token: string | null }) => unknown) =>
    sel({ plan, token }),
}))

import RitualExplainerPage from '../page'

beforeEach(() => {
  push.mockClear()
  replace.mockClear()
  track.mockClear()
  plan = 'free'
  token = 'tok'
  window.history.replaceState({}, '', '/app/ritual/council')
})
afterEach(() => vi.clearAllMocks())

describe('every ritual declares what its button does', () => {
  it('gives each ritual an entry route', () => {
    for (const r of RITUALS) {
      expect(r.entry, `${r.slug} has no entry`).toMatch(/^\/app\//)
    }
  })

  it('gives every GATED ritual its own allow-listed source', () => {
    // The BUG-004 rule, enforced on the type and again here: a Pro ritual
    // routing to a source the paywall does not recognise falls back to the
    // generic line and is indistinguishable from its neighbours in analytics.
    for (const r of RITUALS) {
      if (!r.pro) continue
      expect(isUpgradeSource(r.source), `${r.slug} source not allow-listed`).toBe(true)
    }
  })

  it('does not route two gated rituals to one source', () => {
    // The literal defect: Future Self and the Sunday Letter both sent
    // source=letter, so one line and one analytics bucket covered both.
    const sources = RITUALS.filter((r) => r.pro).map((r) => (r as { source: string }).source)
    expect(new Set(sources).size).toBe(sources.length)
  })
})

describe('the CTA is state-aware', () => {
  it('enters the ritual directly when it is not gated', () => {
    slug = 'counterview'
    render(<RitualExplainerPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Begin' }))
    expect(push).toHaveBeenCalledWith('/app/counterview')
    expect(track).not.toHaveBeenCalled()
  })

  it('enters a gated ritual directly for a Pro reader', () => {
    slug = 'council'
    plan = 'pro'
    render(<RitualExplainerPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Begin' }))
    expect(push).toHaveBeenCalledWith('/app/council')
  })

  it('counts a trialing reader as entitled', () => {
    // computePlan (lib/store.ts) resolves 'trialing' to the paid plan. Offering
    // that reader a paywall they have already passed is the bug this guards.
    slug = 'council'
    plan = 'pro'
    render(<RitualExplainerPage />)
    expect(screen.getByRole('button', { name: 'Begin' })).toBeTruthy()
  })

  it('sends a free reader to the paywall with THAT ritual’s source and a returnTo', () => {
    slug = 'future-self'
    plan = 'free'
    window.history.replaceState({}, '', '/app/ritual/future-self')
    render(<RitualExplainerPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Upgrade to Pro' }))

    const url: string = push.mock.calls[0][0]
    const params = new URLSearchParams(url.split('?')[1])
    expect(url.startsWith('/app/upgrade?')).toBe(true)
    expect(params.get('source')).toBe('future_self')
    // Back to the page they were reading, not to Today.
    expect(params.get('returnTo')).toBe('/app/ritual/future-self')
  })

  it('fires upgrade_clicked on the gated press, naming the ritual', () => {
    // A DELIBERATE CTA, which is the registry's condition for this event
    // (lib/analyticsEvents.ts) -- unlike the guard redirects that push someone
    // to /app/upgrade because they tried to do something else.
    slug = 'you-vs-you'
    plan = 'free'
    render(<RitualExplainerPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Upgrade to Pro' }))
    expect(track).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'you_vs_you',
      reason: 'none',
    })
  })

  it('does not offer the Sunday Letter’s source from the Future Self page', () => {
    slug = 'future-self'
    plan = 'free'
    render(<RitualExplainerPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Upgrade to Pro' }))
    expect(push.mock.calls[0][0]).not.toContain('source=letter')
  })
})
