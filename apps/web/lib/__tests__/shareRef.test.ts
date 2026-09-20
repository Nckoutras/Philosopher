// @vitest-environment jsdom
/**
 * The share reference: storage, garbage, expiry, and a storage that throws.
 *
 * WHY THE GARBAGE CASES ARE THE BULK OF THIS FILE. The value is written by a
 * page anyone can open and read by a signup flow, so by the time it is read it
 * is untrusted input that has been sitting in a browser for up to thirty days.
 * Every malformed shape must read as "no reference" AND delete the key — a
 * value that can never be used should not occupy a person's storage for a
 * month waiting to be re-parsed on every signup.
 *
 * THE THROWING-STORAGE CASES ARE NOT THEORETICAL. localStorage does not return
 * null when it is unavailable; it THROWS, on read and write both, in Safari
 * private mode and under storage-disabled policies. lib/analytics.ts:43 already
 * says so about the consent key. A throw escaping this module would break a
 * signup for a metric.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

import {
  SHARE_REF_TTL_MS,
  clearShareRef,
  getShareRef,
  setShareRef,
} from '../shareRef'

const KEY = 'wr_share_ref'
const ID = 'AbCdEfGhIjKlMnOpQrStUv'

beforeEach(() => {
  localStorage.clear()
  vi.useRealTimers()
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('writing', () => {
  it('stores a versioned, timestamped reference', () => {
    setShareRef(ID)
    const raw = JSON.parse(localStorage.getItem(KEY)!)
    expect(raw.v).toBe(1)
    expect(raw.id).toBe(ID)
    expect(typeof raw.t).toBe('number')
  })

  it('refuses an id that is not the token shape', () => {
    // The scheme is 22 chars of [A-Za-z0-9_-]. Anything else cannot name a
    // share, so it is never written rather than being written and later
    // rejected by a server round-trip.
    for (const bad of ['', 'short', 'A'.repeat(23), 'has/slash/and!bang!!!!']) {
      setShareRef(bad)
      expect(localStorage.getItem(KEY)).toBeNull()
    }
  })

  it('round-trips', () => {
    setShareRef(ID)
    expect(getShareRef()).toBe(ID)
  })
})

describe('garbage', () => {
  const CASES: Array<[string, string]> = [
    ['not JSON at all', 'definitely not json'],
    ['a JSON scalar', '"just a string"'],
    ['null', 'null'],
    ['an array', '[]'],
    ['the wrong version', JSON.stringify({ v: 2, id: ID, t: Date.now() })],
    ['a missing id', JSON.stringify({ v: 1, t: Date.now() })],
    ['a short id', JSON.stringify({ v: 1, id: 'A'.repeat(21), t: Date.now() })],
    ['a long id', JSON.stringify({ v: 1, id: 'A'.repeat(23), t: Date.now() })],
    ['an id with bad characters', JSON.stringify({ v: 1, id: 'A'.repeat(18) + '!@#$', t: Date.now() })],
    ['a missing timestamp', JSON.stringify({ v: 1, id: ID })],
    ['a non-numeric timestamp', JSON.stringify({ v: 1, id: ID, t: 'yesterday' })],
    ['an infinite timestamp', JSON.stringify({ v: 1, id: ID, t: 1e400 })],
  ]

  it.each(CASES)('reads %s as absent and deletes it', (_label, raw) => {
    localStorage.setItem(KEY, raw)
    expect(getShareRef()).toBeNull()
    expect(localStorage.getItem(KEY)).toBeNull()
  })
})

describe('the window', () => {
  it('accepts a reference just inside 30 days', () => {
    localStorage.setItem(
      KEY,
      JSON.stringify({ v: 1, id: ID, t: Date.now() - (SHARE_REF_TTL_MS - 60_000) }),
    )
    expect(getShareRef()).toBe(ID)
  })

  it('discards one just outside, and deletes it', () => {
    localStorage.setItem(
      KEY,
      JSON.stringify({ v: 1, id: ID, t: Date.now() - (SHARE_REF_TTL_MS + 60_000) }),
    )
    expect(getShareRef()).toBeNull()
    expect(localStorage.getItem(KEY)).toBeNull()
  })

  it('discards a FUTURE timestamp rather than trusting it', () => {
    // A clock change or a hand-edited value. Treating it as fresh would make
    // the reference immortal — the one failure mode an expiry cannot recover
    // from on its own.
    localStorage.setItem(KEY, JSON.stringify({ v: 1, id: ID, t: Date.now() + 86_400_000 }))
    expect(getShareRef()).toBeNull()
    expect(localStorage.getItem(KEY)).toBeNull()
  })
})

describe('storage that throws', () => {
  it('writing is a silent no-op', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('QuotaExceededError')
    })
    expect(() => setShareRef(ID)).not.toThrow()
  })

  it('reading returns null', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('SecurityError')
    })
    expect(getShareRef()).toBeNull()
  })

  it('clearing does not throw', () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new DOMException('SecurityError')
    })
    expect(() => clearShareRef()).not.toThrow()
  })
})

describe('clearing', () => {
  it('removes the reference', () => {
    setShareRef(ID)
    clearShareRef()
    expect(getShareRef()).toBeNull()
  })
})
