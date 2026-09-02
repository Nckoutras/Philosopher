// The PENDING_COPY tripwire, and the typed-token invariant.
//
// WHY THIS FILE EXISTS. Account deletion is the only irreversible action in the
// product. Its wording is the last thing between a user and the permanent loss
// of everything they wrote, so placeholder copy reaching production is a product
// failure rather than a cosmetic one. The first test below is RED by design
// while the strings are unapproved, and turns green in the commit that pastes
// the approved copy. It is a gate, not a chore — do not satisfy it by weakening
// the assertion.
import { describe, it, expect } from 'vitest'
import { DELETE_ACCOUNT_COPY } from '../accountDeletionCopy'

describe('account deletion copy', () => {
  it('contains no PENDING_COPY placeholders', () => {
    const unapproved = Object.entries(DELETE_ACCOUNT_COPY)
      .filter(([, value]) => value.includes('PENDING_COPY'))
      .map(([key]) => key)

    expect(
      unapproved,
      `Unapproved copy would ship for: ${unapproved.join(', ')}. ` +
        'Paste the founder-approved strings into lib/accountDeletionCopy.ts.',
    ).toEqual([])
  })

  it('every string is non-empty', () => {
    for (const [key, value] of Object.entries(DELETE_ACCOUNT_COPY)) {
      expect(value.trim(), `${key} is empty`).not.toBe('')
    }
  })

  // Not copy — an invariant. The modal compares the input to typedToken with
  // case-sensitive equality, so a label that instructs a different word (or the
  // same word in a different case) makes the confirm button impossible to
  // enable. That failure is invisible in review and total in production.
  it('the typed label names the token exactly', () => {
    if (DELETE_ACCOUNT_COPY.typedLabel.includes('PENDING_COPY')) return // covered above
    expect(DELETE_ACCOUNT_COPY.typedLabel).toContain(DELETE_ACCOUNT_COPY.typedToken)
  })

  it('the typed token is the ruled literal DELETE', () => {
    expect(DELETE_ACCOUNT_COPY.typedToken).toBe('DELETE')
  })
})
