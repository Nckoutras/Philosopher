// @vitest-environment jsdom
//
// The consent contract, pinned. These are the assertions that make "opt-in"
// mean something: PostHog must not load, initialize, or capture before an
// explicit Accept, and a Decline must leave the SDK entirely unloaded.
//
// HOW THESE CAN FAIL. Every case drives the real lib/analytics.ts against a
// mocked `posthog-js` module and asserts on `init`/`capture`/`identify` spies.
// An implementation that imported the SDK at module scope, or that initialized
// on a null/denied consent value, fails the first three. One that dereferenced
// window.posthog would fail `survives an SDK that fails to load` with a
// TypeError instead of a silent no-op.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// A STATEFUL fake, not bare spies. posthog-js persists an opt-out and drops
// events INSIDE capture(), returning normally — so a test that only asserted
// "capture was called" would pass against the bug this models. `delivered`
// records what the SDK would actually have sent.
let optedOut = false
let delivered: Array<[string, unknown]> = []

const mockInit = vi.fn()
const mockCapture = vi.fn((event: string, props?: unknown) => {
  if (optedOut) return // the silent drop
  delivered.push([event, props])
})
const mockIdentify = vi.fn()
const mockReset = vi.fn()
const mockOptOut = vi.fn(() => {
  optedOut = true // persists across init(), exactly as the real cookie does
})
const mockOptIn = vi.fn(() => {
  optedOut = false
})
const mockHasOptedOut = vi.fn(() => optedOut)

// Counts how many times the SDK module was actually evaluated. This is the
// counter behind "Decline loads no SDK at all", so it has to be live: a
// top-level vi.mock() caches its factory and the count would stay 0 whether or
// not the import fired, making that assertion unable to fail. vi.doMock() is
// not hoisted and re-runs after resetModules(), so each load is counted — and
// the granted case below asserts it reaches 1, which is what proves the
// counter works at all.
let importCount = 0

async function loadModule({ sdkFails = false } = {}) {
  vi.resetModules()
  vi.doMock('posthog-js', () => {
    importCount += 1
    if (sdkFails) throw new Error('blocked by client')
    return {
      default: {
        init: mockInit,
        capture: mockCapture,
        identify: mockIdentify,
        reset: mockReset,
        opt_out_capturing: mockOptOut,
        opt_in_capturing: mockOptIn,
        has_opted_out_capturing: mockHasOptedOut,
      },
    }
  })
  return import('../analytics')
}

beforeEach(() => {
  vi.clearAllMocks()
  importCount = 0
  optedOut = false
  delivered = []
  localStorage.clear()
  process.env.NEXT_PUBLIC_POSTHOG_KEY = 'phc_test'
  process.env.NEXT_PUBLIC_POSTHOG_HOST = 'https://eu.i.posthog.com'
})

afterEach(() => {
  vi.doUnmock('posthog-js')
  delete process.env.NEXT_PUBLIC_POSTHOG_KEY
  delete process.env.NEXT_PUBLIC_POSTHOG_HOST
})

describe('consent gate', () => {
  it('does not initialize before a choice is made', async () => {
    const a = await loadModule()
    expect(a.getConsent()).toBeNull()

    await a.initAnalytics()

    expect(mockInit).not.toHaveBeenCalled()
    expect(importCount).toBe(0)
    expect(a.isInitialized()).toBe(false)
  })

  it('initializes after Accept, against the EU host', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()

    expect(mockInit).toHaveBeenCalledTimes(1)
    // The WHOLE options object, asserted by equality rather than by picking out
    // the keys we care about today. toHaveBeenCalledWith is exact for object
    // arguments, so dropping any line below — or adding an option nobody
    // reviewed — fails here. That is deliberate: every entry after
    // capture_pageview is a privacy control, and autocapture shipped ON to
    // production recording the text of clicked elements.
    expect(mockInit).toHaveBeenCalledWith('phc_test', {
      api_host: 'https://eu.i.posthog.com',
      person_profiles: 'identified_only',
      capture_pageview: false,
      autocapture: false,
      disable_session_recording: true,
      capture_performance: false,
      capture_heatmaps: false,
      disable_surveys: true,
      rageclick: false,
      capture_dead_clicks: false,
      capture_exceptions: false,
    })
    expect(a.isInitialized()).toBe(true)
    // Proves importCount is live, which is what gives the Decline case below
    // its teeth — an always-0 counter would make that assertion vacuous.
    expect(importCount).toBe(1)
  })

  it('turns every automatic capture off', async () => {
    // Named separately from the init-options assertion above so a regression
    // reports as a PRIVACY failure rather than as a config mismatch. Each of
    // these captures something the user did not ask us to record; autocapture
    // in particular records the text of the clicked element, which in this
    // product means saved lines, memory entries and conversation titles.
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()

    const opts = mockInit.mock.calls[0][1] as Record<string, unknown>
    expect(opts.autocapture).toBe(false)
    expect(opts.disable_session_recording).toBe(true)
    expect(opts.capture_performance).toBe(false)
    expect(opts.capture_heatmaps).toBe(false)
    expect(opts.disable_surveys).toBe(true)
    expect(opts.rageclick).toBe(false)
    expect(opts.capture_dead_clicks).toBe(false)
    expect(opts.capture_exceptions).toBe(false)
    // THE REMOTE-CONFIG TRAP. These four are optional in PostHogConfig and
    // documented as falling back to PostHog's REMOTE configuration when
    // undefined — so for them "absent" is not "off", and the server can switch
    // them on without a code change. Presence is asserted separately from
    // value: a refactor that dropped the key would otherwise read as `undefined
    // === not enabled`, which is exactly backwards.
    for (const key of [
      'capture_performance',
      'capture_heatmaps',
      'capture_dead_clicks',
      'capture_exceptions',
    ]) {
      expect(Object.prototype.hasOwnProperty.call(opts, key)).toBe(true)
    }
  })

  it('loads no SDK at all after Decline', async () => {
    const a = await loadModule()
    a.setConsent('denied')
    await a.initAnalytics()

    // Not merely "did not init" — the module was never imported, so a declining
    // user does not download PostHog.
    expect(importCount).toBe(0)
    expect(mockInit).not.toHaveBeenCalled()
    expect(a.isInitialized()).toBe(false)
  })

  it('persists the choice under tw_analytics_consent', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    expect(localStorage.getItem('tw_analytics_consent')).toBe('granted')
    expect(a.getConsent()).toBe('granted')
  })

  it('treats an unreadable localStorage as "no choice", never as consent', async () => {
    const a = await loadModule()
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled by policy')
    })

    expect(a.getConsent()).toBeNull()
    await a.initAnalytics()
    expect(mockInit).not.toHaveBeenCalled()

    spy.mockRestore()
  })

  it('does not initialize twice when called repeatedly', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    await a.initAnalytics()

    expect(mockInit).toHaveBeenCalledTimes(1)
  })

  it('does not initialize when the env vars are missing', async () => {
    delete process.env.NEXT_PUBLIC_POSTHOG_KEY
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()

    expect(mockInit).not.toHaveBeenCalled()
  })
})

describe('track', () => {
  it('captures nothing without consent', async () => {
    const a = await loadModule()
    a.track('paywall_viewed', { surface: 'paywall_modal', reason: 'daily' })
    expect(mockCapture).not.toHaveBeenCalled()
  })

  it('captures nothing after Decline', async () => {
    const a = await loadModule()
    a.setConsent('denied')
    await a.initAnalytics()
    a.track('upgrade_clicked', { surface: 'paywall_modal', reason: 'save_limit' })
    expect(mockCapture).not.toHaveBeenCalled()
  })

  it('captures once consented and initialized', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.track('upgrade_clicked', { surface: 'paywall_modal', reason: 'save_limit' })

    expect(mockCapture).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'paywall_modal',
      reason: 'save_limit',
    })
  })

  it('survives an SDK that fails to load (adblock) without throwing', async () => {
    const a = await loadModule({ sdkFails: true })
    a.setConsent('granted')

    // The §18 case: no rejection, no console error, no thrown click handler.
    await expect(a.initAnalytics()).resolves.toBeUndefined()
    expect(a.isInitialized()).toBe(false)
    expect(() => a.track('paywall_viewed', { reason: 'daily' })).not.toThrow()
    expect(mockCapture).not.toHaveBeenCalled()
  })

  it('never dereferences window.posthog', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    // The module holds its own reference. If it read the global instead, this
    // deletion would break capture.
    delete (window as unknown as Record<string, unknown>).posthog

    a.track('paywall_viewed', { reason: 'daily' })
    expect(mockCapture).toHaveBeenCalled()
  })
})

describe('identify', () => {
  it('sends the internal user id', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.identify('8f14e45f-ceea-467a-9575-2b3c1c2f1234')

    expect(mockIdentify).toHaveBeenCalledWith('8f14e45f-ceea-467a-9575-2b3c1c2f1234')
  })

  it('refuses an email-shaped id', async () => {
    // A distinct_id is effectively permanent once written; there is no cheap
    // way to unsend one. This guard is the last line before that.
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.identify('someone@example.com')

    expect(mockIdentify).not.toHaveBeenCalled()
  })

  it('sends no person properties at all', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.identify('user-123')

    // One argument only — no props object that could carry an email later.
    expect(mockIdentify.mock.calls[0]).toHaveLength(1)
  })

  it('no-ops before init', async () => {
    const a = await loadModule()
    a.identify('user-123')
    expect(mockIdentify).not.toHaveBeenCalled()
  })
})

describe('withdrawal', () => {
  it('opts out, resets and drops the reference when switched off', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    expect(a.isInitialized()).toBe(true)

    a.optOutAnalytics()

    expect(mockOptOut).toHaveBeenCalledTimes(1)
    expect(a.isInitialized()).toBe(false)

    a.track('paywall_viewed', { reason: 'daily' })
    expect(mockCapture).not.toHaveBeenCalled()
  })

  it('can be re-enabled after withdrawal, and events actually reach capture', async () => {
    // THE REGRESSION. posthog-js persists opt_out_capturing() and init()
    // restores it, so without an explicit opt_in the re-enabled SDK initializes
    // cleanly and then drops every event inside capture(). Asserting on the
    // mockCapture spy alone would NOT catch that — `delivered` is what the SDK
    // would really have sent.
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.optOutAnalytics()
    expect(optedOut).toBe(true)

    a.setConsent('granted')
    await a.initAnalytics()

    expect(a.isInitialized()).toBe(true)
    expect(mockInit).toHaveBeenCalledTimes(2)
    expect(mockOptIn).toHaveBeenCalledTimes(1)

    a.track('upgrade_clicked', { surface: 'paywall_modal', reason: 'daily' })
    expect(delivered).toEqual([
      ['upgrade_clicked', { surface: 'paywall_modal', reason: 'daily' }],
    ])
  })

  it('clears a PERSISTED opt-out on a fresh load with consent granted', async () => {
    // The reload half of the same bug: the toggle was switched off in an
    // earlier session, the cookie survived, and the user has since re-consented.
    // init() alone would restore the opt-out and swallow everything.
    optedOut = true
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()

    expect(mockHasOptedOut).toHaveBeenCalled()
    expect(mockOptIn).toHaveBeenCalledTimes(1)
    expect(optedOut).toBe(false)

    a.track('$pageview', { $current_url: '/app/upgrade?source=paywall_modal' })
    expect(delivered).toEqual([
      ['$pageview', { $current_url: '/app/upgrade?source=paywall_modal' }],
    ])
  })

  it('does not call opt_in_capturing when there was no opt-out to clear', async () => {
    // opt_in_capturing() writes its own cookie. Calling it unconditionally
    // would set one for every consenting user on every load.
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()

    expect(mockOptIn).not.toHaveBeenCalled()
  })

  it('resetAnalytics is safe before init', async () => {
    const a = await loadModule()
    expect(() => a.resetAnalytics()).not.toThrow()
    expect(mockReset).not.toHaveBeenCalled()
  })

  it('resetAnalytics clears identity on sign-out', async () => {
    const a = await loadModule()
    a.setConsent('granted')
    await a.initAnalytics()
    a.resetAnalytics()

    expect(mockReset).toHaveBeenCalledTimes(1)
  })
})
