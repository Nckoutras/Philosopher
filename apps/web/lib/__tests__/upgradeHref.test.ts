// @vitest-environment jsdom
//
// jsdom, because currentReturnTo reads window.location and the whole point of
// these cases is what it does at particular paths. The repo's default for a
// lib test is node (vitest.config.ts), where the function's own
// `typeof window === 'undefined'` guard would make every case trivially null.

// The one spelling of /app/upgrade, and the returnTo that gives its Close
// button somewhere to go (BUG-003 / BUG-004).
//
// WHY currentReturnTo IS TESTED AGAINST safeReturnTo RATHER THAN AGAINST A LIST
// OF PATHS. The write side and the read side have to agree, and the way they
// agree here is that the writer asks the reader. A test that restated the
// allow-list would pass while the two drifted apart, which is the failure it
// exists to prevent.
import { describe, it, expect, afterEach } from 'vitest'
import { currentReturnTo, upgradeHref, RETURN_TO_PARAM } from '../upgradeHref'
import { safeReturnTo, DEFAULT_RETURN_TO } from '../safeReturnTo'
import { UPGRADE_SOURCES, benefitLine, isUpgradeSource } from '../upgradeCopy'

function at(path: string) {
  window.history.replaceState({}, '', path)
}

afterEach(() => at('/'))

describe('upgradeHref', () => {
  it('builds the minimal URL when only a source is given', () => {
    expect(upgradeHref({ source: 'council' })).toBe('/app/upgrade?source=council')
  })

  it('omits every optional key rather than serializing "undefined"', () => {
    const href = upgradeHref({ source: 'account', reason: undefined, persona: undefined, returnTo: null })
    expect(href).toBe('/app/upgrade?source=account')
    expect(href).not.toContain('undefined')
  })

  it('carries reason, persona and returnTo when they are given', () => {
    const params = new URLSearchParams(
      upgradeHref({
        source: 'persona_locked',
        reason: 'persona_locked',
        persona: 'george_orwell',
        returnTo: '/app/chat/conv/abc?x=1',
      }).split('?')[1],
    )
    expect(params.get('source')).toBe('persona_locked')
    expect(params.get('reason')).toBe('persona_locked')
    expect(params.get('persona')).toBe('george_orwell')
    expect(params.get(RETURN_TO_PARAM)).toBe('/app/chat/conv/abc?x=1')
  })

  it('escapes a returnTo that carries its own query string', () => {
    // The raw '?' and '&' must not leak into the outer query, or the paywall
    // would read a truncated destination and the reader would land elsewhere.
    const href = upgradeHref({ source: 'letter', returnTo: '/app/letters/42?src=email&a=b' })
    expect(href.split('?').length).toBe(2)
    const parsed = new URLSearchParams(href.split('?')[1])
    expect(parsed.get(RETURN_TO_PARAM)).toBe('/app/letters/42?src=email&a=b')
    expect(parsed.get('a')).toBeNull()
  })
})

describe('currentReturnTo', () => {
  it('returns the current in-app path, query included', () => {
    at('/app/letters/42?src=email')
    expect(currentReturnTo()).toBe('/app/letters/42?src=email')
  })

  it('returns null outside /app/, rather than a value the reader would discard', () => {
    // safeReturnTo answers DEFAULT_RETURN_TO for these, so carrying them would
    // add a parameter that changes nothing and reads like a bug on a shared URL.
    for (const path of ['/', '/auth', '/legal/terms', '/home']) {
      at(path)
      expect(currentReturnTo(), `expected null at ${path}`).toBeNull()
    }
  })

  it('never emits anything safeReturnTo would rewrite', () => {
    // THE INVARIANT, stated as one property rather than as a second copy of the
    // allow-list: whatever this produces must survive the reader untouched.
    for (const path of ['/', '/auth', '/app/today', '/app/mirror?insightId=7', '/legal/privacy']) {
      at(path)
      const emitted = currentReturnTo()
      if (emitted !== null) expect(safeReturnTo(emitted)).toBe(emitted)
    }
  })

  it('degrades to the default destination when it emits nothing', () => {
    at('/legal/terms')
    expect(safeReturnTo(currentReturnTo())).toBe(DEFAULT_RETURN_TO)
  })
})

describe('the two sources BUG-004 added', () => {
  it('allow-lists future_self and you_vs_you', () => {
    // Until this landed, an unknown source was dropped before checkout, so
    // neither Stripe metadata nor checkout_started could tell the two rituals
    // apart -- which is the defect, not the copy.
    expect(isUpgradeSource('future_self')).toBe(true)
    expect(isUpgradeSource('you_vs_you')).toBe(true)
    expect(UPGRADE_SOURCES).toContain('future_self')
    expect(UPGRADE_SOURCES).toContain('you_vs_you')
  })

  it('gives Future Self its own line, not the Sunday Letter’s', () => {
    const futureSelf = benefitLine({ source: 'future_self' })
    const letter = benefitLine({ source: 'letter' })
    expect(futureSelf).toBe("Write to the person you'll be in a year. Pro delivers it.")
    expect(futureSelf).not.toBe(letter)
    // The exact sentence a Future Self reader used to be shown.
    expect(futureSelf).not.toContain('Sunday Letter')
  })

  it('leaves the Sunday Letter line untouched', () => {
    expect(benefitLine({ source: 'letter' })).toBe(
      'Your Sunday Letter arrives on Pro — a reading of your week, in the voice you spoke with most.',
    )
  })

  it('gives You vs You its own line', () => {
    expect(benefitLine({ source: 'you_vs_you' })).toBe(
      'Set what you said then against what you say now. Pro opens the comparison.',
    )
  })

  it('still falls back for a source with no approved line', () => {
    // Nine of the sources have always fallen back; adding two named lines must
    // not have turned the default branch into something else.
    expect(benefitLine({ source: 'ritual' })).toBe(benefitLine({ source: 'account' }))
  })
})
