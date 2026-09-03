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

  it('encodes a slug rather than pasting it into the query string', () => {
    expect(lockedPersonaUpgradeHref('a slug/with&chars')).toBe(
      '/app/upgrade?source=persona_locked&persona=a%20slug%2Fwith%26chars',
    )
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
