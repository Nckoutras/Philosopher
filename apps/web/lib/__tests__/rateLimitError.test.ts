import { describe, it, expect } from 'vitest'
import { RateLimitError } from '../api'

describe('RateLimitError', () => {
  it('constructs with all fields and correct prototype chain', () => {
    const resetAt = new Date('2026-05-17T12:00:00Z')
    const err = new RateLimitError({
      resetAt,
      limit: 10,
      remaining: 0,
      errorCode: 'rate_limited',
      personaVoice: 'The well of thought runs dry.',
      upgradeTarget: 'pro',
    })

    expect(err).toBeInstanceOf(RateLimitError)
    expect(err).toBeInstanceOf(Error)
    expect(err.message).toBe('RATE_LIMIT')
    expect(err.name).toBe('RateLimitError')
    expect(err.resetAt).toEqual(resetAt)
    expect(err.limit).toBe(10)
    expect(err.remaining).toBe(0)
    expect(err.errorCode).toBe('rate_limited')
    expect(err.personaVoice).toBe('The well of thought runs dry.')
    expect(err.upgradeTarget).toBe('pro')
  })

  it('constructs without optional personaVoice', () => {
    const err = new RateLimitError({
      resetAt: new Date(),
      limit: 50,
      remaining: 0,
      errorCode: 'rate_limited',
      upgradeTarget: 'pro',
    })

    expect(err.personaVoice).toBeUndefined()
    expect(err.upgradeTarget).toBe('pro')
  })
})
