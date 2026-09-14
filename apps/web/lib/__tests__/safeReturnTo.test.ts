// The allow-list that decides where sign-in may send someone.
//
// WHY THIS FILE IS MOSTLY HOSTILE INPUT. `next` arrives in a link, so the
// interesting cases are not "does a good path work" but "which crafted path gets
// through". Each rejection below is a specific documented redirect technique, not
// a generic bad string — a test suite of typos would pass against a startsWith('/')
// check that a real payload walks straight past.

import { describe, it, expect } from 'vitest'
import { safeReturnTo, DEFAULT_RETURN_TO } from '../safeReturnTo'

const LETTER = '/app/letters/7f3c1a90-0000-4000-8000-000000000001'

describe('safeReturnTo — accepted', () => {
  it('keeps a plain /app/ path', () => {
    expect(safeReturnTo('/app/today')).toBe('/app/today')
  })

  it('keeps the letter path WITH its query — the whole point of Γ-1c', () => {
    // If the query is dropped here, ?src=email never reaches the letter page,
    // email_opened_at is never written, and the §16 gate keeps under-counting
    // exactly the readers this feature exists to recover.
    expect(safeReturnTo(`${LETTER}?src=email`)).toBe(`${LETTER}?src=email`)
  })

  it('keeps a path with several query params', () => {
    expect(safeReturnTo('/app/letters/x?src=email&foo=bar')).toBe('/app/letters/x?src=email&foo=bar')
  })
})

describe('safeReturnTo — rejected, each a known redirect technique', () => {
  const hostile: [string, string][] = [
    ['//evil.com',                 'protocol-relative — a browser reads this as a host'],
    ['///evil.com',                'three slashes, same trick'],
    ['/\\evil.com',                'backslash spelling that browsers normalise to //'],
    ['/app/\\\\evil.com',          'backslash after a legitimate-looking prefix'],
    ['https://evil.com',           'absolute URL'],
    ['http://evil.com',            'absolute URL, plain'],
    ['javascript:alert(1)',        'scheme that is not navigation at all'],
    ['/auth?mode=signin',          'same-origin but outside /app/ — a sign-in loop'],
    ['/admin',                     'same-origin but not /app/'],
    ['app/today',                  'relative, no leading slash'],
    ['',                           'empty'],
    ['/appfoo/bar',                'prefix that merely starts with the letters app'],
  ]

  it.each(hostile)('rejects %s (%s)', (value) => {
    expect(safeReturnTo(value)).toBe(DEFAULT_RETURN_TO)
  })

  it('rejects the %2f%2f-encoded protocol-relative form', () => {
    // URLSearchParams decodes once, so a caller reading ?next=%2f%2fevil.com
    // already holds '//evil.com' — covered above. This asserts the case where the
    // encoded text survives to the helper verbatim: it is not a /app/ path, so it
    // loses on the allow-list before decoding is even considered.
    expect(safeReturnTo('%2f%2fevil.com')).toBe(DEFAULT_RETURN_TO)
    expect(safeReturnTo('%2F%2Fevil.com')).toBe(DEFAULT_RETURN_TO)
  })

  it('a traversal survives the helper — and cannot leave the origin anyway', () => {
    // MEASURED, not assumed. The helper's own comment claims a traversal is not
    // an open redirect because it normalises to a same-origin path. That is a
    // claim about URL resolution, so it is checked here rather than trusted:
    // resolving each accepted value against the site origin must stay on it.
    //
    // This is what makes the rule safe WITHOUT a `..` clause. If a future browser
    // or a future rewrite made one of these escape, this test goes red and the
    // comment stops being true at the same moment.
    const origin = 'https://thewiseroom.app'
    const traversals = [
      '/app/../../auth',
      '/app/../..///evil.com',
      '/app/..%2f..%2f%2f%2fevil.com',
    ]
    for (const t of traversals) {
      expect(safeReturnTo(t)).toBe(t)
      expect(new URL(safeReturnTo(t), origin).origin).toBe(origin)
    }

    // The forms that DO leave the origin are the ones the rule refuses, and the
    // same resolution check proves the distinction is real rather than stylistic.
    expect(new URL('///evil.com', origin).origin).toBe('https://evil.com')
    expect(safeReturnTo('///evil.com')).toBe(DEFAULT_RETURN_TO)
  })

  it('never throws on an undecodable value', () => {
    // decodeURIComponent('%') raises URIError. A crafted link must not turn
    // sign-in into a crash.
    expect(() => safeReturnTo('/app/%')).not.toThrow()
    expect(safeReturnTo('/app/%')).toBe(DEFAULT_RETURN_TO)
  })

  it('rejects an over-long path', () => {
    expect(safeReturnTo('/app/' + 'a'.repeat(600))).toBe(DEFAULT_RETURN_TO)
  })

  it('accepts a path exactly at the 512 limit', () => {
    const atLimit = '/app/' + 'a'.repeat(512 - '/app/'.length)
    expect(atLimit).toHaveLength(512)
    expect(safeReturnTo(atLimit)).toBe(atLimit)
  })

  it('rejects null and undefined', () => {
    expect(safeReturnTo(null)).toBe(DEFAULT_RETURN_TO)
    expect(safeReturnTo(undefined)).toBe(DEFAULT_RETURN_TO)
  })
})
