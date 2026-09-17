// The shared locked-persona → paywall route, and the refusal matcher behind the
// fallback path. Kept in one module so a fourth caller cannot invent a fifth
// spelling of the query string (#576/#582 already wired three).
import { describe, it, expect } from 'vitest'
import { isPersonaLockedError, lockedPersonaUpgradeHref } from '../personaLock'

describe('lockedPersonaUpgradeHref', () => {
  it('matches the destination the already-wired surfaces use', () => {
    expect(lockedPersonaUpgradeHref('george_orwell')).toBe(
      '/app/upgrade?source=persona_locked&persona=george_orwell',
    )
  })

  // AMENDED, and the encoding genuinely changed. This helper used to build its
  // query string with encodeURIComponent (space -> '%20'); it now delegates to
  // lib/upgradeHref, which uses URLSearchParams (space -> '+'). Both are correct
  // encodings of the same value and both round-trip through the
  // URLSearchParams.get() on the reading side, so nothing a reader can observe
  // has changed.
  //
  // THE CODEBASE ALREADY HELD BOTH SPELLINGS: PaywallModal built the very same
  // `persona` key with URLSearchParams while this helper used
  // encodeURIComponent, so the two surfaces encoded one parameter two ways.
  // Consolidating them had to pick one. The previous assertion pinned the
  // spelling rather than the property it was named for, so it is rewritten to
  // assert the PROPERTY -- encoded, not pasted, and it round-trips -- which is
  // what "encodes a slug rather than pasting it into the query string" means and
  // is true of either encoding.
  //
  // (No real slug can tell the difference: persona slugs are [a-z_]+ and contain
  // no spaces. The adversarial input below exists to prove the escaping, not to
  // describe traffic.)
  it('encodes a slug rather than pasting it into the query string', () => {
    const href = lockedPersonaUpgradeHref('a slug/with&chars')

    // Not pasted: the raw separators never reach the query as themselves.
    expect(href).not.toContain('persona=a slug/with&chars')
    expect(href).toContain('%2F')
    expect(href).toContain('%26')

    // And it round-trips to exactly the slug that went in.
    const parsed = new URLSearchParams(href.split('?')[1])
    expect(parsed.get('persona')).toBe('a slug/with&chars')
    expect(parsed.get('source')).toBe('persona_locked')
  })
})

describe('isPersonaLockedError', () => {
  it('recognises the API refusal that used to be toasted verbatim', () => {
    expect(isPersonaLockedError(new Error('Persona george_orwell requires plan upgrade'))).toBe(true)
  })

  it('does not claim an unrelated failure', () => {
    expect(isPersonaLockedError(new Error('Network down'))).toBe(false)
    expect(isPersonaLockedError(new Error('500 Internal Server Error'))).toBe(false)
  })

  it('is safe on non-Error throws', () => {
    expect(isPersonaLockedError('requires plan upgrade')).toBe(false)
    expect(isPersonaLockedError(null)).toBe(false)
    expect(isPersonaLockedError(undefined)).toBe(false)
  })
})
