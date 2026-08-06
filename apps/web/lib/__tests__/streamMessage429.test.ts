// RF-02: verify upgradeTarget is computed correctly from userPlan on 429
import { describe, it, expect, vi, afterEach } from 'vitest'
import { api, RateLimitError } from '../api'

function make429Fetch(body: object) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status: 429,
    headers: {
      get: (name: string) => {
        const h: Record<string, string> = {
          'X-RateLimit-Limit': '10',
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': '2026-05-17T12:00:00Z',
        }
        return h[name] ?? null
      },
    },
    json: vi.fn().mockResolvedValue(body),
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('RF-02 upgradeTarget on 429', () => {
  it('free user gets upgradeTarget "pro"', async () => {
    vi.stubGlobal('fetch', make429Fetch({ error_code: 'rate_limited', persona_voice: 'I am limited.' }))

    const err = await api.streamMessage('conv-1', 'hello', 'free').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(RateLimitError)
    expect((err as RateLimitError).upgradeTarget).toBe('pro')
  })

  it('pro user ALSO gets upgradeTarget "pro" — Premium is retired', async () => {
    // This test previously asserted 'premium', pinning the defect: a paying Pro
    // user hitting a rate limit was offered a tier that will never exist.
    vi.stubGlobal('fetch', make429Fetch({ error_code: 'rate_limited', persona_voice: 'I am limited.' }))

    const err = await api.streamMessage('conv-1', 'hello', 'pro').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(RateLimitError)
    expect((err as RateLimitError).upgradeTarget).toBe('pro')
  })

  it('parses X-RateLimit headers into RateLimitError fields', async () => {
    vi.stubGlobal('fetch', make429Fetch({ error_code: 'rate_limited', persona_voice: 'Rest now.' }))

    const err = await api.streamMessage('conv-1', 'hello', 'free').catch((e: unknown) => e) as RateLimitError
    expect(err.limit).toBe(10)
    expect(err.remaining).toBe(0)
    expect(err.resetAt).toEqual(new Date('2026-05-17T12:00:00Z'))
    expect(err.personaVoice).toBe('Rest now.')
    expect(err.errorCode).toBe('rate_limited')
  })
})
