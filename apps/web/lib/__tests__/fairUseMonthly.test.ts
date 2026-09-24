// The Pro MONTHLY ceiling (founder ruling 2026-09-24): 400 per UTC calendar month.
//
// The backend refuses with the SAME error_code as the daily cap — fair_use_limit —
// and says which window refused in `period`. It is deliberately not a new code:
// every client branch that does not match 'fair_use_limit' opens the PaywallModal,
// so a new code would show a paying subscriber an upgrade prompt on any client
// that had not yet learned it.
//
// What this file pins:
//   1. `period` survives the wire at EVERY door the fair-use cap guards. A door
//      that drops it silently falls back to the daily sentence and a clock-time
//      reset — "Resets at 1:00 AM" on a refusal that lasts until the 1st.
//   2. The copy module picks the sentence from `period`, and an absent period
//      words itself exactly as before (older API, same text).
import { describe, it, expect, vi, afterEach } from 'vitest'
import { api, RateLimitError } from '../api'
import { FAIR_USE_COPY, fairUseMessage, resetDateSuffix } from '../fairUseCopy'

const MONTH_RESET = '2026-10-01T00:00:00Z'

function make429Fetch(body: object) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status: 429,
    statusText: 'Too Many Requests',
    headers: {
      get: (name: string) => {
        const h: Record<string, string> = {
          'X-RateLimit-Limit': '400',
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': MONTH_RESET,
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

// Every door check_fair_use_limit guards, by the api method the client calls.
const DOORS: Array<[string, () => Promise<unknown>]> = [
  ['streamMessage', () => api.streamMessage('conv-1', 'hello', 'pro')],
  ['streamAnotherMind', () => api.streamAnotherMind('conv-1', 'socrates', 'pro')],
  ['streamGoDeeper', () => api.streamGoDeeper('conv-1', 'pro')],
  ['counterviewFromInsight', () => api.counterviewFromInsight('insight-1')],
  ['createCounterview', () => api.createCounterview('a belief')],
]

describe.each(DOORS)('%s carries the fair-use period', (_name, call) => {
  it('month', async () => {
    vi.stubGlobal('fetch', make429Fetch({ error_code: 'fair_use_limit', period: 'month' }))
    const err = (await call().catch((e: unknown) => e)) as RateLimitError
    expect(err).toBeInstanceOf(RateLimitError)
    expect(err.errorCode).toBe('fair_use_limit')
    expect(err.period).toBe('month')
    expect(err.resetAt).toEqual(new Date(MONTH_RESET))
  })

  it('absent (an API from before the monthly cap) stays undefined', async () => {
    vi.stubGlobal('fetch', make429Fetch({ error_code: 'fair_use_limit' }))
    const err = (await call().catch((e: unknown) => e)) as RateLimitError
    expect(err.period).toBeUndefined()
  })
})

describe('fairUseMessage', () => {
  const reset = new Date(MONTH_RESET)

  it('words the monthly refusal with the approved sentence and a DATE', () => {
    const shown = fairUseMessage(reset, 'month')
    expect(shown.startsWith(FAIR_USE_COPY.monthly)).toBe(true)
    expect(FAIR_USE_COPY.monthly).toBe(
      "You've reached this month's limit. Everything here will be waiting when it resets.",
    )
    // Shape, not the formatted text: that is the runner's ICU output.
    expect(shown.slice(FAIR_USE_COPY.monthly.length)).toMatch(/^ Resets on .+\.$/)
    expect(shown).not.toContain('Resets at')
  })

  it('reads the monthly reset date in UTC, so it is the 1st everywhere', () => {
    // 00:00 UTC on Oct 1 is still Sep 30 in every timezone west of UTC. Reading
    // it locally would name the wrong month for half the world.
    const utcDay = reset.toLocaleDateString(undefined, { month: 'long', day: 'numeric', timeZone: 'UTC' })
    expect(resetDateSuffix(reset)).toBe(` Resets on ${utcDay}.`)
  })

  it('keeps the daily sentence and clock time for period "day" and for no period', () => {
    for (const period of ['day', undefined] as const) {
      const shown = fairUseMessage(reset, period)
      expect(shown.startsWith(FAIR_USE_COPY.message)).toBe(true)
      expect(shown.slice(FAIR_USE_COPY.message.length)).toMatch(/^ Resets at .+\.$/)
    }
  })

  it('drops only the suffix when the date is unusable', () => {
    expect(fairUseMessage(new Date('not-a-date'), 'month')).toBe(FAIR_USE_COPY.monthly)
  })
})
