// A11 — sliding session. refreshSession() exchanges a still-valid token for a
// fresh one on app load and on return to the foreground.
//
// Runs in the default `node` environment, like the other lib/__tests__ api
// tests. That means setToken's persistence branch (`typeof window !==
// 'undefined'` → localStorage + middleware cookie) does not execute here, so the
// assertions are on what the app actually depends on: which bearer token the
// NEXT request carries. That is the observable contract; localStorage is the
// mechanism.
//
// The load-bearing assertion is the failure one: a refresh failure must NEVER
// log anyone out. Refresh is a background convenience; the 401 self-heal in
// request() is what handles a genuinely dead session.
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { api } from '../api'

function okFetch(accessToken: string) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue({
      access_token: accessToken,
      token_type: 'bearer',
      user: { id: 'u1', email: 'reader@example.com' },
    }),
  })
}

function failingFetch(status: number) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: vi.fn().mockResolvedValue({ detail: 'nope' }),
  })
}

/** The bearer token the client would send right now, read off a probe request. */
async function currentBearer(): Promise<string | undefined> {
  const probe = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue({}),
  })
  vi.stubGlobal('fetch', probe)
  await api.me()
  return probe.mock.calls[0][1].headers.Authorization
}

beforeEach(() => {
  api.setToken('old-token')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  api.setToken(null)
})

describe('refreshSession', () => {
  it('adopts the new token on success', async () => {
    vi.stubGlobal('fetch', okFetch('fresh-token'))

    const ok = await api.refreshSession()

    expect(ok).toBe(true)
    expect(await currentBearer()).toBe('Bearer fresh-token')
  })

  it('sends the CURRENT token as its own credential', async () => {
    const f = okFetch('fresh-token')
    vi.stubGlobal('fetch', f)

    await api.refreshSession()

    const [url, init] = f.mock.calls[0]
    expect(url).toContain('/auth/refresh')
    expect(init.method).toBe('POST')
    expect(init.headers.Authorization).toBe('Bearer old-token')
  })

  it('swallows a failed response WITHOUT clearing the session', async () => {
    // The assertion that matters. Losing the token here would sign out every
    // user whose refresh hit a blip — the exact regression this feature exists
    // to prevent.
    vi.stubGlobal('fetch', failingFetch(500))

    const ok = await api.refreshSession()

    expect(ok).toBe(false)
    expect(await currentBearer()).toBe('Bearer old-token')
  })

  it('swallows a network error WITHOUT clearing the session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    const ok = await api.refreshSession()

    expect(ok).toBe(false)
    expect(await currentBearer()).toBe('Bearer old-token')
  })

  it('never throws, so it can be fired and forgotten at app load', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await expect(api.refreshSession()).resolves.toBe(false)
  })

  it('does nothing when there is no token to refresh', async () => {
    api.setToken(null)
    const f = okFetch('fresh-token')
    vi.stubGlobal('fetch', f)

    const ok = await api.refreshSession()

    expect(ok).toBe(false)
    expect(f).not.toHaveBeenCalled()
  })

  it('collapses concurrent calls into a single request', async () => {
    const f = okFetch('fresh-token')
    vi.stubGlobal('fetch', f)

    const [a, b] = await Promise.all([api.refreshSession(), api.refreshSession()])

    expect(f).toHaveBeenCalledTimes(1)
    expect([a, b].filter(Boolean)).toHaveLength(1)
  })
})
