// The first test this middleware has ever had.
//
// It is the front door for every protected route, it has redirected people since
// the project started, and nothing has ever asserted where it sends them. That
// gap is how `next` came to be written on every bounce and read by nobody for
// months — a parameter with no reader and no test looks identical to a working
// feature from the outside.
//
// What matters here is the DESTINATION STRING, not Next.js internals: given a
// signed-out request for a letter, the Location header must carry a returnTo that
// can actually bring the reader back to that letter, marker included.

import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import { middleware } from '../middleware'

const ORIGIN = 'https://thewiseroom.app'
const LETTER = '/app/letters/7f3c1a90-0000-4000-8000-000000000001'

/** A signed-out request — no ph_token cookie, no Authorization header. */
function signedOut(path: string): NextRequest {
  return new NextRequest(new URL(path, ORIGIN))
}

function signedIn(path: string): NextRequest {
  const req = new NextRequest(new URL(path, ORIGIN))
  req.cookies.set('ph_token', 'a.b.c')
  return req
}

/** The Location the middleware redirected to, as a URL. */
function redirectTo(req: NextRequest): URL {
  const res = middleware(req)
  const location = res.headers.get('location')
  expect(location, 'expected a redirect, got none').toBeTruthy()
  return new URL(location as string)
}

describe('middleware — the signed-out bounce', () => {
  it('sends a signed-out letter click to sign-in', () => {
    const url = redirectTo(signedOut(`${LETTER}?src=email`))
    expect(url.pathname).toBe('/auth')
    expect(url.searchParams.get('mode')).toBe('signin')
  })

  it('carries the destination INCLUDING its query — the Γ-1c fix', () => {
    // The whole loop depends on this one assertion. `next` used to be
    // nextUrl.pathname, so ?src=email was dropped and the reader came back as an
    // unattributed visit: read_at written, email_opened_at not, and the §16 gate
    // under-counting precisely the people it exists to measure.
    const url = redirectTo(signedOut(`${LETTER}?src=email`))
    expect(url.searchParams.get('next')).toBe(`${LETTER}?src=email`)
  })

  it('does not leave the destination query dangling on /auth', () => {
    // clone() copies the whole URL, so overwriting only `pathname` used to leave
    // /auth?src=email&mode=signin&next=... — a stray param on the wrong URL that
    // meant nothing and was read by nobody. Pinned so the clone-then-overwrite
    // shape cannot come back.
    const url = redirectTo(signedOut(`${LETTER}?src=email`))
    expect(url.searchParams.get('src')).toBeNull()
    expect([...url.searchParams.keys()].sort()).toEqual(['mode', 'next'])
  })

  it('carries a bare path unchanged when there is no query', () => {
    const url = redirectTo(signedOut('/app/today'))
    expect(url.searchParams.get('next')).toBe('/app/today')
  })

  it('preserves every param of a multi-param destination', () => {
    const url = redirectTo(signedOut(`${LETTER}?src=email&foo=bar`))
    expect(url.searchParams.get('next')).toBe(`${LETTER}?src=email&foo=bar`)
  })

  it('bounces /admin too, with the same shape', () => {
    const url = redirectTo(signedOut('/admin'))
    expect(url.pathname).toBe('/auth')
    expect(url.searchParams.get('next')).toBe('/admin')
  })
})

describe('middleware — what it must NOT do', () => {
  it('lets a signed-in reader through to the letter', () => {
    const res = middleware(signedIn(`${LETTER}?src=email`))
    expect(res.headers.get('location')).toBeNull()
  })

  it('still sends a signed-in user away from /auth', () => {
    const url = redirectTo(signedIn('/auth'))
    expect(url.pathname).toBe('/app/welcome')
  })

  it('does not touch a public route', () => {
    const res = middleware(signedOut('/legal/privacy'))
    expect(res.headers.get('location')).toBeNull()
  })

  it('accepts an Authorization header as authentication, as before', () => {
    const req = new NextRequest(new URL(LETTER, ORIGIN), {
      headers: { authorization: 'Bearer a.b.c' },
    })
    expect(middleware(req).headers.get('location')).toBeNull()
  })
})

describe('middleware — the returnTo it produces is one safeReturnTo accepts', () => {
  it('round-trips through the validator unchanged', async () => {
    // The two halves are written in different files and could disagree; a `next`
    // the validator rejects would silently send every bounced reader to Today.
    const { safeReturnTo } = await import('../lib/safeReturnTo')
    const url = redirectTo(signedOut(`${LETTER}?src=email`))
    const next = url.searchParams.get('next') as string
    expect(safeReturnTo(next)).toBe(`${LETTER}?src=email`)
  })
})
